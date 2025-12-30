# 代碼功能說明: 溫度單位轉換工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""溫度單位轉換工具

支持攝氏度、華氏度、開爾文等溫度單位轉換。
"""

from __future__ import annotations

from typing import Dict

import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)

# 支持的溫度單位
SUPPORTED_TEMPERATURE_UNITS = {"celsius", "fahrenheit", "kelvin", "c", "f", "k"}


class TemperatureInput(ToolInput):
    """溫度單位轉換輸入參數"""

    value: float  # 數值
    from_unit: str  # 源單位（如 "celsius", "fahrenheit", "kelvin"）
    to_unit: str  # 目標單位


class TemperatureOutput(ToolOutput):
    """溫度單位轉換輸出結果"""

    value: float  # 轉換後的數值
    from_unit: str  # 源單位
    to_unit: str  # 目標單位
    original_value: float  # 原始數值


class TemperatureConverter(BaseTool[TemperatureInput, TemperatureOutput]):
    """溫度單位轉換工具

    支持攝氏度、華氏度、開爾文等溫度單位轉換。
    """

    @property
    def name(self) -> str:
        """工具名稱"""
        return "temperature_converter"

    @property
    def description(self) -> str:
        """工具描述"""
        return "溫度單位轉換工具，支持攝氏度、華氏度、開爾文等單位"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _normalize_unit(self, unit: str) -> str:
        """
        標準化單位名稱

        Args:
            unit: 單位名稱

        Returns:
            標準化的單位名稱
        """
        unit_lower = unit.lower().strip()
        # 映射簡寫到完整名稱
        unit_map: Dict[str, str] = {
            "c": "celsius",
            "f": "fahrenheit",
            "k": "kelvin",
        }
        return unit_map.get(unit_lower, unit_lower)

    def _validate_unit(self, unit: str) -> None:
        """
        驗證單位是否支持

        Args:
            unit: 單位名稱

        Raises:
            ToolValidationError: 單位不支持
        """
        normalized = self._normalize_unit(unit)
        if normalized not in SUPPORTED_TEMPERATURE_UNITS:
            supported_units = ", ".join(sorted(SUPPORTED_TEMPERATURE_UNITS))
            raise ToolValidationError(
                f"Unsupported temperature unit: {unit}. Supported units: {supported_units}",
                field="from_unit" if unit == unit else "to_unit",
            )

    def _to_celsius(self, value: float, from_unit: str) -> float:
        """
        將溫度轉換為攝氏度

        Args:
            value: 溫度值
            from_unit: 源單位

        Returns:
            攝氏度值
        """
        normalized = self._normalize_unit(from_unit)
        if normalized == "celsius":
            return value
        elif normalized == "fahrenheit":
            return (value - 32) * 5 / 9
        elif normalized == "kelvin":
            return value - 273.15
        else:
            raise ToolValidationError(f"Unknown temperature unit: {from_unit}")

    def _from_celsius(self, value: float, to_unit: str) -> float:
        """
        從攝氏度轉換為目標單位

        Args:
            value: 攝氏度值
            to_unit: 目標單位

        Returns:
            目標單位的溫度值
        """
        normalized = self._normalize_unit(to_unit)
        if normalized == "celsius":
            return value
        elif normalized == "fahrenheit":
            return value * 9 / 5 + 32
        elif normalized == "kelvin":
            return value + 273.15
        else:
            raise ToolValidationError(f"Unknown temperature unit: {to_unit}")

    async def execute(self, input_data: TemperatureInput) -> TemperatureOutput:
        """
        執行溫度單位轉換

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

            # 轉換：先轉為攝氏度，再轉為目標單位
            value_in_celsius = self._to_celsius(input_data.value, from_unit)
            converted_value = self._from_celsius(value_in_celsius, to_unit)

            logger.debug(
                "temperature_conversion_completed",
                original_value=input_data.value,
                from_unit=from_unit,
                to_unit=to_unit,
                converted_value=converted_value,
            )

            return TemperatureOutput(
                value=converted_value,
                from_unit=input_data.from_unit,
                to_unit=input_data.to_unit,
                original_value=input_data.value,
            )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("temperature_conversion_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to convert temperature: {str(e)}", tool_name=self.name
            ) from e
