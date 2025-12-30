# 代碼功能說明: 文本格式化工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""文本格式化工具

支持大小寫轉換、文本對齊等格式化操作。
"""

from __future__ import annotations

from typing import Optional

import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)

# 支持的操作類型
SUPPORTED_OPERATIONS = {
    "uppercase",  # 轉為大寫
    "lowercase",  # 轉為小寫
    "title",  # 標題格式（每個單詞首字母大寫）
    "capitalize",  # 首字母大寫
    "swapcase",  # 交換大小寫
    "strip",  # 去除首尾空白
    "lstrip",  # 去除左側空白
    "rstrip",  # 去除右側空白
}


class TextFormatterInput(ToolInput):
    """文本格式化輸入參數"""

    text: str  # 輸入文本
    operation: str  # 操作類型（如 "uppercase", "lowercase", "title"）
    width: Optional[int] = None  # 寬度（用於對齊操作）
    align: Optional[str] = None  # 對齊方式（"left", "right", "center"），僅用於對齊操作


class TextFormatterOutput(ToolOutput):
    """文本格式化輸出結果"""

    formatted_text: str  # 格式化後的文本
    original_text: str  # 原始文本
    operation: str  # 操作類型


class TextFormatter(BaseTool[TextFormatterInput, TextFormatterOutput]):
    """文本格式化工具

    支持大小寫轉換、文本對齊等格式化操作。
    """

    @property
    def name(self) -> str:
        """工具名稱"""
        return "text_formatter"

    @property
    def description(self) -> str:
        """工具描述"""
        return "文本格式化工具，支持大小寫轉換、文本對齊等格式化操作"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _validate_operation(self, operation: str) -> None:
        """
        驗證操作類型是否支持

        Args:
            operation: 操作類型

        Raises:
            ToolValidationError: 操作類型不支持
        """
        if operation.lower() not in SUPPORTED_OPERATIONS:
            supported = ", ".join(sorted(SUPPORTED_OPERATIONS))
            raise ToolValidationError(
                f"Unsupported operation: {operation}. Supported operations: {supported}",
                field="operation",
            )

    def _format_text(
        self, text: str, operation: str, width: Optional[int] = None, align: Optional[str] = None
    ) -> str:
        """
        格式化文本

        Args:
            text: 輸入文本
            operation: 操作類型
            width: 寬度（用於對齊）
            align: 對齊方式

        Returns:
            格式化後的文本

        Raises:
            ToolValidationError: 格式化失敗
        """
        operation_lower = operation.lower()

        if operation_lower == "uppercase":
            return text.upper()
        elif operation_lower == "lowercase":
            return text.lower()
        elif operation_lower == "title":
            return text.title()
        elif operation_lower == "capitalize":
            return text.capitalize()
        elif operation_lower == "swapcase":
            return text.swapcase()
        elif operation_lower == "strip":
            return text.strip()
        elif operation_lower == "lstrip":
            return text.lstrip()
        elif operation_lower == "rstrip":
            return text.rstrip()
        else:
            # 對齊操作
            if width is None:
                raise ToolValidationError(
                    "width parameter is required for alignment operations", field="width"
                )
            if align is None:
                align = "left"

            align_lower = align.lower()
            if align_lower == "left":
                return text.ljust(width)
            elif align_lower == "right":
                return text.rjust(width)
            elif align_lower == "center":
                return text.center(width)
            else:
                raise ToolValidationError(
                    f"Unsupported align value: {align}. Supported: left, right, center",
                    field="align",
                )

    async def execute(self, input_data: TextFormatterInput) -> TextFormatterOutput:
        """
        執行文本格式化

        Args:
            input_data: 工具輸入參數

        Returns:
            工具輸出結果

        Raises:
            ToolExecutionError: 工具執行失敗
            ToolValidationError: 輸入參數驗證失敗
        """
        try:
            # 驗證操作類型
            self._validate_operation(input_data.operation)

            # 格式化文本
            formatted_text = self._format_text(
                input_data.text, input_data.operation, input_data.width, input_data.align
            )

            logger.debug(
                "text_formatting_completed",
                operation=input_data.operation,
                original_length=len(input_data.text),
                formatted_length=len(formatted_text),
            )

            return TextFormatterOutput(
                formatted_text=formatted_text,
                original_text=input_data.text,
                operation=input_data.operation,
            )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("text_formatting_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(f"Failed to format text: {str(e)}", tool_name=self.name) from e
