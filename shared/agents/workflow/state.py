# Agent Workflow State Manager - 工作流狀態管理器
# 實現工作流狀態的 ArangoDB 持久化
# 創建日期: 2026-02-08

import logging
from typing import Optional, List, Dict, Any
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
    WorkflowEvent,
    WorkflowEvent,
)

logger = logging.getLogger(__name__)


class WorkflowStateManager:
    """工作流狀態管理器 - 負責 ArangoDB 持久化"""

    def __init__(self):
        """初始化狀態管理器"""
        self._arango = None
        self._initialized = False

    def _get_arango_client(self):
        """獲取 ArangoDB 客戶端"""
        if self._arango is None:
            from shared.database.arango_client import SharedArangoClient

            self._arango = SharedArangoClient.get_instance()
        return self._arango

    async def initialize(self) -> bool:
        """初始化（創建 Collection）"""
        if self._initialized:
            return True

        try:
            db = self._get_arango_client().db
            collection_name = "ai_workflows"

            # 創建 Collection
            if not await db.has_collection(collection_name):
                await db.create_collection(collection_name)
                logger.info(f"Created collection: {collection_name}")

            # 創建索引
            collection = await db.collection(collection_name)

            # session_id 索引（查詢用戶工作流）
            await collection.add_hash_index(fields=["session_id"], unique=False)

            # user_id 索引
            await collection.add_hash_index(fields=["user_id"], unique=False)

            # status 索引（查詢運行中工作流）
            await collection.add_hash_index(fields=["status"], unique=False)

            # created_at 索引（排序）
            await collection.add_ttl_index(fields=["created_at"], expire_at=None)

            # 創建事件 Collection
            events_collection = "ai_workflow_events"
            if not await db.has_collection(events_collection):
                await db.create_collection(events_collection)
                await collection.add_hash_index(fields=["workflow_id"], unique=False)
                await collection.add_ttl_index(fields=["timestamp"], expire_at=None)

            self._initialized = True
            logger.info("[WorkflowStateManager] Initialized successfully")
            return True

        except Exception as e:
            logger.error(f"[WorkflowStateManager] Initialization failed: {e}")
            return False

    async def create(self, workflow: WorkflowState) -> bool:
        """創建工作流"""
        try:
            db = self._get_arango_client().db
            collection = await db.collection("ai_workflows")

            doc = workflow.model_dump()
            await collection.insert(doc)

            # 記錄事件
            await self._log_event(
                workflow_id=workflow.workflow_id,
                event_type="workflow_created",
                details={"task_type": workflow.task_type},
            )

            logger.info(f"[WorkflowStateManager] Created workflow: {workflow.workflow_id}")
            return True

        except Exception as e:
            logger.error(f"[WorkflowStateManager] Create failed: {e}")
            return False

    async def get(self, workflow_id: str) -> Optional[WorkflowState]:
        """獲取工作流"""
        try:
            db = self._get_arango_client().db
            collection = await db.collection("ai_workflows")

            doc = await collection.get(workflow_id)
            if doc:
                return WorkflowState(**doc)
            return None

        except Exception as e:
            logger.error(f"[WorkflowStateManager] Get failed: {e}")
            return None

    async def update(self, workflow: WorkflowState) -> bool:
        """更新工作流"""
        try:
            db = self._get_arango_client().db
            collection = await db.collection("ai_workflows")

            workflow.updated_at = datetime.utcnow()
            doc = workflow.model_dump()

            # 使用 upsert 更新
            await collection.update(workflow_id=doc["workflow_id"], document=doc)

            return True

        except Exception as e:
            logger.error(f"[WorkflowStateManager] Update failed: {e}")
            return False

    async def delete(self, workflow_id: str) -> bool:
        """刪除工作流"""
        try:
            db = self._get_arango_client().db
            collection = await db.collection("ai_workflows")

            await collection.delete(workflow_id)

            logger.info(f"[WorkflowStateManager] Deleted workflow: {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"[WorkflowStateManager] Delete failed: {e}")
            return False

    async def list_by_session(self, session_id: str, limit: int = 20) -> List[WorkflowState]:
        """按會話查詢工作流"""
        try:
            db = self._get_arango_client().db
            collection = await db.collection("ai_workflows")

            # 使用 AQL 查詢
            query = """
            FOR wf IN ai_workflows
                FILTER wf.session_id == @session_id
                SORT wf.created_at DESC
                LIMIT @limit
                RETURN wf
            """

            cursor = await db.aql.execute(
                query, bind_vars={"session_id": session_id, "limit": limit}
            )
            results = await cursor.result()

            return [WorkflowState(**doc) for doc in results]

        except Exception as e:
            logger.error(f"[WorkflowStateManager] List by session failed: {e}")
            return []

    async def list_by_status(self, status: str, limit: int = 100) -> List[WorkflowState]:
        """按狀態查詢工作流（用於監控）"""
        try:
            db = self._get_arango_client().db
            collection = await db.collection("ai_workflows")

            query = """
            FOR wf IN ai_workflows
                FILTER wf.status == @status
                SORT wf.created_at DESC
                LIMIT @limit
                RETURN wf
            """

            cursor = await db.aql.execute(query, bind_vars={"status": status, "limit": limit})
            results = await cursor.result()

            return [WorkflowState(**doc) for doc in results]

        except Exception as e:
            logger.error(f"[WorkflowStateManager] List by status failed: {e}")
            return []

    async def update_heartbeat(self, workflow_id: str) -> bool:
        """更新心跳"""
        try:
            workflow = await self.get(workflow_id)
            if workflow:
                workflow.last_heartbeat = datetime.utcnow()
                return await self.update(workflow)
            return False

        except Exception as e:
            logger.error(f"[WorkflowStateManager] Heartbeat update failed: {e}")
            return False

    async def check_timeout(self, workflow_id: str, timeout: float = 300.0) -> bool:
        """檢查是否超時"""
        try:
            workflow = await self.get(workflow_id)
            if not workflow or not workflow.last_heartbeat:
                return True

            elapsed = (datetime.utcnow() - workflow.last_heartbeat).total_seconds()
            return elapsed > timeout

        except Exception as e:
            logger.error(f"[WorkflowStateManager] Timeout check failed: {e}")
            return False

    async def _log_event(
        self,
        workflow_id: str,
        event_type: str,
        step_id: Optional[int] = None,
        from_status: Optional[str] = None,
        to_status: Optional[str] = None,
        details: Optional[Dict] = None,
        actor: str = "system",
    ) -> bool:
        """記錄事件（審計日誌）"""
        try:
            db = self._get_arango_client().db
            collection = await db.collection("ai_workflow_events")

            event = WorkflowEvent(
                workflow_id=workflow_id,
                event_type=event_type,
                step_id=step_id,
                from_status=from_status,
                to_status=to_status,
                details=details or {},
                actor=actor,
            )

            await collection.insert(event.model_dump())
            return True

        except Exception as e:
            logger.warning(f"[WorkflowStateManager] Event log failed: {e}")
            return False


# 單例實例
_state_manager: Optional[WorkflowStateManager] = None


def get_workflow_state_manager() -> WorkflowStateManager:
    """獲取狀態管理器單例"""
    global _state_manager
    if _state_manager is None:
        _state_manager = WorkflowStateManager()
    return _state_manager
