# 代碼功能說明: Task Analyzer 配置操作解析測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Task Analyzer 配置操作解析測試"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import ConfigIntent, TaskClassificationResult, TaskType


class TestTaskAnalyzerConfigIntent:
    """Task Analyzer 配置操作解析測試類"""

    @pytest.fixture
    def task_analyzer(self):
        """創建 TaskAnalyzer 實例"""
        return TaskAnalyzer()

    @pytest.fixture
    def mock_classification(self):
        """模擬任務分類結果"""
        return TaskClassificationResult(
            task_type=TaskType.QUERY,
            confidence=0.9,
            reasoning="這是配置查詢任務",
        )

    def test_is_config_operation_with_config_keywords(self, task_analyzer, mock_classification):
        """測試 _is_config_operation() 方法：識別配置操作關鍵字"""
        config_tasks = [
            "查詢系統配置",
            "設置限流策略",
            "查看 GenAI policy",
            "修改系統設置",
            "配置模型",
        ]

        for task in config_tasks:
            result = task_analyzer._is_config_operation(mock_classification, task)
            assert result is True, f"應該識別為配置操作: {task}"

    def test_is_config_operation_without_config_keywords(self, task_analyzer, mock_classification):
        """測試 _is_config_operation() 方法：非配置操作不識別"""
        non_config_tasks = [
            "查詢用戶信息",
            "執行文件上傳",
            "分析數據",
        ]

        for task in non_config_tasks:
            result = task_analyzer._is_config_operation(mock_classification, task)
            assert result is False, f"不應該識別為配置操作: {task}"

    @pytest.mark.asyncio
    async def test_extract_config_intent_query(self, task_analyzer, mock_classification):
        """測試 _extract_config_intent() 方法：提取查詢操作意圖"""
        instruction = "查詢系統級的 GenAI 策略配置"
        context = {"user_id": "user_123"}

        # Mock LLM 客戶端（LLMClientFactory 是在函數內部導入的）
        with (
            patch("llm.clients.factory.LLMClientFactory") as mock_factory,
            patch.object(task_analyzer.llm_router, "route"),
        ):
            mock_client = AsyncMock()
            # client.chat() 返回一個字典，包含 "content" 鍵
            mock_response_dict = {
                "content": """{
                "action": "query",
                "scope": "genai.policy",
                "level": "system",
                "tenant_id": null,
                "user_id": null,
                "config_data": null,
                "clarification_needed": false,
                "clarification_question": null,
                "missing_slots": [],
                "original_instruction": "查詢系統級的 GenAI 策略配置"
            }"""
            }
            mock_client.chat = AsyncMock(return_value=mock_response_dict)
            mock_factory.create_client = Mock(return_value=mock_client)

            intent = await task_analyzer._extract_config_intent(
                instruction, mock_classification, context
            )

            assert isinstance(intent, ConfigIntent)
            assert intent.action == "query"
            assert intent.scope == "genai.policy"
            assert intent.level == "system"
            assert intent.clarification_needed is False

    @pytest.mark.asyncio
    async def test_extract_config_intent_update(self, task_analyzer, mock_classification):
        """測試 _extract_config_intent() 方法：提取更新操作意圖"""
        instruction = "更新租戶 A 的限流設置為 500"
        context = {"user_id": "user_123", "tenant_id": "tenant_a"}

        with (
            patch("llm.clients.factory.LLMClientFactory") as mock_factory,
            patch.object(task_analyzer.llm_router, "route"),
        ):
            mock_client = AsyncMock()
            mock_response_dict = {
                "content": """{
                "action": "update",
                "scope": "genai.policy",
                "level": "tenant",
                "tenant_id": "tenant_a",
                "user_id": null,
                "config_data": {"rate_limit": 500},
                "clarification_needed": false,
                "clarification_question": null,
                "missing_slots": [],
                "original_instruction": "更新租戶 A 的限流設置為 500"
            }"""
            }
            mock_client.chat = AsyncMock(return_value=mock_response_dict)
            mock_factory.create_client = Mock(return_value=mock_client)

            intent = await task_analyzer._extract_config_intent(
                instruction, mock_classification, context
            )

            assert isinstance(intent, ConfigIntent)
            assert intent.action == "update"
            assert intent.scope == "genai.policy"
            assert intent.level == "tenant"
            assert intent.tenant_id == "tenant_a"
            assert intent.config_data == {"rate_limit": 500}

    @pytest.mark.asyncio
    async def test_extract_config_intent_clarification_needed(
        self, task_analyzer, mock_classification
    ):
        """測試 _extract_config_intent() 方法：缺失槽位時需要澄清"""
        instruction = "修改配置"
        context = {"user_id": "user_123"}

        with (
            patch("llm.clients.factory.LLMClientFactory") as mock_factory,
            patch.object(task_analyzer.llm_router, "route"),
        ):
            mock_client = AsyncMock()
            mock_response_dict = {
                "content": """{
                "action": "update",
                "scope": "genai.policy",
                "level": null,
                "tenant_id": null,
                "user_id": null,
                "config_data": null,
                "clarification_needed": true,
                "clarification_question": "請確認：\\n1. 要修改哪一層配置？(系統級/租戶級/用戶級)\\n2. 要修改哪些具體配置項？",
                "missing_slots": ["level", "config_data"],
                "original_instruction": "修改配置"
            }"""
            }
            mock_client.chat = AsyncMock(return_value=mock_response_dict)
            mock_factory.create_client = Mock(return_value=mock_client)

            intent = await task_analyzer._extract_config_intent(
                instruction, mock_classification, context
            )

            assert isinstance(intent, ConfigIntent)
            assert intent.clarification_needed is True
            assert len(intent.missing_slots) > 0
            assert "level" in intent.missing_slots or "config_data" in intent.missing_slots
            assert intent.clarification_question is not None

    @pytest.mark.asyncio
    async def test_extract_config_intent_all_actions(self, task_analyzer, mock_classification):
        """測試各種配置操作：query、create、update、delete、list、rollback、inspect"""
        actions = ["query", "create", "update", "delete", "list", "rollback", "inspect"]

        for action in actions:
            instruction = f"{action} 配置"
            context = {"user_id": "user_123"}

            with (
                patch("llm.clients.factory.LLMClientFactory") as mock_factory,
                patch.object(task_analyzer.llm_router, "route"),
            ):
                mock_client = AsyncMock()
                mock_response_dict = {
                    "content": f"""{{
                    "action": "{action}",
                    "scope": "genai.policy",
                    "level": "system",
                    "tenant_id": null,
                    "user_id": null,
                    "config_data": null,
                    "clarification_needed": false,
                    "clarification_question": null,
                    "missing_slots": [],
                    "original_instruction": "{instruction}"
                }}"""
                }
                mock_client.chat = AsyncMock(return_value=mock_response_dict)
                mock_factory.create_client = Mock(return_value=mock_client)

                intent = await task_analyzer._extract_config_intent(
                    instruction, mock_classification, context
                )

                assert isinstance(intent, ConfigIntent)
                assert intent.action == action

    def test_config_intent_model_validation(self):
        """測試 ConfigIntent 模型驗證"""
        # 有效的 ConfigIntent
        valid_intent = ConfigIntent(
            action="query",
            scope="genai.policy",
            level="system",
            original_instruction="查詢配置",
        )
        assert valid_intent.action == "query"

        # 無效的 action（應該拋出驗證錯誤）
        with pytest.raises(Exception):  # Pydantic 驗證錯誤
            ConfigIntent(
                action="invalid_action",
                scope="genai.policy",
                original_instruction="無效操作",
            )
