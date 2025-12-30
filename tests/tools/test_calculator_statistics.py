# 代碼功能說明: 統計計算工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""統計計算工具測試"""

from __future__ import annotations

import pytest

from tools.calculator import StatisticsCalculator, StatisticsInput, StatisticsOutput
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestStatisticsCalculator:
    """統計計算工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return StatisticsCalculator()

    @pytest.fixture
    def sample_data(self):
        """示例數據"""
        return [1.0, 2.0, 3.0, 4.0, 5.0]

    @pytest.mark.asyncio
    async def test_mean(self, tool, sample_data):
        """測試平均值"""
        input_data = StatisticsInput(data=sample_data, operation="mean")
        result = await tool.execute(input_data)

        assert isinstance(result, StatisticsOutput)
        assert result.result == 3.0
        assert result.data_count == 5

    @pytest.mark.asyncio
    async def test_median(self, tool, sample_data):
        """測試中位數"""
        input_data = StatisticsInput(data=sample_data, operation="median")
        result = await tool.execute(input_data)

        assert result.result == 3.0

    @pytest.mark.asyncio
    async def test_min(self, tool, sample_data):
        """測試最小值"""
        input_data = StatisticsInput(data=sample_data, operation="min")
        result = await tool.execute(input_data)

        assert result.result == 1.0

    @pytest.mark.asyncio
    async def test_max(self, tool, sample_data):
        """測試最大值"""
        input_data = StatisticsInput(data=sample_data, operation="max")
        result = await tool.execute(input_data)

        assert result.result == 5.0

    @pytest.mark.asyncio
    async def test_std(self, tool, sample_data):
        """測試標準差"""
        input_data = StatisticsInput(data=sample_data, operation="std")
        result = await tool.execute(input_data)

        assert result.result > 0

    @pytest.mark.asyncio
    async def test_empty_data(self, tool):
        """測試空數據"""
        input_data = StatisticsInput(data=[], operation="mean")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_invalid_operation(self, tool, sample_data):
        """測試無效操作"""
        input_data = StatisticsInput(data=sample_data, operation="invalid")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)
