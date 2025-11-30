# 代碼功能說明: Ollama LLM API 端點測試
# 創建日期: 2025-11-25 23:57 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 23:57 (UTC+8)

"""測試 /api/v1/llm/* 端點行為。"""

import pytest
from fastapi.testclient import TestClient

from services.api.main import app
from services.api.clients.ollama_client import (
    get_ollama_client,
    OllamaTimeoutError,
)


class SuccessfulOllamaStub:
    async def generate(self, **kwargs):
        return {"response": "hello", "node": "stub"}

    async def chat(self, **kwargs):
        return {"response": "chat", "messages": kwargs.get("messages")}

    async def embeddings(self, **kwargs):
        return {"embedding": [0.1, 0.2, 0.3]}


class TimeoutOllamaStub(SuccessfulOllamaStub):
    async def generate(self, **kwargs):
        raise OllamaTimeoutError("timeout")


@pytest.fixture
def client():
    app.dependency_overrides[get_ollama_client] = lambda: SuccessfulOllamaStub()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_ollama_client, None)


def test_generate_success(client):
    response = client.post(
        "/api/v1/llm/generate",
        json={"prompt": "ping"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["response"]["response"] == "hello"


def test_chat_success(client):
    response = client.post(
        "/api/v1/llm/chat",
        json={
            "messages": [
                {"role": "system", "content": "You are a bot."},
                {"role": "user", "content": "Hi"},
            ]
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["response"]["response"] == "chat"


def test_embeddings_success(client):
    response = client.post(
        "/api/v1/llm/embeddings",
        json={"text": "vector me"},
    )
    assert response.status_code == 200
    payload = response.json()
    items = payload["data"]["items"]
    assert len(items) == 1
    assert items[0]["embedding"] == [0.1, 0.2, 0.3]


def test_generate_timeout():
    app.dependency_overrides[get_ollama_client] = lambda: TimeoutOllamaStub()
    with TestClient(app) as test_client:
        response = test_client.post("/api/v1/llm/generate", json={"prompt": "ping"})
    app.dependency_overrides.pop(get_ollama_client, None)
    assert response.status_code == 504
    assert response.json()["success"] is False
