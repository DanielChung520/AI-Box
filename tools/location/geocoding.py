# 代碼功能說明: 地理編碼工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""地理編碼工具

正向地理編碼（地址 → 坐標）和反向地理編碼（坐標 → 地址）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.cache import generate_cache_key, get_cache
from tools.utils.errors import ToolExecutionError, ToolValidationError
from tools.utils.validator import validate_coordinates, validate_non_empty_string

logger = structlog.get_logger(__name__)

# 緩存時間：7 天（604800 秒）
GEOCODING_CACHE_TTL = 604800.0


class GeocodingInput(ToolInput):
    """地理編碼輸入參數"""

    address: Optional[str] = None  # 地址（正向編碼）
    lat: Optional[float] = None  # 緯度（反向編碼）
    lon: Optional[float] = None  # 經度（反向編碼）
    language: str = "zh-TW"  # 結果語言
    provider: Optional[str] = None  # 地理編碼服務提供商（默認使用 Nominatim）


class GeocodingOutput(ToolOutput):
    """地理編碼輸出結果"""

    address: str  # 完整地址
    formatted_address: str  # 格式化地址
    latitude: float  # 緯度
    longitude: float  # 經度
    country: str  # 國家
    country_code: str  # 國家代碼
    region: Optional[str] = None  # 地區
    city: Optional[str] = None  # 城市
    district: Optional[str] = None  # 區/縣
    street: Optional[str] = None  # 街道
    postal_code: Optional[str] = None  # 郵政編碼
    place_id: Optional[str] = None  # 地點 ID（某些提供商）


class GeocodingTool(BaseTool[GeocodingInput, GeocodingOutput]):
    """地理編碼工具

    正向地理編碼（地址 → 坐標）和反向地理編碼（坐標 → 地址）。
    """

    def __init__(self, provider: Optional[str] = None) -> None:
        """
        初始化地理編碼工具

        Args:
            provider: 地理編碼服務提供商（默認使用 Nominatim）
        """
        self._provider = provider or "nominatim"
        self._base_url = "https://nominatim.openstreetmap.org"

    @property
    def name(self) -> str:
        """工具名稱"""
        return "geocoding"

    @property
    def description(self) -> str:
        """工具描述"""
        return "正向地理編碼（地址 → 坐標）和反向地理編碼（坐標 → 地址）"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _validate_input(self, input_data: GeocodingInput) -> None:
        """
        驗證輸入參數

        Args:
            input_data: 輸入參數

        Raises:
            ToolValidationError: 輸入參數驗證失敗
        """
        # 必須提供 address 或 lat/lon
        if not input_data.address and (input_data.lat is None or input_data.lon is None):
            raise ToolValidationError("Either address or lat/lon must be provided", field="address")

        # 驗證 address
        if input_data.address:
            validate_non_empty_string(input_data.address, "address")

        # 驗證坐標
        if input_data.lat is not None and input_data.lon is not None:
            if not validate_coordinates(input_data.lat, input_data.lon):
                raise ToolValidationError(
                    "Invalid coordinates: lat must be between -90 and 90, lon must be between -180 and 180",
                    field="lat",
                )

    async def _forward_geocode(self, address: str, language: str) -> GeocodingOutput:
        """
        正向地理編碼（地址 → 坐標）

        Args:
            address: 地址
            language: 結果語言

        Returns:
            地理編碼結果
        """
        try:
            url = f"{self._base_url}/search"
            params: Dict[str, str] = {
                "q": address,
                "format": "json",
                "limit": "1",
                "accept-language": language,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            if not data:
                raise ToolExecutionError(
                    f"No results found for address: {address}",
                    tool_name=self.name,
                )

            result = data[0]
            return self._parse_nominatim_result(result)

        except httpx.HTTPError as e:
            logger.error("geocoding_api_error", error=str(e))
            raise ToolExecutionError(
                f"Failed to geocode address: {str(e)}",
                tool_name=self.name,
            ) from e

    async def _reverse_geocode(self, lat: float, lon: float, language: str) -> GeocodingOutput:
        """
        反向地理編碼（坐標 → 地址）

        Args:
            lat: 緯度
            lon: 經度
            language: 結果語言

        Returns:
            地理編碼結果
        """
        try:
            url = f"{self._base_url}/reverse"
            params: Dict[str, str] = {
                "lat": str(lat),
                "lon": str(lon),
                "format": "json",
                "accept-language": language,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            if "error" in data:
                raise ToolExecutionError(
                    f"Reverse geocoding error: {data['error']}",
                    tool_name=self.name,
                )

            return self._parse_nominatim_result(data)

        except httpx.HTTPError as e:
            logger.error("reverse_geocoding_api_error", error=str(e))
            raise ToolExecutionError(
                f"Failed to reverse geocode coordinates: {str(e)}",
                tool_name=self.name,
            ) from e

    def _parse_nominatim_result(self, data: Dict[str, Any]) -> GeocodingOutput:
        """
        解析 Nominatim API 響應

        Args:
            data: API 響應數據

        Returns:
            地理編碼結果
        """
        address_data = data.get("address", {})
        lat = float(data.get("lat", 0.0))
        lon = float(data.get("lon", 0.0))

        return GeocodingOutput(
            address=data.get("display_name", ""),
            formatted_address=data.get("display_name", ""),
            latitude=lat,
            longitude=lon,
            country=address_data.get("country", "Unknown"),
            country_code=address_data.get("country_code", "Unknown"),
            region=address_data.get("state") or address_data.get("region"),
            city=address_data.get("city")
            or address_data.get("town")
            or address_data.get("village"),
            district=address_data.get("county"),
            street=address_data.get("road"),
            postal_code=address_data.get("postcode"),
            place_id=str(data.get("place_id", "")) if data.get("place_id") else None,
        )

    async def execute(self, input_data: GeocodingInput) -> GeocodingOutput:
        """
        執行地理編碼工具

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

            # 生成緩存鍵
            cache_key = generate_cache_key(
                "geocoding",
                address=input_data.address or "",
                lat=input_data.lat or 0.0,
                lon=input_data.lon or 0.0,
                language=input_data.language,
                provider=self._provider,
            )

            # 嘗試從緩存獲取
            cache = get_cache()
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug("geocoding_cache_hit", cache_key=cache_key)
                return GeocodingOutput(**cached_result)

            # 執行地理編碼
            if input_data.address:
                result = await self._forward_geocode(input_data.address, input_data.language)
            else:
                result = await self._reverse_geocode(
                    input_data.lat or 0.0, input_data.lon or 0.0, input_data.language
                )

            # 存入緩存
            cache.set(cache_key, result.model_dump(), ttl=GEOCODING_CACHE_TTL)

            return result

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("geocoding_tool_execution_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to execute geocoding tool: {str(e)}",
                tool_name=self.name,
            ) from e
