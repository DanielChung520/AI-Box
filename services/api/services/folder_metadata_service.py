# 代碼功能說明: 資料夾元數據服務
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""資料夾元數據服務 - 實現 ArangoDB CRUD"""

from datetime import datetime
from typing import List, Optional

import structlog

from database.arangodb import ArangoDBClient

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "folder_metadata"


class FolderMetadataService:
    """資料夾元數據服務"""

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
        collection = self.client.db.collection(COLLECTION_NAME)
        if not self.client.db.has_collection(COLLECTION_NAME):
            self.client.db.create_collection(COLLECTION_NAME)
            collection.add_index({"type": "persistent", "fields": ["folder_id"]})
            collection.add_index({"type": "persistent", "fields": ["task_id"]})
            collection.add_index({"type": "persistent", "fields": ["user_id"]})
            collection.add_index({"type": "persistent", "fields": ["parent_folder_id"]})
            collection.add_index({"type": "persistent", "fields": ["folder_path"]})

    def create(
        self,
        folder_id: str,
        folder_name: str,
        task_id: str,
        user_id: str,
        parent_folder_id: Optional[str] = None,
        folder_path: Optional[str] = None,
        description: Optional[str] = None,
        custom_metadata: Optional[dict] = None,
    ) -> dict:
        """創建資料夾元數據"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        doc = {
            "_key": folder_id,
            "folder_id": folder_id,
            "folder_name": folder_name,
            "task_id": task_id,
            "user_id": user_id,
            "parent_folder_id": parent_folder_id,
            "folder_path": folder_path,
            "description": description,
            "custom_metadata": custom_metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        collection = self.client.db.collection(COLLECTION_NAME)

        try:
            existing = collection.get(folder_id)
            if existing:
                self.logger.warning(
                    "Folder metadata already exists, skipping creation",
                    folder_id=folder_id,
                    folder_name=folder_name,
                )
                return existing
        except Exception:
            pass

        self.logger.info(
            "Inserting folder metadata document",
            folder_id=folder_id,
            collection=COLLECTION_NAME,
        )
        try:
            result = collection.insert(doc)
            self.logger.info(
                "Folder metadata document inserted successfully",
                folder_id=folder_id,
                result=result,
            )
            return doc
        except Exception as e:
            self.logger.error(
                "Failed to insert folder metadata document",
                folder_id=folder_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def get(self, folder_id: str) -> Optional[dict]:
        """獲取資料夾元數據"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        doc = collection.get(folder_id)

        if doc is None:
            return None

        if not isinstance(doc, dict):
            return None

        return doc

    def update(
        self,
        folder_id: str,
        folder_name: Optional[str] = None,
        parent_folder_id: Optional[str] = None,
        folder_path: Optional[str] = None,
        description: Optional[str] = None,
        custom_metadata: Optional[dict] = None,
    ) -> Optional[dict]:
        """更新資料夾元數據"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        doc = collection.get(folder_id)

        if doc is None:
            return None

        update_data: dict = {
            "updated_at": datetime.utcnow().isoformat(),
            "folder_name": folder_name or doc.get("folder_name"),
            "parent_folder_id": (
                parent_folder_id if parent_folder_id is not None else doc.get("parent_folder_id")
            ),
            "folder_path": folder_path or doc.get("folder_path"),
            "description": description if description is not None else doc.get("description"),
        }

        if custom_metadata is not None:
            update_data["custom_metadata"] = custom_metadata

        doc_to_update = {"_key": folder_id}
        doc_to_update.update(update_data)

        collection.update(doc_to_update)
        updated_doc = collection.get(folder_id)

        if updated_doc is None or not isinstance(updated_doc, dict):
            return None

        return updated_doc

    def delete(self, folder_id: str) -> bool:
        """刪除資料夾元數據"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        try:
            collection.delete(folder_id)
            return True
        except Exception:
            return False

    def list(
        self,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        parent_folder_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """查詢資料夾元數據列表"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        if self.client.db.aql is None:
            raise RuntimeError("ArangoDB AQL is not available")

        filter_conditions = []
        bind_vars: dict = {}

        if task_id:
            filter_conditions.append("doc.task_id == @task_id")
            bind_vars["task_id"] = task_id

        if user_id:
            filter_conditions.append("doc.user_id == @user_id")
            bind_vars["user_id"] = user_id

        if parent_folder_id is not None:
            filter_conditions.append("doc.parent_folder_id == @parent_folder_id")
            bind_vars["parent_folder_id"] = parent_folder_id

        aql = f"FOR doc IN {COLLECTION_NAME}"
        if filter_conditions:
            aql += " FILTER " + " AND ".join(filter_conditions)
        else:
            aql += " FILTER 1 == 1"

        aql += " SORT doc.created_at DESC"

        if offset > 0:
            aql += " LIMIT @offset, @limit"
            bind_vars["offset"] = offset
            bind_vars["limit"] = limit
        else:
            aql += " LIMIT @limit"
            bind_vars["limit"] = limit

        aql += " RETURN doc"

        cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
        results = list(cursor)

        return results

    def delete_by_task_id(self, task_id: str) -> int:
        """刪除指定任務下的所有資料夾

        Args:
            task_id: 任務 ID

        Returns:
            刪除的資料夾數量
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        try:
            collection = self.client.db.collection(COLLECTION_NAME)

            aql_query = """
            FOR folder IN folder_metadata
                FILTER folder.task_id == @task_id
                RETURN folder._key
            """
            cursor = self.client.db.aql.execute(aql_query, bind_vars={"task_id": task_id})
            folder_ids = list(cursor)

            deleted_count = 0
            for folder_id in folder_ids:
                try:
                    collection.delete(folder_id)
                    deleted_count += 1
                    self.logger.info(
                        "Folder deleted successfully", folder_id=folder_id, task_id=task_id
                    )
                except Exception as e:
                    self.logger.warning(
                        "Failed to delete folder",
                        folder_id=folder_id,
                        task_id=task_id,
                        error=str(e),
                    )

            self.logger.info(
                "Task folders deletion completed",
                task_id=task_id,
                folders_deleted=deleted_count,
            )

            return deleted_count

        except Exception as e:
            self.logger.error(
                "Failed to delete task folders",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
            raise


_folder_metadata_service: Optional[FolderMetadataService] = None


def get_folder_metadata_service() -> FolderMetadataService:
    """獲取資料夾元數據服務單例"""
    global _folder_metadata_service
    if _folder_metadata_service is None:
        _folder_metadata_service = FolderMetadataService()
    return _folder_metadata_service
