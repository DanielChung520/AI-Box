# 代碼功能說明: 錯誤處理端到端測試
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""錯誤處理端到端測試 - 測試各種錯誤場景"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import TaskAnalysisRequest


class TestErrorHandlingE2E:
    """錯誤處理端到端測試類"""

    @pytest.mark.asyncio
    async def test_llm_timeout_error(self, task_analyzer: TaskAnalyzer):
        """測試 LLM 調用超時錯誤"""
        request = TaskAnalysisRequest(
            task="測試任務",
            context={"user_id": "test_user"},
        )

        # Mock LLM 調用超時
        with patch.object(
            task_analyzer.router_llm, "analyze", side_effect=TimeoutError("LLM 調用超時")
        ):
            result = await task_analyzer.analyze(request)

            # 驗證錯誤處理
            # 系統應該有 Fallback 機制，不應該完全失敗
            assert result is not None, "即使 LLM 超時，也應該返回結果"

    @pytest.mark.asyncio
    async def test_llm_api_error(self, task_analyzer: TaskAnalyzer):
        """測試 LLM API 錯誤"""
        request = TaskAnalysisRequest(
            task="測試任務",
            context={"user_id": "test_user"},
        )

        # Mock LLM API 錯誤
        with patch.object(
            task_analyzer.router_llm,
            "analyze",
            side_effect=Exception("LLM API 錯誤"),
        ):
            result = await task_analyzer.analyze(request)

            # 驗證錯誤處理
            assert result is not None, "即使 LLM API 錯誤，也應該返回結果"

    @pytest.mark.asyncio
    async def test_database_connection_error(self, task_analyzer: TaskAnalyzer):
        """測試數據庫連接錯誤"""
        request = TaskAnalysisRequest(
            task="查詢配置",
            context={"user_id": "test_user"},
        )

        # Mock 數據庫連接錯誤
        with patch.object(
            task_analyzer.intent_matcher.intent_registry,
            "get_intent",
            side_effect=ConnectionError("數據庫連接失敗"),
        ):
            # 系統應該能夠處理數據庫錯誤，使用 Fallback 機制
            result = await task_analyzer.analyze(request)

            # 驗證錯誤處理
            assert result is not None, "即使數據庫連接失敗，也應該返回結果"

    @pytest.mark.asyncio
    async def test_rag_retrieval_error(self, task_analyzer: TaskAnalyzer):
        """測試 RAG 檢索錯誤"""
        request = TaskAnalysisRequest(
            task="複雜任務需要能力檢索",
            context={"user_id": "test_user"},
        )

        # Mock RAG 檢索錯誤
        with patch.object(
            task_analyzer.decision_engine.rag_service,
            "retrieve",
            side_effect=Exception("RAG 檢索失敗"),
        ):
            result = await task_analyzer.analyze(request)

            # 驗證錯誤處理
            assert result is not None, "即使 RAG 檢索失敗，也應該返回結果"

    @pytest.mark.asyncio
    async def test_policy_check_error(self, task_analyzer: TaskAnalyzer):
        """測試 Policy 檢查錯誤"""
        request = TaskAnalysisRequest(
            task="高風險任務",
            context={"user_id": "test_user"},
        )

        # Mock Policy 檢查錯誤
        with patch.object(
            task_analyzer.decision_engine.policy_service,
            "validate_task",
            side_effect=Exception("Policy 檢查失敗"),
        ):
            result = await task_analyzer.analyze(request)

            # 驗證錯誤處理
            # Policy 檢查失敗應該被記錄，但不應該阻止任務分析
            assert result is not None, "即使 Policy 檢查失敗，也應該返回結果"

    @pytest.mark.asyncio
    async def test_agent_execution_error(self, task_analyzer: TaskAnalyzer):
        """測試 Agent 執行錯誤"""
        request = TaskAnalysisRequest(
            task="需要 Agent 執行的任務",
            context={"user_id": "test_user"},
        )

        # 這個測試主要驗證分析階段，實際 Agent 執行錯誤在 Orchestrator 中處理
        result = await task_analyzer.analyze(request)

        # 驗證分析結果包含建議的 Agent
        if result.requires_agent:
            assert len(result.suggested_agents) > 0, "應該建議使用 Agent"

    @pytest.mark.asyncio
    async def test_network_error(self, task_analyzer: TaskAnalyzer):
        """測試網絡錯誤"""
        request = TaskAnalysisRequest(
            task="需要網絡請求的任務",
            context={"user_id": "test_user"},
        )

        # Mock 網絡錯誤
        with patch(
            "agents.task_analyzer.router_llm.LLMClientFactory.create_client",
            side_effect=ConnectionError("網絡連接失敗"),
        ):
            result = await task_analyzer.analyze(request)

            # 驗證錯誤處理
            assert result is not None, "即使網絡錯誤，也應該返回結果"

    @pytest.mark.asyncio
    async def test_data_validation_error(self, task_analyzer: TaskAnalyzer):
        """測試數據驗證錯誤"""
        # 創建無效的請求
        request = TaskAnalysisRequest(
            task="",  # 空任務
            context={"user_id": "test_user"},
        )

        # 系統應該能夠處理空任務
        result = await task_analyzer.analyze(request)

        # 驗證錯誤處理
        assert result is not None, "即使任務為空，也應該返回結果"

    @pytest.mark.asyncio
    async def test_invalid_intent_error(self, task_analyzer: TaskAnalyzer):
        """測試無效 Intent 錯誤"""
        request = TaskAnalysisRequest(
            task="無法匹配 Intent 的任務",
            context={"user_id": "test_user"},
        )

        # Mock Intent 匹配失敗
        with patch.object(
            task_analyzer.intent_matcher,
            "match_intent",
            return_value=None,  # 匹配失敗
        ):
            result = await task_analyzer.analyze(request)

            # 驗證 Fallback Intent 機制
            assert result is not None, "即使 Intent 匹配失敗，也應該使用 Fallback Intent"
