# 代碼功能說明: P-T-A-O 迴圈核心邏輯測試
# 創建日期: 2026-03-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-10

from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest

from agents.services.protocol.base import AgentServiceRequest
from mm_agent.models import Responsibility, SemanticAnalysisResult
from mm_agent.ptao.loop import PTAOLoop
from mm_agent.ptao.responsibility_registry import ResponsibilityRegistry


@pytest.fixture
def registry() -> ResponsibilityRegistry:
    return ResponsibilityRegistry()


@pytest.fixture
def loop(registry: ResponsibilityRegistry) -> PTAOLoop:
    return PTAOLoop(registry=registry)


@pytest.fixture
def sample_request() -> AgentServiceRequest:
    return AgentServiceRequest(
        task_id="task-001",
        task_type="inventory_query",
        task_data={"instruction": "查詢 A-100 庫存"},
        metadata={"session_id": "s-1", "user_id": "u-1"},
    )


@pytest.fixture
def simple_semantic_result() -> SemanticAnalysisResult:
    return SemanticAnalysisResult(
        intent="query_stock",
        confidence=0.95,
        parameters={"part_no": "A-100"},
        original_instruction="查詢 A-100 庫存",
        clarification_needed=False,
        clarification_questions=[],
        responsibility_type="query_stock",
    )


@pytest.fixture
def complex_semantic_result() -> SemanticAnalysisResult:
    return SemanticAnalysisResult(
        intent="analyze_shortage",
        confidence=0.87,
        parameters={"part_no": "B-200", "required_qty": 100},
        original_instruction="分析 B-200 是否缺料並計算採購量",
        clarification_needed=False,
        clarification_questions=[],
        responsibility_type="analyze_shortage",
    )


class TestPTAOLoopPlan:
    @pytest.mark.asyncio
    async def test_plan_simple_when_single_step(
        self,
        loop: PTAOLoop,
        registry: ResponsibilityRegistry,
        sample_request: AgentServiceRequest,
        simple_semantic_result: SemanticAnalysisResult,
    ) -> None:
        async def handler(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {"success": True, "data": {"part_no": "A-100"}}

        registry.register("query_stock", handler)
        responsibility = Responsibility(
            type="query_stock",
            description="查詢庫存",
            steps=["查詢單一庫存"],
        )

        result = await loop.run(
            responsibility=responsibility,
            semantic_result=simple_semantic_result,
            request=sample_request,
            user_instruction="查詢 A-100 庫存",
        )

        assert result.thought.complexity == "simple"

    @pytest.mark.asyncio
    async def test_plan_complex_when_multiple_steps(
        self,
        loop: PTAOLoop,
        registry: ResponsibilityRegistry,
        sample_request: AgentServiceRequest,
        simple_semantic_result: SemanticAnalysisResult,
    ) -> None:
        async def handler(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {"success": True, "data": {"ok": True}}

        registry.register("query_stock", handler)
        responsibility = Responsibility(
            type="query_stock",
            description="查詢庫存",
            steps=["查詢庫存", "彙總結果"],
        )

        result = await loop.run(
            responsibility=responsibility,
            semantic_result=simple_semantic_result,
            request=sample_request,
            user_instruction="查詢 A-100 庫存並彙整",
        )

        assert result.thought.complexity == "complex"

    @pytest.mark.asyncio
    async def test_plan_complex_when_type_is_analyze_shortage(
        self,
        loop: PTAOLoop,
        registry: ResponsibilityRegistry,
        sample_request: AgentServiceRequest,
        complex_semantic_result: SemanticAnalysisResult,
    ) -> None:
        async def handler(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {"success": True, "data": {"shortage": 20}}

        registry.register("analyze_shortage", handler)
        responsibility = Responsibility(
            type="analyze_shortage",
            description="分析缺料",
            steps=["分析缺料"],
        )

        result = await loop.run(
            responsibility=responsibility,
            semantic_result=complex_semantic_result,
            request=sample_request,
            user_instruction="分析 B-200 缺料",
        )

        assert result.thought.complexity == "complex"

    @pytest.mark.asyncio
    async def test_plan_complex_when_type_is_generate_purchase_order(
        self,
        loop: PTAOLoop,
        registry: ResponsibilityRegistry,
        sample_request: AgentServiceRequest,
        simple_semantic_result: SemanticAnalysisResult,
    ) -> None:
        async def handler(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {"success": True, "data": {"po_id": "PO-1"}}

        registry.register("generate_purchase_order", handler)
        responsibility = Responsibility(
            type="generate_purchase_order",
            description="生成採購單",
            steps=["生成採購單"],
        )

        result = await loop.run(
            responsibility=responsibility,
            semantic_result=simple_semantic_result,
            request=sample_request,
            user_instruction="建立採購單",
        )

        assert result.thought.complexity == "complex"


class TestPTAOLoopThink:
    @pytest.mark.asyncio
    async def test_think_reasoning_is_traditional_chinese(
        self,
        loop: PTAOLoop,
        registry: ResponsibilityRegistry,
        sample_request: AgentServiceRequest,
        simple_semantic_result: SemanticAnalysisResult,
    ) -> None:
        async def handler(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {"success": True, "data": {"ok": True}}

        registry.register("query_stock", handler)
        responsibility = Responsibility(
            type="query_stock",
            description="查詢庫存",
            steps=["查詢單一步驟"],
        )

        result = await loop.run(
            responsibility=responsibility,
            semantic_result=simple_semantic_result,
            request=sample_request,
            user_instruction="查詢 A-100 庫存",
        )

        assert "規則" in result.thought.reasoning
        assert "參數" in result.thought.reasoning

    @pytest.mark.asyncio
    async def test_think_includes_intent_summary(
        self,
        loop: PTAOLoop,
        registry: ResponsibilityRegistry,
        sample_request: AgentServiceRequest,
        simple_semantic_result: SemanticAnalysisResult,
    ) -> None:
        async def handler(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {"success": True, "data": {"ok": True}}

        registry.register("query_stock", handler)
        responsibility = Responsibility(
            type="query_stock",
            description="查詢庫存",
            steps=["查詢"],
        )

        result = await loop.run(
            responsibility=responsibility,
            semantic_result=simple_semantic_result,
            request=sample_request,
            user_instruction="查詢 A-100 庫存",
        )

        assert "query_stock" in result.thought.intent_summary

    @pytest.mark.asyncio
    async def test_think_marks_parameter_insufficient_when_empty(
        self,
        loop: PTAOLoop,
        registry: ResponsibilityRegistry,
        sample_request: AgentServiceRequest,
    ) -> None:
        semantic_result = SemanticAnalysisResult(
            intent="query_part",
            confidence=0.61,
            parameters={},
            original_instruction="查詢料號資訊",
            clarification_needed=False,
            clarification_questions=[],
            responsibility_type="query_part",
        )

        async def handler(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {"success": True, "data": {"ok": True}}

        registry.register("query_part", handler)
        responsibility = Responsibility(
            type="query_part",
            description="查詢料號",
            steps=["查詢"],
        )

        result = await loop.run(
            responsibility=responsibility,
            semantic_result=semantic_result,
            request=sample_request,
            user_instruction="查詢料號資訊",
        )

        assert "不足" in result.thought.reasoning


class TestPTAOLoopActAndObserve:
    @pytest.mark.asyncio
    async def test_act_calls_handler_with_required_signature(
        self,
        loop: PTAOLoop,
        registry: ResponsibilityRegistry,
        sample_request: AgentServiceRequest,
        simple_semantic_result: SemanticAnalysisResult,
    ) -> None:
        mock_handler = AsyncMock(return_value={"success": True, "data": {"qty": 50}})
        registry.register("query_stock", mock_handler)

        responsibility = Responsibility(
            type="query_stock",
            description="查詢庫存",
            steps=["查詢"],
        )

        await loop.run(
            responsibility=responsibility,
            semantic_result=simple_semantic_result,
            request=sample_request,
            user_instruction="查詢 A-100 庫存",
        )

        mock_handler.assert_awaited_once_with(
            responsibility,
            simple_semantic_result,
            sample_request,
            "查詢 A-100 庫存",
        )

    @pytest.mark.asyncio
    async def test_observe_success_true_when_handler_success(
        self,
        loop: PTAOLoop,
        registry: ResponsibilityRegistry,
        sample_request: AgentServiceRequest,
        simple_semantic_result: SemanticAnalysisResult,
    ) -> None:
        async def handler(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {"success": True, "data": {"qty": 50}}

        registry.register("query_stock", handler)
        responsibility = Responsibility(
            type="query_stock",
            description="查詢庫存",
            steps=["查詢"],
        )

        result = await loop.run(
            responsibility=responsibility,
            semantic_result=simple_semantic_result,
            request=sample_request,
            user_instruction="查詢 A-100 庫存",
        )

        assert result.observation.success is True
        assert result.observation.data == {"success": True, "data": {"qty": 50}}
        assert result.raw_result == {"success": True, "data": {"qty": 50}}

    @pytest.mark.asyncio
    async def test_observe_records_duration_ms(
        self,
        loop: PTAOLoop,
        registry: ResponsibilityRegistry,
        sample_request: AgentServiceRequest,
        simple_semantic_result: SemanticAnalysisResult,
    ) -> None:
        async def handler(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {"success": True, "data": {"qty": 50}}

        registry.register("query_stock", handler)
        responsibility = Responsibility(
            type="query_stock",
            description="查詢庫存",
            steps=["查詢"],
        )

        result = await loop.run(
            responsibility=responsibility,
            semantic_result=simple_semantic_result,
            request=sample_request,
            user_instruction="查詢 A-100 庫存",
        )

        assert result.observation.duration_ms >= 0.0

    @pytest.mark.asyncio
    async def test_handler_failure_sets_observation_failed(
        self,
        loop: PTAOLoop,
        registry: ResponsibilityRegistry,
        sample_request: AgentServiceRequest,
        simple_semantic_result: SemanticAnalysisResult,
    ) -> None:
        async def handler(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            raise RuntimeError("服務不可用")

        registry.register("query_stock", handler)
        responsibility = Responsibility(
            type="query_stock",
            description="查詢庫存",
            steps=["查詢"],
        )

        result = await loop.run(
            responsibility=responsibility,
            semantic_result=simple_semantic_result,
            request=sample_request,
            user_instruction="查詢 A-100 庫存",
        )

        assert result.observation.success is False
        assert result.observation.error == "服務不可用"
        assert result.raw_result == {}

    @pytest.mark.asyncio
    async def test_unknown_responsibility_sets_observation_failed(
        self,
        loop: PTAOLoop,
        sample_request: AgentServiceRequest,
        simple_semantic_result: SemanticAnalysisResult,
    ) -> None:
        responsibility = Responsibility(
            type="unknown_type",
            description="未知職責",
            steps=["嘗試執行"],
        )

        result = await loop.run(
            responsibility=responsibility,
            semantic_result=simple_semantic_result,
            request=sample_request,
            user_instruction="做一些未知事情",
        )

        assert result.observation.success is False
        assert result.observation.error == "未知的職責類型: unknown_type"

    @pytest.mark.asyncio
    async def test_decision_log_has_four_phases(
        self,
        loop: PTAOLoop,
        registry: ResponsibilityRegistry,
        sample_request: AgentServiceRequest,
        simple_semantic_result: SemanticAnalysisResult,
    ) -> None:
        async def handler(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {"success": True, "data": {"qty": 99}}

        registry.register("query_stock", handler)
        responsibility = Responsibility(
            type="query_stock",
            description="查詢庫存",
            steps=["查詢"],
        )

        result = await loop.run(
            responsibility=responsibility,
            semantic_result=simple_semantic_result,
            request=sample_request,
            user_instruction="查詢 A-100 庫存",
        )

        phases = [entry.phase for entry in result.decision_log.entries]
        assert len(result.decision_log.entries) >= 4
        assert phases[:4] == ["plan", "think", "act", "observe"]

    @pytest.mark.asyncio
    async def test_returns_ptao_result_complete_fields(
        self,
        loop: PTAOLoop,
        registry: ResponsibilityRegistry,
        sample_request: AgentServiceRequest,
        simple_semantic_result: SemanticAnalysisResult,
    ) -> None:
        async def handler(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {"success": True, "data": {"qty": 99}}

        registry.register("query_stock", handler)
        responsibility = Responsibility(
            type="query_stock",
            description="查詢庫存",
            steps=["查詢"],
        )

        result = await loop.run(
            responsibility=responsibility,
            semantic_result=simple_semantic_result,
            request=sample_request,
            user_instruction="查詢 A-100 庫存",
        )

        assert result.thought is not None
        assert result.observation is not None
        assert result.decision_log is not None
        assert result.raw_result == {"success": True, "data": {"qty": 99}}
