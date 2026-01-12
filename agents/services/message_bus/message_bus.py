# 代碼功能說明: Message Bus 核心類
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Message Bus 核心類

實現 GRO 規範的異步訊息總線，支持 Task Contract 模式、fan-out 和 fan-in。
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from agents.services.message_bus.models import MessageType, TaskDispatch, TaskResult

logger = logging.getLogger(__name__)


class MessageBus:
    """Message Bus 核心類

    實現 GRO 規範的異步訊息總線，支持 Task Contract 模式、fan-out 和 fan-in。
    """

    def __init__(self):
        """初始化 Message Bus"""
        # 訂閱者字典：{message_type: [callback1, callback2, ...]}
        self._subscribers: Dict[MessageType, List[Callable]] = defaultdict(list)
        # 消息隊列：{react_id: [message1, message2, ...]}
        self._message_queues: Dict[str, List[Any]] = defaultdict(list)
        # 任務結果字典：{task_id: TaskResult}
        self._task_results: Dict[str, TaskResult] = {}

    def subscribe(self, message_type: MessageType, callback: Callable) -> None:
        """
        訂閱消息類型

        Args:
            message_type: 消息類型
            callback: 回調函數
        """
        self._subscribers[message_type].append(callback)
        logger.debug(f"Subscribed to {message_type.value}: {callback.__name__}")

    def unsubscribe(self, message_type: MessageType, callback: Callable) -> None:
        """
        取消訂閱消息類型

        Args:
            message_type: 消息類型
            callback: 回調函數
        """
        if callback in self._subscribers[message_type]:
            self._subscribers[message_type].remove(callback)
            logger.debug(f"Unsubscribed from {message_type.value}: {callback.__name__}")

    async def publish(self, message: TaskDispatch | TaskResult) -> None:
        """
        發布消息

        Args:
            message: 消息對象
        """
        message_type = message.message_type

        # 通知所有訂閱者
        for callback in self._subscribers.get(message_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}", exc_info=True)

        # 如果是 TASK_RESULT，存儲結果
        if message_type == MessageType.TASK_RESULT and isinstance(message, TaskResult):
            self._task_results[message.task_id] = message

        # 將消息添加到隊列
        react_id = getattr(message, "react_id", None)
        if react_id:
            self._message_queues[react_id].append(message)

        logger.debug(
            f"Published {message_type.value}: task_id={getattr(message, 'task_id', 'N/A')}"
        )

    async def publish_task_dispatch(self, dispatch: TaskDispatch) -> None:
        """
        發布任務派發消息

        Args:
            dispatch: TaskDispatch 對象
        """
        await self.publish(dispatch)

    async def publish_task_result(self, result: TaskResult) -> None:
        """
        發布任務結果消息

        Args:
            result: TaskResult 對象
        """
        await self.publish(result)

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """
        獲取任務結果

        Args:
            task_id: 任務 ID

        Returns:
            TaskResult 對象，如果不存在則返回 None
        """
        return self._task_results.get(task_id)

    async def wait_for_results(
        self, react_id: str, task_ids: List[str], timeout: int = 300
    ) -> List[TaskResult]:
        """
        等待任務結果（fan-in）

        Args:
            react_id: ReAct session ID
            task_ids: 任務 ID 列表
            timeout: 超時時間（秒）

        Returns:
            任務結果列表
        """
        results = []
        start_time = asyncio.get_event_loop().time()

        while len(results) < len(task_ids):
            # 檢查超時
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.warning(f"Timeout waiting for results: {len(results)}/{len(task_ids)}")
                break

            # 檢查是否有結果
            for task_id in task_ids:
                if task_id not in [r.task_id for r in results]:
                    result = self.get_task_result(task_id)
                    if result:
                        results.append(result)

            # 如果還沒有所有結果，等待一小段時間
            if len(results) < len(task_ids):
                await asyncio.sleep(0.1)

        return results

    def get_messages_by_react_id(self, react_id: str) -> List[Any]:
        """
        獲取指定 react_id 的所有消息

        Args:
            react_id: ReAct session ID

        Returns:
            消息列表
        """
        return self._message_queues.get(react_id, [])
