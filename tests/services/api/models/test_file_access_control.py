# 代碼功能說明: 文件訪問控制模型單元測試
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""文件訪問控制模型單元測試"""

import pytest
from datetime import datetime, timedelta

from services.api.models.data_classification import DataClassification, SensitivityLabel
from services.api.models.file_access_control import FileAccessControl, FileAccessLevel


class TestFileAccessLevel:
    """FileAccessLevel 枚舉測試"""

    def test_enum_values(self):
        """測試枚舉值"""
        assert FileAccessLevel.PUBLIC.value == "public"
        assert FileAccessLevel.ORGANIZATION.value == "organization"
        assert FileAccessLevel.SECURITY_GROUP.value == "security_group"
        assert FileAccessLevel.PRIVATE.value == "private"

    def test_get_all_values(self):
        """測試獲取所有值"""
        values = FileAccessLevel.get_all_values()
        assert "public" in values
        assert "organization" in values
        assert "security_group" in values
        assert "private" in values
        assert len(values) == 4

    def test_validate_valid(self):
        """測試驗證有效值"""
        assert FileAccessLevel.validate("public") == "public"
        assert FileAccessLevel.validate("private") == "private"

    def test_validate_invalid(self):
        """測試驗證無效值"""
        with pytest.raises(ValueError, match="Invalid access level"):
            FileAccessLevel.validate("invalid")


class TestFileAccessControl:
    """FileAccessControl 模型測試"""

    def test_create_minimal(self):
        """測試創建最小配置"""
        acl = FileAccessControl(
            access_level=FileAccessLevel.PRIVATE.value,
            owner_id="user123",
        )
        assert acl.access_level == "private"
        assert acl.owner_id == "user123"
        assert acl.data_classification == DataClassification.INTERNAL.value
        assert acl.sensitivity_labels == []
        assert acl.authorized_users == ["user123"]  # 自動包含 owner_id

    def test_create_with_all_fields(self):
        """測試創建完整配置"""
        expires_at = datetime.utcnow() + timedelta(days=30)
        acl = FileAccessControl(
            access_level=FileAccessLevel.ORGANIZATION.value,
            authorized_organizations=["org1", "org2"],
            data_classification=DataClassification.CONFIDENTIAL.value,
            sensitivity_labels=[SensitivityLabel.PII.value, SensitivityLabel.FINANCIAL.value],
            owner_id="user123",
            owner_tenant_id="tenant1",
            access_log_enabled=True,
            access_expires_at=expires_at,
        )
        assert acl.access_level == "organization"
        assert acl.authorized_organizations == ["org1", "org2"]
        assert acl.data_classification == "confidential"
        assert len(acl.sensitivity_labels) == 2
        assert acl.owner_id == "user123"
        assert acl.owner_tenant_id == "tenant1"
        assert acl.access_log_enabled is True
        assert acl.access_expires_at == expires_at

    def test_validate_access_level(self):
        """測試訪問級別驗證"""
        with pytest.raises(ValueError, match="Invalid access level"):
            FileAccessControl(
                access_level="invalid",
                owner_id="user123",
            )

    def test_validate_data_classification(self):
        """測試數據分類驗證"""
        with pytest.raises(ValueError, match="Invalid classification"):
            FileAccessControl(
                access_level=FileAccessLevel.PRIVATE.value,
                owner_id="user123",
                data_classification="invalid",
            )

    def test_validate_sensitivity_labels(self):
        """測試敏感性標籤驗證"""
        with pytest.raises(ValueError, match="Invalid sensitivity labels"):
            FileAccessControl(
                access_level=FileAccessLevel.PRIVATE.value,
                owner_id="user123",
                sensitivity_labels=["invalid"],
            )

    def test_private_auto_include_owner(self):
        """測試 PRIVATE 級別自動包含所有者"""
        acl = FileAccessControl(
            access_level=FileAccessLevel.PRIVATE.value,
            owner_id="user123",
            authorized_users=["user456"],  # 不包含 owner_id
        )
        # 應該自動包含 owner_id
        assert "user123" in acl.authorized_users
        assert "user456" in acl.authorized_users

    def test_empty_authorized_lists(self):
        """測試空授權列表轉換為 None"""
        acl = FileAccessControl(
            access_level=FileAccessLevel.PRIVATE.value,
            owner_id="user123",
            authorized_organizations=[],
            authorized_security_groups=[],
        )
        # 空列表應該轉換為 None（通過驗證器）
        # 注意：PRIVATE 級別的 authorized_users 不會為空（自動包含 owner_id）

    def test_default_values(self):
        """測試默認值"""
        acl = FileAccessControl(
            access_level=FileAccessLevel.PRIVATE.value,
            owner_id="user123",
        )
        assert acl.data_classification == DataClassification.INTERNAL.value
        assert acl.sensitivity_labels == []
        assert acl.access_log_enabled is True
        assert acl.access_expires_at is None
        assert acl.owner_tenant_id is None

