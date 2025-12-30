# 代碼功能說明: 天氣提供商基類
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""天氣提供商基類

定義天氣 API 提供商的統一接口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel


class WeatherData(BaseModel):
    """天氣數據模型"""

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


class ForecastItemData(BaseModel):
    """預報項數據模型"""

    date: str  # 日期（ISO 8601）
    temperature: float  # 溫度
    min_temp: float  # 最低溫度
    max_temp: float  # 最高溫度
    description: str  # 天氣描述
    icon: str  # 天氣圖標
    humidity: int  # 濕度（百分比）
    wind_speed: float  # 風速
    precipitation: Optional[float] = None  # 降水量（mm）
    timestamp: float  # 數據時間戳


class HourlyForecastData(BaseModel):
    """小時級別預報數據模型"""

    time: str  # 時間（ISO 8601）
    temperature: float  # 溫度
    description: str  # 天氣描述
    icon: str  # 天氣圖標
    humidity: int  # 濕度（百分比）
    wind_speed: float  # 風速
    precipitation: Optional[float] = None  # 降水量（mm）
    timestamp: float  # 數據時間戳


class ForecastData(BaseModel):
    """預報數據模型"""

    city: str  # 城市名稱
    country: str  # 國家代碼
    forecasts: List[ForecastItemData]  # 預報列表
    hourly_forecasts: Optional[List[HourlyForecastData]] = None  # 小時級別預報（可選）


class WeatherProvider(ABC):
    """天氣 API 提供商基類"""

    @abstractmethod
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
            Exception: 獲取天氣數據失敗
        """
        pass

    @abstractmethod
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
            Exception: 獲取預報數據失敗
        """
        pass
