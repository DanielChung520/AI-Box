# 代碼功能說明: Chat 附件權限驗證（調用 FilePermissionService）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""validate_attachments_access：校驗用戶有權訪問請求中的附件。"""

import logging
from typing import List, Optional

from fastapi import HTTPException
from services.api.models.chat import ChatAttachment
from system.security.models import Permission, User

logger = logging.getLogger(__name__)


async def validate_attachments_access(
    attachments: Optional[List[ChatAttachment]],
    user: User,
) -> None:
    """
    校驗用戶對所有附件的訪問權限；無權則 raise HTTPException(403)。

    Args:
        attachments: 附件列表，None 或空則直接通過
        user: 當前用戶

    Raises:
        HTTPException: 403 當某附件無權訪問
    """
    if not attachments:
        return
    from api.routers.chat_module.dependencies import get_file_permission_service

    permission_service = get_file_permission_service()
    for att in attachments:
        try:
            permission_service.check_file_access(
                user=user,
                file_id=att.file_id,
                required_permission=Permission.FILE_READ.value,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning(
                f"Attachment permission check failed: file_id={att.file_id}, error={str(exc)}"
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error_code": "AUTHORIZATION_ERROR",
                    "message": f"無權訪問附件 {att.file_id}",
                },
            ) from exc
