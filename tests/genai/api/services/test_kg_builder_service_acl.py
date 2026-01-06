# 代碼功能說明: 知識圖譜構建服務 ACL 單元測試
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""知識圖譜構建服務 ACL 單元測試"""

import pytest
from unittest.mock import MagicMock, patch

from genai.api.services.kg_builder_service import KGBuilderService
from services.api.models.data_classification import DataClassification
from services.api.models.file_access_control import FileAccessControl, FileAccessLevel
from services.api.models.file_metadata import FileMetadata
from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.file_permission_service import FilePermissionService
from system.security.models import Permission, User


@pytest.fixture
def kg_service():
    """創建知識圖譜構建服務實例"""
    return KGBuilderService()


@pytest.fixture
def owner_user():
    """創建文件所有者用戶"""
    return User(
        user_id="owner123",
        username="owner",
        permissions=[Permission.FILE_READ.value, Permission.DATA_ACCESS_INTERNAL.value],
    )


@pytest.fixture
def unauthorized_user():
    """創建未授權用戶"""
    return User(
        user_id="unauthorized123",
        username="unauthorized",
        permissions=[Permission.FILE_READ.value],
    )


class TestKGBuilderServiceACL:
    """知識圖譜構建服務 ACL 測試"""

    @patch("genai.api.services.kg_builder_service.get_metadata_service")
    @patch("genai.api.services.kg_builder_service.get_file_permission_service")
    def test_list_triples_by_file_id_with_acl_denies_access(
        self,
        mock_get_permission_service,
        mock_get_metadata_service,
        kg_service: KGBuilderService,
        owner_user: User,
        unauthorized_user: User,
    ):
        """測試 list_triples_by_file_id_with_acl 拒絕無權訪問的用戶"""
        # Mock 文件元數據服務
        metadata_service = MagicMock(spec=FileMetadataService)
        file_metadata = FileMetadata(
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
        metadata_service.get.return_value = file_metadata
        mock_get_metadata_service.return_value = metadata_service

        # Mock 權限服務
        permission_service = MagicMock(spec=FilePermissionService)
        permission_service.check_file_access_with_acl.side_effect = (
            lambda user, file_metadata, **kwargs: user.user_id == "owner123"
        )
        mock_get_permission_service.return_value = permission_service

        # 測試所有者用戶可以訪問
        result_owner = kg_service.list_triples_by_file_id_with_acl(
            file_id="file1",
            user=owner_user,
            limit=10,
            offset=0,
        )
        # 應該調用 list_triples_by_file_id（因為有權訪問）
        assert "total" in result_owner
        assert "triples" in result_owner

        # 測試未授權用戶不能訪問
        result_unauthorized = kg_service.list_triples_by_file_id_with_acl(
            file_id="file1",
            user=unauthorized_user,
            limit=10,
            offset=0,
        )
        # 應該返回空結果
        assert result_unauthorized["total"] == 0
        assert result_unauthorized["triples"] == []

    @patch("genai.api.services.kg_builder_service.get_metadata_service")
    @patch("genai.api.services.kg_builder_service.get_file_permission_service")
    def test_list_entities_with_acl_filters_by_permission(
        self,
        mock_get_permission_service,
        mock_get_metadata_service,
        kg_service: KGBuilderService,
        owner_user: User,
        unauthorized_user: User,
    ):
        """測試 list_entities_with_acl 根據權限過濾實體"""
        # Mock list_entities 返回結果
        mock_entities = [
            {
                "_key": "entity1",
                "type": "Person",
                "name": "Alice",
                "file_id": "file1",
            },
            {
                "_key": "entity2",
                "type": "Person",
                "name": "Bob",
                "file_id": "file2",
            },
        ]

        with patch.object(kg_service, "list_entities", return_value=mock_entities):
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
            )
            mock_get_permission_service.return_value = permission_service

            # 測試所有者用戶可以訪問所有實體
            results_owner = kg_service.list_entities_with_acl(
                user=owner_user,
                limit=10,
                offset=0,
            )
            assert len(results_owner) == 2

            # 測試未授權用戶不能訪問任何實體
            permission_service.check_file_access_with_acl.return_value = False
            results_unauthorized = kg_service.list_entities_with_acl(
                user=unauthorized_user,
                limit=10,
                offset=0,
            )
            assert len(results_unauthorized) == 0

    @patch("genai.api.services.kg_builder_service.get_metadata_service")
    @patch("genai.api.services.kg_builder_service.get_file_permission_service")
    def test_get_entity_neighbors_with_acl_filters_by_permission(
        self,
        mock_get_permission_service,
        mock_get_metadata_service,
        kg_service: KGBuilderService,
        owner_user: User,
        unauthorized_user: User,
    ):
        """測試 get_entity_neighbors_with_acl 根據權限過濾鄰居節點"""
        # Mock get_entity_neighbors 返回結果
        mock_neighbors = [
            {
                "_key": "neighbor1",
                "type": "Person",
                "name": "Charlie",
                "file_id": "file1",
            },
            {
                "_key": "neighbor2",
                "type": "Person",
                "name": "David",
                "file_id": "file2",
            },
        ]

        with patch.object(
            kg_service, "get_entity_neighbors", return_value=mock_neighbors
        ):
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
            )
            mock_get_permission_service.return_value = permission_service

            # 測試所有者用戶可以訪問所有鄰居
            results_owner = kg_service.get_entity_neighbors_with_acl(
                entity_id="entity1",
                user=owner_user,
                limit=10,
            )
            assert len(results_owner) == 2

            # 測試未授權用戶不能訪問任何鄰居
            permission_service.check_file_access_with_acl.return_value = False
            results_unauthorized = kg_service.get_entity_neighbors_with_acl(
                entity_id="entity1",
                user=unauthorized_user,
                limit=10,
            )
            assert len(results_unauthorized) == 0

