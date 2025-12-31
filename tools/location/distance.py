# 代碼功能說明: 距離計算工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""距離計算工具

計算兩個地理位置之間的距離（支持 Haversine、駕車、步行等方法）。
"""

from __future__ import annotations

import math
import os
from typing import Any, Dict, Optional

import httpx
import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError
from tools.utils.validator import validate_coordinates

logger = structlog.get_logger(__name__)


class DistanceInput(ToolInput):
    """距離計算輸入參數"""

    lat1: float  # 起點緯度
    lon1: float  # 起點經度
    lat2: float  # 終點緯度
    lon2: float  # 終點經度
    method: str = "haversine"  # 計算方法：haversine, driving, walking
    unit: str = "km"  # 單位：km, mile, meter
    provider: Optional[str] = (
        None  # 地圖服務提供商（用於 driving/walking，默認使用 OpenRouteService）
    )


class DistanceOutput(ToolOutput):
    """距離計算輸出結果"""

    distance: float  # 距離（指定單位）
    distance_km: float  # 距離（公里）
    distance_mile: float  # 距離（英里）
    distance_meter: float  # 距離（米）
    method: str  # 使用的計算方法
    duration: Optional[float] = None  # 預計時間（秒，僅 driving/walking）
    route: Optional[Dict[str, Any]] = None  # 路線信息（僅 driving/walking，可選）


class DistanceTool(BaseTool[DistanceInput, DistanceOutput]):
    """距離計算工具

    計算兩個地理位置之間的距離（支持 Haversine、駕車、步行等方法）。
    """

    # 地球半徑（公里）
    EARTH_RADIUS_KM = 6371.0

    # OpenRouteService API 基礎 URL
    ORS_BASE_URL = "https://api.openrouteservice.org/v2/directions"

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        初始化距離計算工具

        Args:
            api_key: OpenRouteService API 密鑰（可選，如果不提供則不使用 API，僅支持 Haversine）
        """
        self._api_key = api_key or os.getenv("OPENROUTESERVICE_API_KEY")

    @property
    def name(self) -> str:
        """工具名稱"""
        return "distance"

    @property
    def description(self) -> str:
        """工具描述"""
        return "計算兩個地理位置之間的距離（支持 Haversine、駕車、步行等方法）"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _validate_input(self, input_data: DistanceInput) -> None:
        """
        驗證輸入參數

        Args:
            input_data: 輸入參數

        Raises:
            ToolValidationError: 輸入參數驗證失敗
        """
        # 驗證坐標
        if not validate_coordinates(input_data.lat1, input_data.lon1):
            raise ToolValidationError(
                "Invalid coordinates for point 1: lat must be between -90 and 90, lon must be between -180 and 180",
                field="lat1",
            )

        if not validate_coordinates(input_data.lat2, input_data.lon2):
            raise ToolValidationError(
                "Invalid coordinates for point 2: lat must be between -90 and 90, lon must be between -180 and 180",
                field="lat2",
            )

        # 驗證方法
        if input_data.method not in ["haversine", "driving", "walking"]:
            raise ToolValidationError(
                f"Unsupported method: {input_data.method}. Supported methods: haversine, driving, walking",
                field="method",
            )

        # 驗證單位
        if input_data.unit not in ["km", "mile", "meter"]:
            raise ToolValidationError(
                "unit must be 'km', 'mile', or 'meter'",
                field="unit",
            )

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        使用 Haversine 公式計算兩點之間的距離（公里）

        Args:
            lat1: 起點緯度
            lon1: 起點經度
            lat2: 終點緯度
            lon2: 終點經度

        Returns:
            距離（公里）
        """
        # 將度數轉換為弧度
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # 計算差值
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Haversine 公式
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # 計算距離（公里）
        distance_km = self.EARTH_RADIUS_KM * c

        return distance_km

    def _convert_distance(self, distance_km: float, unit: str) -> float:
        """
        轉換距離單位

        Args:
            distance_km: 距離（公里）
            unit: 目標單位

        Returns:
            轉換後的距離
        """
        if unit == "km":
            return distance_km
        elif unit == "mile":
            return distance_km * 0.621371  # 1 公里 = 0.621371 英里
        elif unit == "meter":
            return distance_km * 1000.0  # 1 公里 = 1000 米
        else:
            return distance_km

    async def _driving_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> tuple[float, Optional[float], Optional[Dict[str, Any]]]:
        """
        使用 OpenRouteService API 計算駕車距離

        Args:
            lat1: 起點緯度
            lon1: 起點經度
            lat2: 終點緯度
            lon2: 終點經度

        Returns:
            距離（公里）、預計時間（秒）、路線信息（可選）的元組

        Raises:
            ToolExecutionError: API 調用失敗
        """
        if not self._api_key:
            logger.warning("openrouteservice_api_key_not_provided")
            # 回退到 Haversine
            distance_km = self._haversine_distance(lat1, lon1, lat2, lon2)
            return distance_km, None, None

        try:
            url = f"{self.ORS_BASE_URL}/driving-car"
            headers: Dict[str, str] = {}
            if self._api_key:
                headers["Authorization"] = self._api_key

            body = {
                "coordinates": [[lon1, lat1], [lon2, lat2]],
                "units": "km",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=body, headers=headers)
                response.raise_for_status()
                data = response.json()

            # 解析響應
            routes = data.get("routes", [])
            if not routes:
                raise ToolExecutionError("No routes found", tool_name=self.name)

            route = routes[0]
            summary = route.get("summary", {})
            distance_km = summary.get("distance", 0.0) / 1000.0  # 轉換為公里
            duration_seconds = summary.get("duration", None)

            # 提取路線信息（簡化版本）
            route_info: Dict[str, Any] = {
                "distance": distance_km,
                "duration": duration_seconds,
            }

            return distance_km, duration_seconds, route_info

        except httpx.HTTPError as e:
            logger.warning("openrouteservice_api_error", error=str(e))
            # 回退到 Haversine
            distance_km = self._haversine_distance(lat1, lon1, lat2, lon2)
            return distance_km, None, None
        except Exception as e:
            logger.warning("openrouteservice_parse_error", error=str(e))
            # 回退到 Haversine
            distance_km = self._haversine_distance(lat1, lon1, lat2, lon2)
            return distance_km, None, None

    async def _walking_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> tuple[float, Optional[float], Optional[Dict[str, Any]]]:
        """
        使用 OpenRouteService API 計算步行距離

        Args:
            lat1: 起點緯度
            lon1: 起點經度
            lat2: 終點緯度
            lon2: 終點經度

        Returns:
            距離（公里）、預計時間（秒）、路線信息（可選）的元組

        Raises:
            ToolExecutionError: API 調用失敗
        """
        if not self._api_key:
            logger.warning("openrouteservice_api_key_not_provided")
            # 回退到 Haversine
            distance_km = self._haversine_distance(lat1, lon1, lat2, lon2)
            return distance_km, None, None

        try:
            url = f"{self.ORS_BASE_URL}/foot-walking"
            headers: Dict[str, str] = {}
            if self._api_key:
                headers["Authorization"] = self._api_key

            body = {
                "coordinates": [[lon1, lat1], [lon2, lat2]],
                "units": "km",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=body, headers=headers)
                response.raise_for_status()
                data = response.json()

            # 解析響應
            routes = data.get("routes", [])
            if not routes:
                raise ToolExecutionError("No routes found", tool_name=self.name)

            route = routes[0]
            summary = route.get("summary", {})
            distance_km = summary.get("distance", 0.0) / 1000.0  # 轉換為公里
            duration_seconds = summary.get("duration", None)

            # 提取路線信息（簡化版本）
            route_info: Dict[str, Any] = {
                "distance": distance_km,
                "duration": duration_seconds,
            }

            return distance_km, duration_seconds, route_info

        except httpx.HTTPError as e:
            logger.warning("openrouteservice_api_error", error=str(e))
            # 回退到 Haversine
            distance_km = self._haversine_distance(lat1, lon1, lat2, lon2)
            return distance_km, None, None
        except Exception as e:
            logger.warning("openrouteservice_parse_error", error=str(e))
            # 回退到 Haversine
            distance_km = self._haversine_distance(lat1, lon1, lat2, lon2)
            return distance_km, None, None

    async def execute(self, input_data: DistanceInput) -> DistanceOutput:
        """
        執行距離計算工具

        Args:
            input_data: 工具輸入參數

        Returns:
            工具輸出結果

        Raises:
            ToolExecutionError: 工具執行失敗
            ToolValidationError: 輸入參數驗證失敗
        """
        try:
            # 驗證輸入
            self._validate_input(input_data)

            # 根據方法計算距離
            if input_data.method == "haversine":
                distance_km = self._haversine_distance(
                    input_data.lat1,
                    input_data.lon1,
                    input_data.lat2,
                    input_data.lon2,
                )
                duration = None
                route = None
            elif input_data.method == "driving":
                distance_km, duration, route = await self._driving_distance(
                    input_data.lat1,
                    input_data.lon1,
                    input_data.lat2,
                    input_data.lon2,
                )
            elif input_data.method == "walking":
                distance_km, duration, route = await self._walking_distance(
                    input_data.lat1,
                    input_data.lon1,
                    input_data.lat2,
                    input_data.lon2,
                )
            else:
                # 不應該到達這裡（已經驗證），但為了類型安全
                raise ToolValidationError(
                    f"Unsupported method: {input_data.method}", field="method"
                )

            # 轉換為指定單位
            distance = self._convert_distance(distance_km, input_data.unit)

            # 計算其他單位的距離
            distance_mile = self._convert_distance(distance_km, "mile")
            distance_meter = self._convert_distance(distance_km, "meter")

            return DistanceOutput(
                distance=distance,
                distance_km=distance_km,
                distance_mile=distance_mile,
                distance_meter=distance_meter,
                method=input_data.method,
                duration=duration,
                route=route,
            )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("distance_tool_execution_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to execute distance tool: {str(e)}",
                tool_name=self.name,
            ) from e
