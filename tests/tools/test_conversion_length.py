# 代碼功能說明: 長度單位轉換工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""長度單位轉換工具測試"""

from __future__ import annotations

import pytest

from tools.conversion import LengthConverter, LengthInput, LengthOutput
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestLengthConverter:
    """長度單位轉換工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return LengthConverter()

    @pytest.mark.asyncio
    async def test_meter_to_kilometer(self, tool):
        """測試米轉公里"""
        input_data = LengthInput(value=1000.0, from_unit="meter", to_unit="kilometer")
        result = await tool.execute(input_data)

        assert isinstance(result, LengthOutput)
        assert result.value == 1.0
        assert result.from_unit == "meter"
        assert result.to_unit == "kilometer"
        assert result.original_value == 1000.0

    @pytest.mark.asyncio
    async def test_foot_to_meter(self, tool):
        """測試英尺轉米"""
        input_data = LengthInput(value=1.0, from_unit="foot", to_unit="meter")
        result = await tool.execute(input_data)

        assert isinstance(result, LengthOutput)
        assert abs(result.value - 0.3048) < 0.0001

    @pytest.mark.asyncio
    async def test_mile_to_kilometer(self, tool):
        """測試英里轉公里"""
        input_data = LengthInput(value=1.0, from_unit="mile", to_unit="kilometer")
        result = await tool.execute(input_data)

        assert isinstance(result, LengthOutput)
        assert abs(result.value - 1.609344) < 0.0001

    @pytest.mark.asyncio
    async def test_invalid_unit(self, tool):
        """測試無效單位"""
        input_data = LengthInput(value=1.0, from_unit="invalid", to_unit="meter")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_same_unit(self, tool):
        """測試相同單位轉換"""
        input_data = LengthInput(value=100.0, from_unit="meter", to_unit="meter")
        result = await tool.execute(input_data)

        assert result.value == 100.0
