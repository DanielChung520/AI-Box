# 代碼功能說明: 數據使用同意路由
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""數據使用同意路由 - 提供同意記錄、查詢和撤銷功能。"""

from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
import structlog

from api.core.response import APIResponse
from services.api.models.data_consent import (
    DataConsentCreate,
    DataConsentResponse,
    ConsentType,
)
from services.api.services.data_consent_service import get_consent_service
from system.security.dependencies import get_current_user
from system.security.models import User
from system.security.audit_decorator import audit_log
from services.api.models.audit_log import AuditAction
from fastapi import Request

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/consent", tags=["Data Consent"])


@router.post("", response_model=DataConsentResponse)
@audit_log(
    action=AuditAction.CONSENT_GRANTED,
    resource_type="consent",
    get_resource_id=lambda body: body.get("data", {}).get("consent_type"),
)
async def record_consent(
    consent_create: DataConsentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """記錄用戶同意狀態。

    Args:
        consent_create: 同意創建請求
        current_user: 當前認證用戶

    Returns:
        創建的同意記錄
    """
    service = get_consent_service()
    consent = service.record_consent(current_user.user_id, consent_create)

    logger.info(
        "Consent recorded",
        user_id=current_user.user_id,
        consent_type=consent.consent_type.value,
        granted=consent.granted,
    )

    return APIResponse.success(
        data=DataConsentResponse(
            user_id=consent.user_id,
            consent_type=consent.consent_type,
            purpose=consent.purpose,
            granted=consent.granted,
            timestamp=consent.timestamp,
            expires_at=consent.expires_at,
        ),
        message="Consent recorded successfully",
    )


@router.get("", response_model=List[DataConsentResponse])
async def get_user_consents(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """查詢當前用戶的所有同意狀態。

    Args:
        current_user: 當前認證用戶

    Returns:
        用戶的所有同意記錄列表
    """
    service = get_consent_service()
    consents = service.get_user_consents(current_user.user_id)

    return APIResponse.success(
        data=[
            DataConsentResponse(
                user_id=c.user_id,
                consent_type=c.consent_type,
                purpose=c.purpose,
                granted=c.granted,
                timestamp=c.timestamp,
                expires_at=c.expires_at,
            )
            for c in consents
        ],
        message="Consents retrieved successfully",
    )


@router.get("/{consent_type}", response_model=DataConsentResponse)
async def get_consent_by_type(
    consent_type: ConsentType,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """查詢當前用戶的特定類型同意狀態。

    Args:
        consent_type: 同意類型
        current_user: 當前認證用戶

    Returns:
        同意記錄
    """
    service = get_consent_service()
    has_consent = service.check_consent(current_user.user_id, consent_type)

    if not has_consent:
        # 返回未同意的記錄
        return APIResponse.success(
            data=DataConsentResponse(
                user_id=current_user.user_id,
                consent_type=consent_type,
                purpose="",
                granted=False,
                timestamp=None,
                expires_at=None,
            ),
            message="Consent not granted",
        )

    # 獲取完整的同意記錄
    consents = service.get_user_consents(current_user.user_id)
    consent = next((c for c in consents if c.consent_type == consent_type), None)

    if consent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent record not found",
        )

    return APIResponse.success(
        data=DataConsentResponse(
            user_id=consent.user_id,
            consent_type=consent.consent_type,
            purpose=consent.purpose,
            granted=consent.granted,
            timestamp=consent.timestamp,
            expires_at=consent.expires_at,
        ),
        message="Consent retrieved successfully",
    )


@router.delete("/{consent_type}")
@audit_log(
    action=AuditAction.CONSENT_REVOKED,
    resource_type="consent",
    get_resource_id=lambda body: body.get("data", {}).get("consent_type")
    if body and body.get("data")
    else None,
)
async def revoke_consent(
    consent_type: ConsentType,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """撤銷用戶的特定類型同意。

    Args:
        consent_type: 同意類型
        current_user: 當前認證用戶

    Returns:
        撤銷成功的響應
    """
    service = get_consent_service()
    success = service.revoke_consent(current_user.user_id, consent_type)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent record not found",
        )

    logger.info(
        "Consent revoked",
        user_id=current_user.user_id,
        consent_type=consent_type.value,
    )

    return APIResponse.success(
        data={"consent_type": consent_type.value},
        message="Consent revoked successfully",
    )
