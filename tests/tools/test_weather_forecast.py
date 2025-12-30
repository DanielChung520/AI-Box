# 代碼功能說明: 天氣預報工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""天氣預報工具測試"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from tools.utils.errors import ToolExecutionError, ToolValidationError
from tools.weather import ForecastInput, ForecastOutput, ForecastTool
from tools.weather.providers.base import ForecastData, ForecastItemData, HourlyForecastData


@pytest.mark.asyncio
class TestForecastTool:
    """天氣預報工具測試"""

    @pytest.fixture
    def mock_provider(self):
        """模擬天氣提供商"""
        provider = AsyncMock()
        # 模擬預報數據
        forecast_data = ForecastData(
            city="Taipei",
            country="TW",
            forecasts=[
                ForecastItemData(
                    date="2025-12-31",
                    temperature=25.5,
                    min_temp=20.0,
                    max_temp=30.0,
                    description="晴天",
                    icon="01d",
                    humidity=65,
                    wind_speed=3.5,
                    precipitation=None,
                    timestamp=1735549200.0,
                ),
                ForecastItemData(
                    date="2026-01-01",
                    temperature=24.0,
                    min_temp=18.0,
                    max_temp=28.0,
                    description="多雲",
                    icon="02d",
                    humidity=70,
                    wind_speed=4.0,
                    precipitation=5.0,
                    timestamp=1735635600.0,
                ),
            ],
            hourly_forecasts=None,
        )
        provider.get_forecast.return_value = forecast_data
        return provider

    @pytest.fixture
    def tool(self, mock_provider):
        """創建工具實例"""
        tool = ForecastTool.__new__(ForecastTool)
        tool._provider_name = "openweathermap"
        tool._provider = mock_provider
        return tool

    @pytest.fixture
    def mock_cache(self):
        """模擬緩存"""
        with patch("tools.weather.forecast_tool.get_cache") as mock:
            cache = Mock()
            cache.get.return_value = None
            cache.set.return_value = None
            mock.return_value = cache
            yield cache

    @pytest.mark.asyncio
    async def test_get_forecast_by_city(self, tool, mock_cache):
        """測試根據城市獲取預報"""
        input_data = ForecastInput(city="Taipei", days=3, units="metric")
        result = await tool.execute(input_data)

        assert isinstance(result, ForecastOutput)
        assert result.city == "Taipei"
        assert result.country == "TW"
        assert len(result.forecasts) == 2
        assert result.forecasts[0].date == "2025-12-31"
        assert result.forecasts[0].temperature == 25.5
        tool._provider.get_forecast.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_forecast_by_coordinates(self, tool, mock_provider, mock_cache):
        """測試根據經緯度獲取預報"""
        tool._provider = mock_provider
        input_data = ForecastInput(lat=25.0330, lon=121.5654, days=3, units="metric")
        result = await tool.execute(input_data)

        assert isinstance(result, ForecastOutput)
        assert result.city == "Taipei"
        mock_provider.get_forecast.assert_called_once_with(
            city=None, lat=25.0330, lon=121.5654, days=3, hourly=False, units="metric"
        )

    @pytest.mark.asyncio
    async def test_get_forecast_with_hourly(self, tool, mock_provider, mock_cache):
        """測試獲取小時級別預報"""
        # 添加小時級別預報數據
        hourly_data = [
            HourlyForecastData(
                time="2025-12-31T12:00:00",
                temperature=25.5,
                description="晴天",
                icon="01d",
                humidity=65,
                wind_speed=3.5,
                precipitation=None,
                timestamp=1735549200.0,
            ),
            HourlyForecastData(
                time="2025-12-31T15:00:00",
                temperature=27.0,
                description="晴天",
                icon="01d",
                humidity=60,
                wind_speed=4.0,
                precipitation=None,
                timestamp=1735560000.0,
            ),
        ]
        forecast_data = ForecastData(
            city="Taipei",
            country="TW",
            forecasts=[
                ForecastItemData(
                    date="2025-12-31",
                    temperature=25.5,
                    min_temp=20.0,
                    max_temp=30.0,
                    description="晴天",
                    icon="01d",
                    humidity=65,
                    wind_speed=3.5,
                    precipitation=None,
                    timestamp=1735549200.0,
                )
            ],
            hourly_forecasts=hourly_data,
        )
        mock_provider.get_forecast.return_value = forecast_data
        tool._provider = mock_provider

        input_data = ForecastInput(city="Taipei", days=1, hourly=True, units="metric")
        result = await tool.execute(input_data)

        assert isinstance(result, ForecastOutput)
        assert len(result.forecasts) == 1
        assert result.forecasts[0].hourly is not None
        assert len(result.forecasts[0].hourly) == 2

    @pytest.mark.asyncio
    async def test_get_forecast_cached(self, tool, mock_cache):
        """測試緩存機制"""
        # 設置緩存中有數據
        cached_data = {
            "city": "Taipei",
            "country": "TW",
            "forecasts": [
                {
                    "date": "2025-12-31",
                    "temperature": 25.5,
                    "min_temp": 20.0,
                    "max_temp": 30.0,
                    "description": "晴天",
                    "icon": "01d",
                    "humidity": 65,
                    "wind_speed": 3.5,
                    "precipitation": None,
                    "hourly": None,
                    "timestamp": 1735549200.0,
                }
            ],
        }
        mock_cache.get.return_value = cached_data

        input_data = ForecastInput(city="Taipei", days=3)
        result = await tool.execute(input_data)

        assert isinstance(result, ForecastOutput)
        assert result.city == "Taipei"
        # 不應該調用 provider
        tool._provider.get_forecast.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_days(self, tool):
        """測試無效天數"""
        input_data = ForecastInput(city="Taipei", days=0)
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

        input_data = ForecastInput(city="Taipei", days=8)
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_invalid_units(self, tool):
        """測試無效單位"""
        input_data = ForecastInput(city="Taipei", units="invalid")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_missing_city_and_coordinates(self, tool):
        """測試缺少城市和坐標"""
        input_data = ForecastInput(days=3)
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_invalid_coordinates(self, tool):
        """測試無效坐標"""
        input_data = ForecastInput(lat=100.0, lon=121.5654, days=3)
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_provider_error(self, tool, mock_provider, mock_cache):
        """測試提供商錯誤"""
        mock_provider.get_forecast.side_effect = ToolExecutionError(
            "API error", tool_name="provider"
        )
        tool._provider = mock_provider

        input_data = ForecastInput(city="Taipei", days=3)
        with pytest.raises(ToolExecutionError):
            await tool.execute(input_data)
