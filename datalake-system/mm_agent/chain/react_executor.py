# 代碼功能說明: ReAct 模式執行器 - 執行 TODO 步驟
# 創建日期: 2026-02-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-08
# v1.2 更新: 集成 Saga 補償機制

"""ReAct 模式執行器 - 執行 TODO 步驟（帶補償機制）"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime

import sys

sys.path.insert(0, "/home/daniel/ai-box")

from shared.agents.todo.schema import (
    Todo,
    TodoType,
    TodoState,
    ExecutionResult as TodoExecutionResult,
)
from shared.agents.todo.state_machine import TodoStateMachine
from shared.agents.todo.preconditions import PreconditionChecker, PreconditionType
from shared.agents.contracts.heartbeat import get_heartbeat_manager
from shared.database.arango_client import SharedArangoClient

from .compensation import get_compensation_manager
from .react_planner import Action, TodoPlan, ReActPlanner

logger = logging.getLogger(__name__)


def _get_rq_queue():
    """Lazy import RQ queue"""
    from database.rq.queue import get_task_queue, AGENT_TODO_QUEUE

    return get_task_queue(AGENT_TODO_QUEUE)


def _get_enqueue_function():
    """Lazy import enqueue function"""
    from .rq_task import enqueue_agent_todo

    return enqueue_agent_todo


_react_engine_instance = None


def get_react_engine() -> "ReActEngine":
    """獲取 ReActEngine 單例"""
    global _react_engine_instance
    if _react_engine_instance is None:
        _react_engine_instance = ReActEngine()
    return _react_engine_instance


class WorkflowState(BaseModel):
    """工作流狀態"""

    session_id: str
    instruction: str
    plan: Optional[Dict[str, Any]] = None
    current_step: int = 0
    completed_steps: List[int] = []
    failed_steps: List[int] = []
    results: Dict[str, Any] = {}
    context: Optional[Dict[str, Any]] = None

    # Saga 補償機制
    compensations: List[Dict] = []  # 補償動作列表
    compensation_history: List[Dict] = []  # 補償歷史
    status: str = "pending"  # pending/running/completed/failed/compensating

    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class ReActEngine:
    """ReAct 模式引擎 - 管理工作流程（帶補償機制）"""

    def __init__(self):
        """初始化引擎"""
        self._planner = ReActPlanner()
        self._executor = ReActExecutor()
        self._compensation_mgr = None  # 延遲初始化
        self._workflows: Dict[str, WorkflowState] = {}
        self._sse_publisher = SSEPublisher.get_instance()
        logger.info("[ReActEngine] ReAct 引擎初始化完成（帶補償機制）")

    async def start_workflow(
        self,
        instruction: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """啟動工作流程

        Args:
            instruction: 用戶指令
            session_id: 會話 ID
            context: 上下文信息

        Returns:
            工作流程結果
        """
        logger.info(
            f"[ReActEngine] 啟動工作流程: session_id={session_id}, instruction={instruction[:50]}..."
        )

        if session_id in self._workflows:
            logger.info("[ReActEngine] 會話已存在，清除舊狀態")
            del self._workflows[session_id]

        # 發布 LLM 思考開始
        self._sse_publisher.publish_thinking(
            request_id=session_id,
            thinking="正在分析用戶需求...",
            progress=0.0,
        )

        plan = await self._planner.plan(instruction, context)

        # 發布工作流計劃
        if plan and plan.steps:
            plan_steps = [
                {
                    "step_id": s.step_id,
                    "action_type": s.action_type,
                    "description": s.description,
                }
                for s in plan.steps
            ]
            self._sse_publisher.publish_workflow_plan(
                request_id=session_id,
                instruction=instruction,
                steps=plan_steps,
            )
        else:
            logger.warning("[ReActEngine] 無法生成計劃")
            return {
                "success": False,
                "task_type": "unknown",
                "error": "無法生成計劃",
            }

        # 初始化補償管理器
        comp_mgr = get_compensation_manager()

        # 為每個步驟創建補償動作
        compensations = []
        if plan and plan.steps:
            for step in plan.steps:
                compensation = comp_mgr.create_compensation(
                    step_id=step.step_id,
                    action_type=step.action_type,
                    params={
                        "description": step.description,
                        "instruction": step.instruction,
                    },
                )
                compensations.append(compensation)
                logger.info(
                    f"[ReActEngine] Created compensation: step={step.step_id}, type={compensation.compensation_type}"
                )

        # 將 CompensationAction 轉換為 Dict
        compensations_dict = [
            {
                "action_id": c.action_id,
                "step_id": c.step_id,
                "action_type": c.action_type,
                "compensation_type": c.compensation_type,
                "params": c.params,
                "status": c.status,
            }
            for c in compensations
        ]

        self._workflows[session_id] = WorkflowState(
            session_id=session_id,
            instruction=instruction,
            plan=plan.model_dump() if plan else None,
            current_step=0,
            completed_steps=[],
            failed_steps=[],
            results={},
            context=context,
            compensations=compensations_dict,
            status="pending",
        )

        self._sse_publisher.start_tracking(session_id)

        step_names = [s.description for s in (plan.steps if plan else [])]
        total = len(plan.steps) if plan else 0

        self._sse_publisher.publish(
            request_id=session_id,
            step="workflow_started",
            status="processing",
            message=f"工作流程已啟動，共 {total} 個步驟",
            progress=0.0,
        )

        for i, step_name in enumerate(step_names):
            self._sse_publisher.publish(
                request_id=session_id,
                step=step_name,
                status="pending",
                message=f"等待執行: {step_name}",
                progress=(i) / total if total > 0 else 0,
            )

        logger.info(f"[ReActEngine] 生成計劃: {len(plan.steps) if plan else 0} 步驟")

        return {
            "success": True,
            "task_type": plan.task_type if plan else "unknown",
            "plan": {
                "task_type": plan.task_type if plan else "unknown",
                "steps": [
                    {
                        "step_id": s.step_id,
                        "action_type": s.action_type,
                        "description": s.description,
                        "instruction": s.instruction,
                    }
                    for s in (plan.steps if plan else [])
                ],
                "thought_process": plan.thought_process if plan else "",
            },
            "response": self._planner.format_plan(plan) if plan else "無法生成計劃",
        }

    async def execute_next_step(
        self,
        session_id: str,
        user_response: Optional[str] = None,
    ) -> Dict[str, Any]:
        """執行工作流程下一步

        Args:
            session_id: 會話 ID
            user_response: 用戶回覆（用於 user_confirmation 步驟）

        Returns:
            執行結果
        """
        logger.info(f"[ReActEngine] 執行下一步: session_id={session_id}")

        if session_id not in self._workflows:
            return {"success": False, "error": "會話不存在"}

        state = self._workflows[session_id]
        if not state.plan or not state.plan.get("steps"):
            return {"success": False, "error": "計劃不存在"}

        plan_dict = state.plan
        steps_data = plan_dict.get("steps", [])

        state.current_step += 1

        if state.current_step > len(steps_data):
            logger.info("[ReActEngine] 所有步驟已完成")
            final_response = state.results.get(
                "final_response", state.results.get("response", "處理完成")
            )
            return {
                "success": True,
                "response": final_response,
                "step_id": state.current_step,
                "completed_steps": state.completed_steps,
                "total_steps": len(steps_data),
                "waiting_for_user": False,
                "debug_info": {"step": "workflow_completed", "all_results": state.results},
            }

        step_data = steps_data[state.current_step - 1]
        action_type = step_data.get("action_type", "unknown")
        description = step_data.get("description", "")
        total_steps = len(steps_data)
        current = state.current_step

        # 發布步驟開始
        self._sse_publisher.publish_step_start(
            request_id=session_id,
            step_id=current,
            action_type=action_type,
            description=description,
            total_steps=total_steps,
        )

        if action_type == "user_confirmation":
            state.completed_steps.append(state.current_step)
            question = step_data.get("parameters", {}).get("question", "確認？")
            return {
                "success": True,
                "response": question,
                "step_id": state.current_step,
                "action_type": action_type,
                "completed_steps": state.completed_steps,
                "total_steps": len(steps_data),
                "waiting_for_user": True,
                "debug_info": {"step": "waiting_confirmation"},
            }

        from .react_planner import Action

        action = Action(
            step_id=step_data.get("step_id", state.current_step),
            action_type=action_type,
            description=description,
            parameters=step_data.get("parameters", {}),
            dependencies=step_data.get("dependencies", []),
            result_key=step_data.get("result_key"),
        )

        from .react_planner import TodoPlan

        plan_obj = TodoPlan(**plan_dict)
        previous_results = {k: v for k, v in state.results.items() if k != "final_response"}

        progress = current / total_steps if total_steps > 0 else 0

        self._sse_publisher.publish(
            request_id=session_id,
            step=f"step_{current}_{action_type}",
            status="processing",
            message=f"正在執行: {description}",
            progress=progress,
        )

        result = await self._executor.execute_step(action, plan_obj, previous_results, session_id)

        # 檢查步驟是否失敗
        step_failed = (
            result is None
            or (hasattr(result, "success") and not result.success)
            or (isinstance(result, dict) and not result.get("success", True))
        )

        if step_failed:
            logger.warning(
                f"[ReActEngine] 步驟失敗: step={state.current_step}, action={action_type}"
            )
            state.failed_steps.append(state.current_step)
            state.status = "compensating"

            # 執行補償
            if state.compensations:
                comp_mgr = get_compensation_manager()
                completed_comps = [c for c in state.compensations if c.get("status") == "pending"]
                if completed_comps:
                    logger.info(f"[ReActEngine] 執行補償，共 {len(completed_comps)} 個補償動作")
                    comp_result = await comp_mgr.execute_compensation(
                        completed_comps, state.results
                    )
                    state.compensation_history.append(
                        {
                            "triggered_at": datetime.now().isoformat(),
                            "failed_step": state.current_step,
                            "results": comp_result,
                        }
                    )

            state.status = "failed"
            self._sse_publisher.publish(
                request_id=session_id,
                step=step_data.get("description", f"步驟 {current}"),
                status="error",
                message="步驟失敗，已執行補償",
                progress=1.0,
            )
            return {
                "success": False,
                "response": f"步驟執行失敗: {result.observation if hasattr(result, 'observation') else result.get('observation', '未知錯誤')}",
                "step_id": state.current_step,
                "action_type": action_type,
                "completed_steps": state.completed_steps,
                "failed_steps": state.failed_steps,
                "total_steps": len(steps_data),
                "waiting_for_user": False,
                "compensated": True,
                "debug_info": {
                    "step": "step_failed_compensated",
                    "observation": result.observation if hasattr(result, "observation") else "",
                    "compensation_result": comp_result if "comp_result" in dir() else None,
                },
            }

        state.completed_steps.append(state.current_step)
        state.results[str(state.current_step)] = (
            result.result if hasattr(result, "result") else result.get("result", {})
        )

        if result and result.result:
            for k, v in result.result.items():
                if k not in ["response", "abc_result"]:
                    state.results[k] = v
            # 優先使用 response，若無則使用 business_explanation
            response_text = (
                result.result.get("response") or result.result.get("business_explanation") or ""
            )
            if response_text:
                state.results["final_response"] = response_text

        logger.info(
            f"[ReActEngine] 步驟完成: {action_type}, observation: {result.observation if result else 'N/A'}"
        )

        if action_type == "user_confirmation":
            question = step_data.get("parameters", {}).get("question", "確認？")
            return {
                "success": True,
                "response": question,
                "step_id": state.current_step,
                "action_type": action_type,
                "completed_steps": state.completed_steps,
                "total_steps": len(steps_data),
                "waiting_for_user": True,
                "debug_info": {
                    "step": "waiting_confirmation",
                    "observation": result.observation if result else "",
                },
            }

        return {
            "success": True,
            "response": result.observation if result else "處理完成",
            "step_id": state.current_step,
            "action_type": action_type,
            "completed_steps": state.completed_steps,
            "total_steps": len(steps_data),
            "waiting_for_user": False,
            "debug_info": {
                "step": "step_completed",
                "observation": result.observation if result else "",
                "result": result.result if result else {},
            },
        }

    async def execute_all_steps(
        self,
        session_id: str,
        user_response: Optional[str] = None,
        instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """自動執行所有步驟

        Args:
            session_id: 會話 ID
            user_response: 用戶回覆
            instruction: 用戶指令（用於啟動工作流）

        Returns:
            所有步驟執行結果
        """
        logger.info(f"[ReActEngine] 自動執行所有步驟: session_id={session_id}")

        if session_id not in self._workflows:
            if instruction:
                logger.info(f"[ReActEngine] 工作流不存在，自動啟動: session_id={session_id}")
                await self.start_workflow(instruction, session_id, {})
            else:
                return {"success": False, "error": "會話不存在，請先啟動工作流"}

        responses = []
        all_results = []

        while True:
            result = await self.execute_next_step(session_id, user_response)

            # 提取最終回應
            # 優先順序：
            # 1. result.debug_info.result.response (當前步驟的實際回應)
            # 2. result.debug_info.result.business_explanation (當前步驟的業務解釋)
            # 3. 頂層的 response

            response_text = ""

            # 從當前步驟的 debug_info.result 獲取
            debug_info = result.get("debug_info", {})
            nested_result = debug_info.get("result", {})

            if nested_result:
                response_text = (
                    nested_result.get("response") or nested_result.get("business_explanation") or ""
                )

            # 如果沒有找到，使用頂層 response
            if not response_text:
                response_text = result.get("response", "") or "處理完成"

            responses.append(response_text)

            if result.get("completed_steps"):
                all_results.append(result)

            if not result.get("waiting_for_user", False):
                if result.get("success"):
                    logger.info(
                        f"[ReActEngine] 步驟完成: {result.get('step_id')}/{result.get('total_steps')}"
                    )
                else:
                    logger.warning(f"[ReActEngine] 步驟失敗: {result.get('error')}")
                    break

            if not result.get("waiting_for_user", True):
                if result.get("completed_steps") and result.get("total_steps"):
                    if result["completed_steps"][-1] >= result["total_steps"]:
                        logger.info("[ReActEngine] 工作流完成")
                        break
            else:
                break

        final_response = responses[-1] if responses else "處理完成"
        self._workflows.get(session_id)

        self._sse_publisher.publish(
            request_id=session_id,
            step="workflow_completed",
            status="completed",
            message="工作流程已完成",
            progress=1.0,
        )

        self._sse_publisher.end_tracking(session_id)

        return {
            "success": True,
            "final_response": final_response,
            "responses": responses,
            "completed_steps": result.get("completed_steps", []) if result else [],
            "total_steps": result.get("total_steps", 0) if result else 0,
            "all_results": all_results,
        }

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """獲取工作流狀態"""
        if session_id not in self._workflows:
            return None
        state = self._workflows[session_id]
        return {
            "session_id": state.session_id,
            "instruction": state.instruction,
            "current_step": state.current_step,
            "completed_steps": state.completed_steps,
            "total_steps": len(state.plan.get("steps", [])) if state.plan else 0,
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
        }

    def clear_state(self, session_id: str):
        """清除工作流狀態"""
        if session_id in self._workflows:
            del self._workflows[session_id]
            logger.info(f"[ReActEngine] 清除會話狀態: {session_id}")


class ExecutionResult(BaseModel):
    """執行結果"""

    step_id: int
    action_type: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    observation: str = ""


class TodoTracker:
    """Todo 追蹤器 - 集成 Agent-todo v1.1 + SSE"""

    _sse_client: Optional["SSEPublisher"] = None

    def __init__(self):
        self._arango = SharedArangoClient.get_instance()
        self._prechecker = PreconditionChecker()
        self._heartbeat_mgr = get_heartbeat_manager()
        self._current_todos: Dict[str, str] = {}
        self._session_id: Optional[str] = None

    @classmethod
    def set_sse_client(cls, client: "SSEPublisher") -> None:
        """設置 SSE 客戶端"""
        cls._sse_client = client
        logger.info(f"[TodoTracker] SSE client set: {client}")

    def set_session_id(self, session_id: str) -> None:
        """設置會話 ID"""
        self._session_id = session_id
        logger.info(f"[TodoTracker] Session ID set: {session_id}")

    async def _publish_sse(
        self, step: str, status: str, message: str, progress: float = 0.0
    ) -> None:
        """發布 SSE 事件到前端"""
        if not self._session_id or not TodoTracker._sse_client:
            return

        try:
            TodoTracker._sse_client.publish(
                request_id=self._session_id,
                step=step,
                status=status,
                message=message,
                progress=progress,
            )
            logger.info(f"[TodoTracker] SSE published: {step} - {status}")
        except Exception as e:
            logger.warning(f"[TodoTracker] SSE publish failed: {e}")

    async def create_todo(
        self,
        step_id: int,
        action: Action,
        instruction: str,
        total_steps: int = 1,
    ) -> str:
        """為執行步驟建立 Todo（含 Heartbeat）"""
        action_map = {
            "knowledge_retrieval": TodoType.KNOWLEDGE_RETRIEVAL,
            "data_query": TodoType.DATA_QUERY,
            "computation": TodoType.COMPUTATION,
            "response_generation": TodoType.RESPONSE_GENERATION,
        }

        todo_type = action_map.get(action.action_type, TodoType.COMPUTATION)

        todo = Todo(
            type=todo_type,
            owner_agent="MM-Agent",
            instruction=instruction,
            input={
                "step_id": step_id,
                "action_type": action.action_type,
                "description": action.description,
                "parameters": action.parameters,
                "total_steps": total_steps,
            },
        )

        todo_id = await self._arango.create_todo(todo)
        self._current_todos[str(step_id)] = todo_id

        # 創建 Heartbeat
        self._heartbeat_mgr.create(
            todo_id=todo_id,
            total_steps=total_steps,
            callback=None,
            interval=5.0,
        )

        logger.info(f"[TodoTracker] Created todo: {todo_id} for step {step_id}")
        return todo_id

    async def check_preconditions(self, action: Action) -> bool:
        """檢查前置條件"""
        preconditions = []

        if action.action_type == "data_query":
            preconditions.append(
                {"type": PreconditionType.AGENT_AVAILABLE.value, "ref": "data-agent"}
            )
        elif action.action_type == "knowledge_retrieval":
            preconditions.append({"type": PreconditionType.AGENT_AVAILABLE.value, "ref": "llm"})

        if not preconditions:
            return True

        from shared.agents.todo.preconditions import Precondition

        pcs = [Precondition(**pc) for pc in preconditions]
        result = await self._prechecker.check_all(pcs)

        logger.info(f"[TodoTracker] Preconditions: all_satisfied={result.all_satisfied}")
        return result.all_satisfied

    async def dispatch_todo(self, step_id: str) -> bool:
        """分派 Todo"""
        todo_id = self._current_todos.get(step_id)
        if not todo_id:
            return False

        success, event, history = TodoStateMachine.transition(
            TodoState.PENDING, TodoState.DISPATCHED
        )

        if success:
            await self._arango.update_todo(todo_id, state=TodoState.DISPATCHED, history=history)

            # 啟動 Heartbeat
            hb = self._heartbeat_mgr.get(todo_id)
            if hb:
                hb.start(message="Task dispatched")

        return success

    async def update_progress(self, step_id: str, step: int, message: str = ""):
        """更新進度"""
        todo_id = self._current_todos.get(step_id)
        if not todo_id:
            return

        hb = self._heartbeat_mgr.get(todo_id)
        if hb:
            hb.update_progress(step=step, message=message)

    async def complete_todo(
        self,
        step_id: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """完成 Todo"""
        todo_id = self._current_todos.get(step_id)
        if not todo_id:
            return False

        new_state = TodoState.COMPLETED if success else TodoState.FAILED

        success_transition, event, history = TodoStateMachine.transition(
            TodoState.EXECUTING, new_state
        )

        todo_result = TodoExecutionResult(
            success=success,
            data=result or {},
            error=error,
            observation=(result or {}).get("observation", "") if result else "",
        )

        await self._arango.update_todo(
            todo_id, state=new_state, result=todo_result, history=history
        )

        # 完成 Heartbeat
        hb = self._heartbeat_mgr.get(todo_id)
        if hb:
            if success:
                hb.complete(message="Task completed successfully")
            else:
                hb.fail(message=(error or {}).get("message", "Task failed"))

        logger.info(f"[TodoTracker] Completed todo: {todo_id}, state: {new_state}")
        return True


# ==================== RQ Task Integration ====================
# RQ 任務已移到 rq_task.py 模組，避免循環導入問題

# 導入新的 RQ 任務模組
from .rq_task import enqueue_agent_todo, execute_agent_todo_sync, AGENT_TODO_QUEUE


def enqueue_rq_task(
    session_id: str,
    step_id: int,
    action_type: str,
    instruction: str,
    parameters: Dict[str, Any],
    total_steps: int,
) -> str:
    """交付 RQ 任務並返回 job_id（使用新模組）"""
    return enqueue_agent_todo(
        session_id=session_id,
        step_id=step_id,
        action_type=action_type,
        instruction=instruction,
        parameters=parameters,
        total_steps=total_steps,
    )


class ReActExecutor:
    """ReAct 模式執行器 - 集成 Agent-todo + RQ 任務交付"""

    def __init__(self):
        """初始化執行器"""
        self._knowledge_client = None
        self._data_client = None
        self._tracker = TodoTracker()
        self._use_rq = True  # 是否使用 RQ 交付
        self._sse_publisher = SSEPublisher.get_instance()  # SSE 發布器

    async def execute_step(
        self,
        action: Action,
        plan: TodoPlan,
        previous_results: Dict[str, Any],
        session_id: str = "unknown",
    ) -> ExecutionResult:
        """執行單一步驟

        Args:
            action: 行動定義
            plan: 工作計劃
            previous_results: 之前的執行結果
            session_id: 會話 ID

        Returns:
            ExecutionResult: 執行結果
        """
        logger.info(f"[ReActExecutor] 執行步驟 {action.step_id}: {action.action_type}")

        instruction = action.parameters.get("instruction", action.description)
        total_steps = len(plan.steps)

        # 1. 建立 Todo（含 Heartbeat）
        todo_id = await self._tracker.create_todo(action.step_id, action, instruction, total_steps)

        # 2. 使用 RQ 交付任務（非同步執行）
        if self._use_rq:
            try:
                from .rq_task import enqueue_agent_todo

                job_id = enqueue_agent_todo(
                    session_id=session_id,
                    step_id=action.step_id,
                    action_type=action.action_type,
                    instruction=instruction,
                    parameters=action.parameters,
                    total_steps=total_steps,
                )
                logger.info(f"[ReActExecutor] RQ 任務已交付: job_id={job_id}")

                # 發布 RQ 交付事件
                self._sse_publisher.publish_rq_delivery(
                    request_id=session_id,
                    step_id=action.step_id,
                    action_type=action.action_type,
                    job_id=job_id,
                )

                # RQ 交付後直接返回，讓 Worker 異步執行
                await self._tracker.dispatch_todo(str(action.step_id))
                await self._tracker.update_progress(
                    str(action.step_id), step=1, message=f"任務已交付到 RQ: {job_id}"
                )

                return ExecutionResult(
                    step_id=action.step_id,
                    action_type=action.action_type,
                    success=True,
                    result={"job_id": job_id, "rq_delivered": True},
                    observation=f"步驟已交付到 RQ 隊列，job_id={job_id}",
                )

            except Exception as e:
                logger.warning(f"[ReActExecutor] RQ 交付失敗，回退到同步執行: {e}")
                self._use_rq = False

        # 3. 同步執行模式（回退）
        preconditions_ok = await self._tracker.check_preconditions(action)
        if not preconditions_ok:
            error_result = ExecutionResult(
                step_id=action.step_id,
                action_type=action.action_type,
                success=False,
                error="前置條件檢查失敗",
                observation="Preconditions check failed",
            )
            await self._tracker.complete_todo(
                str(action.step_id),
                success=False,
                error={"code": "PRECONDITIONS_FAILED", "message": "前置條件檢查失敗"},
            )
            return error_result

        # 分派 Todo
        await self._tracker.dispatch_todo(str(action.step_id))
        await self._tracker.update_progress(
            str(action.step_id), step=1, message=f"執行 {action.action_type}"
        )

        try:
            # 4. 執行步驟
            if action.action_type == "knowledge_retrieval":
                result = await self._execute_knowledge_retrieval(
                    action, previous_results, session_id
                )
            elif action.action_type == "data_query":
                result = await self._execute_data_query(action, previous_results, session_id)
            elif action.action_type == "data_cleaning":
                result = await self._execute_data_cleaning(action, previous_results)
            elif action.action_type == "computation":
                result = await self._execute_computation(action, previous_results)
            elif action.action_type == "visualization":
                result = await self._execute_visualization(action, previous_results)
            elif action.action_type == "user_confirmation":
                result = await self._execute_user_confirmation(action, previous_results)
            elif action.action_type == "response_generation":
                result = await self._execute_response_generation(action, previous_results)
            else:
                result = ExecutionResult(
                    step_id=action.step_id,
                    action_type=action.action_type,
                    success=False,
                    error=f"未知的行動類型: {action.action_type}",
                )

            # 5. 完成 Todo
            await self._tracker.complete_todo(
                str(action.step_id),
                success=result.success,
                result=result.model_dump() if result else None,
            )
            return result

        except Exception as e:
            logger.error(f"[ReActExecutor] 步驟執行失敗: {e}", exc_info=True)
            error_result = ExecutionResult(
                step_id=action.step_id,
                action_type=action.action_type,
                success=False,
                error=str(e),
                observation="執行異常",
            )
            await self._tracker.complete_todo(
                str(action.step_id),
                success=False,
                error={"code": "EXECUTION_ERROR", "message": str(e)},
            )
            return error_result

    async def _execute_knowledge_retrieval(
        self, action: Action, previous_results: Dict[str, Any], session_id: str = "unknown"
    ) -> ExecutionResult:
        """執行知識庫檢索"""
        query = action.parameters.get("query", action.description)
        knowledge = ""
        source = "unknown"

        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://localhost:8000/api/v1/agents/execute",
                    json={
                        "agent_id": "ka-agent",
                        "task": {
                            "type": "knowledge_query",
                            "action": "ka.retrieve",
                            "instruction": query,
                            "domain": "mm_agent",
                            "major": "responsibilities",
                            "top_k": 5,
                            "query_type": "hybrid",
                        },
                        "metadata": {
                            "caller_agent_id": "mm-agent",
                            "caller_agent_key": "-h0tjyh",
                        },
                    },
                )

                result = response.json()
                if result.get("status") == "success":
                    knowledge = result.get("result", {}).get("knowledge", "")
                    source = "ka_agent"

        except Exception as e:
            logger.warning(f"[Knowledge] KA-Agent 調用失敗: {e}")

        if not knowledge:
            try:
                import httpx

                async with httpx.AsyncClient(timeout=120.0) as client:
                    llm_response = await client.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": "gpt-oss:120b",
                            "prompt": f"請用繁體中文回答：{query}",
                            "stream": False,
                            "options": {"temperature": 0.3, "num_predict": 2048},
                        },
                    )

                    if llm_response.status_code == 200:
                        llm_result = llm_response.json()
                        knowledge = llm_result.get("response", "")
                        source = "llm_knowledge"

            except Exception as e:
                logger.warning(f"[Knowledge] LLM 生成知識失敗: {e}")

        # 發布知識檢索結果
        self._sse_publisher.publish_knowledge_result(
            request_id=session_id,
            step_id=action.step_id,
            source=source,
            knowledge_length=len(knowledge) if knowledge else 0,
        )

        return ExecutionResult(
            step_id=action.step_id,
            action_type="knowledge_retrieval",
            success=True,
            result={"knowledge": knowledge, "source": source},
            observation=f"知識獲取成功，來源: {source}",
        )

    async def _execute_data_query(
        self, action: Action, previous_results: Dict[str, Any], session_id: str = "unknown"
    ) -> ExecutionResult:
        """執行數據查詢 - 使用 Data-Agent-JP，並通過 LLM 生成業務解說"""
        instruction = action.parameters.get("instruction", action.description)
        logger.info(f"[Data] 開始執行數據查詢: {instruction}")

        try:
            import httpx
            from llm.clients.factory import get_client

            logger.info(
                f"[Data] 準備調用 Data-Agent-JP: http://localhost:8004/api/v1/data-agent/v4/execute"
            )

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "http://localhost:8004/api/v1/data-agent/v4/execute",
                    json={
                        "task_id": f"react_data_{id(instruction)}",
                        "task_type": "schema_driven_query",
                        "task_data": {
                            "nlq": instruction,
                        },
                    },
                )

                result = response.json()

                # 初始化 sql 變量
                sql = ""

                if result.get("status") == "success":
                    rows = result.get("result", {}).get("data", [])
                    sql = result.get("result", {}).get("sql", "")

                    logger.info(f"[Data] Data-Agent 返回: rows={len(rows)}")

                    # 調用 LLM 生成業務解說（無論是否有資料）
                    logger.info(f"[Data] 調用 LLM 生成業務解說...")
                    try:
                        # 構建數據摘要
                        data_summary = self._build_data_summary(rows, instruction)

                        # 根據是否有資料選擇不同的 prompt
                        if rows:
                            explanation_prompt = f"""你是一個物料管理專家，請根據以下查詢結果，用自然語言向用戶解說業務情況：

用戶查詢：{instruction}

查詢結果摘要：
{data_summary}

原始數據：
{self._format_data_for_llm(rows)}

請用專業但易懂的語言，提供以下內容：
1. 簡短說明查詢結果的業務意義
2. 關鍵數據的解讀（如：最大庫存位置、庫存分布等）
3. 建議或提醒（如：庫存過高、過低等）

回答請簡潔明瞭，使用 Markdown 格式。"""
                        else:
                            # 空結果時，LLM 根據用戶意圖生成適當的回覆
                            explanation_prompt = f"""你是一個物料管理專家，用戶查詢：

{instruction}

查詢結果：沒有找到符合條件的資料。

請用自然語言向用戶說明情況，並提供適當的建議（如：檢查查詢條件、輸入不同的關鍵字等）。

回答請簡潔明瞭，使用 Markdown 格式。"""

                        # 調用 LLM
                        from llm.clients.factory import get_client
                        from services.api.models.llm_model import LLMProvider

                        llm_client = get_client(LLMProvider.OLLAMA)

                        logger.info(f"[Data] 發送請求到 LLM...")
                        llm_response = await llm_client.generate(
                            prompt=explanation_prompt,
                            temperature=0.3,
                            max_tokens=1500,
                        )
                        logger.info(f"[Data] LLM 回應類型: {type(llm_response)}")

                        # 處理 LLM 回應（可能是字串或字典）
                        if isinstance(llm_response, str):
                            business_explanation = llm_response
                        elif isinstance(llm_response, dict):
                            business_explanation = llm_response.get("text", "") or llm_response.get(
                                "content", ""
                            )
                        else:
                            business_explanation = str(llm_response)

                        logger.info(f"[Data] LLM 業務解說生成成功: {len(business_explanation)} 字")

                    except Exception as llm_error:
                        logger.warning(f"[Data] LLM 業務解說生成失敗: {llm_error}，使用默認解說")
                        import traceback

                        traceback.print_exc()
                        business_explanation = self._generate_default_explanation(rows, sql=sql)

                    # 發布數據查詢結果
                    self._sse_publisher.publish_data_result(
                        request_id=session_id,
                        step_id=action.step_id,
                        sql=sql,
                        row_count=len(rows),
                        sample_data=rows[:3],
                    )

                    return ExecutionResult(
                        step_id=action.step_id,
                        action_type="data_query",
                        success=True,
                        result={
                            "data": rows,
                            "sql": sql,
                            "row_count": len(rows),
                            "instruction": instruction,
                            "business_explanation": business_explanation,
                        },
                        observation=f"數據查詢完成，返回 {len(rows)} 行",
                    )
                else:
                    # Data-Agent 返回錯誤狀態
                    error_code = result.get("error_code", "")
                    error_msg = result.get("message", "未知錯誤")
                    logger.warning(
                        f"[Data] Data-Agent 返回錯誤: error_code={error_code}, message={error_msg}"
                    )

                    return ExecutionResult(
                        step_id=action.step_id,
                        action_type="data_query",
                        success=False,
                        result={
                            "data": [],
                            "sql": sql if "sql" in dir() else "",
                            "row_count": 0,
                            "instruction": instruction,
                            "error_code": error_code,
                            "business_explanation": error_msg,
                        },
                        observation=f"數據查詢失敗: {error_msg}",
                    )

        except Exception as e:
            logger.warning(f"[Data] Data-Agent 調用失敗: {e}，返回錯誤")
            error_explanation = ""

            # 嘗試讓 LLM 生成錯誤解說
            try:
                from llm.clients.factory import get_client
                from services.api.models.llm_model import LLMProvider

                llm_client = get_client(LLMProvider.OLLAMA)
                error_prompt = f"""用戶查詢：{instruction}

發生錯誤：{str(e)}

請用自然語言向用戶說明發生了什麼問題，並建議用戶可以嘗試什麼。

回答請簡潔明瞭，使用 Markdown 格式。"""
                llm_response = await llm_client.generate(
                    prompt=error_prompt,
                    temperature=0.3,
                    max_tokens=500,
                )
                # 處理 LLM 回應（可能是字串或字典）
                if isinstance(llm_response, str):
                    error_explanation = llm_response
                elif isinstance(llm_response, dict):
                    error_explanation = llm_response.get("text", "") or llm_response.get(
                        "content", ""
                    )
                else:
                    error_explanation = str(llm_response)
            except Exception:
                error_explanation = "查詢失敗，請稍後重試或聯繫管理員。"

            return ExecutionResult(
                step_id=action.step_id,
                action_type="data_query",
                success=False,
                result={
                    "data": [],
                    "sql": "",
                    "row_count": 0,
                    "instruction": instruction,
                    "business_explanation": error_explanation,
                },
                observation=f"數據查詢失敗: {str(e)}",
            )

    def _build_data_summary(self, rows: List[Dict], instruction: str) -> str:
        """構建數據摘要"""
        if not rows:
            return "無符合條件的數據"

        summary_parts = []

        # 統計庫存數據
        if "existing_stocks" in rows[0] or "inventory_value" in rows[0]:
            stocks = [r.get("existing_stocks", 0) or r.get("inventory_value", 0) for r in rows]
            total = sum(stocks)
            max_stock = max(stocks)
            max_location = None
            for r in rows:
                stock = r.get("existing_stocks", 0) or r.get("inventory_value", 0)
                if stock == max_stock:
                    max_location = r.get("warehouse_no", r.get("location_no", "N/A"))
                    break

            summary_parts.append(f"總筆數: {len(rows)}")
            summary_parts.append(f"總庫存/價值: {total:,.2f}")
            summary_parts.append(f"最大庫存位置: {max_location}")

        return " | ".join(summary_parts)

    def _format_data_for_llm(self, rows: List[Dict]) -> str:
        """格式化數據給 LLM"""
        if not rows:
            return "無數據"

        # 只取前 10 行，避免過長
        display_rows = rows[:10]
        lines = []
        for row in display_rows:
            lines.append(str(row))

        if len(rows) > 10:
            lines.append(f"... (共 {len(rows)} 筆數據)")

        return "\n".join(lines)

    def _generate_default_explanation(
        self, rows: List[Dict], sql: str = "", show_sql: bool = False
    ) -> str:
        """生成自然語言回應（表格格式，隱藏 SQL）

        Args:
            rows: 查詢結果數據
            sql: SQL 查詢語句
            show_sql: 是否顯示 SQL（預設 False）
        """
        if not rows:
            return "查詢結果為空，請確認查詢條件是否正確。"

        # 建構表格格式的回應
        lines = []

        # 標題
        lines.append(f"**查詢結果**：共 {len(rows)} 筆資料")

        # 如果是庫存相關查詢，添加統計摘要
        if "existing_stocks" in rows[0]:
            stocks = [r.get("existing_stocks", 0) for r in rows]
            total = sum(stocks)
            positive_stocks = [s for s in stocks if s > 0]

            if positive_stocks:
                lines.append(f"\n**📊 庫存統計**")
                lines.append(f"- 總庫存：{total:,.0f}")
                lines.append(f"- 有庫存的筆數：{len(positive_stocks)} 筆")

                # 最大庫存位置
                max_stock = max(positive_stocks)
                for r in rows:
                    if r.get("existing_stocks", 0) == max_stock:
                        location = r.get("warehouse_no", r.get("location_no", ""))
                        lines.append(f"- 最大庫存位置：{location}，數量：{max_stock:,.0f}")
                        break

        # 數據表格（Markdown 格式）
        lines.append("\n**📋 詳細資料**")

        # 取得欄位名稱
        if rows:
            columns = list(rows[0].keys())

            # 表格標題行
            header = "| " + " | ".join(columns) + " |"
            separator = "| " + " | ".join(["---"] * len(columns)) + " |"
            lines.append(header)
            lines.append(separator)

            # 表格數據行（最多顯示 10 筆）
            display_rows = rows[:10]
            for row in display_rows:
                values = [str(row.get(col, "-")) for col in columns]
                lines.append("| " + " | ".join(values) + " |")

            # 如果超過 10 筆，顯示提示
            if len(rows) > 10:
                lines.append(f"\n> 僅顯示前 10 筆資料，共 {len(rows)} 筆")

        # 可選：顯示 SQL（如果前端要求）
        if show_sql and sql:
            lines.append(f"\n> **SQL 查詢**：`{sql[:200]}`{'...' if len(sql) > 200 else ''}")

        return "\n".join(lines)

    async def _execute_data_cleaning(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """執行數據清洗"""
        _ = action.parameters.get("instruction", action.description)

        query_result = None
        for step_id, step_result in previous_results.items():
            if isinstance(step_result, dict) and "data" in step_result:
                query_result = step_result["data"]
                break

        if not query_result:
            return ExecutionResult(
                step_id=action.step_id,
                action_type="data_cleaning",
                success=True,
                result={"cleaned_data": [], "summary": "無數據可清洗"},
                observation="無數據，跳過清洗",
            )

        try:
            cleaned_data = []
            errors = []

            for idx, row in enumerate(query_result):
                try:
                    cleaned_row = {}

                    for key, value in row.items():
                        if value is None:
                            cleaned_row[key] = None
                        elif isinstance(value, str):
                            cleaned_row[key] = value.strip()
                        elif isinstance(value, (int, float)):
                            cleaned_row[key] = value
                        else:
                            cleaned_row[key] = str(value)

                    if "material_code" not in cleaned_row and "img01" in row:
                        cleaned_row["material_code"] = row["img01"]
                    if "inventory_value" not in cleaned_row:
                        if "StockValue" in row:
                            cleaned_row["inventory_value"] = float(row["StockValue"])
                        elif "inventory_value" in row:
                            cleaned_row["inventory_value"] = float(row["inventory_value"])
                        else:
                            cleaned_row["inventory_value"] = 0

                    if "material_code" in cleaned_row and cleaned_row["material_code"]:
                        cleaned_data.append(cleaned_row)
                    else:
                        errors.append(f"Row {idx}: 缺少料號")

                except Exception as row_error:
                    errors.append(f"Row {idx}: {str(row_error)}")

            summary = {
                "total_rows": len(query_result),
                "cleaned_rows": len(cleaned_data),
                "errors": len(errors),
                "columns": list(cleaned_data[0].keys()) if cleaned_data else [],
            }

            return ExecutionResult(
                step_id=action.step_id,
                action_type="data_cleaning",
                success=True,
                result={
                    "cleaned_data": cleaned_data,
                    "summary": summary,
                    "errors": errors,
                },
                observation=f"數據清洗完成：{len(cleaned_data)}/{len(query_result)} 行有效",
            )

        except Exception as e:
            logger.error(f"[DataCleaning] 清洗失敗: {e}")
            return ExecutionResult(
                step_id=action.step_id,
                action_type="data_cleaning",
                success=False,
                error=str(e),
                observation=f"數據清洗失敗: {str(e)}",
            )

    async def _execute_computation(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """執行計算"""
        instruction = action.parameters.get("instruction", action.parameters.get("algorithm", ""))

        query_result = None
        for step_id, step_result in previous_results.items():
            if isinstance(step_result, dict) and "data" in step_result:
                query_result = step_result["data"]
                break

        if not query_result:
            return ExecutionResult(
                step_id=action.step_id,
                action_type="computation",
                success=True,
                result={"abc_result": {}},
                observation="無數據，跳過計算",
            )

        try:
            if "abc" in instruction.lower():
                items = []
                for row in query_result:
                    value = (
                        row.get("StockValue")
                        or row.get("inventory_value")
                        or row.get("total_value")
                        or row.get("value", 0)
                    )
                    code = (
                        row.get("ItemCode")
                        or row.get("material")
                        or row.get("material_code")
                        or row.get("mb001")
                        or row.get("img01", "")
                    )
                    if value and code:
                        items.append({"code": code, "value": float(value)})

                if not items:
                    raise Exception("無有效數據")

                items.sort(key=lambda x: x["value"], reverse=True)
                total = sum(item["value"] for item in items)

                a_items, b_items, c_items = [], [], []
                cumulative = 0

                for item in items:
                    cumulative += item["value"]
                    pct = cumulative / total if total > 0 else 0

                    if pct <= 0.70:
                        a_items.append(item["code"])
                    elif pct <= 0.90:
                        b_items.append(item["code"])
                    else:
                        c_items.append(item["code"])

                logger.info(f"[ABC] 分類完成: A={len(a_items)}, B={len(b_items)}, C={len(c_items)}")

                return ExecutionResult(
                    step_id=action.step_id,
                    action_type="computation",
                    success=True,
                    result={
                        "abc_result": {
                            "A類": a_items,
                            "B類": b_items,
                            "C類": c_items,
                        },
                        "instruction": instruction,
                    },
                    observation=f"ABC 分類計算完成：A={len(a_items)} 項，B={len(b_items)} 項，C={len(c_items)} 項",
                )

        except Exception as e:
            logger.error(f"[ABC] 計算失敗: {e}")

        return ExecutionResult(
            step_id=action.step_id,
            action_type="computation",
            success=True,
            result={"abc_result": {}},
            observation="計算完成",
        )

    async def _execute_user_confirmation(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """執行用戶確認"""
        question = action.parameters.get("question", action.description)
        return ExecutionResult(
            step_id=action.step_id,
            action_type="user_confirmation",
            success=True,
            result={"response": f"確認問題：{question}"},
            observation="用戶確認步驟",
        )

    async def _execute_visualization(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """生成可視化"""
        _ = action.parameters.get("instruction", action.description)

        abc_result = None
        for step_id, step_result in previous_results.items():
            if isinstance(step_result, dict) and "abc_result" in step_result:
                abc_result = step_result["abc_result"]
                break

        try:
            visualization = {
                "type": "chart",
                "chart_type": "bar",
                "title": "ABC 分類分布",
                "data": {},
            }

            if abc_result:
                a_items = abc_result.get("A類", [])
                b_items = abc_result.get("B類", [])
                c_items = abc_result.get("C類", [])
                a_value = abc_result.get("A類價值", 0)
                b_value = abc_result.get("B類價值", 0)
                c_value = abc_result.get("C類價值", 0)

                total = a_value + b_value + c_value
                if total > 0:
                    visualization["data"] = {
                        "labels": ["A 類", "B 類", "C 類"],
                        "values": [a_value, b_value, c_value],
                        "percentages": [
                            round(a_value / total * 100, 1),
                            round(b_value / total * 100, 1),
                            round(c_value / total * 100, 1),
                        ],
                        "counts": [len(a_items), len(b_items), len(c_items)],
                    }

            return ExecutionResult(
                step_id=action.step_id,
                action_type="visualization",
                success=True,
                result={
                    "visualization": visualization,
                    "description": "ABC 分類分布圖表",
                },
                observation="可視化生成完成",
            )

        except Exception as e:
            logger.error(f"[Visualization] 生成失敗: {e}")
            return ExecutionResult(
                step_id=action.step_id,
                action_type="visualization",
                success=False,
                error=str(e),
                observation=f"可視化生成失敗: {str(e)}",
            )

    async def _execute_response_generation(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """生成最終報告"""
        knowledge = None
        abc_result = None

        for step_id, step_result in previous_results.items():
            if isinstance(step_result, dict):
                if "knowledge" in step_result:
                    knowledge = step_result["knowledge"]
                if "abc_result" in step_result:
                    abc_result = step_result["abc_result"]

        if abc_result and "A類" in abc_result:
            a_items = abc_result.get("A類", [])
            b_items = abc_result.get("B類", [])
            c_items = abc_result.get("C類", [])

            response = "## ABC 分類結果\n\n"
            response += f"### A 類（累積價值 70%）\n- 共 {len(a_items)} 項\n- 料號：{', '.join(a_items[:10])}\n"
            response += f"\n### B 類（累積價值 70-90%）\n- 共 {len(b_items)} 項\n- 料號：{', '.join(b_items[:10])}\n"
            response += f"\n### C 類（累積價值 90-100%）\n- 共 {len(c_items)} 項\n- 料號：{', '.join(c_items[:10])}\n"

        elif knowledge:
            response = knowledge

        else:
            # 嘗試從 previous_results 中獲取 business_explanation
            business_explanation = None

            # 首先直接檢查是否有 business_explanation（被 _simple_query_plan 保存）
            if "business_explanation" in previous_results:
                business_explanation = previous_results.get("business_explanation")
                logger.info(
                    f"[Debug] Found business_explanation directly: {business_explanation[:100] if business_explanation else 'None'}"
                )

            # 如果沒有，檢查步驟結果
            if not business_explanation:
                for step_id, step_result in previous_results.items():
                    if isinstance(step_result, dict):
                        logger.info(f"[Debug] step_id={step_id}, keys={list(step_result.keys())}")

                        # 檢查 action_type
                        action_type = step_result.get("action_type")
                        if not action_type:
                            # 嘗試從 nested result 獲取
                            action_type = step_result.get("result", {}).get("action_type")

                        logger.info(f"[Debug] action_type={action_type}")

                        if action_type == "data_query":
                            # 獲取 business_explanation
                            business_explanation = step_result.get(
                                "business_explanation"
                            ) or step_result.get("result", {}).get("business_explanation")
                            logger.info(
                                f"[Debug] Found data_query, business_explanation: {business_explanation[:100] if business_explanation else 'None'}"
                            )
                            if business_explanation:
                                break

            if business_explanation:
                response = business_explanation
            else:
                logger.info(f"[Debug] business_explanation is None, using default response")
                response = "處理完成！"

        return ExecutionResult(
            step_id=action.step_id,
            action_type="response_generation",
            success=True,
            result={"response": response, "abc_result": abc_result},
            observation="回覆生成完成",
        )


class SSEPublisher:
    """SSE 發布器 - 推送 AI 狀態到前端（非阻塞）"""

    _instance: Optional["SSEPublisher"] = None

    def __init__(self, api_url: str = "http://localhost:8000"):
        """初始化 SSE 發布器"""
        self._api_url = api_url
        self._enabled = True
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        logger.info(f"[SSEPublisher] Initialized: {api_url}")

    @classmethod
    def get_instance(cls, api_url: str = "http://localhost:8000") -> "SSEPublisher":
        """獲取單例"""
        if cls._instance is None:
            cls._instance = cls(api_url)
        return cls._instance

    async def _worker(self):
        """後台工作線程 - 處理 SSE 發送"""
        while True:
            try:
                data = await self._queue.get()
                await self._send_http(data)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[SSEPublisher] Worker error: {e}")

    async def _send_http(self, data: dict):
        """發送 HTTP 請求"""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{self._api_url}/api/v1/agent-status/event",
                    json=data,
                )
        except Exception as e:
            logger.warning(f"[SSEPublisher] Send failed: {e}", exc_info=True)

    def _ensure_worker(self):
        """確保後台工作線程運行"""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())

    def publish(
        self,
        request_id: str,
        step: str,
        status: str,
        message: str,
        progress: float = 0.0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """發布狀態事件（非阻塞）

        Args:
            request_id: 請求 ID
            step: 當前步驟名稱
            status: 狀態 (processing/completed/error)
            message: 狀態描述
            progress: 進度 0-1
            extra: 額外信息 (action_type, sql, row_count, job_id 等)
        """
        if not self._enabled:
            return

        data = {
            "request_id": request_id,
            "step": step,
            "status": status,
            "message": message,
            "progress": progress,
            "timestamp": datetime.now().isoformat(),
        }
        if extra:
            data["extra"] = extra

        self._queue.put_nowait(data)
        self._ensure_worker()

    def publish_thinking(
        self,
        request_id: str,
        thinking: str,
        progress: float = 0.0,
    ) -> None:
        """發布 LLM 思考過程"""
        self.publish(
            request_id=request_id,
            step="llm_thinking",
            status="processing",
            message=thinking,
            progress=progress,
            extra={"type": "thinking"},
        )

    def publish_step_start(
        self,
        request_id: str,
        step_id: int,
        action_type: str,
        description: str,
        total_steps: int,
    ) -> None:
        """發布步驟開始"""
        progress = (step_id - 1) / total_steps if total_steps > 0 else 0
        self.publish(
            request_id=request_id,
            step=f"step_{step_id}_{action_type}",
            status="processing",
            message=description,
            progress=progress,
            extra={
                "type": "step_start",
                "step_id": step_id,
                "action_type": action_type,
                "total_steps": total_steps,
            },
        )

    def publish_step_complete(
        self,
        request_id: str,
        step_id: int,
        action_type: str,
        result_summary: str,
        row_count: Optional[int] = None,
        sql: Optional[str] = None,
    ) -> None:
        """發布步驟完成"""
        self.publish(
            request_id=request_id,
            step=f"step_{step_id}_{action_type}",
            status="processing",
            message=result_summary,
            progress=1.0,
            extra={
                "type": "step_complete",
                "step_id": step_id,
                "action_type": action_type,
                "row_count": row_count,
                "sql": sql[:200] if sql else None,
            },
        )

    def publish_rq_delivery(
        self,
        request_id: str,
        step_id: int,
        action_type: str,
        job_id: str,
    ) -> None:
        """發布 RQ 任務交付"""
        self.publish(
            request_id=request_id,
            step=f"step_{step_id}_{action_type}",
            status="processing",
            message=f"任務已交付到隊列: {job_id}",
            progress=0.5,
            extra={
                "type": "rq_delivery",
                "step_id": step_id,
                "action_type": action_type,
                "job_id": job_id,
            },
        )

    def publish_data_result(
        self,
        request_id: str,
        step_id: int,
        sql: str,
        row_count: int,
        sample_data: Optional[List[Dict]] = None,
    ) -> None:
        """發布數據查詢結果"""
        self.publish(
            request_id=request_id,
            step=f"step_{step_id}_data_query",
            status="processing",
            message=f"查詢完成，返回 {row_count} 行數據",
            progress=0.8,
            extra={
                "type": "data_result",
                "step_id": step_id,
                "sql": sql[:500],
                "row_count": row_count,
                "sample": sample_data[:3] if sample_data else None,
            },
        )

    def publish_knowledge_result(
        self,
        request_id: str,
        step_id: int,
        source: str,
        knowledge_length: int,
    ) -> None:
        """發布知識檢索結果"""
        self.publish(
            request_id=request_id,
            step=f"step_{step_id}_knowledge_retrieval",
            status="processing",
            message=f"知識獲取成功，來源: {source}，長度: {knowledge_length} 字",
            progress=0.8,
            extra={
                "type": "knowledge_result",
                "step_id": step_id,
                "source": source,
                "knowledge_length": knowledge_length,
            },
        )

    def publish_workflow_plan(
        self,
        request_id: str,
        instruction: str,
        steps: List[Dict],
    ) -> None:
        """發布工作流計劃"""
        step_list = [
            {
                "step_id": s.get("step_id"),
                "action_type": s.get("action_type"),
                "description": s.get("description"),
            }
            for s in steps
        ]
        self.publish(
            request_id=request_id,
            step="workflow_planned",
            status="processing",
            message=f"已分析需求，生成 {len(steps)} 個步驟",
            progress=0.1,
            extra={
                "type": "workflow_plan",
                "instruction": instruction[:100],
                "steps": step_list,
                "total_steps": len(steps),
            },
        )

    def start_tracking(self, request_id: str) -> None:
        """開始追蹤（非阻塞）"""
        self.publish(request_id, "workflow_started", "processing", "工作流程已啟動", 0.0)

    def end_tracking(self, request_id: str) -> None:
        """結束追蹤（非阻塞）"""
        self.publish(request_id, "workflow_completed", "completed", "工作流程已完成", 1.0)


def get_sse_publisher() -> SSEPublisher:
    """獲取 SSE 發布器"""
    return SSEPublisher.get_instance()
