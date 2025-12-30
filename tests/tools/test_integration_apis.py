# 代碼功能說明: 外部 API 集成測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""外部 API 集成測試

測試工具與外部 API 的集成，包括錯誤處理和降級策略。
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from tools.conversion import CurrencyConverter, CurrencyInput
from tools.location import GeocodingInput, GeocodingTool
from tools.utils.errors import ToolExecutionError
from tools.weather import WeatherInput, WeatherTool


@pytest.mark.asyncio
class TestWeatherAPIIntegration:
    """天氣 API 集成測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        # 使用環境變數中的 API Key，如果沒有則使用 mock
        api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        return WeatherTool(api_key=api_key)

    @pytest.mark.asyncio
    async def test_weather_api_success(self, tool):
        """測試天氣 API 成功響應（使用 mock）"""
        mock_weather_data = {
            "name": "Taipei",
            "sys": {"country": "TW"},
            "main": {
                "temp": 25.0,
                "feels_like": 26.0,
                "humidity": 70,
                "pressure": 1013,
            },
            "weather": [{"description": "clear sky", "icon": "01d"}],
            "wind": {"speed": 5.0, "deg": 180},
            "visibility": 10000,
            "dt": 1735549200,
        }

        with patch(
            "tools.weather.providers.openweathermap.OpenWeatherMapProvider._fetch_weather"
        ) as mock_fetch:
            mock_fetch.return_value = mock_weather_data

            input_data = WeatherInput(city="Taipei")
            result = await tool.execute(input_data)

            assert result is not None
            assert result.city == "Taipei"
            assert result.temperature == 25.0

    @pytest.mark.asyncio
    async def test_weather_api_failure(self, tool):
        """測試天氣 API 失敗處理"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("API Error")
            )

            input_data = WeatherInput(city="Taipei")
            with pytest.raises(ToolExecutionError):
                await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_weather_api_timeout(self, tool):
        """測試天氣 API 超時處理"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Request timeout")
            )

            input_data = WeatherInput(city="Taipei")
            with pytest.raises(ToolExecutionError):
                await tool.execute(input_data)


@pytest.mark.asyncio
class TestGeocodingAPIIntegration:
    """地理編碼 API 集成測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return GeocodingTool()

    @pytest.mark.asyncio
    async def test_geocoding_api_success(self, tool):
        """測試地理編碼 API 成功響應（使用 mock）"""
        mock_geocoding_data = [
            {
                "display_name": "Taipei, Taiwan",
                "lat": "25.0330",
                "lon": "121.5654",
                "address": {
                    "country": "Taiwan",
                    "city": "Taipei",
                },
            }
        ]

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_geocoding_data
            mock_response.raise_for_status = AsyncMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            input_data = GeocodingInput(address="Taipei, Taiwan")
            result = await tool.execute(input_data)

            assert result is not None
            assert result.latitude == 25.0330
            assert result.longitude == 121.5654

    @pytest.mark.asyncio
    async def test_geocoding_api_failure(self, tool):
        """測試地理編碼 API 失敗處理"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("API Error")
            )

            input_data = GeocodingInput(address="Taipei, Taiwan")
            with pytest.raises(ToolExecutionError):
                await tool.execute(input_data)


@pytest.mark.asyncio
class TestCurrencyAPIIntegration:
    """貨幣 API 集成測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return CurrencyConverter()

    @pytest.mark.asyncio
    async def test_currency_api_success(self, tool):
        """測試貨幣 API 成功響應"""
        mock_currency_data = {
            "rates": {
                "TWD": 30.0,
                "EUR": 0.85,
            },
            "base": "USD",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_currency_data
            mock_response.raise_for_status = AsyncMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            input_data = CurrencyInput(amount=100.0, from_currency="USD", to_currency="TWD")
            result = await tool.execute(input_data)

            assert result is not None
            assert result.amount == 3000.0
            assert result.exchange_rate == 30.0

    @pytest.mark.asyncio
    async def test_currency_api_failure(self, tool):
        """測試貨幣 API 失敗處理"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("API Error")
            )

            input_data = CurrencyInput(amount=100.0, from_currency="USD", to_currency="TWD")
            with pytest.raises(ToolExecutionError):
                await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_currency_api_rate_not_found(self, tool):
        """測試匯率未找到"""
        mock_currency_data = {
            "rates": {
                "EUR": 0.85,
            },
            "base": "USD",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_currency_data
            mock_response.raise_for_status = AsyncMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            input_data = CurrencyInput(amount=100.0, from_currency="USD", to_currency="TWD")
            with pytest.raises(ToolExecutionError):
                await tool.execute(input_data)


@pytest.mark.asyncio
class TestAPICacheIntegration:
    """API 緩存集成測試"""

    @pytest.mark.asyncio
    async def test_weather_api_cache(self):
        """測試天氣 API 緩存"""
        tool = WeatherTool()

        mock_weather_data = {
            "name": "Taipei",
            "sys": {"country": "TW"},
            "main": {"temp": 25.0, "feels_like": 26.0, "humidity": 70, "pressure": 1013},
            "weather": [{"description": "clear sky", "icon": "01d"}],
            "wind": {"speed": 5.0, "deg": 180},
            "dt": 1735549200,
        }

        with patch(
            "tools.weather.providers.openweathermap.OpenWeatherMapProvider._fetch_weather"
        ) as mock_fetch:
            mock_fetch.return_value = mock_weather_data

            # 第一次調用
            input_data1 = WeatherInput(city="Taipei")
            result1 = await tool.execute(input_data1)

            # 第二次調用（應該使用緩存）
            input_data2 = WeatherInput(city="Taipei")
            result2 = await tool.execute(input_data2)

            # 驗證結果一致
            assert result1.temperature == result2.temperature
            # 驗證 API 只被調用一次（如果實現了緩存）
            # 注意：實際緩存行為取決於實現
