# 代碼功能說明: 時區查詢工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""時區查詢工具

根據地理位置獲取時區信息。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pytz
import structlog
from timezonefinder import TimezoneFinder

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.location.geocoding import GeocodingInput, GeocodingTool
from tools.utils.errors import ToolExecutionError, ToolValidationError
from tools.utils.validator import validate_coordinates, validate_non_empty_string

logger = structlog.get_logger(__name__)


class TimezoneInput(ToolInput):
    """時區查詢輸入參數"""

    lat: Optional[float] = None  # 緯度
    lon: Optional[float] = None  # 經度
    city: Optional[str] = None  # 城市名稱（可選，如果提供則先進行地理編碼）
    timestamp: Optional[float] = None  # 時間戳（用於歷史時區查詢，默認使用當前時間）


class TimezoneOutput(ToolOutput):
    """時區查詢輸出結果"""

    timezone: str  # 時區名稱（如 "Asia/Taipei"）
    offset: int  # UTC 偏移量（秒）
    offset_hours: float  # UTC 偏移量（小時）
    dst: bool  # 是否使用夏令時
    abbreviation: str  # 時區縮寫（如 "CST"）


class TimezoneTool(BaseTool[TimezoneInput, TimezoneOutput]):
    """時區查詢工具

    根據地理位置獲取時區信息。
    """

    def __init__(self) -> None:
        """初始化時區查詢工具"""
        self._timezone_finder = TimezoneFinder()
        self._geocoding_tool = GeocodingTool()

    @property
    def name(self) -> str:
        """工具名稱"""
        return "timezone"

    @property
    def description(self) -> str:
        """工具描述"""
        return "根據地理位置獲取時區信息"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _validate_input(self, input_data: TimezoneInput) -> None:
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

    async def _get_coordinates_from_city(self, city: str) -> tuple[float, float]:
        """
        根據城市名稱獲取坐標

        Args:
            city: 城市名稱

        Returns:
            緯度和經度的元組

        Raises:
            ToolExecutionError: 地理編碼失敗
        """
        try:
            geocoding_input = GeocodingInput(address=city)
            geocoding_output = await self._geocoding_tool.execute(geocoding_input)
            return geocoding_output.latitude, geocoding_output.longitude
        except Exception as e:
            logger.error("geocoding_failed", city=city, error=str(e))
            raise ToolExecutionError(
                f"Failed to geocode city '{city}': {str(e)}", tool_name=self.name
            ) from e

    def _get_timezone_from_coordinates(
        self, lat: float, lon: float, timestamp: Optional[float] = None
    ) -> TimezoneOutput:
        """
        根據坐標獲取時區信息

        Args:
            lat: 緯度
            lon: 經度
            timestamp: 時間戳（用於判斷夏令時，默認使用當前時間）

        Returns:
            時區信息

        Raises:
            ToolExecutionError: 獲取時區失敗
        """
        try:
            # 使用 timezonefinder 獲取時區名稱
            timezone_name = self._timezone_finder.timezone_at(lat=lat, lng=lon)

            if not timezone_name:
                raise ToolExecutionError(
                    f"Unable to determine timezone for coordinates ({lat}, {lon})",
                    tool_name=self.name,
                )

            # 獲取時區對象
            tz = pytz.timezone(timezone_name)

            # 計算偏移量和夏令時
            if timestamp is None:
                dt = datetime.now(pytz.UTC)
            else:
                dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)

            # 轉換到目標時區
            dt_local = dt.astimezone(tz)

            # 計算偏移量（秒）
            offset_seconds = int(dt_local.utcoffset().total_seconds())  # type: ignore[union-attr]

            # 計算偏移量（小時）
            offset_hours = offset_seconds / 3600.0

            # 判斷是否使用夏令時
            is_dst = bool(dt_local.dst().total_seconds() > 0 if dt_local.dst() else False)  # type: ignore[union-attr]

            # 獲取時區縮寫
            abbreviation = dt_local.strftime("%Z")

            return TimezoneOutput(
                timezone=timezone_name,
                offset=offset_seconds,
                offset_hours=offset_hours,
                dst=is_dst,
                abbreviation=abbreviation,
            )

        except pytz.UnknownTimeZoneError as e:
            logger.error("unknown_timezone", error=str(e))
            raise ToolExecutionError(f"Unknown timezone: {str(e)}", tool_name=self.name) from e
        except Exception as e:
            logger.error("timezone_lookup_failed", lat=lat, lon=lon, error=str(e))
            raise ToolExecutionError(
                f"Failed to get timezone information: {str(e)}", tool_name=self.name
            ) from e

    async def execute(self, input_data: TimezoneInput) -> TimezoneOutput:
        """
        執行時區查詢工具

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

            # 如果提供城市名稱，先進行地理編碼獲取坐標
            if input_data.city:
                lat, lon = await self._get_coordinates_from_city(input_data.city)
            else:
                # 使用提供的坐標
                if input_data.lat is None or input_data.lon is None:
                    raise ToolValidationError(
                        "lat and lon must be provided when city is not provided",
                        field="lat",
                    )
                lat = input_data.lat
                lon = input_data.lon

            # 根據坐標獲取時區信息
            return self._get_timezone_from_coordinates(lat, lon, input_data.timestamp)

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("timezone_tool_execution_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to execute timezone tool: {str(e)}", tool_name=self.name
            ) from e
