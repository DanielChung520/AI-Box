# 代碼功能說明: IP 地址定位工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""IP 地址定位工具測試"""

from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from tools.location import IPLocationInput, IPLocationOutput, IPLocationTool
from tools.utils.errors import ToolExecutionError, ToolValidationError


@pytest.mark.asyncio
class TestIPLocationTool:
    """IP 地址定位工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return IPLocationTool()

    @pytest.fixture
    def mock_cache(self):
        """模擬緩存"""
        with patch("tools.location.ip_location.get_cache") as mock:
            cache = Mock()
            cache.get.return_value = None
            cache.set.return_value = None
            mock.return_value = cache
            yield cache

    @pytest.mark.asyncio
    async def test_get_location_by_ipv4(self, tool, mock_cache):
        """測試 IPv4 地址定位"""
        mock_response_data = {
            "status": "success",
            "country": "Taiwan",
            "countryCode": "TW",
            "regionName": "Taipei",
            "city": "Taipei",
            "lat": 25.0330,
            "lon": 121.5654,
            "timezone": "Asia/Taipei",
            "isp": "Test ISP",
            "org": "Test Organization",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            input_data = IPLocationInput(ip="8.8.8.8")
            result = await tool.execute(input_data)

            assert isinstance(result, IPLocationOutput)
            assert result.ip == "8.8.8.8"
            assert result.country == "Taiwan"
            assert result.country_code == "TW"

    @pytest.mark.asyncio
    async def test_get_location_cached(self, tool, mock_cache):
        """測試緩存機制"""
        cached_data = {
            "ip": "8.8.8.8",
            "country": "Taiwan",
            "country_code": "TW",
            "region": "Taipei",
            "city": "Taipei",
            "latitude": 25.0330,
            "longitude": 121.5654,
            "timezone": "Asia/Taipei",
            "isp": "Test ISP",
            "org": "Test Organization",
        }
        mock_cache.get.return_value = cached_data

        input_data = IPLocationInput(ip="8.8.8.8")
        result = await tool.execute(input_data)

        assert result.city == "Taipei"
        # 驗證未調用 API
        mock_cache.get.assert_called()

    @pytest.mark.asyncio
    async def test_get_location_invalid_ip(self, tool):
        """測試無效 IP 地址"""
        input_data = IPLocationInput(ip="invalid-ip")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_get_location_api_error(self, tool, mock_cache):
        """測試 API 錯誤"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.HTTPError(
                "Connection error"
            )

            input_data = IPLocationInput(ip="8.8.8.8")
            with pytest.raises(ToolExecutionError):
                await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_get_location_api_fail_status(self, tool, mock_cache):
        """測試 API 返回失敗狀態"""
        mock_response_data = {"status": "fail", "message": "Invalid IP address"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            input_data = IPLocationInput(ip="8.8.8.8")
            with pytest.raises(ToolExecutionError):
                await tool.execute(input_data)
