# 代碼功能說明: 文件元數據服務
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""文件元數據服務 - 實現 ArangoDB CRUD 和全文搜索"""

from datetime import datetime
from typing import List, Optional
import structlog

from databases.arangodb import ArangoDBClient
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

    def _ensure_collection(self):
        """確保集合存在"""
        if not self.client.db.has_collection(COLLECTION_NAME):
            self.client.db.create_collection(COLLECTION_NAME)
            # 創建索引
            collection = self.client.db.collection(COLLECTION_NAME)
            collection.add_index({"type": "persistent", "fields": ["file_id"]})
            collection.add_index({"type": "persistent", "fields": ["filename"]})
            collection.add_index({"type": "persistent", "fields": ["file_type"]})
            collection.add_index({"type": "persistent", "fields": ["upload_time"]})
            collection.add_index({"type": "persistent", "fields": ["user_id"]})

    def create(self, metadata: FileMetadataCreate) -> FileMetadata:
        """創建文件元數據"""
        doc = {
            "_key": metadata.file_id,
            "file_id": metadata.file_id,
            "filename": metadata.filename,
            "file_type": metadata.file_type,
            "file_size": metadata.file_size,
            "user_id": metadata.user_id,
            "tags": metadata.tags,
            "description": metadata.description,
            "custom_metadata": metadata.custom_metadata,
            "upload_time": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        collection = self.client.db.collection(COLLECTION_NAME)
        collection.insert(doc)

        return FileMetadata(**doc)

    def get(self, file_id: str) -> Optional[FileMetadata]:
        """獲取文件元數據"""
        collection = self.client.db.collection(COLLECTION_NAME)
        doc = collection.get(file_id)

        if doc is None:
            return None

        return FileMetadata(**doc)

    def update(
        self, file_id: str, update: FileMetadataUpdate
    ) -> Optional[FileMetadata]:
        """更新文件元數據"""
        collection = self.client.db.collection(COLLECTION_NAME)
        doc = collection.get(file_id)

        if doc is None:
            return None

        update_data = {"updated_at": datetime.utcnow().isoformat()}

        if update.tags is not None:
            update_data["tags"] = update.tags
        if update.description is not None:
            update_data["description"] = update.description
        if update.custom_metadata is not None:
            update_data["custom_metadata"] = update.custom_metadata

        collection.update(file_id, update_data)
        updated_doc = collection.get(file_id)

        return FileMetadata(**updated_doc)

    def delete(self, file_id: str) -> bool:
        """刪除文件元數據"""
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
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "upload_time",
        sort_order: str = "desc",
    ) -> List[FileMetadata]:
        """查詢文件元數據列表"""
        aql = f"""
        FOR doc IN {COLLECTION_NAME}
        FILTER 1 == 1
        """
        bind_vars = {}

        if file_type:
            aql += " AND doc.file_type == @file_type"
            bind_vars["file_type"] = file_type

        if user_id:
            aql += " AND doc.user_id == @user_id"
            bind_vars["user_id"] = user_id

        if tags:
            aql += " AND LENGTH(INTERSECTION(doc.tags, @tags)) > 0"
            bind_vars["tags"] = tags

        aql += f" SORT doc.{sort_by} {sort_order.upper()}"
        aql += " LIMIT @offset, @limit"
        bind_vars["offset"] = offset
        bind_vars["limit"] = limit

        cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
        results = [FileMetadata(**doc) for doc in cursor]

        return results

    def search(self, query: str, limit: int = 100) -> List[FileMetadata]:
        """全文搜索"""
        aql = f"""
        FOR doc IN {COLLECTION_NAME}
        FILTER doc.filename LIKE @query
           OR doc.description LIKE @query
           OR @query IN doc.tags
        LIMIT @limit
        """
        bind_vars = {
            "query": f"%{query}%",
            "limit": limit,
        }

        cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
        results = [FileMetadata(**doc) for doc in cursor]

        return results
