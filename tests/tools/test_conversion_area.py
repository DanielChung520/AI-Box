# 代碼功能說明: 面積單位轉換工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""面積單位轉換工具測試"""

from __future__ import annotations

import pytest

from tools.conversion import AreaConverter, AreaInput, AreaOutput
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestAreaConverter:
    """面積單位轉換工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return AreaConverter()

    @pytest.mark.asyncio
    async def test_square_meter_to_square_kilometer(self, tool):
        """測試平方米轉平方公里"""
        input_data = AreaInput(
            value=1000000.0, from_unit="square_meter", to_unit="square_kilometer"
        )
        result = await tool.execute(input_data)

        assert isinstance(result, AreaOutput)
        assert result.value == 1.0
        assert result.from_unit == "square_meter"
        assert result.to_unit == "square_kilometer"
        assert result.original_value == 1000000.0

    @pytest.mark.asyncio
    async def test_square_foot_to_square_meter(self, tool):
        """測試平方英尺轉平方米"""
        input_data = AreaInput(value=1.0, from_unit="square_foot", to_unit="square_meter")
        result = await tool.execute(input_data)

        assert isinstance(result, AreaOutput)
        assert abs(result.value - 0.092903) < 0.0001

    @pytest.mark.asyncio
    async def test_hectare_to_square_meter(self, tool):
        """測試公頃轉平方米"""
        input_data = AreaInput(value=1.0, from_unit="hectare", to_unit="square_meter")
        result = await tool.execute(input_data)

        assert isinstance(result, AreaOutput)
        assert result.value == 10000.0

    @pytest.mark.asyncio
    async def test_acre_to_square_meter(self, tool):
        """測試英畝轉平方米"""
        input_data = AreaInput(value=1.0, from_unit="acre", to_unit="square_meter")
        result = await tool.execute(input_data)

        assert isinstance(result, AreaOutput)
        assert abs(result.value - 4046.86) < 0.1

    @pytest.mark.asyncio
    async def test_ping_to_square_meter(self, tool):
        """測試坪轉平方米（台灣常用單位）"""
        input_data = AreaInput(value=1.0, from_unit="ping", to_unit="square_meter")
        result = await tool.execute(input_data)

        assert isinstance(result, AreaOutput)
        assert abs(result.value - 3.30579) < 0.0001

    @pytest.mark.asyncio
    async def test_invalid_unit(self, tool):
        """測試無效單位"""
        input_data = AreaInput(value=1.0, from_unit="invalid", to_unit="square_meter")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_same_unit(self, tool):
        """測試相同單位轉換"""
        input_data = AreaInput(value=100.0, from_unit="square_meter", to_unit="square_meter")
        result = await tool.execute(input_data)

        assert result.value == 100.0

    @pytest.mark.asyncio
    async def test_unit_normalization(self, tool):
        """測試單位標準化（大小寫不敏感）"""
        input_data = AreaInput(value=10000.0, from_unit="M2", to_unit="HA")
        result = await tool.execute(input_data)

        assert isinstance(result, AreaOutput)
        assert result.value == 1.0

    @pytest.mark.asyncio
    async def test_zero_value(self, tool):
        """測試零值"""
        input_data = AreaInput(value=0.0, from_unit="square_meter", to_unit="square_kilometer")
        result = await tool.execute(input_data)

        assert result.value == 0.0

    @pytest.mark.asyncio
    async def test_square_mile_to_square_kilometer(self, tool):
        """測試平方英里轉平方公里"""
        input_data = AreaInput(value=1.0, from_unit="square_mile", to_unit="square_kilometer")
        result = await tool.execute(input_data)

        assert isinstance(result, AreaOutput)
        assert abs(result.value - 2.589988) < 0.1
