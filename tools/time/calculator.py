# 代碼功能說明: 日期計算工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""日期計算工具

日期差值計算、加減運算、工作日計算。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import structlog
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)


class CalculateInput(ToolInput):
    """日期計算輸入參數"""

    operation: str  # 操作類型：add, subtract, diff
    date1: str  # 第一個日期（ISO 8601）
    date2: Optional[str] = None  # 第二個日期（用於 diff 操作）
    days: Optional[int] = None  # 天數（用於 add/subtract）
    months: Optional[int] = None  # 月數（用於 add/subtract）
    years: Optional[int] = None  # 年數（用於 add/subtract）
    workdays_only: bool = False  # 是否只計算工作日（排除週末）


class CalculateOutput(ToolOutput):
    """日期計算輸出結果"""

    result: str  # 計算結果（ISO 8601 格式）
    days_diff: Optional[int] = None  # 天數差值（diff 操作）
    hours_diff: Optional[float] = None  # 小時差值（diff 操作）
    workdays_diff: Optional[int] = None  # 工作日差值（diff 操作，如果 workdays_only=True）


class DateCalculator(BaseTool[CalculateInput, CalculateOutput]):
    """日期計算工具

    日期差值計算、加減運算、工作日計算。
    """

    @property
    def name(self) -> str:
        """工具名稱"""
        return "date_calculator"

    @property
    def description(self) -> str:
        """工具描述"""
        return "日期差值計算、加減運算、工作日計算"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _parse_date(self, date_str: str) -> datetime:
        """
        解析日期字符串

        Args:
            date_str: 日期字符串

        Returns:
            datetime 對象

        Raises:
            ToolValidationError: 日期解析失敗
        """
        try:
            return date_parser.parse(date_str)
        except Exception as e:
            raise ToolValidationError(
                f"Failed to parse date '{date_str}': {str(e)}", field="date1"
            ) from e

    def _count_workdays(self, start: datetime, end: datetime) -> int:
        """
        計算工作日數量（排除週末）

        Args:
            start: 開始日期
            end: 結束日期

        Returns:
            工作日數量
        """
        if start > end:
            start, end = end, start

        workdays = 0
        current = start
        while current <= end:
            # 週一到週五（0=週一，6=週日）
            if current.weekday() < 5:
                workdays += 1
            current += timedelta(days=1)

        return workdays

    async def execute(self, input_data: CalculateInput) -> CalculateOutput:
        """
        執行日期計算工具

        Args:
            input_data: 工具輸入參數

        Returns:
            工具輸出結果

        Raises:
            ToolExecutionError: 工具執行失敗
            ToolValidationError: 輸入參數驗證失敗
        """
        try:
            operation = input_data.operation.lower()

            if operation == "diff":
                # 計算日期差值
                if not input_data.date2:
                    raise ToolValidationError("date2 is required for diff operation", field="date2")

                date1 = self._parse_date(input_data.date1)
                date2 = self._parse_date(input_data.date2)

                # 計算差值
                delta = date2 - date1
                days_diff = delta.days
                hours_diff = delta.total_seconds() / 3600.0

                # 計算工作日差值（如果需要）
                workdays_diff = None
                if input_data.workdays_only:
                    workdays_diff = self._count_workdays(date1, date2)

                return CalculateOutput(
                    result=date2.isoformat(),
                    days_diff=days_diff,
                    hours_diff=hours_diff,
                    workdays_diff=workdays_diff,
                )

            elif operation == "add":
                # 日期加運算
                date1 = self._parse_date(input_data.date1)
                result = date1

                # 加天數
                if input_data.days:
                    result += timedelta(days=input_data.days)

                # 加月數和年數（使用 relativedelta）
                if input_data.months or input_data.years:
                    delta = relativedelta(
                        months=input_data.months or 0, years=input_data.years or 0
                    )
                    result += delta

                # 如果只計算工作日，跳過週末
                if input_data.workdays_only and input_data.days:
                    days_added = 0
                    current = date1
                    while days_added < input_data.days:
                        current += timedelta(days=1)
                        if current.weekday() < 5:  # 週一到週五
                            days_added += 1
                    result = current

                return CalculateOutput(result=result.isoformat())

            elif operation == "subtract":
                # 日期減運算
                date1 = self._parse_date(input_data.date1)
                result = date1

                # 減天數
                if input_data.days:
                    result -= timedelta(days=input_data.days)

                # 減月數和年數（使用 relativedelta）
                if input_data.months or input_data.years:
                    delta = relativedelta(
                        months=input_data.months or 0, years=input_data.years or 0
                    )
                    result -= delta

                # 如果只計算工作日，跳過週末
                if input_data.workdays_only and input_data.days:
                    days_subtracted = 0
                    current = date1
                    while days_subtracted < input_data.days:
                        current -= timedelta(days=1)
                        if current.weekday() < 5:  # 週一到週五
                            days_subtracted += 1
                    result = current

                return CalculateOutput(result=result.isoformat())

            else:
                raise ToolValidationError(
                    f"Invalid operation '{operation}'. Must be 'add', 'subtract', or 'diff'",
                    field="operation",
                )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("calculator_tool_execution_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to execute date calculator tool: {str(e)}", tool_name=self.name
            ) from e
