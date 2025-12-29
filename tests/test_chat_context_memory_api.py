"""
代碼功能說明: G3/G4 產品級 Chat（/api/v1/chat）短期上下文與長期記憶注入 pytest 驗證
創建日期: 2025-12-13 19:46:41 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 21:24:33 (UTC+8)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """建立指向 root API（api.main）的 TestClient，並 stub 掉 MoE 與 MemoryService。"""

    from api.main import app
    from api.routers import chat as chat_router
    from services.api.services.chat_memory_service import MemoryRetrievalResult
    from system.security.dependencies import get_current_user
    from system.security.models import User

    async def _fake_user() -> User:
        return User(
            user_id="test-user",
            username="test-user",
            email=None,
            roles=[],
            permissions=[],
            is_active=True,
            metadata={"test": True},
        )

    app.dependency_overrides[get_current_user] = _fake_user

    calls: List[List[Dict[str, Any]]] = []

    async def _fake_moe_chat(
        messages: List[Dict[str, Any]], *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:
        calls.append(messages)
        return {
            "content": f"reply-{len(calls)}",
            "_routing": {
                "provider": "ollama",
                "model": kwargs.get("model") or "mock-model",
                "strategy": "manual",
                "latency_ms": 1.0,
                "failover_used": False,
            },
        }

    moe = chat_router.get_moe_manager()
    monkeypatch.setattr(moe, "chat", _fake_moe_chat, raising=True)

    class _FakeMemoryService:
        def __init__(self) -> None:
            self.mode: str = "empty"  # empty/inject

        async def retrieve_for_prompt(
            self,
            *,
            user_id: str,
            session_id: str,
            task_id: Optional[str],
            request_id: Optional[str],
            query: str,
            attachments: Any = None,
        ) -> MemoryRetrievalResult:
            if self.mode == "inject":
                return MemoryRetrievalResult(
                    injection_messages=[{"role": "system", "content": "MEM"}],
                    memory_hit_count=1,
                    memory_sources=["aam"],
                    retrieval_latency_ms=12.3,
                )
            return MemoryRetrievalResult(
                injection_messages=[],
                memory_hit_count=0,
                memory_sources=[],
                retrieval_latency_ms=0.0,
            )

        async def write_from_turn(self, *args: Any, **kwargs: Any) -> None:
            return None

    fake_memory_service = _FakeMemoryService()
    monkeypatch.setattr(
        chat_router,
        "get_chat_memory_service",
        lambda: fake_memory_service,
        raising=True,
    )

    class _AllowConsentService:
        def check_consent(self, user_id: str, consent_type: Any) -> bool:
            return True

    monkeypatch.setattr(
        chat_router,
        "get_consent_service",
        lambda: _AllowConsentService(),
        raising=True,
    )
    client = TestClient(app)
    client._chat_calls = calls  # type: ignore[attr-defined]
    client._fake_memory_service = fake_memory_service  # type: ignore[attr-defined]

    yield client

    app.dependency_overrides.clear()


def test_g3_session_accumulates_and_replay(app_client: TestClient) -> None:
    session_id = "sess-g3"

    resp1 = app_client.post(
        "/api/v1/chat",
        json={
            "messages": [{"role": "user", "content": "hi"}],
            "session_id": session_id,
            "task_id": "t1",
            "model_selector": {"mode": "manual", "model_id": "qwen3-coder:30b"},
        },
    )
    assert resp1.status_code == 200

    resp2 = app_client.post(
        "/api/v1/chat",
        json={
            "messages": [{"role": "user", "content": "second"}],
            "session_id": session_id,
            "task_id": "t1",
            "model_selector": {"mode": "manual", "model_id": "qwen3-coder:30b"},
        },
    )
    assert resp2.status_code == 200

    # MoE messages：第一次只有 user；第二次至少包含 (user,assistant,user)
    calls: List[List[Dict[str, Any]]] = getattr(app_client, "_chat_calls")  # type: ignore[assignment]
    assert len(calls) == 2
    assert [m.get("role") for m in calls[0]] == ["user"]
    assert [m.get("role") for m in calls[1]] == ["user", "assistant", "user"]

    replay = app_client.get(f"/api/v1/chat/sessions/{session_id}/messages")
    assert replay.status_code == 200
    payload = replay.json()
    assert payload["success"] is True

    msgs = payload["data"]["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert msgs[0]["content"] == "hi"
    assert msgs[2]["content"] == "second"


def test_g4_memory_injection_and_metrics(app_client: TestClient) -> None:
    fake_memory_service = getattr(app_client, "_fake_memory_service")  # type: ignore[assignment]
    fake_memory_service.mode = "inject"

    resp = app_client.post(
        "/api/v1/chat",
        json={
            "messages": [{"role": "user", "content": "what did we discuss?"}],
            "session_id": "sess-g4",
            "task_id": "t2",
            "model_selector": {"mode": "manual", "model_id": "qwen3-coder:30b"},
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True

    # 檢查 observability 指標
    data = payload["data"]
    obs = data.get("observability")
    assert isinstance(obs, dict)
    assert obs.get("memory_hit_count") == 1
    assert obs.get("memory_sources") == ["aam"]
    assert obs.get("retrieval_latency_ms") == 12.3

    # 確認注入 system message（MEM）有送到 MoE
    calls: List[List[Dict[str, Any]]] = getattr(app_client, "_chat_calls")  # type: ignore[assignment]
    last = calls[-1]
    assert last[0].get("role") == "system"
    assert last[0].get("content") == "MEM"
