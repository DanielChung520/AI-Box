# 代碼功能說明: 體積單位轉換工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""體積單位轉換工具測試"""

from __future__ import annotations

import pytest

from tools.conversion import VolumeConverter, VolumeInput, VolumeOutput
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestVolumeConverter:
    """體積單位轉換工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return VolumeConverter()

    @pytest.mark.asyncio
    async def test_liter_to_milliliter(self, tool):
        """測試升轉毫升"""
        input_data = VolumeInput(value=1.0, from_unit="liter", to_unit="milliliter")
        result = await tool.execute(input_data)

        assert isinstance(result, VolumeOutput)
        assert result.value == 1000.0
        assert result.from_unit == "liter"
        assert result.to_unit == "milliliter"
        assert result.original_value == 1.0

    @pytest.mark.asyncio
    async def test_gallon_to_liter(self, tool):
        """測試加侖轉升"""
        input_data = VolumeInput(value=1.0, from_unit="gallon", to_unit="liter")
        result = await tool.execute(input_data)

        assert isinstance(result, VolumeOutput)
        assert abs(result.value - 3.78541) < 0.0001

    @pytest.mark.asyncio
    async def test_cubic_meter_to_liter(self, tool):
        """測試立方米轉升"""
        input_data = VolumeInput(value=1.0, from_unit="cubic_meter", to_unit="liter")
        result = await tool.execute(input_data)

        assert isinstance(result, VolumeOutput)
        assert result.value == 1000.0

    @pytest.mark.asyncio
    async def test_fluid_ounce_to_milliliter(self, tool):
        """測試液體盎司轉毫升"""
        input_data = VolumeInput(value=1.0, from_unit="fluid_ounce", to_unit="milliliter")
        result = await tool.execute(input_data)

        assert isinstance(result, VolumeOutput)
        assert abs(result.value - 29.5735) < 0.0001

    @pytest.mark.asyncio
    async def test_cup_to_milliliter(self, tool):
        """測試杯轉毫升"""
        input_data = VolumeInput(value=1.0, from_unit="cup", to_unit="milliliter")
        result = await tool.execute(input_data)

        assert isinstance(result, VolumeOutput)
        assert abs(result.value - 236.588) < 0.1

    @pytest.mark.asyncio
    async def test_invalid_unit(self, tool):
        """測試無效單位"""
        input_data = VolumeInput(value=1.0, from_unit="invalid", to_unit="liter")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_same_unit(self, tool):
        """測試相同單位轉換"""
        input_data = VolumeInput(value=100.0, from_unit="liter", to_unit="liter")
        result = await tool.execute(input_data)

        assert result.value == 100.0

    @pytest.mark.asyncio
    async def test_unit_normalization(self, tool):
        """測試單位標準化（大小寫不敏感）"""
        input_data = VolumeInput(value=1.0, from_unit="L", to_unit="ML")
        result = await tool.execute(input_data)

        assert isinstance(result, VolumeOutput)
        assert result.value == 1000.0

    @pytest.mark.asyncio
    async def test_zero_value(self, tool):
        """測試零值"""
        input_data = VolumeInput(value=0.0, from_unit="liter", to_unit="milliliter")
        result = await tool.execute(input_data)

        assert result.value == 0.0

    @pytest.mark.asyncio
    async def test_imperial_gallon(self, tool):
        """測試英制加侖"""
        input_data = VolumeInput(value=1.0, from_unit="imperial_gallon", to_unit="liter")
        result = await tool.execute(input_data)

        assert isinstance(result, VolumeOutput)
        assert abs(result.value - 4.54609) < 0.0001
