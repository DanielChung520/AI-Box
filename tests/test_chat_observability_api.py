"""
代碼功能說明: G5 觀測性 API（/api/v1/chat/observability/*）pytest 回歸驗證
創建日期: 2025-12-13 20:57:56 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 21:00:38 (UTC+8)
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from api.main import app
    from api.routers import chat as chat_router
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

    async def _fake_moe_chat(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {
            "content": "pong",
            "_routing": {
                "provider": "ollama",
                "model": kwargs.get("model") or "mock-model",
                "strategy": "manual",
                "latency_ms": 12.3,
                "failover_used": False,
            },
        }

    moe = chat_router.get_moe_manager()
    monkeypatch.setattr(moe, "chat", _fake_moe_chat, raising=True)

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_observability_trace_recent_stats(app_client: TestClient) -> None:
    # 先打一次 chat 產生 trace/metrics
    resp = app_client.post(
        "/api/v1/chat",
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "session_id": "sess-g5",
            "task_id": "t-g5",
            "model_selector": {"mode": "manual", "model_id": "qwen3-coder:30b"},
        },
        headers={"X-Request-ID": "req-g5-1"},
    )
    assert resp.status_code == 200

    # recent
    recent = app_client.get("/api/v1/chat/observability/recent?limit=50")
    assert recent.status_code == 200
    recent_payload = recent.json()
    assert recent_payload["success"] is True
    events: List[Dict[str, Any]] = recent_payload["data"]["events"]
    assert any(e.get("request_id") == "req-g5-1" for e in events)

    # traces
    traces = app_client.get("/api/v1/chat/observability/traces/req-g5-1")
    assert traces.status_code == 200
    traces_payload = traces.json()
    assert traces_payload["success"] is True
    trace_events: List[Dict[str, Any]] = traces_payload["data"]["events"]
    names = [e.get("event") for e in trace_events]
    assert "chat.request_received" in names
    assert "chat.memory_retrieved" in names
    assert "chat.llm_completed" in names
    assert "chat.response_sent" in names

    # stats
    stats = app_client.get("/api/v1/chat/observability/stats")
    assert stats.status_code == 200
    stats_payload = stats.json()
    assert stats_payload["success"] is True
    s = stats_payload["data"]["stats"]
    assert s["chat_total"] >= 1
