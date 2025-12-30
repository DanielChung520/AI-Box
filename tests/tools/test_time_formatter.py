# 代碼功能說明: 日期格式化工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""日期格式化工具測試"""

from __future__ import annotations

import pytest

from tools.time import DateFormatter, FormatInput, FormatOutput
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestDateFormatter:
    """日期格式化工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return DateFormatter()

    @pytest.mark.asyncio
    async def test_format_date_iso(self, tool):
        """測試格式化 ISO 日期"""
        input_data = FormatInput(date="2025-12-30T12:00:00", format="%Y-%m-%d")
        result = await tool.execute(input_data)

        assert isinstance(result, FormatOutput)
        assert result.formatted == "2025-12-30"
        assert "2025-12-30" in result.iso_format
        assert result.timestamp > 0

    @pytest.mark.asyncio
    async def test_format_date_with_source_format(self, tool):
        """測試使用源格式解析"""
        input_data = FormatInput(date="30/12/2025", format="%Y-%m-%d", source_format="%d/%m/%Y")
        result = await tool.execute(input_data)

        assert isinstance(result, FormatOutput)
        assert result.formatted == "2025-12-30"

    @pytest.mark.asyncio
    async def test_format_date_custom_format(self, tool):
        """測試自定義格式"""
        input_data = FormatInput(date="2025-12-30T12:00:00", format="%Y年%m月%d日")
        result = await tool.execute(input_data)

        assert isinstance(result, FormatOutput)
        assert "2025" in result.formatted
        assert "12" in result.formatted
        assert "30" in result.formatted

    @pytest.mark.asyncio
    async def test_format_date_invalid_date(self, tool):
        """測試無效日期"""
        input_data = FormatInput(date="invalid-date", format="%Y-%m-%d")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_format_date_invalid_source_format(self, tool):
        """測試無效源格式"""
        input_data = FormatInput(date="2025-12-30", format="%Y-%m-%d", source_format="%invalid")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)
