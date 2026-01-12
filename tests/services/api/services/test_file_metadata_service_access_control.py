# 代碼功能說明: 文件元數據服務訪問控制集成測試
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""文件元數據服務訪問控制集成測試"""

from datetime import datetime

import pytest

from services.api.models.data_classification import DataClassification
from services.api.models.file_access_control import FileAccessControl, FileAccessLevel
from services.api.models.file_metadata import FileMetadataCreate, FileMetadataUpdate
from services.api.services.file_metadata_service import FileMetadataService


@pytest.fixture
def metadata_service():
    """創建文件元數據服務實例"""
    return FileMetadataService()


@pytest.fixture
def sample_file_metadata_create():
    """創建示例文件元數據"""
    return FileMetadataCreate(
        file_id="test_file_123",
        filename="test.txt",
        file_type="text/plain",
        file_size=1024,
        user_id="user123",
        task_id="task123",
        storage_path="/path/to/file",
    )


class TestFileMetadataServiceAccessControl:
    """文件元數據服務訪問控制測試"""

    def test_get_default_access_control(self):
        """測試獲取默認訪問控制配置"""
        default_acl = FileMetadataService.get_default_access_control(
            user_id="user123", tenant_id="tenant1"
        )
        assert default_acl.access_level == FileAccessLevel.PRIVATE.value
        assert default_acl.owner_id == "user123"
        assert default_acl.owner_tenant_id == "tenant1"
        assert default_acl.data_classification == DataClassification.INTERNAL.value
        assert default_acl.sensitivity_labels == []
        assert default_acl.authorized_users == ["user123"]

    def test_create_with_default_access_control(
        self, metadata_service: FileMetadataService, sample_file_metadata_create
    ):
        """測試創建文件時自動生成默認 access_control"""
        # 不提供 access_control，應該自動生成默認配置
        metadata = metadata_service.create(sample_file_metadata_create)

        assert metadata.access_control is not None
        assert metadata.access_control.access_level == FileAccessLevel.PRIVATE.value
        assert metadata.access_control.owner_id == "user123"
        assert metadata.data_classification == DataClassification.INTERNAL.value

        # 清理
        metadata_service.delete("test_file_123")

    def test_create_with_custom_access_control(
        self, metadata_service: FileMetadataService, sample_file_metadata_create
    ):
        """測試創建文件時使用自定義 access_control"""
        custom_acl = FileAccessControl(
            access_level=FileAccessLevel.PUBLIC.value,
            owner_id="user123",
            data_classification=DataClassification.PUBLIC.value,
        )
        sample_file_metadata_create.access_control = custom_acl

        metadata = metadata_service.create(sample_file_metadata_create)

        assert metadata.access_control is not None
        assert metadata.access_control.access_level == FileAccessLevel.PUBLIC.value
        assert metadata.access_control.data_classification == DataClassification.PUBLIC.value

        # 清理
        metadata_service.delete("test_file_123")

    def test_update_access_control(
        self, metadata_service: FileMetadataService, sample_file_metadata_create
    ):
        """測試更新文件 access_control"""
        # 先創建文件
        metadata = metadata_service.create(sample_file_metadata_create)
        assert metadata.access_control is not None
        assert metadata.access_control.access_level == FileAccessLevel.PRIVATE.value

        # 更新 access_control
        new_acl = FileAccessControl(
            access_level=FileAccessLevel.ORGANIZATION.value,
            authorized_organizations=["org1"],
            owner_id="user123",
            data_classification=DataClassification.CONFIDENTIAL.value,
        )
        update = FileMetadataUpdate(access_control=new_acl)
        updated_metadata = metadata_service.update("test_file_123", update)

        assert updated_metadata is not None
        assert updated_metadata.access_control is not None
        assert updated_metadata.access_control.access_level == FileAccessLevel.ORGANIZATION.value
        assert updated_metadata.access_control.authorized_organizations == ["org1"]
        assert updated_metadata.data_classification == DataClassification.CONFIDENTIAL.value

        # 清理
        metadata_service.delete("test_file_123")

    def test_backward_compatibility_no_access_control(self, metadata_service: FileMetadataService):
        """測試向後兼容性：舊文件無 access_control 字段"""
        # 創建一個沒有 access_control 的文檔（模擬舊數據）
        if metadata_service.client.db is None:
            pytest.skip("ArangoDB not connected")

        collection = metadata_service.client.db.collection("file_metadata")
        old_doc = {
            "_key": "old_file_123",
            "file_id": "old_file_123",
            "filename": "old.txt",
            "file_type": "text/plain",
            "file_size": 1024,
            "user_id": "user123",
            "task_id": "task123",
            "upload_time": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            # 沒有 access_control 字段
        }
        collection.insert(old_doc)

        # 讀取應該能正常工作（access_control 為 None）
        metadata = metadata_service.get("old_file_123")
        assert metadata is not None
        assert metadata.access_control is None  # 舊文件沒有 access_control

        # 清理
        metadata_service.delete("old_file_123")

    def test_sync_data_classification_and_labels(
        self, metadata_service: FileMetadataService, sample_file_metadata_create
    ):
        """測試 data_classification 和 sensitivity_labels 同步"""
        custom_acl = FileAccessControl(
            access_level=FileAccessLevel.PRIVATE.value,
            owner_id="user123",
            data_classification=DataClassification.CONFIDENTIAL.value,
            sensitivity_labels=["pii", "financial"],
        )
        sample_file_metadata_create.access_control = custom_acl

        metadata = metadata_service.create(sample_file_metadata_create)

        # 驗證同步
        assert metadata.access_control is not None
        assert metadata.data_classification == DataClassification.CONFIDENTIAL.value
        assert metadata.sensitivity_labels == ["pii", "financial"]
        assert metadata.access_control.data_classification == DataClassification.CONFIDENTIAL.value
        assert metadata.access_control.sensitivity_labels == ["pii", "financial"]

        # 清理
        metadata_service.delete("test_file_123")
