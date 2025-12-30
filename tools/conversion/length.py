# 代碼功能說明: 長度單位轉換工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""長度單位轉換工具

支持米、英尺、英里、公里、厘米、毫米等長度單位轉換。
"""

from __future__ import annotations

from typing import Dict

import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)

# 長度單位轉換係數（以米為基準）
LENGTH_CONVERSION_FACTORS: Dict[str, float] = {
    # 公制單位
    "meter": 1.0,
    "metre": 1.0,  # 英式拼寫
    "m": 1.0,
    "kilometer": 1000.0,
    "kilometre": 1000.0,  # 英式拼寫
    "km": 1000.0,
    "centimeter": 0.01,
    "centimetre": 0.01,  # 英式拼寫
    "cm": 0.01,
    "millimeter": 0.001,
    "millimetre": 0.001,  # 英式拼寫
    "mm": 0.001,
    "decimeter": 0.1,
    "dm": 0.1,
    # 英制單位
    "foot": 0.3048,
    "feet": 0.3048,
    "ft": 0.3048,
    "inch": 0.0254,
    "in": 0.0254,
    "yard": 0.9144,
    "yd": 0.9144,
    "mile": 1609.344,
    "mi": 1609.344,
    "nautical_mile": 1852.0,
    "nmi": 1852.0,
    # 其他單位
    "light_year": 9.461e15,  # 光年
    "parsec": 3.086e16,  # 秒差距
}


class LengthInput(ToolInput):
    """長度單位轉換輸入參數"""

    value: float  # 數值
    from_unit: str  # 源單位（如 "meter", "foot", "mile"）
    to_unit: str  # 目標單位


class LengthOutput(ToolOutput):
    """長度單位轉換輸出結果"""

    value: float  # 轉換後的數值
    from_unit: str  # 源單位
    to_unit: str  # 目標單位
    original_value: float  # 原始數值


class LengthConverter(BaseTool[LengthInput, LengthOutput]):
    """長度單位轉換工具

    支持米、英尺、英里、公里、厘米、毫米等長度單位轉換。
    """

    @property
    def name(self) -> str:
        """工具名稱"""
        return "length_converter"

    @property
    def description(self) -> str:
        """工具描述"""
        return "長度單位轉換工具，支持米、英尺、英里、公里、厘米、毫米等單位"

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
        if normalized not in LENGTH_CONVERSION_FACTORS:
            supported_units = ", ".join(sorted(LENGTH_CONVERSION_FACTORS.keys()))
            raise ToolValidationError(
                f"Unsupported length unit: {unit}. Supported units: {supported_units}",
                field="from_unit" if unit == unit else "to_unit",
            )

    async def execute(self, input_data: LengthInput) -> LengthOutput:
        """
        執行長度單位轉換

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
            from_factor = LENGTH_CONVERSION_FACTORS[from_unit]
            to_factor = LENGTH_CONVERSION_FACTORS[to_unit]

            # 轉換：先轉為米，再轉為目標單位
            value_in_meters = input_data.value * from_factor
            converted_value = value_in_meters / to_factor

            logger.debug(
                "length_conversion_completed",
                original_value=input_data.value,
                from_unit=from_unit,
                to_unit=to_unit,
                converted_value=converted_value,
            )

            return LengthOutput(
                value=converted_value,
                from_unit=input_data.from_unit,
                to_unit=input_data.to_unit,
                original_value=input_data.value,
            )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("length_conversion_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to convert length: {str(e)}", tool_name=self.name
            ) from e
