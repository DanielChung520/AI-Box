# 代碼功能說明: P-T-A-O Pipeline 整合測試
# 創建日期: 2026-03-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-09

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.routers.chat_module.config import ChatConfig, IntentStrategy
from api.routers.chat_module.services.completion_layer import FinalResponse
from api.routers.chat_module.services.orchestrator_service import OrchestratorService
from api.routers.chat_module.services.perception_layer import PerceptionResult
from api.routers.chat_module.services.supervision_layer import SupervisionResult
from services.api.models.chat import ChatMessage


def _make_perception_result(text: str) -> PerceptionResult:
    return PerceptionResult(
        original_text=text,
        resolved_text=text,
        corrected_text=text,
        is_complete=True,
        perception_metadata={"corrections": [], "errors": []},
        latency_ms=50.0,
    )


def _make_rag_result(
    intent_name: str, action_strategy_value: str, response_template: str, score: float
) -> MagicMock:
    rag_result = MagicMock()
    rag_result.intent_name = intent_name
    rag_result.description = "測試意圖"
    rag_result.priority = 1
    rag_result.action_strategy = MagicMock(value=action_strategy_value)
    rag_result.response_template = response_template
    rag_result.score = score
    return rag_result


@pytest.fixture()
def service_bundle() -> dict[str, Any]:
    with (
        patch(
            "api.routers.chat_module.services.orchestrator_service.PerceptionLayer"
        ) as mock_pl_cls,
        patch(
            "api.routers.chat_module.services.orchestrator_service.SupervisionLayer"
        ) as mock_sl_cls,
        patch(
            "api.routers.chat_module.services.orchestrator_service.CompletionLayer"
        ) as mock_cl_cls,
        patch(
            "api.routers.chat_module.services.orchestrator_service._get_endpoint_url"
        ) as mock_get_url,
        patch(
            "api.routers.chat_module.services.orchestrator_service.httpx.AsyncClient"
        ) as mock_httpx_client,
    ):
        mock_pl = MagicMock()
        mock_sl = MagicMock()
        mock_cl = MagicMock()
        mock_pl_cls.return_value = mock_pl
        mock_sl_cls.return_value = mock_sl
        mock_cl_cls.return_value = mock_cl
        mock_get_url.return_value = "http://mock-bpa"

        mock_pl.perceive = AsyncMock(return_value=_make_perception_result("預設查詢"))

        async def _supervise(
            action_coro: Any, config: Any = None, action_factory: Any = None
        ) -> SupervisionResult:
            result = await action_coro
            return SupervisionResult(
                success=True,
                result=result,
                error=None,
                retries_used=0,
                total_time_ms=25.0,
            )

        mock_sl.supervise = AsyncMock(side_effect=_supervise)

        mock_cl.complete = AsyncMock(
            return_value=FinalResponse(
                content="formatted answer",
                status="success",
                metadata={},
                total_latency_ms=80.0,
            )
        )
        mock_cl.to_dict = MagicMock(
            return_value={
                "content": "formatted answer",
                "status": "success",
                "metadata": {},
            }
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"data": {"content": "BPA answer"}})
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx_client.return_value.__aenter__.return_value = mock_client

        svc = OrchestratorService()
        svc.intent_rag = MagicMock()

        yield {
            "service": svc,
            "perception": mock_pl,
            "supervision": mock_sl,
            "completion": mock_cl,
            "get_url": mock_get_url,
            "http_client": mock_client,
        }


@pytest.mark.asyncio
async def test_full_pipeline_business_query(service_bundle: dict[str, Any]) -> None:
    svc = service_bundle["service"]
    svc.intent_rag.sync_classify.return_value = _make_rag_result(
        "BUSINESS_QUERY", "ROUTE_TO_BPA", "", 0.92
    )
    service_bundle["perception"].perceive.return_value = _make_perception_result("查詢庫存")

    result = await svc.process(
        messages=[ChatMessage(role="user", content="查詢庫存")],
        config=ChatConfig(),
        context={"session_id": "s1", "user_id": "u1", "agent_id": "tiptop"},
    )

    assert result["content"] == "formatted answer"
    assert result["intent"]["intent_name"] == "BUSINESS_QUERY"
    assert result["strategy"] == IntentStrategy.ROUTE_TO_AGENT.value
    assert result["agent_type"] == "bpa"
    service_bundle["perception"].perceive.assert_awaited_once()
    service_bundle["supervision"].supervise.assert_awaited_once()
    service_bundle["completion"].complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_full_pipeline_greeting(service_bundle: dict[str, Any]) -> None:
    svc = service_bundle["service"]
    svc.intent_rag.sync_classify.return_value = _make_rag_result(
        "GREETING", "DIRECT_RESPONSE", "您好！", 0.95
    )

    result = await svc.process(
        messages=[ChatMessage(role="user", content="你好")],
        config=ChatConfig(),
        context={"session_id": "s2", "user_id": "u2"},
    )

    assert result["content"] == "您好！"
    assert result["strategy"] == IntentStrategy.DIRECT_RESPONSE.value
    service_bundle["supervision"].supervise.assert_not_awaited()
    service_bundle["completion"].complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_full_pipeline_knowledge_query(service_bundle: dict[str, Any]) -> None:
    svc = service_bundle["service"]
    svc.intent_rag.sync_classify.return_value = _make_rag_result(
        "GENERAL_QA", "KNOWLEDGE_RAG", "", 0.91
    )
    service_bundle["perception"].perceive.return_value = _make_perception_result("說明庫存規則")

    result = await svc.process(
        messages=[ChatMessage(role="user", content="說明庫存規則")],
        config=ChatConfig(),
        context={"session_id": "s3", "user_id": "u3", "agent_id": "tiptop"},
    )

    assert result["content"] == "formatted answer"
    assert result["strategy"] == IntentStrategy.KNOWLEDGE_RAG.value
    assert result["agent_type"] == "bpa"
    service_bundle["supervision"].supervise.assert_awaited_once()
    service_bundle["http_client"].post.assert_awaited_once()


@pytest.mark.asyncio
async def test_regression_existing_greeting(service_bundle: dict[str, Any]) -> None:
    svc = service_bundle["service"]
    template = "哈囉！很高興為您服務"
    svc.intent_rag.sync_classify.return_value = _make_rag_result(
        "GREETING", "DIRECT_RESPONSE", template, 0.96
    )

    result = await svc.process(
        messages=[ChatMessage(role="user", content="嗨")],
        config=ChatConfig(),
        context={"session_id": "s4", "user_id": "u4"},
    )

    assert result["content"] == template
    assert result["strategy"] == IntentStrategy.DIRECT_RESPONSE.value


@pytest.mark.asyncio
async def test_regression_existing_bpa_routing(service_bundle: dict[str, Any]) -> None:
    svc = service_bundle["service"]
    perception = PerceptionResult(
        original_text="查詢 10-0001",
        resolved_text="查詢 10-0001",
        corrected_text="查詢料號 10-0001",
        is_complete=True,
        perception_metadata={"corrections": ["補全料號語意"], "errors": []},
        latency_ms=40.0,
    )
    service_bundle["perception"].perceive.return_value = perception
    svc.intent_rag.sync_classify.return_value = _make_rag_result(
        "BUSINESS_QUERY", "ROUTE_TO_BPA", "", 0.89
    )

    await svc.process(
        messages=[ChatMessage(role="user", content="查詢 10-0001")],
        config=ChatConfig(),
        context={"session_id": "s5", "user_id": "u5", "agent_id": "tiptop"},
    )

    post_call = service_bundle["http_client"].post.await_args
    post_kwargs = post_call.kwargs
    payload = post_kwargs["json"]
    assert post_call.args[0] == "http://mock-bpa/execute"
    assert payload["task_data"]["instruction"] == "查詢料號 10-0001"
    assert payload["task_data"]["original_text"] == "查詢 10-0001"
    assert payload["task_data"]["intent"] == "BUSINESS_QUERY"
    assert payload["task_data"]["intent_confidence"] == 0.89
    assert payload["metadata"]["perception"] == {"corrections": ["補全料號語意"], "errors": []}


@pytest.mark.asyncio
async def test_empty_input(service_bundle: dict[str, Any]) -> None:
    svc = service_bundle["service"]

    result = await svc.process(
        messages=[], config=ChatConfig(), context={"session_id": "s6", "user_id": "u6"}
    )

    assert "抱歉" in result["content"]
    assert result["strategy"] == IntentStrategy.DIRECT_RESPONSE.value
    service_bundle["perception"].perceive.assert_not_awaited()


@pytest.mark.asyncio
async def test_garbled_input(service_bundle: dict[str, Any]) -> None:
    svc = service_bundle["service"]
    garbled_text = "@@@%%%###??"
    service_bundle["perception"].perceive.return_value = _make_perception_result(garbled_text)
    svc.intent_rag.sync_classify.return_value = _make_rag_result(
        "BUSINESS_QUERY", "ROUTE_TO_BPA", "", 0.82
    )

    result = await svc.process(
        messages=[ChatMessage(role="user", content=garbled_text)],
        config=ChatConfig(),
        context={"session_id": "s7", "user_id": "u7", "agent_id": "tiptop"},
    )

    assert result["content"] == "formatted answer"
    service_bundle["perception"].perceive.assert_awaited_once_with(garbled_text, "s7", "u7")


@pytest.mark.asyncio
async def test_no_session_id(service_bundle: dict[str, Any]) -> None:
    svc = service_bundle["service"]
    service_bundle["perception"].perceive.return_value = _make_perception_result("查詢工單")
    svc.intent_rag.sync_classify.return_value = _make_rag_result(
        "BUSINESS_QUERY", "ROUTE_TO_BPA", "", 0.9
    )

    result = await svc.process(
        messages=[ChatMessage(role="user", content="查詢工單")],
        config=ChatConfig(),
        context={"user_id": "u8", "agent_id": "tiptop"},
    )

    assert result["content"] == "formatted answer"
    service_bundle["perception"].perceive.assert_awaited_once_with("查詢工單", "", "u8")
