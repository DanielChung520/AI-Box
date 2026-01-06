# 代碼功能說明: 文件權限服務 ACL 單元測試
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""文件權限服務 ACL 單元測試"""

import pytest
from datetime import datetime, timedelta

from services.api.models.data_classification import DataClassification, SensitivityLabel
from services.api.models.file_access_control import FileAccessControl, FileAccessLevel
from services.api.models.file_metadata import FileMetadata, FileMetadataCreate
from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.file_permission_service import FilePermissionService
from system.security.models import Permission, User


@pytest.fixture
def permission_service():
    """創建文件權限服務實例"""
    return FilePermissionService()


@pytest.fixture
def owner_user():
    """創建文件所有者用戶"""
    return User(
        user_id="owner123",
        username="owner",
        permissions=[Permission.FILE_READ.value],
        metadata={"organization_id": "org1", "security_groups": ["group1"]},
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


@pytest.fixture
def admin_user():
    """創建管理員用戶"""
    return User(
        user_id="admin123",
        username="admin",
        permissions=[Permission.ALL.value],
    )


@pytest.fixture
def sample_file_metadata(owner_user):
    """創建示例文件元數據"""
    acl = FileAccessControl(
        access_level=FileAccessLevel.PRIVATE.value,
        owner_id=owner_user.user_id,
        data_classification=DataClassification.INTERNAL.value,
    )
    return FileMetadata(
        file_id="test_file_123",
        filename="test.txt",
        file_type="text/plain",
        file_size=1024,
        user_id=owner_user.user_id,
        task_id="task123",
        access_control=acl,
        data_classification=DataClassification.INTERNAL.value,
        upload_time=datetime.utcnow(),
    )


class TestFilePermissionServiceACL:
    """文件權限服務 ACL 測試"""

    def test_check_public_access(
        self, permission_service: FilePermissionService, authorized_user: User
    ):
        """測試 PUBLIC 訪問級別"""
        acl = FileAccessControl(
            access_level=FileAccessLevel.PUBLIC.value,
            owner_id="owner123",
            data_classification=DataClassification.PUBLIC.value,
        )
        file_metadata = FileMetadata(
            file_id="public_file",
            filename="public.txt",
            file_type="text/plain",
            file_size=1024,
            user_id="owner123",
            task_id="task123",
            access_control=acl,
            data_classification=DataClassification.PUBLIC.value,
            upload_time=datetime.utcnow(),
        )

        assert permission_service.check_file_access_with_acl(
            user=authorized_user, file_metadata=file_metadata
        ) is True

    def test_check_organization_access(
        self,
        permission_service: FilePermissionService,
        authorized_user: User,
        unauthorized_user: User,
    ):
        """測試 ORGANIZATION 訪問級別"""
        acl = FileAccessControl(
            access_level=FileAccessLevel.ORGANIZATION.value,
            authorized_organizations=["org1"],
            owner_id="owner123",
            data_classification=DataClassification.INTERNAL.value,
        )
        file_metadata = FileMetadata(
            file_id="org_file",
            filename="org.txt",
            file_type="text/plain",
            file_size=1024,
            user_id="owner123",
            task_id="task123",
            access_control=acl,
            data_classification=DataClassification.INTERNAL.value,
            upload_time=datetime.utcnow(),
        )

        # 授權組織的用戶可以訪問
        assert (
            permission_service.check_file_access_with_acl(
                user=authorized_user, file_metadata=file_metadata
            )
            is True
        )

        # 未授權組織的用戶不能訪問
        assert (
            permission_service.check_file_access_with_acl(
                user=unauthorized_user, file_metadata=file_metadata
            )
            is False
        )

    def test_check_security_group_access(
        self,
        permission_service: FilePermissionService,
        authorized_user: User,
        unauthorized_user: User,
    ):
        """測試 SECURITY_GROUP 訪問級別"""
        acl = FileAccessControl(
            access_level=FileAccessLevel.SECURITY_GROUP.value,
            authorized_security_groups=["group1"],
            owner_id="owner123",
            data_classification=DataClassification.INTERNAL.value,
        )
        file_metadata = FileMetadata(
            file_id="group_file",
            filename="group.txt",
            file_type="text/plain",
            file_size=1024,
            user_id="owner123",
            task_id="task123",
            access_control=acl,
            data_classification=DataClassification.INTERNAL.value,
            upload_time=datetime.utcnow(),
        )

        # 授權安全組的用戶可以訪問
        assert (
            permission_service.check_file_access_with_acl(
                user=authorized_user, file_metadata=file_metadata
            )
            is True
        )

        # 未授權安全組的用戶不能訪問
        assert (
            permission_service.check_file_access_with_acl(
                user=unauthorized_user, file_metadata=file_metadata
            )
            is False
        )

    def test_check_private_access(
        self,
        permission_service: FilePermissionService,
        owner_user: User,
        authorized_user: User,
        unauthorized_user: User,
    ):
        """測試 PRIVATE 訪問級別"""
        acl = FileAccessControl(
            access_level=FileAccessLevel.PRIVATE.value,
            authorized_users=[authorized_user.user_id],
            owner_id=owner_user.user_id,
            data_classification=DataClassification.INTERNAL.value,
        )
        file_metadata = FileMetadata(
            file_id="private_file",
            filename="private.txt",
            file_type="text/plain",
            file_size=1024,
            user_id=owner_user.user_id,
            task_id="task123",
            access_control=acl,
            data_classification=DataClassification.INTERNAL.value,
            upload_time=datetime.utcnow(),
        )

        # 所有者可以訪問
        assert (
            permission_service.check_file_access_with_acl(
                user=owner_user, file_metadata=file_metadata
            )
            is True
        )

        # 授權用戶可以訪問
        assert (
            permission_service.check_file_access_with_acl(
                user=authorized_user, file_metadata=file_metadata
            )
            is True
        )

        # 未授權用戶不能訪問
        assert (
            permission_service.check_file_access_with_acl(
                user=unauthorized_user, file_metadata=file_metadata
            )
            is False
        )

    def test_check_data_classification_access(
        self, permission_service: FilePermissionService
    ):
        """測試數據分類級別檢查"""
        # 創建沒有 CONFIDENTIAL 權限的用戶
        user = User(
            user_id="user123",
            permissions=[Permission.FILE_READ.value, Permission.DATA_ACCESS_INTERNAL.value],
        )

        acl = FileAccessControl(
            access_level=FileAccessLevel.PUBLIC.value,
            owner_id="owner123",
            data_classification=DataClassification.CONFIDENTIAL.value,
        )
        file_metadata = FileMetadata(
            file_id="confidential_file",
            filename="confidential.txt",
            file_type="text/plain",
            file_size=1024,
            user_id="owner123",
            task_id="task123",
            access_control=acl,
            data_classification=DataClassification.CONFIDENTIAL.value,
            upload_time=datetime.utcnow(),
        )

        # 用戶沒有 CONFIDENTIAL 權限，應該被拒絕
        assert (
            permission_service.check_file_access_with_acl(
                user=user, file_metadata=file_metadata
            )
            is False
        )

    def test_check_sensitivity_labels_access(
        self, permission_service: FilePermissionService
    ):
        """測試敏感性標籤檢查"""
        # 創建沒有 PII 標籤權限的用戶
        user = User(
            user_id="user123",
            permissions=[
                Permission.FILE_READ.value,
                Permission.DATA_ACCESS_INTERNAL.value,
                # 沒有 DATA_LABEL_PII 權限
            ],
        )

        acl = FileAccessControl(
            access_level=FileAccessLevel.PUBLIC.value,
            owner_id="owner123",
            data_classification=DataClassification.INTERNAL.value,
            sensitivity_labels=[SensitivityLabel.PII.value],
        )
        file_metadata = FileMetadata(
            file_id="pii_file",
            filename="pii.txt",
            file_type="text/plain",
            file_size=1024,
            user_id="owner123",
            task_id="task123",
            access_control=acl,
            data_classification=DataClassification.INTERNAL.value,
            sensitivity_labels=[SensitivityLabel.PII.value],
            upload_time=datetime.utcnow(),
        )

        # 用戶沒有 PII 標籤權限，應該被拒絕
        assert (
            permission_service.check_file_access_with_acl(
                user=user, file_metadata=file_metadata
            )
            is False
        )

    def test_check_access_expired(
        self, permission_service: FilePermissionService, authorized_user: User
    ):
        """測試訪問權限過期"""
        expired_time = datetime.utcnow() - timedelta(days=1)
        acl = FileAccessControl(
            access_level=FileAccessLevel.PUBLIC.value,
            owner_id="owner123",
            data_classification=DataClassification.PUBLIC.value,
            access_expires_at=expired_time,
        )
        file_metadata = FileMetadata(
            file_id="expired_file",
            filename="expired.txt",
            file_type="text/plain",
            file_size=1024,
            user_id="owner123",
            task_id="task123",
            access_control=acl,
            data_classification=DataClassification.PUBLIC.value,
            upload_time=datetime.utcnow(),
        )

        # 訪問已過期，應該被拒絕
        assert (
            permission_service.check_file_access_with_acl(
                user=authorized_user, file_metadata=file_metadata
            )
            is False
        )

    def test_check_admin_access_all(
        self, permission_service: FilePermissionService, admin_user: User
    ):
        """測試管理員可以訪問所有文件"""
        acl = FileAccessControl(
            access_level=FileAccessLevel.PRIVATE.value,
            owner_id="owner123",
            data_classification=DataClassification.RESTRICTED.value,
            sensitivity_labels=[SensitivityLabel.PII.value, SensitivityLabel.FINANCIAL.value],
        )
        file_metadata = FileMetadata(
            file_id="restricted_file",
            filename="restricted.txt",
            file_type="text/plain",
            file_size=1024,
            user_id="owner123",
            task_id="task123",
            access_control=acl,
            data_classification=DataClassification.RESTRICTED.value,
            sensitivity_labels=[SensitivityLabel.PII.value, SensitivityLabel.FINANCIAL.value],
            upload_time=datetime.utcnow(),
        )

        # 管理員應該可以訪問所有文件
        assert (
            permission_service.check_file_access_with_acl(
                user=admin_user, file_metadata=file_metadata
            )
            is True
        )

    def test_check_backward_compatibility_no_acl(
        self, permission_service: FilePermissionService, owner_user: User
    ):
        """測試向後兼容性：沒有 access_control 的文件"""
        # 創建沒有 access_control 的文件（模擬舊數據）
        file_metadata = FileMetadata(
            file_id="old_file",
            filename="old.txt",
            file_type="text/plain",
            file_size=1024,
            user_id=owner_user.user_id,
            task_id="task123",
            access_control=None,  # 沒有 access_control
            data_classification=None,
            upload_time=datetime.utcnow(),
        )

        # 應該使用默認配置（PRIVATE），所有者可以訪問
        assert (
            permission_service.check_file_access_with_acl(
                user=owner_user, file_metadata=file_metadata
            )
            is True
        )

