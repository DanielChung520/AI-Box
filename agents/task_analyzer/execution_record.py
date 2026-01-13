# 代碼功能說明: Execution Record 數據模型和存儲服務
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""Execution Record 數據模型和存儲服務

用於記錄任務執行指標，包括 intent、task_count、execution_success、latency_ms 等。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecutionRecord(BaseModel):
    """執行記錄模型"""

    intent: str = Field(..., description="Intent 名稱")
    task_count: int = Field(..., description="任務數量", ge=0)
    execution_success: bool = Field(..., description="執行是否成功")
    user_correction: bool = Field(default=False, description="用戶是否修正")
    latency_ms: int = Field(..., description="延遲時間（毫秒）", ge=0)
    task_results: List[Dict[str, Any]] = Field(default_factory=list, description="任務執行結果列表")
    trace_id: Optional[str] = Field(None, description="追蹤 ID")
    user_id: Optional[str] = Field(None, description="用戶 ID")
    session_id: Optional[str] = Field(None, description="會話 ID")
    agent_ids: List[str] = Field(default_factory=list, description="使用的 Agent ID 列表")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="創建時間")


class ExecutionRecordCreate(BaseModel):
    """執行記錄創建模型"""

    intent: str = Field(..., description="Intent 名稱")
    task_count: int = Field(..., description="任務數量", ge=0)
    execution_success: bool = Field(..., description="執行是否成功")
    user_correction: bool = Field(default=False, description="用戶是否修正")
    latency_ms: int = Field(..., description="延遲時間（毫秒）", ge=0)
    task_results: List[Dict[str, Any]] = Field(default_factory=list, description="任務執行結果列表")
    trace_id: Optional[str] = Field(None, description="追蹤 ID")
    user_id: Optional[str] = Field(None, description="用戶 ID")
    session_id: Optional[str] = Field(None, description="會話 ID")
    agent_ids: List[str] = Field(default_factory=list, description="使用的 Agent ID 列表")


class ExecutionRecordStoreService:
    """執行記錄存儲服務

    使用 ArangoDB 存儲執行記錄。
    """

    COLLECTION_NAME = "execution_records"

    def __init__(self, client: Optional[Any] = None):
        """
        初始化 Execution Record Store Service

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        from database.arangodb import ArangoDBClient

        self._client = client or ArangoDBClient()

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        collection = self._client.get_or_create_collection(self.COLLECTION_NAME)
        self._collection = collection

        # 創建索引
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        try:
            # Intent 索引（用於命中率統計）
            self._collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["intent"],
                    "name": "idx_execution_records_intent",
                }
            )
            # 創建時間索引（用於時間範圍查詢）
            self._collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["created_at"],
                    "name": "idx_execution_records_created_at",
                }
            )
            # 用戶 ID 索引
            self._collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["user_id"],
                    "name": "idx_execution_records_user_id",
                }
            )
            # Trace ID 索引
            self._collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["trace_id"],
                    "name": "idx_execution_records_trace_id",
                }
            )
        except Exception:
            # 索引可能已存在，忽略錯誤
            pass

    def save_record(self, record: ExecutionRecordCreate) -> str:
        """
        保存執行記錄

        Args:
            record: 執行記錄創建模型

        Returns:
            記錄 ID（_key）
        """
        import uuid

        record_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        doc = {
            "_key": record_id,
            "intent": record.intent,
            "task_count": record.task_count,
            "execution_success": record.execution_success,
            "user_correction": record.user_correction,
            "latency_ms": record.latency_ms,
            "task_results": record.task_results,
            "trace_id": record.trace_id,
            "user_id": record.user_id,
            "session_id": record.session_id,
            "agent_ids": record.agent_ids,
            "created_at": now,
        }

        self._collection.insert(doc)
        return record_id

    def get_records_by_intent(self, intent: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        根據 Intent 查詢記錄

        Args:
            intent: Intent 名稱
            limit: 返回記錄數量限制

        Returns:
            記錄列表
        """
        aql = """
        FOR doc IN execution_records
        FILTER doc.intent == @intent
        SORT doc.created_at DESC
        LIMIT @limit
        RETURN doc
        """
        cursor = self._client.db.aql.execute(aql, bind_vars={"intent": intent, "limit": limit})
        return list(cursor)

    def get_records_by_time_range(
        self, start_time: datetime, end_time: datetime, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        根據時間範圍查詢記錄

        Args:
            start_time: 開始時間
            end_time: 結束時間
            limit: 返回記錄數量限制

        Returns:
            記錄列表
        """
        aql = """
        FOR doc IN execution_records
        FILTER doc.created_at >= @start_time AND doc.created_at <= @end_time
        SORT doc.created_at DESC
        LIMIT @limit
        RETURN doc
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")
        cursor = self._client.db.aql.execute(
            aql,
            bind_vars={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "limit": limit,
            },
        )
        result = list(cursor) if cursor else []
        return result

    def get_records_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        根據 Trace ID 查詢記錄

        Args:
            trace_id: 追蹤 ID

        Returns:
            記錄列表
        """
        aql = """
        FOR doc IN execution_records
        FILTER doc.trace_id == @trace_id
        SORT doc.created_at DESC
        RETURN doc
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")
        cursor = self._client.db.aql.execute(aql, bind_vars={"trace_id": trace_id})
        result = list(cursor) if cursor else []
        return result


def get_execution_record_store_service() -> ExecutionRecordStoreService:
    """獲取 Execution Record Store Service 單例"""
    global _execution_record_store_service
    if _execution_record_store_service is None:
        _execution_record_store_service = ExecutionRecordStoreService()
    return _execution_record_store_service


_execution_record_store_service: Optional[ExecutionRecordStoreService] = None
