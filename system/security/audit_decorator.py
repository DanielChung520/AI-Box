# 代碼功能說明: 審計日誌裝飾器
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""審計日誌裝飾器 - 自動記錄 API 調用。"""

from functools import wraps
from typing import Callable, Any, Optional, Dict
from fastapi import Request
import structlog

from services.api.models.audit_log import AuditLogCreate, AuditAction
from services.api.services.audit_log_service import get_audit_log_service
from system.security.dependencies import get_current_user
from system.security.models import User
from system.security.config import get_security_settings

logger = structlog.get_logger(__name__)


def audit_log(
    action: AuditAction,
    resource_type: str,
    get_resource_id: Optional[Callable] = None,
    filter_sensitive: bool = True,
):
    """審計日誌裝飾器。

    自動記錄 API 調用的審計日誌，包括用戶信息、IP 地址、User-Agent 等。

    使用示例：
        @router.post("/files/upload")
        @audit_log(AuditAction.FILE_UPLOAD, "file")
        async def upload_files(
            files: List[UploadFile],
            request: Request,
            current_user: User = Depends(get_current_user)
        ):
            ...

    Args:
        action: 審計操作類型
        resource_type: 資源類型（file, task, etc.）
        get_resource_id: 可選函數，用於從響應中提取資源ID
        filter_sensitive: 是否過濾敏感信息（默認為 True）

    Returns:
        裝飾器函數
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            settings = get_security_settings()

            # 開發模式下可選記錄日誌
            if settings.should_bypass_auth:
                # 開發模式仍然記錄，但使用開發用戶
                pass

            # 提取請求對象和用戶
            request: Optional[Request] = None
            current_user: Optional[User] = None

            # 從參數中提取 Request 和 User
            # FastAPI 會將 Request 和 User 作為參數注入
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            for key, value in kwargs.items():
                if isinstance(value, Request):
                    request = value
                elif isinstance(value, User):
                    current_user = value
                elif key == "request" and isinstance(value, Request):
                    request = value

            # 如果沒有找到用戶，嘗試獲取用戶
            # 注意：對於登錄等不需要認證的端點，如果獲取失敗則記錄為匿名
            if current_user is None and request:
                try:
                    # 嘗試獲取用戶（在開發模式下會返回開發用戶，不會失敗）
                    current_user = await get_current_user(request)
                except Exception as e:
                    # 如果獲取用戶失敗（如登錄端點不需要認證），記錄為匿名
                    # 這是正常的，因為登錄端點不需要認證
                    logger.debug(
                        "Could not get current user for audit log (this is normal for login endpoints)",
                        error=str(e),
                        action=action.value,
                    )
                    current_user = None

            # 執行被裝飾的函數
            try:
                response = await func(*args, **kwargs)
            except Exception as e:
                # 記錄錯誤
                if current_user and request:
                    _log_audit_event(
                        action=action,
                        resource_type=resource_type,
                        resource_id=None,
                        user_id=current_user.user_id if current_user else "anonymous",
                        request=request,
                        details={"error": str(e)},
                    )
                raise

            # 提取資源ID（如果提供了函數）
            resource_id: Optional[str] = None
            if get_resource_id and response:
                try:
                    if hasattr(response, "body"):
                        # 處理 JSONResponse
                        import json

                        body = json.loads(response.body.decode())
                        resource_id = get_resource_id(body)
                    elif isinstance(response, dict):
                        resource_id = get_resource_id(response)
                except Exception as e:
                    logger.warning("Failed to extract resource_id", error=str(e))

            # 記錄審計日誌
            if current_user and request:
                details: dict = {}
                if hasattr(response, "status_code"):
                    details["status_code"] = response.status_code

                _log_audit_event(
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    user_id=current_user.user_id,
                    request=request,
                    details=details,
                    filter_sensitive=filter_sensitive,
                )

            return response

        return wrapper

    return decorator


def _log_audit_event(
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[str],
    user_id: str,
    request: Request,
    details: dict,
    filter_sensitive: bool = True,
) -> None:
    """記錄審計事件。

    Args:
        action: 審計操作類型
        resource_type: 資源類型
        resource_id: 資源ID
        user_id: 用戶ID
        request: FastAPI Request 對象
        details: 額外詳情
        filter_sensitive: 是否過濾敏感信息
    """
    try:
        # 獲取 IP 地址
        ip_address = request.client.host if request.client else "unknown"

        # 獲取 User-Agent
        user_agent = request.headers.get("user-agent", "unknown")

        # 過濾敏感信息
        if filter_sensitive:
            filtered_details = _filter_sensitive_data(details)
        else:
            filtered_details = details

        # 創建審計日誌記錄
        log_create = AuditLogCreate(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=filtered_details,
        )

        # 異步記錄日誌
        service = get_audit_log_service()
        service.log(log_create, async_mode=True)

    except Exception as e:
        logger.error("Failed to log audit event", error=str(e))
        # 不拋出異常，避免影響主流程


def _filter_sensitive_data(data: dict) -> dict:
    """過濾敏感信息。

    Args:
        data: 原始數據

    Returns:
        過濾後的數據
    """
    sensitive_keys = {
        "password",
        "token",
        "secret",
        "api_key",
        "authorization",
        "cookie",
        "session",
    }

    filtered: Dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            filtered[key] = "[FILTERED]"
        elif isinstance(value, dict):
            filtered[key] = _filter_sensitive_data(value)
        elif isinstance(value, list):
            filtered[key] = [
                _filter_sensitive_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            filtered[key] = value

    return filtered
