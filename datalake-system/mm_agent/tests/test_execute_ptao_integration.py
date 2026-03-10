# 代碼功能說明: execute() 整合 PTAO 迴圈測試
# 創建日期: 2026-03-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-10

"""驗證 MMAgent.execute() 透過 PTAOLoop 回傳 metadata 與狀態。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.services.protocol.base import AgentServiceRequest
from mm_agent.agent import MMAgent


@pytest.fixture
def agent() -> MMAgent:
    mock_services = {
        "orchestrator_client": MagicMock(),
        "semantic_analyzer": MagicMock(),
        "responsibility_analyzer": MagicMock(),
        "context_manager": MagicMock(),
        "part_service": MagicMock(),
        "stock_service": MagicMock(),
        "shortage_analyzer": MagicMock(),
        "purchase_service": MagicMock(),
        "result_validator": MagicMock(),
        "data_validator": MagicMock(),
    }
    with patch("data_agent.structured_query_handler.StructuredQueryHandler"):
        instance = MMAgent(**mock_services)

    instance._context_manager.get_context = AsyncMock(
        return_value=SimpleNamespace(last_result=None, current_query=None, entities={})
    )
    instance._context_manager.resolve_references = AsyncMock(side_effect=lambda txt, _ctx: txt)
    instance._context_manager.update_context = AsyncMock()
    return instance


def _make_request() -> AgentServiceRequest:
    return AgentServiceRequest(
        task_id="task-ptao-001",
        task_type="execute",
        task_data={"instruction": "查詢庫存"},
        metadata={"session_id": "s-ptao", "user_id": "u-1"},
    )


def _make_semantic_result() -> SimpleNamespace:
    return SimpleNamespace(
        intent="query_stock",
        confidence=0.95,
        parameters={"part_number": "ABC-123"},
        model_dump=lambda: {
            "intent": "query_stock",
            "confidence": 0.95,
            "parameters": {"part_number": "ABC-123"},
        },
    )


def _make_responsibility() -> SimpleNamespace:
    return SimpleNamespace(
        type="query_stock",
        description="查詢庫存職責",
        steps=["query"],
        clarification_questions=[],
    )


def _make_ptao_result(success: bool) -> SimpleNamespace:
    raw_result = {"success": success, "data": [{"part_number": "ABC-123", "qty": 10}]}
    if not success:
        raw_result = {"success": False, "error": "handler failure"}

    return SimpleNamespace(
        raw_result=raw_result,
        thought=SimpleNamespace(model_dump=lambda: {"reasoning": "r", "complexity": "simple"}),
        observation=SimpleNamespace(
            success=success,
            model_dump=lambda: {
                "source": "query_stock",
                "success": success,
                "data": raw_result if success else None,
                "error": None if success else "handler failure",
                "duration_ms": 1.0,
            },
        ),
        decision_log=SimpleNamespace(
            entries=[
                SimpleNamespace(
                    model_dump=lambda: {"phase": "plan", "action": "x", "rationale": "y"}
                )
            ]
        ),
    )


@pytest.mark.asyncio
async def test_execute_ptao_metadata_in_completed_response(agent: MMAgent) -> None:
    agent._semantic_analyzer.analyze = AsyncMock(return_value=_make_semantic_result())
    agent._responsibility_analyzer.understand = AsyncMock(return_value=_make_responsibility())
    agent._generate_llm_business_response = AsyncMock(side_effect=lambda **kwargs: kwargs["result"])

    fake_ptao = _make_ptao_result(success=True)
    with patch("mm_agent.agent.PTAOLoop") as ptao_cls:
        ptao_cls.return_value.run = AsyncMock(return_value=fake_ptao)

        response = await agent.execute(_make_request())

    assert response.task_id == "task-ptao-001"
    assert response.status == "completed"
    assert response.error is None
    assert response.result is not None
    assert response.result["metadata"]["ptao"]["thought"]["complexity"] == "simple"
    assert response.result["metadata"]["ptao"]["observation"]["success"] is True
    assert response.result["result"]["success"] is True


@pytest.mark.asyncio
async def test_execute_ptao_metadata_kept_when_observation_failed(agent: MMAgent) -> None:
    agent._semantic_analyzer.analyze = AsyncMock(return_value=_make_semantic_result())
    agent._responsibility_analyzer.understand = AsyncMock(return_value=_make_responsibility())
    agent._generate_llm_business_response = AsyncMock(side_effect=lambda **kwargs: kwargs["result"])

    fake_ptao = _make_ptao_result(success=False)
    with patch("mm_agent.agent.PTAOLoop") as ptao_cls:
        ptao_cls.return_value.run = AsyncMock(return_value=fake_ptao)

        response = await agent.execute(_make_request())

    assert response.task_id == "task-ptao-001"
    assert response.status == "failed"
    assert response.error == "handler failure"
    assert response.result is not None
    assert response.result["metadata"]["ptao"]["observation"]["success"] is False
    assert response.result["result"]["success"] is False
