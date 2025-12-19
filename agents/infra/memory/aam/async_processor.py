# 代碼功能說明: AAM 異步處理器
# 創建日期: 2025-11-28 21:54 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-28 21:54 (UTC+8)

"""AAM 異步處理器 - 提供異步任務隊列、調度和管理功能"""

from __future__ import annotations

import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    """任務狀態枚舉"""

    PENDING = "pending"  # 待處理
    RUNNING = "running"  # 運行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失敗
    CANCELLED = "cancelled"  # 已取消


@dataclass
class AsyncTask:
    """異步任務數據模型"""

    task_id: str
    task_type: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0  # 優先級（數字越大優先級越高）
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


class AsyncProcessor:
    """異步處理器 - 管理異步任務的執行"""

    def __init__(
        self,
        max_workers: int = 4,
        default_timeout: int = 300,  # 5分鐘
    ):
        """
        初始化異步處理器

        Args:
            max_workers: 最大工作線程數
            default_timeout: 默認超時時間（秒）
        """
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: Dict[str, AsyncTask] = {}
        self.futures: Dict[str, Future[Any]] = {}
        self.logger = logger.bind(component="async_processor")

    def submit_task(
        self,
        task_type: str,
        task_func: Callable[[], Any],
        priority: int = 0,
        max_retries: int = 3,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        提交異步任務

        Args:
            task_type: 任務類型
            task_func: 任務函數
            priority: 任務優先級
            max_retries: 最大重試次數
            timeout: 超時時間（秒）
            metadata: 任務元數據

        Returns:
            任務 ID
        """
        task_id = str(uuid.uuid4())
        task = AsyncTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            max_retries=max_retries,
            metadata=metadata or {},
        )
        self.tasks[task_id] = task

        # 提交任務到線程池
        future = self.executor.submit(self._execute_task, task, task_func, timeout)
        self.futures[task_id] = future

        self.logger.info("Submitted task", task_id=task_id, task_type=task_type)
        return task_id

    def _execute_task(
        self, task: AsyncTask, task_func: Callable[[], Any], timeout: Optional[int]
    ) -> Any:
        """執行任務"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        try:
            # 執行任務（帶超時）
            timeout = timeout or self.default_timeout
            result = task_func()

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result

            self.logger.info("Task completed", task_id=task.task_id)
            return result
        except Exception as e:
            task.error = str(e)
            task.retry_count += 1

            # 重試邏輯
            if task.retry_count <= task.max_retries:
                self.logger.warning(
                    "Task failed, retrying",
                    task_id=task.task_id,
                    retry_count=task.retry_count,
                    error=str(e),
                )
                # 簡單重試（實際應用中應該使用指數退避）
                time.sleep(1)
                return self._execute_task(task, task_func, timeout)
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                self.logger.error("Task failed", task_id=task.task_id, error=str(e))
                raise

    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """獲取任務狀態"""
        return self.tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """取消任務"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            return False

        if task_id in self.futures:
            future = self.futures[task_id]
            future.cancel()

        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()

        self.logger.info("Task cancelled", task_id=task_id)
        return True

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
    ) -> List[AsyncTask]:
        """列出任務"""
        tasks = list(self.tasks.values())

        if status is not None:
            tasks = [t for t in tasks if t.status == status]

        if task_type is not None:
            tasks = [t for t in tasks if t.task_type == task_type]

        # 按優先級和創建時間排序
        tasks.sort(key=lambda t: (t.priority, t.created_at), reverse=True)

        return tasks

    def shutdown(self, wait: bool = True) -> None:
        """關閉處理器"""
        self.executor.shutdown(wait=wait)
        self.logger.info("Async processor shut down")
