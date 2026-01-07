# 代碼功能說明: 文件編輯流程集成測試
# 創建日期: 2026-01-06
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-06

"""文件編輯流程集成測試

測試完整的文件編輯流程，包括：
- 編輯 Session 創建
- 編輯指令提交
- 流式 patches 接收
- 修改應用和提交
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from system.security.dependencies import get_current_user
from system.security.models import User


@pytest.fixture
def mock_user():
    """模擬用戶"""
    user = User(
        user_id="test-user-123",
        username="testuser",
        email="test@example.com",
        tenant_id="test-tenant-123",
    )
    return user


@pytest.fixture
def app_client(mock_user):
    """創建測試客戶端"""

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_file_metadata():
    """模擬文件元數據"""
    return MagicMock(
        file_id="file-123",
        filename="test.md",
        file_type="text/markdown",
        storage_path="/path/to/test.md",
        user_id="test-user-123",
        task_id="task-123",
    )


@pytest.fixture
def mock_file_content():
    """模擬文件內容"""
    return "# 測試文件\n\n這是原始內容。\n\n## 子標題\n\n更多內容。"


@pytest.mark.integration
class TestDocumentEditingFlow:
    """文件編輯流程集成測試"""

    @patch("services.api.services.file_metadata_service.FileMetadataService")
    @patch("services.api.services.editing_session_service.get_editing_session_service")
    def test_create_editing_session(
        self,
        mock_session_service,
        mock_metadata_service,
        app_client,
        mock_file_metadata,
    ):
        """測試創建編輯 Session"""
        # Mock 文件元數據服務
        mock_metadata_instance = MagicMock()
        mock_metadata_instance.get.return_value = mock_file_metadata
        mock_metadata_service.return_value = mock_metadata_instance

        # Mock Session 服務
        mock_session = MagicMock()
        mock_session.session_id = "session-123"
        mock_session_service_instance = MagicMock()
        mock_session_service_instance.create_session.return_value = mock_session
        mock_session_service.return_value = mock_session_service_instance

        response = app_client.post(
            "/api/v1/editing/session/start",
            json={"doc_id": "file-123"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "session_id" in data["data"]
        assert data["data"]["session_id"] == "session-123"

    @patch("services.api.services.file_metadata_service.FileMetadataService")
    @patch("services.api.services.editing_session_service.get_editing_session_service")
    @patch("agents.builtin.document_editing.agent.DocumentEditingAgent")
    def test_submit_editing_command(
        self,
        mock_agent_class,
        mock_session_service,
        mock_metadata_service,
        app_client,
        mock_file_metadata,
    ):
        """測試提交編輯指令"""
        # Mock 文件元數據服務
        mock_metadata_instance = MagicMock()
        mock_metadata_instance.get.return_value = mock_file_metadata
        mock_metadata_service.return_value = mock_metadata_instance

        # Mock Session 服務
        mock_session = MagicMock()
        mock_session.session_id = "session-123"
        mock_session.doc_id = "file-123"
        mock_session.user_id = "test-user-123"
        mock_session.tenant_id = "test-tenant-123"
        mock_session_service_instance = MagicMock()
        mock_session_service_instance.get_session.return_value = mock_session
        mock_session_service.return_value = mock_session_service_instance

        # Mock Agent
        mock_agent = AsyncMock()
        from agents.services.protocol.base import AgentServiceResponse

        mock_agent.execute.return_value = AgentServiceResponse(
            task_id="task-123",
            status="completed",
            result={
                "patch_kind": "search_replace",
                "patch_payload": {
                    "patches": [
                        {
                            "search_block": "原始內容",
                            "replace_block": "修改後的內容",
                        }
                    ]
                },
                "summary": "測試摘要",
            },
            error=None,
        )
        mock_agent_class.return_value = mock_agent

        response = app_client.post(
            "/api/v1/editing/command",
            json={
                "session_id": "session-123",
                "command": "修改內容",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "request_id" in data["data"]

    @patch("services.api.services.file_metadata_service.FileMetadataService")
    @patch("services.api.services.editing_session_service.get_editing_session_service")
    def test_streaming_patches(
        self,
        mock_session_service,
        mock_metadata_service,
        app_client,
        mock_file_metadata,
    ):
        """測試流式接收 patches"""
        # Mock 文件元數據服務
        mock_metadata_instance = MagicMock()
        mock_metadata_instance.get.return_value = mock_file_metadata
        mock_metadata_service.return_value = mock_metadata_instance

        # Mock Session 服務
        mock_session = MagicMock()
        mock_session.session_id = "session-123"
        mock_session.doc_id = "file-123"
        mock_session.user_id = "test-user-123"
        mock_session.tenant_id = "test-tenant-123"
        mock_session.metadata = {"request_id": "request-123"}
        mock_session_service_instance = MagicMock()
        mock_session_service_instance.get_session.return_value = mock_session
        mock_session_service.return_value = mock_session_service_instance

        # 測試 SSE 端點
        response = app_client.get(
            "/api/v1/streaming/editing/session-123/stream?request_id=request-123"
        )

        # SSE 響應應該是流式的
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    @patch("services.api.services.file_metadata_service.FileMetadataService")
    def test_file_not_found_error(
        self,
        mock_metadata_service,
        app_client,
    ):
        """測試文件不存在錯誤"""
        # Mock 文件元數據服務返回 None
        mock_metadata_instance = MagicMock()
        mock_metadata_instance.get.return_value = None
        mock_metadata_service.return_value = mock_metadata_instance

        response = app_client.post(
            "/api/v1/editing/session/start",
            json={"doc_id": "non-existent-file"},
        )

        # 應該返回錯誤
        assert response.status_code in [404, 400]

    @patch("services.api.services.file_metadata_service.FileMetadataService")
    @patch("services.api.services.editing_session_service.get_editing_session_service")
    def test_session_not_found_error(
        self,
        mock_session_service,
        mock_metadata_service,
        app_client,
        mock_file_metadata,
    ):
        """測試 Session 不存在錯誤"""
        # Mock 文件元數據服務
        mock_metadata_instance = MagicMock()
        mock_metadata_instance.get.return_value = mock_file_metadata
        mock_metadata_service.return_value = mock_metadata_instance

        # Mock Session 服務返回 None
        mock_session_service_instance = MagicMock()
        mock_session_service_instance.get_session.return_value = None
        mock_session_service.return_value = mock_session_service_instance

        response = app_client.post(
            "/api/v1/editing/command",
            json={
                "session_id": "non-existent-session",
                "command": "測試指令",
            },
        )

        # 應該返回錯誤
        assert response.status_code in [404, 400]

    @patch("services.api.services.file_metadata_service.FileMetadataService")
    @patch("services.api.services.editing_session_service.get_editing_session_service")
    @patch("storage.file_storage.create_storage_from_config")
    def test_complete_editing_flow(
        self,
        mock_storage,
        mock_session_service,
        mock_metadata_service,
        app_client,
        mock_file_metadata,
        mock_file_content,
    ):
        """測試完整編輯流程"""
        # Mock 文件元數據服務
        mock_metadata_instance = MagicMock()
        mock_metadata_instance.get.return_value = mock_file_metadata
        mock_metadata_service.return_value = mock_metadata_instance

        # Mock 存儲服務
        mock_storage_instance = MagicMock()
        mock_storage_instance.read.return_value = mock_file_content.encode("utf-8")
        mock_storage.return_value = mock_storage_instance

        # Mock Session 服務
        mock_session = MagicMock()
        mock_session.session_id = "session-123"
        mock_session.doc_id = "file-123"
        mock_session.user_id = "test-user-123"
        mock_session.tenant_id = "test-tenant-123"
        mock_session.metadata = {}
        mock_session_service_instance = MagicMock()
        mock_session_service_instance.create_session.return_value = mock_session
        mock_session_service_instance.get_session.return_value = mock_session
        mock_session_service.return_value = mock_session_service_instance

        # 1. 創建 Session
        response = app_client.post(
            "/api/v1/editing/session/start",
            json={"doc_id": "file-123"},
        )
        assert response.status_code == 201
        session_data = response.json()
        session_id = session_data["data"]["session_id"]

        # 2. 提交編輯指令（需要 Mock Agent）
        with patch(
            "agents.builtin.document_editing.agent.DocumentEditingAgent"
        ) as mock_agent_class:
            mock_agent = AsyncMock()
            from agents.services.protocol.base import AgentServiceResponse

            mock_agent.execute.return_value = AgentServiceResponse(
                task_id="task-123",
                status="completed",
                result={
                    "patch_kind": "search_replace",
                    "patch_payload": {
                        "patches": [
                            {
                                "search_block": "原始內容",
                                "replace_block": "修改後的內容",
                            }
                        ]
                    },
                    "summary": "測試摘要",
                },
                error=None,
            )
            mock_agent_class.return_value = mock_agent

            response = app_client.post(
                "/api/v1/editing/command",
                json={
                    "session_id": session_id,
                    "command": "修改內容",
                },
            )
            assert response.status_code == 200
            command_data = response.json()
            assert "request_id" in command_data["data"]

            # 3. 測試流式接收（簡化測試，只驗證端點可訪問）
            # 注意：完整的流式測試需要更複雜的 mock
            response = app_client.get(f"/api/v1/streaming/editing/{session_id}/stream")
            assert response.status_code == 200
