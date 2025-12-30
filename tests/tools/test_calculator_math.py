# 代碼功能說明: 數學計算工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""數學計算工具測試"""

from __future__ import annotations

import pytest

from tools.calculator import MathCalculator, MathInput, MathOutput
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestMathCalculator:
    """數學計算工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return MathCalculator()

    @pytest.mark.asyncio
    async def test_basic_addition(self, tool):
        """測試基本加法"""
        input_data = MathInput(expression="2 + 3")
        result = await tool.execute(input_data)

        assert isinstance(result, MathOutput)
        assert result.result == 5.0

    @pytest.mark.asyncio
    async def test_multiplication(self, tool):
        """測試乘法"""
        input_data = MathInput(expression="4 * 5")
        result = await tool.execute(input_data)

        assert result.result == 20.0

    @pytest.mark.asyncio
    async def test_complex_expression(self, tool):
        """測試複雜表達式"""
        input_data = MathInput(expression="2 + 3 * 4")
        result = await tool.execute(input_data)

        assert result.result == 14.0

    @pytest.mark.asyncio
    async def test_sqrt_function(self, tool):
        """測試平方根函數"""
        input_data = MathInput(expression="sqrt(16)")
        result = await tool.execute(input_data)

        assert result.result == 4.0

    @pytest.mark.asyncio
    async def test_sin_function(self, tool):
        """測試三角函數"""
        input_data = MathInput(expression="sin(0)")
        result = await tool.execute(input_data)

        assert abs(result.result - 0.0) < 0.0001

    @pytest.mark.asyncio
    async def test_invalid_expression(self, tool):
        """測試無效表達式"""
        input_data = MathInput(expression="2 +")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_unsafe_expression(self, tool):
        """測試不安全表達式（應該被拒絕）"""
        input_data = MathInput(expression="__import__('os').system('ls')")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)
