# 代碼功能說明: 重量單位轉換工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""重量單位轉換工具測試"""

from __future__ import annotations

import pytest

from tools.conversion import WeightConverter, WeightInput, WeightOutput
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestWeightConverter:
    """重量單位轉換工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return WeightConverter()

    @pytest.mark.asyncio
    async def test_kilogram_to_gram(self, tool):
        """測試公斤轉克"""
        input_data = WeightInput(value=1.0, from_unit="kilogram", to_unit="gram")
        result = await tool.execute(input_data)

        assert isinstance(result, WeightOutput)
        assert result.value == 1000.0
        assert result.from_unit == "kilogram"
        assert result.to_unit == "gram"
        assert result.original_value == 1.0

    @pytest.mark.asyncio
    async def test_pound_to_kilogram(self, tool):
        """測試磅轉公斤"""
        input_data = WeightInput(value=1.0, from_unit="pound", to_unit="kilogram")
        result = await tool.execute(input_data)

        assert isinstance(result, WeightOutput)
        assert abs(result.value - 0.453592) < 0.0001

    @pytest.mark.asyncio
    async def test_ounce_to_gram(self, tool):
        """測試盎司轉克"""
        input_data = WeightInput(value=1.0, from_unit="ounce", to_unit="gram")
        result = await tool.execute(input_data)

        assert isinstance(result, WeightOutput)
        assert abs(result.value - 28.3495) < 0.0001

    @pytest.mark.asyncio
    async def test_metric_ton_to_kilogram(self, tool):
        """測試公噸轉公斤"""
        input_data = WeightInput(value=1.0, from_unit="metric_ton", to_unit="kilogram")
        result = await tool.execute(input_data)

        assert isinstance(result, WeightOutput)
        assert result.value == 1000.0

    @pytest.mark.asyncio
    async def test_carat_to_gram(self, tool):
        """測試克拉轉克"""
        input_data = WeightInput(value=5.0, from_unit="carat", to_unit="gram")
        result = await tool.execute(input_data)

        assert isinstance(result, WeightOutput)
        assert result.value == 1.0

    @pytest.mark.asyncio
    async def test_invalid_unit(self, tool):
        """測試無效單位"""
        input_data = WeightInput(value=1.0, from_unit="invalid", to_unit="kilogram")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_same_unit(self, tool):
        """測試相同單位轉換"""
        input_data = WeightInput(value=100.0, from_unit="kilogram", to_unit="kilogram")
        result = await tool.execute(input_data)

        assert result.value == 100.0

    @pytest.mark.asyncio
    async def test_unit_normalization(self, tool):
        """測試單位標準化（大小寫不敏感）"""
        input_data = WeightInput(value=1.0, from_unit="KG", to_unit="g")
        result = await tool.execute(input_data)

        assert isinstance(result, WeightOutput)
        assert result.value == 1000.0

    @pytest.mark.asyncio
    async def test_zero_value(self, tool):
        """測試零值"""
        input_data = WeightInput(value=0.0, from_unit="kilogram", to_unit="gram")
        result = await tool.execute(input_data)

        assert result.value == 0.0

    @pytest.mark.asyncio
    async def test_large_value(self, tool):
        """測試大數值"""
        input_data = WeightInput(value=1000.0, from_unit="kilogram", to_unit="metric_ton")
        result = await tool.execute(input_data)

        assert result.value == 1.0
