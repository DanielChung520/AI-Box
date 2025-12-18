"""
代碼功能說明: G6（安全與權限）- Chat API policy/consent/file isolation gate 測試（MVP）
創建日期: 2025-12-13 21:09:37 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 23:34:17 (UTC+8)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from agents.task_analyzer.models import TaskClassificationResult, TaskType
from api.main import app
from system.security.dependencies import get_current_user
from system.security.models import Permission, User


class _FakeTaskClassifier:
    def classify(self, *args: Any, **kwargs: Any) -> TaskClassificationResult:
        return TaskClassificationResult(
            task_type=TaskType.QUERY,
            confidence=1.0,
            reasoning="test",
        )


@dataclass
class _Msg:
    role: str
    content: str


class _FakeContextManager:
    def __init__(self) -> None:
        self._by_session: Dict[str, List[_Msg]] = {}

    def get_messages(self, *, session_id: str, limit: int = 20) -> List[_Msg]:
        items = self._by_session.get(session_id, [])
        return items[-limit:]

    def get_context_with_window(
        self, session_id: str, max_messages: int = 20
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


class _FakeMemoryService:
    async def retrieve_for_prompt(self, *args: Any, **kwargs: Any) -> Any:
        return {
            "injection_messages": [],
            "memory_hit_count": 0,
            "memory_sources": [],
            "retrieval_latency_ms": 0.0,
        }

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

    # 避免依賴真實 classifier/context/memory
    monkeypatch.setattr(
        chat_router, "get_task_classifier", lambda: _FakeTaskClassifier(), raising=True
    )
    monkeypatch.setattr(
        chat_router, "get_context_manager", lambda: _FakeContextManager(), raising=True
    )
    monkeypatch.setattr(
        chat_router,
        "get_chat_memory_service",
        lambda: _FakeMemoryService(),
        raising=True,
    )

    # 避免實際呼叫外部 LLM
    from llm.moe.moe_manager import LLMMoEManager

    async def _fake_chat(
        self: LLMMoEManager, *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:
        provider = kwargs.get("provider")
        return {
            "content": "ok",
            "model": kwargs.get("model") or "fake-model",
            "_routing": {
                "provider": (provider.value if provider else "ollama"),
                "model": kwargs.get("model") or "fake-model",
                "strategy": "manual",
                "latency_ms": 1.0,
                "failover_used": False,
            },
        }

    monkeypatch.setattr(LLMMoEManager, "chat", _fake_chat, raising=True)

    return TestClient(app)


@dataclass
class _FakePolicyGate:
    allowed_providers: List[str]
    allowed_models: Dict[str, List[str]]

    def get_allowed_providers(self) -> List[str]:
        return list(self.allowed_providers)

    def is_model_allowed(self, provider: str, model_id: Optional[str]) -> bool:
        prov = (provider or "").lower()
        mid = (model_id or "").lower()
        if self.allowed_providers and prov not in {
            p.lower() for p in self.allowed_providers
        }:
            return False
        patterns = self.allowed_models.get(prov)
        if patterns is None:
            return True
        if not mid:
            return True
        for p in patterns:
            p = p.lower()
            if p == "*":
                return True
            if p.endswith("*") and mid.startswith(p[:-1]):
                return True
            if mid == p:
                return True
        return False

    def filter_favorite_models(self, model_ids: List[str]) -> List[str]:
        out: List[str] = []
        seen: set[str] = set()
        for mid in model_ids:
            if mid in seen:
                continue
            seen.add(mid)
            # 測試中簡化：一律視為 chatgpt
            if self.is_model_allowed("chatgpt", mid):
                out.append(mid)
        return out


class _FakeConsentService:
    def __init__(self, *, allow: bool):
        self.allow = allow

    def check_consent(self, user_id: str, consent_type: Any) -> bool:
        return self.allow


class _FakeFilePermissionService:
    def __init__(self, *, allow: bool):
        self.allow = allow

    def check_file_access(
        self,
        *,
        user: User,
        file_id: str,
        required_permission: str = Permission.FILE_READ.value,
    ) -> Any:
        _ = user
        _ = required_permission
        if not self.allow:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
            )
        return {"file_id": file_id}


class _FakePreferenceService:
    def __init__(self) -> None:
        self._store: Dict[str, List[str]] = {}

    def get_favorite_models(self, *, user_id: str) -> List[str]:
        return self._store.get(user_id, [])

    def set_favorite_models(self, *, user_id: str, model_ids: List[str]) -> List[str]:
        self._store[user_id] = list(model_ids)
        return self._store[user_id]


def test_g6_model_gate_manual_disallowed(
    app_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from api.routers import chat as chat_router

    class _FakeConfigResolver:
        def get_effective_policy_gate(
            self, *, tenant_id: str, user_id: str
        ) -> _FakePolicyGate:
            _ = tenant_id
            _ = user_id
            return _FakePolicyGate(
                allowed_providers=["chatgpt"],
                allowed_models={"chatgpt": ["gpt-*"]},
            )

    monkeypatch.setattr(
        chat_router,
        "get_genai_config_resolver_service",
        lambda: _FakeConfigResolver(),
        raising=True,
    )

    payload = {
        "messages": [{"role": "user", "content": "hi"}],
        "model_selector": {"mode": "manual", "model_id": "gemini-pro"},
    }
    r = app_client.post("/api/v1/chat", json=payload)
    assert r.status_code == 403
    body = r.json()
    assert body["success"] is False
    assert body["error_code"] == "MODEL_NOT_ALLOWED"


def test_g6_favorites_filtered_on_put(
    app_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from api.routers import chat as chat_router

    class _FakeConfigResolver:
        def get_effective_policy_gate(
            self, *, tenant_id: str, user_id: str
        ) -> _FakePolicyGate:
            _ = tenant_id
            _ = user_id
            return _FakePolicyGate(
                allowed_providers=["chatgpt"],
                allowed_models={"chatgpt": ["gpt-*"]},
            )

    monkeypatch.setattr(
        chat_router,
        "get_genai_config_resolver_service",
        lambda: _FakeConfigResolver(),
        raising=True,
    )

    from services.api.services import user_preference_service

    pref = _FakePreferenceService()
    monkeypatch.setattr(
        user_preference_service,
        "get_user_preference_service",
        lambda: pref,
        raising=True,
    )

    r = app_client.put(
        "/api/v1/chat/preferences/models",
        json={"model_ids": ["gpt-4-turbo", "gemini-pro", "gpt-4-turbo"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    model_ids = body["data"]["model_ids"]
    assert model_ids == ["gpt-4-turbo"]


def test_g6_consent_gate_skips_memory(
    app_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from api.routers import chat as chat_router

    monkeypatch.setattr(
        chat_router,
        "get_genai_policy_gate_service",
        lambda: _FakePolicyGate(allowed_providers=[], allowed_models={}),
        raising=True,
    )

    monkeypatch.setattr(
        chat_router,
        "get_consent_service",
        lambda: _FakeConsentService(allow=False),
        raising=True,
    )

    from services.api.services.chat_memory_service import ChatMemoryService

    async def _boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("memory retrieval should be skipped when no consent")

    monkeypatch.setattr(ChatMemoryService, "retrieve_for_prompt", _boom, raising=True)
    monkeypatch.setattr(ChatMemoryService, "write_from_turn", _boom, raising=True)

    payload = {
        "messages": [{"role": "user", "content": "hi"}],
        "model_selector": {"mode": "manual", "model_id": "qwen3-coder:30b"},
    }
    r = app_client.post("/api/v1/chat", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    obs = body["data"]["observability"]
    assert obs["memory_hit_count"] == 0
    assert obs["memory_sources"] == []


def test_g6_file_isolation_blocks_attachments(
    app_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from api.routers import chat as chat_router

    monkeypatch.setattr(
        chat_router,
        "get_genai_policy_gate_service",
        lambda: _FakePolicyGate(allowed_providers=[], allowed_models={}),
        raising=True,
    )

    monkeypatch.setattr(
        chat_router,
        "get_file_permission_service",
        lambda: _FakeFilePermissionService(allow=False),
        raising=True,
    )

    payload = {
        "messages": [{"role": "user", "content": "hi"}],
        "model_selector": {"mode": "manual", "model_id": "qwen3-coder:30b"},
        "attachments": [{"file_id": "file_other", "file_name": "x.txt"}],
    }
    r = app_client.post("/api/v1/chat", json=payload)
    assert r.status_code == 403
    body = r.json()
    assert body["success"] is False
    assert body["error_code"] == "CHAT_HTTP_ERROR"
