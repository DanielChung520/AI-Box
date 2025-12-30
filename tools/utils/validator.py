# 代碼功能說明: 參數驗證工具函數
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""參數驗證工具函數

提供通用的參數驗證工具函數。
"""

from __future__ import annotations

from typing import Optional


def validate_ip_address(ip: str) -> bool:
    """
    驗證 IP 地址格式（IPv4 或 IPv6）

    Args:
        ip: IP 地址字符串

    Returns:
        是否為有效的 IP 地址
    """
    import ipaddress

    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_latitude(lat: float) -> bool:
    """
    驗證緯度範圍（-90 到 90）

    Args:
        lat: 緯度值

    Returns:
        是否為有效的緯度
    """
    return -90.0 <= lat <= 90.0


def validate_longitude(lon: float) -> bool:
    """
    驗證經度範圍（-180 到 180）

    Args:
        lon: 經度值

    Returns:
        是否為有效的經度
    """
    return -180.0 <= lon <= 180.0


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    驗證經緯度坐標

    Args:
        lat: 緯度值
        lon: 經度值

    Returns:
        是否為有效的坐標
    """
    return validate_latitude(lat) and validate_longitude(lon)


def validate_non_empty_string(value: Optional[str], field_name: str = "value") -> str:
    """
    驗證非空字符串

    Args:
        value: 字符串值
        field_name: 字段名稱（用於錯誤消息）

    Returns:
        驗證後的字符串

    Raises:
        ValueError: 如果值為 None 或空字符串
    """
    if value is None or not isinstance(value, str) or len(value.strip()) == 0:
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def validate_positive_number(value: float, field_name: str = "value") -> float:
    """
    驗證正數

    Args:
        value: 數值
        field_name: 字段名稱（用於錯誤消息）

    Returns:
        驗證後的數值

    Raises:
        ValueError: 如果值不是正數
    """
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value
