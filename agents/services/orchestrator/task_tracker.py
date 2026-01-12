# 代碼功能說明: Task Tracker - 任務追蹤器實現
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Task Tracker - 任務追蹤器

負責創建和管理任務記錄，追蹤任務執行狀態，支持異步任務執行。
支持 ArangoDB 持久化存儲。
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv

from agents.services.orchestrator.models import TaskStatus
from database.arangodb import ArangoDBClient

# 加載環境變數
base_dir = Path(__file__).resolve().parent.parent.parent.parent
env_path = base_dir / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# ArangoDB Collection 名稱
TASK_RECORDS_COLLECTION_NAME = "task_records"

# 默認超時時間（秒）
DEFAULT_TASK_TIMEOUT = 3600  # 1小時


class TaskRecord:
    """任務記錄模型"""

    def __init__(
        self,
        task_id: str,
        instruction: str,
        target_agent_id: str,
        user_id: str,
        intent: Optional[Dict[str, Any]] = None,
        status: TaskStatus = TaskStatus.PENDING,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        self.task_id = task_id
        self.instruction = instruction
        self.intent = intent
        self.target_agent_id = target_agent_id
        self.user_id = user_id
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.result = result
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "task_id": self.task_id,
            "instruction": self.instruction,
            "intent": self.intent,
            "target_agent_id": self.target_agent_id,
            "user_id": self.user_id,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "result": self.result,
            "error": self.error,
        }


class TaskTracker:
    """任務追蹤器

    負責創建和管理任務記錄，追蹤任務執行狀態。
    支持 ArangoDB 持久化存儲和內存存儲（向後兼容）。
    """

    def __init__(
        self,
        use_arangodb: bool = True,
        client: Optional[ArangoDBClient] = None,
        default_timeout: int = DEFAULT_TASK_TIMEOUT,
    ):
        """
        初始化 Task Tracker

        Args:
            use_arangodb: 是否使用 ArangoDB 持久化（默認 True）
            client: ArangoDB 客戶端（可選，如果不提供則使用默認客戶端）
            default_timeout: 默認任務超時時間（秒）
        """
        self.use_arangodb = use_arangodb
        self.default_timeout = default_timeout
        # 內存存儲（用於向後兼容和緩存）
        self._tasks: Dict[str, TaskRecord] = {}
        # 異步任務回調註冊表
        self._callbacks: Dict[str, List[Callable[[TaskRecord], None]]] = {}
        # 超時任務追蹤
        self._timeout_tasks: Dict[str, datetime] = {}
        # 超時檢查任務（後台運行）
        self._timeout_check_task: Optional[asyncio.Task] = None

        # ArangoDB 客戶端（如果啟用持久化）
        if self.use_arangodb:
            self.client = client or ArangoDBClient()
            self._ensure_collection()
        else:
            self.client = None
            logger.info("Task Tracker initialized with in-memory storage only")

        # 啟動超時檢查任務（如果支持異步）
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循環正在運行，創建後台任務
                self._timeout_check_task = asyncio.create_task(self._timeout_checker())
            else:
                # 否則在事件循環啟動後創建任務
                loop.call_soon_threadsafe(lambda: asyncio.create_task(self._timeout_checker()))
        except RuntimeError:
            # 沒有事件循環，跳過超時檢查
            logger.warning("No event loop available, timeout checking disabled")

    def _ensure_collection(self) -> None:
        """確保 task_records Collection 存在並創建必要的索引"""
        if not self.use_arangodb or self.client is None or self.client.db is None:
            return

        if not self.client.db.has_collection(TASK_RECORDS_COLLECTION_NAME):
            self.client.db.create_collection(TASK_RECORDS_COLLECTION_NAME)
            logger.info(f"Created collection: {TASK_RECORDS_COLLECTION_NAME}")

        collection = self.client.db.collection(TASK_RECORDS_COLLECTION_NAME)

        # 創建索引
        indexes = collection.indexes()
        index_names = [idx["name"] for idx in indexes]

        # task_id 唯一索引
        if "idx_task_id" not in index_names:
            collection.add_index(
                {"type": "persistent", "fields": ["task_id"], "unique": True, "name": "idx_task_id"}
            )

        # user_id 索引
        if "idx_user_id" not in index_names:
            collection.add_index(
                {"type": "persistent", "fields": ["user_id"], "name": "idx_user_id"}
            )

        # status 索引
        if "idx_status" not in index_names:
            collection.add_index({"type": "persistent", "fields": ["status"], "name": "idx_status"})

        # created_at 索引
        if "idx_created_at" not in index_names:
            collection.add_index(
                {"type": "persistent", "fields": ["created_at"], "name": "idx_created_at"}
            )

        # 複合索引：user_id + status
        if "idx_user_status" not in index_names:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["user_id", "status"],
                    "name": "idx_user_status",
                }
            )

        # 複合索引：user_id + created_at
        if "idx_user_created" not in index_names:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["user_id", "created_at"],
                    "name": "idx_user_created",
                }
            )

    def create_task(
        self,
        instruction: str,
        target_agent_id: str,
        user_id: str,
        intent: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        callback_url: Optional[str] = None,
    ) -> str:
        """
        創建任務記錄

        Args:
            instruction: 原始指令
            target_agent_id: 目標 Agent ID
            user_id: 用戶 ID
            intent: 結構化意圖（可選）
            timeout: 任務超時時間（秒，可選，默認使用 default_timeout）
            callback_url: 異步任務完成時的回調URL（可選）

        Returns:
            任務 ID
        """
        task_id = str(uuid.uuid4())

        task_record = TaskRecord(
            task_id=task_id,
            instruction=instruction,
            intent=intent,
            target_agent_id=target_agent_id,
            user_id=user_id,
            status=TaskStatus.PENDING,
        )

        # 保存到內存（用於緩存）
        self._tasks[task_id] = task_record

        # 保存到 ArangoDB（如果啟用）
        if self.use_arangodb:
            self._save_task_to_db(task_record)

        # 設置超時時間
        timeout_seconds = timeout or self.default_timeout
        self._timeout_tasks[task_id] = datetime.utcnow() + timedelta(seconds=timeout_seconds)

        # 註冊回調（如果有）
        if callback_url:
            self.register_callback(task_id, callback_url)

        logger.info(
            f"Created task: {task_id} (agent: {target_agent_id}, user: {user_id}, timeout: {timeout_seconds}s)"
        )

        return task_id

    def register_callback(self, task_id: str, callback: Callable[[TaskRecord], None] | str) -> None:
        """
        註冊任務完成回調

        Args:
            task_id: 任務ID
            callback: 回調函數或回調URL（字符串）
        """
        if task_id not in self._callbacks:
            self._callbacks[task_id] = []

        # 如果是URL字符串，創建HTTP回調函數
        if isinstance(callback, str):
            callback_url = callback

            async def http_callback(task_record: TaskRecord) -> None:
                try:
                    import httpx

                    async with httpx.AsyncClient() as client:
                        await client.post(
                            callback_url,
                            json=task_record.to_dict(),
                            timeout=10.0,
                        )
                except Exception as e:
                    logger.error(f"Failed to call callback URL {callback_url}: {e}")

            # 包裝為同步回調（異步回調在觸發時處理）
            self._callbacks[task_id].append(lambda tr: asyncio.create_task(http_callback(tr)))
        else:
            self._callbacks[task_id].append(callback)

    async def _timeout_checker(self) -> None:
        """後台任務：檢查超時任務"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分鐘檢查一次
                current_time = datetime.utcnow()

                timeout_task_ids = []
                for task_id, timeout_time in self._timeout_tasks.items():
                    if current_time >= timeout_time:
                        timeout_task_ids.append(task_id)

                for task_id in timeout_task_ids:
                    await self._handle_timeout(task_id)
                    del self._timeout_tasks[task_id]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in timeout checker: {e}")

    async def _handle_timeout(self, task_id: str) -> None:
        """處理任務超時"""
        task_record = self.get_task_status(task_id)
        if not task_record:
            return

        # 只處理仍在運行中的任務
        if task_record.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            logger.warning(f"Task {task_id} timed out")
            self.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error="Task timeout",
            )

    def _trigger_callbacks(self, task_record: TaskRecord) -> None:
        """觸發任務完成回調"""
        callbacks = self._callbacks.get(task_record.task_id, [])
        for callback in callbacks:
            try:
                callback(task_record)
            except Exception as e:
                logger.error(f"Callback execution failed for task {task_record.task_id}: {e}")

    def _save_task_to_db(self, task_record: TaskRecord) -> None:
        """保存任務記錄到 ArangoDB"""
        if not self.use_arangodb or self.client is None or self.client.db is None:
            return

        try:
            collection = self.client.db.collection(TASK_RECORDS_COLLECTION_NAME)
            doc = task_record.to_dict()
            doc["_key"] = task_record.task_id  # 使用 task_id 作為 _key
            collection.insert(doc)
        except Exception as e:
            logger.error(f"Failed to save task to ArangoDB: {e}", exc_info=True)
            # 不拋出異常，允許繼續使用內存存儲

    def get_task_status(self, task_id: str) -> Optional[TaskRecord]:
        """
        獲取任務狀態

        Args:
            task_id: 任務 ID

        Returns:
            任務記錄，如果不存在則返回 None
        """
        # 先從內存緩存查找
        if task_id in self._tasks:
            return self._tasks[task_id]

        # 從 ArangoDB 讀取（如果啟用）
        if self.use_arangodb:
            return self._get_task_from_db(task_id)

        return None

    def _get_task_from_db(self, task_id: str) -> Optional[TaskRecord]:
        """從 ArangoDB 讀取任務記錄"""
        if not self.use_arangodb or self.client is None or self.client.db is None:
            return None

        try:
            collection = self.client.db.collection(TASK_RECORDS_COLLECTION_NAME)
            doc = collection.get(task_id)

            if not doc:
                return None

            # 轉換為 TaskRecord 對象
            task_record = TaskRecord(
                task_id=doc.get("task_id", task_id),
                instruction=doc.get("instruction", ""),
                target_agent_id=doc.get("target_agent_id", ""),
                user_id=doc.get("user_id", ""),
                intent=doc.get("intent"),
                status=TaskStatus(doc.get("status", TaskStatus.PENDING.value)),
                created_at=(
                    datetime.fromisoformat(doc["created_at"]) if doc.get("created_at") else None
                ),
                updated_at=(
                    datetime.fromisoformat(doc["updated_at"]) if doc.get("updated_at") else None
                ),
                result=doc.get("result"),
                error=doc.get("error"),
            )

            # 更新內存緩存
            self._tasks[task_id] = task_record

            return task_record

        except Exception as e:
            logger.error(f"Failed to get task from ArangoDB: {e}", exc_info=True)
            return None

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        更新任務狀態

        Args:
            task_id: 任務 ID
            status: 新狀態
            result: 任務結果（可選）
            error: 錯誤信息（可選）

        Returns:
            是否成功更新
        """
        # 從內存或數據庫獲取任務記錄
        task_record = self.get_task_status(task_id)
        if not task_record:
            logger.warning(f"Task not found: {task_id}")
            return False

        # 更新任務記錄
        task_record.status = status
        task_record.updated_at = datetime.utcnow()

        if result is not None:
            task_record.result = result

        if error is not None:
            task_record.error = error

        # 更新內存緩存
        self._tasks[task_id] = task_record

        # 更新 ArangoDB（如果啟用）
        if self.use_arangodb:
            self._update_task_in_db(task_record)

        # 如果任務完成或失敗，觸發回調並清理超時追蹤
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            self._trigger_callbacks(task_record)
            if task_id in self._timeout_tasks:
                del self._timeout_tasks[task_id]
            if task_id in self._callbacks:
                del self._callbacks[task_id]

        logger.info(f"Updated task {task_id} status to {status.value}")

        return True

    def _update_task_in_db(self, task_record: TaskRecord) -> None:
        """更新 ArangoDB 中的任務記錄"""
        if not self.use_arangodb or self.client is None or self.client.db is None:
            return

        try:
            collection = self.client.db.collection(TASK_RECORDS_COLLECTION_NAME)
            doc = task_record.to_dict()
            collection.update({"_key": task_record.task_id, **doc})
        except Exception as e:
            logger.error(f"Failed to update task in ArangoDB: {e}", exc_info=True)
            # 不拋出異常，允許繼續使用內存存儲

    def list_tasks(
        self,
        user_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
    ) -> List[TaskRecord]:
        """
        列出任務記錄

        Args:
            user_id: 用戶 ID 過濾器（可選）
            status: 狀態過濾器（可選）
            limit: 返回數量限制

        Returns:
            任務記錄列表
        """
        # 如果使用 ArangoDB，從數據庫查詢
        if self.use_arangodb:
            return self._list_tasks_from_db(user_id, status, limit)

        # 否則使用內存存儲
        tasks = list(self._tasks.values())

        # 應用過濾器
        if user_id:
            tasks = [t for t in tasks if t.user_id == user_id]

        if status:
            tasks = [t for t in tasks if t.status == status]

        # 按創建時間倒序排序（最新的在前）
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        # 限制數量
        return tasks[:limit]

    def _list_tasks_from_db(
        self,
        user_id: Optional[str],
        status: Optional[TaskStatus],
        limit: int,
    ) -> List[TaskRecord]:
        """從 ArangoDB 查詢任務列表"""
        if not self.use_arangodb or self.client is None or self.client.db is None:
            return []

        try:
            # 構建 AQL 查詢
            filters = []
            bind_vars = {}

            if user_id:
                filters.append("doc.user_id == @user_id")
                bind_vars["user_id"] = user_id

            if status:
                filters.append("doc.status == @status")
                bind_vars["status"] = status.value if hasattr(status, "value") else str(status)

            filter_clause = " AND ".join(filters) if filters else "true"

            aql = f"""
            FOR doc IN {TASK_RECORDS_COLLECTION_NAME}
            FILTER {filter_clause}
            SORT doc.created_at DESC
            LIMIT @limit
            RETURN doc
            """
            bind_vars["limit"] = limit

            cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
            docs = list(cursor)

            # 轉換為 TaskRecord 對象
            tasks = []
            for doc in docs:
                try:
                    task_record = TaskRecord(
                        task_id=doc.get("task_id", doc.get("_key", "")),
                        instruction=doc.get("instruction", ""),
                        target_agent_id=doc.get("target_agent_id", ""),
                        user_id=doc.get("user_id", ""),
                        intent=doc.get("intent"),
                        status=TaskStatus(doc.get("status", TaskStatus.PENDING.value)),
                        created_at=(
                            datetime.fromisoformat(doc["created_at"])
                            if doc.get("created_at")
                            else None
                        ),
                        updated_at=(
                            datetime.fromisoformat(doc["updated_at"])
                            if doc.get("updated_at")
                            else None
                        ),
                        result=doc.get("result"),
                        error=doc.get("error"),
                    )
                    tasks.append(task_record)
                    # 更新內存緩存
                    self._tasks[task_record.task_id] = task_record
                except Exception as e:
                    logger.warning(f"Failed to parse task record: {e}")

            return tasks

        except Exception as e:
            logger.error(f"Failed to list tasks from ArangoDB: {e}", exc_info=True)
            # Fallback 到內存存儲
            tasks = list(self._tasks.values())
            if user_id:
                tasks = [t for t in tasks if t.user_id == user_id]
            if status:
                tasks = [t for t in tasks if t.status == status]
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return tasks[:limit]

    def get_tasks_by_user(self, user_id: str, limit: int = 100) -> List[TaskRecord]:
        """
        獲取用戶的所有任務

        Args:
            user_id: 用戶 ID
            limit: 返回數量限制

        Returns:
            任務記錄列表
        """
        return self.list_tasks(user_id=user_id, limit=limit)
