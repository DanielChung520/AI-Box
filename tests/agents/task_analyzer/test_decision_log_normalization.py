# 代碼功能說明: Decision Log 規範化測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Decision Log 規範化測試 - 測試 GRO 規範 DecisionLog 模型和向後兼容性"""

from datetime import datetime

import pytest

from agents.task_analyzer.models import (
    DecisionAction,
    DecisionLog,
    DecisionOutcome,
    DecisionResult,
    GroDecision,
    GroDecisionLog,
    ReactStateType,
    RouterDecision,
)


class TestGroDecisionLog:
    """測試 GRO 規範 DecisionLog 模型"""

    def test_gro_decision_log_creation(self):
        """測試創建 GRO DecisionLog"""
        decision = GroDecision(
            action=DecisionAction.COMPLETE,
            reason="Task completed successfully",
            next_state=ReactStateType.DECISION,
        )

        decision_log = GroDecisionLog(
            react_id="test-react-123",
            iteration=0,
            state=ReactStateType.DECISION,
            input_signature={
                "command_type": "TASK",
                "scope": "multi_step",
                "risk_level": "safe",
            },
            decision=decision,
            outcome=DecisionOutcome.SUCCESS,
            timestamp=datetime.utcnow(),
        )

        assert decision_log.react_id == "test-react-123"
        assert decision_log.iteration == 0
        assert decision_log.state == ReactStateType.DECISION
        assert decision_log.outcome == DecisionOutcome.SUCCESS
        assert decision_log.decision.action == DecisionAction.COMPLETE

    def test_gro_decision_log_to_dict(self):
        """測試 GRO DecisionLog 轉換為字典"""
        decision = GroDecision(
            action=DecisionAction.RETRY,
            reason="Timeout, retrying",
            next_state=ReactStateType.DELEGATION,
        )

        decision_log = GroDecisionLog(
            react_id="test-react-456",
            iteration=1,
            state=ReactStateType.DECISION,
            input_signature={"command_type": "TASK"},
            decision=decision,
            outcome=DecisionOutcome.PARTIAL,
        )

        result = decision_log.to_dict()

        assert result["react_id"] == "test-react-456"
        assert result["iteration"] == 1
        assert result["state"] == "DECISION"
        assert result["outcome"] == "partial"
        assert result["decision"]["action"] == "retry"
        assert result["decision"]["next_state"] == "DELEGATION"

    def test_gro_decision_log_from_dict(self):
        """測試從字典創建 GRO DecisionLog"""
        data = {
            "react_id": "test-react-789",
            "iteration": 2,
            "state": "DECISION",
            "input_signature": {"command_type": "TASK"},
            "observations": {"success_rate": 0.8},
            "decision": {
                "action": "extend_plan",
                "reason": "Need more steps",
                "next_state": "PLANNING",
            },
            "outcome": "partial",
            "timestamp": "2026-01-08T12:00:00Z",
        }

        decision_log = GroDecisionLog.from_dict(data)

        assert decision_log.react_id == "test-react-789"
        assert decision_log.iteration == 2
        assert decision_log.state == ReactStateType.DECISION
        assert decision_log.outcome == DecisionOutcome.PARTIAL
        assert decision_log.decision.action == DecisionAction.EXTEND_PLAN


class TestBackwardCompatibility:
    """測試向後兼容性"""

    def test_from_legacy_decision_log(self):
        """測試從舊版 DecisionLog 轉換為 GroDecisionLog"""
        # 創建舊版 DecisionLog
        router_output = RouterDecision(
            intent_type="execution",
            complexity="mid",
            needs_agent=True,
            needs_tools=False,
            determinism_required=True,
            risk_level="low",
            confidence=0.8,
        )

        decision_result = DecisionResult(
            router_result=router_output,
            chosen_agent="execution_agent",
            chosen_tools=[],
            chosen_model="gpt-4",
            score=0.9,
            fallback_used=False,
            reasoning="Agent selected based on capability match",
        )

        legacy_log = DecisionLog(
            decision_id="legacy-decision-123",
            timestamp=datetime.utcnow(),
            query={"text": "Execute task"},
            router_output=router_output,
            decision_engine=decision_result,
            execution_result={"success": True, "latency_ms": 100},
        )

        # 轉換為 GroDecisionLog
        gro_log = GroDecisionLog.from_legacy_decision_log(
            legacy_log, react_id="test-react-999", iteration=0
        )

        assert gro_log.react_id == "test-react-999"
        assert gro_log.iteration == 0
        assert gro_log.state == ReactStateType.DECISION
        assert gro_log.outcome == DecisionOutcome.SUCCESS
        assert gro_log.input_signature["intent_type"] == "execution"
        assert gro_log.metadata["chosen_agent"] == "execution_agent"
        assert gro_log.metadata["legacy_decision_id"] == "legacy-decision-123"

    def test_legacy_decision_log_failure_outcome(self):
        """測試舊版 DecisionLog 失敗情況的轉換"""
        router_output = RouterDecision(
            intent_type="execution",
            complexity="high",
            needs_agent=True,
            needs_tools=True,
            determinism_required=False,
            risk_level="high",
            confidence=0.6,
        )

        decision_result = DecisionResult(
            router_result=router_output,
            chosen_agent="execution_agent",
            chosen_tools=["tool1"],
            chosen_model="gpt-4",
            score=0.7,
            fallback_used=True,
            reasoning="Fallback used due to low confidence",
        )

        legacy_log = DecisionLog(
            decision_id="legacy-decision-fail",
            timestamp=datetime.utcnow(),
            query={"text": "Execute complex task"},
            router_output=router_output,
            decision_engine=decision_result,
            execution_result={"success": False, "latency_ms": 500, "error": "Timeout"},
        )

        gro_log = GroDecisionLog.from_legacy_decision_log(
            legacy_log, react_id="test-react-fail", iteration=0
        )

        assert gro_log.outcome == DecisionOutcome.FAILURE
        assert gro_log.metadata["execution_result"]["success"] is False


class TestRoutingMemoryIntegration:
    """測試 Routing Memory 集成"""

    @pytest.mark.asyncio
    async def test_record_gro_decision_log(self):
        """測試記錄 GRO DecisionLog 到 Routing Memory"""
        from agents.task_analyzer.routing_memory.memory_service import RoutingMemoryService

        service = RoutingMemoryService()

        decision = GroDecision(
            action=DecisionAction.COMPLETE,
            reason="Task completed",
            next_state=ReactStateType.DECISION,
        )

        gro_log = GroDecisionLog(
            react_id="test-react-memory",
            iteration=0,
            state=ReactStateType.DECISION,
            input_signature={"command_type": "TASK"},
            decision=decision,
            outcome=DecisionOutcome.SUCCESS,
        )

        # 記錄決策（異步，不等待完成）
        result = await service.record_decision(gro_log)
        assert result is True

    @pytest.mark.asyncio
    async def test_record_legacy_decision_log(self):
        """測試記錄舊版 DecisionLog 到 Routing Memory（向後兼容）"""
        from agents.task_analyzer.routing_memory.memory_service import RoutingMemoryService

        service = RoutingMemoryService()

        router_output = RouterDecision(
            intent_type="query",
            complexity="low",
            needs_agent=False,
            needs_tools=False,
            determinism_required=True,
            risk_level="low",
            confidence=0.9,
        )

        decision_result = DecisionResult(
            router_result=router_output,
            chosen_agent=None,
            chosen_tools=[],
            chosen_model="gpt-4",
            score=0.95,
            fallback_used=False,
            reasoning="Simple query, no agent needed",
        )

        legacy_log = DecisionLog(
            decision_id="legacy-memory-test",
            timestamp=datetime.utcnow(),
            query={"text": "Simple query"},
            router_output=router_output,
            decision_engine=decision_result,
            execution_result={"success": True},
        )

        # 記錄決策（需要提供 react_id 和 iteration）
        result = await service.record_decision(
            legacy_log, react_id="test-react-legacy", iteration=0
        )
        assert result is True
