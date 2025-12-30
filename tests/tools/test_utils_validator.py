# 代碼功能說明: 參數驗證工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""參數驗證工具測試"""

from __future__ import annotations

import pytest

from tools.utils.validator import (
    validate_coordinates,
    validate_ip_address,
    validate_latitude,
    validate_longitude,
    validate_non_empty_string,
    validate_positive_number,
)


class TestValidateIPAddress:
    """IP 地址驗證測試"""

    def test_valid_ipv4(self):
        """測試有效的 IPv4 地址"""
        assert validate_ip_address("192.168.1.1") is True
        assert validate_ip_address("127.0.0.1") is True
        assert validate_ip_address("0.0.0.0") is True
        assert validate_ip_address("255.255.255.255") is True

    def test_valid_ipv6(self):
        """測試有效的 IPv6 地址"""
        assert validate_ip_address("2001:0db8:85a3:0000:0000:8a2e:0370:7334") is True
        assert validate_ip_address("::1") is True
        assert validate_ip_address("2001:db8::1") is True

    def test_invalid_ip(self):
        """測試無效的 IP 地址"""
        assert validate_ip_address("invalid") is False
        assert validate_ip_address("256.256.256.256") is False
        assert validate_ip_address("192.168.1") is False
        assert validate_ip_address("") is False


class TestValidateLatitude:
    """緯度驗證測試"""

    def test_valid_latitude(self):
        """測試有效的緯度"""
        assert validate_latitude(0.0) is True
        assert validate_latitude(90.0) is True
        assert validate_latitude(-90.0) is True
        assert validate_latitude(45.5) is True

    def test_invalid_latitude(self):
        """測試無效的緯度"""
        assert validate_latitude(90.1) is False
        assert validate_latitude(-90.1) is False
        assert validate_latitude(100.0) is False
        assert validate_latitude(-100.0) is False


class TestValidateLongitude:
    """經度驗證測試"""

    def test_valid_longitude(self):
        """測試有效的經度"""
        assert validate_longitude(0.0) is True
        assert validate_longitude(180.0) is True
        assert validate_longitude(-180.0) is True
        assert validate_longitude(120.5) is True

    def test_invalid_longitude(self):
        """測試無效的經度"""
        assert validate_longitude(180.1) is False
        assert validate_longitude(-180.1) is False
        assert validate_longitude(200.0) is False
        assert validate_longitude(-200.0) is False


class TestValidateCoordinates:
    """坐標驗證測試"""

    def test_valid_coordinates(self):
        """測試有效的坐標"""
        assert validate_coordinates(25.0, 121.0) is True
        assert validate_coordinates(0.0, 0.0) is True
        assert validate_coordinates(90.0, 180.0) is True
        assert validate_coordinates(-90.0, -180.0) is True

    def test_invalid_coordinates(self):
        """測試無效的坐標"""
        assert validate_coordinates(100.0, 121.0) is False  # 無效緯度
        assert validate_coordinates(25.0, 200.0) is False  # 無效經度
        assert validate_coordinates(100.0, 200.0) is False  # 都無效


class TestValidateNonEmptyString:
    """非空字符串驗證測試"""

    def test_valid_string(self):
        """測試有效的字符串"""
        assert validate_non_empty_string("test") == "test"
        assert validate_non_empty_string("  test  ") == "test"  # 自動去除空格

    def test_invalid_string(self):
        """測試無效的字符串"""
        with pytest.raises(ValueError):
            validate_non_empty_string(None)

        with pytest.raises(ValueError):
            validate_non_empty_string("")

        with pytest.raises(ValueError):
            validate_non_empty_string("   ")  # 只有空格

    def test_custom_field_name(self):
        """測試自定義字段名稱"""
        with pytest.raises(ValueError, match="custom_field cannot be empty"):
            validate_non_empty_string("", field_name="custom_field")


class TestValidatePositiveNumber:
    """正數驗證測試"""

    def test_valid_positive_number(self):
        """測試有效的正數"""
        assert validate_positive_number(1.0) == 1.0
        assert validate_positive_number(0.1) == 0.1
        assert validate_positive_number(100.0) == 100.0

    def test_invalid_positive_number(self):
        """測試無效的正數"""
        with pytest.raises(ValueError):
            validate_positive_number(0.0)

        with pytest.raises(ValueError):
            validate_positive_number(-1.0)

        with pytest.raises(ValueError):
            validate_positive_number(-0.1)

    def test_custom_field_name(self):
        """測試自定義字段名稱"""
        with pytest.raises(ValueError, match="amount must be positive"):
            validate_positive_number(-1.0, field_name="amount")
