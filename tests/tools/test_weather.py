# 代碼功能說明: 天氣工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""天氣工具測試"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from tools.utils.errors import ToolExecutionError, ToolValidationError
from tools.weather import WeatherInput, WeatherOutput, WeatherTool
from tools.weather.providers.base import WeatherData


@pytest.mark.asyncio
class TestWeatherTool:
    """天氣工具測試"""

    @pytest.fixture
    def mock_provider(self):
        """模擬天氣提供商"""
        provider = AsyncMock()
        provider.get_current_weather.return_value = WeatherData(
            city="Taipei",
            country="TW",
            temperature=25.5,
            feels_like=26.0,
            humidity=65,
            pressure=1013,
            description="晴天",
            icon="01d",
            wind_speed=3.5,
            wind_direction=180,
            visibility=10000,
            uv_index=5.0,
            timestamp=1735549200.0,
        )
        return provider

    @pytest.fixture
    def tool(self, mock_provider):
        """創建工具實例"""
        # 直接創建工具實例，不調用 __init__ 以避免 API key 要求
        tool = WeatherTool.__new__(WeatherTool)
        tool._provider_name = "openweathermap"
        tool._provider = mock_provider
        return tool

    @pytest.fixture
    def mock_cache(self):
        """模擬緩存"""
        with patch("tools.weather.weather_tool.get_cache") as mock:
            cache = Mock()
            cache.get.return_value = None
            cache.set.return_value = None
            mock.return_value = cache
            yield cache

    @pytest.mark.asyncio
    async def test_get_weather_by_city(self, tool, mock_cache):
        """測試根據城市獲取天氣"""
        input_data = WeatherInput(city="Taipei", units="metric")
        result = await tool.execute(input_data)

        assert isinstance(result, WeatherOutput)
        assert result.city == "Taipei"
        assert result.temperature == 25.5
        assert result.humidity == 65
        tool._provider.get_current_weather.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_weather_by_coordinates(self, tool, mock_provider, mock_cache):
        """測試根據經緯度獲取天氣"""
        tool._provider = mock_provider  # 設置 provider
        input_data = WeatherInput(lat=25.0330, lon=121.5654, units="metric")
        result = await tool.execute(input_data)

        assert isinstance(result, WeatherOutput)
        assert result.city is not None
        mock_provider.get_current_weather.assert_called_once_with(
            city=None, lat=25.0330, lon=121.5654, units="metric"
        )

    @pytest.mark.asyncio
    async def test_get_weather_cached(self, tool, mock_cache):
        """測試緩存機制"""
        # 設置緩存中有數據
        cached_data = {
            "city": "Taipei",
            "country": "TW",
            "temperature": 25.5,
            "feels_like": 26.0,
            "humidity": 65,
            "pressure": 1013,
            "description": "晴天",
            "icon": "01d",
            "wind_speed": 3.5,
            "wind_direction": 180,
            "visibility": 10000,
            "uv_index": 5.0,
            "timestamp": 1735549200.0,
        }
        mock_cache.get.return_value = cached_data

        input_data = WeatherInput(city="Taipei")
        result = await tool.execute(input_data)

        # 驗證從緩存獲取，未調用提供商
        tool._provider.get_current_weather.assert_not_called()
        assert result.city == "Taipei"

    @pytest.mark.asyncio
    async def test_get_weather_missing_location(self, tool):
        """測試缺少位置信息"""
        input_data = WeatherInput(city=None, lat=None, lon=None)
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_get_weather_invalid_coordinates(self, tool):
        """測試無效坐標"""
        input_data = WeatherInput(lat=100.0, lon=200.0)  # 無效坐標
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_get_weather_invalid_units(self, tool):
        """測試無效單位"""
        input_data = WeatherInput(city="Taipei", units="invalid")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_get_weather_provider_error(self, tool, mock_provider, mock_cache):
        """測試提供商錯誤"""
        mock_provider.get_current_weather.side_effect = Exception("API Error")
        tool._provider = mock_provider  # 替換為會出錯的 provider

        input_data = WeatherInput(city="Taipei")
        with pytest.raises(ToolExecutionError):
            await tool.execute(input_data)


@pytest.mark.asyncio
class TestOpenWeatherMapProvider:
    """OpenWeatherMap 提供商測試"""

    @pytest.fixture
    def provider(self):
        """創建提供商實例"""
        with patch.dict("os.environ", {"OPENWEATHERMAP_API_KEY": "test_key"}):
            from tools.weather.providers.openweathermap import OpenWeatherMapProvider

            return OpenWeatherMapProvider(api_key="test_key")

    @pytest.mark.asyncio
    async def test_get_current_weather_by_city(self, provider):
        """測試根據城市獲取天氣"""
        mock_response_data = {
            "name": "Taipei",
            "sys": {"country": "TW"},
            "main": {
                "temp": 25.5,
                "feels_like": 26.0,
                "humidity": 65,
                "pressure": 1013,
            },
            "weather": [{"description": "晴天", "icon": "01d"}],
            "wind": {"speed": 3.5, "deg": 180},
            "visibility": 10000,
            "dt": 1735549200,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await provider.get_current_weather(city="Taipei", units="metric")

            assert result.city == "Taipei"
            assert result.country == "TW"
            assert result.temperature == 25.5

    @pytest.mark.asyncio
    async def test_get_current_weather_by_coordinates(self, provider):
        """測試根據經緯度獲取天氣"""
        mock_response_data = {
            "name": "Taipei",
            "sys": {"country": "TW"},
            "main": {"temp": 25.5, "feels_like": 26.0, "humidity": 65, "pressure": 1013},
            "weather": [{"description": "晴天", "icon": "01d"}],
            "wind": {"speed": 3.5, "deg": 180},
            "visibility": 10000,
            "dt": 1735549200,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await provider.get_current_weather(lat=25.0330, lon=121.5654, units="metric")

            assert result.city == "Taipei"

    @pytest.mark.asyncio
    async def test_get_current_weather_api_error(self, provider):
        """測試 API 錯誤"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.HTTPError(
                "Connection error"
            )

            with pytest.raises(ToolExecutionError):
                await provider.get_current_weather(city="Taipei")

    def test_provider_init_missing_api_key(self):
        """測試缺少 API Key"""
        with patch.dict("os.environ", {}, clear=True):
            from tools.utils.errors import ToolConfigurationError
            from tools.weather.providers.openweathermap import OpenWeatherMapProvider

            with pytest.raises(ToolConfigurationError):
                OpenWeatherMapProvider()
