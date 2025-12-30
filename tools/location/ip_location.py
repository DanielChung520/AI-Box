# 代碼功能說明: IP 地址定位工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""IP 地址定位工具

根據 IP 地址獲取地理位置信息。
"""

from __future__ import annotations

from typing import Optional

import httpx
import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.cache import generate_cache_key, get_cache
from tools.utils.errors import ToolExecutionError, ToolValidationError
from tools.utils.validator import validate_ip_address

logger = structlog.get_logger(__name__)

# 緩存時間：24 小時（86400 秒）
IP_LOCATION_CACHE_TTL = 86400.0


class IPLocationInput(ToolInput):
    """IP 定位輸入參數"""

    ip: str  # IP 地址（IPv4 或 IPv6）
    provider: Optional[str] = None  # IP 定位服務提供商（默認使用 ip-api.com）


class IPLocationOutput(ToolOutput):
    """IP 定位輸出結果"""

    ip: str  # IP 地址
    country: str  # 國家名稱
    country_code: str  # 國家代碼（ISO 3166-1 alpha-2）
    region: Optional[str] = None  # 地區/州
    city: Optional[str] = None  # 城市
    latitude: Optional[float] = None  # 緯度
    longitude: Optional[float] = None  # 經度
    timezone: Optional[str] = None  # 時區
    isp: Optional[str] = None  # ISP 提供商
    org: Optional[str] = None  # 組織


class IPLocationTool(BaseTool[IPLocationInput, IPLocationOutput]):
    """IP 地址定位工具

    根據 IP 地址獲取地理位置信息。
    """

    def __init__(self, provider: Optional[str] = None) -> None:
        """
        初始化 IP 定位工具

        Args:
            provider: IP 定位服務提供商（默認使用 ip-api.com）
        """
        self._provider = provider or "ip-api"

    @property
    def name(self) -> str:
        """工具名稱"""
        return "ip_location"

    @property
    def description(self) -> str:
        """工具描述"""
        return "根據 IP 地址獲取地理位置信息"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _validate_input(self, input_data: IPLocationInput) -> None:
        """
        驗證輸入參數

        Args:
            input_data: 輸入參數

        Raises:
            ToolValidationError: 輸入參數驗證失敗
        """
        if not validate_ip_address(input_data.ip):
            raise ToolValidationError(f"Invalid IP address: {input_data.ip}", field="ip")

    async def _get_location_from_ip_api(self, ip: str) -> IPLocationOutput:
        """
        從 ip-api.com 獲取位置信息

        Args:
            ip: IP 地址

        Returns:
            位置信息

        Raises:
            ToolExecutionError: 獲取位置信息失敗
        """
        try:
            url = f"http://ip-api.com/json/{ip}"
            params = {
                "fields": "status,message,country,countryCode,region,regionName,city,lat,lon,timezone,isp,org"
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            if data.get("status") == "fail":
                raise ToolExecutionError(
                    f"IP API error: {data.get('message', 'Unknown error')}",
                    tool_name=self.name,
                )

            return IPLocationOutput(
                ip=ip,
                country=data.get("country", "Unknown"),
                country_code=data.get("countryCode", "Unknown"),
                region=data.get("regionName"),
                city=data.get("city"),
                latitude=data.get("lat"),
                longitude=data.get("lon"),
                timezone=data.get("timezone"),
                isp=data.get("isp"),
                org=data.get("org"),
            )

        except httpx.HTTPError as e:
            logger.error("ip_api_error", error=str(e))
            raise ToolExecutionError(
                f"Failed to fetch IP location: {str(e)}",
                tool_name=self.name,
            ) from e

    async def execute(self, input_data: IPLocationInput) -> IPLocationOutput:
        """
        執行 IP 定位工具

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
                "ip_location",
                ip=input_data.ip,
                provider=self._provider,
            )

            # 嘗試從緩存獲取
            cache = get_cache()
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug("ip_location_cache_hit", cache_key=cache_key)
                return IPLocationOutput(**cached_result)

            # 獲取位置信息
            if self._provider == "ip-api":
                result = await self._get_location_from_ip_api(input_data.ip)
            else:
                raise ToolExecutionError(
                    f"Unsupported provider: {self._provider}",
                    tool_name=self.name,
                )

            # 存入緩存
            cache.set(cache_key, result.model_dump(), ttl=IP_LOCATION_CACHE_TTL)

            return result

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("ip_location_tool_execution_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to execute IP location tool: {str(e)}",
                tool_name=self.name,
            ) from e
