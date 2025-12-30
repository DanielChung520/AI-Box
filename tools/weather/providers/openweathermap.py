# 代碼功能說明: OpenWeatherMap 天氣提供商實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""OpenWeatherMap 天氣提供商實現"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
import structlog

from tools.utils.errors import ToolConfigurationError, ToolExecutionError
from tools.weather.providers.base import (
    ForecastData,
    ForecastItemData,
    HourlyForecastData,
    WeatherData,
    WeatherProvider,
)

logger = structlog.get_logger(__name__)


class OpenWeatherMapProvider(WeatherProvider):
    """OpenWeatherMap 天氣提供商"""

    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
    FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        初始化 OpenWeatherMap 提供商

        Args:
            api_key: API 密鑰，如果為 None 則從環境變數獲取
        """
        self._api_key = api_key or os.getenv("OPENWEATHERMAP_API_KEY")
        if not self._api_key:
            raise ToolConfigurationError(
                "OpenWeatherMap API key not provided. Set OPENWEATHERMAP_API_KEY environment variable or pass api_key parameter.",
                tool_name="OpenWeatherMapProvider",
            )

    async def get_current_weather(
        self,
        city: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        units: str = "metric",
    ) -> WeatherData:
        """
        獲取當前天氣

        Args:
            city: 城市名稱
            lat: 緯度
            lon: 經度
            units: 單位（metric 或 imperial）

        Returns:
            天氣數據

        Raises:
            ToolExecutionError: 獲取天氣數據失敗
        """
        try:
            # 構建查詢參數
            params: Dict[str, Any] = {
                "appid": self._api_key,
                "units": units,
            }

            if city:
                params["q"] = city
            elif lat is not None and lon is not None:
                params["lat"] = str(lat)
                params["lon"] = str(lon)
            else:
                raise ToolExecutionError(
                    "Either city or lat/lon must be provided",
                    tool_name="OpenWeatherMapProvider",
                )

            # 發送請求
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            # 解析響應
            return self._parse_response(data, units)

        except httpx.HTTPError as e:
            logger.error("openweathermap_api_error", error=str(e))
            raise ToolExecutionError(
                f"Failed to fetch weather data from OpenWeatherMap: {str(e)}",
                tool_name="OpenWeatherMapProvider",
            ) from e
        except Exception as e:
            logger.error("openweathermap_parse_error", error=str(e))
            raise ToolExecutionError(
                f"Failed to parse weather data: {str(e)}",
                tool_name="OpenWeatherMapProvider",
            ) from e

    def _parse_response(self, data: Dict[str, Any], units: str) -> WeatherData:
        """
        解析 OpenWeatherMap API 響應

        Args:
            data: API 響應數據
            units: 單位

        Returns:
            天氣數據
        """
        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        wind = data.get("wind", {})
        sys_data = data.get("sys", {})

        return WeatherData(
            city=data.get("name", "Unknown"),
            country=sys_data.get("country", "Unknown"),
            temperature=main.get("temp", 0.0),
            feels_like=main.get("feels_like", 0.0),
            humidity=main.get("humidity", 0),
            pressure=main.get("pressure", 0),
            description=weather.get("description", ""),
            icon=weather.get("icon", ""),
            wind_speed=wind.get("speed", 0.0),
            wind_direction=wind.get("deg", 0),
            visibility=data.get("visibility"),
            uv_index=None,  # OpenWeatherMap 免費版不提供 UV 指數
            timestamp=float(data.get("dt", 0)),
        )

    async def get_forecast(
        self,
        city: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 3,
        hourly: bool = False,
        units: str = "metric",
    ) -> ForecastData:
        """
        獲取天氣預報

        Args:
            city: 城市名稱
            lat: 緯度
            lon: 經度
            days: 預報天數（1-7）
            hourly: 是否獲取小時級別預報
            units: 單位（metric 或 imperial）

        Returns:
            預報數據

        Raises:
            ToolExecutionError: 獲取預報數據失敗
        """
        try:
            # 驗證 days 參數
            if days < 1 or days > 7:
                raise ToolExecutionError(
                    "days must be between 1 and 7", tool_name="OpenWeatherMapProvider"
                )

            # 構建查詢參數
            params: Dict[str, Any] = {
                "appid": self._api_key,
                "units": units,
            }

            if city:
                params["q"] = city
            elif lat is not None and lon is not None:
                params["lat"] = str(lat)
                params["lon"] = str(lon)
            else:
                raise ToolExecutionError(
                    "Either city or lat/lon must be provided",
                    tool_name="OpenWeatherMapProvider",
                )

            # 發送請求
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.FORECAST_URL, params=params)
                response.raise_for_status()
                data = response.json()

            # 解析響應
            return self._parse_forecast_response(data, days, hourly, units)

        except httpx.HTTPError as e:
            logger.error("openweathermap_forecast_api_error", error=str(e))
            raise ToolExecutionError(
                f"Failed to fetch forecast data from OpenWeatherMap: {str(e)}",
                tool_name="OpenWeatherMapProvider",
            ) from e
        except Exception as e:
            logger.error("openweathermap_forecast_parse_error", error=str(e))
            raise ToolExecutionError(
                f"Failed to parse forecast data: {str(e)}",
                tool_name="OpenWeatherMapProvider",
            ) from e

    def _parse_forecast_response(
        self, data: Dict[str, Any], days: int, hourly: bool, units: str
    ) -> ForecastData:
        """
        解析 OpenWeatherMap 預報 API 響應

        Args:
            data: API 響應數據
            days: 預報天數
            hourly: 是否包含小時級別預報
            units: 單位

        Returns:
            預報數據
        """
        city_info = data.get("city", {})
        city_name = city_info.get("name", "Unknown")
        country_code = city_info.get("country", "Unknown")

        # 獲取所有預報項（每 3 小時一個數據點）
        list_data = data.get("list", [])

        # 按日期聚合預報數據
        daily_forecasts: Dict[str, list[Dict[str, Any]]] = defaultdict(list)

        for item in list_data:
            timestamp = item.get("dt", 0)
            dt = datetime.fromtimestamp(timestamp)
            date_key = dt.strftime("%Y-%m-%d")
            daily_forecasts[date_key].append(item)

        # 生成每日預報列表
        forecast_items: list[ForecastItemData] = []
        hourly_forecasts_list: list[HourlyForecastData] = []

        # 按日期排序並取前 days 天
        sorted_dates = sorted(daily_forecasts.keys())[:days]

        for date_key in sorted_dates:
            day_items = daily_forecasts[date_key]

            # 計算每日的平均/最大/最小溫度
            min_temps = [item.get("main", {}).get("temp_min", 0.0) for item in day_items]
            max_temps = [item.get("main", {}).get("temp_max", 0.0) for item in day_items]

            # 使用中午時段的數據作為代表（最接近 12:00 的）
            noon_item = min(
                day_items,
                key=lambda x: abs(datetime.fromtimestamp(x.get("dt", 0)).hour - 12),
            )

            main_data = noon_item.get("main", {})
            weather_data = noon_item.get("weather", [{}])[0]
            wind_data = noon_item.get("wind", {})
            rain_data = noon_item.get("rain", {})
            snow_data = noon_item.get("snow", {})

            # 計算降水量（mm）
            precipitation = None
            if rain_data:
                precipitation = rain_data.get("3h", 0.0)
            elif snow_data:
                precipitation = snow_data.get("3h", 0.0)

            forecast_item = ForecastItemData(
                date=date_key,
                temperature=main_data.get("temp", 0.0),
                min_temp=min(min_temps) if min_temps else main_data.get("temp_min", 0.0),
                max_temp=max(max_temps) if max_temps else main_data.get("temp_max", 0.0),
                description=weather_data.get("description", ""),
                icon=weather_data.get("icon", ""),
                humidity=main_data.get("humidity", 0),
                wind_speed=wind_data.get("speed", 0.0),
                precipitation=precipitation,
                timestamp=float(noon_item.get("dt", 0)),
            )
            forecast_items.append(forecast_item)

            # 如果請求小時級別預報，添加該日的小時預報
            if hourly:
                for item in day_items:
                    item_main = item.get("main", {})
                    item_weather = item.get("weather", [{}])[0]
                    item_wind = item.get("wind", {})
                    item_rain = item.get("rain", {})
                    item_snow = item.get("snow", {})

                    item_precipitation = None
                    if item_rain:
                        item_precipitation = item_rain.get("3h", 0.0)
                    elif item_snow:
                        item_precipitation = item_snow.get("3h", 0.0)

                    item_timestamp = item.get("dt", 0)
                    item_dt = datetime.fromtimestamp(item_timestamp)

                    hourly_forecast = HourlyForecastData(
                        time=item_dt.isoformat(),
                        temperature=item_main.get("temp", 0.0),
                        description=item_weather.get("description", ""),
                        icon=item_weather.get("icon", ""),
                        humidity=item_main.get("humidity", 0),
                        wind_speed=item_wind.get("speed", 0.0),
                        precipitation=item_precipitation,
                        timestamp=float(item_timestamp),
                    )
                    hourly_forecasts_list.append(hourly_forecast)

        return ForecastData(
            city=city_name,
            country=country_code,
            forecasts=forecast_items,
            hourly_forecasts=hourly_forecasts_list if hourly else None,
        )
