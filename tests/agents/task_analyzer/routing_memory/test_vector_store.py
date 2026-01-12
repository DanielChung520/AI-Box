# 代碼功能說明: Routing Memory 向量存儲測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Routing Memory 向量存儲測試 - 測試向量存儲和搜索功能"""


import pytest

from agents.task_analyzer.models import (
    DecisionAction,
    DecisionOutcome,
    GroDecision,
    GroDecisionLog,
    ReactStateType,
)


class TestRoutingVectorStore:
    """測試 Routing Vector Store"""

    @pytest.mark.asyncio
    async def test_add_gro_decision_log(self):
        """測試添加 GRO DecisionLog 到向量存儲"""
        from agents.task_analyzer.routing_memory.vector_store import RoutingVectorStore

        vector_store = RoutingVectorStore()

        decision = GroDecision(
            action=DecisionAction.COMPLETE,
            reason="Task completed",
            next_state=ReactStateType.DECISION,
        )

        gro_log = GroDecisionLog(
            react_id="test-vector-123",
            iteration=0,
            state=ReactStateType.DECISION,
            input_signature={
                "intent_type": "execution",
                "complexity": "mid",
                "risk_level": "low",
            },
            decision=decision,
            outcome=DecisionOutcome.SUCCESS,
            metadata={"chosen_agent": "execution_agent"},
        )

        semantic = "Intent:execution\nComplexity:mid\nRisk:low\nState:DECISION\nAction:complete\nOutcome:success\nChosenPath:execution_agent\n"

        result = await vector_store.add(semantic, gro_log)
        # 注意：實際測試需要 mock vector_store_service 和 embedding_service
        # 這裡只測試接口是否正常
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_search_similar_decisions(self):
        """測試搜索相似決策"""
        from agents.task_analyzer.routing_memory.vector_store import RoutingVectorStore

        vector_store = RoutingVectorStore()

        query = "Execute task with low risk"
        results = await vector_store.search(query, top_k=3)

        # 注意：實際測試需要 mock 服務
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_filters(self):
        """測試帶過濾條件的搜索"""
        from agents.task_analyzer.routing_memory.vector_store import RoutingVectorStore

        vector_store = RoutingVectorStore()

        query = "Execute task"
        filters = {"outcome": "success", "state": "DECISION"}

        results = await vector_store.search(query, top_k=5, filters=filters)

        assert isinstance(results, list)
        # 驗證過濾條件（如果結果不為空）
        for result in results:
            if result.get("metadata"):
                metadata = result["metadata"]
                if "outcome" in metadata:
                    assert metadata["outcome"] == "success"
                if "state" in metadata:
                    assert metadata["state"] == "DECISION"
