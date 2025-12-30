# 代碼功能說明: Tools 測試共用 Fixtures
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""Tools 測試共用 Fixtures"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from services.api.services.config_store_service import ConfigStoreService
from tools.time.smart_time_service import TimeService
from tools.utils.cache import Cache


@pytest.fixture
def mock_config_store_service():
    """模擬 ConfigStoreService"""
    service = Mock(spec=ConfigStoreService)
    return service


@pytest.fixture
def mock_time_service():
    """模擬 TimeService"""
    service = Mock(spec=TimeService)
    service.now.return_value = 1735549200.0  # 2025-12-30 12:00:00 UTC
    service.now_datetime.return_value = Mock(
        year=2025, month=12, day=30, hour=12, minute=0, second=0
    )
    service.now_utc_datetime.return_value = Mock(
        year=2025, month=12, day=30, hour=12, minute=0, second=0
    )
    return service


@pytest.fixture
def mock_cache():
    """模擬緩存"""
    cache = Mock(spec=Cache)
    cache.get.return_value = None
    cache.set.return_value = None
    return cache


@pytest.fixture
def sample_datetime_config():
    """示例日期時間配置"""
    return {
        "default_format": "%Y-%m-%d %H:%M:%S",
        "default_timezone": "UTC",
        "default_locale": "en_US",
        "iso_format": "%Y-%m-%dT%H:%M:%S%z",
        "date_only_format": "%Y-%m-%d",
        "time_only_format": "%H:%M:%S",
        "localized_formats": {
            "zh_TW": "%Y年%m月%d日 %H:%M:%S",
            "en_US": "%B %d, %Y %I:%M:%S %p",
        },
    }
