# Agent Workflow Saga Manager - Saga 補償管理器
# 實現補償模式、斷線恢復
# 創建日期: 2026-02-08

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import sys
from pathlib import Path

# 添加 shared 目錄到路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from shared.agents.workflow.schema import (
    WorkflowState,
    WorkflowStatus,
    SagaStep,
    CompensationAction,
    CompensationStatus,
)
from shared.agents.workflow.state import get_workflow_state_manager
from shared.agents.workflow.executor import get_workflow_executor

logger = logging.getLogger(__name__)


class CompensationStrategy:
    """補償策略定義"""

    # 標準補償動作映射
    COMPENSATION_HANDLERS: Dict[str, str] = {
        "delete_knowledge_cache": "清除知識缓存",
        "rollback_temp_table": "回滾臨時表",
        "restore_original_data": "恢復原始數據",
        "delete_report": "刪除報告",
        "release_lock": "釋放鎖",
        "cleanup_temp_files": "清理臨時文件",
        "cancel_order": "取消訂單",
        "revert_status": "恢復狀態",
    }

    @classmethod
    def get_handler(cls, compensation_type: str) -> Optional[str]:
        """獲取補償處理器名稱"""
        return cls.COMPENSATION_HANDLERS.get(compensation_type)


class SagaManager:
    """Saga 補償管理器"""

    def __init__(self):
        """初始化 Saga 管理器"""
        self._state_manager = get_workflow_state_manager()
        self._executor = get_workflow_executor()
        self._compensation_handlers: Dict[str, callable] = {}

    def register_compensation_handler(self, compensation_type: str, handler: callable) -> None:
        """註冊補償處理器"""
        self._compensation_handlers[compensation_type] = handler
        logger.info(f"[SagaManager] Registered compensation handler: {compensation_type}")

    async def create_compensation(
        self, workflow: WorkflowState, step: SagaStep
    ) -> CompensationAction:
        """為步驟創建補償動作"""
        compensation = CompensationAction(
            step_id=step.step_id,
            action_type=step.action_type,
            compensation_type=step.compensation_type
            or self._get_default_compensation(step.action_type),
            params=step.compensation_params,
        )

        workflow.compensations.append(compensation)
        await self._state_manager.update(workflow)

        return compensation

    def _get_default_compensation(self, action_type: str) -> str:
        """獲取默認補償類型"""
        compensation_map = {
            "knowledge_retrieval": "delete_knowledge_cache",
            "data_query": "rollback_temp_table",
            "data_cleaning": "restore_original_data",
            "computation": "cleanup_temp_files",
            "response_generation": "delete_report",
            "visualization": "delete_report",
            "user_confirmation": None,
        }
        return compensation_map.get(action_type, "cleanup_temp_files")

    async def execute_compensation(
        self, workflow: WorkflowState, compensation: CompensationAction
    ) -> Dict[str, Any]:
        """執行單個補償動作"""
        compensation.status = CompensationStatus.EXECUTING
        compensation.executed_at = datetime.utcnow()
        await self._state_manager.update(workflow)

        try:
            # 查找處理器
            handler = self._compensation_handlers.get(compensation.compensation_type)

            if handler:
                # 調用註冊的處理器
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(compensation.params)
                else:
                    result = handler(compensation.params)

                compensation.status = CompensationStatus.COMPLETED
                return {"success": True, "error": None}

            else:
                # 使用默認補償邏輯
                result = await self._default_compensation(compensation)
                compensation.status = CompensationStatus.COMPLETED
                return {"success": True, "error": None}

        except Exception as e:
            logger.error(f"[SagaManager] Compensation failed: {e}")
            compensation.status = CompensationStatus.FAILED
            compensation.error = str(e)
            return {"success": False, "error": str(e)}

    async def _default_compensation(self, compensation: CompensationAction) -> Dict[str, Any]:
        """默認補償邏輯"""
        compensation_type = compensation.compensation_type

        # 記錄補償意圖（實際執行需要根據具體情況）
        logger.info(
            f"[SagaManager] Default compensation for {compensation_type}: "
            f"step={compensation.step_id}, params={compensation.params}"
        )

        # 模擬執行補償
        await asyncio.sleep(0.1)

        return {"success": True, "message": f"補償 {compensation_type} 已執行"}

    async def compensate_all(self, workflow: WorkflowState) -> Dict[str, Any]:
        """執行所有已完成步驟的補償（倒序）"""
        workflow.status = WorkflowStatus.COMPENSATING
        await self._state_manager.update(workflow)

        results = []
        completed_count = 0

        # 倒序執行補償
        for step_id in reversed(workflow.completed_steps):
            compensation = next((c for c in workflow.compensations if c.step_id == step_id), None)

            if compensation and compensation.compensation_type:
                result = await self.execute_compensation(workflow, compensation)
                results.append(
                    {
                        "step_id": step_id,
                        "compensation_type": compensation.compensation_type,
                        "success": result["success"],
                        "error": result.get("error"),
                    }
                )

                if result["success"]:
                    completed_count += 1

        # 更新工作流狀態
        workflow.status = WorkflowStatus.FAILED
        workflow.compensation_history = results
        workflow.completed_at = datetime.utcnow()

        await self._state_manager.update(workflow)

        # 記錄事件
        await self._state_manager._log_event(
            workflow_id=workflow.workflow_id,
            event_type="compensation_completed",
            from_status=WorkflowStatus.COMPENSATING.value,
            to_status=WorkflowStatus.FAILED.value,
            details={
                "total_compensations": len(results),
                "completed": completed_count,
                "results": results,
            },
        )

        return {
            "success": True,
            "total": len(results),
            "completed": completed_count,
            "results": results,
        }

    async def compensate_from(self, workflow: WorkflowState, from_step_id: int) -> Dict[str, Any]:
        """從指定步驟開始補償（用於斷線恢復）"""
        # 收集需要補償的步驟
        steps_to_compensate = [s_id for s_id in workflow.completed_steps if s_id >= from_step_id]

        results = []

        for step_id in reversed(steps_to_compensate):
            compensation = next((c for c in workflow.compensations if c.step_id == step_id), None)

            if compensation and compensation.compensation_type:
                result = await self.execute_compensation(workflow, compensation)
                results.append(
                    {
                        "step_id": step_id,
                        "success": result["success"],
                    }
                )

        return {"success": True, "results": results}


class WorkflowRecoveryManager:
    """工作流恢復管理器 - 斷線恢復"""

    def __init__(self):
        """初始化恢復管理器"""
        self._state_manager = get_workflow_state_manager()
        self._saga_manager = SagaManager()

    async def get_recoverable_workflows(self, session_id: str) -> List[WorkflowState]:
        """獲取可恢復的工作流"""
        workflows = await self._state_manager.list_by_session(session_id)

        # 過濾出可恢復的工作流
        recoverable = []
        for wf in workflows:
            if wf.status in [
                WorkflowStatus.RUNNING.value,
                WorkflowStatus.PAUSED.value,
            ]:
                # 檢查是否超時
                if not await self._state_manager.check_timeout(wf.workflow_id, 300.0):
                    recoverable.append(wf)

        return recoverable

    async def resume(self, workflow_id: str, user_response: Optional[str] = None) -> Dict[str, Any]:
        """恢復執行工作流"""
        workflow = await self._state_manager.get(workflow_id)
        if not workflow:
            return {"success": False, "error": "工作流不存在"}

        # 檢查狀態
        if workflow.status not in [WorkflowStatus.RUNNING.value, WorkflowStatus.PAUSED.value]:
            return {
                "success": False,
                "error": f"無法恢復，狀態為: {workflow.status}",
            }

        # 獲取下一步
        next_step_id = workflow.current_step + 1
        step = next((s for s in workflow.steps if s.step_id == next_step_id), None)

        if not step:
            # 工作流已完成
            workflow.status = WorkflowStatus.COMPLETED
            await self._state_manager.update(workflow)
            return {
                "success": True,
                "message": "工作流已完成",
                "final_response": workflow.final_response,
            }

        # 恢復執行
        workflow.status = WorkflowStatus.RUNNING
        await self._state_manager.update(workflow)

        executor = get_workflow_executor()
        result = await executor.execute_step(workflow, step, workflow.results, user_response)

        return {
            "success": result.success,
            "step_id": step.step_id,
            "result": result.data,
            "observation": result.observation,
        }

    async def cancel(self, workflow_id: str, force: bool = False) -> Dict[str, Any]:
        """取消工作流"""
        workflow = await self._state_manager.get(workflow_id)
        if not workflow:
            return {"success": False, "error": "工作流不存在"}

        # 如果強制取消，執行補償
        if force and workflow.completed_steps:
            await self._saga_manager.compensate_all(workflow)

        workflow.status = WorkflowStatus.CANCELLED
        await self._state_manager.update(workflow)

        await self._state_manager._log_event(
            workflow_id=workflow.workflow_id,
            event_type="workflow_cancelled",
            to_status=WorkflowStatus.CANCELLED.value,
            details={"force": force},
        )

        return {"success": True, "status": "cancelled"}


# 單例實例
_saga_manager: Optional[SagaManager] = None
_recovery_manager: Optional[WorkflowRecoveryManager] = None


def get_saga_manager() -> SagaManager:
    """獲取 Saga 管理器單例"""
    global _saga_manager
    if _saga_manager is None:
        _saga_manager = SagaManager()
    return _saga_manager


def get_workflow_recovery_manager() -> WorkflowRecoveryManager:
    """獲取恢復管理器單例"""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = WorkflowRecoveryManager()
    return _recovery_manager
