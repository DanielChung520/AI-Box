# 代碼功能說明: 文件權限檢查服務
# 創建日期: 2025-12-06 15:20 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""文件權限檢查服務 - 實現文件級別的訪問權限控制"""

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

import structlog
from fastapi import HTTPException, Request, status

from services.api.models.data_classification import DataClassification
from services.api.models.file_access_control import FileAccessLevel
from services.api.models.file_metadata import FileMetadata
from services.api.services.audit_log_service import AuditLogService
from services.api.services.file_metadata_service import FileMetadataService, get_metadata_service
from services.api.services.user_task_service import get_user_task_service
from system.security.models import Permission, User

if TYPE_CHECKING:
    from fastapi import Request

logger = structlog.get_logger(__name__)


class FilePermissionService:
    """文件權限檢查服務"""

    def __init__(self, metadata_service: Optional[FileMetadataService] = None):
        """
        初始化文件權限服務

        Args:
            metadata_service: 文件元數據服務（可選，如果不提供則自動創建）
        """
        self.metadata_service: FileMetadataService = metadata_service or get_metadata_service()
        self.logger = logger
        # 審計日誌服務（懶加載）
        self._audit_log_service: Optional[AuditLogService] = None

    def check_file_access(
        self,
        user: User,
        file_id: str,
        required_permission: str = Permission.FILE_READ.value,
    ) -> FileMetadata:
        """
        檢查用戶是否有權訪問指定文件

        修改時間：2025-12-09 - 添加任務所有者檢查，確保用戶只能訪問自己任務的文件

        Args:
            user: 當前用戶
            file_id: 文件ID
            required_permission: 需要的權限（默認為 FILE_READ）

        Returns:
            FileMetadata: 文件元數據（如果權限檢查通過）

        Raises:
            HTTPException: 如果文件不存在或用戶無權訪問
        """
        # 獲取文件元數據
        file_metadata = self.metadata_service.get(file_id)
        if file_metadata is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}",
            )

        # 修改時間：2025-12-09 - 檢查任務所有者權限
        # 如果文件有關聯的任務，必須檢查任務是否屬於當前用戶
        if file_metadata.task_id:
            if not self.check_task_file_access(
                user=user,
                task_id=file_metadata.task_id,
                required_permission=required_permission,
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions to access file: {file_id}. Task {file_metadata.task_id} does not belong to user {user.user_id}",
                )

        # 檢查文件權限
        if not self.has_file_permission(user, file_metadata, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions to access file: {file_id}. Required: {required_permission}",
            )

        return file_metadata

    def has_file_permission(
        self,
        user: User,
        file_metadata: FileMetadata,
        permission: str,
    ) -> bool:
        """
        檢查用戶是否有權對文件執行指定操作

        權限檢查邏輯：
        1. 如果用戶擁有 ALL 權限，直接通過
        2. 如果用戶擁有對應的通用權限（如 file:read），檢查是否為文件所有者或共享文件
        3. 如果用戶擁有 own 權限（如 file:read:own），檢查是否為文件所有者
        4. 如果用戶擁有 shared 權限（如 file:read:shared），檢查是否為共享文件

        Args:
            user: 當前用戶
            file_metadata: 文件元數據
            permission: 需要的權限

        Returns:
            bool: 是否有權限
        """
        # 超級管理員權限
        if user.has_permission(Permission.ALL.value):
            return True

        # 檢查是否為文件所有者
        is_owner = file_metadata.user_id == user.user_id

        # 修改時間：2025-12-09 - 如果用戶是文件所有者，自動允許操作（即使沒有明確的 own 權限）
        # 這是為了確保文件所有者可以操作自己的文件，避免權限配置問題
        if is_owner:
            # 文件所有者對自己的文件有完全控制權
            # 允許的操作：read, update, delete, download
            owner_allowed_permissions = [
                Permission.FILE_READ.value,
                Permission.FILE_UPDATE.value,
                Permission.FILE_DELETE.value,
                Permission.FILE_DOWNLOAD.value,
            ]
            if permission in owner_allowed_permissions:
                return True

        # 檢查是否為共享文件（可以通過 task_id 或其他共享機制判斷）
        # TODO: 實現共享文件檢查邏輯（階段5任務1.1.2）
        is_shared = False  # 暫時設為 False，後續實現共享機制

        # 權限映射
        permission_map = {
            Permission.FILE_READ.value: [
                Permission.FILE_READ.value,
                Permission.FILE_READ_OWN.value if is_owner else None,
                Permission.FILE_READ_SHARED.value if is_shared else None,
            ],
            Permission.FILE_READ_OWN.value: [
                Permission.FILE_READ_OWN.value if is_owner else None,
            ],
            Permission.FILE_READ_SHARED.value: [
                Permission.FILE_READ_SHARED.value if is_shared else None,
            ],
            Permission.FILE_DELETE.value: [
                Permission.FILE_DELETE.value,
                Permission.FILE_DELETE_OWN.value if is_owner else None,
            ],
            Permission.FILE_DELETE_OWN.value: [
                Permission.FILE_DELETE_OWN.value if is_owner else None,
            ],
            Permission.FILE_UPDATE.value: [
                Permission.FILE_UPDATE.value,
                Permission.FILE_UPDATE_OWN.value if is_owner else None,
            ],
            Permission.FILE_UPDATE_OWN.value: [
                Permission.FILE_UPDATE_OWN.value if is_owner else None,
            ],
            Permission.FILE_DOWNLOAD.value: [
                Permission.FILE_DOWNLOAD.value,
                Permission.FILE_DOWNLOAD_OWN.value if is_owner else None,
            ],
            Permission.FILE_DOWNLOAD_OWN.value: [
                Permission.FILE_DOWNLOAD_OWN.value if is_owner else None,
            ],
        }

        # 獲取允許的權限列表
        allowed_permissions = permission_map.get(permission, [])
        allowed_permissions = [p for p in allowed_permissions if p is not None]

        # 確保所有權限都是字符串類型
        allowed_permissions_str: List[str] = [str(p) for p in allowed_permissions if p is not None]

        # 檢查用戶是否擁有任一允許的權限
        if not allowed_permissions_str:
            return False

        return user.has_any_permission(*allowed_permissions_str)

    def check_upload_permission(self, user: User) -> bool:
        """
        檢查用戶是否有權上傳文件

        修改時間：2025-12-09 - 在測試環境中，如果用戶沒有權限，自動授予文件上傳權限

        Args:
            user: 當前用戶

        Returns:
            bool: 是否有權上傳

        Raises:
            HTTPException: 如果用戶無權上傳
        """
        # 超級管理員權限
        if user.has_permission(Permission.ALL.value):
            return True

        # 檢查是否有文件上傳權限
        if user.has_permission(Permission.FILE_UPLOAD.value):
            return True

        # 修改時間：2025-12-09 - 在測試環境中，如果用戶沒有權限，記錄警告但允許上傳
        # 這是為了確保測試環境的可用性，避免因為權限配置問題導致功能無法使用
        from system.security.config import get_security_settings

        settings = get_security_settings()

        if settings.should_bypass_auth:
            logger.warning(
                "User missing FILE_UPLOAD permission, allowing upload (test environment)",
                user_id=user.user_id,
                permissions=user.permissions,
            )
            return True

        # 生產環境：嚴格檢查權限
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to upload files. Required: file:upload",
        )

    def check_task_file_access(
        self,
        user: User,
        task_id: str,
        required_permission: str = Permission.FILE_READ.value,
    ) -> bool:
        """
        檢查用戶是否有權訪問任務下的文件

        修改時間：2025-12-09 - 實現任務所有者檢查，確保用戶只能訪問自己的任務

        Args:
            user: 當前用戶
            task_id: 任務ID
            required_permission: 需要的權限

        Returns:
            bool: 是否有權訪問

        Raises:
            HTTPException: 如果用戶無權訪問任務文件
        """
        # 超級管理員權限
        if user.has_permission(Permission.ALL.value):
            return True

        # 修改時間：2025-12-09 - 檢查任務是否屬於當前用戶
        # 每個用戶只能訪問自己的任務
        try:
            task_service = get_user_task_service()
            task = task_service.get(user_id=user.user_id, task_id=task_id)

            if task is None:
                # 任務不存在或任務不屬於當前用戶
                self.logger.warning(
                    "Task access denied: task does not belong to user",
                    user_id=user.user_id,
                    task_id=task_id,
                )
                return False

            # 任務存在且屬於當前用戶，允許訪問
            return True
        except Exception as e:
            self.logger.error(
                "Error checking task access",
                user_id=user.user_id,
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
            return False

    def _get_audit_log_service(self) -> AuditLogService:
        """獲取審計日誌服務（懶加載）"""
        if self._audit_log_service is None:
            self._audit_log_service = AuditLogService()
        return self._audit_log_service

    def _get_user_organization_id(self, user: User) -> Optional[str]:
        """獲取用戶組織ID

        從 User.metadata 讀取組織ID（簡化版本，後續可集成專用服務）

        Args:
            user: 用戶對象

        Returns:
            組織ID，如果不存在則返回 None
        """
        return user.metadata.get("organization_id") if user.metadata else None

    def _get_user_security_groups(self, user: User) -> List[str]:
        """獲取用戶安全組列表

        從 User.metadata 讀取安全組列表（簡化版本，後續可集成專用服務）

        Args:
            user: 用戶對象

        Returns:
            安全組ID列表
        """
        if not user.metadata:
            return []
        security_groups = user.metadata.get("security_groups", [])
        if isinstance(security_groups, list):
            return security_groups
        return []

    def _check_data_classification_access(
        self, user: User, file_classification: Optional[str]
    ) -> bool:
        """檢查用戶是否有權限訪問指定分類級別的數據

        AI治理原則：用戶權限級別必須匹配或高於文件分類級別

        Args:
            user: 用戶對象
            file_classification: 文件分類級別

        Returns:
            是否有權限訪問
        """
        # 如果文件沒有分類級別，默認允許
        if not file_classification:
            return True

        # 超級管理員可以訪問所有級別
        if user.has_permission(Permission.ALL.value):
            return True

        # 權限級別映射
        classification_permissions = {
            DataClassification.PUBLIC.value: [],  # 無需特殊權限
            DataClassification.INTERNAL.value: [Permission.DATA_ACCESS_INTERNAL.value],
            DataClassification.CONFIDENTIAL.value: [Permission.DATA_ACCESS_CONFIDENTIAL.value],
            DataClassification.RESTRICTED.value: [Permission.DATA_ACCESS_RESTRICTED.value],
        }

        required_permissions = classification_permissions.get(
            file_classification,
            [Permission.DATA_ACCESS_INTERNAL.value],  # 默認需要內部權限
        )

        # 如果無需特殊權限，直接允許
        if not required_permissions:
            return True

        # 檢查用戶是否擁有所需權限
        return user.has_any_permission(*required_permissions)

    def _check_sensitivity_labels_access(
        self, user: User, file_sensitivity_labels: Optional[List[str]]
    ) -> bool:
        """檢查用戶是否有權限訪問包含特定敏感性標籤的數據

        AI治理原則：用戶必須擁有對應敏感性標籤的訪問權限

        Args:
            user: 用戶對象
            file_sensitivity_labels: 文件敏感性標籤列表

        Returns:
            是否有權限訪問
        """
        if not file_sensitivity_labels:
            return True  # 無敏感性標籤，直接允許

        # 超級管理員可以訪問所有標籤
        if user.has_permission(Permission.ALL.value):
            return True

        # 檢查用戶是否擁有所有所需標籤的訪問權限
        label_permission_map = {
            "pii": Permission.DATA_LABEL_PII.value,
            "phi": Permission.DATA_LABEL_PHI.value,
            "financial": Permission.DATA_LABEL_FINANCIAL.value,
            "ip": Permission.DATA_LABEL_IP.value,
            "customer": Permission.DATA_LABEL_CUSTOMER.value,
            "proprietary": Permission.DATA_LABEL_PROPRIETARY.value,
        }

        for label in file_sensitivity_labels:
            required_permission = label_permission_map.get(label.lower())
            if required_permission and not user.has_permission(required_permission):
                return False

        return True

    def _log_access_granted(
        self,
        user: User,
        file_metadata: FileMetadata,
        reason: str,
        request: Optional["Request"] = None,
    ) -> None:
        """記錄訪問授權日誌 (WBS-4.4.1)

        Args:
            user: 用戶對象
            file_metadata: 文件元數據
            reason: 授權原因（如 "PUBLIC access", "ORGANIZATION access", "OWNER access" 等）
            request: FastAPI Request 對象（可選，用於獲取 IP 地址和 User-Agent）
        """
        try:
            from services.api.models.audit_log import AuditAction, AuditLogCreate

            # 獲取 IP 地址和 User-Agent
            ip_address = "unknown"
            user_agent = "unknown"
            if request:
                ip_address = request.client.host if request.client else "unknown"
                user_agent = request.headers.get("user-agent", "unknown")

            # 構建詳細的日誌信息
            details: dict = {
                "reason": reason,
                "granted": True,
                "file_id": file_metadata.file_id,
                "filename": file_metadata.filename,
            }

            # 添加訪問控制詳細信息
            if file_metadata.access_control:
                details["access_level"] = file_metadata.access_control.access_level
                details["data_classification"] = (
                    file_metadata.data_classification
                    or file_metadata.access_control.data_classification
                )
                if file_metadata.access_control.sensitivity_labels:
                    details["sensitivity_labels"] = [
                        label.value if hasattr(label, "value") else label
                        for label in file_metadata.access_control.sensitivity_labels
                    ]
                if file_metadata.access_control.owner_id:
                    details["owner_id"] = file_metadata.access_control.owner_id

            audit_log = AuditLogCreate(
                user_id=user.user_id,
                action=AuditAction.FILE_ACCESS.value,
                resource_type="file",
                resource_id=file_metadata.file_id,
                timestamp=datetime.utcnow(),
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
            )
            audit_service = self._get_audit_log_service()
            audit_service.log(audit_log, async_mode=True)
        except Exception as e:
            self.logger.warning(
                "Failed to log access granted",
                user_id=user.user_id,
                file_id=file_metadata.file_id,
                error=str(e),
            )

    def _log_access_denied(
        self,
        user: User,
        file_metadata: FileMetadata,
        reason: str,
        required_permission: str,
        request: Optional["Request"] = None,
    ) -> None:
        """記錄訪問拒絕日誌 (WBS-4.4.1)

        Args:
            user: 用戶對象
            file_metadata: 文件元數據
            reason: 拒絕原因（如 "Access expired", "Insufficient clearance" 等）
            required_permission: 需要的權限
            request: FastAPI Request 對象（可選，用於獲取 IP 地址和 User-Agent）
        """
        try:
            from services.api.models.audit_log import AuditAction, AuditLogCreate

            # 獲取 IP 地址和 User-Agent
            ip_address = "unknown"
            user_agent = "unknown"
            if request:
                ip_address = request.client.host if request.client else "unknown"
                user_agent = request.headers.get("user-agent", "unknown")

            # 構建詳細的日誌信息
            details: dict = {
                "reason": reason,
                "granted": False,
                "required_permission": required_permission,
                "file_id": file_metadata.file_id,
                "filename": file_metadata.filename,
            }

            # 添加訪問控制詳細信息
            if file_metadata.access_control:
                details["access_level"] = file_metadata.access_control.access_level
                details["data_classification"] = (
                    file_metadata.data_classification
                    or file_metadata.access_control.data_classification
                )
                if file_metadata.access_control.sensitivity_labels:
                    details["sensitivity_labels"] = [
                        label.value if hasattr(label, "value") else label
                        for label in file_metadata.access_control.sensitivity_labels
                    ]
                if file_metadata.access_control.owner_id:
                    details["owner_id"] = file_metadata.access_control.owner_id

            audit_log = AuditLogCreate(
                user_id=user.user_id,
                action=AuditAction.FILE_ACCESS.value,
                resource_type="file",
                resource_id=file_metadata.file_id,
                timestamp=datetime.utcnow(),
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
            )
            audit_service = self._get_audit_log_service()
            audit_service.log(audit_log, async_mode=True)
        except Exception as e:
            self.logger.warning(
                "Failed to log access denied",
                user_id=user.user_id,
                file_id=file_metadata.file_id,
                error=str(e),
            )

    def check_file_access_with_acl(
        self,
        user: User,
        file_metadata: FileMetadata,
        required_permission: str = Permission.FILE_READ.value,
        request: Optional["Request"] = None,
    ) -> bool:
        """基於訪問控制列表（ACL）檢查文件訪問權限

        AI治理原則：
        1. 最小權限原則：默認拒絕，明確授權
        2. 數據分類檢查：用戶權限級別必須匹配或高於文件分類級別
        3. 分層授權：按優先級檢查（PUBLIC → ORGANIZATION → SECURITY_GROUP → PRIVATE）
        4. 審計日誌：記錄所有訪問嘗試

        Args:
            user: 當前用戶
            file_metadata: 文件元數據（包含 access_control）
            required_permission: 需要的權限
            request: FastAPI Request 對象（可選，用於審計日誌記錄）

        Returns:
            bool: 是否有權限訪問
        """
        # 如果文件沒有 access_control，使用默認配置（向後兼容）
        if file_metadata.access_control is None:
            # 使用默認的 PRIVATE 配置
            from services.api.services.file_metadata_service import (
                FileMetadataService,
            )

            default_acl = FileMetadataService.get_default_access_control(
                user_id=file_metadata.user_id or "unknown"
            )
            # 臨時設置 access_control 用於檢查
            # 注意：這裡不修改原始 file_metadata 對象
            access_control = default_acl
            data_classification = (
                file_metadata.data_classification or default_acl.data_classification
            )
            sensitivity_labels = file_metadata.sensitivity_labels or default_acl.sensitivity_labels
        else:
            access_control = file_metadata.access_control
            data_classification = (
                file_metadata.data_classification or access_control.data_classification
            )
            sensitivity_labels = (
                file_metadata.sensitivity_labels or access_control.sensitivity_labels
            )

        # 1. 檢查訪問權限是否過期
        if access_control.access_expires_at:
            if datetime.utcnow() > access_control.access_expires_at:
                self._log_access_denied(
                    user, file_metadata, "Access expired", required_permission, request
                )
                return False

        # 2. 數據分類級別檢查（AI治理要求）
        if not self._check_data_classification_access(user, data_classification):
            self._log_access_denied(
                user,
                file_metadata,
                f"Insufficient clearance for {data_classification}",
                required_permission,
                request,
            )
            return False

        # 3. 敏感性標籤檢查（AI治理要求）
        if not self._check_sensitivity_labels_access(user, sensitivity_labels):
            self._log_access_denied(
                user,
                file_metadata,
                "User lacks required sensitivity label access",
                required_permission,
                request,
            )
            return False

        # 4. 檢查用戶是否有基本文件權限
        if not user.has_permission(required_permission):
            # 超級管理員例外
            if not user.has_permission(Permission.ALL.value):
                self._log_access_denied(
                    user,
                    file_metadata,
                    f"User lacks required permission: {required_permission}",
                    required_permission,
                    request,
                )
                return False

        # 5. 按訪問級別檢查權限（優先級從高到低）
        access_level = access_control.access_level

        # 5.1 PUBLIC：全公司可見
        if access_level == FileAccessLevel.PUBLIC.value:
            self._log_access_granted(user, file_metadata, "PUBLIC access", request)
            return True

        # 5.2 ORGANIZATION：組織級授權
        elif access_level == FileAccessLevel.ORGANIZATION.value:
            user_org_id = self._get_user_organization_id(user)
            authorized_orgs = access_control.authorized_organizations or []
            if user_org_id and user_org_id in authorized_orgs:
                self._log_access_granted(user, file_metadata, "ORGANIZATION access", request)
                return True

        # 5.3 SECURITY_GROUP：安全組級授權
        elif access_level == FileAccessLevel.SECURITY_GROUP.value:
            user_security_groups = self._get_user_security_groups(user)
            authorized_groups = access_control.authorized_security_groups or []
            if any(g in authorized_groups for g in user_security_groups):
                self._log_access_granted(user, file_metadata, "SECURITY_GROUP access", request)
                return True

        # 5.4 PRIVATE：私有（默認）
        elif access_level == FileAccessLevel.PRIVATE.value:
            # 檢查用戶是否為文件所有者
            if file_metadata.user_id == user.user_id:
                self._log_access_granted(user, file_metadata, "OWNER access", request)
                return True

            # 檢查用戶是否在授權用戶列表中
            authorized_users = access_control.authorized_users or []
            if user.user_id in authorized_users:
                self._log_access_granted(user, file_metadata, "PRIVATE authorized access", request)
                return True

        # 6. 默認拒絕（最小權限原則）
        self._log_access_denied(
            user,
            file_metadata,
            f"Access level {access_level} check failed",
            required_permission,
            request,
        )
        return False


# 全局服務實例（懶加載）
_file_permission_service: Optional[FilePermissionService] = None


def get_file_permission_service() -> FilePermissionService:
    """獲取文件權限服務實例（單例模式）"""
    global _file_permission_service
    if _file_permission_service is None:
        _file_permission_service = FilePermissionService()
    return _file_permission_service
