# 代碼功能說明: 時區查詢工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""時區查詢工具測試"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from tools.location import TimezoneInput, TimezoneOutput, TimezoneTool
from tools.location.geocoding import GeocodingOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError


@pytest.mark.asyncio
class TestTimezoneTool:
    """時區查詢工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return TimezoneTool()

    @pytest.mark.asyncio
    async def test_get_timezone_by_coordinates(self, tool):
        """測試根據坐標獲取時區"""
        # 台北坐標 (25.0330, 121.5654)
        input_data = TimezoneInput(lat=25.0330, lon=121.5654)
        result = await tool.execute(input_data)

        assert isinstance(result, TimezoneOutput)
        assert result.timezone == "Asia/Taipei"
        assert result.offset != 0  # UTC+8
        assert result.offset_hours == 8.0
        assert result.dst is False  # 台灣不使用夏令時
        assert result.abbreviation in ["CST", "TST"]  # 台灣時區縮寫

    @pytest.mark.asyncio
    async def test_get_timezone_by_city(self, tool):
        """測試根據城市名稱獲取時區"""
        # Mock 地理編碼工具
        mock_geocoding_output = GeocodingOutput(
            address="Taipei, Taiwan",
            formatted_address="Taipei, Taiwan",
            latitude=25.0330,
            longitude=121.5654,
            country="Taiwan",
            country_code="tw",
        )

        with patch.object(tool._geocoding_tool, "execute", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = mock_geocoding_output

            input_data = TimezoneInput(city="Taipei")
            result = await tool.execute(input_data)

            assert isinstance(result, TimezoneOutput)
            assert result.timezone == "Asia/Taipei"
            mock_geocode.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_timezone_utc(self, tool):
        """測試 UTC 時區"""
        # 倫敦格林威治坐標 (51.4769, -0.0005)
        input_data = TimezoneInput(lat=51.4769, lon=-0.0005)
        result = await tool.execute(input_data)

        assert isinstance(result, TimezoneOutput)
        # 可能返回 Europe/London 或其他時區
        assert result.timezone is not None
        assert result.offset_hours in [0.0, 1.0]  # UTC 或 BST (夏令時)

    @pytest.mark.asyncio
    async def test_get_timezone_with_timestamp(self, tool):
        """測試使用時間戳查詢時區（用於判斷夏令時）"""
        # 紐約坐標 (40.7128, -74.0060)
        # 測試冬季（不使用夏令時）
        winter_timestamp = 1704067200.0  # 2024-01-01 00:00:00 UTC
        input_data = TimezoneInput(lat=40.7128, lon=-74.0060, timestamp=winter_timestamp)
        result = await tool.execute(input_data)

        assert isinstance(result, TimezoneOutput)
        assert result.timezone == "America/New_York"
        assert result.offset_hours == -5.0  # EST (Eastern Standard Time)
        assert result.dst is False

    @pytest.mark.asyncio
    async def test_get_timezone_dst_summer(self, tool):
        """測試夏令時"""
        # 紐約坐標 (40.7128, -74.0060)
        # 測試夏季（使用夏令時）
        summer_timestamp = 1717200000.0  # 2024-06-01 00:00:00 UTC
        input_data = TimezoneInput(lat=40.7128, lon=-74.0060, timestamp=summer_timestamp)
        result = await tool.execute(input_data)

        assert isinstance(result, TimezoneOutput)
        assert result.timezone == "America/New_York"
        assert result.offset_hours == -4.0  # EDT (Eastern Daylight Time)
        assert result.dst is True

    @pytest.mark.asyncio
    async def test_invalid_coordinates_lat(self, tool):
        """測試無效緯度"""
        input_data = TimezoneInput(lat=100.0, lon=121.5654)
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_invalid_coordinates_lon(self, tool):
        """測試無效經度"""
        input_data = TimezoneInput(lat=25.0330, lon=200.0)
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_missing_coordinates_and_city(self, tool):
        """測試缺少坐標和城市名稱"""
        input_data = TimezoneInput()
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_geocoding_failure(self, tool):
        """測試地理編碼失敗"""
        with patch.object(tool._geocoding_tool, "execute", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.side_effect = ToolExecutionError("Geocoding failed", tool_name="geocoding")

            input_data = TimezoneInput(city="InvalidCityName12345")
            with pytest.raises(ToolExecutionError):
                await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_empty_city_name(self, tool):
        """測試空城市名稱"""
        input_data = TimezoneInput(city="")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)
