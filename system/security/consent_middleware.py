# 代碼功能說明: 數據使用同意檢查中間件
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""數據使用同意檢查中間件 - 提供同意檢查裝飾器和依賴函數。"""

from functools import wraps
from typing import Callable
from fastapi import HTTPException, status, Depends
import structlog

from services.api.models.data_consent import ConsentType
from services.api.services.data_consent_service import get_consent_service
from system.security.dependencies import get_current_user
from system.security.models import User
from system.security.config import get_security_settings

logger = structlog.get_logger(__name__)


def require_consent(consent_type: ConsentType):
    """創建一個需要特定同意的依賴函數。

    此函數可以在路由中使用，例如：
        @router.post("/files/upload")
        async def upload_files(
            user: User = Depends(require_consent(ConsentType.FILE_UPLOAD))
        ):
            ...

    Args:
        consent_type: 需要的同意類型

    Returns:
        依賴函數
    """

    async def check_consent(user: User = Depends(get_current_user)) -> User:
        """檢查用戶是否已同意。

        Args:
            user: 當前用戶（通過 get_current_user 依賴注入）

        Returns:
            User 對象（如果同意檢查通過）

        Raises:
            HTTPException: 如果用戶未同意
        """
        settings = get_security_settings()

        # 開發模式下自動通過同意檢查
        if settings.should_bypass_auth:
            logger.info(
                "Bypassing consent check in development mode",
                user_id=user.user_id,
                consent_type=consent_type.value,
            )
            return user

        # 檢查同意
        service = get_consent_service()
        has_consent = service.check_consent(user.user_id, consent_type)

        if not has_consent:
            logger.warning(
                "Consent check failed",
                user_id=user.user_id,
                consent_type=consent_type.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Consent required: {consent_type.value}. Please grant consent before proceeding.",
            )

        return user

    return check_consent
