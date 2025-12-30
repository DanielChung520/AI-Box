# 代碼功能說明: 天氣預報工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""天氣預報工具

獲取未來幾天的天氣預報。
"""

from __future__ import annotations

from typing import List, Optional

import structlog
from pydantic import BaseModel

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.cache import generate_cache_key, get_cache
from tools.utils.errors import ToolExecutionError, ToolValidationError
from tools.utils.validator import validate_coordinates, validate_non_empty_string
from tools.weather.providers.base import ForecastData
from tools.weather.providers.openweathermap import OpenWeatherMapProvider

logger = structlog.get_logger(__name__)

# 緩存時間：1 小時（3600 秒）
FORECAST_CACHE_TTL = 3600.0


class HourlyForecast(BaseModel):
    """小時級別預報項"""

    time: str  # 時間（ISO 8601）
    temperature: float  # 溫度
    description: str  # 天氣描述
    icon: str  # 天氣圖標
    humidity: int  # 濕度（百分比）
    wind_speed: float  # 風速
    precipitation: Optional[float] = None  # 降水量（mm）
    timestamp: float  # 數據時間戳


class ForecastItem(BaseModel):
    """單個預報項"""

    date: str  # 日期（ISO 8601）
    temperature: float  # 溫度
    min_temp: float  # 最低溫度
    max_temp: float  # 最高溫度
    description: str  # 天氣描述
    icon: str  # 天氣圖標
    humidity: int  # 濕度（百分比）
    wind_speed: float  # 風速
    precipitation: Optional[float] = None  # 降水量（mm）
    hourly: Optional[List[HourlyForecast]] = None  # 小時級別預報
    timestamp: float  # 數據時間戳


class ForecastInput(ToolInput):
    """天氣預報輸入參數"""

    city: Optional[str] = None  # 城市名稱（如 "Taipei"）
    lat: Optional[float] = None  # 緯度
    lon: Optional[float] = None  # 經度
    days: int = 3  # 預報天數（1-7）
    hourly: bool = False  # 是否獲取小時級別預報
    units: str = "metric"  # 單位：metric (攝氏度), imperial (華氏度)
    provider: Optional[str] = None  # 天氣 API 提供商（如 "openweathermap"）


class ForecastOutput(ToolOutput):
    """天氣預報輸出結果"""

    city: str  # 城市名稱
    country: str  # 國家代碼
    forecasts: List[ForecastItem]  # 預報列表


class ForecastTool(BaseTool[ForecastInput, ForecastOutput]):
    """天氣預報工具

    獲取未來幾天的天氣預報。
    """

    def __init__(self, provider: Optional[str] = None) -> None:
        """
        初始化天氣預報工具

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
        return "forecast"

    @property
    def description(self) -> str:
        """工具描述"""
        return "獲取未來幾天的天氣預報"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _validate_input(self, input_data: ForecastInput) -> None:
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

        # 驗證 days
        if input_data.days < 1 or input_data.days > 7:
            raise ToolValidationError("days must be between 1 and 7", field="days")

        # 驗證 units
        if input_data.units not in ["metric", "imperial"]:
            raise ToolValidationError("units must be 'metric' or 'imperial'", field="units")

    def _convert_forecast_data(self, forecast_data: ForecastData) -> ForecastOutput:
        """
        轉換預報數據格式

        Args:
            forecast_data: 提供商返回的預報數據

        Returns:
            工具輸出格式的預報數據
        """
        forecast_items: List[ForecastItem] = []

        # 如果有小時級別預報，按日期分組
        hourly_by_date: dict[str, List[HourlyForecast]] = {}
        if forecast_data.hourly_forecasts:
            for hourly in forecast_data.hourly_forecasts:
                # 從時間戳提取日期
                from datetime import datetime

                date_key = datetime.fromtimestamp(hourly.timestamp).strftime("%Y-%m-%d")
                if date_key not in hourly_by_date:
                    hourly_by_date[date_key] = []
                hourly_by_date[date_key].append(
                    HourlyForecast(
                        time=hourly.time,
                        temperature=hourly.temperature,
                        description=hourly.description,
                        icon=hourly.icon,
                        humidity=hourly.humidity,
                        wind_speed=hourly.wind_speed,
                        precipitation=hourly.precipitation,
                        timestamp=hourly.timestamp,
                    )
                )

        # 轉換每日預報
        for item in forecast_data.forecasts:
            hourly_list = hourly_by_date.get(item.date)
            forecast_items.append(
                ForecastItem(
                    date=item.date,
                    temperature=item.temperature,
                    min_temp=item.min_temp,
                    max_temp=item.max_temp,
                    description=item.description,
                    icon=item.icon,
                    humidity=item.humidity,
                    wind_speed=item.wind_speed,
                    precipitation=item.precipitation,
                    hourly=hourly_list,
                    timestamp=item.timestamp,
                )
            )

        return ForecastOutput(
            city=forecast_data.city,
            country=forecast_data.country,
            forecasts=forecast_items,
        )

    async def execute(self, input_data: ForecastInput) -> ForecastOutput:
        """
        執行天氣預報工具

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
                "forecast",
                city=input_data.city or "",
                lat=input_data.lat or 0.0,
                lon=input_data.lon or 0.0,
                days=input_data.days,
                hourly=input_data.hourly,
                units=input_data.units,
                provider=self._provider_name,
            )

            # 嘗試從緩存獲取
            cache = get_cache()
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug("forecast_cache_hit", cache_key=cache_key)
                return ForecastOutput(**cached_result)

            # 獲取預報數據
            forecast_data = await self._provider.get_forecast(
                city=input_data.city,
                lat=input_data.lat,
                lon=input_data.lon,
                days=input_data.days,
                hourly=input_data.hourly,
                units=input_data.units,
            )

            # 轉換為輸出格式
            output = self._convert_forecast_data(forecast_data)

            # 存入緩存
            cache.set(cache_key, output.model_dump(), ttl=FORECAST_CACHE_TTL)

            return output

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("forecast_tool_execution_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to execute forecast tool: {str(e)}", tool_name=self.name
            ) from e
