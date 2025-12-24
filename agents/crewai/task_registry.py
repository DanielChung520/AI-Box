# 代碼功能說明: Task Registry 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""實現任務註冊表，管理所有 Task 實例。"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from agents.crewai.task_models import CrewTask, TaskHistoryEntry, TaskResult, TaskStatus

logger = logging.getLogger(__name__)


class TaskRegistry:
    """任務註冊表。"""

    def __init__(self):
        """初始化任務註冊表。"""
        self._tasks: Dict[str, CrewTask] = {}
        self._task_history: Dict[str, List[TaskHistoryEntry]] = {}
        self._task_results: Dict[str, TaskResult] = {}

    def register_task(
        self,
        task: CrewTask,
    ) -> bool:
        """
        註冊任務。

        Args:
            task: 任務定義

        Returns:
            是否成功註冊
        """
        try:
            if task.task_id in self._tasks:
                logger.warning(f"Task '{task.task_id}' already registered, updating...")
                self._tasks[task.task_id].updated_at = datetime.now()
            else:
                self._tasks[task.task_id] = task
                self._task_history[task.task_id] = []
                self._add_history_entry(
                    task.task_id,
                    TaskStatus.PENDING,
                    "Task registered",
                )

            logger.info(f"Registered task: {task.task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register task '{task.task_id}': {e}")
            return False

    def get_task(self, task_id: str) -> Optional[CrewTask]:
        """
        獲取任務信息。

        Args:
            task_id: 任務 ID

        Returns:
            任務定義，如果不存在則返回 None
        """
        return self._tasks.get(task_id)

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        message: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        更新任務狀態。

        Args:
            task_id: 任務 ID
            status: 新狀態
            message: 狀態更新消息（可選）
            metadata: 元數據（可選）

        Returns:
            是否成功更新
        """
        try:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning(f"Task '{task_id}' not found")
                return False

            old_status = task.status
            task.status = status
            task.updated_at = datetime.now()

            if status == TaskStatus.IN_PROGRESS and not task.started_at:
                task.started_at = datetime.now()
            elif status in (
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ):
                if not task.completed_at:
                    task.completed_at = datetime.now()

            # 更新元數據
            if metadata:
                task.metadata.update(metadata)

            # 記錄歷史
            history_message = message or f"Status changed from {old_status.value} to {status.value}"
            self._add_history_entry(task_id, status, history_message, metadata)

            logger.info(f"Updated task '{task_id}' status: {old_status.value} -> {status.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to update task status '{task_id}': {e}")
            return False

    def list_tasks(
        self,
        crew_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
    ) -> List[CrewTask]:
        """
        列出任務。

        Args:
            crew_id: 隊伍 ID 過濾器（可選）
            status: 狀態過濾器（可選）

        Returns:
            任務列表
        """
        tasks = list(self._tasks.values())

        if crew_id:
            tasks = [t for t in tasks if t.crew_id == crew_id]

        if status:
            tasks = [t for t in tasks if t.status == status]

        return tasks

    def get_task_history(self, task_id: str) -> List[TaskHistoryEntry]:
        """
        獲取任務執行歷史。

        Args:
            task_id: 任務 ID

        Returns:
            歷史條目列表
        """
        return self._task_history.get(task_id, [])

    def save_task_result(self, result: TaskResult) -> bool:
        """
        保存任務執行結果。

        Args:
            result: 任務結果

        Returns:
            是否成功保存
        """
        try:
            self._task_results[result.task_id] = result
            logger.info(f"Saved task result: {result.task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save task result '{result.task_id}': {e}")
            return False

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """
        獲取任務執行結果。

        Args:
            task_id: 任務 ID

        Returns:
            任務結果，如果不存在則返回 None
        """
        return self._task_results.get(task_id)

    def _add_history_entry(
        self,
        task_id: str,
        status: TaskStatus,
        message: str,
        metadata: Optional[Dict] = None,
    ) -> None:
        """添加歷史條目。"""
        if task_id not in self._task_history:
            self._task_history[task_id] = []

        entry = TaskHistoryEntry(
            task_id=task_id,
            status=status,
            timestamp=datetime.now(),
            message=message,
            metadata=metadata or {},
        )
        self._task_history[task_id].append(entry)
