# 代碼功能說明: 資料夾元數據服務單元測試
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""資料夾元數據服務單元測試"""

import uuid

import pytest

from services.api.services.folder_metadata_service import FolderMetadataService


@pytest.fixture
def folder_service():
    """創建資料夾元數據服務實例"""
    return FolderMetadataService()


@pytest.fixture
def sample_folder_id():
    """生成唯一的測試資料夾 ID"""
    return f"test_folder_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def sample_task_id():
    """生成唯一的測試任務 ID"""
    return f"test_task_{uuid.uuid4().hex[:8]}"


class TestFolderMetadataService:
    """資料夾元數據服務測試"""

    def test_create_folder(
        self, folder_service: FolderMetadataService, sample_folder_id: str, sample_task_id: str
    ):
        """測試創建資料夾"""
        folder = folder_service.create(
            folder_id=sample_folder_id,
            folder_name="Test Folder",
            task_id=sample_task_id,
            user_id="test_user",
            description="Test folder description",
        )

        assert folder is not None
        assert folder.get("folder_id") == sample_folder_id
        assert folder.get("folder_name") == "Test Folder"
        assert folder.get("task_id") == sample_task_id
        assert folder.get("user_id") == "test_user"
        assert folder.get("description") == "Test folder description"
        assert "created_at" in folder
        assert "updated_at" in folder

    def test_create_duplicate_folder(
        self, folder_service: FolderMetadataService, sample_folder_id: str, sample_task_id: str
    ):
        """測試創建重複資料夾（應該返回現有資料夾）"""
        # 創建第一個資料夾
        folder1 = folder_service.create(
            folder_id=sample_folder_id,
            folder_name="First Folder",
            task_id=sample_task_id,
            user_id="test_user",
        )

        # 嘗試創建同樣 ID 的資料夾
        folder2 = folder_service.create(
            folder_id=sample_folder_id,
            folder_name="Second Folder",
            task_id=sample_task_id,
            user_id="test_user",
        )

        # 應該返回第一個資料夾（不應該覆蓋）
        assert folder1.get("folder_id") == folder2.get("folder_id")
        assert folder1.get("folder_name") == folder2.get("folder_name")

    def test_get_folder(
        self, folder_service: FolderMetadataService, sample_folder_id: str, sample_task_id: str
    ):
        """測試獲取資料夾"""
        # 創建資料夾
        folder_service.create(
            folder_id=sample_folder_id,
            folder_name="Get Test Folder",
            task_id=sample_task_id,
            user_id="test_user",
        )

        # 獲取資料夾
        folder = folder_service.get(sample_folder_id)

        assert folder is not None
        assert folder.get("folder_id") == sample_folder_id
        assert folder.get("folder_name") == "Get Test Folder"

    def test_get_nonexistent_folder(self, folder_service: FolderMetadataService):
        """測試獲取不存在的資料夾"""
        folder = folder_service.get("nonexistent_folder_123")
        assert folder is None

    def test_update_folder(
        self, folder_service: FolderMetadataService, sample_folder_id: str, sample_task_id: str
    ):
        """測試更新資料夾"""
        # 創建資料夾
        folder_service.create(
            folder_id=sample_folder_id,
            folder_name="Original Name",
            task_id=sample_task_id,
            user_id="test_user",
        )

        # 更新資料夾
        updated = folder_service.update(
            folder_id=sample_folder_id,
            folder_name="Updated Name",
            description="Updated description",
        )

        assert updated is not None
        assert updated.get("folder_name") == "Updated Name"
        assert updated.get("description") == "Updated description"

    def test_update_nonexistent_folder(self, folder_service: FolderMetadataService):
        """測試更新不存在的資料夾"""
        updated = folder_service.update(
            folder_id="nonexistent_folder_123",
            folder_name="New Name",
        )
        assert updated is None

    def test_delete_folder(
        self, folder_service: FolderMetadataService, sample_folder_id: str, sample_task_id: str
    ):
        """測試刪除資料夾"""
        # 創建資料夾
        folder_service.create(
            folder_id=sample_folder_id,
            folder_name="Delete Test Folder",
            task_id=sample_task_id,
            user_id="test_user",
        )

        # 刪除資料夾
        result = folder_service.delete(sample_folder_id)
        assert result is True

        # 驗證資料夾已刪除
        folder = folder_service.get(sample_folder_id)
        assert folder is None

    def test_delete_nonexistent_folder(self, folder_service: FolderMetadataService):
        """測試刪除不存在的資料夾"""
        result = folder_service.delete("nonexistent_folder_123")
        assert result is False

    def test_list_folders_by_task_id(self, folder_service: FolderMetadataService):
        """測試按任務 ID 列出資料夾"""
        task_id = f"list_test_task_{uuid.uuid4().hex[:8]}"

        # 創建多個資料夾
        folder1_id = f"list_folder_1_{uuid.uuid4().hex[:4]}"
        folder2_id = f"list_folder_2_{uuid.uuid4().hex[:4]}"

        folder_service.create(
            folder_id=folder1_id,
            folder_name="List Folder 1",
            task_id=task_id,
            user_id="test_user",
        )
        folder_service.create(
            folder_id=folder2_id,
            folder_name="List Folder 2",
            task_id=task_id,
            user_id="test_user",
        )

        # 列出任務下的所有資料夾
        folders = folder_service.list(task_id=task_id)

        assert len(folders) >= 2
        folder_ids = [f.get("folder_id") for f in folders]
        assert folder1_id in folder_ids
        assert folder2_id in folder_ids

    def test_list_folders_by_user_id(self, folder_service: FolderMetadataService):
        """測試按用戶 ID 列出資料夾"""
        user_id = f"list_test_user_{uuid.uuid4().hex[:8]}"

        # 創建資料夾
        folder_id = f"list_user_folder_{uuid.uuid4().hex[:4]}"
        folder_service.create(
            folder_id=folder_id,
            folder_name="User List Folder",
            task_id="any_task",
            user_id=user_id,
        )

        # 列出用戶的所有資料夾
        folders = folder_service.list(user_id=user_id)

        assert len(folders) >= 1
        folder_ids = [f.get("folder_id") for f in folders]
        assert folder_id in folder_ids

    def test_delete_by_task_id(self, folder_service: FolderMetadataService):
        """測試按任務 ID 刪除所有資料夾"""
        task_id = f"delete_task_{uuid.uuid4().hex[:8]}"

        # 創建多個資料夾
        folder_ids = []
        for i in range(3):
            folder_id = f"delete_task_folder_{i}_{uuid.uuid4().hex[:4]}"
            folder_service.create(
                folder_id=folder_id,
                folder_name=f"Delete Task Folder {i}",
                task_id=task_id,
                user_id="test_user",
            )
            folder_ids.append(folder_id)

        # 刪除任務下的所有資料夾
        deleted_count = folder_service.delete_by_task_id(task_id)

        assert deleted_count >= 3

        # 驗證所有資料夾已刪除
        for folder_id in folder_ids:
            folder = folder_service.get(folder_id)
            assert folder is None

    def test_folder_with_parent(self, folder_service: FolderMetadataService):
        """測試創建帶父資料夾的資料夾"""
        parent_folder_id = f"parent_{uuid.uuid4().hex[:8]}"
        child_folder_id = f"child_{uuid.uuid4().hex[:8]}"
        task_id = f"nested_task_{uuid.uuid4().hex[:8]}"

        # 創建父資料夾
        parent = folder_service.create(
            folder_id=parent_folder_id,
            folder_name="Parent Folder",
            task_id=task_id,
            user_id="test_user",
        )

        # 創建子資料夾
        child = folder_service.create(
            folder_id=child_folder_id,
            folder_name="Child Folder",
            task_id=task_id,
            user_id="test_user",
            parent_folder_id=parent_folder_id,
        )

        assert parent is not None
        assert child is not None
        assert child.get("parent_folder_id") == parent_folder_id
