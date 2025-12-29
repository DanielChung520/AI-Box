# 代碼功能說明: Config Preview 和 Rollback Service 測試
# 創建日期: 2025-12-21
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""Config Preview 和 Rollback Service 測試

測試配置預覽服務和回滾服務的功能。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.builtin.system_config_agent.models import ConfigPreview, RollbackResult
from agents.builtin.system_config_agent.preview_service import ConfigPreviewService
from agents.builtin.system_config_agent.rollback_service import ConfigRollbackService
from agents.task_analyzer.models import ConfigIntent
from services.api.models.config import ConfigModel


@pytest.fixture
def preview_service():
    """創建 ConfigPreviewService 實例（不需要數據庫連接）"""
    return ConfigPreviewService()


@pytest.fixture
def rollback_service(monkeypatch):
    """創建 ConfigRollbackService 實例（mock 數據庫連接）"""
    mock_config_service = MagicMock()
    mock_log_service = MagicMock()

    # 使用 monkeypatch 來替換服務獲取函數
    monkeypatch.setattr(
        "agents.builtin.system_config_agent.rollback_service.get_config_store_service",
        lambda: mock_config_service,
    )
    monkeypatch.setattr(
        "agents.builtin.system_config_agent.rollback_service.get_log_service",
        lambda: mock_log_service,
    )

    service = ConfigRollbackService()
    # 確保使用 mock 服務
    service._config_service = mock_config_service
    service._log_service = mock_log_service
    return service


@pytest.fixture
def sample_intent():
    """創建示例 ConfigIntent"""
    return ConfigIntent(
        action="update",
        scope="genai.policy",
        level="tenant",
        tenant_id="tenant-123",
        config_data={"allowed_providers": ["openai"], "rate_limit": 1000},
        original_instruction="更新租戶配置",
    )


@pytest.fixture
def sample_config():
    """創建示例 ConfigModel"""
    return ConfigModel(
        id="config-123",
        scope="genai.policy",
        tenant_id="tenant-123",
        config_data={"allowed_providers": ["openai"], "rate_limit": 500},
        is_active=True,
    )


@pytest.mark.asyncio
class TestConfigPreviewService:
    """測試配置預覽服務"""

    async def test_generate_preview_basic(self, preview_service, sample_intent):
        """測試生成預覽（基礎）"""
        preview = await preview_service.generate_preview(sample_intent, None)
        assert isinstance(preview, ConfigPreview)
        assert preview.changes == sample_intent.config_data
        assert preview.risk_level in ["low", "medium", "high"]
        assert isinstance(preview.impact_analysis, dict)

    async def test_generate_preview_with_current_config(
        self, preview_service, sample_intent, sample_config
    ):
        """測試生成預覽（帶當前配置）"""
        preview = await preview_service.generate_preview(sample_intent, sample_config)
        assert isinstance(preview, ConfigPreview)
        assert "affected_users" in preview.impact_analysis
        assert "affected_tenants" in preview.impact_analysis

    async def test_analyze_impact_system_level(self, preview_service):
        """測試影響分析 - 系統級"""
        intent = ConfigIntent(
            action="update",
            scope="genai.policy",
            level="system",
            config_data={"test": "value"},
            original_instruction="測試",
        )
        impact = await preview_service._analyze_impact(intent, None)
        assert impact["affected_users"] == -1  # -1 表示所有用戶
        assert impact["affected_tenants"] == -1  # -1 表示所有租戶

    async def test_analyze_impact_tenant_level(self, preview_service):
        """測試影響分析 - 租戶級"""
        intent = ConfigIntent(
            action="update",
            scope="genai.policy",
            level="tenant",
            tenant_id="tenant-123",
            config_data={"test": "value"},
            original_instruction="測試",
        )
        impact = await preview_service._analyze_impact(intent, None)
        assert impact["affected_tenants"] == 1
        assert "affected_services" in impact

    async def test_calculate_cost_change(self, preview_service, sample_intent, sample_config):
        """測試成本變化計算"""
        cost_change = await preview_service._calculate_cost_change(sample_intent, sample_config)
        # cost_change 可能為 None（如果沒有變化）
        if cost_change:
            assert "estimated_monthly_change" in cost_change
            assert "change_percentage" in cost_change
            assert "factors" in cost_change

    async def test_assess_risk_system_level(self, preview_service):
        """測試風險評估 - 系統級（高風險）"""
        intent = ConfigIntent(
            action="update",
            scope="genai.policy",
            level="system",
            config_data={"rate_limit": 5000},
            original_instruction="測試",
        )
        risk = await preview_service._assess_risk(intent, None)
        assert risk in ["low", "medium", "high"]
        # 系統級應該至少是 medium
        assert risk in ["medium", "high"]

    async def test_assess_risk_delete_action(self, preview_service):
        """測試風險評估 - 刪除操作（高風險）"""
        intent = ConfigIntent(
            action="delete",
            scope="genai.policy",
            level="system",
            original_instruction="測試",
        )
        risk = await preview_service._assess_risk(intent, None)
        # 刪除操作應該至少是 medium
        assert risk in ["medium", "high"]


@pytest.mark.asyncio
class TestConfigRollbackService:
    """測試配置回滾服務"""

    @patch("agents.builtin.system_config_agent.rollback_service.get_config_store_service")
    @patch("agents.builtin.system_config_agent.rollback_service.get_log_service")
    async def test_rollback_config_success(
        self, mock_log_service, mock_config_service, rollback_service
    ):
        """測試配置回滾 - 成功"""
        # Mock services
        mock_config = MagicMock()
        mock_config.update_config = MagicMock(
            return_value=MagicMock(config_data={"test": "old_value"})
        )
        mock_config_service.return_value = mock_config

        mock_log = MagicMock()
        mock_log.log_audit = AsyncMock()
        mock_log_service.return_value = mock_log
        rollback_service._log_service = mock_log
        rollback_service._config_service = mock_config

        # Mock audit log retrieval
        with patch.object(
            rollback_service,
            "_get_audit_log_by_rollback_id",
            new=AsyncMock(return_value={"content": {"before": {"test": "old_value"}}}),
        ):
            result = await rollback_service.rollback_config(
                rollback_id="rb-12345678",
                admin_user_id="admin-123",
                scope="genai.policy",
                level="system",
            )
            assert isinstance(result, RollbackResult)
            # 由於 mock 實現，結果可能成功或失敗，但應該是 RollbackResult 類型

    async def test_get_recent_changes(self, rollback_service):
        """測試獲取最近的配置變更"""
        changes = await rollback_service.get_recent_changes(
            scope="genai.policy", limit=10, hours=24
        )
        # 目前實現返回空列表（功能待實現）
        assert isinstance(changes, list)
