# 代碼功能說明: 文件樹同步服務，提供構建、驗證與同步功能
# 創建日期: 2025-12-09 15:54:48 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-09 15:54:48 UTC+8

"""文件樹同步服務 - 確保前端文件樹與 ArangoDB 及檔案系統一致"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import structlog

from database.arangodb import ArangoDBClient
from services.api.services.task_workspace_service import FOLDER_COLLECTION_NAME
from storage.file_storage import FileStorage, create_storage_from_config
from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)


class FileTreeSyncService:
    """文件樹同步服務"""

    def __init__(
        self,
        client: Optional[ArangoDBClient] = None,
        storage: Optional[FileStorage] = None,
    ) -> None:
        """
        初始化文件樹同步服務

        Args:
            client: ArangoDB 客戶端
            storage: 文件存儲實例
        """
        self.client = client or ArangoDBClient()
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        self.storage = storage or self._create_storage()
        self._ensure_collections()

    def _create_storage(self) -> FileStorage:
        """從配置建立文件存儲實例"""
        config = get_config_section("file_upload", default={}) or {}
        return create_storage_from_config(config)

    def _ensure_collections(self) -> None:
        """確保所需集合存在"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        if not self.client.db.has_collection(FOLDER_COLLECTION_NAME):
            self.client.db.create_collection(FOLDER_COLLECTION_NAME)

        if not self.client.db.has_collection("file_metadata"):
            self.client.db.create_collection("file_metadata")

        if not self.client.db.has_collection("user_tasks"):
            self.client.db.create_collection("user_tasks")

    def _fetch_files_and_folders(
        self, user_id: str, task_id: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """取得指定任務的文件與資料夾元數據"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        file_metadata_collection = self.client.db.collection("file_metadata")
        folder_collection = self.client.db.collection(FOLDER_COLLECTION_NAME)

        files = list(
            file_metadata_collection.find({"user_id": user_id, "task_id": task_id})
        )
        folders = list(
            folder_collection.find({"user_id": user_id, "task_id": task_id})
        )
        return files, folders

    def build_file_tree(
        self, user_id: str, task_id: str
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Dict[str, Any]]]:
        """
        從元數據構建文件樹

        Returns:
            (tree, folders_info)
        """
        files, folders = self._fetch_files_and_folders(user_id, task_id)

        tree: Dict[str, List[Dict[str, Any]]] = {}
        folders_info: Dict[str, Dict[str, Any]] = {}

        # 初始化任務工作區節點
        workspace_key = f"{task_id}_workspace"
        tree[workspace_key] = []

        for folder_doc in folders:
            folder_key = folder_doc.get("_key")
            if not folder_key:
                continue

            folders_info[folder_key] = {
                "folder_name": folder_doc.get("folder_name", folder_key),
                "parent_task_id": folder_doc.get("parent_task_id"),
                "user_id": folder_doc.get("user_id"),
                "folder_type": folder_doc.get("folder_type"),
                "task_id": folder_doc.get("task_id"),
            }

            if folder_doc.get("task_id") == task_id:
                if folder_key not in tree:
                    tree[folder_key] = []

        for file_doc in files:
            file_task_id = file_doc.get("task_id")
            if file_task_id != task_id:
                continue

            tree[workspace_key].append(
                {
                    "id": file_doc.get("_key") or file_doc.get("file_id"),
                    "name": file_doc.get("filename"),
                    "type": "file",
                    "task_id": file_task_id,
                    "user_id": file_doc.get("user_id"),
                    "storage_path": file_doc.get("storage_path"),
                    "file_type": file_doc.get("file_type"),
                }
            )

        return tree, folders_info

    def validate_file_tree(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """驗證文件樹與檔案系統一致性"""
        files, _ = self._fetch_files_and_folders(user_id, task_id)

        missing_files: List[Dict[str, Any]] = []
        for file_doc in files:
            file_id = file_doc.get("_key") or file_doc.get("file_id") or ""
            filename = file_doc.get("filename")
            storage_path = file_doc.get("storage_path")
            resolved_path = self.storage.get_file_path(
                file_id=file_id,
                task_id=task_id,
                metadata_storage_path=storage_path,
            )

            if not resolved_path:
                missing_files.append(
                    {
                        "file_id": file_id,
                        "filename": filename,
                        "reason": "path_not_found",
                    }
                )
                continue

            # 再次確認檔案是否存在
            tree_path_exists = self.storage.file_exists(
                file_id, task_id=task_id, metadata_storage_path=storage_path
            )
            if not tree_path_exists:
                missing_files.append(
                    {
                        "file_id": file_id,
                        "filename": filename,
                        "resolved_path": resolved_path,
                        "reason": "file_missing_on_disk",
                    }
                )

        issues_found = len(missing_files) > 0
        return {
            "task_id": task_id,
            "user_id": user_id,
            "issues_found": issues_found,
            "missing_files": missing_files,
            "checked_at": datetime.utcnow().isoformat(),
        }

    def sync_file_tree(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """
        構建並同步文件樹到 user_tasks 集合

        Returns:
            同步結果（包含版本與哈希）
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        tree, folders_info = self.build_file_tree(user_id, task_id)

        serialized_tree = json.dumps(tree, sort_keys=True, ensure_ascii=False)
        tree_hash = hashlib.sha256(serialized_tree.encode("utf-8")).hexdigest()

        user_task_collection = self.client.db.collection("user_tasks")
        task_doc_key = f"{user_id}_{task_id}"
        task_doc = user_task_collection.get(task_doc_key)

        version = 1
        if task_doc and isinstance(task_doc.get("fileTreeVersion"), int):
            version = task_doc["fileTreeVersion"] + 1

        # 修改時間：2025-12-09 - 構建完整的 fileTree 結構（包含資料夾和文件）
        # 使用 user_task_service 的 _build_file_tree_for_task 方法構建完整的文件樹
        from services.api.services.user_task_service import get_user_task_service
        user_task_service = get_user_task_service()
        complete_file_tree = user_task_service._build_file_tree_for_task(user_id, task_id)
        
        # 重新計算哈希值（基於完整的文件樹）
        serialized_complete_tree = json.dumps(complete_file_tree, sort_keys=True, ensure_ascii=False)
        complete_tree_hash = hashlib.sha256(serialized_complete_tree.encode("utf-8")).hexdigest()
        
        updated_doc = task_doc or {}
        updated_doc.update(
            {
                "_key": task_doc_key,
                "task_id": task_id,
                "user_id": user_id,
                "fileTree": complete_file_tree,  # 使用完整的文件樹結構（包含資料夾）
                "fileTreeVersion": version,
                "fileTreeUpdatedAt": datetime.utcnow().isoformat(),
                "fileTreeHash": complete_tree_hash,  # 使用完整文件樹的哈希值
            }
        )

        persisted = True
        if task_doc is None:
            persisted = False
            logger.warning(
                "User task not found when syncing file tree, skip persistence",
                task_id=task_id,
                user_id=user_id,
            )
        else:
            user_task_collection.update(updated_doc)

        return {
            "task_id": task_id,
            "user_id": user_id,
            "fileTreeVersion": version,
            "fileTreeHash": complete_tree_hash,  # 使用完整文件樹的哈希值
            "fileTree": complete_file_tree,  # 返回完整的文件樹
            "folders": folders_info,
            "tree": tree,  # 保留舊格式的 tree（用於兼容）
            "persisted": persisted,
        }

    def get_file_tree_version(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """取得文件樹版本資訊"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        task_doc_key = f"{user_id}_{task_id}"
        task_doc = self.client.db.collection("user_tasks").get(task_doc_key)
        return {
            "task_id": task_id,
            "user_id": user_id,
            "fileTreeVersion": task_doc.get("fileTreeVersion", 0) if task_doc else 0,
            "fileTreeUpdatedAt": task_doc.get("fileTreeUpdatedAt") if task_doc else None,
            "fileTreeHash": task_doc.get("fileTreeHash") if task_doc else None,
        }


_file_tree_sync_service: Optional[FileTreeSyncService] = None


def get_file_tree_sync_service() -> FileTreeSyncService:
    """取得文件樹同步服務單例"""
    global _file_tree_sync_service
    if _file_tree_sync_service is None:
        _file_tree_sync_service = FileTreeSyncService()
    return _file_tree_sync_service
