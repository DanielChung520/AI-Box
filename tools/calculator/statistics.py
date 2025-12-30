# 代碼功能說明: 統計計算工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""統計計算工具

支持平均值、中位數、眾數、標準差、方差等統計計算。
"""

from __future__ import annotations

import statistics
from typing import List, Optional

import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)

# 支持的統計操作
SUPPORTED_OPERATIONS = {
    "mean",  # 平均值
    "median",  # 中位數
    "mode",  # 眾數
    "std",  # 標準差
    "stdev",  # 標準差（別名）
    "variance",  # 方差
    "min",  # 最小值
    "max",  # 最大值
    "range",  # 範圍（最大值 - 最小值）
    "sum",  # 總和
    "count",  # 數量
    "percentile",  # 百分位數
}


class StatisticsInput(ToolInput):
    """統計計算輸入參數"""

    data: List[float]  # 數值列表
    operation: str  # 統計操作類型（如 "mean", "median", "std"）
    percentile: Optional[float] = None  # 百分位數（0-100），僅用於 percentile 操作


class StatisticsOutput(ToolOutput):
    """統計計算輸出結果"""

    result: float  # 統計結果
    operation: str  # 操作類型
    data_count: int  # 數據點數量


class StatisticsCalculator(BaseTool[StatisticsInput, StatisticsOutput]):
    """統計計算工具

    支持平均值、中位數、眾數、標準差、方差等統計計算。
    """

    @property
    def name(self) -> str:
        """工具名稱"""
        return "statistics_calculator"

    @property
    def description(self) -> str:
        """工具描述"""
        return "統計計算工具，支持平均值、中位數、眾數、標準差、方差等統計計算"

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

    def _calculate_statistic(
        self, data: List[float], operation: str, percentile: Optional[float] = None
    ) -> float:
        """
        計算統計值

        Args:
            data: 數據列表
            operation: 操作類型
            percentile: 百分位數（0-100）

        Returns:
            統計結果

        Raises:
            ToolValidationError: 計算失敗
        """
        operation_lower = operation.lower()

        try:
            if operation_lower == "mean":
                return statistics.mean(data)
            elif operation_lower == "median":
                return statistics.median(data)
            elif operation_lower == "mode":
                return float(statistics.mode(data))
            elif operation_lower in ("std", "stdev"):
                if len(data) < 2:
                    raise ToolValidationError(
                        "At least 2 data points required for standard deviation",
                        field="data",
                    )
                return statistics.stdev(data)
            elif operation_lower == "variance":
                if len(data) < 2:
                    raise ToolValidationError(
                        "At least 2 data points required for variance", field="data"
                    )
                return statistics.variance(data)
            elif operation_lower == "min":
                return min(data)
            elif operation_lower == "max":
                return max(data)
            elif operation_lower == "range":
                return max(data) - min(data)
            elif operation_lower == "sum":
                return sum(data)
            elif operation_lower == "count":
                return float(len(data))
            elif operation_lower == "percentile":
                if percentile is None:
                    raise ToolValidationError(
                        "percentile parameter is required for percentile operation",
                        field="percentile",
                    )
                if not 0 <= percentile <= 100:
                    raise ToolValidationError(
                        "percentile must be between 0 and 100", field="percentile"
                    )
                # 使用 statistics.quantiles 計算百分位數
                quantiles = statistics.quantiles(data, n=100, method="inclusive")
                index = int(percentile)
                if index >= len(quantiles):
                    index = len(quantiles) - 1
                return quantiles[index]
            else:
                raise ToolValidationError(f"Unknown operation: {operation}", field="operation")

        except statistics.StatisticsError as e:
            raise ToolValidationError(
                f"Statistics calculation failed: {str(e)}", field="data"
            ) from e
        except Exception as e:
            raise ToolValidationError(f"Calculation failed: {str(e)}", field="data") from e

    async def execute(self, input_data: StatisticsInput) -> StatisticsOutput:
        """
        執行統計計算

        Args:
            input_data: 工具輸入參數

        Returns:
            工具輸出結果

        Raises:
            ToolExecutionError: 工具執行失敗
            ToolValidationError: 輸入參數驗證失敗
        """
        try:
            # 驗證數據
            if not input_data.data:
                raise ToolValidationError("Data list cannot be empty", field="data")

            # 驗證操作類型
            self._validate_operation(input_data.operation)

            # 計算統計值
            result = self._calculate_statistic(
                input_data.data, input_data.operation, input_data.percentile
            )

            logger.debug(
                "statistics_calculation_completed",
                operation=input_data.operation,
                data_count=len(input_data.data),
                result=result,
            )

            return StatisticsOutput(
                result=result,
                operation=input_data.operation,
                data_count=len(input_data.data),
            )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("statistics_calculation_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to calculate statistics: {str(e)}", tool_name=self.name
            ) from e
