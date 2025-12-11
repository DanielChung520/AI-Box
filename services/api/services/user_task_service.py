# 代碼功能說明: 用戶任務服務
# 創建日期: 2025-12-08 09:04:21 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-08 09:14:28 UTC+8

"""用戶任務服務 - 實現 ArangoDB CRUD 操作"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import structlog

from database.arangodb import ArangoDBClient
from services.api.models.user_task import (
    UserTask,
    UserTaskCreate,
    UserTaskUpdate,
)
from services.api.services.task_workspace_service import get_task_workspace_service

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "user_tasks"


class UserTaskService:
    """用戶任務服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化用戶任務服務

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
            collection.add_index({"type": "persistent", "fields": ["task_id"]})
            collection.add_index({"type": "persistent", "fields": ["user_id"]})
            collection.add_index({"type": "persistent", "fields": ["status"]})
            collection.add_index({"type": "persistent", "fields": ["created_at"]})
            collection.add_index(
                {"type": "persistent", "fields": ["user_id", "created_at"]}
            )

    def create(self, task: UserTaskCreate) -> UserTask:
        """創建用戶任務"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 使用 user_id 和 task_id 組合作為 _key，確保唯一性
        doc_key = f"{task.user_id}_{task.task_id}"

        doc = {
            "_key": doc_key,
            "task_id": task.task_id,
            "user_id": task.user_id,
            "title": task.title,
            "status": task.status or "pending",
            # 修改時間：2025-12-09 - 設置 task_status 默認值為 activate
            "task_status": task.task_status or "activate",
            # 修改時間：2025-12-09 - 保存 label_color
            "label_color": task.label_color,
            "dueDate": task.dueDate,
            "messages": [
                msg.model_dump() if hasattr(msg, "model_dump") else msg
                for msg in (task.messages or [])
            ],
            # 修改時間：2025-01-27 - 確保 executionConfig 包含 mode 字段
            "executionConfig": task.executionConfig.model_dump()
            if task.executionConfig and hasattr(task.executionConfig, "model_dump")
            else (task.executionConfig or {"mode": "free"}),
            "fileTree": [
                node.model_dump() if hasattr(node, "model_dump") else node
                for node in (task.fileTree or [])
            ],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        collection = self.client.db.collection(COLLECTION_NAME)
        collection.insert(doc)

        # 修改時間：2025-01-27 - 創建任務時自動創建任務工作區和排程任務目錄
        try:
            workspace_service = get_task_workspace_service()
            # 創建任務工作區
            workspace_service.create_workspace(
                task_id=task.task_id,
                user_id=task.user_id,
            )
            # 創建排程任務目錄（為後續功能預留）
            workspace_service.create_scheduled_folder(
                task_id=task.task_id,
                user_id=task.user_id,
            )
            self.logger.info(
                "任務工作區和排程任務目錄創建成功",
                task_id=task.task_id,
                user_id=task.user_id,
            )
        except Exception as e:
            self.logger.error(
                "創建任務工作區失敗",
                task_id=task.task_id,
                user_id=task.user_id,
                error=str(e),
                exc_info=True,
            )
            # 工作區創建失敗不影響任務創建，但記錄錯誤

        return UserTask(**doc)

    def get(self, user_id: str, task_id: str) -> Optional[UserTask]:
        """獲取用戶任務"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        doc_key = f"{user_id}_{task_id}"
        doc = collection.get(doc_key)

        if doc is None:
            return None

        # 修改時間：2025-01-27 - 獲取任務時也動態構建 fileTree
        task_id = doc.get('task_id')
        user_id = doc.get('user_id')
        if task_id and user_id:
            try:
                fileTree = self._build_file_tree_for_task(user_id, task_id)
                if fileTree:
                    doc['fileTree'] = fileTree
            except Exception as e:
                self.logger.warning(
                    "Failed to build fileTree for task",
                    task_id=task_id,
                    error=str(e),
                )
        
        return UserTask(**doc)

    def list(self, user_id: str, limit: int = 100, offset: int = 0) -> List[UserTask]:
        """列出用戶的所有任務
        
        修改時間：2025-01-27 - 從 file_metadata 和 folder_metadata 動態構建 fileTree
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        aql_query = """
        FOR task IN user_tasks
            FILTER task.user_id == @user_id
            SORT task.created_at DESC
            LIMIT @offset, @limit
            RETURN task
        """

        cursor = self.client.db.aql.execute(
            aql_query,
            bind_vars={
                "user_id": user_id,
                "offset": offset,
                "limit": limit,
            },
        )

        tasks = []
        for doc in cursor:
            # 修改時間：2025-01-27 - 動態構建 fileTree
            task_id = doc.get('task_id')
            if task_id:
                try:
                    fileTree = self._build_file_tree_for_task(user_id, task_id)
                    if fileTree:
                        doc['fileTree'] = fileTree
                except Exception as e:
                    self.logger.warning(
                        "Failed to build fileTree for task",
                        task_id=task_id,
                        error=str(e),
                    )
            
            tasks.append(UserTask(**doc))

        return tasks

    def _build_file_tree_for_task(self, user_id: str, task_id: str) -> List[Dict[str, Any]]:
        """從 file_metadata 和 folder_metadata 構建 fileTree
        
        修改時間：2025-01-27 - 添加動態構建 fileTree 的方法
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        
        file_tree: List[Dict[str, Any]] = []
        
        try:
            # 1. 獲取該任務的所有文件
            file_metadata_collection = self.client.db.collection('file_metadata')
            files = list(file_metadata_collection.find({
                'user_id': user_id,
                'task_id': task_id
            }))
            
            # 2. 獲取該任務的所有目錄（包括根目錄，parent_task_id == task_id 或為空）
            folder_metadata_collection = self.client.db.collection('folder_metadata')
            # 查找所有與任務相關的目錄（task_id 匹配的目錄）
            folders = list(folder_metadata_collection.find({
                'user_id': user_id,
                'task_id': task_id
            }))
            
            # 3. 構建資料夾映射，支持巢狀
            folder_map: Dict[str, Dict[str, Any]] = {}
            workspace_folder_id = f"{task_id}_workspace"

            # 先建立所有節點
            for folder in folders:
                folder_id = folder.get("_key", "")
                folder_map[folder_id] = {
                    "id": folder_id,
                    "name": folder.get("folder_name", ""),
                    "type": "folder",
                    "children": [],
                    "folder_type": folder.get("folder_type", "workspace"),
                    "parent_task_id": folder.get("parent_task_id"),
                }

            # 確保任務工作區節點存在
            if workspace_folder_id not in folder_map:
                folder_map[workspace_folder_id] = {
                    "id": workspace_folder_id,
                    "name": "任務工作區",
                    "type": "folder",
                    "children": [],
                    "folder_type": "workspace",
                    "parent_task_id": None,
                }

            # 建立父子關係
            for folder_id, node in list(folder_map.items()):
                parent_id = node.get("parent_task_id")
                if parent_id and parent_id in folder_map:
                    folder_map[parent_id]["children"].append(node)
                elif parent_id and parent_id not in folder_map:
                    # 找不到父節點，掛到工作區
                    folder_map[workspace_folder_id]["children"].append(node)
                else:
                    # parent_task_id 為 None，根節點（通常是 workspace）
                    pass

            # 4. 把文件掛到對應的資料夾（folder_id）; 若缺省則掛到工作區
            for file in files:
                file_id = file.get("_key", "")
                filename = file.get("filename", "")
                folder_id = file.get("folder_id") or workspace_folder_id
                if folder_id not in folder_map:
                    # 如果資料夾不存在，掛到工作區
                    folder_id = workspace_folder_id
                folder_map[folder_id]["children"].append(
                    {"id": file_id, "name": filename, "type": "file"}
                )

            # 5. 生成 file_tree：根節點取工作區，其餘根級（parent_task_id is None）在後
            roots: List[Dict[str, Any]] = []
            workspace_node = folder_map.get(workspace_folder_id)
            if workspace_node:
                roots.append(workspace_node)
            for fid, node in folder_map.items():
                if fid == workspace_folder_id:
                    continue
                if node.get("parent_task_id") is None:
                    roots.append(node)

            file_tree.extend(roots)
            
        except Exception as e:
            self.logger.error(
                "Failed to build file tree",
                user_id=user_id,
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
        
        return file_tree

    def update(
        self, user_id: str, task_id: str, update: UserTaskUpdate
    ) -> Optional[UserTask]:
        """更新用戶任務"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        doc_key = f"{user_id}_{task_id}"
        doc = collection.get(doc_key)

        if doc is None:
            return None

        update_data: dict = {"updated_at": datetime.utcnow().isoformat()}

        if update.title is not None:
            update_data["title"] = update.title
        if update.status is not None:
            update_data["status"] = update.status
        # 修改時間：2025-12-09 - 支持更新 task_status
        if update.task_status is not None:
            update_data["task_status"] = update.task_status
        # 修改時間：2025-12-09 - 支持更新 label_color
        if update.label_color is not None:
            update_data["label_color"] = update.label_color
        if update.dueDate is not None:
            update_data["dueDate"] = update.dueDate
        if update.messages is not None:
            update_data["messages"] = [
                msg.model_dump() if hasattr(msg, "model_dump") else msg
                for msg in update.messages
            ]
        if update.executionConfig is not None:
            update_data["executionConfig"] = (
                update.executionConfig.model_dump()
                if hasattr(update.executionConfig, "model_dump")
                else update.executionConfig
            )
        if update.fileTree is not None:
            update_data["fileTree"] = [
                node.model_dump() if hasattr(node, "model_dump") else node
                for node in update.fileTree
            ]

        doc.update(update_data)
        collection.update(doc)

        return UserTask(**doc)

    def delete(self, user_id: str, task_id: str) -> bool:
        """刪除用戶任務"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        doc_key = f"{user_id}_{task_id}"
        doc = collection.get(doc_key)

        if doc is None:
            return False

        collection.delete(doc_key)
        return True

    def sync_tasks(self, user_id: str, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        同步任務列表（批量創建或更新）

        Args:
            user_id: 用戶 ID
            tasks: 任務列表（包含 task_id 和完整任務數據）

        Returns:
            同步結果統計
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        created = 0
        updated = 0
        errors = 0

        for task_data in tasks:
            try:
                task_id = str(task_data.get("id") or task_data.get("task_id"))
                if not task_id:
                    errors += 1
                    continue

                # 檢查任務是否存在
                existing = self.get(user_id, task_id)
                if existing:
                    # 更新現有任務
                    update = UserTaskUpdate(
                        **{
                            "title": task_data.get("title"),
                            "status": task_data.get("status"),
                            "dueDate": task_data.get("dueDate"),
                            "messages": task_data.get("messages"),
                            "executionConfig": task_data.get("executionConfig"),
                            "fileTree": task_data.get("fileTree"),
                        }
                    )
                    self.update(user_id, task_id, update)
                    updated += 1
                else:
                    # 創建新任務
                    create = UserTaskCreate(
                        task_id=task_id,
                        user_id=user_id,
                        title=task_data.get("title", "新任務"),
                        status=task_data.get("status", "pending"),
                        dueDate=task_data.get("dueDate"),
                        messages=task_data.get("messages"),
                        executionConfig=task_data.get("executionConfig"),
                        fileTree=task_data.get("fileTree"),
                    )
                    self.create(create)
                    created += 1
            except Exception as e:
                self.logger.error(
                    "Failed to sync task", error=str(e), task_data=task_data
                )
                errors += 1

        return {
            "created": created,
            "updated": updated,
            "errors": errors,
            "total": len(tasks),
        }


# 單例模式
_user_task_service: Optional[UserTaskService] = None


def get_user_task_service() -> UserTaskService:
    """獲取用戶任務服務單例"""
    global _user_task_service
    if _user_task_service is None:
        _user_task_service = UserTaskService()
    return _user_task_service
