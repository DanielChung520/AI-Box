# 代碼功能說明: Agent 註冊申請管理路由
# 創建日期: 2026-01-17 18:27 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 11:15 UTC+8

"""Agent 註冊申請管理路由 - 提供 Agent 申請的提交、查詢、審查批准 API"""

import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, Path, Query, Request, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.agent_registration_request import (
    AgentRegistrationRequestCreate,
    AgentRegistrationRequestUpdate,
    AgentRegistrationStatus,
    ApproveRequest,
    ApproveResponse,
    RejectRequest,
    RevokeRequest,
)
from services.api.models.audit_log import AuditAction
from services.api.services.agent_registration_request_store_service import (
    AgentRegistrationRequestStoreService,
)
from services.api.services.agent_request_notification_service import (
    get_agent_request_notification_service,
)
from services.api.services.cloudflare_kv_permission_service import (
    get_cloudflare_kv_permission_service,
)
from system.security.audit_decorator import audit_log
from system.security.dependencies import get_current_user
from system.security.models import Permission, User

logger = logging.getLogger(__name__)

# 公開路由（申請提交和查詢）
public_router = APIRouter(prefix="/agent-registration", tags=["Agent Registration"])

# 管理員路由（申請審查）
admin_router = APIRouter(prefix="/admin/agent-requests", tags=["Agent Request Management"])


# 創建需要系統管理員權限的依賴函數
async def require_system_admin(user: User = Depends(get_current_user)) -> User:
    """檢查用戶是否擁有系統管理員權限的依賴函數（修改時間：2026-01-18）"""
    from fastapi import HTTPException

    from system.security.config import get_security_settings

    settings = get_security_settings()

    # 開發模式下自動通過權限檢查
    if settings.should_bypass_auth:
        return user

    # 生產模式下進行真實權限檢查
    if not settings.rbac.enabled:
        # 如果 RBAC 未啟用，則所有已認證用戶都可以訪問
        return user

    if not user.has_permission(Permission.ALL.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: system_admin",
        )

    return user


def get_agent_request_service() -> AgentRegistrationRequestStoreService:
    """獲取 AgentRegistrationRequest Store Service 實例"""
    from services.api.services.agent_registration_request_store_service import (
        get_agent_registration_request_store_service,
    )

    return get_agent_registration_request_store_service()


# ============================================
# 公開 API（申請提交和查詢）
# ============================================


@public_router.post("/request", status_code=status.HTTP_201_CREATED)
async def submit_agent_request(
    request_data: AgentRegistrationRequestCreate,
    request: Request,
) -> JSONResponse:
    """
    提交 Agent 註冊申請

    Args:
        request_data: 申請數據
        request: FastAPI Request 對象

    Returns:
        創建的申請信息（包含 request_id）
    """
    try:
        service = get_agent_request_service()

        # 提取 IP 地址和 User-Agent
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        created_request = service.create_request(
            request_data,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info(
            f"Agent registration request submitted: request_id={created_request.request_id}, "
            f"agent_id={created_request.agent_id}"
        )

        # 通知系統管理員有新的申請
        notification_service = get_agent_request_notification_service()
        notification_service.notify_new_request(
            request_id=created_request.request_id,
            agent_name=created_request.agent_name,
            applicant_name=created_request.applicant_info.name,
            applicant_email=created_request.applicant_info.email,
        )

        # 不返回敏感信息
        response_data = created_request.model_dump(mode="json")

        return APIResponse.success(
            data=response_data,
            message="Agent registration request submitted successfully. You will be notified once it is reviewed.",
            status_code=status.HTTP_201_CREATED,
        )
    except ValueError as e:
        logger.warning(f"Failed to submit agent request: {str(e)}")
        return APIResponse.error(
            message=f"Failed to submit agent request: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Failed to submit agent request: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to submit agent request: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@public_router.get("/request/{request_id}", status_code=status.HTTP_200_OK)
async def get_agent_request_status(
    request_id: str = Path(description="申請 ID"),
) -> JSONResponse:
    """
    查詢 Agent 註冊申請狀態

    Args:
        request_id: 申請 ID

    Returns:
        申請信息（不包含敏感信息）
    """
    try:
        service = get_agent_request_service()
        request_obj = service.get_request(request_id)

        if request_obj is None:
            return APIResponse.error(
                message=f"Request '{request_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 不返回敏感信息（secret_key_hash）
        response_data = request_obj.model_dump(mode="json")
        response_data["secret_info"]["secret_key_hash"] = None  # 移除哈希

        return APIResponse.success(
            data=response_data,
            message="Request retrieved successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to get agent request: request_id={request_id}, error={str(e)}", exc_info=True
        )
        return APIResponse.error(
            message=f"Failed to get agent request: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================
# 管理員 API（申請審查）
# ============================================


@admin_router.get("", status_code=status.HTTP_200_OK)
async def list_agent_requests(
    status_filter: Optional[AgentRegistrationStatus] = Query(
        default=None, alias="status", description="申請狀態過濾"
    ),
    tenant_id: Optional[str] = Query(default=None, description="租戶 ID 過濾"),
    limit: Optional[int] = Query(default=100, description="限制返回數量"),
    offset: int = Query(default=0, description="偏移量（用於分頁）"),
    search: Optional[str] = Query(default=None, description="搜索關鍵字（Agent 名稱、ID、申請者郵箱）"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取所有 Agent 申請列表（支持狀態過濾、分頁）

    Args:
        status_filter: 申請狀態過濾
        tenant_id: 租戶 ID 過濾
        limit: 限制返回數量
        offset: 偏移量
        search: 搜索關鍵字
        current_user: 當前認證用戶

    Returns:
        申請列表
    """
    try:
        service = get_agent_request_service()

        requests, total = service.list_requests(
            status=status_filter,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
            search=search,
        )

        # 移除敏感信息
        request_dicts = []
        for req in requests:
            req_dict = req.model_dump(mode="json")
            req_dict["secret_info"]["secret_key_hash"] = None  # 移除哈希
            request_dicts.append(req_dict)

        return APIResponse.success(
            data={"requests": request_dicts, "total": total, "limit": limit, "offset": offset},
            message="Agent requests retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to list agent requests: error={str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to list agent requests: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@admin_router.get("/{request_id}", status_code=status.HTTP_200_OK)
async def get_agent_request(
    request_id: str = Path(description="申請 ID"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取 Agent 申請詳情

    Args:
        request_id: 申請 ID
        current_user: 當前認證用戶

    Returns:
        申請詳情
    """
    try:
        service = get_agent_request_service()
        request_obj = service.get_request(request_id)

        if request_obj is None:
            return APIResponse.error(
                message=f"Request '{request_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 移除敏感信息
        response_data = request_obj.model_dump(mode="json")
        response_data["secret_info"]["secret_key_hash"] = None  # 移除哈希

        return APIResponse.success(
            data=response_data,
            message="Request retrieved successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to get agent request: request_id={request_id}, error={str(e)}", exc_info=True
        )
        return APIResponse.error(
            message=f"Failed to get agent request: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@admin_router.post("/{request_id}/approve", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="agent_registration_request",
    get_resource_id=lambda request_id: request_id,
)
async def approve_agent_request(
    request_id: str = Path(description="申請 ID"),
    approve_data: ApproveRequest = Body(default=ApproveRequest(review_notes=None)),
    secret_expires_days: Optional[int] = Query(
        default=None, description="Secret 過期天數（可選，None 表示永不過期）"
    ),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    批准 Agent 註冊申請

    Args:
        request_id: 申請 ID
        approve_data: 批准數據
        secret_expires_days: Secret 過期天數
        current_user: 當前認證用戶

    Returns:
        批准結果（包含 Secret ID/Key，僅此一次返回）
    """
    try:
        service = get_agent_request_service()

        # 批准申請並生成 Secret
        approved_request, secret_key = service.approve_request(
            request_id=request_id,
            reviewed_by=current_user.user_id,
            review_notes=approve_data.review_notes,
            secret_expires_days=secret_expires_days,
        )

        logger.info(
            f"Agent registration request approved: request_id={request_id}, "
            f"agent_id={approved_request.agent_id}, "
            f"secret_id={approved_request.secret_info.secret_id}"
        )

        # 配置 Cloudflare KV Store 權限
        kv_permission_service = get_cloudflare_kv_permission_service()
        permissions_set = await kv_permission_service.set_agent_permissions(
            tenant_id=approved_request.tenant_id,
            agent_id=approved_request.agent_id,
            permissions=(
                approved_request.requested_permissions.model_dump(mode="json")
                if approved_request.requested_permissions
                else {}
            ),
        )
        if not permissions_set:
            logger.warning(
                f"Failed to set Cloudflare KV permissions for agent: agent_id={approved_request.agent_id}"
            )

        # 通知申請者申請已批准
        notification_service = get_agent_request_notification_service()
        notification_service.notify_request_approved(
            request_id=approved_request.request_id,
            agent_name=approved_request.agent_name,
            applicant_email=approved_request.applicant_info.email,
            secret_id=approved_request.secret_info.secret_id or "",
        )

        # 構建響應（包含 Secret Key，僅此一次）
        response = ApproveResponse(
            request_id=approved_request.request_id,
            agent_id=approved_request.agent_id,
            secret_id=approved_request.secret_info.secret_id or "",
            secret_key=secret_key,
        )

        return APIResponse.success(
            data=response.model_dump(mode="json"),
            message="Agent registration request approved successfully. Please copy the Secret Key immediately as it will not be shown again.",
            status_code=status.HTTP_200_OK,
        )
    except ValueError as e:
        logger.warning(f"Failed to approve agent request: request_id={request_id}, error={str(e)}")
        return APIResponse.error(
            message=f"Failed to approve agent request: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(
            f"Failed to approve agent request: request_id={request_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to approve agent request: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@admin_router.post("/{request_id}/reject", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="agent_registration_request",
    get_resource_id=lambda request_id: request_id,
)
async def reject_agent_request(
    request_id: str = Path(description="申請 ID"),
    reject_data: RejectRequest = Body(...),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    拒絕 Agent 註冊申請

    Args:
        request_id: 申請 ID
        reject_data: 拒絕數據（包含拒絕原因）
        current_user: 當前認證用戶

    Returns:
        拒絕結果
    """
    try:
        service = get_agent_request_service()

        rejected_request = service.reject_request(
            request_id=request_id,
            reviewed_by=current_user.user_id,
            rejection_reason=reject_data.rejection_reason,
            review_notes=reject_data.review_notes,
        )

        if rejected_request is None:
            return APIResponse.error(
                message=f"Request '{request_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(
            f"Agent registration request rejected: request_id={request_id}, "
            f"agent_id={rejected_request.agent_id}"
        )

        # 通知申請者申請已拒絕
        notification_service = get_agent_request_notification_service()
        notification_service.notify_request_rejected(
            request_id=rejected_request.request_id,
            agent_name=rejected_request.agent_name,
            applicant_email=rejected_request.applicant_info.email,
            rejection_reason=reject_data.rejection_reason,
        )

        # 移除敏感信息
        response_data = rejected_request.model_dump(mode="json")
        response_data["secret_info"]["secret_key_hash"] = None

        return APIResponse.success(
            data=response_data,
            message="Agent registration request rejected successfully",
        )
    except ValueError as e:
        logger.warning(f"Failed to reject agent request: request_id={request_id}, error={str(e)}")
        return APIResponse.error(
            message=f"Failed to reject agent request: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(
            f"Failed to reject agent request: request_id={request_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to reject agent request: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@admin_router.post("/{request_id}/revoke", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="agent_registration_request",
    get_resource_id=lambda request_id: request_id,
)
async def revoke_agent_request(
    request_id: str = Path(description="申請 ID"),
    revoke_data: RevokeRequest = Body(...),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    撤銷已批准的 Agent 註冊申請

    Args:
        request_id: 申請 ID
        revoke_data: 撤銷數據（包含撤銷原因）
        current_user: 當前認證用戶

    Returns:
        撤銷結果
    """
    try:
        service = get_agent_request_service()

        revoked_request = service.revoke_request(
            request_id=request_id,
            revoked_by=current_user.user_id,
            revoke_reason=revoke_data.revoke_reason,
        )

        if revoked_request is None:
            return APIResponse.error(
                message=f"Request '{request_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(
            f"Agent registration request revoked: request_id={request_id}, "
            f"agent_id={revoked_request.agent_id}"
        )

        # 移除 Cloudflare KV Store 權限
        kv_permission_service = get_cloudflare_kv_permission_service()
        permissions_deleted = await kv_permission_service.delete_agent_permissions(
            tenant_id=revoked_request.tenant_id,
            agent_id=revoked_request.agent_id,
        )
        if not permissions_deleted:
            logger.warning(
                f"Failed to delete Cloudflare KV permissions for agent: agent_id={revoked_request.agent_id}"
            )

        # 通知申請者申請已撤銷
        notification_service = get_agent_request_notification_service()
        notification_service.notify_request_revoked(
            request_id=revoked_request.request_id,
            agent_name=revoked_request.agent_name,
            applicant_email=revoked_request.applicant_info.email,
            revoke_reason=revoke_data.revoke_reason,
        )

        # 移除敏感信息
        response_data = revoked_request.model_dump(mode="json")
        response_data["secret_info"]["secret_key_hash"] = None

        return APIResponse.success(
            data=response_data,
            message="Agent registration request revoked successfully",
        )
    except ValueError as e:
        logger.warning(f"Failed to revoke agent request: request_id={request_id}, error={str(e)}")
        return APIResponse.error(
            message=f"Failed to revoke agent request: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(
            f"Failed to revoke agent request: request_id={request_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to revoke agent request: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@admin_router.put("/{request_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="agent_registration_request",
    get_resource_id=lambda request_id: request_id,
)
async def update_agent_request(
    request_id: str = Path(description="申請 ID"),
    request_data: AgentRegistrationRequestUpdate = Body(...),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    更新 Agent 申請信息（僅 pending 狀態可更新）

    Args:
        request_id: 申請 ID
        request_data: 申請更新數據
        current_user: 當前認證用戶

    Returns:
        更新後的申請信息
    """
    try:
        service = get_agent_request_service()

        updated_request = service.update_request(request_id, request_data)

        if updated_request is None:
            return APIResponse.error(
                message=f"Request '{request_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"Agent registration request updated: request_id={request_id}")

        # 移除敏感信息
        response_data = updated_request.model_dump(mode="json")
        response_data["secret_info"]["secret_key_hash"] = None

        return APIResponse.success(
            data=response_data,
            message="Agent registration request updated successfully",
        )
    except ValueError as e:
        logger.warning(f"Failed to update agent request: request_id={request_id}, error={str(e)}")
        return APIResponse.error(
            message=f"Failed to update agent request: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(
            f"Failed to update agent request: request_id={request_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to update agent request: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@admin_router.get("/{request_id}/audit-log", status_code=status.HTTP_200_OK)
async def get_request_audit_log(
    request_id: str = Path(description="申請 ID"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    查看申請的審計日誌

    Args:
        request_id: 申請 ID
        current_user: 當前認證用戶

    Returns:
        審計日誌列表
    """
    try:
        from services.api.services.audit_log_service import get_audit_log_service

        audit_service = get_audit_log_service()

        # 查詢相關審計日誌
        logs = audit_service.query_logs(
            resource_type="agent_registration_request",
            resource_id=request_id,
            limit=100,
        )

        return APIResponse.success(
            data={"audit_logs": logs, "total": len(logs)},
            message="Audit logs retrieved successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to get audit log for agent request: request_id={request_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to get audit log: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
