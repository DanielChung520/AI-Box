# 代碼功能說明: 任務工作區服務
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""任務工作區服務 - 管理任務工作區和排程任務目錄的創建和管理"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog

from database.arangodb import ArangoDBClient
from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)

FOLDER_COLLECTION_NAME = "folder_metadata"
WORKSPACE_FOLDER_NAME = "任務工作區"
SCHEDULED_FOLDER_NAME = "排程任務"


# 修改時間：2025-01-27 - 從配置文件讀取存儲路徑
def _get_base_storage_path() -> str:
    """從配置文件獲取基礎存儲路徑"""
    config = get_config_section("file_upload", default={}) or {}
    # 優先使用配置中的 storage_root，否則使用默認值
    storage_root = config.get("storage_root", "./data")
    tasks_path = config.get("tasks_path", f"{storage_root}/tasks")
    return tasks_path


class TaskWorkspaceService:
    """任務工作區服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化任務工作區服務

        Args:
            client: ArangoDB 客戶端（可選，如果不提供則自動創建）
        """
        self.client = client or ArangoDBClient()
        self.logger = logger
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """確保資料夾集合存在"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        if not self.client.db.has_collection(FOLDER_COLLECTION_NAME):
            self.client.db.create_collection(FOLDER_COLLECTION_NAME)
            # 創建索引
            collection = self.client.db.collection(FOLDER_COLLECTION_NAME)
            collection.add_index({"type": "persistent", "fields": ["task_id"]})
            collection.add_index({"type": "persistent", "fields": ["user_id"]})

    def create_workspace(
        self, task_id: str, user_id: str, base_storage_path: Optional[str] = None
    ) -> dict:
        """
        創建任務工作區

        Args:
            task_id: 任務ID
            user_id: 用戶ID
            base_storage_path: 基礎存儲路徑（如果為 None，則從配置文件讀取）

        Returns:
            創建的工作區信息
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 修改時間：2025-01-27 - 從配置文件讀取基礎存儲路徑
        if base_storage_path is None:
            base_storage_path = _get_base_storage_path()

        # 1. 在文件系統中創建目錄
        workspace_path = Path(base_storage_path) / task_id / "workspace"
        workspace_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            "任務工作區目錄創建成功",
            task_id=task_id,
            workspace_path=str(workspace_path),
        )

        # 2. 在 ArangoDB 中創建 folder_metadata 記錄
        collection = self.client.db.collection(FOLDER_COLLECTION_NAME)

        # 檢查是否已存在
        existing_folder = collection.get(f"{task_id}_workspace")
        if existing_folder is None:
            folder_doc = {
                "_key": f"{task_id}_workspace",
                "task_id": task_id,
                "folder_name": WORKSPACE_FOLDER_NAME,
                "user_id": user_id,
                "parent_task_id": None,  # 根目錄
                "folder_type": "workspace",  # 標識為任務工作區
                "storage_path": str(workspace_path),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            collection.insert(folder_doc)
            self.logger.info(
                "任務工作區記錄創建成功",
                task_id=task_id,
                folder_key=f"{task_id}_workspace",
            )
        else:
            self.logger.debug(
                "任務工作區已存在",
                task_id=task_id,
                folder_key=f"{task_id}_workspace",
            )

        return {
            "task_id": task_id,
            "folder_name": WORKSPACE_FOLDER_NAME,
            "folder_type": "workspace",
            "storage_path": str(workspace_path),
            "folder_key": f"{task_id}_workspace",
        }

    def create_scheduled_folder(
        self, task_id: str, user_id: str, base_storage_path: Optional[str] = None
    ) -> dict:
        """
        創建排程任務目錄（為後續功能預留）

        Args:
            task_id: 任務ID
            user_id: 用戶ID
            base_storage_path: 基礎存儲路徑（如果為 None，則從配置文件讀取）

        Returns:
            創建的排程任務目錄信息
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 修改時間：2025-01-27 - 從配置文件讀取基礎存儲路徑
        if base_storage_path is None:
            base_storage_path = _get_base_storage_path()

        # 1. 在文件系統中創建目錄
        scheduled_path = Path(base_storage_path) / task_id / "scheduled"
        scheduled_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            "排程任務目錄創建成功",
            task_id=task_id,
            scheduled_path=str(scheduled_path),
        )

        # 2. 在 ArangoDB 中創建 folder_metadata 記錄
        collection = self.client.db.collection(FOLDER_COLLECTION_NAME)

        # 檢查是否已存在
        existing_folder = collection.get(f"{task_id}_scheduled")
        if existing_folder is None:
            folder_doc = {
                "_key": f"{task_id}_scheduled",
                "task_id": task_id,
                "folder_name": SCHEDULED_FOLDER_NAME,
                "user_id": user_id,
                "parent_task_id": None,  # 根目錄
                "folder_type": "scheduled",  # 標識為排程任務目錄
                "storage_path": str(scheduled_path),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            collection.insert(folder_doc)
            self.logger.info(
                "排程任務目錄記錄創建成功",
                task_id=task_id,
                folder_key=f"{task_id}_scheduled",
            )
        else:
            self.logger.debug(
                "排程任務目錄已存在",
                task_id=task_id,
                folder_key=f"{task_id}_scheduled",
            )

        return {
            "task_id": task_id,
            "folder_name": SCHEDULED_FOLDER_NAME,
            "folder_type": "scheduled",
            "storage_path": str(scheduled_path),
            "folder_key": f"{task_id}_scheduled",
        }

    def ensure_workspace_exists(
        self, task_id: str, user_id: str, base_storage_path: Optional[str] = None
    ) -> dict:
        """
        確保任務工作區存在（如果不存在則創建）

        修改時間：2026-01-28 - 避免重複創建工作區目錄
        只有在資料庫和文件系統中都不存在時才創建

        Args:
            task_id: 任務ID
            user_id: 用戶ID
            base_storage_path: 基礎存儲路徑（如果為 None，則從配置文件讀取）

        Returns:
            工作區信息
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 修改時間：2025-01-27 - 從配置文件讀取基礎存儲路徑
        if base_storage_path is None:
            base_storage_path = _get_base_storage_path()

        collection = self.client.db.collection(FOLDER_COLLECTION_NAME)
        folder_key = f"{task_id}_workspace"
        existing_folder = collection.get(folder_key)

        workspace_path = Path(base_storage_path) / task_id / "workspace"

        if existing_folder is None:
            # 資料庫中無記錄，創建新的工作區
            return self.create_workspace(task_id, user_id, base_storage_path)
        else:
            # 資料庫中已有記錄
            if workspace_path.exists():
                # 文件系統目錄也存在，直接返回
                self.logger.debug(
                    "workspace_exists",
                    task_id=task_id,
                    user_id=user_id,
                    note="Workspace exists in both database and filesystem",
                )
                return {
                    "task_id": task_id,
                    "folder_name": existing_folder.get("folder_name", WORKSPACE_FOLDER_NAME),
                    "folder_type": "workspace",
                    "storage_path": str(workspace_path),
                    "folder_key": folder_key,
                }
            else:
                # 資料庫有記錄但文件系統目錄不存在，記錄警告但不自動創建
                self.logger.warning(
                    "workspace_missing_in_filesystem",
                    task_id=task_id,
                    user_id=user_id,
                    folder_key=folder_key,
                    note="Workspace exists in database but not in filesystem (not auto-created to avoid bulk creation)",
                )
                return {
                    "task_id": task_id,
                    "folder_name": existing_folder.get("folder_name", WORKSPACE_FOLDER_NAME),
                    "folder_type": "workspace",
                    "storage_path": str(workspace_path),
                    "folder_key": folder_key,
                    "exists": False,
                    "note": "Database record exists but filesystem directory does not",
                }

    def get_workspace_path(self, task_id: str, base_storage_path: Optional[str] = None) -> Path:
        """
        獲取任務工作區的文件系統路徑

        Args:
            task_id: 任務ID
            base_storage_path: 基礎存儲路徑（如果為 None，則從配置文件讀取）

        Returns:
            工作區路徑
        """
        # 修改時間：2025-01-27 - 從配置文件讀取基礎存儲路徑
        if base_storage_path is None:
            base_storage_path = _get_base_storage_path()
        return Path(base_storage_path) / task_id / "workspace"

    def delete_workspace(self, task_id: str, base_storage_path: Optional[str] = None) -> bool:
        """
        刪除任務工作區（包括文件系統目錄和數據庫記錄）

        Args:
            task_id: 任務ID
            base_storage_path: 基礎存儲路徑（如果為 None，則從配置文件讀取）

        Returns:
            是否成功刪除
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 修改時間：2025-01-27 - 從配置文件讀取基礎存儲路徑
        if base_storage_path is None:
            base_storage_path = _get_base_storage_path()

        try:
            # 1. 刪除數據庫記錄
            collection = self.client.db.collection(FOLDER_COLLECTION_NAME)
            workspace_key = f"{task_id}_workspace"
            scheduled_key = f"{task_id}_scheduled"

            if collection.has(workspace_key):
                collection.delete(workspace_key)
                self.logger.info("任務工作區記錄已刪除", task_id=task_id)

            if collection.has(scheduled_key):
                collection.delete(scheduled_key)
                self.logger.info("排程任務目錄記錄已刪除", task_id=task_id)

            # 2. 刪除文件系統目錄
            task_path = Path(base_storage_path) / task_id
            if task_path.exists():
                import shutil

                shutil.rmtree(task_path)
                self.logger.info("任務目錄已刪除", task_id=task_id, path=str(task_path))

            return True
        except Exception as e:
            self.logger.error("刪除任務工作區失敗", task_id=task_id, error=str(e), exc_info=True)
            return False


# 單例模式
_task_workspace_service: Optional[TaskWorkspaceService] = None


def get_task_workspace_service() -> TaskWorkspaceService:
    """獲取任務工作區服務單例"""
    global _task_workspace_service
    if _task_workspace_service is None:
        _task_workspace_service = TaskWorkspaceService()
    return _task_workspace_service
