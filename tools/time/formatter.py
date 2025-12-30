# 代碼功能說明: 日期格式化工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""日期格式化工具

日期格式化和解析，支持多種語言環境。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import structlog
from dateutil import parser as date_parser

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)


class FormatInput(ToolInput):
    """日期格式化輸入參數"""

    date: str  # 日期字符串或 ISO 8601 格式
    format: str  # 目標格式（如 "%Y年%m月%d日"）
    source_format: Optional[str] = None  # 源格式（如果 date 不是 ISO 8601）


class FormatOutput(ToolOutput):
    """日期格式化輸出結果"""

    formatted: str  # 格式化後的日期字符串
    iso_format: str  # ISO 8601 格式
    timestamp: float  # Unix 時間戳


class DateFormatter(BaseTool[FormatInput, FormatOutput]):
    """日期格式化工具

    日期格式化和解析。
    """

    @property
    def name(self) -> str:
        """工具名稱"""
        return "date_formatter"

    @property
    def description(self) -> str:
        """工具描述"""
        return "日期格式化和解析，支持多種語言環境"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _parse_date(self, date_str: str, source_format: Optional[str] = None) -> datetime:
        """
        解析日期字符串

        Args:
            date_str: 日期字符串
            source_format: 源格式（可選）

        Returns:
            datetime 對象

        Raises:
            ToolValidationError: 日期解析失敗
        """
        try:
            if source_format:
                # 使用指定格式解析
                return datetime.strptime(date_str, source_format)
            else:
                # 使用 dateutil 自動解析（支持多種格式）
                return date_parser.parse(date_str)
        except Exception as e:
            raise ToolValidationError(
                f"Failed to parse date '{date_str}' with format '{source_format}': {str(e)}",
                field="date",
            ) from e

    async def execute(self, input_data: FormatInput) -> FormatOutput:
        """
        執行日期格式化工具

        Args:
            input_data: 工具輸入參數

        Returns:
            工具輸出結果

        Raises:
            ToolExecutionError: 工具執行失敗
            ToolValidationError: 輸入參數驗證失敗
        """
        try:
            # 解析日期
            dt = self._parse_date(input_data.date, input_data.source_format)

            # 格式化日期
            formatted = dt.strftime(input_data.format)

            # ISO 8601 格式
            iso_formatted = dt.isoformat()

            # Unix 時間戳
            timestamp = dt.timestamp()

            return FormatOutput(
                formatted=formatted,
                iso_format=iso_formatted,
                timestamp=timestamp,
            )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("formatter_tool_execution_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to execute date formatter tool: {str(e)}", tool_name=self.name
            ) from e
