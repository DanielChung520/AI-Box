"""
代碼功能說明: Chat 模型清單 API 測試（/api/v1/chat/models）
創建日期: 2025-12-13 23:06:09 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 23:34:17 (UTC+8)
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from api.main import app
from system.security.dependencies import get_current_user
from system.security.models import Permission, User


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

    class _FakeRegistry:
        async def list_models(self, *, refresh: bool = False) -> List[Dict[str, Any]]:
            _ = refresh
            return [
                {
                    "provider": "ollama",
                    "model_id": "qwen3-coder:30b",
                    "display_name": "Qwen3 Coder 30B",
                    "capabilities": ["chat"],
                    "source": "config",
                },
                {
                    "provider": "ollama",
                    "model_id": "mistral-nemo:12b",
                    "display_name": "Mistral Nemo 12B",
                    "capabilities": ["chat"],
                    "source": "config",
                },
            ]

    class _FakePolicy:
        def is_model_allowed(self, provider: str, model_id: str) -> bool:
            # only allow qwen*
            return provider == "ollama" and model_id.startswith("qwen")

    monkeypatch.setattr(
        chat_router,
        "get_genai_model_registry_service",
        lambda: _FakeRegistry(),
        raising=True,
    )

    class _FakeConfigResolver:
        def get_effective_policy_gate(
            self, *, tenant_id: str, user_id: str
        ) -> _FakePolicy:
            _ = tenant_id
            _ = user_id
            return _FakePolicy()

    monkeypatch.setattr(
        chat_router,
        "get_genai_config_resolver_service",
        lambda: _FakeConfigResolver(),
        raising=True,
    )

    return TestClient(app)


def test_list_models_filtered_by_policy(app_client: TestClient) -> None:
    r = app_client.get("/api/v1/chat/models")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    models = body["data"]["models"]
    assert len(models) == 1
    assert models[0]["model_id"] == "qwen3-coder:30b"


def test_list_models_include_disallowed(app_client: TestClient) -> None:
    r = app_client.get("/api/v1/chat/models?include_disallowed=true")
    assert r.status_code == 200
    body = r.json()
    models = body["data"]["models"]
    assert {m["model_id"] for m in models} == {"qwen3-coder:30b", "mistral-nemo:12b"}
