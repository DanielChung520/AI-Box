# 代碼功能說明: 文件元數據服務
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""文件元數據服務 - 實現 ArangoDB CRUD 和全文搜索"""

from datetime import datetime
from typing import List, Optional
import structlog

from database.arangodb import ArangoDBClient
from services.api.models.file_metadata import (
    FileMetadata,
    FileMetadataCreate,
    FileMetadataUpdate,
)

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "file_metadata"


class FileMetadataService:
    """文件元數據服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化元數據服務

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
            collection.add_index({"type": "persistent", "fields": ["file_id"]})
            collection.add_index({"type": "persistent", "fields": ["filename"]})
            collection.add_index({"type": "persistent", "fields": ["file_type"]})
            collection.add_index({"type": "persistent", "fields": ["upload_time"]})
            collection.add_index({"type": "persistent", "fields": ["user_id"]})
            collection.add_index({"type": "persistent", "fields": ["task_id"]})
            collection.add_index({"type": "persistent", "fields": ["status"]})

    def create(self, metadata: FileMetadataCreate) -> FileMetadata:
        """創建文件元數據"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        doc = {
            "_key": metadata.file_id,
            "file_id": metadata.file_id,
            "filename": metadata.filename,
            "file_type": metadata.file_type,
            "file_size": metadata.file_size,
            "user_id": metadata.user_id,
            "task_id": metadata.task_id,
            "tags": metadata.tags,
            "description": metadata.description,
            "custom_metadata": metadata.custom_metadata,
            "status": metadata.status or "uploaded",
            "processing_status": metadata.processing_status,
            "chunk_count": metadata.chunk_count,
            "vector_count": metadata.vector_count,
            "kg_status": metadata.kg_status,
            "upload_time": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        collection = self.client.db.collection(COLLECTION_NAME)
        collection.insert(doc)

        return FileMetadata(**doc)

    def get(self, file_id: str) -> Optional[FileMetadata]:
        """獲取文件元數據"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        doc = collection.get(file_id)

        if doc is None:
            return None

        return FileMetadata(**doc)

    def update(
        self, file_id: str, update: FileMetadataUpdate
    ) -> Optional[FileMetadata]:
        """更新文件元數據"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        doc = collection.get(file_id)

        if doc is None:
            return None

        update_data: dict = {"updated_at": datetime.utcnow().isoformat()}

        if update.task_id is not None:
            update_data["task_id"] = update.task_id
        if update.tags is not None:
            update_data["tags"] = update.tags
        if update.description is not None:
            update_data["description"] = update.description
        if update.custom_metadata is not None:
            update_data["custom_metadata"] = update.custom_metadata
        if update.status is not None:
            update_data["status"] = update.status
        if update.processing_status is not None:
            update_data["processing_status"] = update.processing_status
        if update.chunk_count is not None:
            update_data["chunk_count"] = update.chunk_count
        if update.vector_count is not None:
            update_data["vector_count"] = update.vector_count
        if update.kg_status is not None:
            update_data["kg_status"] = update.kg_status

        collection.update(file_id, update_data)
        updated_doc = collection.get(file_id)

        return FileMetadata(**updated_doc) if updated_doc else None

    def delete(self, file_id: str) -> bool:
        """刪除文件元數據"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        try:
            collection.delete(file_id)
            return True
        except Exception:
            return False

    def list(
        self,
        file_type: Optional[str] = None,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "upload_time",
        sort_order: str = "desc",
    ) -> List[FileMetadata]:
        """查詢文件元數據列表"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        if self.client.db.aql is None:
            raise RuntimeError("ArangoDB AQL is not available")

        # 構建 AQL 查詢
        filter_conditions = []
        bind_vars: dict = {}

        if file_type:
            filter_conditions.append("doc.file_type == @file_type")
            bind_vars["file_type"] = file_type

        if user_id:
            filter_conditions.append("doc.user_id == @user_id")
            bind_vars["user_id"] = user_id

        if task_id:
            filter_conditions.append("doc.task_id == @task_id")
            bind_vars["task_id"] = task_id

        if tags:
            filter_conditions.append("LENGTH(INTERSECTION(doc.tags, @tags)) > 0")
            bind_vars["tags"] = tags

        # 構建完整的 AQL 語句
        aql = f"FOR doc IN {COLLECTION_NAME}"
        if filter_conditions:
            aql += " FILTER " + " AND ".join(filter_conditions)
        else:
            aql += " FILTER 1 == 1"

        aql += f" SORT doc.{sort_by} {sort_order.upper()}"
        # ArangoDB LIMIT 語法：LIMIT offset, count 或 LIMIT count
        # 如果 offset 為 0，可以只使用 LIMIT count
        if offset > 0:
            aql += " LIMIT @offset, @limit"
            bind_vars["offset"] = offset
            bind_vars["limit"] = limit
        else:
            aql += " LIMIT @limit"
            bind_vars["limit"] = limit

        # 添加 RETURN 語句（AQL 查詢必須有 RETURN）
        aql += " RETURN doc"

        cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
        results = [FileMetadata(**doc) for doc in cursor]

        return results

    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[FileMetadata]:
        """全文搜索"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        if self.client.db.aql is None:
            raise RuntimeError("ArangoDB AQL is not available")
        aql = f"""
        FOR doc IN {COLLECTION_NAME}
        FILTER (doc.filename LIKE @query
           OR doc.description LIKE @query
           OR @query IN doc.tags)
        """
        bind_vars: dict = {
            "query": f"%{query}%",
            "limit": limit,
        }

        if user_id:
            aql += " AND doc.user_id == @user_id"
            bind_vars["user_id"] = user_id

        if file_type:
            aql += " AND doc.file_type == @file_type"
            bind_vars["file_type"] = file_type

        aql += " LIMIT @limit"

        cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
        results = [FileMetadata(**doc) for doc in cursor]

        return results


# 單例服務實例
_metadata_service: Optional[FileMetadataService] = None


def get_metadata_service() -> FileMetadataService:
    """獲取文件元數據服務單例"""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = FileMetadataService()
    return _metadata_service
