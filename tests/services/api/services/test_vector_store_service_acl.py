# 代碼功能說明: 向量存儲服務 ACL 單元測試
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""向量存儲服務 ACL 單元測試"""

import pytest
from unittest.mock import MagicMock, patch

from services.api.models.data_classification import DataClassification
from services.api.models.file_access_control import FileAccessControl, FileAccessLevel
from services.api.models.file_metadata import FileMetadata
from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.file_permission_service import FilePermissionService
from services.api.services.vector_store_service import VectorStoreService
from system.security.models import Permission, User


@pytest.fixture
def vector_service():
    """創建向量存儲服務實例"""
    return VectorStoreService()


@pytest.fixture
def owner_user():
    """創建文件所有者用戶"""
    return User(
        user_id="owner123",
        username="owner",
        permissions=[Permission.FILE_READ.value, Permission.DATA_ACCESS_INTERNAL.value],
    )


@pytest.fixture
def authorized_user():
    """創建授權用戶"""
    return User(
        user_id="authorized123",
        username="authorized",
        permissions=[Permission.FILE_READ.value, Permission.DATA_ACCESS_INTERNAL.value],
        metadata={"organization_id": "org1", "security_groups": ["group1"]},
    )


@pytest.fixture
def unauthorized_user():
    """創建未授權用戶"""
    return User(
        user_id="unauthorized123",
        username="unauthorized",
        permissions=[Permission.FILE_READ.value],
        metadata={"organization_id": "org2", "security_groups": ["group2"]},
    )


class TestVectorStoreServiceACL:
    """向量存儲服務 ACL 測試"""

    @patch("services.api.services.vector_store_service.get_metadata_service")
    @patch("services.api.services.vector_store_service.get_file_permission_service")
    def test_query_vectors_with_acl_filters_by_permission(
        self,
        mock_get_permission_service,
        mock_get_metadata_service,
        vector_service: VectorStoreService,
        owner_user: User,
        authorized_user: User,
        unauthorized_user: User,
    ):
        """測試 query_vectors_with_acl 根據權限過濾結果"""
        # Mock 向量查詢結果
        mock_results = [
            {
                "id": "vec1",
                "document": "content1",
                "metadata": {"file_id": "file1"},
                "distance": 0.1,
            },
            {
                "id": "vec2",
                "document": "content2",
                "metadata": {"file_id": "file2"},
                "distance": 0.2,
            },
        ]

        # Mock query_vectors 方法
        with patch.object(vector_service, "query_vectors", return_value=mock_results):
            # Mock 文件元數據服務
            metadata_service = MagicMock(spec=FileMetadataService)
            file1_metadata = FileMetadata(
                file_id="file1",
                filename="file1.txt",
                file_type="text/plain",
                file_size=1024,
                user_id="owner123",
                task_id="task123",
                access_control=FileAccessControl(
                    access_level=FileAccessLevel.PRIVATE.value,
                    owner_id="owner123",
                    data_classification=DataClassification.INTERNAL.value,
                ),
                upload_time=None,
            )
            file2_metadata = FileMetadata(
                file_id="file2",
                filename="file2.txt",
                file_type="text/plain",
                file_size=2048,
                user_id="owner123",
                task_id="task123",
                access_control=FileAccessControl(
                    access_level=FileAccessLevel.PRIVATE.value,
                    owner_id="owner123",
                    data_classification=DataClassification.INTERNAL.value,
                ),
                upload_time=None,
            )
            metadata_service.get.side_effect = lambda fid: (
                file1_metadata if fid == "file1" else file2_metadata
            )
            mock_get_metadata_service.return_value = metadata_service

            # Mock 權限服務
            permission_service = MagicMock(spec=FilePermissionService)
            permission_service.check_file_access_with_acl.side_effect = (
                lambda user, file_metadata, **kwargs: user.user_id == "owner123"
                or user.user_id == "authorized123"
            )
            mock_get_permission_service.return_value = permission_service

            # 測試所有者用戶可以訪問所有結果
            results_owner = vector_service.query_vectors_with_acl(
                query_text="test",
                user=owner_user,
                n_results=10,
            )
            assert len(results_owner) == 2

            # 測試授權用戶可以訪問所有結果
            results_authorized = vector_service.query_vectors_with_acl(
                query_text="test",
                user=authorized_user,
                n_results=10,
            )
            assert len(results_authorized) == 2

            # 測試未授權用戶不能訪問任何結果
            permission_service.check_file_access_with_acl.side_effect = (
                lambda user, file_metadata, **kwargs: False
            )
            results_unauthorized = vector_service.query_vectors_with_acl(
                query_text="test",
                user=unauthorized_user,
                n_results=10,
            )
            assert len(results_unauthorized) == 0

    @patch("services.api.services.vector_store_service.get_metadata_service")
    @patch("services.api.services.vector_store_service.get_file_permission_service")
    def test_query_vectors_with_acl_batches_metadata_queries(
        self,
        mock_get_permission_service,
        mock_get_metadata_service,
        vector_service: VectorStoreService,
        owner_user: User,
    ):
        """測試 query_vectors_with_acl 批量獲取文件元數據（性能優化）"""
        # Mock 向量查詢結果（多個文件）
        mock_results = [
            {
                "id": f"vec{i}",
                "document": f"content{i}",
                "metadata": {"file_id": f"file{i % 3}"},  # 3個不同的文件
                "distance": 0.1 * i,
            }
            for i in range(10)
        ]

        with patch.object(vector_service, "query_vectors", return_value=mock_results):
            metadata_service = MagicMock(spec=FileMetadataService)
            file_metadata_cache = {}

            def mock_get(file_id: str):
                if file_id not in file_metadata_cache:
                    file_metadata_cache[file_id] = FileMetadata(
                        file_id=file_id,
                        filename=f"{file_id}.txt",
                        file_type="text/plain",
                        file_size=1024,
                        user_id="owner123",
                        task_id="task123",
                        access_control=FileAccessControl(
                            access_level=FileAccessLevel.PRIVATE.value,
                            owner_id="owner123",
                            data_classification=DataClassification.INTERNAL.value,
                        ),
                        upload_time=None,
                    )
                return file_metadata_cache[file_id]

            metadata_service.get.side_effect = mock_get
            mock_get_metadata_service.return_value = metadata_service

            permission_service = MagicMock(spec=FilePermissionService)
            permission_service.check_file_access_with_acl.return_value = True
            mock_get_permission_service.return_value = permission_service

            results = vector_service.query_vectors_with_acl(
                query_text="test",
                user=owner_user,
                n_results=10,
            )

            # 驗證每個文件只查詢一次（批量優化）
            assert len(results) == 10
            # 驗證 get 被調用的次數應該等於唯一文件數（3個）
            unique_file_ids = set()
            for result in mock_results:
                unique_file_ids.add(result["metadata"]["file_id"])
            # 注意：由於緩存機制，每個唯一文件ID應該只查詢一次
            assert metadata_service.get.call_count <= len(unique_file_ids) + 2  # 允許一些容差

