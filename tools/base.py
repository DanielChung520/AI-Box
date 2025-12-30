# 代碼功能說明: 工具基類定義
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""工具基類定義

定義所有工具的統一接口規範和基類。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, TypeVar

from pydantic import BaseModel

from tools.utils.errors import ToolValidationError

TInput = TypeVar("TInput", bound="ToolInput")
TOutput = TypeVar("TOutput", bound="ToolOutput")


class ToolInput(BaseModel):
    """工具輸入參數基類"""

    pass


class ToolOutput(BaseModel):
    """工具輸出結果基類"""

    pass


class BaseTool(ABC, Generic[TInput, TOutput]):
    """工具基類

    所有工具都必須繼承此基類並實現統一接口。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名稱"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """工具版本"""
        pass

    @abstractmethod
    async def execute(self, input_data: TInput) -> TOutput:
        """
        執行工具

        Args:
            input_data: 工具輸入參數

        Returns:
            工具輸出結果

        Raises:
            ToolExecutionError: 工具執行失敗
            ToolValidationError: 輸入參數驗證失敗
        """
        pass

    def validate_input(self, input_data: Dict[str, Any]) -> ToolInput:
        """
        驗證輸入參數

        Args:
            input_data: 原始輸入參數（字典）

        Returns:
            驗證後的輸入參數

        Raises:
            ToolValidationError: 輸入參數驗證失敗
        """
        try:
            # 使用 Pydantic 自動驗證
            return ToolInput(**input_data)
        except Exception as e:
            raise ToolValidationError(
                f"Input validation failed for tool '{self.name}': {str(e)}"
            ) from e
