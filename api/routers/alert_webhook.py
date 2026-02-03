# 代碼功能說明: Alertmanager Webhook 接收端點
# 創建日期: 2026-01-18 18:18 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 19:36 UTC+8

"""Alertmanager Webhook 接收端點 - 接收 Prometheus Alertmanager 發送的告警通知"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services.api.models.service_alert import AlertSeverity, AlertStatus, ServiceAlertModel
from services.api.services.service_alert_service import get_service_alert_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/alerts", tags=["Alert Webhook"])


class AlertLabel(BaseModel):
    """告警標籤模型"""

    alertname: Optional[str] = None
    severity: Optional[str] = None
    service: Optional[str] = None
    instance: Optional[str] = None
    job: Optional[str] = None
    cluster: Optional[str] = None
    environment: Optional[str] = None


class AlertAnnotation(BaseModel):
    """告警註釋模型"""

    summary: Optional[str] = None
    description: Optional[str] = None


class Alert(BaseModel):
    """單個告警模型"""

    status: str  # firing 或 resolved
    labels: Dict[str, Any]
    annotations: Dict[str, Any]
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None


class AlertmanagerWebhookPayload(BaseModel):
    """Alertmanager Webhook 請求體模型"""

    version: str
    groupKey: str
    status: str  # firing 或 resolved
    receiver: str
    groupLabels: Dict[str, Any]
    commonLabels: Dict[str, Any]
    commonAnnotations: Dict[str, Any]
    externalURL: Optional[str] = None
    alerts: List[Alert]


def _map_prometheus_severity_to_alert_severity(severity: Optional[str]) -> AlertSeverity:
    """將 Prometheus 嚴重程度映射到系統告警嚴重程度"""
    if severity is None:
        return AlertSeverity.MEDIUM

    severity_lower = severity.lower()
    if severity_lower == "critical":
        return AlertSeverity.CRITICAL
    elif severity_lower == "warning":
        return AlertSeverity.HIGH
    elif severity_lower == "high":
        return AlertSeverity.HIGH
    elif severity_lower == "medium":
        return AlertSeverity.MEDIUM
    elif severity_lower == "low":
        return AlertSeverity.LOW
    else:
        return AlertSeverity.MEDIUM


def _extract_service_name(labels: Dict[str, Any]) -> str:
    """從標籤中提取服務名稱"""
    # 優先使用 service 標籤，否則使用 job 標籤，最後使用 alertname
    service_name = labels.get("service") or labels.get("job") or labels.get("alertname", "unknown")
    return service_name


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def receive_alert_webhook(request: Request) -> JSONResponse:
    """
    接收 Alertmanager 發送的告警 Webhook

    此端點接收 Prometheus Alertmanager 發送的告警通知，
    並將告警信息存儲到數據庫中。

    Args:
        request: FastAPI 請求對象

    Returns:
        成功響應
    """
    try:
        # 解析請求體
        body = await request.json()
        payload = AlertmanagerWebhookPayload(**body)

        logger.info(
            f"Received alert webhook: version={payload.version}, "
            f"status={payload.status}, receiver={payload.receiver}, "
            f"alerts_count={len(payload.alerts)}"
        )

        # 获取告警服务（延迟初始化，避免在数据库不可用时导致启动失败）
        try:
            alert_service = get_service_alert_service()
        except Exception as e:
            logger.error(f"Failed to get service alert service: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "error",
                    "message": f"Alert service unavailable: {str(e)}",
                },
            )

        processed_alerts = []

        # 處理每個告警
        for alert in payload.alerts:
            try:
                # 提取服務名稱
                service_name = _extract_service_name(alert.labels)

                # 映射嚴重程度
                severity = _map_prometheus_severity_to_alert_severity(alert.labels.get("severity"))

                # 確定告警狀態
                if alert.status == "firing":
                    alert_status = AlertStatus.ACTIVE
                    if alert.startsAt:
                        triggered_at = datetime.fromisoformat(alert.startsAt.replace("Z", "+00:00"))
                    else:
                        triggered_at = datetime.now(timezone.utc)
                    resolved_at = None
                else:  # resolved
                    alert_status = AlertStatus.RESOLVED
                    if alert.startsAt:
                        triggered_at = datetime.fromisoformat(alert.startsAt.replace("Z", "+00:00"))
                    else:
                        triggered_at = datetime.now(timezone.utc)
                    if alert.endsAt:
                        resolved_at = datetime.fromisoformat(alert.endsAt.replace("Z", "+00:00"))
                    else:
                        resolved_at = datetime.now(timezone.utc)

                # 生成告警 ID（使用 groupKey 和 alertname 確保唯一性）
                alert_id = (
                    f"prometheus_{payload.groupKey}_{alert.labels.get('alertname', 'unknown')}"
                )

                # 生成標題和消息
                title = alert.annotations.get("summary") or alert.labels.get(
                    "alertname", "Unknown Alert"
                )
                message = alert.annotations.get("description") or title

                # 創建告警模型
                alert_model = ServiceAlertModel(
                    id=None,  # 將由數據庫生成
                    alert_id=alert_id,
                    rule_id=f"prometheus_rule_{alert.labels.get('alertname', 'unknown')}",
                    service_name=service_name,
                    severity=severity,
                    status=alert_status,
                    title=title,
                    message=message,
                    triggered_at=triggered_at,
                    resolved_at=resolved_at,
                    acknowledged_at=None,
                    acknowledged_by=None,
                    resolution_notes=None,
                    current_value=None,
                    threshold=None,
                    metadata={
                        "source": "prometheus",
                        "version": payload.version,
                        "receiver": payload.receiver,
                        "groupKey": payload.groupKey,
                        "labels": alert.labels,
                        "annotations": alert.annotations,
                        "generatorURL": alert.generatorURL,
                        "externalURL": payload.externalURL,
                    },
                )

                # 保存告警到數據庫
                # 使用 ServiceAlertService 的內部集合來保存告警
                alert_doc = {
                    "_key": alert_id,
                    "alert_id": alert_model.alert_id,
                    "rule_id": alert_model.rule_id,
                    "service_name": alert_model.service_name,
                    "severity": alert_model.severity.value,
                    "status": alert_model.status.value,
                    "title": alert_model.title,
                    "message": alert_model.message,
                    "triggered_at": alert_model.triggered_at.isoformat(),
                    "resolved_at": (
                        alert_model.resolved_at.isoformat() if alert_model.resolved_at else None
                    ),
                    "acknowledged_at": None,
                    "acknowledged_by": None,
                    "resolution_notes": None,
                    "current_value": None,
                    "threshold": None,
                    "metadata": alert_model.metadata,
                }

                # 使用 ServiceAlertService 的內部集合來保存
                # 通過訪問服務的 _alerts_collection 來保存告警
                try:
                    alerts_collection = alert_service._alerts_collection
                    alerts_collection.insert(alert_doc)
                except Exception as e:
                    logger.error(
                        f"Failed to save alert to database: alert_id={alert_id}, error={str(e)}",
                        exc_info=True,
                    )
                    # 繼續處理下一個告警，不中斷整個流程
                    continue

                processed_alerts.append(alert_id)

                logger.info(
                    f"Alert processed: alert_id={alert_id}, service_name={service_name}, "
                    f"status={alert_status.value}, severity={severity.value}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to process alert: labels={alert.labels}, error={str(e)}",
                    exc_info=True,
                )
                # 繼續處理下一個告警，不中斷整個流程

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": f"Processed {len(processed_alerts)} alerts",
                "processed_alerts": processed_alerts,
            },
        )

    except Exception as e:
        logger.error(f"Failed to process alert webhook: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": f"Failed to process alert webhook: {str(e)}",
            },
        )
