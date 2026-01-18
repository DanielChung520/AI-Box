# 代碼功能說明: 服務告警路由
# 創建日期: 2026-01-17 19:41 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 11:15 UTC+8

"""服務告警路由 - 提供服務告警規則和告警管理 API"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Path, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.audit_log import AuditAction
from services.api.models.service_alert import AlertRule, AlertSeverity, AlertStatus
from services.api.services.service_alert_service import get_service_alert_service
from system.security.audit_decorator import audit_log
from system.security.dependencies import get_current_user
from system.security.models import Permission, User

logger = structlog.get_logger(__name__)


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


router = APIRouter(prefix="/admin/service-alerts", tags=["Service Alert"])


@router.get("/rules", status_code=status.HTTP_200_OK)
async def list_alert_rules(
    service_name: Optional[str] = Query(default=None, description="服務名稱過濾"),
    enabled: Optional[bool] = Query(default=None, description="是否啟用過濾"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取告警規則列表

    Args:
        service_name: 服務名稱過濾（可選）
        enabled: 是否啟用過濾（可選）
        current_user: 當前認證用戶

    Returns:
        告警規則列表
    """
    try:
        service = get_service_alert_service()
        rules = service.list_alert_rules(service_name=service_name, enabled=enabled)

        rules_dicts = [rule.model_dump(mode="json") for rule in rules]

        return APIResponse.success(
            data={"rules": rules_dicts, "total": len(rules_dicts)},
            message="Alert rules retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to list alert rules: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to list alert rules: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/rules", status_code=status.HTTP_201_CREATED)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="alert_rule",
    get_resource_id=lambda body: body.get("data", {}).get("rule_id"),
)
async def create_alert_rule(
    rule: AlertRule,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    創建告警規則

    Args:
        rule: 告警規則
        current_user: 當前認證用戶

    Returns:
        創建的告警規則
    """
    try:
        service = get_service_alert_service()
        created_rule = service.create_alert_rule(rule)

        logger.info(f"Alert rule created: rule_id={created_rule.rule_id}")

        return APIResponse.success(
            data=created_rule.model_dump(mode="json"),
            message="Alert rule created successfully",
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        logger.error(f"Failed to create alert rule: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to create alert rule: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/rules/{rule_id}", status_code=status.HTTP_200_OK)
async def get_alert_rule(
    rule_id: str = Path(description="規則 ID"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取告警規則詳情

    Args:
        rule_id: 規則 ID
        current_user: 當前認證用戶

    Returns:
        告警規則詳情
    """
    try:
        service = get_service_alert_service()
        rule = service.get_alert_rule(rule_id)

        if rule is None:
            return APIResponse.error(
                message=f"Alert rule '{rule_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return APIResponse.success(
            data=rule.model_dump(mode="json"),
            message="Alert rule retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to get alert rule: rule_id={rule_id}, error={str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to get alert rule: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.put("/rules/{rule_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="alert_rule",
    get_resource_id=lambda rule_id: rule_id,
)
async def update_alert_rule(
    rule_id: str = Path(description="規則 ID"),
    updates: dict = None,  # type: ignore
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    更新告警規則

    Args:
        rule_id: 規則 ID
        updates: 更新字段
        current_user: 當前認證用戶

    Returns:
        更新後的告警規則
    """
    try:
        service = get_service_alert_service()

        if updates is None:
            return APIResponse.error(
                message="Updates are required",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        updated_rule = service.update_alert_rule(rule_id, updates)

        if updated_rule is None:
            return APIResponse.error(
                message=f"Alert rule '{rule_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"Alert rule updated: rule_id={rule_id}")

        return APIResponse.success(
            data=updated_rule.model_dump(mode="json"),
            message="Alert rule updated successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to update alert rule: rule_id={rule_id}, error={str(e)}", exc_info=True
        )
        return APIResponse.error(
            message=f"Failed to update alert rule: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/rules/{rule_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="alert_rule",
    get_resource_id=lambda rule_id: rule_id,
)
async def delete_alert_rule(
    rule_id: str = Path(description="規則 ID"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    刪除告警規則

    Args:
        rule_id: 規則 ID
        current_user: 當前認證用戶

    Returns:
        刪除結果
    """
    try:
        service = get_service_alert_service()
        success = service.delete_alert_rule(rule_id)

        if not success:
            return APIResponse.error(
                message=f"Alert rule '{rule_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"Alert rule deleted: rule_id={rule_id}")

        return APIResponse.success(
            data={"rule_id": rule_id},
            message="Alert rule deleted successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to delete alert rule: rule_id={rule_id}, error={str(e)}", exc_info=True
        )
        return APIResponse.error(
            message=f"Failed to delete alert rule: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("", status_code=status.HTTP_200_OK)
async def list_alerts(
    service_name: Optional[str] = Query(default=None, description="服務名稱過濾"),
    status: Optional[str] = Query(
        default=None, description="狀態過濾（active/resolved/acknowledged/suppressed）"
    ),
    severity: Optional[str] = Query(default=None, description="嚴重程度過濾（critical/high/medium/low）"),
    limit: Optional[int] = Query(default=100, description="限制返回數量"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取告警列表

    Args:
        service_name: 服務名稱過濾（可選）
        status: 狀態過濾（可選）
        severity: 嚴重程度過濾（可選）
        limit: 限制返回數量（可選）
        current_user: 當前認證用戶

    Returns:
        告警列表
    """
    try:
        service = get_service_alert_service()

        alert_status = None
        if status:
            try:
                alert_status = AlertStatus(status)
            except ValueError:
                return APIResponse.error(
                    message=f"Invalid status: {status}",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        alert_severity = None
        if severity:
            try:
                alert_severity = AlertSeverity(severity)
            except ValueError:
                return APIResponse.error(
                    message=f"Invalid severity: {severity}",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        alerts = service.list_alerts(
            service_name=service_name,
            status=alert_status,
            severity=alert_severity,
            limit=limit,
        )

        alerts_dicts = [alert.model_dump(mode="json") for alert in alerts]

        return APIResponse.success(
            data={"alerts": alerts_dicts, "total": len(alerts_dicts)},
            message="Alerts retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to list alerts: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to list alerts: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/{alert_id}/acknowledge", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="alert",
    get_resource_id=lambda alert_id: alert_id,
)
async def acknowledge_alert(
    alert_id: str = Path(description="告警 ID"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    確認告警

    Args:
        alert_id: 告警 ID
        current_user: 當前認證用戶

    Returns:
        更新後的告警
    """
    try:
        service = get_service_alert_service()
        alert = service.acknowledge_alert(alert_id, current_user.user_id)

        if alert is None:
            return APIResponse.error(
                message=f"Alert '{alert_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"Alert acknowledged: alert_id={alert_id}, user_id={current_user.user_id}")

        return APIResponse.success(
            data=alert.model_dump(mode="json"),
            message="Alert acknowledged successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to acknowledge alert: alert_id={alert_id}, error={str(e)}", exc_info=True
        )
        return APIResponse.error(
            message=f"Failed to acknowledge alert: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/{alert_id}/resolve", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="alert",
    get_resource_id=lambda alert_id: alert_id,
)
async def resolve_alert(
    alert_id: str = Path(description="告警 ID"),
    resolution_notes: Optional[str] = Query(default=None, description="解決說明"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    解決告警

    Args:
        alert_id: 告警 ID
        resolution_notes: 解決說明（可選）
        current_user: 當前認證用戶

    Returns:
        更新後的告警
    """
    try:
        service = get_service_alert_service()
        alert = service.resolve_alert(alert_id, resolution_notes)

        if alert is None:
            return APIResponse.error(
                message=f"Alert '{alert_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"Alert resolved: alert_id={alert_id}")

        return APIResponse.success(
            data=alert.model_dump(mode="json"),
            message="Alert resolved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to resolve alert: alert_id={alert_id}, error={str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to resolve alert: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
