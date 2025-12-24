# 代碼功能說明: Task Tracker - 任務追蹤器實現
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""Task Tracker - 任務追蹤器

負責創建和管理任務記錄，追蹤任務執行狀態，支持異步任務執行。
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.services.orchestrator.models import TaskStatus

logger = logging.getLogger(__name__)


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
    """

    def __init__(self):
        """初始化 Task Tracker"""
        # 使用內存存儲任務記錄（可以擴展為使用 ArangoDB）
        self._tasks: Dict[str, TaskRecord] = {}

    def create_task(
        self,
        instruction: str,
        target_agent_id: str,
        user_id: str,
        intent: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        創建任務記錄

        Args:
            instruction: 原始指令
            target_agent_id: 目標 Agent ID
            user_id: 用戶 ID
            intent: 結構化意圖（可選）

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

        self._tasks[task_id] = task_record

        logger.info(f"Created task: {task_id} (agent: {target_agent_id}, user: {user_id})")

        return task_id

    def get_task_status(self, task_id: str) -> Optional[TaskRecord]:
        """
        獲取任務狀態

        Args:
            task_id: 任務 ID

        Returns:
            任務記錄，如果不存在則返回 None
        """
        return self._tasks.get(task_id)

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
        task_record = self._tasks.get(task_id)
        if not task_record:
            logger.warning(f"Task not found: {task_id}")
            return False

        task_record.status = status
        task_record.updated_at = datetime.utcnow()

        if result is not None:
            task_record.result = result

        if error is not None:
            task_record.error = error

        logger.info(f"Updated task {task_id} status to {status.value}")

        return True

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
