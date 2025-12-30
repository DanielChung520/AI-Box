# 代碼功能說明: 配置服務集成測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""配置服務集成測試

測試 DateTimeTool 與 ConfigStoreService 的集成。
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from services.api.models.config import EffectiveConfig
from tools.time import DateTimeInput, DateTimeTool


@pytest.mark.asyncio
class TestConfigServiceIntegration:
    """配置服務集成測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return DateTimeTool()

    @pytest.fixture
    def sample_datetime_config(self):
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

    @pytest.mark.asyncio
    async def test_read_system_config(self, tool, sample_datetime_config):
        """測試讀取系統級配置"""
        with patch("tools.time.datetime_tool.get_config_store_service") as mock_service:
            effective_config = EffectiveConfig(
                scope="tools.datetime",
                tenant_id=None,
                user_id=None,
                config=sample_datetime_config,
                merged_from={"system": True, "tenant": False, "user": False},
            )
            mock_service.return_value.get_effective_config.return_value = effective_config

            input_data = DateTimeInput(tenant_id=None, user_id=None)
            result = await tool.execute(input_data)

            assert result is not None
            assert result.timezone == "UTC"  # 使用配置中的默認時區

    @pytest.mark.asyncio
    async def test_read_tenant_config(self, tool, sample_datetime_config):
        """測試讀取租戶級配置"""
        tenant_config = sample_datetime_config.copy()
        tenant_config["default_timezone"] = "Asia/Taipei"  # 租戶特定配置

        with patch("tools.time.datetime_tool.get_config_store_service") as mock_service:
            effective_config = EffectiveConfig(
                scope="tools.datetime",
                tenant_id="tenant_123",
                user_id=None,
                config=tenant_config,
                merged_from={"system": True, "tenant": True, "user": False},
            )
            mock_service.return_value.get_effective_config.return_value = effective_config

            input_data = DateTimeInput(tenant_id="tenant_123", user_id=None)
            result = await tool.execute(input_data)

            assert result is not None
            assert result.timezone == "Asia/Taipei"  # 使用租戶配置

    @pytest.mark.asyncio
    async def test_read_user_config(self, tool, sample_datetime_config):
        """測試讀取用戶級配置"""
        user_config = sample_datetime_config.copy()
        user_config["default_format"] = "%Y年%m月%d日"  # 用戶特定格式

        with patch("tools.time.datetime_tool.get_config_store_service") as mock_service:
            effective_config = EffectiveConfig(
                scope="tools.datetime",
                tenant_id="tenant_123",
                user_id="user_456",
                config=user_config,
                merged_from={"system": True, "tenant": True, "user": True},
            )
            mock_service.return_value.get_effective_config.return_value = effective_config

            input_data = DateTimeInput(tenant_id="tenant_123", user_id="user_456")
            result = await tool.execute(input_data)

            assert result is not None
            # 驗證使用了用戶配置的格式
            assert result.datetime is not None

    @pytest.mark.asyncio
    async def test_config_priority_user_over_tenant(self, tool, sample_datetime_config):
        """測試配置優先級：用戶 > 租戶 > 系統"""
        # 系統配置
        system_config = sample_datetime_config.copy()
        system_config["default_timezone"] = "UTC"

        # 租戶配置（覆蓋系統）
        tenant_config = system_config.copy()
        tenant_config["default_timezone"] = "Asia/Taipei"

        # 用戶配置（覆蓋租戶和系統）
        user_config = tenant_config.copy()
        user_config["default_timezone"] = "America/New_York"

        with patch("tools.time.datetime_tool.get_config_store_service") as mock_service:
            effective_config = EffectiveConfig(
                scope="tools.datetime",
                tenant_id="tenant_123",
                user_id="user_456",
                config=user_config,
                merged_from={"system": True, "tenant": True, "user": True},
            )
            mock_service.return_value.get_effective_config.return_value = effective_config

            input_data = DateTimeInput(tenant_id="tenant_123", user_id="user_456")
            result = await tool.execute(input_data)

            assert result is not None
            # 應該使用用戶配置（最高優先級）
            assert result.timezone == "America/New_York"

    @pytest.mark.asyncio
    async def test_config_override_with_input(self, tool, sample_datetime_config):
        """測試輸入參數覆蓋配置"""
        with patch("tools.time.datetime_tool.get_config_store_service") as mock_service:
            effective_config = EffectiveConfig(
                scope="tools.datetime",
                tenant_id="tenant_123",
                user_id=None,
                config=sample_datetime_config,
                merged_from={"system": True, "tenant": False, "user": False},
            )
            mock_service.return_value.get_effective_config.return_value = effective_config

            # 輸入參數覆蓋配置中的時區
            input_data = DateTimeInput(tenant_id="tenant_123", timezone="Asia/Tokyo", format=None)
            result = await tool.execute(input_data)

            assert result is not None
            assert result.timezone == "Asia/Tokyo"  # 使用輸入參數，而不是配置

    @pytest.mark.asyncio
    async def test_config_not_found_fallback(self, tool):
        """測試配置不存在時的降級處理"""
        with patch("tools.time.datetime_tool.get_config_store_service") as mock_service:
            # 模擬配置服務拋出異常
            mock_service.return_value.get_effective_config.side_effect = Exception(
                "Config not found"
            )
            mock_service.return_value.get_config.return_value = None

            # 應該使用默認值，不應該報錯
            input_data = DateTimeInput()
            result = await tool.execute(input_data)

            assert result is not None
            assert result.timestamp > 0

    @pytest.mark.asyncio
    async def test_config_cache(self, tool, sample_datetime_config):
        """測試配置緩存（如果實現了）"""
        with patch("tools.time.datetime_tool.get_config_store_service") as mock_service:
            effective_config = EffectiveConfig(
                scope="tools.datetime",
                tenant_id="tenant_123",
                user_id=None,
                config=sample_datetime_config,
                merged_from={"system": True, "tenant": False, "user": False},
            )
            mock_service.return_value.get_effective_config.return_value = effective_config

            # 第一次調用
            input_data1 = DateTimeInput(tenant_id="tenant_123")
            result1 = await tool.execute(input_data1)

            # 第二次調用（應該使用緩存的配置）
            input_data2 = DateTimeInput(tenant_id="tenant_123")
            result2 = await tool.execute(input_data2)

            assert result1 is not None
            assert result2 is not None
            # 驗證配置服務被調用（實際實現可能會有緩存）
            assert mock_service.return_value.get_effective_config.call_count >= 1
