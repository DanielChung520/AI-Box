# 代碼功能說明: 操作日誌記錄服務
# 創建日期: 2025-12-08 14:20:00 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-08 14:20:00 UTC+8

"""操作日誌記錄服務 - 記錄所有任務和文件操作的詳細信息"""

from datetime import datetime
from typing import Optional
import structlog
from database.arangodb import ArangoDBClient

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "operation_logs"


class OperationLogService:
    """操作日誌記錄服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化操作日誌記錄服務

        Args:
            client: ArangoDB 客戶端（可選，如果不提供則使用默認客戶端）
        """
        self.client = client or ArangoDBClient()
        self._collection_ensured = False  # 延遲初始化標記

    def _ensure_collection(self) -> None:
        """確保操作日誌集合存在"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        if not self.client.db.has_collection(COLLECTION_NAME):
            self.client.db.create_collection(COLLECTION_NAME)
            logger.info(f"Created collection: {COLLECTION_NAME}")

    def log_operation(
        self,
        user_id: str,
        resource_id: str,
        resource_type: str,  # "task" 或 "document"
        resource_name: str,
        operation_type: str,  # "create", "update", "archive", "delete"
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        archived_at: Optional[str] = None,
        deleted_at: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """
        記錄操作日誌

        Args:
            user_id: 用戶 ID 或 token ID
            resource_id: 資源 ID（任務 ID 或文件 ID）
            resource_type: 資源類型（"task" 或 "document"）
            resource_name: 資源名稱（任務標題或文件名）
            operation_type: 操作類型（"create", "update", "archive", "delete"）
            created_at: 創建日期時間（ISO 8601 格式，UTC）
            updated_at: 最近更新時間（ISO 8601 格式，UTC）
            archived_at: 歸檔時間（ISO 8601 格式，UTC）
            deleted_at: 刪除時間（ISO 8601 格式，UTC）
            notes: 備註

        Returns:
            是否成功記錄
        """
        try:
            # 修改時間：2025-12-08 14:30:00 UTC+8 - 延遲初始化集合，避免阻塞
            if not self._collection_ensured:
                try:
                    self._ensure_collection()
                    self._collection_ensured = True
                except Exception as e:
                    logger.warning("無法初始化操作日誌集合，跳過日誌記錄", error=str(e))
                    return False

            if self.client.db is None:
                raise RuntimeError("ArangoDB client is not connected")

            collection = self.client.db.collection(COLLECTION_NAME)

            # 生成文檔鍵（使用時間戳確保唯一性）
            doc_key = f"{user_id}_{resource_id}_{operation_type}_{int(datetime.utcnow().timestamp() * 1000)}"

            # 構建操作日誌文檔
            log_doc = {
                "_key": doc_key,
                "user_id": user_id,
                "resource_id": resource_id,
                "resource_type": resource_type,
                "resource_name": resource_name,
                "operation_type": operation_type,
                "created_at": created_at,
                "updated_at": updated_at,
                "archived_at": archived_at,
                "deleted_at": deleted_at,
                "notes": notes,
                "log_timestamp": datetime.utcnow().isoformat()
                + "Z",  # 記錄日誌的時間戳
            }

            # 插入日誌文檔
            collection.insert(log_doc)
            logger.info(
                "操作日誌記錄成功",
                user_id=user_id,
                resource_id=resource_id,
                resource_type=resource_type,
                operation_type=operation_type,
            )
            return True

        except Exception as e:
            logger.error(
                "記錄操作日誌失敗",
                user_id=user_id,
                resource_id=resource_id,
                resource_type=resource_type,
                operation_type=operation_type,
                error=str(e),
                exc_info=True,
            )
            return False


# 單例模式
_operation_log_service: Optional[OperationLogService] = None


def get_operation_log_service() -> OperationLogService:
    """獲取操作日誌記錄服務實例（單例模式）"""
    global _operation_log_service
    if _operation_log_service is None:
        _operation_log_service = OperationLogService()
    return _operation_log_service
