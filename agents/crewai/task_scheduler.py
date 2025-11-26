# 代碼功能說明: Task Scheduler 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""實現任務排程功能。"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from queue import PriorityQueue

from agents.crewai.task_models import CrewTask, TaskStatus, TaskPriority
from agents.crewai.task_registry import TaskRegistry

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任務排程器。"""

    def __init__(self, task_registry: Optional[TaskRegistry] = None):
        """
        初始化任務排程器。

        Args:
            task_registry: 任務註冊表（可選）
        """
        self._task_registry = task_registry or TaskRegistry()
        self._task_queue: PriorityQueue = PriorityQueue()
        self._scheduled_tasks: Dict[str, CrewTask] = {}

    def _get_priority_value(self, priority: TaskPriority) -> int:
        """獲取優先級數值（數值越小優先級越高）。"""
        priority_map = {
            TaskPriority.URGENT: 1,
            TaskPriority.HIGH: 2,
            TaskPriority.MEDIUM: 3,
            TaskPriority.LOW: 4,
        }
        return priority_map.get(priority, 3)

    def schedule_task(
        self,
        task: CrewTask,
    ) -> bool:
        """
        排程任務。

        Args:
            task: 任務定義

        Returns:
            是否成功排程
        """
        try:
            # 註冊任務
            if not self._task_registry.register_task(task):
                return False

            # 添加到排程隊列
            priority_value = self._get_priority_value(task.priority)
            self._task_queue.put(
                (priority_value, task.created_at.timestamp(), task.task_id)
            )
            self._scheduled_tasks[task.task_id] = task

            logger.info(
                f"Scheduled task: {task.task_id} (priority: {task.priority.value})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to schedule task '{task.task_id}': {e}")
            return False

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任務。

        Args:
            task_id: 任務 ID

        Returns:
            是否成功取消
        """
        try:
            task = self._task_registry.get_task(task_id)
            if not task:
                logger.warning(f"Task '{task_id}' not found")
                return False

            # 更新狀態
            self._task_registry.update_task_status(
                task_id,
                TaskStatus.CANCELLED,
                message="Task cancelled by scheduler",
            )

            # 從排程中移除
            if task_id in self._scheduled_tasks:
                del self._scheduled_tasks[task_id]

            logger.info(f"Cancelled task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel task '{task_id}': {e}")
            return False

    def get_task_queue(self) -> List[CrewTask]:
        """
        獲取任務隊列。

        Returns:
            任務列表（按優先級排序）
        """
        # 重新構建隊列（因為 PriorityQueue 不支持直接遍歷）
        queue_items = []
        temp_queue = PriorityQueue()

        while not self._task_queue.empty():
            item = self._task_queue.get()
            queue_items.append(item)
            temp_queue.put(item)

        # 恢復隊列
        self._task_queue = temp_queue

        # 獲取任務列表
        tasks = []
        for _, _, task_id in queue_items:
            task = self._scheduled_tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                tasks.append(task)

        return tasks

    def prioritize_task(
        self,
        task_id: str,
        new_priority: TaskPriority,
    ) -> bool:
        """
        調整任務優先級。

        Args:
            task_id: 任務 ID
            new_priority: 新優先級

        Returns:
            是否成功調整
        """
        try:
            task = self._task_registry.get_task(task_id)
            if not task:
                logger.warning(f"Task '{task_id}' not found")
                return False

            old_priority = task.priority
            task.priority = new_priority
            task.updated_at = datetime.now()

            # 更新排程隊列
            if task_id in self._scheduled_tasks:
                # 重新排程
                self._scheduled_tasks[task_id] = task
                # 注意：PriorityQueue 不支持直接更新，需要重新排程
                # 這裡簡化處理，實際使用時可能需要更複雜的邏輯

            logger.info(
                f"Updated task '{task_id}' priority: {old_priority.value} -> {new_priority.value}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to prioritize task '{task_id}': {e}")
            return False

    def get_next_task(self) -> Optional[CrewTask]:
        """
        獲取下一個待處理的任務。

        Returns:
            下一個任務，如果沒有則返回 None
        """
        while not self._task_queue.empty():
            _, _, task_id = self._task_queue.get()
            task = self._scheduled_tasks.get(task_id)

            if task and task.status == TaskStatus.PENDING:
                return task

        return None
