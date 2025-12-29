"""
代碼功能說明: GenAI 使用者 API Key（Secrets）API 測試（/api/v1/genai/user/secrets）
創建日期: 2025-12-13 23:34:17 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 23:34:17 (UTC+8)
"""

from __future__ import annotations

from typing import Dict, Set

import pytest
from fastapi.testclient import TestClient

from api.main import app
from system.security.dependencies import get_current_user
from system.security.models import Permission, User


class _FakeUserSecretService:
    def __init__(self) -> None:
        self._store: Dict[str, str] = {}

    def upsert(self, *, tenant_id: str, user_id: str, provider: str, api_key: str) -> None:
        self._store[f"{tenant_id}_{user_id}_{provider}"] = api_key

    def delete(self, *, tenant_id: str, user_id: str, provider: str) -> None:
        self._store.pop(f"{tenant_id}_{user_id}_{provider}", None)

    def list_configured_providers(self, *, tenant_id: str, user_id: str) -> Set[str]:
        prefix = f"{tenant_id}_{user_id}_"
        return {k[len(prefix) :] for k in self._store.keys() if k.startswith(prefix)}


@pytest.fixture()
def app_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    def _fake_user() -> User:
        return User(
            user_id="u_test",
            username="test",
            roles=["user"],
            permissions=[Permission.ALL.value],
            metadata={},
        )

    app.dependency_overrides[get_current_user] = _fake_user

    from api.routers import genai_user_config as user_router

    fake = _FakeUserSecretService()
    monkeypatch.setattr(
        user_router,
        "get_genai_user_llm_secret_service",
        lambda: fake,
        raising=True,
    )

    return TestClient(app)


def test_user_secrets_roundtrip(app_client: TestClient) -> None:
    headers = {"X-Tenant-ID": "t1"}

    r = app_client.put(
        "/api/v1/genai/user/secrets",
        json={"keys": {"chatgpt": "sk-test", "gemini": "g-test"}},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["success"] is True

    r = app_client.get("/api/v1/genai/user/secrets/status", headers=headers)
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["tenant_id"] == "t1"
    assert set(body["configured_providers"]) == {"chatgpt", "gemini"}

    r = app_client.delete("/api/v1/genai/user/secrets/chatgpt", headers=headers)
    assert r.status_code == 200

    r = app_client.get("/api/v1/genai/user/secrets/status", headers=headers)
    providers = set(r.json()["data"]["configured_providers"])
    assert providers == {"gemini"}
