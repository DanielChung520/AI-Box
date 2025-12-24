# 代碼功能說明: Token 預算控制實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""實現 Token 預算監控和控制。"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token 使用記錄。"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def add_usage(self, input_tokens: int, output_tokens: int) -> None:
        """添加使用量。"""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens = self.input_tokens + self.output_tokens


class TokenBudgetGuard:
    """Token 預算守門員。"""

    def __init__(self, budget: int):
        """
        初始化 Token 預算守門員。

        Args:
            budget: Token 預算上限
        """
        self.budget = budget
        self.usage = TokenUsage()
        self._exceeded = False

    def check_budget(self, estimated_tokens: Optional[int] = None) -> bool:
        """
        檢查是否超預算。

        Args:
            estimated_tokens: 預估的 Token 使用量（可選）

        Returns:
            如果未超預算返回 True，否則返回 False
        """
        if self._exceeded:
            logger.warning("Token budget already exceeded")
            return False

        if estimated_tokens:
            if self.usage.total_tokens + estimated_tokens > self.budget:
                self._exceeded = True
                logger.warning(
                    f"Token budget exceeded: {self.usage.total_tokens + estimated_tokens} > {self.budget}"
                )
                return False

        if self.usage.total_tokens >= self.budget:
            self._exceeded = True
            logger.warning(f"Token budget exceeded: {self.usage.total_tokens} >= {self.budget}")
            return False

        return True

    def record_usage(self, input_tokens: int, output_tokens: int) -> None:
        """
        記錄 Token 使用量。

        Args:
            input_tokens: 輸入 Token 數量
            output_tokens: 輸出 Token 數量
        """
        self.usage.add_usage(input_tokens, output_tokens)
        logger.debug(
            f"Token usage: {self.usage.total_tokens}/{self.budget} "
            f"(input: {self.usage.input_tokens}, output: {self.usage.output_tokens})"
        )

        # 檢查是否超預算
        if self.usage.total_tokens >= self.budget:
            self._exceeded = True
            logger.warning(f"Token budget exceeded: {self.usage.total_tokens} >= {self.budget}")

    def get_remaining_budget(self) -> int:
        """
        獲取剩餘預算。

        Returns:
            剩餘 Token 預算
        """
        remaining = self.budget - self.usage.total_tokens
        return max(0, remaining)

    def is_exceeded(self) -> bool:
        """
        檢查是否已超預算。

        Returns:
            如果已超預算返回 True
        """
        return self._exceeded

    def reset(self) -> None:
        """重置使用量。"""
        self.usage = TokenUsage()
        self._exceeded = False
        logger.debug("Token budget guard reset")
