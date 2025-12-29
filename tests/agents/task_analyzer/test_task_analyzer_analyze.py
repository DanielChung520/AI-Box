# 代碼功能說明: Task Analyzer analyze() 方法完整流程測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Task Analyzer analyze() 方法完整流程測試"""

from unittest.mock import AsyncMock, Mock

import pytest

from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import (
    ConfigIntent,
    LLMProvider,
    LLMRoutingResult,
    LogQueryIntent,
    TaskAnalysisRequest,
    TaskClassificationResult,
    TaskType,
    WorkflowSelectionResult,
    WorkflowType,
)


class TestTaskAnalyzerAnalyze:
    """Task Analyzer analyze() 方法測試類"""

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
            reasoning="這是查詢任務",
        )

    @pytest.fixture
    def mock_workflow_selection(self):
        """模擬工作流選擇結果"""
        return WorkflowSelectionResult(
            workflow_type=WorkflowType.LANGCHAIN,
            confidence=0.85,
            reasoning="適合使用 LangChain 工作流",
            config={},
        )

    @pytest.fixture
    def mock_llm_routing(self):
        """模擬 LLM 路由結果"""
        return LLMRoutingResult(
            provider=LLMProvider.CHATGPT,
            model="gpt-4",
            confidence=0.9,
            reasoning="使用 ChatGPT",
            fallback_providers=[],
        )

    @pytest.mark.asyncio
    async def test_analyze_config_operation_complete_flow(
        self, task_analyzer, mock_classification, mock_workflow_selection, mock_llm_routing
    ):
        """測試 analyze() 方法：配置操作的完整流程"""
        request = TaskAnalysisRequest(
            task="查詢系統配置",
            context={"user_id": "user_123"},
        )

        # Mock 分類器、工作流選擇器、LLM 路由器
        task_analyzer.classifier.classify = Mock(return_value=mock_classification)
        task_analyzer.workflow_selector.select = Mock(return_value=mock_workflow_selection)
        task_analyzer.llm_router.route = Mock(return_value=mock_llm_routing)

        # Mock _is_config_operation 返回 True
        task_analyzer._is_config_operation = Mock(return_value=True)

        # Mock _extract_config_intent
        mock_intent = ConfigIntent(
            action="query",
            scope="genai.policy",
            level="system",
            original_instruction="查詢系統配置",
        )
        task_analyzer._extract_config_intent = AsyncMock(return_value=mock_intent)

        # Mock _should_use_agent
        task_analyzer._should_use_agent = Mock(return_value=True)

        result = await task_analyzer.analyze(request)

        assert result.task_type == TaskType.QUERY
        assert result.workflow_type == WorkflowType.LANGCHAIN
        assert result.llm_provider == LLMProvider.CHATGPT
        assert result.requires_agent is True
        assert "system_config_agent" in result.suggested_agents
        assert "intent" in result.analysis_details

    @pytest.mark.asyncio
    async def test_analyze_log_query_complete_flow(
        self, task_analyzer, mock_workflow_selection, mock_llm_routing
    ):
        """測試 analyze() 方法：日誌查詢的完整流程"""
        request = TaskAnalysisRequest(
            task="查詢審計日誌",
            context={"user_id": "user_123"},
        )

        # Mock 分類結果為日誌查詢
        log_classification = TaskClassificationResult(
            task_type=TaskType.LOG_QUERY,
            confidence=0.95,
            reasoning="這是日誌查詢任務",
        )

        task_analyzer.classifier.classify = Mock(return_value=log_classification)
        task_analyzer.workflow_selector.select = Mock(return_value=mock_workflow_selection)
        task_analyzer.llm_router.route = Mock(return_value=mock_llm_routing)

        # Mock _extract_log_query_intent
        mock_intent = LogQueryIntent(log_type="AUDIT", actor="user_123", limit=10)
        task_analyzer._extract_log_query_intent = Mock(return_value=mock_intent)

        result = await task_analyzer.analyze(request)

        assert result.task_type == TaskType.LOG_QUERY
        assert result.requires_agent is False
        assert result.suggested_agents == []
        assert "intent" in result.analysis_details

    @pytest.mark.asyncio
    async def test_analyze_other_task_type(
        self, task_analyzer, mock_workflow_selection, mock_llm_routing
    ):
        """測試 analyze() 方法：其他任務類型"""
        request = TaskAnalysisRequest(
            task="執行文件處理",
            context={"user_id": "user_123"},
        )

        # Mock 分類結果為執行任務
        exec_classification = TaskClassificationResult(
            task_type=TaskType.EXECUTION,
            confidence=0.9,
            reasoning="這是執行任務",
        )

        task_analyzer.classifier.classify = Mock(return_value=exec_classification)
        task_analyzer.workflow_selector.select = Mock(return_value=mock_workflow_selection)
        task_analyzer.llm_router.route = Mock(return_value=mock_llm_routing)

        # Mock _is_config_operation 返回 False
        task_analyzer._is_config_operation = Mock(return_value=False)

        # Mock _should_use_agent
        task_analyzer._should_use_agent = Mock(return_value=True)

        # Mock _suggest_agents
        task_analyzer._suggest_agents = Mock(return_value=["execution_agent"])

        result = await task_analyzer.analyze(request)

        assert result.task_type == TaskType.EXECUTION
        assert result.requires_agent is True
        assert "execution_agent" in result.suggested_agents

    @pytest.mark.asyncio
    async def test_analyze_hybrid_workflow(
        self, task_analyzer, mock_classification, mock_llm_routing
    ):
        """測試 analyze() 方法：混合工作流"""
        request = TaskAnalysisRequest(
            task="複雜任務",
            context={"user_id": "user_123"},
        )

        # Mock 混合工作流選擇結果
        from agents.task_analyzer.models import WorkflowStrategy

        hybrid_workflow = WorkflowSelectionResult(
            workflow_type=WorkflowType.HYBRID,
            confidence=0.9,
            reasoning="適合混合工作流",
            config={},
            strategy=WorkflowStrategy(
                mode="hybrid",
                primary=WorkflowType.LANGCHAIN,
                fallback=[],
                switch_conditions={},
                reasoning="並行執行",
            ),
        )

        task_analyzer.classifier.classify = Mock(return_value=mock_classification)
        task_analyzer.workflow_selector.select = Mock(return_value=hybrid_workflow)
        task_analyzer.llm_router.route = Mock(return_value=mock_llm_routing)

        task_analyzer._is_config_operation = Mock(return_value=False)
        task_analyzer._should_use_agent = Mock(return_value=True)
        task_analyzer._suggest_agents = Mock(return_value=["execution_agent"])

        result = await task_analyzer.analyze(request)

        assert result.workflow_type == WorkflowType.HYBRID
        assert "workflow_strategy" in result.analysis_details

    def test_should_use_agent_complex_task(self, task_analyzer):
        """測試 _should_use_agent() 方法：複雜任務"""
        result = task_analyzer._should_use_agent(TaskType.COMPLEX, "複雜任務")
        assert result is True

    def test_should_use_agent_planning_task(self, task_analyzer):
        """測試 _should_use_agent() 方法：規劃任務"""
        result = task_analyzer._should_use_agent(TaskType.PLANNING, "規劃任務")
        assert result is True

    def test_should_use_agent_execution_task(self, task_analyzer):
        """測試 _should_use_agent() 方法：執行任務"""
        result = task_analyzer._should_use_agent(TaskType.EXECUTION, "執行任務")
        assert result is True

    def test_should_use_agent_query_task_simple(self, task_analyzer):
        """測試 _should_use_agent() 方法：簡單查詢任務"""
        result = task_analyzer._should_use_agent(TaskType.QUERY, "查詢用戶信息")
        assert result is False

    def test_should_use_agent_query_task_complex(self, task_analyzer):
        """測試 _should_use_agent() 方法：複雜查詢任務"""
        result = task_analyzer._should_use_agent(TaskType.QUERY, "執行多步驟查詢和綜合分析")
        assert result is True

    def test_should_use_agent_review_task(self, task_analyzer):
        """測試 _should_use_agent() 方法：審查任務"""
        result = task_analyzer._should_use_agent(TaskType.REVIEW, "審查代碼")
        assert result is True

    def test_suggest_agents_planning(self, task_analyzer):
        """測試 _suggest_agents() 方法：規劃任務"""
        agents = task_analyzer._suggest_agents(TaskType.PLANNING, WorkflowType.LANGCHAIN)
        assert "planning_agent" in agents

    def test_suggest_agents_execution(self, task_analyzer):
        """測試 _suggest_agents() 方法：執行任務"""
        agents = task_analyzer._suggest_agents(TaskType.EXECUTION, WorkflowType.LANGCHAIN)
        assert "execution_agent" in agents

    def test_suggest_agents_review(self, task_analyzer):
        """測試 _suggest_agents() 方法：審查任務"""
        agents = task_analyzer._suggest_agents(TaskType.REVIEW, WorkflowType.LANGCHAIN)
        assert "review_agent" in agents

    def test_suggest_agents_complex(self, task_analyzer):
        """測試 _suggest_agents() 方法：複雜任務"""
        agents = task_analyzer._suggest_agents(TaskType.COMPLEX, WorkflowType.LANGCHAIN)
        assert "planning_agent" in agents
        assert "execution_agent" in agents
        assert "review_agent" in agents

    def test_extract_log_query_intent_audit(self, task_analyzer):
        """測試 _extract_log_query_intent() 方法：審計日誌查詢"""
        intent = task_analyzer._extract_log_query_intent("查詢審計日誌", {"user_id": "user_123"})
        assert isinstance(intent, LogQueryIntent)
        assert intent.log_type == "AUDIT"

    def test_extract_log_query_intent_security(self, task_analyzer):
        """測試 _extract_log_query_intent() 方法：安全日誌查詢"""
        intent = task_analyzer._extract_log_query_intent("查詢安全日誌", {"user_id": "user_123"})
        assert isinstance(intent, LogQueryIntent)
        assert intent.log_type == "SECURITY"

    def test_extract_log_query_intent_task(self, task_analyzer):
        """測試 _extract_log_query_intent() 方法：任務日誌查詢"""
        intent = task_analyzer._extract_log_query_intent("查詢任務日誌", {"user_id": "user_123"})
        assert isinstance(intent, LogQueryIntent)
        assert intent.log_type == "TASK"

    def test_extract_log_query_intent_with_trace_id(self, task_analyzer):
        """測試 _extract_log_query_intent() 方法：使用 trace_id"""
        # 測試 trace_id 在 context 中的情況
        intent = task_analyzer._extract_log_query_intent(
            "查詢日誌", {"user_id": "user_123", "trace_id": "trace_123"}
        )
        assert isinstance(intent, LogQueryIntent)
        assert intent.trace_id == "trace_123"
