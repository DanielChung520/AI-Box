# 代碼功能說明: Tools 工具組模組初始化
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""Tools 工具組模組

提供各種工具功能，包括時間日期、天氣、地理位置、單位轉換、計算、文本處理等。
"""

from typing import Optional

__all__ = [
    # 基礎類和註冊表
    "BaseTool",
    "ToolInput",
    "ToolOutput",
    "ToolRegistry",
    "get_tool_registry",
    # 時間工具
    "TimeService",
    "get_time_service",
    "get_smart_time_service",  # 向後兼容
    "DateTimeTool",
    "DateTimeInput",
    "DateTimeOutput",
    "DateFormatter",
    "FormatInput",
    "FormatOutput",
    "DateCalculator",
    "CalculateInput",
    "CalculateOutput",
    # 天氣工具
    "WeatherTool",
    "WeatherInput",
    "WeatherOutput",
    "ForecastTool",
    "ForecastInput",
    "ForecastOutput",
    "ForecastItem",
    "HourlyForecast",
    # 地理位置工具
    "IPLocationTool",
    "IPLocationInput",
    "IPLocationOutput",
    "GeocodingTool",
    "GeocodingInput",
    "GeocodingOutput",
    "DistanceTool",
    "DistanceInput",
    "DistanceOutput",
    "TimezoneTool",
    "TimezoneInput",
    "TimezoneOutput",
    # 單位轉換工具
    "LengthConverter",
    "LengthInput",
    "LengthOutput",
    "WeightConverter",
    "WeightInput",
    "WeightOutput",
    "TemperatureConverter",
    "TemperatureInput",
    "TemperatureOutput",
    "CurrencyConverter",
    "CurrencyInput",
    "CurrencyOutput",
    "VolumeConverter",
    "VolumeInput",
    "VolumeOutput",
    "AreaConverter",
    "AreaInput",
    "AreaOutput",
    # 計算工具
    "MathCalculator",
    "MathInput",
    "MathOutput",
    "StatisticsCalculator",
    "StatisticsInput",
    "StatisticsOutput",
    # 文本處理工具
    "TextFormatter",
    "TextFormatterInput",
    "TextFormatterOutput",
    "TextCleaner",
    "TextCleanerInput",
    "TextCleanerOutput",
    "TextConverter",
    "TextConverterInput",
    "TextConverterOutput",
    "TextSummarizer",
    "TextSummarizerInput",
    "TextSummarizerOutput",
    # Web 搜索工具
    "WebSearchTool",
    "WebSearchInput",
    "WebSearchOutput",
    "SearchResult",
    # 工具錯誤
    "ToolExecutionError",
    "ToolValidationError",
    "ToolNotFoundError",
    "ToolConfigurationError",
    # 工具註冊清單載入器
    "load_tools_registry",
    "get_tool_info",
    "list_all_tools",
    "get_tools_by_category",
    "search_tools",
    "get_tools_for_task_analysis",
]

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.calculator import (
    MathCalculator,
    MathInput,
    MathOutput,
    StatisticsCalculator,
    StatisticsInput,
    StatisticsOutput,
)
from tools.conversion import (
    AreaConverter,
    AreaInput,
    AreaOutput,
    CurrencyConverter,
    CurrencyInput,
    CurrencyOutput,
    LengthConverter,
    LengthInput,
    LengthOutput,
    TemperatureConverter,
    TemperatureInput,
    TemperatureOutput,
    VolumeConverter,
    VolumeInput,
    VolumeOutput,
    WeightConverter,
    WeightInput,
    WeightOutput,
)
from tools.location import (
    DistanceInput,
    DistanceOutput,
    DistanceTool,
    GeocodingInput,
    GeocodingOutput,
    GeocodingTool,
    IPLocationInput,
    IPLocationOutput,
    IPLocationTool,
    TimezoneInput,
    TimezoneOutput,
    TimezoneTool,
)
from tools.registry import ToolRegistry, get_tool_registry
from tools.registry_loader import (
    get_tool_info,
    get_tools_by_category,
    get_tools_for_task_analysis,
    list_all_tools,
    load_tools_registry,
    search_tools,
)
from tools.text import (
    TextCleaner,
    TextCleanerInput,
    TextCleanerOutput,
    TextConverter,
    TextConverterInput,
    TextConverterOutput,
    TextFormatter,
    TextFormatterInput,
    TextFormatterOutput,
    TextSummarizer,
    TextSummarizerInput,
    TextSummarizerOutput,
)
from tools.time import (
    CalculateInput,
    CalculateOutput,
    DateCalculator,
    DateFormatter,
    DateTimeInput,
    DateTimeOutput,
    DateTimeTool,
    FormatInput,
    FormatOutput,
    TimeService,
    get_smart_time_service,
    get_time_service,
)
from tools.utils import (
    ToolConfigurationError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
)
from tools.weather import (
    ForecastInput,
    ForecastItem,
    ForecastOutput,
    ForecastTool,
    HourlyForecast,
    WeatherInput,
    WeatherOutput,
    WeatherTool,
)
from tools.web_search import SearchResult, WebSearchInput, WebSearchOutput, WebSearchTool


def register_all_tools(registry: Optional[ToolRegistry] = None) -> ToolRegistry:
    """
    註冊所有工具到工具註冊表

    Args:
        registry: 工具註冊表，如果為 None 則使用全局註冊表

    Returns:
        工具註冊表實例
    """
    if registry is None:
        registry = get_tool_registry()

    # 註冊時間工具
    registry.register(DateTimeTool())
    registry.register(DateFormatter())
    registry.register(DateCalculator())

    # 註冊天氣工具
    registry.register(WeatherTool())
    registry.register(ForecastTool())

    # 註冊地理位置工具
    registry.register(IPLocationTool())
    registry.register(GeocodingTool())
    registry.register(DistanceTool())
    registry.register(TimezoneTool())

    # 註冊單位轉換工具
    registry.register(LengthConverter())
    registry.register(WeightConverter())
    registry.register(TemperatureConverter())
    registry.register(CurrencyConverter())
    registry.register(VolumeConverter())
    registry.register(AreaConverter())

    # 註冊計算工具
    registry.register(MathCalculator())
    registry.register(StatisticsCalculator())

    # 註冊文本處理工具
    registry.register(TextFormatter())
    registry.register(TextCleaner())
    registry.register(TextConverter())
    registry.register(TextSummarizer())

    # 註冊 Web 搜索工具
    registry.register(WebSearchTool())

    return registry
