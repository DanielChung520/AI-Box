# 代碼功能說明: 體積單位轉換工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""體積單位轉換工具

支持升、加侖、毫升、立方米等體積單位轉換。
"""

from __future__ import annotations

from typing import Dict

import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)

# 體積單位轉換係數（以升為基準）
VOLUME_CONVERSION_FACTORS: Dict[str, float] = {
    # 公制單位
    "liter": 1.0,
    "litre": 1.0,  # 英式拼寫
    "l": 1.0,
    "milliliter": 0.001,
    "millilitre": 0.001,  # 英式拼寫
    "ml": 0.001,
    "cubic_meter": 1000.0,
    "cubic_metre": 1000.0,  # 英式拼寫
    "m3": 1000.0,
    "cubic_centimeter": 0.001,
    "cubic_centimetre": 0.001,  # 英式拼寫
    "cm3": 0.001,
    "cc": 0.001,  # 立方厘米的簡寫
    # 英制單位
    "gallon": 3.78541,  # 美制加侖
    "gal": 3.78541,
    "imperial_gallon": 4.54609,  # 英制加侖
    "quart": 0.946353,  # 美制夸脫
    "qt": 0.946353,
    "pint": 0.473176,  # 美制品脫
    "pt": 0.473176,
    "cup": 0.236588,  # 美制杯
    "fluid_ounce": 0.0295735,  # 美制液體盎司
    "fl_oz": 0.0295735,
    "tablespoon": 0.0147868,  # 美制湯匙
    "tbsp": 0.0147868,
    "teaspoon": 0.00492892,  # 美制茶匙
    "tsp": 0.00492892,
    # 其他單位
    "barrel": 158.987,  # 美制桶（石油）
    "bbl": 158.987,
}


class VolumeInput(ToolInput):
    """體積單位轉換輸入參數"""

    value: float  # 數值
    from_unit: str  # 源單位（如 "liter", "gallon", "milliliter"）
    to_unit: str  # 目標單位


class VolumeOutput(ToolOutput):
    """體積單位轉換輸出結果"""

    value: float  # 轉換後的數值
    from_unit: str  # 源單位
    to_unit: str  # 目標單位
    original_value: float  # 原始數值


class VolumeConverter(BaseTool[VolumeInput, VolumeOutput]):
    """體積單位轉換工具

    支持升、加侖、毫升、立方米等體積單位轉換。
    """

    @property
    def name(self) -> str:
        """工具名稱"""
        return "volume_converter"

    @property
    def description(self) -> str:
        """工具描述"""
        return "體積單位轉換工具，支持升、加侖、毫升、立方米等單位"

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
        if normalized not in VOLUME_CONVERSION_FACTORS:
            supported_units = ", ".join(sorted(VOLUME_CONVERSION_FACTORS.keys()))
            raise ToolValidationError(
                f"Unsupported volume unit: {unit}. Supported units: {supported_units}",
                field="from_unit" if unit == unit else "to_unit",
            )

    async def execute(self, input_data: VolumeInput) -> VolumeOutput:
        """
        執行體積單位轉換

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
            from_factor = VOLUME_CONVERSION_FACTORS[from_unit]
            to_factor = VOLUME_CONVERSION_FACTORS[to_unit]

            # 轉換：先轉為升，再轉為目標單位
            value_in_liters = input_data.value * from_factor
            converted_value = value_in_liters / to_factor

            logger.debug(
                "volume_conversion_completed",
                original_value=input_data.value,
                from_unit=from_unit,
                to_unit=to_unit,
                converted_value=converted_value,
            )

            return VolumeOutput(
                value=converted_value,
                from_unit=input_data.from_unit,
                to_unit=input_data.to_unit,
                original_value=input_data.value,
            )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("volume_conversion_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to convert volume: {str(e)}", tool_name=self.name
            ) from e
