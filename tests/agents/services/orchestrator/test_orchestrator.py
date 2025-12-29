# 代碼功能說明: Orchestrator 單元測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Orchestrator 單元測試"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.models import ConfigIntent


class TestAgentOrchestrator:
    """AgentOrchestrator 測試類"""

    @pytest.fixture
    def orchestrator(self):
        """創建 AgentOrchestrator 實例"""
        with patch("agents.services.orchestrator.orchestrator.get_agent_registry"):
            return AgentOrchestrator()

    @pytest.fixture
    def sample_config_intent(self):
        """示例 ConfigIntent"""
        return ConfigIntent(
            action="query",
            scope="genai.policy",
            level="system",
            original_instruction="查詢系統配置",
        )

    @pytest.fixture
    def sample_config_definition(self):
        """示例配置定義"""
        return {
            "scope": "genai.policy",
            "fields": {
                "max_concurrent_requests": {
                    "type": "integer",
                    "min": 1,
                    "max": 1000,
                    "description": "最大並發請求數",
                },
                "default_model": {
                    "type": "string",
                    "options": ["gpt-4", "gpt-3.5-turbo", "claude-3"],
                    "description": "默認模型",
                },
                "enabled": {
                    "type": "boolean",
                    "description": "是否啟用",
                },
            },
        }

    def test_check_type_integer(self, orchestrator):
        """測試 _check_type() 方法：檢查整數類型"""
        assert orchestrator._check_type(42, "integer") is True
        assert orchestrator._check_type("42", "integer") is False
        assert orchestrator._check_type(42.0, "integer") is False

    def test_check_type_number(self, orchestrator):
        """測試 _check_type() 方法：檢查數值類型（int 或 float）"""
        assert orchestrator._check_type(42, "number") is True
        assert orchestrator._check_type(42.5, "number") is True
        assert orchestrator._check_type("42", "number") is False

    def test_check_type_string(self, orchestrator):
        """測試 _check_type() 方法：檢查字符串類型"""
        assert orchestrator._check_type("hello", "string") is True
        assert orchestrator._check_type(42, "string") is False

    def test_check_type_boolean(self, orchestrator):
        """測試 _check_type() 方法：檢查布爾類型"""
        assert orchestrator._check_type(True, "boolean") is True
        assert orchestrator._check_type(False, "boolean") is True
        assert orchestrator._check_type(1, "boolean") is False

    def test_check_type_array(self, orchestrator):
        """測試 _check_type() 方法：檢查數組類型"""
        assert orchestrator._check_type([1, 2, 3], "array") is True
        assert orchestrator._check_type("not array", "array") is False

    def test_check_type_object(self, orchestrator):
        """測試 _check_type() 方法：檢查對象類型"""
        assert orchestrator._check_type({"key": "value"}, "object") is True
        assert orchestrator._check_type("not object", "object") is False

    def test_validate_field_type_check(self, orchestrator, sample_config_definition):
        """測試 _validate_field() 方法：類型檢查"""
        field_def = sample_config_definition["fields"]["max_concurrent_requests"]

        # 正確類型
        result = orchestrator._validate_field("max_concurrent_requests", 100, field_def)
        assert result.valid is True

        # 錯誤類型
        result = orchestrator._validate_field("max_concurrent_requests", "100", field_def)
        assert result.valid is False
        assert "類型錯誤" in result.reason

    def test_validate_field_min_boundary(self, orchestrator, sample_config_definition):
        """測試 _validate_field() 方法：最小值邊界檢查"""
        field_def = sample_config_definition["fields"]["max_concurrent_requests"]

        # 小於最小值
        result = orchestrator._validate_field("max_concurrent_requests", 0, field_def)
        assert result.valid is False
        assert "小於系統定義下限" in result.reason

        # 等於最小值
        result = orchestrator._validate_field("max_concurrent_requests", 1, field_def)
        assert result.valid is True

        # 大於最小值
        result = orchestrator._validate_field("max_concurrent_requests", 100, field_def)
        assert result.valid is True

    def test_validate_field_max_boundary(self, orchestrator, sample_config_definition):
        """測試 _validate_field() 方法：最大值邊界檢查"""
        field_def = sample_config_definition["fields"]["max_concurrent_requests"]

        # 大於最大值
        result = orchestrator._validate_field("max_concurrent_requests", 2000, field_def)
        assert result.valid is False
        assert "超出系統定義上限" in result.reason

        # 等於最大值
        result = orchestrator._validate_field("max_concurrent_requests", 1000, field_def)
        assert result.valid is True

        # 小於最大值
        result = orchestrator._validate_field("max_concurrent_requests", 100, field_def)
        assert result.valid is True

    def test_validate_field_enum_options(self, orchestrator, sample_config_definition):
        """測試 _validate_field() 方法：枚舉值檢查"""
        field_def = sample_config_definition["fields"]["default_model"]

        # 有效選項
        result = orchestrator._validate_field("default_model", "gpt-4", field_def)
        assert result.valid is True

        # 無效選項
        result = orchestrator._validate_field("default_model", "invalid-model", field_def)
        assert result.valid is False
        assert "不在允許列表中" in result.reason

    def test_validate_field_enum_options_array(self, orchestrator):
        """測試 _validate_field() 方法：數組枚舉值檢查"""
        field_def = {
            "type": "array",
            "options": ["option1", "option2", "option3"],
        }

        # 有效選項
        result = orchestrator._validate_field("test_field", ["option1", "option2"], field_def)
        assert result.valid is True

        # 無效選項
        result = orchestrator._validate_field("test_field", ["option1", "invalid"], field_def)
        assert result.valid is False
        assert "包含無效值" in result.reason

    @pytest.mark.asyncio
    async def test_pre_check_config_intent_valid(
        self, orchestrator, sample_config_intent, sample_config_definition
    ):
        """測試 _pre_check_config_intent() 方法：有效的配置意圖"""
        # Mock DefinitionLoader
        mock_loader = Mock()
        mock_loader.get_definition = Mock(return_value=sample_config_definition)
        orchestrator._definition_loader = mock_loader

        intent_dict = sample_config_intent.model_dump()
        result = await orchestrator._pre_check_config_intent(intent_dict, "system_config_agent")

        assert result.valid is True

    @pytest.mark.asyncio
    async def test_pre_check_config_intent_missing_scope(self, orchestrator):
        """測試 _pre_check_config_intent() 方法：缺少 scope"""
        intent_dict = {"action": "query"}

        result = await orchestrator._pre_check_config_intent(intent_dict, "system_config_agent")

        assert result.valid is False
        assert "scope" in result.reason.lower() or "required" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_pre_check_config_intent_definition_not_found(
        self, orchestrator, sample_config_intent
    ):
        """測試 _pre_check_config_intent() 方法：配置定義不存在"""
        # Mock DefinitionLoader 返回 None
        mock_loader = Mock()
        mock_loader.get_definition = Mock(return_value=None)
        orchestrator._definition_loader = mock_loader

        intent_dict = sample_config_intent.model_dump()
        result = await orchestrator._pre_check_config_intent(intent_dict, "system_config_agent")

        assert result.valid is False
        assert "Config definition not found" in result.reason

    @pytest.mark.asyncio
    async def test_pre_check_config_intent_invalid_field(
        self, orchestrator, sample_config_intent, sample_config_definition
    ):
        """測試 _pre_check_config_intent() 方法：無效的字段"""
        # Mock DefinitionLoader
        mock_loader = Mock()
        mock_loader.get_definition = Mock(return_value=sample_config_definition)
        orchestrator._definition_loader = mock_loader

        # 使用無效的字段值（超出範圍）
        intent_dict = sample_config_intent.model_dump()
        intent_dict["config_data"] = {"max_concurrent_requests": 2000}

        result = await orchestrator._pre_check_config_intent(intent_dict, "system_config_agent")

        assert result.valid is False
        assert "超出系統定義上限" in result.reason

    @pytest.mark.asyncio
    async def test_check_permission_with_security_agent(self, orchestrator):
        """測試 _check_permission() 方法：使用 Security Agent 進行權限檢查"""
        # Mock Security Agent
        mock_security_agent = AsyncMock()
        from agents.builtin.security_manager.models import SecurityCheckResult

        mock_security_agent.verify_access = AsyncMock(
            return_value=SecurityCheckResult(
                allowed=True,
                reason="Permission granted",
                requires_double_check=False,
                risk_level="low",
                audit_context={},
            )
        )
        orchestrator._security_agent = mock_security_agent

        intent_dict = {"action": "query", "scope": "genai.policy"}
        result = await orchestrator._check_permission(
            user_id="user_123",
            intent=intent_dict,
            target_agents=["system_config_agent"],
        )

        assert result.allowed is True
        assert result.risk_level == "low"

    @pytest.mark.asyncio
    async def test_check_permission_security_agent_not_available(self, orchestrator):
        """測試 _check_permission() 方法：Security Agent 不可用時默認允許"""
        # Mock _get_security_agent 返回 None
        orchestrator._get_security_agent = Mock(return_value=None)

        intent_dict = {"action": "query", "scope": "genai.policy"}
        result = await orchestrator._check_permission(
            user_id="user_123",
            intent=intent_dict,
            target_agents=["system_config_agent"],
        )

        assert result.allowed is True
        assert (
            "Security Agent not available" in result.reason
            or "not available" in result.reason.lower()
        )

    def test_format_result_simple(self, orchestrator):
        """測試 _format_result_simple() 方法：簡單結果修飾"""
        agent_result = {"status": "success", "config": {"max_requests": 100}}
        original_instruction = "查詢系統配置"

        formatted = orchestrator._format_result_simple(agent_result, original_instruction)

        assert isinstance(formatted, str)
        assert original_instruction in formatted

    def test_format_result_simple_with_error(self, orchestrator):
        """測試 _format_result_simple() 方法：錯誤結果修飾"""
        agent_result = {"status": "error", "error": "配置未找到"}
        original_instruction = "查詢系統配置"

        formatted = orchestrator._format_result_simple(agent_result, original_instruction)

        assert isinstance(formatted, str)
        assert "配置未找到" in formatted or "error" in formatted.lower()

    @pytest.mark.asyncio
    async def test_process_natural_language_request_complete_flow(self, orchestrator):
        """測試 process_natural_language_request() 完整流程"""
        # Mock Task Analyzer
        from agents.task_analyzer.models import (
            LLMProvider,
            TaskAnalysisResult,
            TaskType,
            WorkflowType,
        )

        mock_analyzer = AsyncMock()
        mock_analyzer.analyze = AsyncMock(
            return_value=TaskAnalysisResult(
                task_id="test_task",
                task_type=TaskType.EXECUTION,
                workflow_type=WorkflowType.LANGCHAIN,
                llm_provider=LLMProvider.CHATGPT,
                confidence=0.95,
                requires_agent=True,
                suggested_agents=["system_config_agent"],
                analysis_details={
                    "intent": ConfigIntent(
                        action="query",
                        scope="genai.policy",
                        level="system",
                        original_instruction="查詢系統配置",
                    ).model_dump()
                },
            )
        )
        orchestrator._task_analyzer = mock_analyzer

        # Mock DefinitionLoader
        mock_loader = Mock()
        mock_loader.get_definition = Mock(return_value={"scope": "genai.policy", "fields": {}})
        orchestrator._definition_loader = mock_loader

        # Mock Security Agent
        from agents.builtin.security_manager.models import SecurityCheckResult

        mock_security = AsyncMock()
        mock_security.verify_access = AsyncMock(
            return_value=SecurityCheckResult(
                allowed=True,
                reason="Permission granted",
                requires_double_check=False,
                risk_level="low",
                audit_context={},
            )
        )
        orchestrator._security_agent = mock_security

        # Mock LogService
        mock_log_service = AsyncMock()
        orchestrator._get_log_service = Mock(return_value=mock_log_service)

        result = await orchestrator.process_natural_language_request(
            instruction="查詢系統配置",
            user_id="user_123",
        )

        assert result["status"] == "task_created"
        assert "task_id" in result["result"]
        assert "trace_id" in result

    @pytest.mark.asyncio
    async def test_process_natural_language_request_log_query(self, orchestrator):
        """測試 process_natural_language_request() - 日誌查詢類型"""
        from agents.task_analyzer.models import (
            LLMProvider,
            LogQueryIntent,
            TaskAnalysisResult,
            TaskType,
            WorkflowType,
        )

        mock_analyzer = AsyncMock()
        mock_analyzer.analyze = AsyncMock(
            return_value=TaskAnalysisResult(
                task_id="test_task",
                task_type=TaskType.LOG_QUERY,
                workflow_type=WorkflowType.LANGCHAIN,
                llm_provider=LLMProvider.CHATGPT,
                confidence=0.95,
                requires_agent=False,
                suggested_agents=[],
                analysis_details={
                    "intent": LogQueryIntent(
                        log_type="AUDIT", actor="user_123", limit=10
                    ).model_dump()
                },
            )
        )
        orchestrator._task_analyzer = mock_analyzer

        # Mock LogService
        mock_log_service = AsyncMock()
        mock_log_service.get_audit_logs = AsyncMock(return_value=[{"_key": "log1"}])
        orchestrator._get_log_service = Mock(return_value=mock_log_service)

        result = await orchestrator.process_natural_language_request(
            instruction="查詢審計日誌",
            user_id="user_123",
        )

        assert result["status"] == "completed"
        assert "result" in result

    @pytest.mark.asyncio
    async def test_process_natural_language_request_clarification_needed(self, orchestrator):
        """測試 process_natural_language_request() - 需要澄清"""
        from agents.task_analyzer.models import (
            LLMProvider,
            TaskAnalysisResult,
            TaskType,
            WorkflowType,
        )

        mock_analyzer = AsyncMock()
        mock_analyzer.analyze = AsyncMock(
            return_value=TaskAnalysisResult(
                task_id="test_task",
                task_type=TaskType.EXECUTION,
                workflow_type=WorkflowType.LANGCHAIN,
                llm_provider=LLMProvider.CHATGPT,
                confidence=0.7,
                requires_agent=True,
                suggested_agents=["system_config_agent"],
                analysis_details={
                    "intent": ConfigIntent(
                        action="update",
                        scope="genai.policy",
                        level="system",
                        original_instruction="更新配置",
                    ).model_dump(),
                    "clarification_needed": True,
                    "clarification_question": "請指定要更新的字段",
                    "missing_slots": ["config_data"],
                },
            )
        )
        orchestrator._task_analyzer = mock_analyzer

        # Mock LogService
        mock_log_service = AsyncMock()
        orchestrator._get_log_service = Mock(return_value=mock_log_service)

        result = await orchestrator.process_natural_language_request(
            instruction="更新配置",
            user_id="user_123",
        )

        assert result["status"] == "clarification_needed"
        assert "clarification_question" in result["result"]

    @pytest.mark.asyncio
    async def test_process_natural_language_request_permission_denied(self, orchestrator):
        """測試 process_natural_language_request() - 權限被拒絕"""
        from agents.task_analyzer.models import (
            LLMProvider,
            TaskAnalysisResult,
            TaskType,
            WorkflowType,
        )

        mock_analyzer = AsyncMock()
        mock_analyzer.analyze = AsyncMock(
            return_value=TaskAnalysisResult(
                task_id="test_task",
                task_type=TaskType.EXECUTION,
                workflow_type=WorkflowType.LANGCHAIN,
                llm_provider=LLMProvider.CHATGPT,
                confidence=0.95,
                requires_agent=True,
                suggested_agents=["system_config_agent"],
                analysis_details={
                    "intent": ConfigIntent(
                        action="update",
                        scope="genai.policy",
                        level="system",
                        original_instruction="更新配置",
                    ).model_dump()
                },
            )
        )
        orchestrator._task_analyzer = mock_analyzer

        # Mock DefinitionLoader
        mock_loader = Mock()
        mock_loader.get_definition = Mock(return_value={"scope": "genai.policy", "fields": {}})
        orchestrator._definition_loader = mock_loader

        # Mock Security Agent - 拒絕權限
        from agents.builtin.security_manager.models import SecurityCheckResult

        mock_security = AsyncMock()
        mock_security.verify_access = AsyncMock(
            return_value=SecurityCheckResult(
                allowed=False,
                reason="Permission denied",
                requires_double_check=False,
                risk_level="high",
                audit_context={},
            )
        )
        orchestrator._security_agent = mock_security

        # Mock LogService
        mock_log_service = AsyncMock()
        orchestrator._get_log_service = Mock(return_value=mock_log_service)

        result = await orchestrator.process_natural_language_request(
            instruction="更新配置",
            user_id="user_123",
        )

        assert result["status"] == "permission_denied"
        assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_process_natural_language_request_exception_handling(self, orchestrator):
        """測試 process_natural_language_request() - 異常處理"""
        # Mock Task Analyzer 拋出異常
        mock_analyzer = AsyncMock()
        mock_analyzer.analyze = AsyncMock(side_effect=Exception("Analyzer error"))
        orchestrator._task_analyzer = mock_analyzer

        # Mock LogService
        mock_log_service = AsyncMock()
        orchestrator._get_log_service = Mock(return_value=mock_log_service)

        result = await orchestrator.process_natural_language_request(
            instruction="測試指令",
            user_id="user_123",
        )

        assert result["status"] == "failed"
        assert "error" in result
        assert "trace_id" in result

    @pytest.mark.asyncio
    async def test_handle_log_query_audit_logs(self, orchestrator):
        """測試 _handle_log_query() - 審計日誌查詢"""
        from agents.task_analyzer.models import LogQueryIntent

        analysis_result = Mock()
        analysis_result.get_intent = Mock(
            return_value=LogQueryIntent(log_type="AUDIT", actor="user_123", limit=10)
        )

        # Mock LogService
        mock_log_service = AsyncMock()
        mock_log_service.get_audit_logs = AsyncMock(return_value=[{"_key": "log1"}])
        orchestrator._get_log_service = Mock(return_value=mock_log_service)

        result = await orchestrator._handle_log_query(analysis_result, "user_123", "trace_123")

        assert result["status"] == "completed"
        assert "result" in result

    @pytest.mark.asyncio
    async def test_handle_log_query_security_logs(self, orchestrator):
        """測試 _handle_log_query() - 安全日誌查詢"""
        from agents.task_analyzer.models import LogQueryIntent

        analysis_result = Mock()
        analysis_result.get_intent = Mock(
            return_value=LogQueryIntent(log_type="SECURITY", actor="user_123", limit=10)
        )

        # Mock LogService
        mock_log_service = AsyncMock()
        mock_log_service.get_security_logs = AsyncMock(return_value=[{"_key": "sec1"}])
        orchestrator._get_log_service = Mock(return_value=mock_log_service)

        result = await orchestrator._handle_log_query(analysis_result, "user_123", "trace_123")

        assert result["status"] == "completed"
        assert "result" in result

    @pytest.mark.asyncio
    async def test_handle_log_query_by_trace_id(self, orchestrator):
        """測試 _handle_log_query() - 按 trace_id 查詢"""
        from agents.task_analyzer.models import LogQueryIntent

        analysis_result = Mock()
        analysis_result.get_intent = Mock(
            return_value=LogQueryIntent(query_type="trace", trace_id="trace_123")
        )

        # Mock LogService
        mock_log_service = AsyncMock()
        mock_log_service.get_logs_by_trace_id = AsyncMock(
            return_value=[{"_key": "log1"}, {"_key": "log2"}]
        )
        orchestrator._get_log_service = Mock(return_value=mock_log_service)

        result = await orchestrator._handle_log_query(analysis_result, "user_123", "trace_123")

        assert result["status"] == "completed"
        assert len(result["result"]["logs"]) == 2

    def test_generate_confirmation_message(self, orchestrator):
        """測試 _generate_confirmation_message() 方法"""
        intent = ConfigIntent(
            action="delete",
            scope="genai.policy",
            level="system",
            original_instruction="刪除配置",
        )

        message = orchestrator._generate_confirmation_message(intent, "high")

        assert isinstance(message, str)
        assert "high" in message.lower() or "刪除" in message

    def test_format_result_simple_with_data(self, orchestrator):
        """測試 _format_result_simple() 方法：包含數據的結果"""
        agent_result = {
            "status": "success",
            "data": {"max_requests": 100, "enabled": True},
        }
        original_instruction = "查詢系統配置"

        formatted = orchestrator._format_result_simple(agent_result, original_instruction)

        assert isinstance(formatted, str)
        assert original_instruction in formatted
