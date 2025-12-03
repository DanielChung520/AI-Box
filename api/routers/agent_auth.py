# 代碼功能說明: Agent 認證 API 路由
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent 認證 API 路由 - 提供 Agent 認證和權限檢查接口"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from agents.services.auth.internal_auth import authenticate_internal_agent
from agents.services.auth.external_auth import authenticate_external_agent
from agents.services.auth.models import AuthenticationResult, AuthenticationStatus
from agents.services.resource_controller import get_resource_controller, ResourceType
from system.security.dependencies import get_current_user
from system.security.models import User

router = APIRouter()


@router.post("/agents/{agent_id}/auth/internal", status_code=http_status.HTTP_200_OK)
async def authenticate_internal(
    agent_id: str,
    service_identity: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    認證內部 Agent

    Args:
        agent_id: Agent ID
        service_identity: 服務標識（可選，用於額外驗證）
        user: 當前認證用戶（可選）

    Returns:
        認證結果
    """
    try:
        result = await authenticate_internal_agent(
            agent_id=agent_id,
            service_identity=service_identity,
        )

        if result.status == AuthenticationStatus.SUCCESS:
            return APIResponse.success(
                data=result.model_dump(mode="json"),
                message="Internal agent authenticated successfully",
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail=result.error or result.message,
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal authentication failed: {str(e)}",
        )


@router.post("/agents/{agent_id}/auth/external", status_code=http_status.HTTP_200_OK)
async def authenticate_external(
    agent_id: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    認證外部 Agent

    執行多層認證檢查：
    1. mTLS 證書驗證
    2. API Key 驗證
    3. 請求簽名驗證（HMAC-SHA256）
    4. IP 白名單檢查
    5. 服務器指紋驗證

    Args:
        agent_id: Agent ID
        request: FastAPI Request 對象（用於提取請求信息）
        user: 當前認證用戶（可選）

    Returns:
        認證結果
    """
    try:
        # 從請求中提取認證信息
        request_ip = request.client.host if request.client else None

        # 從請求頭提取 API Key 和簽名
        api_key_header = request.headers.get("Authorization", "").replace("Bearer ", "")
        request_signature = request.headers.get("X-Request-Signature")

        # 從請求體提取數據（用於簽名驗證）
        request_body = None
        try:
            request_body = await request.json()
        except Exception:
            pass

        # 從請求頭提取客戶端證書（簡化實現，實際應從 TLS 連接中提取）
        client_certificate = request.headers.get("X-Client-Certificate")
        server_fingerprint = request.headers.get("X-Server-Fingerprint")

        result = await authenticate_external_agent(
            agent_id=agent_id,
            request_ip=request_ip,
            request_signature=request_signature,
            request_body=request_body,
            client_certificate=client_certificate,
            api_key_header=api_key_header,
            server_fingerprint=server_fingerprint,
        )

        if result.status == AuthenticationStatus.SUCCESS:
            return APIResponse.success(
                data=result.model_dump(mode="json"),
                message="External agent authenticated successfully",
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail=result.error or result.message,
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"External authentication failed: {str(e)}",
        )


@router.post(
    "/agents/{agent_id}/auth/resource-access", status_code=http_status.HTTP_200_OK
)
async def check_resource_access(
    agent_id: str,
    resource_type: str,
    resource_name: str,
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    檢查 Agent 對特定資源的訪問權限

    Args:
        agent_id: Agent ID
        resource_type: 資源類型（memory, tool, llm, database, file）
        resource_name: 資源名稱
        user: 當前認證用戶（可選）

    Returns:
        權限檢查結果
    """
    try:
        resource_controller = get_resource_controller()

        # 將字符串轉換為 ResourceType 枚舉
        try:
            resource_type_enum = ResourceType(resource_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid resource type: {resource_type}. Valid types: {', '.join([rt.value for rt in ResourceType])}",
            )

        has_access = resource_controller.check_access(
            agent_id=agent_id,
            resource_type=resource_type_enum,
            resource_name=resource_name,
        )

        return APIResponse.success(
            data={
                "agent_id": agent_id,
                "resource_type": resource_type,
                "resource_name": resource_name,
                "has_access": has_access,
            },
            message=f"Resource access check completed: {'allowed' if has_access else 'denied'}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resource access check failed: {str(e)}",
        )
