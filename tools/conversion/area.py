# 代碼功能說明: 面積單位轉換工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""面積單位轉換工具

支持平方米、平方英尺、公頃、英畝等面積單位轉換。
"""

from __future__ import annotations

from typing import Dict

import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)

# 面積單位轉換係數（以平方米為基準）
AREA_CONVERSION_FACTORS: Dict[str, float] = {
    # 公制單位
    "square_meter": 1.0,
    "square_metre": 1.0,  # 英式拼寫
    "m2": 1.0,
    "square_kilometer": 1000000.0,
    "square_kilometre": 1000000.0,  # 英式拼寫
    "km2": 1000000.0,
    "square_centimeter": 0.0001,
    "square_centimetre": 0.0001,  # 英式拼寫
    "cm2": 0.0001,
    "hectare": 10000.0,  # 公頃
    "ha": 10000.0,
    "are": 100.0,  # 公畝
    "a": 100.0,
    # 英制單位
    "square_foot": 0.092903,
    "square_feet": 0.092903,
    "ft2": 0.092903,
    "square_inch": 0.00064516,
    "in2": 0.00064516,
    "square_yard": 0.836127,
    "yd2": 0.836127,
    "square_mile": 2589988.11,
    "mi2": 2589988.11,
    "acre": 4046.86,  # 英畝
    "ac": 4046.86,
    # 其他單位
    "ping": 3.30579,  # 坪（台灣常用）
}


class AreaInput(ToolInput):
    """面積單位轉換輸入參數"""

    value: float  # 數值
    from_unit: str  # 源單位（如 "square_meter", "square_foot", "hectare"）
    to_unit: str  # 目標單位


class AreaOutput(ToolOutput):
    """面積單位轉換輸出結果"""

    value: float  # 轉換後的數值
    from_unit: str  # 源單位
    to_unit: str  # 目標單位
    original_value: float  # 原始數值


class AreaConverter(BaseTool[AreaInput, AreaOutput]):
    """面積單位轉換工具

    支持平方米、平方英尺、公頃、英畝等面積單位轉換。
    """

    @property
    def name(self) -> str:
        """工具名稱"""
        return "area_converter"

    @property
    def description(self) -> str:
        """工具描述"""
        return "面積單位轉換工具，支持平方米、平方英尺、公頃、英畝等單位"

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
        if normalized not in AREA_CONVERSION_FACTORS:
            supported_units = ", ".join(sorted(AREA_CONVERSION_FACTORS.keys()))
            raise ToolValidationError(
                f"Unsupported area unit: {unit}. Supported units: {supported_units}",
                field="from_unit" if unit == unit else "to_unit",
            )

    async def execute(self, input_data: AreaInput) -> AreaOutput:
        """
        執行面積單位轉換

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
            from_factor = AREA_CONVERSION_FACTORS[from_unit]
            to_factor = AREA_CONVERSION_FACTORS[to_unit]

            # 轉換：先轉為平方米，再轉為目標單位
            value_in_square_meters = input_data.value * from_factor
            converted_value = value_in_square_meters / to_factor

            logger.debug(
                "area_conversion_completed",
                original_value=input_data.value,
                from_unit=from_unit,
                to_unit=to_unit,
                converted_value=converted_value,
            )

            return AreaOutput(
                value=converted_value,
                from_unit=input_data.from_unit,
                to_unit=input_data.to_unit,
                original_value=input_data.value,
            )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("area_conversion_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to convert area: {str(e)}", tool_name=self.name
            ) from e
