"""
代碼功能說明: 文件助手 Docs Editing/Generation API 測試（preview/apply/rollback）
創建日期: 2025-12-14 10:53:05 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-14 10:53:05 (UTC+8)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import pytest
from fastapi.testclient import TestClient

from api.main import app
from system.security.dependencies import get_current_user
from system.security.models import Permission, User


class _FakeStorage:
    def __init__(self) -> None:
        self._store: Dict[str, bytes] = {}

    def save_file(
        self,
        file_content: bytes,
        filename: str,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ):
        _ = filename
        _ = task_id
        if file_id is None:
            file_id = f"f_{len(self._store)+1}"
        self._store[file_id] = file_content
        return file_id, f"mem://{file_id}"

    def read_file(
        self,
        file_id: str,
        task_id: Optional[str] = None,
        metadata_storage_path: Optional[str] = None,
    ):
        _ = task_id
        _ = metadata_storage_path
        return self._store.get(file_id)


@dataclass
class _Meta:
    file_id: str
    filename: str
    file_type: str
    file_size: int
    user_id: str
    task_id: str
    folder_id: Optional[str]
    storage_path: str
    tags: list[str]
    description: Optional[str]
    custom_metadata: Dict[str, Any]


class _FakeMetadataService:
    def __init__(self) -> None:
        self._by_id: Dict[str, _Meta] = {}

    def get(self, file_id: str) -> Optional[_Meta]:
        return self._by_id.get(file_id)

    def create(self, metadata: Any) -> Any:
        doc = _Meta(
            file_id=metadata.file_id,
            filename=metadata.filename,
            file_type=metadata.file_type,
            file_size=metadata.file_size,
            user_id=metadata.user_id,
            task_id=metadata.task_id,
            folder_id=metadata.folder_id,
            storage_path=metadata.storage_path,
            tags=list(metadata.tags or []),
            description=metadata.description,
            custom_metadata=dict(metadata.custom_metadata or {}),
        )
        self._by_id[metadata.file_id] = doc
        return doc

    def update(self, file_id: str, update: Any) -> Optional[_Meta]:
        doc = self._by_id.get(file_id)
        if doc is None:
            return None
        update_dict = update.model_dump(exclude_unset=True)
        if "custom_metadata" in update_dict:
            doc.custom_metadata = dict(update.custom_metadata or {})
        return doc


class _FakePermissionService:
    def __init__(self, *, allow_update: bool = True) -> None:
        self.allow_update = allow_update

    def check_file_access(
        self,
        *,
        user: User,
        file_id: str,
        required_permission: str = Permission.FILE_READ.value,
    ):
        _ = user
        _ = file_id
        if (
            required_permission == Permission.FILE_UPDATE.value
            and not self.allow_update
        ):
            raise Exception("forbidden")
        return True

    def check_upload_permission(self, user: User) -> bool:
        _ = user
        return True

    def check_task_file_access(
        self,
        *,
        user: User,
        task_id: str,
        required_permission: str = Permission.FILE_READ.value,
    ) -> bool:
        _ = user
        _ = task_id
        _ = required_permission
        return True


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

    from api.routers import docs_editing as docs_router

    fake_storage = _FakeStorage()
    fake_meta = _FakeMetadataService()
    fake_perm = _FakePermissionService(allow_update=True)

    monkeypatch.setattr(docs_router, "get_storage", lambda: fake_storage, raising=True)
    monkeypatch.setattr(
        docs_router, "get_metadata_service", lambda: fake_meta, raising=True
    )
    monkeypatch.setattr(
        docs_router, "get_file_permission_service", lambda: fake_perm, raising=True
    )

    # mock LLM output
    from llm.moe.moe_manager import LLMMoEManager

    async def _fake_generate(
        self: LLMMoEManager, prompt: str, **kwargs: Any
    ) -> Dict[str, Any]:
        _ = self
        _ = kwargs
        if "RFC6902 JSON Patch" in prompt:
            return {"content": '[{"op":"replace","path":"/title","value":"New Title"}]'}
        if "JSON 文件產生器" in prompt:
            return {"content": '{"title": "Generated"}'}
        return {
            "content": """--- a/file
+++ b/file
@@ -1,2 +1,2 @@
 hello
-world
+cursor
"""
        }

    monkeypatch.setattr(LLMMoEManager, "generate", _fake_generate, raising=True)

    # seed one file
    file_id, storage_path = fake_storage.save_file(
        b"hello\nworld\n", filename="note.md", file_id="f1", task_id="t1"
    )
    from services.api.models.file_metadata import FileMetadataCreate

    fake_meta.create(
        FileMetadataCreate(
            file_id=file_id,
            filename="note.md",
            file_type="text/markdown",
            file_size=11,
            user_id="u_test",
            task_id="t1",
            folder_id=None,
            storage_path=storage_path,
            tags=[],
            description=None,
            custom_metadata={"doc_version": 1, "doc_versions": []},
            status="uploaded",
            processing_status=None,
            chunk_count=None,
            vector_count=None,
            kg_status=None,
        )
    )

    return TestClient(app)


def test_doc_edit_preview_apply_and_versions(app_client: TestClient) -> None:
    r = app_client.post(
        "/api/v1/docs/edits",
        json={"file_id": "f1", "instruction": "replace world"},
        headers={"X-Tenant-ID": "default"},
    )
    assert r.status_code == 202
    request_id = r.json()["data"]["request_id"]

    state = None
    for _ in range(30):
        s = app_client.get(
            f"/api/v1/docs/edits/{request_id}", headers={"X-Tenant-ID": "default"}
        )
        assert s.status_code == 200
        state = s.json()["data"]
        if state["status"] == "succeeded":
            break
    assert state is not None
    assert state["status"] == "succeeded"
    assert state["preview"]["patch_kind"] == "unified_diff"

    a = app_client.post(
        f"/api/v1/docs/edits/{request_id}/apply", headers={"X-Tenant-ID": "default"}
    )
    assert a.status_code == 200
    assert a.json()["data"]["new_version"] == 2

    v = app_client.get(
        "/api/v1/docs/files/f1/versions", headers={"X-Tenant-ID": "default"}
    )
    assert v.status_code == 200
    body = v.json()["data"]
    assert body["doc_version"] == 2
    assert len(body["versions"]) == 1
    assert body["versions"][0]["version"] == 1


def test_doc_edit_base_version_mismatch(app_client: TestClient) -> None:
    r = app_client.post(
        "/api/v1/docs/edits",
        json={"file_id": "f1", "instruction": "replace world"},
        headers={"X-Tenant-ID": "default"},
    )
    request_id = r.json()["data"]["request_id"]
    for _ in range(30):
        s = app_client.get(
            f"/api/v1/docs/edits/{request_id}", headers={"X-Tenant-ID": "default"}
        )
        if s.json()["data"]["status"] == "succeeded":
            break
    app_client.post(
        f"/api/v1/docs/edits/{request_id}/apply", headers={"X-Tenant-ID": "default"}
    )

    r2 = app_client.post(
        "/api/v1/docs/edits",
        json={"file_id": "f1", "instruction": "x", "base_version": 1},
        headers={"X-Tenant-ID": "default"},
    )
    assert r2.status_code == 409


def test_doc_rollback(app_client: TestClient) -> None:
    r = app_client.post(
        "/api/v1/docs/edits",
        json={"file_id": "f1", "instruction": "replace world"},
        headers={"X-Tenant-ID": "default"},
    )
    request_id = r.json()["data"]["request_id"]
    for _ in range(30):
        s = app_client.get(
            f"/api/v1/docs/edits/{request_id}", headers={"X-Tenant-ID": "default"}
        )
        if s.json()["data"]["status"] == "succeeded":
            break
    app_client.post(
        f"/api/v1/docs/edits/{request_id}/apply", headers={"X-Tenant-ID": "default"}
    )

    rb = app_client.post(
        "/api/v1/docs/files/f1/rollback?to_version=1",
        headers={"X-Tenant-ID": "default"},
    )
    assert rb.status_code == 200


def test_doc_generation_preview_apply(app_client: TestClient) -> None:
    r = app_client.post(
        "/api/v1/docs/generations",
        json={
            "task_id": "t1",
            "filename": "new.json",
            "doc_format": "json",
            "instruction": "generate title",
        },
        headers={"X-Tenant-ID": "default"},
    )
    assert r.status_code == 202
    request_id = r.json()["data"]["request_id"]

    state = None
    for _ in range(30):
        s = app_client.get(
            f"/api/v1/docs/generations/{request_id}",
            headers={"X-Tenant-ID": "default"},
        )
        assert s.status_code == 200
        state = s.json()["data"]
        if state["status"] == "succeeded":
            break
    assert state is not None
    assert state["status"] == "succeeded"
    assert "Generated" in state["preview"]["content"]

    a = app_client.post(
        f"/api/v1/docs/generations/{request_id}/apply",
        headers={"X-Tenant-ID": "default"},
    )
    assert a.status_code == 200
    assert a.json()["data"]["file_id"]
