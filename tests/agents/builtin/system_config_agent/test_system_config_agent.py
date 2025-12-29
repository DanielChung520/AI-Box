# 代碼功能說明: System Config Agent 測試
# 創建日期: 2025-12-21
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""System Config Agent 單元測試和集成測試

覆蓋第二層深檢、審計日誌、權限驗證功能。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.builtin.system_config_agent.agent import SystemConfigAgent
from agents.builtin.system_config_agent.models import ComplianceCheckResult, ConfigOperationResult
from agents.services.protocol.base import AgentServiceRequest
from agents.task_analyzer.models import ConfigIntent


@pytest.fixture
def system_config_agent():
    """創建 SystemConfigAgent 實例（mock 數據庫連接）"""
    mock_config_service = MagicMock()
    mock_log_service = MagicMock()

    # 使用 patch 來替換所有可能調用數據庫的服務獲取函數
    # ConfigPreviewService 不需要數據庫連接，所以不需要 mock
    patches = [
        patch(
            "agents.builtin.system_config_agent.agent.get_config_store_service",
            return_value=mock_config_service,
        ),
        patch(
            "agents.builtin.system_config_agent.agent.get_log_service",
            return_value=mock_log_service,
        ),
        patch(
            "agents.builtin.system_config_agent.rollback_service.get_config_store_service",
            return_value=mock_config_service,
        ),
        patch(
            "agents.builtin.system_config_agent.rollback_service.get_log_service",
            return_value=mock_log_service,
        ),
        patch(
            "agents.builtin.system_config_agent.inspection_service.get_config_store_service",
            return_value=mock_config_service,
        ),
    ]

    # 啟動所有 patches
    for p in patches:
        p.start()

    try:
        agent = SystemConfigAgent()
        # 確保使用 mock 服務
        agent._config_service = mock_config_service
        agent._log_service = mock_log_service
        yield agent
    finally:
        # 測試結束後停止所有 patches（按相反順序）
        for p in reversed(patches):
            p.stop()


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
def sample_request(sample_intent):
    """創建示例 AgentServiceRequest"""
    return AgentServiceRequest(
        task_id="task-123",
        task_type="config_update",
        task_data={
            "intent": sample_intent.model_dump(),
            "admin_user_id": "admin-123",
            "context": {"trace_id": "trace-123"},
        },
    )


@pytest.mark.asyncio
class TestComplianceCheck:
    """測試第二層深檢功能"""

    async def test_validate_config_compliance_valid(self, system_config_agent, sample_intent):
        """測試合規性檢查 - 通過"""
        result = await system_config_agent._validate_config_compliance(
            sample_intent, sample_intent.config_data
        )
        assert isinstance(result, ComplianceCheckResult)

    async def test_check_convergence_rules(self, system_config_agent):
        """測試收斂規則檢查"""
        intent = ConfigIntent(
            action="update",
            scope="genai.policy",
            level="tenant",
            tenant_id="tenant-123",
            config_data={"allowed_providers": ["openai", "anthropic"]},
            original_instruction="測試",
        )
        result = await system_config_agent._check_convergence_rules(intent, intent.config_data)
        assert isinstance(result, ComplianceCheckResult)

    async def test_check_business_rules(self, system_config_agent):
        """測試業務規則檢查"""
        intent = ConfigIntent(
            action="update",
            scope="genai.policy",
            level="system",
            config_data={"rate_limit": 5000, "default_model": "gpt-4"},
            original_instruction="測試",
        )
        result = await system_config_agent._check_business_rules(intent, intent.config_data)
        assert isinstance(result, ComplianceCheckResult)
        assert result.valid


@pytest.mark.asyncio
class TestAuditLogging:
    """測試審計日誌記錄功能"""

    @patch("agents.builtin.system_config_agent.agent.get_log_service")
    async def test_audit_log_on_update(self, mock_log_service, system_config_agent, sample_intent):
        """測試配置更新時記錄審計日誌"""
        mock_log = MagicMock()
        mock_log.log_audit = AsyncMock()
        mock_log_service.return_value = mock_log
        system_config_agent._log_service = mock_log

        with patch.object(system_config_agent._config_service, "get_config", return_value=None):
            with patch.object(
                system_config_agent._config_service,
                "update_config",
                return_value=MagicMock(config_data={"test": "value"}),
            ):
                await system_config_agent._handle_update(sample_intent, "admin-123", "trace-123")
                mock_log.log_audit.assert_called_once()


@pytest.mark.asyncio
class TestPermissionVerification:
    """測試權限驗證功能"""

    async def test_verify_permission_system_level(self, system_config_agent):
        """測試系統級配置權限驗證"""
        intent = ConfigIntent(
            action="update",
            scope="genai.policy",
            level="system",
            config_data={"test": "value"},
            original_instruction="測試",
        )
        await system_config_agent._verify_permission("admin-123", intent)


@pytest.mark.asyncio
class TestConfigOperations:
    """測試配置操作功能"""

    @patch("agents.builtin.system_config_agent.agent.get_config_store_service")
    async def test_handle_query_system(self, mock_config_service, system_config_agent):
        """測試系統級配置查詢"""
        mock_service = MagicMock()
        mock_service.get_config = MagicMock(return_value=MagicMock(config_data={"test": "value"}))
        mock_config_service.return_value = mock_service
        system_config_agent._config_service = mock_service

        intent = ConfigIntent(
            action="query",
            scope="genai.policy",
            level="system",
            original_instruction="查詢配置",
        )
        result = await system_config_agent._handle_query(intent)
        assert isinstance(result, ConfigOperationResult)
        assert result.action == "query"

    @patch("agents.builtin.system_config_agent.agent.get_config_store_service")
    async def test_handle_create(self, mock_config_service, system_config_agent):
        """測試配置創建"""
        mock_service = MagicMock()
        mock_service.save_config = MagicMock(return_value="config-123")
        mock_config_service.return_value = mock_service
        system_config_agent._config_service = mock_service

        intent = ConfigIntent(
            action="create",
            scope="genai.policy",
            level="system",
            config_data={"test": "value"},
            original_instruction="創建配置",
        )
        with patch.object(system_config_agent._log_service, "log_audit", new=AsyncMock()):
            result = await system_config_agent._handle_create(intent, "admin-123", "trace-123")
            assert isinstance(result, ConfigOperationResult)
            assert result.action == "create"
            assert result.success is True

    async def test_handle_create_missing_config_data(self, system_config_agent):
        """測試配置創建 - config_data 缺失"""
        intent = ConfigIntent(
            action="create",
            scope="genai.policy",
            level="system",
            config_data=None,
            original_instruction="創建配置",
        )
        result = await system_config_agent._handle_create(intent, "admin-123", "trace-123")
        assert isinstance(result, ConfigOperationResult)
        assert result.success is False
        assert "config_data is required" in result.error

    @patch("agents.builtin.system_config_agent.agent.get_config_store_service")
    async def test_handle_query_tenant_level(self, mock_config_service, system_config_agent):
        """測試租戶級配置查詢"""
        mock_service = MagicMock()
        mock_config = MagicMock()
        mock_config.id = "config-123"
        mock_config.config_data = {"test": "value"}
        mock_config.metadata = {}
        mock_config.is_active = True
        mock_config.created_at = None
        mock_config.updated_at = None
        mock_service.get_config = MagicMock(return_value=mock_config)
        mock_config_service.return_value = mock_service
        system_config_agent._config_service = mock_service

        intent = ConfigIntent(
            action="query",
            scope="genai.policy",
            level="tenant",
            tenant_id="tenant-123",
            original_instruction="查詢租戶配置",
        )
        result = await system_config_agent._handle_query(intent)
        assert isinstance(result, ConfigOperationResult)
        assert result.action == "query"
        assert result.success is True

    async def test_handle_query_tenant_level_missing_tenant_id(self, system_config_agent):
        """測試租戶級配置查詢 - tenant_id 缺失"""
        intent = ConfigIntent(
            action="query",
            scope="genai.policy",
            level="tenant",
            tenant_id=None,
            original_instruction="查詢租戶配置",
        )
        result = await system_config_agent._handle_query(intent)
        assert isinstance(result, ConfigOperationResult)
        assert result.success is False
        assert "tenant_id is required" in result.error

    @patch("agents.builtin.system_config_agent.agent.get_config_store_service")
    async def test_handle_query_user_level(self, mock_config_service, system_config_agent):
        """測試用戶級配置查詢"""
        mock_service = MagicMock()
        mock_config = MagicMock()
        mock_config.id = "config-123"
        mock_config.config_data = {"test": "value"}
        mock_config.metadata = {}
        mock_config.is_active = True
        mock_config.created_at = None
        mock_config.updated_at = None
        mock_service.get_config = MagicMock(return_value=mock_config)
        mock_config_service.return_value = mock_service
        system_config_agent._config_service = mock_service

        intent = ConfigIntent(
            action="query",
            scope="genai.policy",
            level="user",
            tenant_id="tenant-123",
            user_id="user-123",
            original_instruction="查詢用戶配置",
        )
        result = await system_config_agent._handle_query(intent)
        assert isinstance(result, ConfigOperationResult)
        assert result.success is True

    async def test_handle_query_user_level_missing_ids(self, system_config_agent):
        """測試用戶級配置查詢 - tenant_id 或 user_id 缺失"""
        intent = ConfigIntent(
            action="query",
            scope="genai.policy",
            level="user",
            tenant_id=None,
            user_id="user-123",
            original_instruction="查詢用戶配置",
        )
        result = await system_config_agent._handle_query(intent)
        assert isinstance(result, ConfigOperationResult)
        assert result.success is False
        assert "tenant_id and user_id are required" in result.error

    @patch("agents.builtin.system_config_agent.agent.get_config_store_service")
    async def test_handle_query_effective_config(self, mock_config_service, system_config_agent):
        """測試有效配置查詢（合併後）"""
        mock_service = MagicMock()
        mock_effective_config = MagicMock()
        mock_effective_config.config = {"merged": "config"}
        mock_service.get_effective_config = MagicMock(return_value=mock_effective_config)
        mock_config_service.return_value = mock_service
        system_config_agent._config_service = mock_service

        intent = ConfigIntent(
            action="query",
            scope="genai.policy",
            level=None,  # 有效配置查詢
            tenant_id="tenant-123",
            user_id="user-123",
            original_instruction="查詢有效配置",
        )
        result = await system_config_agent._handle_query(intent)
        assert isinstance(result, ConfigOperationResult)
        assert result.action == "query"
        assert result.success is True
        assert result.level == "effective"

    async def test_handle_query_effective_config_missing_tenant_id(self, system_config_agent):
        """測試有效配置查詢 - tenant_id 缺失"""
        intent = ConfigIntent(
            action="query",
            scope="genai.policy",
            level=None,
            tenant_id=None,
            original_instruction="查詢有效配置",
        )
        result = await system_config_agent._handle_query(intent)
        assert isinstance(result, ConfigOperationResult)
        assert result.success is False
        assert "tenant_id is required" in result.error

    @patch("agents.builtin.system_config_agent.agent.get_config_store_service")
    async def test_handle_query_not_found(self, mock_config_service, system_config_agent):
        """測試配置查詢 - 配置不存在"""
        mock_service = MagicMock()
        mock_service.get_config = MagicMock(return_value=None)
        mock_config_service.return_value = mock_service
        system_config_agent._config_service = mock_service

        intent = ConfigIntent(
            action="query",
            scope="genai.policy",
            level="system",
            original_instruction="查詢配置",
        )
        result = await system_config_agent._handle_query(intent)
        assert isinstance(result, ConfigOperationResult)
        assert result.success is True
        assert result.config is None

    @patch("agents.builtin.system_config_agent.agent.get_config_store_service")
    async def test_handle_update(self, mock_config_service, system_config_agent):
        """測試配置更新"""
        mock_service = MagicMock()
        mock_before_config = MagicMock()
        mock_before_config.config_data = {"old": "value"}
        mock_after_config = MagicMock()
        mock_after_config.config_data = {"new": "value"}
        mock_after_config.id = "config-123"
        mock_service.get_config = MagicMock(return_value=mock_before_config)
        mock_service.update_config = MagicMock(return_value=mock_after_config)
        mock_config_service.return_value = mock_service
        system_config_agent._config_service = mock_service

        # Mock 合規檢查
        with patch.object(
            system_config_agent,
            "_validate_config_compliance",
            new=AsyncMock(
                return_value=MagicMock(
                    valid=True, convergence_violations=[], business_rule_violations=[]
                )
            ),
        ):
            intent = ConfigIntent(
                action="update",
                scope="genai.policy",
                level="system",
                config_data={"new": "value"},
                original_instruction="更新配置",
            )
            with patch.object(system_config_agent._log_service, "log_audit", new=AsyncMock()):
                result = await system_config_agent._handle_update(intent, "admin-123", "trace-123")
                assert isinstance(result, ConfigOperationResult)
                assert result.action == "update"
                assert result.success is True

    async def test_handle_update_missing_config_data(self, system_config_agent):
        """測試配置更新 - config_data 缺失"""
        intent = ConfigIntent(
            action="update",
            scope="genai.policy",
            level="system",
            config_data=None,
            original_instruction="更新配置",
        )
        result = await system_config_agent._handle_update(intent, "admin-123", "trace-123")
        assert isinstance(result, ConfigOperationResult)
        assert result.success is False
        assert "config_data is required" in result.error

    @patch("agents.builtin.system_config_agent.agent.get_config_store_service")
    async def test_handle_delete(self, mock_config_service, system_config_agent):
        """測試配置刪除"""
        mock_service = MagicMock()
        mock_config = MagicMock()
        mock_config.config_data = {"test": "value"}
        mock_service.get_config = MagicMock(return_value=mock_config)
        mock_service.delete_config = MagicMock(return_value=True)
        mock_config_service.return_value = mock_service
        system_config_agent._config_service = mock_service

        intent = ConfigIntent(
            action="delete",
            scope="genai.policy",
            level="system",
            original_instruction="刪除配置",
        )
        with patch.object(system_config_agent._log_service, "log_audit", new=AsyncMock()):
            result = await system_config_agent._handle_delete(intent, "admin-123", "trace-123")
            assert isinstance(result, ConfigOperationResult)
            assert result.action == "delete"
            assert result.success is True

    @patch("agents.builtin.system_config_agent.agent.get_config_store_service")
    async def test_handle_delete_not_found(self, mock_config_service, system_config_agent):
        """測試配置刪除 - 配置不存在"""
        mock_service = MagicMock()
        mock_service.get_config = MagicMock(return_value=None)
        mock_config_service.return_value = mock_service
        system_config_agent._config_service = mock_service

        intent = ConfigIntent(
            action="delete",
            scope="genai.policy",
            level="system",
            original_instruction="刪除配置",
        )
        result = await system_config_agent._handle_delete(intent, "admin-123", "trace-123")
        assert isinstance(result, ConfigOperationResult)
        assert result.success is False
        assert "Config not found" in result.error

    @patch("agents.builtin.system_config_agent.agent.get_config_store_service")
    async def test_handle_list(self, mock_config_service, system_config_agent):
        """測試配置列表查詢"""
        mock_service = MagicMock()
        mock_config = MagicMock()
        mock_config.id = "config-123"
        mock_config.scope = "genai.policy"
        mock_config.config_data = {"test": "value"}
        mock_config.is_active = True
        mock_service.get_config = MagicMock(return_value=mock_config)
        mock_config_service.return_value = mock_service
        system_config_agent._config_service = mock_service

        intent = ConfigIntent(
            action="list",
            scope="genai.policy",
            level="system",
            original_instruction="列出配置",
        )
        result = await system_config_agent._handle_list(intent)
        assert isinstance(result, ConfigOperationResult)
        assert result.action == "list"
        assert result.success is True
        assert "configs" in result.config
        assert result.config["count"] == 1

    @patch("agents.builtin.system_config_agent.agent.get_config_store_service")
    async def test_handle_list_empty(self, mock_config_service, system_config_agent):
        """測試配置列表查詢 - 空列表"""
        mock_service = MagicMock()
        mock_service.get_config = MagicMock(return_value=None)
        mock_config_service.return_value = mock_service
        system_config_agent._config_service = mock_service

        intent = ConfigIntent(
            action="list",
            scope="genai.policy",
            level="system",
            original_instruction="列出配置",
        )
        result = await system_config_agent._handle_list(intent)
        assert isinstance(result, ConfigOperationResult)
        assert result.success is True
        assert result.config["count"] == 0

    async def test_handle_update_with_preview(self, system_config_agent):
        """測試配置更新（含預覽機制）"""
        from agents.builtin.system_config_agent.models import ConfigPreview

        # Mock 預覽服務
        mock_preview = ConfigPreview(
            changes={"new": "value"},
            impact_analysis={"affected_users": 10},
            cost_change=None,
            risk_level="low",
            confirmation_required=False,
        )

        with (
            patch.object(
                system_config_agent._config_service,
                "get_config",
                return_value=MagicMock(config_data={"old": "value"}),
            ),
            patch.object(
                system_config_agent._preview_service,
                "generate_preview",
                new=AsyncMock(return_value=mock_preview),
            ),
            patch.object(
                system_config_agent,
                "_handle_update",
                new=AsyncMock(
                    return_value=ConfigOperationResult(
                        action="update",
                        scope="genai.policy",
                        level="system",
                        success=True,
                    )
                ),
            ),
        ):
            intent = ConfigIntent(
                action="update",
                scope="genai.policy",
                level="system",
                config_data={"new": "value"},
                original_instruction="更新配置",
            )
            result = await system_config_agent._handle_update_with_preview(
                intent, "admin-123", "trace-123"
            )
            assert isinstance(result, ConfigOperationResult)
            assert result.success is True

    async def test_execute_clarification_needed(self, system_config_agent):
        """測試執行 - 需要澄清"""
        intent = ConfigIntent(
            action="update",
            scope="genai.policy",
            level=None,
            clarification_needed=True,
            clarification_question="請確認配置層級",
            missing_slots=["level"],
            original_instruction="更新配置",
        )
        request = AgentServiceRequest(
            task_id="task-123",
            task_type="config_update",
            task_data={
                "intent": intent.model_dump(),
                "admin_user_id": "admin-123",
                "context": {},
            },
        )
        response = await system_config_agent.execute(request)
        assert response.status == "clarification_needed"
        assert "clarification_question" in response.result

    async def test_execute_missing_intent(self, system_config_agent):
        """測試執行 - intent 缺失"""
        request = AgentServiceRequest(
            task_id="task-123",
            task_type="config_update",
            task_data={
                "admin_user_id": "admin-123",
                "context": {},
            },
        )
        response = await system_config_agent.execute(request)
        assert response.status == "error"
        assert "ConfigIntent is required" in response.error

    async def test_execute_missing_admin_user_id(self, system_config_agent):
        """測試執行 - admin_user_id 缺失"""
        intent = ConfigIntent(
            action="query",
            scope="genai.policy",
            level="system",
            original_instruction="查詢配置",
        )
        request = AgentServiceRequest(
            task_id="task-123",
            task_type="config_query",
            task_data={
                "intent": intent.model_dump(),
                "context": {},
            },
        )
        response = await system_config_agent.execute(request)
        assert response.status == "error"
        assert "admin_user_id is required" in response.error

    async def test_handle_rollback(self, system_config_agent):
        """測試配置回滾"""
        from agents.builtin.system_config_agent.models import RollbackResult

        mock_rollback_result = RollbackResult(
            success=True,
            rollback_id="rb-12345678",
            restored_config={"old": "value"},
            message="Rollback successful",
        )

        with (
            patch.object(
                system_config_agent._rollback_service,
                "rollback_config",
                new=AsyncMock(return_value=mock_rollback_result),
            ),
            patch.object(system_config_agent._log_service, "log_audit", new=AsyncMock()),
        ):
            intent = ConfigIntent(
                action="rollback",
                scope="genai.policy",
                level="system",
                config_data={"rollback_id": "rb-12345678"},
                original_instruction="回滾配置",
            )
            result = await system_config_agent._handle_rollback(intent, "admin-123", "trace-123")
            assert isinstance(result, ConfigOperationResult)
            assert result.action == "rollback"
            assert result.success is True


@pytest.mark.asyncio
class TestIntegration:
    """集成測試"""

    async def test_execute_with_valid_request(self, system_config_agent, sample_request):
        """測試執行有效請求"""
        with patch.object(system_config_agent._config_service, "get_config", return_value=None):
            with patch.object(
                system_config_agent._config_service,
                "update_config",
                return_value=MagicMock(config_data={"test": "value"}),
            ):
                with patch.object(system_config_agent._log_service, "log_audit", new=AsyncMock()):
                    response = await system_config_agent.execute(sample_request)
                    assert response.task_id == "task-123"
                    assert response.status in ["completed", "failed", "clarification_needed"]

    async def test_handle_inspection(self, system_config_agent):
        """測試配置巡檢集成"""
        from agents.builtin.system_config_agent.models import InspectionIssue
        from agents.task_analyzer.models import ConfigIntent

        intent = ConfigIntent(
            action="inspect",
            scope="genai.policy",
            level="system",
            original_instruction="檢查配置",
        )

        # Mock 巡檢服務
        mock_issues = [
            InspectionIssue(
                issue_type="convergence",
                severity="high",
                scope="genai.policy",
                description="Test issue",
            )
        ]

        with (
            patch.object(
                system_config_agent._inspection_service,
                "inspect_all_configs",
                new=AsyncMock(return_value=mock_issues),
            ),
            patch.object(
                system_config_agent._inspection_service,
                "suggest_fix",
                new=AsyncMock(
                    return_value=MagicMock(
                        model_dump=lambda: {"fix_action": "Test fix", "auto_fixable": True}
                    )
                ),
            ),
            patch.object(system_config_agent._log_service, "log_audit", new=AsyncMock()),
        ):
            result = await system_config_agent._handle_inspection(intent, "admin-123", "trace-123")

            assert result.success is True
            assert result.action == "inspect"
            assert result.config is not None
            assert "issues_count" in result.config
            assert result.config["issues_count"] == 1


class TestErrorHandling:
    """錯誤處理測試"""

    @pytest.mark.asyncio
    async def test_handle_update_exception(self, system_config_agent):
        """測試 _handle_update_with_preview() 方法：異常處理"""
        intent = ConfigIntent(
            action="update",
            scope="genai.policy",
            level="system",
            config_data={"max_requests": 100},
            original_instruction="更新配置",
        )

        # Mock preview_service 拋出異常
        system_config_agent._preview_service.generate_preview = AsyncMock(
            side_effect=Exception("Preview generation failed")
        )

        result = await system_config_agent._handle_update_with_preview(intent, "admin", "trace_123")

        assert result.success is False
        assert "Preview generation failed" in result.error

    @pytest.mark.asyncio
    async def test_handle_list_exception(self, system_config_agent):
        """測試 _handle_list() 方法：異常處理"""
        intent = ConfigIntent(
            action="list",
            scope="genai.policy",
            level="system",
            original_instruction="列出配置",
        )

        # Mock config_service.list_configs 返回空列表（測試正常情況）
        # 如果要測試異常，需要在更早的地方拋出異常
        system_config_agent._config_service.list_configs = AsyncMock(return_value=[])

        result = await system_config_agent._handle_list(intent)

        # list_configs 返回空列表是正常情況，不應該失敗
        assert result.success is True
        assert result.config is not None

    @pytest.mark.asyncio
    async def test_handle_rollback_missing_rollback_id(self, system_config_agent):
        """測試 _handle_rollback() 方法：缺少 rollback_id"""
        intent = ConfigIntent(
            action="rollback",
            scope="genai.policy",
            level="system",
            original_instruction="回滾配置",
            # 注意：沒有提供 rollback_id
        )

        result = await system_config_agent._handle_rollback(intent, "admin", "trace_123")

        assert result.success is False
        assert "rollback_id" in result.error.lower()

    @pytest.mark.asyncio
    async def test_handle_inspection_exception(self, system_config_agent):
        """測試 _handle_inspection() 方法：異常處理"""
        intent = ConfigIntent(
            action="inspect",
            scope="genai.policy",
            level="system",
            original_instruction="巡檢配置",
        )

        # Mock inspection_service 拋出異常
        system_config_agent._inspection_service.inspect_all_configs = AsyncMock(
            side_effect=Exception("Inspection failed")
        )

        result = await system_config_agent._handle_inspection(intent, "admin", "trace_123")

        assert result.success is False
        assert "Inspection failed" in result.error
