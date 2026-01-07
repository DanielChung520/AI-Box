# 代碼功能說明: Document Editing Agent 單元測試
# 創建日期: 2026-01-06
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-06

"""Document Editing Agent 單元測試

測試文件編輯 Agent 的核心功能，包括：
- execute() 方法
- health_check() 方法
- get_capabilities() 方法
- 文件內容讀取
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.builtin.document_editing.agent import DocumentEditingAgent
from agents.services.protocol.base import AgentServiceRequest, AgentServiceStatus


@pytest.fixture
def document_editing_agent():
    """創建 DocumentEditingAgent 實例"""
    return DocumentEditingAgent()


@pytest.fixture
def sample_request():
    """創建示例 AgentServiceRequest"""
    return AgentServiceRequest(
        task_id="task-123",
        task_type="document_editing",
        task_data={
            "command": "在開頭添加一個標題",
            "doc_id": "file-123",
            "format": "md",
            "cursor_context": {"position": 0},
        },
        context={"session_id": "session-123"},
        metadata={"created_via": "test"},
    )


@pytest.fixture
def mock_file_content():
    """模擬文件內容"""
    return "# 原始標題\n\n這是原始內容。"


@pytest.mark.asyncio
class TestDocumentEditingAgent:
    """Document Editing Agent 測試類"""

    async def test_health_check_available(self, document_editing_agent):
        """測試健康檢查 - 可用狀態"""
        status = await document_editing_agent.health_check()
        assert status == AgentServiceStatus.AVAILABLE

    async def test_get_capabilities(self, document_editing_agent):
        """測試獲取服務能力"""
        capabilities = await document_editing_agent.get_capabilities()
        assert isinstance(capabilities, dict)
        assert capabilities["name"] == "Document Editing Agent"
        assert capabilities["agent_id"] == "document-editing-agent"
        assert capabilities["agent_type"] == "document_editing"
        assert "document_editing" in capabilities["capabilities"]
        assert "file_editing" in capabilities["capabilities"]
        assert "markdown_editing" in capabilities["capabilities"]
        assert "streaming_editing" in capabilities["capabilities"]

    async def test_execute_missing_command(self, document_editing_agent):
        """測試執行 - 缺少 command 參數"""
        request = AgentServiceRequest(
            task_id="task-123",
            task_type="document_editing",
            task_data={"doc_id": "file-123"},
        )
        response = await document_editing_agent.execute(request)
        assert response.status == "error"
        assert "command" in response.error.lower()

    async def test_execute_missing_doc_id(self, document_editing_agent):
        """測試執行 - 缺少 doc_id 參數"""
        request = AgentServiceRequest(
            task_id="task-123",
            task_type="document_editing",
            task_data={"command": "測試指令"},
        )
        response = await document_editing_agent.execute(request)
        assert response.status == "error"
        assert "doc_id" in response.error.lower()

    @patch("agents.builtin.document_editing.agent.FileMetadataService")
    @patch("agents.builtin.document_editing.agent.create_storage_from_config")
    @patch("agents.builtin.document_editing.agent.get_config_section")
    async def test_execute_file_not_found(
        self,
        mock_get_config,
        mock_create_storage,
        mock_metadata_service,
        document_editing_agent,
        sample_request,
    ):
        """測試執行 - 文件不存在"""
        # Mock 文件元數據服務
        mock_metadata = MagicMock()
        mock_metadata.get.return_value = None
        mock_metadata_service.return_value = mock_metadata

        response = await document_editing_agent.execute(sample_request)
        assert response.status == "error"
        assert "file" in response.error.lower()

    @patch("agents.builtin.document_editing.agent.FileMetadataService")
    @patch("agents.builtin.document_editing.agent.create_storage_from_config")
    @patch("agents.builtin.document_editing.agent.get_config_section")
    @patch("agents.builtin.document_editing.agent.DocumentEditingService")
    async def test_execute_success(
        self,
        mock_editing_service_class,
        mock_get_config,
        mock_create_storage,
        mock_metadata_service,
        document_editing_agent,
        sample_request,
        mock_file_content,
    ):
        """測試執行 - 成功情況"""
        # Mock 文件元數據
        mock_file_metadata = MagicMock()
        mock_file_metadata.storage_path = "/path/to/file.md"
        mock_metadata_instance = MagicMock()
        mock_metadata_instance.get.return_value = mock_file_metadata
        mock_metadata_service.return_value = mock_metadata_instance

        # Mock 存儲服務
        mock_storage = MagicMock()
        mock_storage.read.return_value = mock_file_content.encode("utf-8")
        mock_create_storage.return_value = mock_storage

        # Mock 配置
        mock_get_config.return_value = {}

        # Mock DocumentEditingService
        mock_editing_service = AsyncMock()
        mock_editing_service.generate_editing_patches.return_value = (
            "search_replace",
            {"patches": [{"search_block": "原始", "replace_block": "修改後"}]},
            "測試摘要",
        )
        mock_editing_service_class.return_value = mock_editing_service
        document_editing_agent.editing_service = mock_editing_service

        response = await document_editing_agent.execute(sample_request)

        assert response.status == "completed"
        assert response.result is not None
        assert response.result["patch_kind"] == "search_replace"
        assert response.result["doc_id"] == "file-123"
        assert response.result["summary"] == "測試摘要"
        assert response.error is None

    @patch("agents.builtin.document_editing.agent.FileMetadataService")
    @patch("agents.builtin.document_editing.agent.create_storage_from_config")
    @patch("agents.builtin.document_editing.agent.get_config_section")
    @patch("agents.builtin.document_editing.agent.DocumentEditingService")
    async def test_execute_with_cursor_context(
        self,
        mock_editing_service_class,
        mock_get_config,
        mock_create_storage,
        mock_metadata_service,
        document_editing_agent,
        mock_file_content,
    ):
        """測試執行 - 帶游標上下文"""
        request = AgentServiceRequest(
            task_id="task-123",
            task_type="document_editing",
            task_data={
                "command": "在游標位置插入內容",
                "doc_id": "file-123",
                "format": "md",
                "cursor_context": {"position": 10, "line": 2},
            },
        )

        # Mock 文件元數據
        mock_file_metadata = MagicMock()
        mock_file_metadata.storage_path = "/path/to/file.md"
        mock_metadata_instance = MagicMock()
        mock_metadata_instance.get.return_value = mock_file_metadata
        mock_metadata_service.return_value = mock_metadata_instance

        # Mock 存儲服務
        mock_storage = MagicMock()
        mock_storage.read.return_value = mock_file_content.encode("utf-8")
        mock_create_storage.return_value = mock_storage

        # Mock 配置
        mock_get_config.return_value = {}

        # Mock DocumentEditingService
        mock_editing_service = AsyncMock()
        mock_editing_service.generate_editing_patches.return_value = (
            "search_replace",
            {"patches": []},
            "摘要",
        )
        mock_editing_service_class.return_value = mock_editing_service
        document_editing_agent.editing_service = mock_editing_service

        response = await document_editing_agent.execute(request)

        assert response.status == "completed"
        # 驗證游標位置被傳遞給 editing_service
        mock_editing_service.generate_editing_patches.assert_called_once()
        call_args = mock_editing_service.generate_editing_patches.call_args
        assert call_args[1]["cursor_position"] == 10

    async def test_get_file_content_success(self, document_editing_agent):
        """測試獲取文件內容 - 成功"""
        with patch(
            "agents.builtin.document_editing.agent.FileMetadataService"
        ) as mock_metadata_service, patch(
            "agents.builtin.document_editing.agent.create_storage_from_config"
        ) as mock_create_storage, patch(
            "agents.builtin.document_editing.agent.get_config_section"
        ) as mock_get_config:
            # Mock 文件元數據
            mock_file_metadata = MagicMock()
            mock_file_metadata.storage_path = "/path/to/file.md"
            mock_metadata_instance = MagicMock()
            mock_metadata_instance.get.return_value = mock_file_metadata
            mock_metadata_service.return_value = mock_metadata_instance

            # Mock 存儲服務
            mock_storage = MagicMock()
            mock_storage.read.return_value = b"# Test Content"
            mock_create_storage.return_value = mock_storage

            # Mock 配置
            mock_get_config.return_value = {}

            content = await document_editing_agent._get_file_content("file-123")
            assert content == "# Test Content"

    async def test_get_file_content_not_found(self, document_editing_agent):
        """測試獲取文件內容 - 文件不存在"""
        with patch(
            "agents.builtin.document_editing.agent.FileMetadataService"
        ) as mock_metadata_service:
            mock_metadata_instance = MagicMock()
            mock_metadata_instance.get.return_value = None
            mock_metadata_service.return_value = mock_metadata_instance

            content = await document_editing_agent._get_file_content("file-123")
            assert content is None

    async def test_execute_exception_handling(self, document_editing_agent, sample_request):
        """測試執行 - 異常處理"""
        # 模擬異常情況
        with patch.object(
            document_editing_agent, "_get_file_content", side_effect=Exception("測試異常")
        ):
            response = await document_editing_agent.execute(sample_request)
            assert response.status == "error"
            assert "測試異常" in response.error
