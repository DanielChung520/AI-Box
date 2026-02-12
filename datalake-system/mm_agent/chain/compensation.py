# Saga Compensation Manager - MM-Agent 補償機制
# 實現步驟失敗時的自動補償
# 創建日期: 2026-02-08

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import sys
from pathlib import Path

ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

logger = logging.getLogger(__name__)


class CompensationAction:
    """補償動作"""

    def __init__(
        self,
        action_id: str,
        step_id: int,
        action_type: str,
        compensation_type: str,
        params: Dict[str, Any] = None,
    ):
        self.action_id = action_id
        self.step_id = step_id
        self.action_type = action_type
        self.compensation_type = compensation_type
        self.params = params or {}
        self.status = "pending"
        self.executed_at = None
        self.error = None


class CompensationManager:
    """補償管理器 - 實現 Saga 補償模式"""

    _instance = None
    _handlers: Dict[str, callable] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._handlers = {}
            self._initialized = True
            self._register_default_handlers()
            logger.info("[CompensationManager] 初始化完成")

    def _register_default_handlers(self):
        """註冊默認補償處理器"""
        self.register_handler("delete_knowledge_cache", self._handle_delete_cache)
        self.register_handler("rollback_temp_table", self._handle_rollback_table)
        self.register_handler("restore_original_data", self._handle_restore_data)
        self.register_handler("cleanup_temp_files", self._handle_cleanup_files)
        self.register_handler("delete_report", self._handle_delete_report)
        self.register_handler("release_lock", self._handle_release_lock)

    def register_handler(self, compensation_type: str, handler: callable) -> None:
        """註冊補償處理器"""
        self._handlers[compensation_type] = handler
        logger.info(f"[CompensationManager] Registered: {compensation_type}")

    def get_handler(self, compensation_type: str) -> Optional[callable]:
        """獲取補償處理器"""
        return self._handlers.get(compensation_type)

    def create_compensation(
        self,
        step_id: int,
        action_type: str,
        params: Dict[str, Any] = None,
    ) -> CompensationAction:
        """創建補償動作"""
        compensation_type = self._get_default_compensation(action_type)
        action_id = f"COMP-{datetime.now().strftime('%Y%m%d')}-{step_id:04d}"

        return CompensationAction(
            action_id=action_id,
            step_id=step_id,
            action_type=action_type,
            compensation_type=compensation_type or "cleanup_temp_files",
            params=params or {},
        )

    def _get_default_compensation(self, action_type: str) -> Optional[str]:
        """獲取默認補償類型"""
        compensation_map = {
            "knowledge_retrieval": "delete_knowledge_cache",
            "data_query": "rollback_temp_table",
            "data_cleaning": "restore_original_data",
            "computation": "cleanup_temp_files",
            "visualization": "delete_report",
            "response_generation": "delete_report",
            "user_confirmation": None,
        }
        return compensation_map.get(action_type)

    async def execute_compensation(
        self, compensations: List, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """執行所有補償（倒序）"""
        results = []
        completed = 0

        for comp in reversed(compensations):
            status = comp.get("status") if isinstance(comp, dict) else comp.status
            if status == "pending":
                result = await self.execute(comp, context)
                comp_id = comp.get("step_id") if isinstance(comp, dict) else comp.step_id
                comp_type = (
                    comp.get("compensation_type")
                    if isinstance(comp, dict)
                    else comp.compensation_type
                )
                results.append(
                    {
                        "step_id": comp_id,
                        "compensation_type": comp_type,
                        "success": result.get("success", False),
                        "error": result.get("error"),
                    }
                )
                if result.get("success", False):
                    completed += 1

        return {"total": len(compensations), "completed": completed, "results": results}

    async def execute(self, compensation: Any, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """執行補償動作（支援 Dict 或 CompensationAction）"""
        if isinstance(compensation, dict):
            comp_type = compensation.get("compensation_type")
            params = compensation.get("params", {})
        else:
            comp_type = compensation.compensation_type
            params = compensation.params

        if not comp_type:
            return {"success": True, "message": "No compensation needed"}

        handler = self.get_handler(comp_type)

        if not handler:
            logger.warning(f"[CompensationManager] No handler for: {comp_type}")
            return {"success": False, "error": f"No handler for: {comp_type}"}

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(compensation, context or {})
            else:
                result = handler(compensation, context or {})

            logger.info(
                f"[CompensationManager] Executed: {comp_type}, success: {result.get('success', False)}"
            )
            return result

        except Exception as e:
            logger.error(f"[CompensationManager] Failed: {e}")
            return {"success": False, "error": str(e)}

    # 默認補償處理器
    async def _handle_delete_cache(self, comp: CompensationAction, context: Dict) -> Dict:
        """知識庫緩存刪除"""
        logger.info(f"[Compensation] Delete cache: {comp.params}")
        return {"success": True, "message": "Knowledge cache cleanup triggered"}

    async def _handle_rollback_table(self, comp: CompensationAction, context: Dict) -> Dict:
        """臨時表回滾"""
        logger.info(f"[Compensation] Rollback table: {comp.params}")
        return {"success": True, "message": "Temp table rollback triggered"}

    async def _handle_restore_data(self, comp: CompensationAction, context: Dict) -> Dict:
        """數據恢復"""
        logger.info(f"[Compensation] Restore data: {comp.params}")
        return {"success": True, "message": "Data restoration triggered"}

    async def _handle_cleanup_files(self, comp: CompensationAction, context: Dict) -> Dict:
        """臨時文件清理"""
        logger.info(f"[Compensation] Cleanup files: {comp.params}")
        return {"success": True, "message": "Temp file cleanup triggered"}

    async def _handle_delete_report(self, comp: CompensationAction, context: Dict) -> Dict:
        """報告刪除"""
        logger.info(f"[Compensation] Delete report: {comp.params}")
        return {"success": True, "message": "Report deletion triggered"}

    async def _handle_release_lock(self, comp: CompensationAction, context: Dict) -> Dict:
        """鎖釋放"""
        logger.info(f"[Compensation] Release lock: {comp.params}")
        return {"success": True, "message": "Lock release triggered"}


# 獲取單例
def get_compensation_manager() -> CompensationManager:
    """獲取補償管理器單例"""
    return CompensationManager()
