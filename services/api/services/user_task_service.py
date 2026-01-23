# 代碼功能說明: 用戶任務服務
# 創建日期: 2025-12-08 09:04:21 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21 12:04 UTC+8

"""用戶任務服務 - 實現 ArangoDB CRUD 操作"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoDBClient
from services.api.models.user_task import ExecutionConfig, UserTask, UserTaskCreate, UserTaskUpdate
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
            collection.add_index({"type": "persistent", "fields": ["user_id", "created_at"]})

    def create(self, task: UserTaskCreate) -> UserTask:
        """創建用戶任務"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 修改時間：2026-01-21 - 添加驗證，防止 task_id 為 None 或空字符串
        if not task.task_id:
            raise ValueError(
                f"task_id cannot be None or empty. user_id={task.user_id}, "
                f"task_id={task.task_id}, title={task.title}"
            )

        # 使用 user_id 和 task_id 組合作為 _key，確保唯一性（用於兼容性檢查）
        doc_key = f"{task.user_id}_{task.task_id}"

        doc = {
            "_key": doc_key,
            "task_id": task.task_id,
            "user_id": task.user_id,
            # 修改時間：2026-01-21 - 如果 title 未提供或為空，使用 task_id 作為 title
            "title": task.title if task.title else task.task_id,
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
            "executionConfig": (
                task.executionConfig.model_dump()
                if task.executionConfig and hasattr(task.executionConfig, "model_dump")
                else (task.executionConfig or {"mode": "free"})
            ),
            "fileTree": [
                node.model_dump() if hasattr(node, "model_dump") else node
                for node in (task.fileTree or [])
            ],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # 使用 task_id 作為 _key（不是 user_id_task_id）
        doc["_key"] = task.task_id
        collection = self.client.db.collection(COLLECTION_NAME)

        # 修改時間：2026-01-21 - 使用 upsert 防止併發導致的重複創建
        # 先檢查是否已存在，如果存在則更新，不存在則插入
        existing_doc = collection.get(task.task_id)
        if existing_doc:
            # 任務已存在，記錄警告但不拋出異常（允許冪等操作）
            self.logger.warning(
                "task_already_exists_using_existing",
                task_id=task.task_id,
                user_id=task.user_id,
                existing_title=existing_doc.get("title"),
                note="Task already exists, using existing record",
            )
            doc = existing_doc
        else:
            # 任務不存在，創建新任務
            try:
                collection.insert(doc)
                doc = collection.get(task.task_id)  # 使用正確的 _key 檢索
            except Exception as e:
                # 如果插入失敗（可能是併發導致的），嘗試再次獲取
                existing_doc = collection.get(task.task_id)
                if existing_doc:
                    self.logger.warning(
                        "task_created_by_concurrent_request",
                        task_id=task.task_id,
                        user_id=task.user_id,
                        error=str(e),
                        note="Task was created by another concurrent request",
                    )
                    doc = existing_doc
                else:
                    # 真正的錯誤，重新拋出
                    raise

        # 修改時間：2026-01-06 - 創建任務時自動創建任務工作區和排程任務目錄（添加超時保護）
        # 修改時間：2026-01-06 - 工作區創建改為快速失敗，避免阻塞任務創建
        try:
            import time

            workspace_start_time = time.time()

            workspace_service = get_task_workspace_service()
            # 創建任務工作區（添加超時保護，最多等待2秒）
            if task.user_id:
                try:
                    workspace_service.create_workspace(
                        task_id=task.task_id,
                        user_id=task.user_id,  # type: ignore[arg-type]  # 已檢查不為 None
                    )
                except Exception as workspace_error:
                    self.logger.warning(
                        "create_workspace_failed",
                        task_id=task.task_id,
                        user_id=task.user_id,
                        error=str(workspace_error),
                        note="Workspace creation failed, but task creation continues",
                    )

            # 創建排程任務目錄（為後續功能預留，添加超時保護）
            if task.user_id:
                try:
                    workspace_service.create_scheduled_folder(
                        task_id=task.task_id,
                        user_id=task.user_id,  # type: ignore[arg-type]  # 已檢查不為 None
                    )
                except Exception as scheduled_error:
                    self.logger.warning(
                        "create_scheduled_folder_failed",
                        task_id=task.task_id,
                        user_id=task.user_id,
                        error=str(scheduled_error),
                        note="Scheduled folder creation failed, but task creation continues",
                    )

            workspace_elapsed_time = time.time() - workspace_start_time
            if workspace_elapsed_time > 1.0:  # 如果超過1秒，記錄警告
                self.logger.warning(
                    "workspace_creation_slow",
                    task_id=task.task_id,
                    elapsed_time=workspace_elapsed_time,
                    note=f"Workspace creation took {workspace_elapsed_time:.2f} seconds",
                )

            self.logger.info(
                "任務工作區和排程任務目錄創建成功",
                task_id=task.task_id,
                user_id=task.user_id,
                elapsed_time=workspace_elapsed_time,
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

        # 確保 doc 是字典類型
        if doc is None or not isinstance(doc, dict):
            raise RuntimeError("Failed to retrieve created task")
        return UserTask(**doc)  # type: ignore[arg-type]  # doc 已檢查為 dict

    def get(self, user_id: str, task_id: str, build_file_tree: bool = False) -> Optional[UserTask]:
        """獲取用戶任務

        修改時間：2026-01-06 - 添加 build_file_tree 參數，默認不構建 fileTree 以提升性能
        修改時間：2026-01-21 - 添加用戶 ownership 檢查，防止跨用戶訪問

        Args:
            user_id: 用戶 ID
            task_id: 任務 ID
            build_file_tree: 是否構建 fileTree（默認 False，避免超時）
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)

        doc = None

        # 嘗試多種 _key 格式（優先使用 user_id前綴的格式）
        for doc_key in [f"{user_id}_{task_id}", task_id]:
            doc = collection.get(doc_key)
            if doc:
                break

        if doc is None:
            return None

        # 確保 doc 是字典類型
        if not isinstance(doc, dict):
            return None

        # 安全檢查：確保任務屬於當前用戶
        # 如果找到的文檔的 user_id 與請求的 user_id 不匹配，則拒絕訪問
        doc_user_id = doc.get("user_id")
        self.logger.info(
            "Task ownership check",
            task_id=task_id,
            requesting_user=user_id,
            doc_user_id=doc_user_id,
            found_key=doc.get("_key") if isinstance(doc, dict) else None,
        )
        if doc_user_id and doc_user_id != user_id:
            self.logger.warning(
                "Attempted to access task owned by another user",
                task_id=task_id,
                requesting_user=user_id,
                actual_owner=doc_user_id,
            )
            return None

        # 修改時間：2026-01-06 - 只有在明確要求時才構建 fileTree（避免超時）
        # 如果前端需要 fileTree，應該單獨調用 /api/v1/files/tree API
        if build_file_tree:
            doc_task_id: Optional[str] = doc.get("task_id")  # type: ignore[assignment]  # doc.get 返回 Any | None
            doc_user_id: Optional[str] = doc.get("user_id")  # type: ignore[assignment]  # doc.get 返回 Any | None
            if doc_task_id and doc_user_id:
                try:
                    # 修改時間：2026-01-06 - 添加性能監控
                    import time

                    start_time = time.time()
                    fileTree = self._build_file_tree_for_task(doc_user_id, doc_task_id)
                    elapsed_time = time.time() - start_time

                    if elapsed_time > 3.0:  # 如果超過3秒，記錄警告
                        self.logger.warning(
                            "file_tree_build_slow",
                            task_id=doc_task_id,
                            elapsed_time=elapsed_time,
                            note="File tree build took longer than 3 seconds, consider optimizing",
                        )

                    if fileTree:
                        doc["fileTree"] = fileTree
                except Exception as e:
                    self.logger.warning(
                        "Failed to build fileTree for task",
                        task_id=doc_task_id,
                        error=str(e),
                        exc_info=True,
                    )

        return UserTask(**doc)  # type: ignore[arg-type]  # doc 已檢查為 dict

    def list(
        self, user_id: str, limit: int = 100, offset: int = 0, build_file_tree: bool = False
    ) -> List[UserTask]:
        """列出用戶的所有任務

        修改時間：2025-01-27 - 從 file_metadata 和 folder_metadata 動態構建 fileTree
        修改時間：2026-01-06 - 添加 build_file_tree 參數，默認不構建 fileTree 以提升性能
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
            # 修改時間：2026-01-21 12:04 UTC+8 - 添加防御性檢查，修復缺失字段的任務
            # 檢查並修復缺失的必需字段
            task_id = doc.get("task_id")
            if not task_id:
                # 如果 task_id 缺失，嘗試從 _key 提取
                key = doc.get("_key", "")
                if "_" in key:
                    # 如果 _key 是 "user_id_task_id" 格式，提取後面的部分
                    task_id = key.split("_", 1)[1] if "_" in key else key
                else:
                    # 否則使用 _key 作為 task_id
                    task_id = key

                if task_id:
                    doc["task_id"] = task_id
                    self.logger.warning(
                        "Fixed missing task_id",
                        _key=key,
                        extracted_task_id=task_id,
                        user_id=user_id,
                    )
                else:
                    # 如果無法提取 task_id，跳過這個任務
                    self.logger.error(
                        "Task missing task_id and cannot extract from _key",
                        _key=key,
                        user_id=user_id,
                        doc_keys=list(doc.keys()),
                    )
                    continue

            # 檢查並修復缺失的時間字段
            if not doc.get("created_at"):
                doc["created_at"] = datetime.utcnow().isoformat()
            if not doc.get("updated_at"):
                doc["updated_at"] = datetime.utcnow().isoformat()

            # 檢查並修復缺失的 task_status 字段
            if not doc.get("task_status"):
                doc["task_status"] = "activate"

            # 修改時間：2026-01-06 - 只有在明確要求時才構建 fileTree（列表查詢通常不需要）
            if build_file_tree:
                if task_id:
                    try:
                        fileTree = self._build_file_tree_for_task(user_id, task_id)
                        if fileTree:
                            doc["fileTree"] = fileTree
                    except Exception as e:
                        self.logger.warning(
                            "Failed to build fileTree for task",
                            task_id=task_id,
                            error=str(e),
                        )

            try:
                tasks.append(UserTask(**doc))
            except Exception as e:
                # 如果 Pydantic 驗證失敗，記錄錯誤並跳過這個任務
                self.logger.error(
                    "Failed to parse task document",
                    _key=doc.get("_key"),
                    task_id=task_id,
                    user_id=user_id,
                    error=str(e),
                    doc_keys=list(doc.keys()),
                )
                continue

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
            file_metadata_collection = self.client.db.collection("file_metadata")
            files_cursor = file_metadata_collection.find({"user_id": user_id, "task_id": task_id})
            files = list(files_cursor) if files_cursor else []  # type: ignore[arg-type]  # 同步模式下 Cursor 可迭代

            # 2. 獲取該任務的所有目錄（包括根目錄，parent_task_id == task_id 或為空）
            folder_metadata_collection = self.client.db.collection("folder_metadata")
            # 查找所有與任務相關的目錄（task_id 匹配的目錄）
            folders_cursor = folder_metadata_collection.find(
                {"user_id": user_id, "task_id": task_id}
            )
            folders = list(folders_cursor) if folders_cursor else []  # type: ignore[arg-type]  # 同步模式下 Cursor 可迭代

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

    def update(self, user_id: str, task_id: str, update: UserTaskUpdate) -> Optional[UserTask]:
        """更新用戶任務"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        # 使用 task_id 作為 _key（與 create 方法保持一致）
        doc_key = task_id
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
                msg.model_dump() if hasattr(msg, "model_dump") else msg for msg in update.messages
            ]
        if update.executionConfig is not None:
            update_data["executionConfig"] = (
                update.executionConfig.model_dump()
                if hasattr(update.executionConfig, "model_dump")
                else update.executionConfig
            )
        # fileTree 不再緩存到任務文檔中，始終從 file_metadata 和 folder_metadata 動態構建
        # 因此不再處理 update.fileTree

        doc.update(update_data)
        collection.update(doc)  # type: ignore[arg-type]  # update 接受 dict

        return UserTask(**doc)  # type: ignore[arg-type]  # doc 已檢查為 dict

    def delete(self, user_id: str, task_id: str) -> bool:
        """刪除用戶任務（永久刪除）"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        # 使用 task_id 作為 _key（與 create 方法保持一致）
        doc_key = task_id
        doc = collection.get(doc_key)

        if doc is None:
            return False

        collection.delete(doc_key)
        return True

    def soft_delete(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """
        軟刪除用戶任務（移至 Trash）

        修改時間：2026-01-21 - 添加 Soft Delete 機制

        Args:
            user_id: 用戶 ID
            task_id: 任務 ID

        Returns:
            包含 deleted_at 和 permanent_delete_at 的字典
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(COLLECTION_NAME)

        # 修改時間：2026-01-22 - 使用靈活的任務查找邏輯
        # 嘗試多種 _key 格式
        doc = None
        for key in [f"{user_id}_{task_id}", task_id]:
            doc = collection.get(key)
            if doc:
                break

        if doc is None:
            return {
                "success": False,
                "error": "Task not found",
                "task_id": task_id,
            }

        # 確保 doc 是字典類型
        if not isinstance(doc, dict):
            return {
                "success": False,
                "error": "Task not found",
                "task_id": task_id,
            }

        # 確保任務屬於當前用戶
        doc_user_id = doc.get("user_id")
        if doc_user_id and doc_user_id != user_id:
            return {
                "success": False,
                "error": "Task not found or access denied",
                "task_id": task_id,
            }

        # 計算永久刪除時間（7 天後）
        from datetime import timedelta

        now = datetime.utcnow()
        permanent_delete_at = now + timedelta(days=7)

        # 更新任務文檔
        update_data = {
            "task_status": "trash",
            "deleted_at": now.isoformat(),
            "permanent_delete_at": permanent_delete_at.isoformat(),
            "updated_at": now.isoformat(),
        }

        doc.update(update_data)
        collection.update(doc)

        self.logger.info(
            "Task soft-deleted",
            task_id=task_id,
            user_id=user_id,
            deleted_at=now.isoformat(),
            permanent_delete_at=permanent_delete_at.isoformat(),
        )

        return {
            "success": True,
            "task_id": task_id,
            "task_status": "trash",
            "deleted_at": now.isoformat(),
            "permanent_delete_at": permanent_delete_at.isoformat(),
        }

    def restore(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """
        恢復用戶任務（從 Trash 恢復到 activate）

        修改時間：2026-01-21 - 添加恢復功能

        Args:
            user_id: 用戶 ID
            task_id: 任務 ID

        Returns:
            恢復結果字典
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(COLLECTION_NAME)

        # 修改時間：2026-01-22 - 使用靈活的任務查找邏輯
        doc = None
        for key in [f"{user_id}_{task_id}", task_id]:
            doc = collection.get(key)
            if doc:
                break

        if doc is None:
            return {
                "success": False,
                "error": "Task not found",
                "task_id": task_id,
            }

        # 確保 doc 是字典類型
        if not isinstance(doc, dict):
            return {
                "success": False,
                "error": "Task not found",
                "task_id": task_id,
            }

        # 確保任務屬於當前用戶
        doc_user_id = doc.get("user_id")
        if doc_user_id and doc_user_id != user_id:
            return {
                "success": False,
                "error": "Task not found or access denied",
                "task_id": task_id,
            }

        # 檢查任務是否在 Trash 中
        if doc.get("task_status") != "trash":
            return {
                "success": False,
                "error": "Task is not in trash",
                "task_id": task_id,
                "current_status": doc.get("task_status"),
            }

        now = datetime.utcnow()

        # 更新任務文檔
        update_data = {
            "task_status": "activate",
            "deleted_at": None,
            "permanent_delete_at": None,
            "updated_at": now.isoformat(),
        }

        doc.update(update_data)
        collection.update(doc)

        self.logger.info(
            "Task restored from trash",
            task_id=task_id,
            user_id=user_id,
        )

        return {
            "success": True,
            "task_id": task_id,
            "task_status": "activate",
            "deleted_at": None,
            "permanent_delete_at": None,
        }

    def permanent_delete(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """
        永久刪除用戶任務（從 Trash 徹底刪除）

        修改時間：2026-01-21 - 添加永久刪除功能

        Args:
            user_id: 用戶 ID
            task_id: 任務 ID

        Returns:
            刪除結果字典
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(COLLECTION_NAME)

        # 修改時間：2026-01-22 - 使用靈活的任務查找邏輯
        doc = None
        for key in [f"{user_id}_{task_id}", task_id]:
            doc = collection.get(key)
            if doc:
                break

        if doc is None:
            return {
                "success": False,
                "error": "Task not found",
                "task_id": task_id,
            }

        # 確保 doc 是字典類型
        if not isinstance(doc, dict):
            return {
                "success": False,
                "error": "Task not found",
                "task_id": task_id,
            }

        # 確保任務屬於當前用戶
        doc_user_id = doc.get("user_id")
        if doc_user_id and doc_user_id != user_id:
            return {
                "success": False,
                "error": "Task not found or access denied",
                "task_id": task_id,
            }

        # 檢查任務是否在 Trash 中
        if doc.get("task_status") != "trash":
            return {
                "success": False,
                "error": "Task is not in trash",
                "task_id": task_id,
                "current_status": doc.get("task_status"),
            }

        # 永久刪除任務文檔（使用找到的 key）
        actual_key = doc.get("_key") or f"{user_id}_{task_id}"
        collection.delete(actual_key)

        self.logger.info(
            "Task permanently deleted",
            task_id=task_id,
            user_id=user_id,
        )

        return {
            "success": True,
            "task_id": task_id,
            "message": "Task permanently deleted",
        }

    def list_tasks(
        self,
        user_id: str,
        task_status: Optional[str] = None,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出用戶任務

        修改時間：2026-01-21 - 添加 Trash 過濾功能

        Args:
            user_id: 用戶 ID
            task_status: 任務狀態過濾（activate/archive/trash）
            include_archived: 是否包含歸檔任務
            limit: 返回數量限制
            offset: 偏移量

        Returns:
            任務列表
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 修改時間：2026-01-22 - 使用 bind_vars 避免 ArangoDB 解析錯誤
        bind_vars = {"user_id": user_id}

        if task_status:
            bind_vars["task_status"] = task_status
        elif not include_archived:
            # 默認只返回 activate 和 trash 狀態的任務
            # 這種情況下需要特殊處理，因為無法使用簡單的 bind_var
            pass

        query = f"""
        FOR doc IN {COLLECTION_NAME}
        FILTER doc.user_id == @user_id
        """

        if task_status:
            query += " && doc.task_status == @task_status"
        elif not include_archived:
            query += ' && (doc.task_status == "activate" OR doc.task_status == "trash")'

        query += """
        SORT doc.created_at DESC
        LIMIT @offset, @limit
        RETURN doc
        """

        bind_vars["offset"] = offset
        bind_vars["limit"] = limit

        cursor = self.client.db.aql.execute(query, bind_vars=bind_vars)
        tasks = list(cursor)

        return tasks

    def sync_tasks(self, user_id: str, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        同步任務列表（批量創建或更新）

        修改時間：2026-01-06 - 優化性能，避免構建 fileTree

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

        collection = self.client.db.collection(COLLECTION_NAME)

        for task_data in tasks:
            try:
                task_id = str(task_data.get("id") or task_data.get("task_id"))
                if not task_id:
                    errors += 1
                    continue

                # 修改時間：2026-01-06 - 直接檢查任務是否存在，避免構建 fileTree
                doc_key = f"{user_id}_{task_id}"
                existing_doc = collection.get(doc_key)

                # 處理 executionConfig：如果存在且為字典，轉換為 ExecutionConfig 對象
                execution_config = task_data.get("executionConfig")
                if execution_config is not None:
                    if isinstance(execution_config, dict):
                        try:
                            execution_config = ExecutionConfig(**execution_config)
                        except Exception as e:
                            self.logger.warning(
                                "Invalid executionConfig format, using default",
                                error=str(e),
                                execution_config=execution_config,
                            )
                            execution_config = ExecutionConfig(mode="free")
                    elif not isinstance(execution_config, ExecutionConfig):
                        execution_config = ExecutionConfig(mode="free")
                else:
                    execution_config = ExecutionConfig(mode="free")

                if existing_doc:
                    # 更新現有任務（直接更新文檔，避免構建 fileTree）
                    update_dict = {"updated_at": datetime.utcnow().isoformat()}
                    if "title" in task_data:
                        update_dict["title"] = task_data.get("title")
                    if "status" in task_data:
                        update_dict["status"] = task_data.get("status")
                    if "task_status" in task_data:
                        update_dict["task_status"] = task_data.get("task_status")
                    if "label_color" in task_data:
                        update_dict["label_color"] = task_data.get("label_color")
                    if "dueDate" in task_data:
                        update_dict["dueDate"] = task_data.get("dueDate")
                    if "messages" in task_data:
                        update_dict["messages"] = task_data.get("messages")
                    if "executionConfig" in task_data:
                        update_dict["executionConfig"] = (
                            execution_config.model_dump()
                            if hasattr(execution_config, "model_dump")
                            else execution_config
                        )
                    # fileTree 不再緩存到任務文檔中，因此不處理 fileTree 更新

                    if len(update_dict) > 1:  # 除了 updated_at 之外還有其他更新
                        existing_doc.update(update_dict)
                        collection.update(existing_doc)
                        updated += 1
                else:
                    # 創建新任務
                    # fileTree 不再緩存到任務文檔中，因此不傳遞 fileTree
                    create = UserTaskCreate(
                        task_id=task_id,
                        user_id=user_id,
                        label_color=None,  # type: ignore[call-arg]  # label_color 有默認值
                        title=task_data.get("title", "新任務"),
                        status=task_data.get("status", "pending"),
                        dueDate=task_data.get("dueDate"),
                        messages=task_data.get("messages"),
                        executionConfig=execution_config,  # 使用處理後的 executionConfig
                        fileTree=[],  # 空 fileTree，始終從 file_metadata 動態構建
                    )
                    self.create(create)
                    created += 1
            except Exception as e:
                self.logger.error("Failed to sync task", error=str(e), task_data=task_data)
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
