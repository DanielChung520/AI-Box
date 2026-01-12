# 代碼功能說明: Document Editing Agent v2.0 API 路由集成測試
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11 15:44:36 (UTC+8)

"""Document Editing Agent v2.0 API 路由集成測試

測試完整的文件操作流程（創建、編輯、刪除、Draft State、Commit & Rollback）。
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


@pytest.fixture
def mock_user():
    """模擬用戶"""
    user = MagicMock()
    user.user_id = "test-user-123"
    user.tenant_id = "test-tenant-456"
    return user


@pytest.fixture
def mock_workspace_integration():
    """模擬 WorkspaceIntegration"""
    with patch("api.routers.document_editing_v2.get_workspace_integration") as mock:
        workspace_integration = MagicMock()
        mock.return_value = workspace_integration
        yield workspace_integration


@pytest.fixture
def mock_agent():
    """模擬 DocumentEditingAgentV2"""
    with patch("api.routers.document_editing_v2.get_agent") as mock:
        agent = MagicMock()
        mock.return_value = agent
        yield agent


class TestFileCreateAPI:
    """測試文件創建 API"""

    @patch("api.routers.document_editing_v2.get_current_user")
    @patch("api.routers.document_editing_v2.get_current_tenant_id")
    def test_create_file_success(self, mock_tenant_id, mock_user, mock_workspace_integration):
        """測試成功創建文件"""
        mock_tenant_id.return_value = "test-tenant-456"
        mock_user.return_value = MagicMock(user_id="test-user-123")

        # 模擬文件元數據
        file_metadata = MagicMock()
        file_metadata.file_id = "file-123"
        file_metadata.storage_path = "data/tasks/task-123/workspace/file-123.md"
        file_metadata.task_id = "task-123"
        file_metadata.folder_id = "task-123_workspace"

        mock_workspace_integration.create_file.return_value = file_metadata

        response = client.post(
            "/api/v1/document-editing-agent/v2/files",
            json={
                "file_name": "test.md",
                "task_id": "task-123",
                "content": "# Test\n\nContent",
                "format": "markdown",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["file_id"] == "file-123"
        assert data["data"]["task_id"] == "task-123"


class TestFileEditAPI:
    """測試文件編輯 API"""

    @patch("api.routers.document_editing_v2.get_current_user")
    @patch("api.routers.document_editing_v2.get_current_tenant_id")
    def test_edit_file_success(self, mock_tenant_id, mock_user, mock_agent):
        """測試成功編輯文件"""
        mock_tenant_id.return_value = "test-tenant-456"
        mock_user.return_value = MagicMock(user_id="test-user-123")

        # 模擬 Agent 響應
        from agents.services.protocol.base import AgentServiceResponse

        mock_response = AgentServiceResponse(
            task_id="task-123",
            status="completed",
            result={
                "patch_id": "patch-123",
                "intent_id": "intent-123",
                "block_patch": {"operations": []},
                "text_patch": "--- a/test.md\n+++ b/test.md\n",
                "preview": "Updated content",
                "audit_info": {},
            },
            error=None,
            metadata={},
        )

        mock_agent.execute = MagicMock(return_value=mock_response)

        response = client.post(
            "/api/v1/document-editing-agent/v2/edit",
            json={
                "document_context": {
                    "doc_id": "doc-123",
                    "file_path": "data/tasks/task-123/workspace/file-123.md",
                    "task_id": "task-123",
                    "user_id": "test-user-123",
                },
                "edit_intent": {
                    "intent_id": "intent-123",
                    "intent_type": "update",
                    "target_selector": {
                        "type": "heading",
                        "selector": {"text": "標題", "level": 1},
                    },
                    "action": {"mode": "update", "content": "Updated content"},
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["patch_id"] == "patch-123"


class TestFileDeleteAPI:
    """測試文件刪除 API"""

    @patch("api.routers.document_editing_v2.get_current_user")
    @patch("api.routers.document_editing_v2.get_current_tenant_id")
    @patch("api.routers.document_editing_v2.get_metadata_service")
    def test_delete_file_success(
        self, mock_metadata_service, mock_tenant_id, mock_user, mock_workspace_integration
    ):
        """測試成功刪除文件"""
        mock_tenant_id.return_value = "test-tenant-456"
        mock_user.return_value = MagicMock(user_id="test-user-123")

        # 模擬文件元數據
        file_metadata = MagicMock()
        file_metadata.user_id = "test-user-123"
        mock_metadata_service.return_value.get.return_value = file_metadata

        mock_workspace_integration.delete_file.return_value = True

        response = client.delete("/api/v1/document-editing-agent/v2/files/file-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted"] is True


class TestDraftStateAPI:
    """測試 Draft State API"""

    @patch("api.routers.document_editing_v2.get_current_user")
    @patch("api.routers.document_editing_v2.get_current_tenant_id")
    def test_save_draft_state_success(self, mock_tenant_id, mock_user):
        """測試成功保存 Draft State"""
        mock_tenant_id.return_value = "test-tenant-456"
        mock_user.return_value = MagicMock(user_id="test-user-123")

        response = client.post(
            "/api/v1/document-editing-agent/v2/draft",
            json={
                "doc_id": "doc-123",
                "content": "Draft content",
                "patches": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["doc_id"] == "doc-123"

    @patch("api.routers.document_editing_v2.get_current_user")
    @patch("api.routers.document_editing_v2.get_current_tenant_id")
    def test_get_draft_state_success(self, mock_tenant_id, mock_user):
        """測試成功讀取 Draft State"""
        mock_tenant_id.return_value = "test-tenant-456"
        mock_user.return_value = MagicMock(user_id="test-user-123")

        # 先保存 Draft State
        client.post(
            "/api/v1/document-editing-agent/v2/draft",
            json={
                "doc_id": "doc-123",
                "content": "Draft content",
                "patches": [],
            },
        )

        # 讀取 Draft State
        response = client.get("/api/v1/document-editing-agent/v2/draft/doc-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["doc_id"] == "doc-123"
        assert data["data"]["content"] == "Draft content"


class TestCommitRollbackAPI:
    """測試 Commit & Rollback API"""

    @patch("api.routers.document_editing_v2.get_current_user")
    @patch("api.routers.document_editing_v2.get_current_tenant_id")
    @patch("api.routers.document_editing_v2.get_metadata_service")
    def test_commit_success(
        self, mock_metadata_service, mock_tenant_id, mock_user, mock_workspace_integration
    ):
        """測試成功提交變更"""
        mock_tenant_id.return_value = "test-tenant-456"
        mock_user.return_value = MagicMock(user_id="test-user-123")

        # 先保存 Draft State
        client.post(
            "/api/v1/document-editing-agent/v2/draft",
            json={
                "doc_id": "doc-123",
                "content": "Draft content",
                "patches": [],
            },
        )

        # 模擬文件元數據
        file_metadata = MagicMock()
        file_metadata.storage_path = "data/tasks/task-123/workspace/file-123.md"
        mock_metadata_service.return_value.get.return_value = file_metadata

        response = client.post(
            "/api/v1/document-editing-agent/v2/commit",
            json={
                "doc_id": "doc-123",
                "content": "Final content",
                "summary": "Test commit",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "new_version_id" in data["data"]

    @patch("api.routers.document_editing_v2.get_current_user")
    @patch("api.routers.document_editing_v2.get_current_tenant_id")
    @patch("api.routers.document_editing_v2.get_metadata_service")
    def test_rollback_success(
        self, mock_metadata_service, mock_tenant_id, mock_user, mock_workspace_integration
    ):
        """測試成功回滾版本"""
        mock_tenant_id.return_value = "test-tenant-456"
        mock_user.return_value = MagicMock(user_id="test-user-123")

        # 先提交一個版本
        commit_response = client.post(
            "/api/v1/document-editing-agent/v2/commit",
            json={
                "doc_id": "doc-123",
                "content": "Version 1",
                "summary": "First commit",
            },
        )
        version_id = commit_response.json()["data"]["new_version_id"]

        # 模擬文件元數據
        file_metadata = MagicMock()
        file_metadata.storage_path = "data/tasks/task-123/workspace/file-123.md"
        mock_metadata_service.return_value.get.return_value = file_metadata

        # 回滾到該版本
        response = client.post(
            "/api/v1/document-editing-agent/v2/rollback",
            json={
                "doc_id": "doc-123",
                "target_version_id": version_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["rolled_back_to_version_id"] == version_id
