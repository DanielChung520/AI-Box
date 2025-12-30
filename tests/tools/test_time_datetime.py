# 代碼功能說明: 日期時間工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""日期時間工具測試"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from services.api.models.config import EffectiveConfig
from tools.time import DateTimeInput, DateTimeOutput, DateTimeTool


@pytest.mark.asyncio
class TestDateTimeTool:
    """日期時間工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return DateTimeTool()

    @pytest.fixture
    def mock_config_service(self, sample_datetime_config):
        """模擬配置服務"""
        with patch("tools.time.datetime_tool.get_config_store_service") as mock:
            service = Mock()
            effective_config = EffectiveConfig(
                scope="tools.datetime",
                tenant_id="test_tenant",
                user_id=None,
                config=sample_datetime_config,
                merged_from={"system": True, "tenant": False, "user": False},
            )
            service.get_effective_config.return_value = effective_config
            service.get_config.return_value = None
            mock.return_value = service
            yield service

    @pytest.fixture
    def mock_time_service(self):
        """模擬時間服務"""
        with patch("tools.time.datetime_tool.get_time_service") as mock:
            service = Mock()
            service.now.return_value = 1735549200.0  # 2025-12-30 12:00:00 UTC
            service.now_utc_datetime.return_value = datetime(2025, 12, 30, 12, 0, 0)
            mock.return_value = service
            yield service

    @pytest.mark.asyncio
    async def test_get_current_datetime_with_config(
        self, tool, mock_config_service, mock_time_service
    ):
        """測試獲取當前日期時間（使用配置）"""
        input_data = DateTimeInput(
            tenant_id="test_tenant", user_id=None, timezone=None, format=None
        )
        result = await tool.execute(input_data)

        assert isinstance(result, DateTimeOutput)
        assert result.timestamp > 0
        assert result.timezone is not None
        assert result.datetime is not None
        assert result.iso_format is not None
        assert result.local_format is not None

    @pytest.mark.asyncio
    async def test_get_current_datetime_with_custom_timezone(
        self, tool, mock_config_service, mock_time_service
    ):
        """測試使用自定義時區"""
        input_data = DateTimeInput(timezone="Asia/Taipei", format=None)
        result = await tool.execute(input_data)

        assert isinstance(result, DateTimeOutput)
        assert result.timezone == "Asia/Taipei"

    @pytest.mark.asyncio
    async def test_get_current_datetime_with_custom_format(
        self, tool, mock_config_service, mock_time_service
    ):
        """測試使用自定義格式"""
        input_data = DateTimeInput(format="%Y-%m-%d")
        result = await tool.execute(input_data)

        assert isinstance(result, DateTimeOutput)
        assert result.datetime is not None

    @pytest.mark.asyncio
    async def test_get_current_datetime_default_config(self, tool, mock_time_service):
        """測試使用默認配置（無配置服務）"""
        with patch("tools.time.datetime_tool.get_config_store_service") as mock:
            mock.return_value.get_effective_config.side_effect = Exception("Config not found")
            mock.return_value.get_config.return_value = None

            input_data = DateTimeInput()
            result = await tool.execute(input_data)

            assert isinstance(result, DateTimeOutput)
            assert result.timezone == "UTC"  # 默認時區

    @pytest.mark.asyncio
    async def test_get_current_datetime_invalid_timezone(
        self, tool, mock_config_service, mock_time_service
    ):
        """測試無效時區（應該回退到 UTC）"""
        input_data = DateTimeInput(timezone="Invalid/Timezone")
        result = await tool.execute(input_data)

        assert isinstance(result, DateTimeOutput)
        assert result.timezone == "UTC"  # 回退到 UTC
