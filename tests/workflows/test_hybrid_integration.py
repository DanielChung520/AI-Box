# 代碼功能說明: 混合模式整合測試
# 創建日期: 2025-11-26 23:45 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 23:45 (UTC+8)

"""測試混合模式的端到端整合流程。"""

import pytest
from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import TaskAnalysisRequest
from agents.workflows.base import WorkflowRequestContext
from agents.workflows.factory_router import get_workflow_factory_router
from agents.task_analyzer.models import WorkflowType


class TestHybridIntegration:
    """測試混合模式整合。"""

    def test_task_analyzer_hybrid_strategy(self):
        """測試 Task Analyzer 輸出混合策略。"""
        analyzer = TaskAnalyzer()

        request = TaskAnalysisRequest(
            task="這是一個複雜的多步驟任務，需要深入分析和長期規劃",
            context={
                "complexity_score": 75,
                "step_count": 15,
                "requires_observability": True,
                "requires_long_horizon": True,
            },
        )

        result = analyzer.analyze(request)

        # 應該選擇混合模式
        assert result.workflow_type == WorkflowType.HYBRID

        # 檢查分析詳情中包含 strategy
        assert "workflow_strategy" in result.analysis_details
        strategy = result.analysis_details["workflow_strategy"]
        assert strategy["mode"] == "hybrid"
        assert "primary" in strategy
        assert "fallback" in strategy

    def test_workflow_factory_router_hybrid(self):
        """測試工作流工廠路由器支援混合模式。"""
        router = get_workflow_factory_router()

        factory = router.get_factory(WorkflowType.HYBRID)
        assert factory is not None

        request_ctx = WorkflowRequestContext(
            task_id="test-task-1",
            task="測試任務",
            workflow_config={
                "primary_workflow": "autogen",
                "fallback_workflows": ["langgraph"],
            },
        )

        workflow = router.build_workflow(WorkflowType.HYBRID, request_ctx)
        assert workflow is not None

    @pytest.mark.asyncio
    async def test_hybrid_workflow_execution(self):
        """測試混合工作流執行（模擬）。"""
        from agents.workflows.hybrid_factory import HybridWorkflowFactory

        factory = HybridWorkflowFactory()

        request_ctx = WorkflowRequestContext(
            task_id="test-task-1",
            task="測試混合模式任務",
            context={"complexity_score": 80},
            workflow_config={
                "primary_workflow": "autogen",
                "fallback_workflows": ["langgraph"],
            },
        )

        workflow = factory.build_workflow(request_ctx)
        assert workflow is not None
        assert workflow._primary_mode == "autogen"
        assert workflow._fallback_modes == ["langgraph"]

    def test_decision_engine_high_complexity(self):
        """測試決策引擎對高複雜度任務的決策。"""
        from agents.task_analyzer.decision_engine import DecisionEngine
        from agents.task_analyzer.models import TaskClassificationResult, TaskType

        engine = DecisionEngine()

        classification = TaskClassificationResult(
            task_type=TaskType.COMPLEX,
            confidence=0.9,
            reasoning="高複雜度任務",
        )

        context = {
            "complexity_score": 85,
            "step_count": 12,
        }

        strategy = engine.decide_strategy(classification, context)

        assert strategy.mode == "hybrid"
        assert strategy.primary.value == "autogen"
        assert len(strategy.fallback) > 0

    def test_switch_conditions(self):
        """測試切換條件配置。"""
        from agents.task_analyzer.decision_engine import DecisionEngine
        from agents.task_analyzer.models import TaskClassificationResult, TaskType

        engine = DecisionEngine()

        classification = TaskClassificationResult(
            task_type=TaskType.COMPLEX,
            confidence=0.9,
            reasoning="測試任務",
        )

        context = {"complexity_score": 75}

        strategy = engine.decide_strategy(classification, context)

        assert "switch_conditions" in strategy.switch_conditions
        assert "error_rate_threshold" in strategy.switch_conditions
        assert "cost_threshold" in strategy.switch_conditions
        assert "cooldown_seconds" in strategy.switch_conditions
