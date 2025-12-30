# 代碼功能說明: 天氣查詢工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""天氣查詢工具

根據城市名稱或經緯度獲取當前天氣信息。
"""

from __future__ import annotations

from typing import Optional

import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.cache import generate_cache_key, get_cache
from tools.utils.errors import ToolExecutionError, ToolValidationError
from tools.utils.validator import validate_coordinates, validate_non_empty_string
from tools.weather.providers.openweathermap import OpenWeatherMapProvider

logger = structlog.get_logger(__name__)

# 緩存時間：10 分鐘（600 秒）
WEATHER_CACHE_TTL = 600.0


class WeatherInput(ToolInput):
    """天氣查詢輸入參數"""

    city: Optional[str] = None  # 城市名稱（如 "Taipei"）
    lat: Optional[float] = None  # 緯度
    lon: Optional[float] = None  # 經度
    units: str = "metric"  # 單位：metric (攝氏度), imperial (華氏度)
    provider: Optional[str] = None  # 天氣 API 提供商（如 "openweathermap"）


class WeatherOutput(ToolOutput):
    """天氣查詢輸出結果"""

    city: str  # 城市名稱
    country: str  # 國家代碼
    temperature: float  # 溫度
    feels_like: float  # 體感溫度
    humidity: int  # 濕度（百分比）
    pressure: int  # 氣壓（hPa）
    description: str  # 天氣描述
    icon: str  # 天氣圖標代碼
    wind_speed: float  # 風速
    wind_direction: int  # 風向（度數）
    visibility: Optional[int] = None  # 能見度（米）
    uv_index: Optional[float] = None  # UV 指數
    timestamp: float  # 數據時間戳


class WeatherTool(BaseTool[WeatherInput, WeatherOutput]):
    """天氣查詢工具

    根據城市名稱或經緯度獲取當前天氣信息。
    """

    def __init__(self, provider: Optional[str] = None) -> None:
        """
        初始化天氣查詢工具

        Args:
            provider: 天氣提供商名稱（默認使用 OpenWeatherMap）
        """
        self._provider_name = provider or "openweathermap"
        self._provider = self._create_provider()

    def _create_provider(self) -> OpenWeatherMapProvider:
        """
        創建天氣提供商實例

        Returns:
            天氣提供商實例
        """
        if self._provider_name == "openweathermap":
            return OpenWeatherMapProvider()
        else:
            raise ToolExecutionError(
                f"Unsupported weather provider: {self._provider_name}",
                tool_name=self.name,
            )

    @property
    def name(self) -> str:
        """工具名稱"""
        return "weather"

    @property
    def description(self) -> str:
        """工具描述"""
        return "根據城市名稱或經緯度獲取當前天氣信息"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _validate_input(self, input_data: WeatherInput) -> None:
        """
        驗證輸入參數

        Args:
            input_data: 輸入參數

        Raises:
            ToolValidationError: 輸入參數驗證失敗
        """
        # 必須提供 city 或 lat/lon
        if not input_data.city and (input_data.lat is None or input_data.lon is None):
            raise ToolValidationError("Either city or lat/lon must be provided", field="city")

        # 驗證 city
        if input_data.city:
            validate_non_empty_string(input_data.city, "city")

        # 驗證坐標
        if input_data.lat is not None and input_data.lon is not None:
            if not validate_coordinates(input_data.lat, input_data.lon):
                raise ToolValidationError(
                    "Invalid coordinates: lat must be between -90 and 90, lon must be between -180 and 180",
                    field="lat",
                )

        # 驗證 units
        if input_data.units not in ["metric", "imperial"]:
            raise ToolValidationError("units must be 'metric' or 'imperial'", field="units")

    async def execute(self, input_data: WeatherInput) -> WeatherOutput:
        """
        執行天氣查詢工具

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
                "weather",
                city=input_data.city or "",
                lat=input_data.lat or 0.0,
                lon=input_data.lon or 0.0,
                units=input_data.units,
                provider=self._provider_name,
            )

            # 嘗試從緩存獲取
            cache = get_cache()
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug("weather_cache_hit", cache_key=cache_key)
                return WeatherOutput(**cached_result)

            # 獲取天氣數據
            weather_data = await self._provider.get_current_weather(
                city=input_data.city,
                lat=input_data.lat,
                lon=input_data.lon,
                units=input_data.units,
            )

            # 轉換為輸出格式
            output = WeatherOutput(
                city=weather_data.city,
                country=weather_data.country,
                temperature=weather_data.temperature,
                feels_like=weather_data.feels_like,
                humidity=weather_data.humidity,
                pressure=weather_data.pressure,
                description=weather_data.description,
                icon=weather_data.icon,
                wind_speed=weather_data.wind_speed,
                wind_direction=weather_data.wind_direction,
                visibility=weather_data.visibility,
                uv_index=weather_data.uv_index,
                timestamp=weather_data.timestamp,
            )

            # 存入緩存
            cache.set(cache_key, output.model_dump(), ttl=WEATHER_CACHE_TTL)

            return output

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("weather_tool_execution_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to execute weather tool: {str(e)}", tool_name=self.name
            ) from e
