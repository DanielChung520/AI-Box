# 代碼功能說明: Chat v2 端點集成測試（POST /api/v2/chat、POST /api/v2/chat/stream，含認證）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""調用 POST /api/v2/chat（含認證），斷言 200 與 data.content；流式端點斷言 SSE start/content/done。"""

from __future__ import annotations

import json
from typing import Any, List
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from services.api.models.chat import (
    ChatResponse,
    ObservabilityInfo,
    RoutingInfo,
)


@pytest.fixture()
def app_client_v2(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """建立指向 api.main 的 TestClient，覆蓋認證與 pipeline（v2）。"""

    from api.main import app
    from system.security.dependencies import get_current_tenant_id, get_current_user
    from system.security.models import User

    async def _fake_user() -> User:
        return User(
            user_id="test-user-v2",
            username="test-user-v2",
            email=None,
            roles=[],
            permissions=[],
            is_active=True,
            metadata={"test": True},
        )

    async def _fake_tenant_id() -> str:
        return "test-tenant-v2"

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_current_tenant_id] = _fake_tenant_id

    mock_response = ChatResponse(
        content="v2 mock reply",
        session_id="sess-v2",
        task_id="task-1",
        routing=RoutingInfo(
            provider="ollama",
            model="mock-model",
            strategy="manual",
            latency_ms=10.0,
            failover_used=False,
        ),
        observability=ObservabilityInfo(
            request_id="req-1",
            session_id="sess-v2",
            task_id="task-1",
        ),
        actions=None,
    )

    async def _mock_process(request: Any) -> ChatResponse:
        return mock_response

    mock_pipeline = AsyncMock()
    mock_pipeline.process = _mock_process

    def _get_mock_pipeline() -> Any:
        return mock_pipeline

    monkeypatch.setattr(
        "api.routers.chat_module.handlers.sync_handler.get_chat_pipeline",
        _get_mock_pipeline,
    )

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_chat_v2_post_200_and_content(app_client_v2: TestClient) -> None:
    """POST /api/v2/chat 應返回 200 且 data.content 存在。"""
    resp = app_client_v2.post(
        "/api/v2/chat",
        json={
            "messages": [{"role": "user", "content": "hello v2"}],
            "session_id": "sess-v2",
            "task_id": "task-1",
            "model_selector": {"mode": "manual", "model_id": "qwen3-coder:30b"},
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    data = payload.get("data")
    assert data is not None
    assert "content" in data
    assert data["content"] == "v2 mock reply"
    assert data.get("session_id") == "sess-v2"
    assert data.get("routing") is not None


def test_chat_v2_validation_error_empty_messages(app_client_v2: TestClient) -> None:
    """POST /api/v2/chat 空 messages 應返回 422。"""
    resp = app_client_v2.post(
        "/api/v2/chat",
        json={
            "messages": [],
            "model_selector": {"mode": "auto"},
        },
    )
    assert resp.status_code == 422


def _parse_sse_events(response_text: str) -> List[dict]:
    """解析 SSE 響應為事件列表（每行 data: {...} 轉為 dict）。"""
    events: List[dict] = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


@pytest.fixture()
def app_client_v2_stream(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """建立用於流式端點測試的 TestClient，mock stream_handler.get_chat_pipeline。"""
    from api.main import app
    from system.security.dependencies import get_current_tenant_id, get_current_user
    from system.security.models import User

    async def _fake_user() -> User:
        return User(
            user_id="test-user-v2",
            username="test-user-v2",
            email=None,
            roles=[],
            permissions=[],
            is_active=True,
            metadata={"test": True},
        )

    async def _fake_tenant_id() -> str:
        return "test-tenant-v2"

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_current_tenant_id] = _fake_tenant_id

    mock_response = ChatResponse(
        content="流式回覆內容",
        session_id="sess-stream",
        task_id="task-1",
        routing=RoutingInfo(
            provider="ollama",
            model="mock-model",
            strategy="manual",
            latency_ms=10.0,
            failover_used=False,
        ),
        observability=ObservabilityInfo(
            request_id="req-stream-1",
            session_id="sess-stream",
            task_id="task-1",
        ),
        actions=None,
    )

    async def _mock_process(request: Any) -> ChatResponse:
        return mock_response

    mock_pipeline = AsyncMock()
    mock_pipeline.process = _mock_process

    def _get_mock_pipeline() -> Any:
        return mock_pipeline

    monkeypatch.setattr(
        "api.routers.chat_module.handlers.stream_handler.get_chat_pipeline",
        _get_mock_pipeline,
    )

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_chat_v2_stream_sse_start_content_done(app_client_v2_stream: TestClient) -> None:
    """POST /api/v2/chat/stream 應返回 SSE，且含 start、content（data.chunk）、done（T6.1–T6.3）。"""
    resp = app_client_v2_stream.post(
        "/api/v2/chat/stream",
        json={
            "messages": [{"role": "user", "content": "hello stream"}],
            "session_id": "sess-stream",
            "model_selector": {"mode": "manual", "model_id": "qwen3-coder:30b"},
        },
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    events = _parse_sse_events(resp.text)
    assert len(events) >= 2
    # 第一筆應為 start（T6.2）
    assert events[0].get("type") == "start"
    assert "data" in events[0]
    assert "request_id" in events[0]["data"]
    assert events[0]["data"].get("session_id") == "sess-stream"
    # 中間為 content（T6.1：type content, data.chunk）
    content_events = [e for e in events if e.get("type") == "content"]
    assert len(content_events) >= 1
    for e in content_events:
        assert "data" in e and "chunk" in e["data"]
    # 最後一筆應為 done（T6.3）
    assert events[-1].get("type") == "done"
    assert events[-1].get("data", {}).get("request_id") is not None
    assert "routing" in events[-1]


def test_chat_v2_stream_file_created_event(
    app_client_v2_stream: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """當 pipeline 返回 actions 含 file_created 時，SSE 應含 file_created 事件（T6.4）。"""
    mock_response_with_file = ChatResponse(
        content="已建立檔案",
        session_id="sess-fc",
        task_id="task-1",
        routing=RoutingInfo(
            provider="ollama",
            model="mock",
            strategy="manual",
            latency_ms=1.0,
            failover_used=False,
        ),
        observability=None,
        actions=[
            {
                "type": "file_created",
                "file_id": "file-123",
                "filename": "new_file.txt",
                "task_id": "task-1",
            },
        ],
    )

    async def _mock_process_with_file(request: Any) -> ChatResponse:
        return mock_response_with_file

    mock_pipeline = AsyncMock()
    mock_pipeline.process = _mock_process_with_file
    monkeypatch.setattr(
        "api.routers.chat_module.handlers.stream_handler.get_chat_pipeline",
        lambda: mock_pipeline,
    )
    resp = app_client_v2_stream.post(
        "/api/v2/chat/stream",
        json={
            "messages": [{"role": "user", "content": "create file"}],
            "session_id": "sess-fc",
            "model_selector": {"mode": "auto"},
        },
    )
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    file_created_events = [e for e in events if e.get("type") == "file_created"]
    assert len(file_created_events) == 1
    assert file_created_events[0]["data"]["file_id"] == "file-123"
    assert file_created_events[0]["data"]["filename"] == "new_file.txt"
