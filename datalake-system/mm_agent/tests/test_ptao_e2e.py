# 代碼功能說明: MM-Agent P-T-A-O 端對端整合測試
# 創建日期: 2026-03-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-10

import sys
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from typing import Any

import pytest

datalake_system_dir = Path(__file__).resolve().parent.parent
if str(datalake_system_dir) not in sys.path:
    sys.path.insert(0, str(datalake_system_dir))

ai_box_root = datalake_system_dir.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))


@pytest.fixture
def agent() -> Any:
    mm_agent_cls = importlib.import_module("mm_agent.agent").MMAgent
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
        instance = mm_agent_cls(**mock_services)

    instance._context_manager.get_context = AsyncMock(
        return_value=SimpleNamespace(last_result=None, current_query=None, entities={})
    )
    instance._context_manager.resolve_references = AsyncMock(side_effect=lambda txt, _ctx: txt)
    instance._context_manager.update_context = AsyncMock()
    instance._semantic_analyzer.analyze = AsyncMock()
    instance._responsibility_analyzer.understand = AsyncMock()
    instance._generate_llm_business_response = AsyncMock(
        side_effect=lambda **kwargs: kwargs["result"]
    )
    instance._orchestrator_client._call_orchestrator = AsyncMock(return_value={})
    return instance


def _make_request(instruction: str) -> SimpleNamespace:
    return SimpleNamespace(
        task_id="task-e2e-001",
        task_type="execute",
        task_data={"instruction": instruction},
        metadata={"session_id": "session-e2e", "user_id": "u-001"},
    )


def _semantic(intent: str, parameters: dict) -> SimpleNamespace:
    return SimpleNamespace(
        intent=intent,
        confidence=0.96,
        parameters=parameters,
        model_dump=lambda: {
            "intent": intent,
            "confidence": 0.96,
            "parameters": parameters,
        },
    )


def _responsibility(
    resp_type: str, steps: list[str], questions: list[str] | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        type=resp_type,
        responsibility_type=resp_type,
        description=f"責責: {resp_type}",
        steps=steps,
        clarification_questions=questions or [],
    )


def _assert_ptao_metadata(resp_result: dict) -> dict:
    ptao = resp_result["metadata"]["ptao"]
    assert "thought" in ptao
    assert "observation" in ptao
    assert "decision_log" in ptao
    return ptao


@pytest.mark.asyncio
async def test_e2e_simple_part_query(agent: Any) -> None:
    agent._semantic_analyzer.analyze.return_value = _semantic(
        "query_part", {"part_number": "P-1001"}
    )
    agent._responsibility_analyzer.understand.return_value = _responsibility(
        "query_part", ["query"]
    )

    query_part_handler = AsyncMock(
        return_value={"success": True, "part_info": {"part_number": "P-1001"}, "response": "ok"}
    )
    agent._responsibility_registry.register("query_part", query_part_handler)

    response = await agent.execute(_make_request("查詢料號 P-1001"))

    assert response.status == "completed"
    assert response.result is not None
    ptao = _assert_ptao_metadata(response.result)
    assert ptao["thought"]["complexity"] == "simple"
    assert ptao["observation"]["success"] is True
    assert ptao["observation"]["source"] == "query_part"
    agent._context_manager.update_context.assert_awaited_once()


@pytest.mark.asyncio
async def test_e2e_stock_query(agent: Any) -> None:
    agent._semantic_analyzer.analyze.return_value = _semantic(
        "query_stock", {"part_number": "S-2002"}
    )
    agent._responsibility_analyzer.understand.return_value = _responsibility(
        "query_stock", ["query"]
    )

    query_stock_handler = AsyncMock(
        return_value={
            "success": True,
            "stock_list": [{"part_number": "S-2002", "qty": 8}],
            "count": 1,
        }
    )
    agent._responsibility_registry.register("query_stock", query_stock_handler)

    response = await agent.execute(_make_request("查詢 S-2002 庫存"))

    assert response.status == "completed"
    assert response.result is not None
    ptao = _assert_ptao_metadata(response.result)
    assert isinstance(ptao["thought"], dict)
    assert isinstance(ptao["observation"], dict)
    assert isinstance(ptao["decision_log"], list)
    assert len(ptao["decision_log"]) >= 4


@pytest.mark.asyncio
async def test_e2e_shortage_analysis(agent: Any) -> None:
    agent._semantic_analyzer.analyze.return_value = _semantic(
        "analyze_shortage", {"part_number": "M-3003"}
    )
    agent._responsibility_analyzer.understand.return_value = _responsibility(
        "analyze_shortage", ["collect", "analyze"]
    )

    analyze_shortage_handler = AsyncMock(
        return_value={"success": True, "analysis": {"part_number": "M-3003", "shortage": 120}}
    )
    agent._responsibility_registry.register("analyze_shortage", analyze_shortage_handler)

    response = await agent.execute(_make_request("分析 M-3003 缺料"))

    assert response.status == "completed"
    assert response.result is not None
    ptao = _assert_ptao_metadata(response.result)
    assert ptao["thought"]["complexity"] == "complex"
    assert len(ptao["decision_log"]) >= 4


@pytest.mark.asyncio
async def test_e2e_missing_params_error(agent: Any) -> None:
    agent._semantic_analyzer.analyze.return_value = _semantic("query_part", {})
    agent._responsibility_analyzer.understand.return_value = _responsibility(
        "query_part", ["query"]
    )

    failing_handler = AsyncMock(side_effect=ValueError("缺少料號參數（part_number）"))
    agent._responsibility_registry.register("query_part", failing_handler)

    response = await agent.execute(_make_request("查詢料號"))

    assert response.status == "failed"
    assert response.result is not None
    ptao = _assert_ptao_metadata(response.result)
    assert ptao["observation"]["success"] is False
    assert "缺少料號參數" in ptao["observation"]["error"]


@pytest.mark.asyncio
async def test_e2e_unknown_intent(agent: Any) -> None:
    agent._semantic_analyzer.analyze.return_value = _semantic("unknown_intent", {"foo": "bar"})
    agent._responsibility_analyzer.understand.return_value = _responsibility(
        "unknown_intent", ["route"]
    )

    response = await agent.execute(_make_request("做一些未知操作"))

    assert response.status == "failed"
    assert response.result is not None
    ptao = _assert_ptao_metadata(response.result)
    assert ptao["observation"]["success"] is False
    assert "未知的職責類型" in ptao["observation"]["error"]


@pytest.mark.asyncio
async def test_e2e_clarification_request(agent: Any) -> None:
    questions = ["請提供料號", "請提供倉庫"]
    agent._semantic_analyzer.analyze.return_value = _semantic("clarification_needed", {})
    agent._responsibility_analyzer.understand.return_value = _responsibility(
        "clarification_needed", ["clarify"], questions
    )

    clarification_handler = AsyncMock(
        return_value={
            "success": False,
            "error": "需要澄清用戶意圖",
            "clarification_questions": questions,
            "response": "請提供料號\n請提供倉庫",
        }
    )
    agent._responsibility_registry.register("clarification_needed", clarification_handler)
    agent._generate_llm_business_response = AsyncMock(
        return_value={
            "success": False,
            "error": "需要澄清用戶意圖",
            "response": "請提供料號\n請提供倉庫",
            "clarification_questions": questions,
        }
    )

    response = await agent.execute(_make_request("幫我查一下"))

    assert response.status == "failed"
    assert response.result is not None
    assert "請提供料號" in response.result["result"]["response"]
    ptao = _assert_ptao_metadata(response.result)
    assert ptao["observation"]["success"] is False


@pytest.mark.asyncio
async def test_ptao_compliance_report(agent: Any) -> None:
    agent._semantic_analyzer.analyze.return_value = _semantic(
        "analyze_shortage", {"part_number": "C-9009"}
    )
    agent._responsibility_analyzer.understand.return_value = _responsibility(
        "analyze_shortage", ["collect", "analyze", "summarize"]
    )

    success_handler = AsyncMock(return_value={"success": True, "analysis": {"shortage": 33}})
    agent._responsibility_registry.register("analyze_shortage", success_handler)
    success_resp = await agent.execute(_make_request("分析 C-9009 缺料"))

    fail_handler = AsyncMock(side_effect=ValueError("handler failure for compliance"))
    agent._responsibility_registry.register("query_part", fail_handler)
    agent._semantic_analyzer.analyze.return_value = _semantic("query_part", {})
    agent._responsibility_analyzer.understand.return_value = _responsibility(
        "query_part", ["query"]
    )
    failure_resp = await agent.execute(_make_request("查詢缺參數料號"))

    assert success_resp.result is not None
    assert failure_resp.result is not None
    ptao_success = success_resp.result["metadata"]["ptao"]
    ptao_failure = failure_resp.result["metadata"]["ptao"]

    decision_log = ptao_success["decision_log"]
    observation = ptao_success["observation"]
    phases = [entry["phase"] for entry in decision_log]

    checklist = {
        "thought_action_trace": bool(ptao_success.get("thought")),
        "action_observation_loop": bool(ptao_success.get("observation")),
        "explicit_stop_condition": phases.count("act") == 1 and phases.count("observe") == 1,
        "planning_phase": bool(decision_log) and decision_log[0]["phase"] == "plan",
        "structured_observation": {"source", "success", "duration_ms"}.issubset(observation.keys()),
        "multi_step_support": ptao_success["thought"].get("complexity") == "complex",
        "state_persistence": agent._context_manager.update_context.await_count >= 2,
        "graceful_error_handling": ptao_failure["observation"]["success"] is False,
        "decision_log": len(decision_log) > 0,
    }
    score = sum(1 for passed in checklist.values() if passed)
    assert score >= 7
