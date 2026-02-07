# 代碼功能說明: Agent Todo 心跳與進度回報
# 創建日期: 2026-02-07
# 創建人: OpenCode AI
# 最後修改日期: 2026-02-07

"""Agent Todo 心跳與進度回報"""

import asyncio
import json
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from shared.agents.todo.schema import TodoState
import logging

logger = logging.getLogger(__name__)


class HeartbeatStatus(str, Enum):
    """心跳狀態"""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Heartbeat(BaseModel):
    """心跳"""

    todo_id: str
    status: HeartbeatStatus = HeartbeatStatus.RUNNING
    progress: float = 0.0  # 0.0 - 1.0
    current_step: Optional[int] = None
    total_steps: int = 0
    message: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = {}


class HeartbeatPublisher:
    """心跳發佈器"""

    def __init__(
        self,
        todo_id: str,
        total_steps: int,
        callback: Optional[Callable] = None,
        interval: float = 5.0,
    ):
        self.todo_id = todo_id
        self.total_steps = total_steps
        self.callback = callback
        self.interval = interval
        self.current_step = 0
        self.progress = 0.0
        self.status = HeartbeatStatus.RUNNING
        self._started = False
        self._task: Optional[asyncio.Task] = None

    def _create_heartbeat(self, message: str = "") -> Heartbeat:
        """創建心跳"""
        return Heartbeat(
            todo_id=self.todo_id,
            status=self.status,
            progress=self.progress,
            current_step=self.current_step,
            total_steps=self.total_steps,
            message=message,
            timestamp=datetime.utcnow().isoformat(),
        )

    async def _publish_loop(self):
        """發佈循環"""
        while self._started and self.status == HeartbeatStatus.RUNNING:
            heartbeat = self._create_heartbeat()

            if self.callback:
                try:
                    await self.callback(heartbeat)
                except Exception as e:
                    logger.warning(f"Heartbeat callback failed: {e}")

            await asyncio.sleep(self.interval)

    def start(self, message: str = "Task started"):
        """開始心跳"""
        if self._started:
            logger.warning(f"Heartbeat already started for {self.todo_id}")
            return

        self._started = True
        self.status = HeartbeatStatus.RUNNING
        logger.info(f"Heartbeat started: {self.todo_id}, total_steps={self.total_steps}")

        if self.callback:
            self._task = asyncio.create_task(self._publish_loop())

    def update_progress(
        self,
        step: int,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """更新進度"""
        self.current_step = step
        self.progress = step / self.total_steps if self.total_steps > 0 else 0.0
        if message:
            self.message = message
        if metadata:
            self.metadata = metadata

        logger.debug(
            f"Heartbeat progress: {self.todo_id}, step={step}/{self.total_steps}, progress={self.progress:.2%}"
        )

    def complete(self, message: str = "Task completed"):
        """完成"""
        self._started = False
        self.status = HeartbeatStatus.COMPLETED
        self.progress = 1.0
        self.current_step = self.total_steps
        self.message = message

        logger.info(f"Heartbeat completed: {self.todo_id}")

        if self._task:
            self._task.cancel()

        heartbeat = self._create_heartbeat(message)
        if self.callback:
            asyncio.create_task(self.callback(heartbeat))

    def fail(self, message: str = "Task failed"):
        """失敗"""
        self._started = False
        self.status = HeartbeatStatus.FAILED
        self.message = message

        logger.error(f"Heartbeat failed: {self.todo_id}, message={message}")

        if self._task:
            self._task.cancel()

        heartbeat = self._create_heartbeat(message)
        if self.callback:
            asyncio.create_task(self.callback(heartbeat))

    def cancel(self, message: str = "Task cancelled"):
        """取消"""
        self._started = False
        self.status = HeartbeatStatus.CANCELLED
        self.message = message

        logger.info(f"Heartbeat cancelled: {self.todo_id}")

        if self._task:
            self._task.cancel()


class HeartbeatManager:
    """心跳管理器"""

    def __init__(self):
        self._heartbeats: Dict[str, HeartbeatPublisher] = {}

    def create(
        self,
        todo_id: str,
        total_steps: int,
        callback: Optional[Callable] = None,
        interval: float = 5.0,
    ) -> HeartbeatPublisher:
        """創建心跳"""
        publisher = HeartbeatPublisher(
            todo_id=todo_id,
            total_steps=total_steps,
            callback=callback,
            interval=interval,
        )
        self._heartbeats[todo_id] = publisher
        return publisher

    def get(self, todo_id: str) -> Optional[HeartbeatPublisher]:
        """取得心跳"""
        return self._heartbeats.get(todo_id)

    def remove(self, todo_id: str):
        """移除心跳"""
        if todo_id in self._heartbeats:
            self._heartbeats[todo_id].cancel()
            del self._heartbeats[todo_id]

    def get_all_active(self) -> list:
        """取得所有活動心跳"""
        return [
            hb._create_heartbeat()
            for hb in self._heartbeats.values()
            if hb.status == HeartbeatStatus.RUNNING
        ]

    def clear(self):
        """清除所有心跳"""
        for todo_id in list(self._heartbeats.keys()):
            self.remove(todo_id)


_default_manager = None


def get_heartbeat_manager() -> HeartbeatManager:
    """取得全域心跳管理器"""
    global _default_manager
    if _default_manager is None:
        _default_manager = HeartbeatManager()
    return _default_manager
