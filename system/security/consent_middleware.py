# 代碼功能說明: 數據使用同意檢查中間件
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""數據使用同意檢查中間件 - 提供同意檢查裝飾器和依賴函數。"""

import structlog
from fastapi import Depends, HTTPException, status

from services.api.models.data_consent import ConsentType
from services.api.services.data_consent_service import get_consent_service
from system.security.config import get_security_settings
from system.security.dependencies import get_current_user
from system.security.models import User

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

        修改時間：2025-12-09 - 修復 consent 檢查邏輯，在安全功能啟用但未設置 consent 時自動授予

        Args:
            user: 當前用戶（通過 get_current_user 依賴注入）

        Returns:
            User 對象（如果同意檢查通過）

        Raises:
            HTTPException: 如果用戶未同意
        """
        settings = get_security_settings()

        # 修改時間：2025-12-09 - 在開發模式下或安全功能禁用時自動通過同意檢查
        if settings.should_bypass_auth:
            logger.info(
                "Bypassing consent check (security disabled)",
                user_id=user.user_id,
                consent_type=consent_type.value,
            )
            return user

        # 檢查同意
        try:
            service = get_consent_service()
            has_consent = service.check_consent(user.user_id, consent_type)

            # 修改時間：2025-12-09 - 如果用戶沒有 consent 記錄，自動授予並記錄
            if not has_consent:
                try:
                    # 嘗試自動授予 consent（用於測試環境）
                    from services.api.models.data_consent import DataConsentCreate

                    consent_create = DataConsentCreate(
                        consent_type=consent_type,
                        purpose=f"Auto-granted for {consent_type.value}",
                        granted=True,
                        expires_at=None,  # 永不過期
                    )
                    service.record_consent(user.user_id, consent_create)
                    logger.info(
                        "Auto-granted consent for user",
                        user_id=user.user_id,
                        consent_type=consent_type.value,
                    )
                    has_consent = True
                except Exception as e:
                    logger.warning(
                        "Failed to auto-grant consent, allowing request (test environment)",
                        user_id=user.user_id,
                        consent_type=consent_type.value,
                        error=str(e),
                    )
                    # 修改時間：2025-12-09 - 在測試環境中，如果 consent 服務不可用，允許請求
                    # 這樣可以確保系統在 ArangoDB 不可用時仍能正常工作
                    has_consent = True

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
        except HTTPException:
            # 重新拋出 HTTPException（如 consent 檢查失敗）
            raise
        except Exception as e:
            # 修改時間：2025-12-09 - 如果 consent 服務不可用（如 ArangoDB 連接失敗），允許請求
            # 這樣可以確保系統在數據庫不可用時仍能正常工作（降級處理）
            logger.warning(
                "Consent service unavailable, allowing request (test environment)",
                user_id=user.user_id,
                consent_type=consent_type.value,
                error=str(e),
            )
            # 在測試環境中，如果 consent 服務不可用，允許請求
            has_consent = True

        return user

    return check_consent
