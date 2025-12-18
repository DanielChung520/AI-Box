"""
代碼功能說明: Chat 非同步 requests API 測試（create/poll/abort/隔離）
創建日期: 2025-12-13 22:26:20 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 22:41:48 (UTC+8)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from api.main import app
from system.security.dependencies import get_current_user
from system.security.models import Permission, User


@dataclass
class _Msg:
    role: str
    content: str


class _FakeContextManager:
    def __init__(self) -> None:
        self._by_session: Dict[str, List[_Msg]] = {}

    def get_messages(self, *, session_id: str, limit: int = 20) -> List[_Msg]:
        return self._by_session.get(session_id, [])[-limit:]

    def get_context_with_window(
        self, *, session_id: str, max_messages: int = 20
    ) -> List[Dict[str, Any]]:
        items = self._by_session.get(session_id, [])
        return [{"role": m.role, "content": m.content} for m in items[-max_messages:]]

    def record_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        _ = agent_name
        _ = metadata
        self._by_session.setdefault(session_id, []).append(
            _Msg(role=role, content=content)
        )
        return True


class _FakeConsentService:
    def __init__(self, *, allow: bool) -> None:
        self.allow = allow

    def check_consent(self, user_id: str, consent_type: Any) -> bool:
        return self.allow


class _FakeFilePermissionService:
    def check_file_access(
        self,
        *,
        user: User,
        file_id: str,
        required_permission: str = Permission.FILE_READ.value,
    ) -> Any:
        _ = user
        _ = required_permission
        return {"file_id": file_id}


class _FakeMemoryService:
    async def retrieve_for_prompt(self, *args: Any, **kwargs: Any) -> Any:
        from services.api.services.chat_memory_service import MemoryRetrievalResult

        return MemoryRetrievalResult(
            injection_messages=[],
            memory_hit_count=0,
            memory_sources=[],
            retrieval_latency_ms=0.0,
        )

    async def write_from_turn(self, *args: Any, **kwargs: Any) -> None:
        return None


@pytest.fixture()
def app_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    def _fake_user() -> User:
        return User(
            user_id="u_test",
            username="test",
            roles=["user"],
            permissions=[Permission.ALL.value],
        )

    app.dependency_overrides[get_current_user] = _fake_user

    from api.routers import chat as chat_router

    monkeypatch.setattr(
        chat_router, "get_context_manager", lambda: _FakeContextManager(), raising=True
    )
    monkeypatch.setattr(
        chat_router,
        "get_consent_service",
        lambda: _FakeConsentService(allow=True),
        raising=True,
    )
    monkeypatch.setattr(
        chat_router,
        "get_file_permission_service",
        lambda: _FakeFilePermissionService(),
        raising=True,
    )
    monkeypatch.setattr(
        chat_router,
        "get_chat_memory_service",
        lambda: _FakeMemoryService(),
        raising=True,
    )

    class _FakeMoE:
        async def chat(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {
                "content": "ok",
                "_routing": {
                    "provider": "ollama",
                    "model": kwargs.get("model") or "mock-model",
                    "strategy": "manual",
                    "latency_ms": 1.0,
                    "failover_used": False,
                },
            }

    monkeypatch.setattr(
        chat_router, "get_moe_manager", lambda: _FakeMoE(), raising=True
    )

    return TestClient(app)


def _poll_state(
    client: TestClient, request_id: str, *, timeout_s: float = 3.0
) -> Dict[str, Any]:
    start = time.time()
    last: Dict[str, Any] = {}
    while time.time() - start < timeout_s:
        r = client.get(f"/api/v1/chat/requests/{request_id}")
        assert r.status_code == 200
        last = r.json()["data"]
        if last.get("status") in {"succeeded", "failed", "aborted"}:
            return last
        time.sleep(0.05)
    return last


def test_async_request_create_and_poll_succeeds(app_client: TestClient) -> None:
    payload = {
        "messages": [{"role": "user", "content": "hi"}],
        "model_selector": {"mode": "manual", "model_id": "qwen3-coder:30b"},
    }
    r = app_client.post("/api/v1/chat/requests", json=payload)
    assert r.status_code == 202
    request_id = r.json()["data"]["request_id"]

    state = _poll_state(app_client, request_id)
    assert state["status"] == "succeeded"
    assert state["response"]["content"] == "ok"


def test_async_request_abort(
    app_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from api.routers import chat as chat_router

    class _SlowMoE:
        async def chat(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
            import asyncio

            await asyncio.sleep(2.0)
            return {
                "content": "late",
                "_routing": {
                    "provider": "ollama",
                    "model": kwargs.get("model") or "mock-model",
                    "strategy": "manual",
                    "latency_ms": 1.0,
                    "failover_used": False,
                },
            }

    monkeypatch.setattr(
        chat_router, "get_moe_manager", lambda: _SlowMoE(), raising=True
    )

    payload = {
        "messages": [{"role": "user", "content": "hi"}],
        "model_selector": {"mode": "manual", "model_id": "qwen3-coder:30b"},
    }
    r = app_client.post("/api/v1/chat/requests", json=payload)
    assert r.status_code == 202
    request_id = r.json()["data"]["request_id"]

    ar = app_client.post(f"/api/v1/chat/requests/{request_id}/abort")
    assert ar.status_code == 200

    state = _poll_state(app_client, request_id)
    assert state["status"] == "aborted"


def test_async_request_isolation(app_client: TestClient) -> None:
    payload = {
        "messages": [{"role": "user", "content": "hi"}],
        "model_selector": {"mode": "manual", "model_id": "qwen3-coder:30b"},
    }
    r = app_client.post("/api/v1/chat/requests", json=payload)
    assert r.status_code == 202
    request_id = r.json()["data"]["request_id"]

    def _other_user() -> User:
        return User(user_id="u_other", username="other", roles=["user"], permissions=[])

    app.dependency_overrides[get_current_user] = _other_user

    gr = app_client.get(f"/api/v1/chat/requests/{request_id}")
    assert gr.status_code == 404
