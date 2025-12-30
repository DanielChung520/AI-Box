# 代碼功能說明: 重量單位轉換工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""重量單位轉換工具

支持公斤、磅、盎司、克等重量單位轉換。
"""

from __future__ import annotations

from typing import Dict

import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)

# 重量單位轉換係數（以公斤為基準）
WEIGHT_CONVERSION_FACTORS: Dict[str, float] = {
    # 公制單位
    "kilogram": 1.0,
    "kg": 1.0,
    "gram": 0.001,
    "g": 0.001,
    "milligram": 0.000001,
    "mg": 0.000001,
    "metric_ton": 1000.0,
    "tonne": 1000.0,
    "t": 1000.0,
    # 英制單位
    "pound": 0.453592,
    "lb": 0.453592,
    "ounce": 0.0283495,
    "oz": 0.0283495,
    "stone": 6.35029,
    "st": 6.35029,
    "ton": 1016.05,  # 英噸（長噸）
    "short_ton": 907.185,  # 美噸（短噸）
    # 其他單位
    "carat": 0.0002,  # 克拉
    "ct": 0.0002,
}


class WeightInput(ToolInput):
    """重量單位轉換輸入參數"""

    value: float  # 數值
    from_unit: str  # 源單位（如 "kilogram", "pound", "ounce"）
    to_unit: str  # 目標單位


class WeightOutput(ToolOutput):
    """重量單位轉換輸出結果"""

    value: float  # 轉換後的數值
    from_unit: str  # 源單位
    to_unit: str  # 目標單位
    original_value: float  # 原始數值


class WeightConverter(BaseTool[WeightInput, WeightOutput]):
    """重量單位轉換工具

    支持公斤、磅、盎司、克等重量單位轉換。
    """

    @property
    def name(self) -> str:
        """工具名稱"""
        return "weight_converter"

    @property
    def description(self) -> str:
        """工具描述"""
        return "重量單位轉換工具，支持公斤、磅、盎司、克等單位"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _normalize_unit(self, unit: str) -> str:
        """
        標準化單位名稱（轉為小寫）

        Args:
            unit: 單位名稱

        Returns:
            標準化的單位名稱
        """
        return unit.lower().strip()

    def _validate_unit(self, unit: str) -> None:
        """
        驗證單位是否支持

        Args:
            unit: 單位名稱

        Raises:
            ToolValidationError: 單位不支持
        """
        normalized = self._normalize_unit(unit)
        if normalized not in WEIGHT_CONVERSION_FACTORS:
            supported_units = ", ".join(sorted(WEIGHT_CONVERSION_FACTORS.keys()))
            raise ToolValidationError(
                f"Unsupported weight unit: {unit}. Supported units: {supported_units}",
                field="from_unit" if unit == unit else "to_unit",
            )

    async def execute(self, input_data: WeightInput) -> WeightOutput:
        """
        執行重量單位轉換

        Args:
            input_data: 工具輸入參數

        Returns:
            工具輸出結果

        Raises:
            ToolExecutionError: 工具執行失敗
            ToolValidationError: 輸入參數驗證失敗
        """
        try:
            # 驗證單位
            from_unit = self._normalize_unit(input_data.from_unit)
            to_unit = self._normalize_unit(input_data.to_unit)

            self._validate_unit(from_unit)
            self._validate_unit(to_unit)

            # 獲取轉換係數
            from_factor = WEIGHT_CONVERSION_FACTORS[from_unit]
            to_factor = WEIGHT_CONVERSION_FACTORS[to_unit]

            # 轉換：先轉為公斤，再轉為目標單位
            value_in_kg = input_data.value * from_factor
            converted_value = value_in_kg / to_factor

            logger.debug(
                "weight_conversion_completed",
                original_value=input_data.value,
                from_unit=from_unit,
                to_unit=to_unit,
                converted_value=converted_value,
            )

            return WeightOutput(
                value=converted_value,
                from_unit=input_data.from_unit,
                to_unit=input_data.to_unit,
                original_value=input_data.value,
            )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("weight_conversion_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to convert weight: {str(e)}", tool_name=self.name
            ) from e
