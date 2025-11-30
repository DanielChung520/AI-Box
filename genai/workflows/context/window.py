# 代碼功能說明: 上下文窗口管理
# 創建日期: 2025-01-27 14:00 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 14:00 (UTC+8)

"""上下文窗口管理器，提供滑動窗口、智能截斷和 Token 計數功能。"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from genai.workflows.context.models import ContextMessage

logger = logging.getLogger(__name__)


class TruncationStrategy(str, Enum):
    """截斷策略枚舉。"""

    FIFO = "fifo"  # 先進先出
    IMPORTANCE = "importance"  # 保留重要消息
    SUMMARY = "summary"  # 摘要壓縮


class ContextWindow:
    """上下文窗口管理器。"""

    def __init__(
        self,
        max_tokens: int = 4096,
        max_messages: Optional[int] = None,
        truncation_strategy: TruncationStrategy = TruncationStrategy.FIFO,
        token_counter: Optional[Any] = None,
    ) -> None:
        """
        初始化上下文窗口管理器。

        Args:
            max_tokens: 最大 Token 數
            max_messages: 最大消息數（可選）
            truncation_strategy: 截斷策略
            token_counter: Token 計數器（如果為 None，則使用簡單計數）
        """
        self._max_tokens = max_tokens
        self._max_messages = max_messages
        self._truncation_strategy = truncation_strategy
        self._token_counter = token_counter or self._default_token_counter

    def _default_token_counter(self, text: str) -> int:
        """
        默認 Token 計數器（簡單估算：1 token ≈ 4 字符）。

        Args:
            text: 文本

        Returns:
            Token 數量
        """
        return len(text) // 4

    def count_tokens(self, message: ContextMessage) -> int:
        """
        計算消息的 Token 數量。

        Args:
            message: 消息對象

        Returns:
            Token 數量
        """
        content_tokens = self._token_counter(message.content)
        # 角色和元數據的 Token（估算）
        role_tokens = 5
        metadata_tokens = len(str(message.metadata)) // 4
        return content_tokens + role_tokens + metadata_tokens

    def count_total_tokens(self, messages: List[ContextMessage]) -> int:
        """
        計算消息列表的總 Token 數量。

        Args:
            messages: 消息列表

        Returns:
            總 Token 數量
        """
        return sum(self.count_tokens(msg) for msg in messages)

    def truncate(self, messages: List[ContextMessage]) -> List[ContextMessage]:
        """
        截斷消息列表以符合窗口限制。

        Args:
            messages: 消息列表

        Returns:
            截斷後的消息列表
        """
        if not messages:
            return []

        # 首先應用消息數量限制
        if self._max_messages is not None and len(messages) > self._max_messages:
            messages = self._truncate_by_count(messages)

        # 然後應用 Token 限制
        total_tokens = self.count_total_tokens(messages)
        if total_tokens > self._max_tokens:
            messages = self._truncate_by_tokens(messages)

        return messages

    def _truncate_by_count(
        self, messages: List[ContextMessage]
    ) -> List[ContextMessage]:
        """
        根據消息數量截斷。

        Args:
            messages: 消息列表

        Returns:
            截斷後的消息列表
        """
        if self._max_messages is None:
            return messages

        if len(messages) <= self._max_messages:
            return messages

        if self._truncation_strategy == TruncationStrategy.FIFO:
            # 先進先出：保留最新的消息
            return messages[-self._max_messages :]
        elif self._truncation_strategy == TruncationStrategy.IMPORTANCE:
            # 保留重要消息：優先保留 system 和 user 消息
            return self._truncate_by_importance(messages)
        else:
            # 默認使用 FIFO
            return messages[-self._max_messages :]

    def _truncate_by_tokens(
        self, messages: List[ContextMessage]
    ) -> List[ContextMessage]:
        """
        根據 Token 數量截斷。

        Args:
            messages: 消息列表

        Returns:
            截斷後的消息列表
        """
        total_tokens = self.count_total_tokens(messages)
        if total_tokens <= self._max_tokens:
            return messages

        if self._truncation_strategy == TruncationStrategy.FIFO:
            # 先進先出：從最舊的消息開始移除
            return self._truncate_fifo(messages)
        elif self._truncation_strategy == TruncationStrategy.IMPORTANCE:
            # 保留重要消息
            return self._truncate_by_importance(messages)
        elif self._truncation_strategy == TruncationStrategy.SUMMARY:
            # 摘要壓縮（簡化實現：保留前後消息，壓縮中間）
            return self._truncate_with_summary(messages)
        else:
            return self._truncate_fifo(messages)

    def _truncate_fifo(self, messages: List[ContextMessage]) -> List[ContextMessage]:
        """
        使用 FIFO 策略截斷。

        Args:
            messages: 消息列表

        Returns:
            截斷後的消息列表
        """
        result: List[ContextMessage] = []
        current_tokens = 0

        # 從最新的消息開始，保留到達到限制
        for message in reversed(messages):
            message_tokens = self.count_tokens(message)
            if current_tokens + message_tokens <= self._max_tokens:
                result.insert(0, message)
                current_tokens += message_tokens
            else:
                break

        return result if result else messages[:1]  # 至少保留一條消息

    def _truncate_by_importance(
        self, messages: List[ContextMessage]
    ) -> List[ContextMessage]:
        """
        根據重要性截斷（優先保留 system 和 user 消息）。

        Args:
            messages: 消息列表

        Returns:
            截斷後的消息列表
        """
        # 分離重要消息和普通消息
        important: List[ContextMessage] = []
        normal: List[ContextMessage] = []

        for msg in messages:
            if msg.role in ("system", "user"):
                important.append(msg)
            else:
                normal.append(msg)

        # 計算重要消息的 Token
        important_tokens = self.count_total_tokens(important)

        # 如果重要消息已經超過限制，只保留最新的重要消息
        if important_tokens > self._max_tokens:
            return self._truncate_fifo(important)

        # 計算可以容納的普通消息 Token
        remaining_tokens = self._max_tokens - important_tokens

        # 從普通消息中選擇（優先保留最新的）
        selected_normal: List[ContextMessage] = []
        current_tokens = 0

        for message in reversed(normal):
            message_tokens = self.count_tokens(message)
            if current_tokens + message_tokens <= remaining_tokens:
                selected_normal.insert(0, message)
                current_tokens += message_tokens
            else:
                break

        # 合併並保持順序
        result: List[ContextMessage] = []
        important_idx = 0
        normal_idx = 0

        for msg in messages:
            if msg.role in ("system", "user"):
                if important_idx < len(important):
                    result.append(important[important_idx])
                    important_idx += 1
            else:
                if normal_idx < len(selected_normal) and msg in selected_normal:
                    result.append(msg)
                    normal_idx += 1

        return result if result else messages[:1]

    def _truncate_with_summary(
        self, messages: List[ContextMessage]
    ) -> List[ContextMessage]:
        """
        使用摘要壓縮策略截斷（簡化實現）。

        Args:
            messages: 消息列表

        Returns:
            截斷後的消息列表
        """
        if len(messages) <= 2:
            return messages

        # 保留第一條和最後幾條消息
        # 中間的消息可以壓縮（這裡簡化為直接移除）
        first_message = messages[0]
        last_messages = messages[-5:]  # 保留最後 5 條

        result = [first_message] + last_messages

        # 檢查 Token 限制
        total_tokens = self.count_total_tokens(result)
        if total_tokens > self._max_tokens:
            # 如果還是超過，使用 FIFO 策略
            return self._truncate_fifo(messages)

        return result

    def slide_window(
        self, messages: List[ContextMessage], new_message: ContextMessage
    ) -> List[ContextMessage]:
        """
        滑動窗口：添加新消息並截斷。

        Args:
            messages: 現有消息列表
            new_message: 新消息

        Returns:
            更新後的消息列表
        """
        # 添加新消息
        updated_messages = messages + [new_message]

        # 截斷以符合限制
        return self.truncate(updated_messages)

    def get_window_info(self, messages: List[ContextMessage]) -> Dict[str, Any]:
        """
        獲取窗口信息。

        Args:
            messages: 消息列表

        Returns:
            窗口信息字典
        """
        total_tokens = self.count_total_tokens(messages)
        message_count = len(messages)

        return {
            "message_count": message_count,
            "total_tokens": total_tokens,
            "max_tokens": self._max_tokens,
            "max_messages": self._max_messages,
            "token_usage_ratio": (
                total_tokens / self._max_tokens if self._max_tokens > 0 else 0.0
            ),
            "truncation_strategy": self._truncation_strategy.value,
        }
