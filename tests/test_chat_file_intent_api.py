"""
代碼功能說明: 測試 /api/v1/chat 的「新增檔案意圖」行為（預設任務工作區根目錄；指定目錄則寫入對應 folder_id）
創建日期: 2025-12-14 11:12:09 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-14 11:12:09 (UTC+8)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import pytest
from fastapi.testclient import TestClient

import api.routers.chat as chat_router
from api.main import app
from services.api.models.file_metadata import FileMetadataCreate
from system.security.models import Permission, User


@dataclass
class _FakeStorage:
    saved: list[dict]

    def save_file(
        self,
        file_content: bytes,
        filename: str,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> tuple[str, str]:
        fid = file_id or "file-123"
        self.saved.append(
            {
                "file_id": fid,
                "filename": filename,
                "task_id": task_id,
                "content": file_content,
            }
        )
        return fid, f"/tmp/{fid}"


@dataclass
class _FakeMetadataService:
    created: list[FileMetadataCreate]

    def create(self, metadata: FileMetadataCreate) -> Any:
        self.created.append(metadata)
        return metadata


class _FakePermissionService:
    def check_task_file_access(self, *, user: User, task_id: str, required_permission: str) -> None:
        return None

    def check_upload_permission(self, *, user: User) -> None:
        return None

    def check_file_access(self, *, user: User, file_id: str, required_permission: str) -> None:
        return None


class _FakeMoE:
    async def chat(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
        return {
            "content": "# Summary\n\nHello world.",
            "_routing": {
                "provider": "ollama",
                "model": "qwen3-coder:30b",
                "strategy": "manual",
                "latency_ms": 12.3,
                "failover_used": False,
            },
        }


@pytest.fixture
def app_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    fake_storage = _FakeStorage(saved=[])
    fake_metadata = _FakeMetadataService(created=[])

    fake_user = User(
        user_id="user-1",
        username="tester",
        email="tester@example.com",
        roles=["user"],
        permissions=[Permission.ALL.value],
        metadata={"tenant_id": "default"},
    )

    app.dependency_overrides[chat_router.get_current_user] = lambda: fake_user

    monkeypatch.setattr(chat_router, "get_moe_manager", lambda: _FakeMoE())
    monkeypatch.setattr(chat_router, "get_storage", lambda: fake_storage)
    monkeypatch.setattr(chat_router, "get_metadata_service", lambda: fake_metadata)
    monkeypatch.setattr(
        chat_router, "get_file_permission_service", lambda: _FakePermissionService()
    )

    client = TestClient(app)
    client._fake_storage = fake_storage  # type: ignore[attr-defined]
    client._fake_metadata = fake_metadata  # type: ignore[attr-defined]
    return client


def test_chat_creates_file_in_workspace_root_when_intent(
    app_client: TestClient,
) -> None:
    resp = app_client.post(
        "/api/v1/chat",
        json={
            "messages": [{"role": "user", "content": "幫我整理以上對話"}],
            "session_id": "s1",
            "task_id": "t1",
            "model_selector": {"mode": "auto"},
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True

    actions = payload["data"].get("actions")
    assert isinstance(actions, list)
    assert actions and actions[0]["type"] == "file_created"
    assert actions[0]["file_id"] == "file-123"
    assert actions[0]["filename"].endswith(".md")
    assert actions[0].get("folder_path") in (None, "")

    fake_storage = app_client._fake_storage  # type: ignore[attr-defined]
    fake_metadata = app_client._fake_metadata  # type: ignore[attr-defined]
    assert fake_storage.saved and fake_storage.saved[0]["task_id"] == "t1"
    assert fake_metadata.created and fake_metadata.created[0].folder_id is None


def test_chat_creates_file_in_specified_folder_path(
    app_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(chat_router, "_ensure_folder_path", lambda **_kwargs: "folder-xyz")

    resp = app_client.post(
        "/api/v1/chat",
        json={
            "messages": [{"role": "user", "content": "請把以上內容整理成 docs/meeting.md"}],
            "session_id": "s2",
            "task_id": "t1",
            "model_selector": {"mode": "auto"},
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True

    actions = payload["data"].get("actions")
    assert isinstance(actions, list)
    assert actions and actions[0]["type"] == "file_created"
    assert actions[0]["filename"] == "meeting.md"
    assert actions[0]["folder_path"] == "docs"
    assert actions[0]["folder_id"] == "folder-xyz"

    fake_metadata = app_client._fake_metadata  # type: ignore[attr-defined]
    assert fake_metadata.created and fake_metadata.created[-1].folder_id == "folder-xyz"
