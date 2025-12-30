# 代碼功能說明: 溫度單位轉換工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""溫度單位轉換工具測試"""

from __future__ import annotations

import pytest

from tools.conversion import TemperatureConverter, TemperatureInput, TemperatureOutput
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestTemperatureConverter:
    """溫度單位轉換工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return TemperatureConverter()

    @pytest.mark.asyncio
    async def test_celsius_to_fahrenheit(self, tool):
        """測試攝氏度轉華氏度"""
        input_data = TemperatureInput(value=0.0, from_unit="celsius", to_unit="fahrenheit")
        result = await tool.execute(input_data)

        assert isinstance(result, TemperatureOutput)
        assert abs(result.value - 32.0) < 0.01

    @pytest.mark.asyncio
    async def test_fahrenheit_to_celsius(self, tool):
        """測試華氏度轉攝氏度"""
        input_data = TemperatureInput(value=32.0, from_unit="fahrenheit", to_unit="celsius")
        result = await tool.execute(input_data)

        assert isinstance(result, TemperatureOutput)
        assert abs(result.value - 0.0) < 0.01

    @pytest.mark.asyncio
    async def test_celsius_to_kelvin(self, tool):
        """測試攝氏度轉開爾文"""
        input_data = TemperatureInput(value=0.0, from_unit="celsius", to_unit="kelvin")
        result = await tool.execute(input_data)

        assert isinstance(result, TemperatureOutput)
        assert abs(result.value - 273.15) < 0.01

    @pytest.mark.asyncio
    async def test_invalid_unit(self, tool):
        """測試無效單位"""
        input_data = TemperatureInput(value=0.0, from_unit="invalid", to_unit="celsius")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)
