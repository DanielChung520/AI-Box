# 代碼功能說明: Task Analyzer v4.0 端到端測試 - 階段七測試驗證
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Task Analyzer v4.0 端到端測試 - 測試 L1-L5 完整流程"""

import pytest
from unittest.mock import AsyncMock, patch

from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import TaskAnalysisRequest, TaskType


@pytest.mark.e2e
@pytest.mark.asyncio
class TestTaskAnalyzerV4E2E:
    """Task Analyzer v4.0 端到端測試類"""

    @pytest.fixture
    def task_analyzer(self):
        """創建 TaskAnalyzer 實例"""
        return TaskAnalyzer()

    @pytest.mark.asyncio
    async def test_l1_to_l5_complete_flow_document_editing(
        self, task_analyzer, sample_document_editing_task, mock_router_llm, mock_orchestrator
    ):
        """測試 L1-L5 完整流程：文檔編輯任務"""
        request = TaskAnalysisRequest(**sample_document_editing_task)

        with patch.object(task_analyzer.router_llm, "route_v4", new=mock_router_llm.route_v4):
            with patch.object(task_analyzer, "_execute_task_dag", new=mock_orchestrator.execute_task):
                result = await task_analyzer.analyze(request)

                assert result is not None
                assert result.task_id is not None
                assert result.task_type in [TaskType.EXECUTION, TaskType.COMPLEX]
                assert "semantic_understanding" in result.analysis_details

    @pytest.mark.asyncio
    async def test_l1_to_l5_complete_flow_simple_query(
        self, task_analyzer, sample_simple_query, mock_router_llm
    ):
        """測試 L1-L5 完整流程：簡單查詢任務"""
        request = TaskAnalysisRequest(**sample_simple_query)

        simple_semantic = AsyncMock(
            return_value={
                "topics": ["time", "query"],
                "entities": [],
                "action_signals": ["query"],
                "modality": "question",
                "certainty": 0.95,
            }
        )

        with patch.object(task_analyzer.router_llm, "route_v4", new=simple_semantic):
            result = await task_analyzer.analyze(request)

            assert result is not None
            assert result.task_id is not None
            assert result.task_type == TaskType.QUERY
            assert "semantic_understanding" in result.analysis_details

    @pytest.mark.asyncio
    async def test_l1_fallback_on_error(self, task_analyzer, sample_task_request):
        """測試 L1 層級錯誤處理和 Fallback"""
        request = TaskAnalysisRequest(**sample_task_request)

        async def failing_route_v4(*args, **kwargs):
            raise Exception("Router LLM failed")

        with patch.object(task_analyzer.router_llm, "route_v4", new=failing_route_v4):
            result = await task_analyzer.analyze(request)

            assert result is not None
            assert result.task_id is not None

    @pytest.mark.asyncio
    async def test_l2_fallback_intent_on_no_match(
        self, task_analyzer, sample_general_query_task, mock_router_llm
    ):
        """測試 L2 層級 Fallback Intent 機制"""
        request = TaskAnalysisRequest(**sample_general_query_task)

        general_semantic = AsyncMock(
            return_value={
                "topics": ["general"],
                "entities": [],
                "action_signals": ["query"],
                "modality": "question",
                "certainty": 0.5,
            }
        )

        with patch.object(task_analyzer.router_llm, "route_v4", new=general_semantic):
            result = await task_analyzer.analyze(request)

            assert result is not None
            assert result.task_id is not None

    @pytest.mark.asyncio
    async def test_l4_policy_rejection(
        self, task_analyzer, sample_high_risk_task, mock_router_llm, mock_security_agent_denied
    ):
        """測試 L4 層級策略拒絕"""
        request = TaskAnalysisRequest(**sample_high_risk_task)

        high_risk_semantic = AsyncMock(
            return_value={
                "topics": ["data", "deletion"],
                "entities": ["user_data", "database"],
                "action_signals": ["delete", "clear"],
                "modality": "command",
                "certainty": 0.95,
            }
        )

        with patch.object(task_analyzer.router_llm, "route_v4", new=high_risk_semantic):
            with patch.object(
                task_analyzer.policy_service, "validate", new=mock_security_agent_denied.check_permission
            ):
                result = await task_analyzer.analyze(request)

                assert result is not None
                assert result.task_id is not None
                assert "policy_validation" in result.analysis_details
