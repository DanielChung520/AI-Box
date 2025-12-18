"""
代碼功能說明: 產品級 Chat API（/api/v1/chat）最小 pytest 驗證（含偏好 API）
創建日期: 2025-12-13 18:28:38 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 18:28:38 (UTC+8)
"""

from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """建立指向 root API（api.main）的 TestClient。

    注意：tests/conftest.py 內建的 test_client 會指向 services.api.main；
    本測試需驗證產品級入口（api.main）。
    """

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


def test_chat_product_manual(app_client: TestClient) -> None:
    resp = app_client.post(
        "/api/v1/chat",
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "session_id": "sess-1",
            "task_id": "123",
            "model_selector": {"mode": "manual", "model_id": "qwen3-coder:30b"},
        },
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True

    data = payload["data"]
    assert data["content"] == "pong"
    assert data["session_id"] == "sess-1"
    assert data["task_id"] == "123"

    routing = data["routing"]
    assert routing["provider"] == "ollama"
    assert routing["strategy"] == "manual"
    assert routing["failover_used"] is False


def test_chat_preferences_models_get_put(app_client: TestClient) -> None:
    # 初始為空
    resp = app_client.get("/api/v1/chat/preferences/models")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    assert isinstance(payload["data"]["model_ids"], list)

    # 更新（含重複與空白）
    resp2 = app_client.put(
        "/api/v1/chat/preferences/models",
        json={"model_ids": ["gpt-4-turbo", "  gpt-4-turbo  ", "", "qwen3-coder:30b"]},
    )
    assert resp2.status_code == 200
    payload2 = resp2.json()
    assert payload2["success"] is True
    assert payload2["data"]["model_ids"] == ["gpt-4-turbo", "qwen3-coder:30b"]

    # 再取一次，應一致
    resp3 = app_client.get("/api/v1/chat/preferences/models")
    assert resp3.status_code == 200
    payload3 = resp3.json()
    assert payload3["success"] is True
    assert payload3["data"]["model_ids"] == ["gpt-4-turbo", "qwen3-coder:30b"]
