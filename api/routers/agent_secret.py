# 代碼功能說明: Agent Secret API 路由
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Secret API 路由 - 提供 Secret ID/Key 驗證接口"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.core.response import APIResponse
from agents.services.auth.secret_manager import get_secret_manager
from system.security.dependencies import get_current_user
from system.security.models import User

router = APIRouter()


class SecretVerificationRequest(BaseModel):
    """Secret 驗證請求"""

    secret_id: str = Field(..., description="Secret ID")
    secret_key: str = Field(..., description="Secret Key")


class SecretGenerationRequest(BaseModel):
    """Secret 生成請求（用於測試，未來應改為審批流程）"""

    organization: Optional[str] = Field(None, description="組織名稱")


@router.post("/agents/secrets/verify", status_code=http_status.HTTP_200_OK)
async def verify_secret(
    request: SecretVerificationRequest,
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    驗證 Secret ID/Key

    用於在 Agent 註冊前驗證 Secret 憑證的有效性。

    Args:
        request: Secret 驗證請求
        user: 當前認證用戶（可選）

    Returns:
        驗證結果
    """
    try:
        secret_manager = get_secret_manager()

        # 驗證 Secret
        is_valid = secret_manager.verify_secret(request.secret_id, request.secret_key)

        if not is_valid:
            return APIResponse.error(
                message="Invalid Secret ID or Secret Key",
                error_code="INVALID_SECRET",
                status_code=http_status.HTTP_401_UNAUTHORIZED,
            )

        # 檢查是否已綁定
        is_bound = secret_manager.is_secret_bound(request.secret_id)

        # 獲取 Secret 信息（不包含敏感信息）
        secret_info = secret_manager.get_secret_info(request.secret_id)

        return APIResponse.success(
            data={
                "valid": True,
                "secret_id": request.secret_id,
                "is_bound": is_bound,
                "secret_info": secret_info,
            },
            message="Secret verified successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Secret verification failed: {str(e)}",
        )


@router.post("/agents/secrets/generate", status_code=http_status.HTTP_201_CREATED)
async def generate_secret(
    request: SecretGenerationRequest,
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    生成 Secret ID/Key 對（用於測試和開發）

    注意：在生產環境中，這應該通過審批流程進行。
    此端點僅用於測試和開發環境。

    Args:
        request: Secret 生成請求
        user: 當前認證用戶（可選）

    Returns:
        Secret ID 和 Secret Key

    警告：Secret Key 只在生成時返回一次，請妥善保管！
    """
    try:
        secret_manager = get_secret_manager()

        # 生成 Secret 對
        secret_id, secret_key = secret_manager.generate_secret_pair(
            organization=request.organization
        )

        return APIResponse.success(
            data={
                "secret_id": secret_id,
                "secret_key": secret_key,  # 注意：僅在生成時返回一次
                "warning": "Please save the secret_key securely. It will not be shown again.",
            },
            message="Secret pair generated successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Secret generation failed: {str(e)}",
        )


@router.get("/agents/secrets/{secret_id}", status_code=http_status.HTTP_200_OK)
async def get_secret_info(
    secret_id: str,
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取 Secret 信息（不包含敏感信息）

    Args:
        secret_id: Secret ID
        user: 當前認證用戶（可選）

    Returns:
        Secret 信息
    """
    try:
        secret_manager = get_secret_manager()
        secret_info = secret_manager.get_secret_info(secret_id)

        if not secret_info:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Secret ID not found: {secret_id}",
            )

        return APIResponse.success(
            data=secret_info,
            message="Secret info retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get secret info: {str(e)}",
        )
