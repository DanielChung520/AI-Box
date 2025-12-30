# 代碼功能說明: 天氣工具模組初始化
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""天氣工具模組

提供天氣查詢和預報功能。
"""

__all__ = [
    "WeatherTool",
    "WeatherInput",
    "WeatherOutput",
    "WeatherProvider",
    "ForecastTool",
    "ForecastInput",
    "ForecastOutput",
    "ForecastItem",
    "HourlyForecast",
]

from tools.weather.forecast_tool import (
    ForecastInput,
    ForecastItem,
    ForecastOutput,
    ForecastTool,
    HourlyForecast,
)
from tools.weather.providers.base import WeatherProvider
from tools.weather.weather_tool import WeatherInput, WeatherOutput, WeatherTool
