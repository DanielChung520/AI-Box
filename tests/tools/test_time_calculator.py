# 代碼功能說明: 日期計算工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""日期計算工具測試"""

from __future__ import annotations

import pytest

from tools.time import CalculateInput, CalculateOutput, DateCalculator
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestDateCalculator:
    """日期計算工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return DateCalculator()

    @pytest.mark.asyncio
    async def test_diff_operation(self, tool):
        """測試日期差值計算"""
        input_data = CalculateInput(
            operation="diff",
            date1="2025-12-01T00:00:00",
            date2="2025-12-30T00:00:00",
        )
        result = await tool.execute(input_data)

        assert isinstance(result, CalculateOutput)
        assert result.days_diff == 29
        assert result.hours_diff is not None
        assert result.result is not None

    @pytest.mark.asyncio
    async def test_diff_operation_reverse(self, tool):
        """測試日期差值計算（反向）"""
        input_data = CalculateInput(
            operation="diff",
            date1="2025-12-30T00:00:00",
            date2="2025-12-01T00:00:00",
        )
        result = await tool.execute(input_data)

        assert isinstance(result, CalculateOutput)
        assert result.days_diff == -29

    @pytest.mark.asyncio
    async def test_diff_operation_workdays_only(self, tool):
        """測試工作日差值計算"""
        input_data = CalculateInput(
            operation="diff",
            date1="2025-12-01T00:00:00",  # 週一
            date2="2025-12-05T00:00:00",  # 週五
            workdays_only=True,
        )
        result = await tool.execute(input_data)

        assert isinstance(result, CalculateOutput)
        assert result.workdays_diff == 5  # 5 個工作日

    @pytest.mark.asyncio
    async def test_add_operation_days(self, tool):
        """測試日期加運算（天數）"""
        input_data = CalculateInput(operation="add", date1="2025-12-01T00:00:00", days=30)
        result = await tool.execute(input_data)

        assert isinstance(result, CalculateOutput)
        assert result.result is not None
        assert "2025-12-31" in result.result

    @pytest.mark.asyncio
    async def test_add_operation_months(self, tool):
        """測試日期加運算（月數）"""
        input_data = CalculateInput(operation="add", date1="2025-12-01T00:00:00", months=1)
        result = await tool.execute(input_data)

        assert isinstance(result, CalculateOutput)
        assert result.result is not None

    @pytest.mark.asyncio
    async def test_subtract_operation_days(self, tool):
        """測試日期減運算（天數）"""
        input_data = CalculateInput(operation="subtract", date1="2025-12-30T00:00:00", days=30)
        result = await tool.execute(input_data)

        assert isinstance(result, CalculateOutput)
        assert result.result is not None

    @pytest.mark.asyncio
    async def test_diff_operation_missing_date2(self, tool):
        """測試差值計算缺少 date2"""
        input_data = CalculateInput(operation="diff", date1="2025-12-01T00:00:00", date2=None)
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_invalid_operation(self, tool):
        """測試無效操作"""
        input_data = CalculateInput(operation="invalid", date1="2025-12-01T00:00:00")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_invalid_date_format(self, tool):
        """測試無效日期格式"""
        input_data = CalculateInput(operation="add", date1="invalid-date", days=1)
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)
