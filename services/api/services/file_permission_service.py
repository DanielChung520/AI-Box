# 代碼功能說明: 文件權限檢查服務
# 創建日期: 2025-12-06 15:20 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-09 16:45 (UTC+8)

"""文件權限檢查服務 - 實現文件級別的訪問權限控制"""

from typing import Optional, List
from fastapi import HTTPException, status
import structlog

from system.security.models import User, Permission
from services.api.models.file_metadata import FileMetadata
from services.api.services.file_metadata_service import (
    FileMetadataService,
    get_metadata_service,
)
from services.api.services.user_task_service import get_user_task_service

logger = structlog.get_logger(__name__)


class FilePermissionService:
    """文件權限檢查服務"""

    def __init__(self, metadata_service: Optional[FileMetadataService] = None):
        """
        初始化文件權限服務

        Args:
            metadata_service: 文件元數據服務（可選，如果不提供則自動創建）
        """
        self.metadata_service: FileMetadataService = (
            metadata_service or get_metadata_service()
        )
        self.logger = logger

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
        allowed_permissions_str: List[str] = [
            str(p) for p in allowed_permissions if p is not None
        ]

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
                permissions=user.permissions
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


# 全局服務實例（懶加載）
_file_permission_service: Optional[FilePermissionService] = None


def get_file_permission_service() -> FilePermissionService:
    """獲取文件權限服務實例（單例模式）"""
    global _file_permission_service
    if _file_permission_service is None:
        _file_permission_service = FilePermissionService()
    return _file_permission_service
