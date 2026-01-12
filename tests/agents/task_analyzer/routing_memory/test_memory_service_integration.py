# 代碼功能說明: Routing Memory 服務集成測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Routing Memory 服務集成測試 - 測試完整的記憶存儲和檢索流程"""


import pytest

from agents.task_analyzer.models import (
    DecisionAction,
    DecisionOutcome,
    GroDecision,
    GroDecisionLog,
    ReactStateType,
)


class TestMemoryServiceIntegration:
    """測試 Routing Memory 服務集成"""

    @pytest.mark.asyncio
    async def test_complete_memory_flow(self):
        """測試完整的記憶存儲和檢索流程"""
        from agents.task_analyzer.routing_memory.memory_service import RoutingMemoryService

        service = RoutingMemoryService()

        # 1. 創建 GRO DecisionLog
        decision = GroDecision(
            action=DecisionAction.COMPLETE,
            reason="Task completed successfully",
            next_state=ReactStateType.DECISION,
        )

        gro_log = GroDecisionLog(
            react_id="test-integration-123",
            iteration=0,
            state=ReactStateType.DECISION,
            input_signature={
                "command_type": "TASK",
                "intent_type": "execution",
                "complexity": "mid",
                "risk_level": "low",
            },
            decision=decision,
            outcome=DecisionOutcome.SUCCESS,
            metadata={"chosen_agent": "execution_agent", "chosen_model": "gpt-4"},
        )

        # 2. 記錄決策
        result = await service.record_decision(gro_log)
        assert result is True

        # 3. 檢索相似決策（向量搜索）
        similar_decisions = await service.recall_similar_decisions(
            query="Execute task with low risk",
            top_k=3,
        )

        assert isinstance(similar_decisions, list)

        # 4. 使用 routing_key 查詢
        routing_key_results = await service.recall_similar_decisions(
            routing_key={
                "intent_type": "execution",
                "complexity": "mid",
                "risk_level": "low",
            },
            top_k=5,
        )

        assert isinstance(routing_key_results, list)

    @pytest.mark.asyncio
    async def test_memory_after_pruning(self):
        """測試記憶裁剪後的檢索準確性"""
        from agents.task_analyzer.routing_memory.memory_service import RoutingMemoryService
        from agents.task_analyzer.routing_memory.pruning import PruningService

        service = RoutingMemoryService()
        pruning_service = PruningService(ttl_days=90)

        # 1. 記錄一些決策
        for i in range(5):
            decision = GroDecision(
                action=DecisionAction.COMPLETE,
                reason=f"Task {i} completed",
                next_state=ReactStateType.DECISION,
            )

            gro_log = GroDecisionLog(
                react_id=f"test-pruning-{i}",
                iteration=0,
                state=ReactStateType.DECISION,
                input_signature={"command_type": "TASK", "intent_type": "execution"},
                decision=decision,
                outcome=DecisionOutcome.SUCCESS,
            )

            await service.record_decision(gro_log)

        # 2. 執行記憶裁剪
        stats = await pruning_service.prune_all()
        assert isinstance(stats, dict)

        # 3. 檢索決策（應該仍然能夠找到未清理的決策）
        results = await service.recall_similar_decisions(query="Execute task", top_k=3)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_gro_decision_log_end_to_end(self):
        """測試 GRO DecisionLog 的端到端流程"""
        from agents.task_analyzer.routing_memory.memory_service import RoutingMemoryService

        service = RoutingMemoryService()

        # 創建多個決策（模擬 ReAct 循環）
        react_id = "test-e2e-456"

        for iteration in range(3):
            decision = GroDecision(
                action=DecisionAction.COMPLETE if iteration == 2 else DecisionAction.RETRY,
                reason=f"Iteration {iteration}",
                next_state=ReactStateType.DECISION if iteration == 2 else ReactStateType.DELEGATION,
            )

            gro_log = GroDecisionLog(
                react_id=react_id,
                iteration=iteration,
                state=ReactStateType.DECISION,
                input_signature={"command_type": "TASK"},
                decision=decision,
                outcome=DecisionOutcome.SUCCESS if iteration == 2 else DecisionOutcome.PARTIAL,
            )

            await service.record_decision(gro_log)

        # 查詢特定 ReAct session 的所有決策
        results = await service.recall_similar_decisions(
            routing_key={"react_id": react_id}, top_k=10
        )

        assert isinstance(results, list)
        # 驗證所有結果都屬於同一個 react_id
        for result in results:
            if "react_id" in result:
                assert result["react_id"] == react_id
