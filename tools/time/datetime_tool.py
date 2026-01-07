# 代碼功能說明: 日期時間工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-06

"""日期時間工具

獲取當前日期時間，支持時區轉換和格式化。
使用 TimeService 獲取高精度時間，從 ConfigStoreService 讀取配置。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import pytz
import structlog

from services.api.services.config_store_service import get_config_store_service
from tools.base import BaseTool, ToolInput, ToolOutput
from tools.time.smart_time_service import get_time_service
from tools.utils.errors import ToolExecutionError

logger = structlog.get_logger(__name__)


class DateTimeInput(ToolInput):
    """日期時間工具輸入參數"""

    timezone: Optional[str] = None  # 時區（如 "Asia/Taipei"），None 表示使用配置中的默認時區
    format: Optional[str] = None  # 輸出格式（如 "%Y-%m-%d %H:%M:%S"），None 表示使用配置中的默認格式
    tenant_id: Optional[str] = None  # 租戶 ID（用於讀取租戶級配置）
    user_id: Optional[str] = None  # 用戶 ID（用於讀取用戶級配置）


class DateTimeOutput(ToolOutput):
    """日期時間工具輸出結果"""

    datetime: str  # 格式化後的日期時間字符串
    timestamp: float  # Unix 時間戳
    timezone: str  # 時區名稱
    iso_format: str  # ISO 8601 格式
    local_format: str  # 本地格式


class DateTimeTool(BaseTool[DateTimeInput, DateTimeOutput]):
    """日期時間工具

    獲取當前日期時間，支持時區轉換和多種格式輸出。
    """

    @property
    def name(self) -> str:
        """工具名稱"""
        return "datetime"

    @property
    def description(self) -> str:
        """工具描述"""
        return "獲取當前日期時間，支持時區轉換和多種格式輸出"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _get_config(self, tenant_id: Optional[str], user_id: Optional[str]) -> Dict[str, Any]:
        """
        獲取有效配置（合併 system > tenant > user）

        Args:
            tenant_id: 租戶 ID
            user_id: 用戶 ID

        Returns:
            配置字典

        Raises:
            ToolConfigurationError: 配置讀取失敗
        """
        try:
            config_service = get_config_store_service()

            # 如果沒有 tenant_id，嘗試讀取 system 配置
            if not tenant_id:
                system_config = config_service.get_config(
                    scope="tools.datetime", tenant_id=None, user_id=None
                )
                if system_config:
                    return system_config.config_data
                # 返回默認配置
                return self._get_default_config()

            # 讀取有效配置（自動合併三層配置）
            effective_config = config_service.get_effective_config(
                scope="tools.datetime",
                tenant_id=tenant_id,
                user_id=user_id,
            )
            return effective_config.config

        except Exception as e:
            logger.warning(
                "config_read_failed",
                error=str(e),
                tenant_id=tenant_id,
                user_id=user_id,
            )
            # 配置讀取失敗時返回默認配置
            return self._get_default_config()

    def _get_system_timezone(self) -> str:
        """
        獲取系統時區

        嘗試從系統環境中獲取時區，如果無法獲取則返回 UTC。

        Returns:
            時區名稱（如 "Asia/Taipei" 或 "UTC"）
        """
        try:
            # 獲取系統本地時區
            local_tz = datetime.now().astimezone().tzinfo

            # 嘗試從時區對象獲取名稱
            if hasattr(local_tz, "zone"):
                timezone_name = local_tz.zone  # type: ignore[attr-defined]
                if timezone_name:
                    logger.debug("system_timezone_detected", timezone=timezone_name)
                    return timezone_name

            # 如果無法獲取名稱，嘗試從偏移量推斷
            offset = datetime.now().astimezone().utcoffset()
            if offset:
                offset_hours = offset.total_seconds() / 3600
                # 根據偏移量推斷時區（常見時區）
                if offset_hours == 8:
                    return "Asia/Taipei"  # UTC+8
                elif offset_hours == 9:
                    return "Asia/Tokyo"  # UTC+9
                elif offset_hours == 0:
                    return "UTC"
                elif offset_hours == -5:
                    return "America/New_York"  # UTC-5
                elif offset_hours == -8:
                    return "America/Los_Angeles"  # UTC-8
                else:
                    logger.warning(
                        "unable_to_infer_timezone_from_offset",
                        offset_hours=offset_hours,
                    )
                    return "UTC"

            logger.warning("unable_to_detect_system_timezone")
            return "UTC"
        except Exception as e:
            logger.warning("system_timezone_detection_failed", error=str(e))
            return "UTC"

    def _get_default_config(self) -> Dict[str, Any]:
        """
        獲取默認配置

        使用系統時區作為默認時區，而不是 UTC。

        Returns:
            默認配置字典
        """
        system_timezone = self._get_system_timezone()
        return {
            "default_format": "%Y-%m-%d %H:%M:%S",
            "default_timezone": system_timezone,  # 使用系統時區而不是 UTC
            "default_locale": "en_US",
            "iso_format": "%Y-%m-%dT%H:%M:%S%z",
            "date_only_format": "%Y-%m-%d",
            "time_only_format": "%H:%M:%S",
        }

    async def execute(self, input_data: DateTimeInput) -> DateTimeOutput:
        """
        執行日期時間工具

        Args:
            input_data: 工具輸入參數

        Returns:
            工具輸出結果

        Raises:
            ToolExecutionError: 工具執行失敗
        """
        try:
            # 獲取高精度時間
            time_service = get_time_service()
            current_timestamp = time_service.now()
            current_datetime_utc = time_service.now_utc_datetime()

            # 讀取配置
            config = self._get_config(input_data.tenant_id, input_data.user_id)

            # 確定時區（優先級：用戶指定 > 配置 > 系統時區 > UTC）
            timezone_str = (
                input_data.timezone
                or config.get("default_timezone")
                or self._get_system_timezone()
                or "UTC"
            )
            try:
                tz = pytz.timezone(timezone_str)
            except Exception as e:
                logger.warning("invalid_timezone", timezone=timezone_str, error=str(e))
                tz = pytz.UTC
                timezone_str = "UTC"

            # 轉換到指定時區
            if current_datetime_utc.tzinfo is None:
                current_datetime_utc = pytz.UTC.localize(current_datetime_utc)
            current_datetime = current_datetime_utc.astimezone(tz)

            # 確定格式
            format_str = input_data.format or config.get("default_format", "%Y-%m-%d %H:%M:%S")

            # 格式化日期時間
            formatted_datetime = current_datetime.strftime(format_str)

            # ISO 8601 格式
            iso_format_str = config.get("iso_format", "%Y-%m-%dT%H:%M:%S%z")
            iso_formatted = current_datetime.strftime(iso_format_str)

            # 本地格式（使用配置中的本地化格式）
            locale = config.get("default_locale", "en_US")
            localized_formats = config.get("localized_formats", {})
            local_format_str = localized_formats.get(locale, format_str)
            local_formatted = current_datetime.strftime(local_format_str)

            return DateTimeOutput(
                datetime=formatted_datetime,
                timestamp=current_timestamp,
                timezone=timezone_str,
                iso_format=iso_formatted,
                local_format=local_formatted,
            )

        except Exception as e:
            logger.error("datetime_tool_execution_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to execute datetime tool: {str(e)}", tool_name=self.name
            ) from e
