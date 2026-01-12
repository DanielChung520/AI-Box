# 代碼功能說明: 任務工作區整合測試
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""任務工作區整合測試

測試文件創建、讀取、刪除在任務工作區中的正確性。
"""

from unittest.mock import MagicMock, patch

import pytest

from agents.core.editing_v2.workspace_integration import WorkspaceIntegration


@pytest.fixture
def workspace_integration():
    """創建 WorkspaceIntegration 實例（使用 Mock 服務）"""
    task_workspace_service = MagicMock()
    file_metadata_service = MagicMock()
    return WorkspaceIntegration(
        task_workspace_service=task_workspace_service,
        file_metadata_service=file_metadata_service,
    )


class TestWorkspaceIntegration:
    """任務工作區整合測試類"""

    def test_create_file_in_workspace(self, workspace_integration):
        """測試在任務工作區創建文件"""
        task_id = "task-123"
        file_name = "test.md"
        content = "# Test\n\nContent"
        user_id = "user-456"

        # Mock 文件元數據
        file_metadata = MagicMock()
        file_metadata.file_id = "file-123"
        file_metadata.storage_path = f"data/tasks/{task_id}/workspace/file-123.md"
        file_metadata.task_id = task_id
        file_metadata.folder_id = f"{task_id}_workspace"

        workspace_integration.file_metadata_service.create_file_metadata.return_value = (
            file_metadata
        )

        # 創建文件
        result = workspace_integration.create_file(
            file_name=file_name,
            content=content,
            task_id=task_id,
            user_id=user_id,
        )

        # 驗證結果
        assert result is not None
        assert result.file_id == "file-123"
        assert result.task_id == task_id
        assert result.folder_id == f"{task_id}_workspace"
        assert f"data/tasks/{task_id}/workspace" in result.storage_path

        # 驗證調用了正確的服務方法
        workspace_integration.file_metadata_service.create_file_metadata.assert_called_once()

    def test_get_file_content_from_workspace(self, workspace_integration):
        """測試從任務工作區讀取文件"""
        file_id = "file-123"
        task_id = "task-123"
        expected_content = "# Test\n\nContent"

        # Mock 文件元數據
        file_metadata = MagicMock()
        file_metadata.file_id = file_id
        file_metadata.storage_path = f"data/tasks/{task_id}/workspace/{file_id}.md"
        file_metadata.task_id = task_id

        workspace_integration.file_metadata_service.get_file_metadata.return_value = file_metadata

        # Mock 文件讀取
        with patch("agents.core.editing_v2.workspace_integration.Path.read_text") as mock_read:
            mock_read.return_value = expected_content

            # 讀取文件
            content = workspace_integration.get_file_content(file_id=file_id, task_id=task_id)

            # 驗證結果
            assert content == expected_content

    def test_get_file_content_file_not_found(self, workspace_integration):
        """測試文件不存在的情況"""
        file_id = "file-not-found"
        task_id = "task-123"

        # Mock 文件元數據不存在
        workspace_integration.file_metadata_service.get_file_metadata.return_value = None

        # 讀取文件
        content = workspace_integration.get_file_content(file_id=file_id, task_id=task_id)

        # 驗證結果
        assert content is None

    def test_delete_file_from_workspace(self, workspace_integration):
        """測試從任務工作區刪除文件"""
        file_id = "file-123"
        task_id = "task-123"
        user_id = "user-456"

        # Mock 文件元數據
        file_metadata = MagicMock()
        file_metadata.file_id = file_id
        file_metadata.storage_path = f"data/tasks/{task_id}/workspace/{file_id}.md"
        file_metadata.task_id = task_id

        workspace_integration.file_metadata_service.get_file_metadata.return_value = file_metadata
        workspace_integration.file_metadata_service.delete_file_metadata.return_value = True

        # Mock 文件刪除
        with patch("agents.core.editing_v2.workspace_integration.Path.unlink") as mock_unlink:
            mock_unlink.return_value = None

            # 刪除文件
            result = workspace_integration.delete_file(
                file_id=file_id, task_id=task_id, user_id=user_id
            )

            # 驗證結果
            assert result is True

            # 驗證調用了正確的服務方法
            workspace_integration.file_metadata_service.delete_file_metadata.assert_called_once()

    def test_file_path_generation(self, workspace_integration):
        """測試文件路徑生成正確性"""
        task_id = "task-123"
        file_id = "file-123"
        file_name = "test.md"

        # Mock 文件元數據
        file_metadata = MagicMock()
        file_metadata.file_id = file_id
        file_metadata.storage_path = f"data/tasks/{task_id}/workspace/{file_id}.md"
        file_metadata.task_id = task_id
        file_metadata.folder_id = f"{task_id}_workspace"

        workspace_integration.file_metadata_service.create_file_metadata.return_value = (
            file_metadata
        )

        # 創建文件
        result = workspace_integration.create_file(
            file_name=file_name,
            content="# Test",
            task_id=task_id,
            user_id="user-456",
        )

        # 驗證文件路徑
        assert result.storage_path.startswith(f"data/tasks/{task_id}/workspace/")
        assert result.storage_path.endswith(".md")
        assert result.folder_id == f"{task_id}_workspace"
