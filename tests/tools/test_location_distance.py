# 代碼功能說明: 距離計算工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""距離計算工具測試"""

from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from tools.location import DistanceInput, DistanceOutput, DistanceTool
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestDistanceTool:
    """距離計算工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return DistanceTool()

    @pytest.mark.asyncio
    async def test_haversine_distance_km(self, tool):
        """測試 Haversine 距離計算（公里）"""
        # 台北 (25.0330, 121.5654) 到 台中 (24.1477, 120.6736)
        input_data = DistanceInput(
            lat1=25.0330, lon1=121.5654, lat2=24.1477, lon2=120.6736, unit="km"
        )
        result = await tool.execute(input_data)

        assert isinstance(result, DistanceOutput)
        assert result.method == "haversine"
        assert result.distance > 0  # 距離應該大於 0
        assert result.distance_km > 0
        assert result.distance_mile > 0
        assert result.distance_meter > 0
        # 台北到台中大約 140-150 公里
        assert 100 < result.distance_km < 200

    @pytest.mark.asyncio
    async def test_haversine_distance_mile(self, tool):
        """測試 Haversine 距離計算（英里）"""
        input_data = DistanceInput(
            lat1=25.0330, lon1=121.5654, lat2=24.1477, lon2=120.6736, unit="mile"
        )
        result = await tool.execute(input_data)

        assert isinstance(result, DistanceOutput)
        assert result.distance == result.distance_mile
        assert result.distance_mile == result.distance_km * 0.621371

    @pytest.mark.asyncio
    async def test_haversine_distance_meter(self, tool):
        """測試 Haversine 距離計算（米）"""
        input_data = DistanceInput(
            lat1=25.0330, lon1=121.5654, lat2=24.1477, lon2=120.6736, unit="meter"
        )
        result = await tool.execute(input_data)

        assert isinstance(result, DistanceOutput)
        assert result.distance == result.distance_meter
        assert result.distance_meter == result.distance_km * 1000.0

    @pytest.mark.asyncio
    async def test_haversine_distance_same_point(self, tool):
        """測試相同點的距離"""
        input_data = DistanceInput(
            lat1=25.0330, lon1=121.5654, lat2=25.0330, lon2=121.5654, unit="km"
        )
        result = await tool.execute(input_data)

        assert isinstance(result, DistanceOutput)
        assert result.distance == 0.0
        assert result.distance_km == 0.0

    @pytest.mark.asyncio
    async def test_invalid_latitude_point1(self, tool):
        """測試無效緯度（點1）"""
        input_data = DistanceInput(lat1=100.0, lon1=121.5654, lat2=24.1477, lon2=120.6736)
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_invalid_longitude_point1(self, tool):
        """測試無效經度（點1）"""
        input_data = DistanceInput(lat1=25.0330, lon1=200.0, lat2=24.1477, lon2=120.6736)
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_invalid_latitude_point2(self, tool):
        """測試無效緯度（點2）"""
        input_data = DistanceInput(lat1=25.0330, lon1=121.5654, lat2=100.0, lon2=120.6736)
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_invalid_method(self, tool):
        """測試無效計算方法"""
        input_data = DistanceInput(
            lat1=25.0330,
            lon1=121.5654,
            lat2=24.1477,
            lon2=120.6736,
            method="invalid",
        )
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_invalid_unit(self, tool):
        """測試無效單位"""
        input_data = DistanceInput(
            lat1=25.0330, lon1=121.5654, lat2=24.1477, lon2=120.6736, unit="invalid"
        )
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_driving_distance(self, tool):
        """測試駕車距離計算"""
        # Mock OpenRouteService API 響應
        mock_response_data = {
            "routes": [
                {
                    "summary": {
                        "distance": 150000.0,  # 150 公里（米）
                        "duration": 7200.0,  # 2 小時（秒）
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

            # 設置 API key（通過環境變數）
            import os

            with patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "test_key"}):
                tool_with_key = DistanceTool(api_key="test_key")
                input_data = DistanceInput(
                    lat1=25.0330,
                    lon1=121.5654,
                    lat2=24.1477,
                    lon2=120.6736,
                    method="driving",
                )
                result = await tool_with_key.execute(input_data)

                assert isinstance(result, DistanceOutput)
                assert result.method == "driving"
                assert result.distance_km == 150.0
                assert result.duration == 7200.0
                assert result.route is not None

    @pytest.mark.asyncio
    async def test_walking_distance(self, tool):
        """測試步行距離計算"""
        # Mock OpenRouteService API 響應
        mock_response_data = {
            "routes": [
                {
                    "summary": {
                        "distance": 5000.0,  # 5 公里（米）
                        "duration": 3600.0,  # 1 小時（秒）
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

            # 設置 API key（通過環境變數）
            import os

            with patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "test_key"}):
                tool_with_key = DistanceTool(api_key="test_key")
                input_data = DistanceInput(
                    lat1=25.0330,
                    lon1=121.5654,
                    lat2=24.1477,
                    lon2=120.6736,
                    method="walking",
                )
                result = await tool_with_key.execute(input_data)

                assert isinstance(result, DistanceOutput)
                assert result.method == "walking"
                assert result.distance_km == 5.0
                assert result.duration == 3600.0
                assert result.route is not None

    @pytest.mark.asyncio
    async def test_driving_distance_no_api_key(self, tool):
        """測試沒有 API key 時的駕車距離（回退到 Haversine）"""
        # 沒有設置 API key
        input_data = DistanceInput(
            lat1=25.0330, lon1=121.5654, lat2=24.1477, lon2=120.6736, method="driving"
        )
        result = await tool.execute(input_data)

        assert isinstance(result, DistanceOutput)
        assert result.method == "driving"
        # 應該回退到 Haversine 計算
        assert result.distance_km > 0
        assert result.duration is None  # 沒有 API，無法獲取預計時間

    @pytest.mark.asyncio
    async def test_walking_distance_no_api_key(self, tool):
        """測試沒有 API key 時的步行距離（回退到 Haversine）"""
        # 沒有設置 API key
        input_data = DistanceInput(
            lat1=25.0330, lon1=121.5654, lat2=24.1477, lon2=120.6736, method="walking"
        )
        result = await tool.execute(input_data)

        assert isinstance(result, DistanceOutput)
        assert result.method == "walking"
        # 應該回退到 Haversine 計算
        assert result.distance_km > 0
        assert result.duration is None  # 沒有 API，無法獲取預計時間

    @pytest.mark.asyncio
    async def test_driving_distance_api_error(self, tool):
        """測試 API 錯誤時的回退機制"""
        with patch("httpx.AsyncClient") as mock_client:
            # 模擬 API 錯誤
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.HTTPError(
                "API error"
            )

            import os

            with patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "test_key"}):
                tool_with_key = DistanceTool(api_key="test_key")
                input_data = DistanceInput(
                    lat1=25.0330,
                    lon1=121.5654,
                    lat2=24.1477,
                    lon2=120.6736,
                    method="driving",
                )
                result = await tool_with_key.execute(input_data)

                # 應該回退到 Haversine
                assert isinstance(result, DistanceOutput)
                assert result.method == "driving"
                assert result.distance_km > 0
                assert result.duration is None
