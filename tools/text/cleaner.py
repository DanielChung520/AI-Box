# 代碼功能說明: 文本清理工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""文本清理工具

支持去除空白字符、特殊字符、重複字符、HTML 標籤等清理操作。
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import List, Optional

import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)

# 支持的操作類型
SUPPORTED_OPERATIONS = {
    "remove_whitespace",  # 去除所有空白字符
    "remove_newlines",  # 去除換行符
    "remove_tabs",  # 去除制表符
    "remove_special_chars",  # 去除特殊字符
    "remove_html_tags",  # 去除 HTML 標籤
    "remove_duplicates",  # 去除重複字符
    "normalize_whitespace",  # 標準化空白字符（多個空白合併為一個）
}


class TextCleanerInput(ToolInput):
    """文本清理輸入參數"""

    text: str  # 輸入文本
    operation: str  # 清理操作類型
    keep_chars: Optional[str] = None  # 保留的字符（用於 remove_special_chars 操作）


class TextCleanerOutput(ToolOutput):
    """文本清理輸出結果"""

    cleaned_text: str  # 清理後的文本
    original_text: str  # 原始文本
    operation: str  # 操作類型
    removed_count: Optional[int] = None  # 移除的字符數量（如果可計算）


class HTMLTagRemover(HTMLParser):
    """HTML 標籤移除器"""

    def __init__(self) -> None:
        """初始化 HTML 標籤移除器"""
        super().__init__()
        self.text: List[str] = []

    def handle_data(self, data: str) -> None:
        """處理文本數據"""
        self.text.append(data)

    def get_text(self) -> str:
        """獲取清理後的文本"""
        return "".join(self.text)


class TextCleaner(BaseTool[TextCleanerInput, TextCleanerOutput]):
    """文本清理工具

    支持去除空白字符、特殊字符、重複字符、HTML 標籤等清理操作。
    """

    @property
    def name(self) -> str:
        """工具名稱"""
        return "text_cleaner"

    @property
    def description(self) -> str:
        """工具描述"""
        return "文本清理工具，支持去除空白字符、特殊字符、重複字符、HTML 標籤等清理操作"

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

    def _clean_text(
        self, text: str, operation: str, keep_chars: Optional[str] = None
    ) -> tuple[str, Optional[int]]:
        """
        清理文本

        Args:
            text: 輸入文本
            operation: 操作類型
            keep_chars: 保留的字符

        Returns:
            (清理後的文本, 移除的字符數量)
        """
        operation_lower = operation.lower()
        original_length = len(text)

        if operation_lower == "remove_whitespace":
            cleaned = re.sub(r"\s+", "", text)
            return cleaned, original_length - len(cleaned)

        elif operation_lower == "remove_newlines":
            cleaned = text.replace("\n", "").replace("\r", "")
            return cleaned, original_length - len(cleaned)

        elif operation_lower == "remove_tabs":
            cleaned = text.replace("\t", "")
            return cleaned, original_length - len(cleaned)

        elif operation_lower == "remove_special_chars":
            # 保留字母、數字、空白和指定字符
            if keep_chars:
                pattern = f"[^a-zA-Z0-9\\s{re.escape(keep_chars)}]"
            else:
                pattern = r"[^a-zA-Z0-9\s]"
            cleaned = re.sub(pattern, "", text)
            return cleaned, original_length - len(cleaned)

        elif operation_lower == "remove_html_tags":
            parser = HTMLTagRemover()
            parser.feed(text)
            cleaned = parser.get_text()
            return cleaned, original_length - len(cleaned)

        elif operation_lower == "remove_duplicates":
            # 去除連續重複字符
            cleaned = re.sub(r"(.)\1+", r"\1", text)
            return cleaned, original_length - len(cleaned)

        elif operation_lower == "normalize_whitespace":
            # 將多個空白字符合併為一個空格
            cleaned = re.sub(r"\s+", " ", text).strip()
            return cleaned, original_length - len(cleaned)

        else:
            raise ToolValidationError(f"Unknown operation: {operation}", field="operation")

    async def execute(self, input_data: TextCleanerInput) -> TextCleanerOutput:
        """
        執行文本清理

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

            # 清理文本
            cleaned_text, removed_count = self._clean_text(
                input_data.text, input_data.operation, input_data.keep_chars
            )

            logger.debug(
                "text_cleaning_completed",
                operation=input_data.operation,
                original_length=len(input_data.text),
                cleaned_length=len(cleaned_text),
                removed_count=removed_count,
            )

            return TextCleanerOutput(
                cleaned_text=cleaned_text,
                original_text=input_data.text,
                operation=input_data.operation,
                removed_count=removed_count,
            )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("text_cleaning_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(f"Failed to clean text: {str(e)}", tool_name=self.name) from e
