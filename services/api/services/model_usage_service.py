# 代碼功能說明: 模型使用記錄服務
# 創建日期: 2025-12-06 15:47 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 15:47 (UTC+8)

"""模型使用記錄服務 - 實現模型調用追蹤和統計"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import structlog
import uuid

from database.arangodb import ArangoDBClient
from services.api.models.model_usage import (
    ModelUsage,
    ModelUsageCreate,
    ModelUsageQuery,
    ModelUsageStats,
)

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "model_usage"


class ModelUsageService:
    """模型使用記錄服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化模型使用服務

        Args:
            client: ArangoDB 客戶端（可選，如果不提供則自動創建）
        """
        self.client = client or ArangoDBClient()
        self.logger = logger
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """確保集合存在"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        if not self.client.db.has_collection(COLLECTION_NAME):
            self.client.db.create_collection(COLLECTION_NAME)
            # 創建索引
            collection = self.client.db.collection(COLLECTION_NAME)
            collection.add_index({"type": "persistent", "fields": ["model_name"]})
            collection.add_index({"type": "persistent", "fields": ["user_id"]})
            collection.add_index({"type": "persistent", "fields": ["file_id"]})
            collection.add_index({"type": "persistent", "fields": ["task_id"]})
            collection.add_index({"type": "persistent", "fields": ["purpose"]})
            collection.add_index({"type": "persistent", "fields": ["timestamp"]})
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["model_name", "timestamp"],
                }
            )
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["user_id", "timestamp"],
                }
            )

    def create(self, usage: ModelUsageCreate) -> ModelUsage:
        """
        創建模型使用記錄

        Args:
            usage: 模型使用記錄數據

        Returns:
            創建的模型使用記錄
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        usage_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()

        doc = {
            "_key": usage_id,
            "usage_id": usage_id,
            "model_name": usage.model_name,
            "model_version": usage.model_version,
            "user_id": usage.user_id,
            "file_id": usage.file_id,
            "task_id": usage.task_id,
            "input_length": usage.input_length,
            "output_length": usage.output_length,
            "purpose": usage.purpose.value,
            "cost": usage.cost,
            "latency_ms": usage.latency_ms,
            "success": usage.success,
            "error_message": usage.error_message,
            "metadata": usage.metadata,
            "timestamp": timestamp.isoformat(),
            "created_at": timestamp.isoformat(),
        }

        collection = self.client.db.collection(COLLECTION_NAME)
        collection.insert(doc)

        self.logger.info(
            "模型使用記錄已創建",
            usage_id=usage_id,
            model_name=usage.model_name,
            purpose=usage.purpose.value,
            user_id=usage.user_id,
        )

        return ModelUsage(**doc)

    def query(self, query_params: ModelUsageQuery) -> List[ModelUsage]:
        """
        查詢模型使用記錄

        Args:
            query_params: 查詢參數

        Returns:
            模型使用記錄列表
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 構建AQL查詢
        filters = []
        bind_vars: Dict[str, Any] = {}

        if query_params.model_name:
            filters.append("doc.model_name == @model_name")
            bind_vars["model_name"] = query_params.model_name

        if query_params.user_id:
            filters.append("doc.user_id == @user_id")
            bind_vars["user_id"] = query_params.user_id

        if query_params.file_id:
            filters.append("doc.file_id == @file_id")
            bind_vars["file_id"] = query_params.file_id

        if query_params.task_id:
            filters.append("doc.task_id == @task_id")
            bind_vars["task_id"] = query_params.task_id

        if query_params.purpose:
            filters.append("doc.purpose == @purpose")
            bind_vars["purpose"] = query_params.purpose.value

        if query_params.start_time:
            filters.append("doc.timestamp >= @start_time")
            bind_vars["start_time"] = query_params.start_time.isoformat()

        if query_params.end_time:
            filters.append("doc.timestamp <= @end_time")
            bind_vars["end_time"] = query_params.end_time.isoformat()

        filter_clause = " AND ".join(filters) if filters else "true"

        aql = f"""
        FOR doc IN {COLLECTION_NAME}
        FILTER {filter_clause}
        SORT doc.timestamp DESC
        LIMIT @offset, @limit
        RETURN doc
        """

        bind_vars["offset"] = query_params.offset
        bind_vars["limit"] = query_params.limit

        if self.client.db.aql is None:
            raise RuntimeError("AQL is not available")

        cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
        results = [ModelUsage(**doc) for doc in cursor]

        return results

    def get_stats(
        self,
        model_name: Optional[str] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[ModelUsageStats]:
        """
        獲取模型使用統計

        Args:
            model_name: 模型名稱（可選，如果不提供則統計所有模型）
            user_id: 用戶ID（可選）
            start_time: 開始時間（可選）
            end_time: 結束時間（可選）

        Returns:
            模型使用統計列表
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 構建AQL查詢
        filters = []
        bind_vars: Dict[str, Any] = {}

        if model_name:
            filters.append("doc.model_name == @model_name")
            bind_vars["model_name"] = model_name

        if user_id:
            filters.append("doc.user_id == @user_id")
            bind_vars["user_id"] = user_id

        if start_time:
            filters.append("doc.timestamp >= @start_time")
            bind_vars["start_time"] = start_time.isoformat()

        if end_time:
            filters.append("doc.timestamp <= @end_time")
            bind_vars["end_time"] = end_time.isoformat()

        filter_clause = " AND ".join(filters) if filters else "true"

        aql = f"""
        FOR doc IN {COLLECTION_NAME}
        FILTER {filter_clause}
        COLLECT model = doc.model_name INTO groups
        LET total_calls = LENGTH(groups)
        LET total_users = LENGTH(UNIQUE(groups[*].doc.user_id))
        LET total_input_length = SUM(groups[*].doc.input_length)
        LET total_output_length = SUM(groups[*].doc.output_length)
        LET total_latency_ms = SUM(groups[*].doc.latency_ms)
        LET avg_latency_ms = total_latency_ms / total_calls
        LET success_count = LENGTH(groups[* FILTER CURRENT.doc.success == true])
        LET success_rate = success_count / total_calls
        LET total_cost = SUM(groups[*].doc.cost)
        LET purposes = MERGE(
            FOR group IN groups
            COLLECT purpose = group.doc.purpose WITH COUNT INTO count
            RETURN {{ [purpose]: count }}
        )
        RETURN {{
            model_name: model,
            total_calls: total_calls,
            total_users: total_users,
            total_input_length: total_input_length,
            total_output_length: total_output_length,
            total_latency_ms: total_latency_ms,
            avg_latency_ms: avg_latency_ms,
            success_rate: success_rate,
            total_cost: total_cost,
            purposes: purposes
        }}
        """

        if self.client.db.aql is None:
            raise RuntimeError("AQL is not available")

        cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
        results = [ModelUsageStats(**doc) for doc in cursor]

        return results


# 全局服務實例（懶加載）
_model_usage_service: Optional[ModelUsageService] = None


def get_model_usage_service() -> ModelUsageService:
    """獲取模型使用服務實例（單例模式）"""
    global _model_usage_service
    if _model_usage_service is None:
        _model_usage_service = ModelUsageService()
    return _model_usage_service
