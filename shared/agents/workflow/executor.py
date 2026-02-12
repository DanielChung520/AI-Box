# Agent Workflow Executor - 工作流執行器
# 實現步驟執行、RQ 任務隊列整合、Heartbeat 機制
# 創建日期: 2026-02-08

import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import sys
from pathlib import Path

# 添加 shared 目錄到路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from shared.agents.workflow.schema import (
    WorkflowState,
    SagaStep,
    StepStatus,
    WorkflowStatus,
    StepExecutionRequest,
)
from shared.agents.workflow.state import get_workflow_state_manager
from shared.agents.todo.schema import ExecutionResult as TodoExecutionResult
from shared.agents.todo.retry import RetryConfig, RetryPolicy

logger = logging.getLogger(__name__)

# RQ 任務隊列
GENAI_CHAT_QUEUE = "genai_chat"


class WorkflowExecutor:
    """工作流執行器 - 負責步驟執行和 RQ 整合"""

    def __init__(self):
        """初始化執行器"""
        self._state_manager = get_workflow_state_manager()
        self._retry_policy = RetryPolicy(RetryConfig(max_attempts=3, initial_delay=1.0))
        self._action_handlers: Dict[str, Callable] = {}

    def register_handler(self, action_type: str, handler: Callable) -> None:
        """註冊動作處理器"""
        self._action_handlers[action_type] = handler
        logger.info(f"[WorkflowExecutor] Registered handler for: {action_type}")

    async def execute_step(
        self,
        workflow: WorkflowState,
        step: SagaStep,
        previous_results: Dict[str, Any],
        user_response: Optional[str] = None,
    ) -> TodoExecutionResult:
        """執行單一步驟"""
        step_id = step.step_id

        # 更新步驟狀態為執行中
        step.status = StepStatus.EXECUTING
        await self._state_manager.update(workflow)

        try:
            # 獲取處理器
            handler = self._action_handlers.get(step.action_type)
            if not handler:
                # 默認處理器
                result = await self._default_handler(step, previous_results)
            else:
                # 調用註冊的處理器
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(step, previous_results, user_response)
                else:
                    result = handler(step, previous_results, user_response)

            # 執行成功
            step.status = StepStatus.COMPLETED
            workflow.completed_steps.append(step_id)
            workflow.results[str(step_id)] = result.data or {}
            workflow.current_step = step_id

            # 更新工作流狀態
            if workflow.status == WorkflowStatus.PENDING:
                workflow.status = WorkflowStatus.RUNNING

            await self._state_manager.update(workflow)

            # 記錄事件
            await self._state_manager._log_event(
                workflow_id=workflow.workflow_id,
                event_type="step_completed",
                step_id=step_id,
                to_status="completed",
                details={"action_type": step.action_type},
            )

            return TodoExecutionResult(
                success=True,
                data=result.data or {},
                observation=f"步驟 {step_id} 執行成功",
            )

        except Exception as e:
            logger.error(f"[WorkflowExecutor] Step {step_id} failed: {e}")

            # 檢查是否可重試
            if step.retry_count < step.max_retries:
                step.retry_count += 1
                await self._state_manager.update(workflow)

                # 重試
                return await self._retry_with_backoff(workflow, step, previous_results)

            # 重試次數用盡，標記為失敗
            step.status = StepStatus.FAILED
            workflow.failed_steps.append(step_id)
            workflow.error = str(e)
            await self._state_manager.update(workflow)

            return TodoExecutionResult(
                success=False,
                error={
                    "code": "STEP_FAILED",
                    "message": str(e),
                    "recoverable": False,
                },
                observation=f"步驟 {step_id} 失敗",
            )

    async def _default_handler(
        self,
        step: SagaStep,
        previous_results: Dict[str, Any],
    ) -> TodoExecutionResult:
        """默認處理器（由 LLM 生成結果）"""
        import httpx

        # 根據 action_type 調用不同的服務
        action_type = step.action_type

        if action_type == "knowledge_retrieval":
            # 調用 KA-Agent
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://localhost:8000/api/v1/agents/execute",
                    json={
                        "agent_id": "ka-agent",
                        "task": {
                            "type": "knowledge_query",
                            "action": "ka.retrieve",
                            "instruction": step.instruction,
                        },
                    },
                )
                result = response.json()
                return TodoExecutionResult(
                    success=result.get("status") == "success",
                    data=result.get("result", {}),
                    observation="知識檢索完成",
                )

        elif action_type == "data_query":
            # 調用 Data-Agent
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "http://localhost:8004/execute",
                    json={
                        "task_id": f"workflow_{step.step_id}",
                        "task_type": "data_query",
                        "task_data": {
                            "action": "execute_structured_query",
                            "natural_language_query": step.instruction,
                        },
                    },
                )
                result = response.json()
                return TodoExecutionResult(
                    success=result.get("status") == "completed",
                    data=result.get("result", {}),
                    observation=f"數據查詢完成，返回 {len(result.get('result', {}).get('rows', []))} 行",
                )

        elif action_type == "response_generation":
            # 調用 LLM 生成回覆
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "gpt-oss:120b",
                        "prompt": step.instruction,
                        "stream": False,
                        "options": {"temperature": 0.7},
                    },
                )
                llm_result = response.json()
                return TodoExecutionResult(
                    success=True,
                    data={"response": llm_result.get("response", "")},
                    observation="回覆生成完成",
                )

        else:
            # 未知類型，返回錯誤
            return TodoExecutionResult(
                success=False,
                error={"code": "UNKNOWN_ACTION", "message": f"未知動作類型: {action_type}"},
                observation=f"無法處理動作類型: {action_type}",
            )

    async def _retry_with_backoff(
        self,
        workflow: WorkflowState,
        step: SagaStep,
        previous_results: Dict[str, Any],
    ) -> TodoExecutionResult:
        """帶退避的重試"""
        import httpx

        delay = 1.0 * (2**step.retry_count)
        logger.info(f"[WorkflowExecutor] Retrying step {step.step_id} in {delay}s")

        await asyncio.sleep(delay)
        return await self.execute_step(workflow, step, previous_results)


class RQTaskWrapper:
    """RQ 任務包裝器（用於異步執行）"""

    @staticmethod
    def create_execute_step_task():
        """創建 RQ 任務函數"""

        from database.rq.queue import get_task_queue, GENAI_CHAT_QUEUE
        from rq import job

        queue = get_task_queue(GENAI_CHAT_QUEUE)

        @job(queue)
        def execute_step_task(
            workflow_id: str,
            step_id: int,
            action_type: str,
            instruction: str,
            parameters: Dict[str, Any],
            compensation_key: str,
            retry_count: int = 0,
        ):
            """執行單一步驟的 RQ 任務（同步版本）"""
            import asyncio
            from shared.agents.workflow.state import get_workflow_state_manager
            from shared.agents.workflow.schema import (
                WorkflowState,
                SagaStep,
                StepStatus,
            )

            async def run():
                state_manager = get_workflow_state_manager()

                # 獲取工作流
                workflow = await state_manager.get(workflow_id)
                if not workflow:
                    return {"success": False, "error": "工作流不存在"}

                # 獲取步驟
                step = next((s for s in workflow.steps if s.step_id == step_id), None)
                if not step:
                    return {"success": False, "error": "步驟不存在"}

                # 執行
                executor = WorkflowExecutor()
                result = await executor.execute_step(workflow, step, workflow.results)

                return {
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "observation": result.observation,
                }

            # 運行異步任務
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(run())
            finally:
                loop.close()

        return execute_step_task


class HeartbeatManager:
    """心跳管理器 - 監控工作流執行狀態"""

    def __init__(self):
        """初始化心跳管理器"""
        self._state_manager = get_workflow_state_manager()
        self._tasks: Dict[str, asyncio.Task] = {}

    async def start(
        self,
        workflow_id: str,
        step_id: int,
        interval: float = 5.0,
    ) -> None:
        """啟動心跳"""
        if workflow_id in self._tasks:
            self._tasks[workflow_id].cancel()

        task = asyncio.create_task(self._heartbeat_loop(workflow_id, step_id, interval))
        self._tasks[workflow_id] = task

    async def stop(self, workflow_id: str) -> None:
        """停止心跳"""
        if workflow_id in self._tasks:
            self._tasks[workflow_id].cancel()
            del self._tasks[workflow_id]

    async def _heartbeat_loop(
        self,
        workflow_id: str,
        step_id: int,
        interval: float,
    ) -> None:
        """心跳循環"""
        try:
            while True:
                await self._state_manager.update_heartbeat(workflow_id)
                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            logger.info(f"[HeartbeatManager] Heartbeat stopped for: {workflow_id}")

    async def check_all_timed_out(self, timeout: float = 300.0) -> list:
        """檢查所有超時的工作流"""
        timed_out = []

        # 獲取所有運行中的工作流
        workflows = await self._state_manager.list_by_status(WorkflowStatus.RUNNING.value)

        for workflow in workflows:
            if await self._state_manager.check_timeout(workflow.workflow_id, timeout):
                timed_out.append(workflow.workflow_id)

        return timed_out


# 單例實例
_executor: Optional[WorkflowExecutor] = None
_heartbeat_manager: Optional[HeartbeatManager] = None


def get_workflow_executor() -> WorkflowExecutor:
    """獲取執行器單例"""
    global _executor
    if _executor is None:
        _executor = WorkflowExecutor()
    return _executor


def get_heartbeat_manager() -> HeartbeatManager:
    """獲取心跳管理器單例"""
    global _heartbeat_manager
    if _heartbeat_manager is None:
        _heartbeat_manager = HeartbeatManager()
    return _heartbeat_manager
