"""
代碼功能說明: GenAI 租戶（Tenant/Org）Policy/Secrets API 測試（/api/v1/genai/tenants/...）
創建日期: 2025-12-13 23:34:17 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 23:34:17 (UTC+8)
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

import pytest
from fastapi.testclient import TestClient

from api.main import app
from services.api.models.genai_tenant_policy import (
    GenAITenantPolicy,
    GenAITenantPolicyUpdate,
)
from system.security.dependencies import get_current_user
from system.security.models import Permission, User


class _FakeTenantPolicyService:
    def __init__(self) -> None:
        self._policy: Dict[str, GenAITenantPolicy] = {}
        self._secrets: Dict[str, Dict[str, str]] = {}

    def get_policy(self, tenant_id: str) -> Optional[GenAITenantPolicy]:
        return self._policy.get(tenant_id)

    def upsert_policy(
        self, tenant_id: str, update: GenAITenantPolicyUpdate
    ) -> GenAITenantPolicy:
        existing = self._policy.get(tenant_id)
        allowed_providers = (
            update.allowed_providers
            if update.allowed_providers is not None
            else (existing.allowed_providers if existing else [])
        )
        allowed_models = (
            update.allowed_models
            if update.allowed_models is not None
            else (existing.allowed_models if existing else {})
        )
        default_fallback = (
            update.default_fallback
            if update.default_fallback is not None
            else (existing.default_fallback if existing else None)
        )
        model_registry_models = (
            update.model_registry_models
            if update.model_registry_models is not None
            else (existing.model_registry_models if existing else [])
        )
        policy = GenAITenantPolicy(
            tenant_id=tenant_id,
            allowed_providers=list(allowed_providers or []),
            allowed_models=dict(allowed_models or {}),
            default_fallback=default_fallback,
            model_registry_models=list(model_registry_models or []),
            updated_at=datetime.utcnow(),
        )
        self._policy[tenant_id] = policy
        return policy

    def set_tenant_secret(self, tenant_id: str, provider: str, api_key: str) -> None:
        self._secrets.setdefault(tenant_id, {})[provider] = api_key

    def delete_tenant_secret(self, tenant_id: str, provider: str) -> None:
        self._secrets.get(tenant_id, {}).pop(provider, None)


@pytest.fixture()
def app_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    def _fake_user() -> User:
        return User(
            user_id="u_admin",
            username="admin",
            roles=["admin"],
            permissions=[Permission.ALL.value],
        )

    app.dependency_overrides[get_current_user] = _fake_user

    from api.routers import genai_tenant_config as tenant_router

    fake = _FakeTenantPolicyService()
    monkeypatch.setattr(
        tenant_router,
        "get_genai_tenant_policy_service",
        lambda: fake,
        raising=True,
    )

    return TestClient(app)


def test_tenant_policy_get_put(app_client: TestClient) -> None:
    payload = {
        "allowed_providers": ["ollama", "chatgpt"],
        "allowed_models": {"ollama": ["qwen*"]},
        "default_fallback": {"provider": "ollama", "model": "llama3.1:8b"},
    }

    r = app_client.put("/api/v1/genai/tenants/t1/policy", json=payload)
    assert r.status_code == 200
    assert r.json()["success"] is True

    r = app_client.get("/api/v1/genai/tenants/t1/policy")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["tenant_id"] == "t1"
    assert set(body["allowed_providers"]) == {"ollama", "chatgpt"}
    assert body["allowed_models"]["ollama"] == ["qwen*"]


def test_tenant_secrets_put_delete(app_client: TestClient) -> None:
    r = app_client.put(
        "/api/v1/genai/tenants/t1/secrets",
        json={"keys": {"chatgpt": "sk-tenant"}},
    )
    assert r.status_code == 200

    r = app_client.delete("/api/v1/genai/tenants/t1/secrets/chatgpt")
    assert r.status_code == 200
