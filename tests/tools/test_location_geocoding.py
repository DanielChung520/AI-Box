# 代碼功能說明: 地理編碼工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""地理編碼工具測試"""

from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from tools.location import GeocodingInput, GeocodingOutput, GeocodingTool
from tools.utils.errors import ToolExecutionError, ToolValidationError


@pytest.mark.asyncio
class TestGeocodingTool:
    """地理編碼工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return GeocodingTool()

    @pytest.fixture
    def mock_cache(self):
        """模擬緩存"""
        with patch("tools.location.geocoding.get_cache") as mock:
            cache = Mock()
            cache.get.return_value = None
            cache.set.return_value = None
            mock.return_value = cache
            yield cache

    @pytest.mark.asyncio
    async def test_forward_geocode(self, tool, mock_cache):
        """測試正向地理編碼（地址 → 坐標）"""
        mock_response_data = [
            {
                "display_name": "Taipei, Taiwan",
                "lat": "25.0330",
                "lon": "121.5654",
                "address": {
                    "country": "Taiwan",
                    "country_code": "tw",
                    "city": "Taipei",
                },
                "place_id": "12345",
            }
        ]

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            input_data = GeocodingInput(address="Taipei, Taiwan")
            result = await tool.execute(input_data)

            assert isinstance(result, GeocodingOutput)
            assert result.latitude == 25.0330
            assert result.longitude == 121.5654
            assert result.city == "Taipei"

    @pytest.mark.asyncio
    async def test_reverse_geocode(self, tool, mock_cache):
        """測試反向地理編碼（坐標 → 地址）"""
        mock_response_data = {
            "display_name": "Taipei, Taiwan",
            "lat": "25.0330",
            "lon": "121.5654",
            "address": {
                "country": "Taiwan",
                "country_code": "tw",
                "city": "Taipei",
                "road": "Test Road",
                "postcode": "100",
            },
            "place_id": "12345",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            input_data = GeocodingInput(lat=25.0330, lon=121.5654)
            result = await tool.execute(input_data)

            assert isinstance(result, GeocodingOutput)
            assert result.latitude == 25.0330
            assert result.longitude == 121.5654
            assert "Taipei" in result.address

    @pytest.mark.asyncio
    async def test_forward_geocode_no_results(self, tool, mock_cache):
        """測試正向地理編碼無結果"""
        mock_response_data = []

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            input_data = GeocodingInput(address="Nonexistent Place")
            with pytest.raises(ToolExecutionError):
                await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_reverse_geocode_error(self, tool, mock_cache):
        """測試反向地理編碼錯誤"""
        mock_response_data = {"error": "Invalid coordinates"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            input_data = GeocodingInput(lat=25.0330, lon=121.5654)
            with pytest.raises(ToolExecutionError):
                await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_geocoding_missing_input(self, tool):
        """測試缺少輸入參數"""
        input_data = GeocodingInput(address=None, lat=None, lon=None)
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_geocoding_invalid_coordinates(self, tool):
        """測試無效坐標"""
        input_data = GeocodingInput(lat=100.0, lon=200.0)  # 無效坐標
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_geocoding_api_error(self, tool, mock_cache):
        """測試 API 錯誤"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.HTTPError(
                "Connection error"
            )

            input_data = GeocodingInput(address="Taipei")
            with pytest.raises(ToolExecutionError):
                await tool.execute(input_data)
