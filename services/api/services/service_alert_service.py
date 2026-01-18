# 代碼功能說明: 服務告警服務
# 創建日期: 2026-01-17 19:41 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 19:41 UTC+8

"""Service Alert Service

提供服務告警規則管理和告警觸發邏輯。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.service_alert import (
    AlertRule,
    AlertSeverity,
    AlertStatus,
    ServiceAlertModel,
)
from services.api.models.service_status import ServiceHealthCheck, ServiceStatusModel

logger = structlog.get_logger(__name__)

ALERT_RULES_COLLECTION = "service_alert_rules"
SERVICE_ALERTS_COLLECTION = "service_alerts"


class ServiceAlertService:
    """服務告警服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化服務告警服務

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collections 存在
        rules_collection = self._client.get_or_create_collection(ALERT_RULES_COLLECTION)
        alerts_collection = self._client.get_or_create_collection(SERVICE_ALERTS_COLLECTION)

        self._rules_collection = ArangoCollection(rules_collection)
        self._alerts_collection = ArangoCollection(alerts_collection)

        # 創建索引
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        try:
            # Alert Rules 索引
            if not self._rules_collection.has_index("idx_rules_service_enabled"):
                self._rules_collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["service_name", "enabled"],
                    },
                    name="idx_rules_service_enabled",
                )

            # Service Alerts 索引
            if not self._alerts_collection.has_index("idx_alerts_service_status"):
                self._alerts_collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["service_name", "status"],
                    },
                    name="idx_alerts_service_status",
                )
            if not self._alerts_collection.has_index("idx_alerts_triggered_at"):
                self._alerts_collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["triggered_at"],
                    },
                    name="idx_alerts_triggered_at",
                )
            if not self._alerts_collection.has_index("idx_alerts_rule_id"):
                self._alerts_collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["rule_id"],
                    },
                    name="idx_alerts_rule_id",
                )
        except Exception as e:
            self._logger.warning(f"Failed to create indexes: {str(e)}")

    def create_alert_rule(self, rule: AlertRule) -> AlertRule:
        """
        創建告警規則

        Args:
            rule: 告警規則

        Returns:
            創建的告警規則
        """
        doc = {
            "_key": rule.rule_id,
            "rule_id": rule.rule_id,
            "rule_name": rule.rule_name,
            "service_name": rule.service_name,
            "rule_type": rule.rule_type,
            "threshold": rule.threshold,
            "comparison": rule.comparison,
            "severity": rule.severity.value,
            "enabled": rule.enabled,
            "duration": rule.duration,
            "cooldown": rule.cooldown or 300,
            "notification_channels": rule.notification_channels,
            "metadata": rule.metadata,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        self._rules_collection.insert(doc, overwrite=True)

        self._logger.info(f"Alert rule created: rule_id={rule.rule_id}")

        return rule

    def get_alert_rule(self, rule_id: str) -> Optional[AlertRule]:
        """
        獲取告警規則

        Args:
            rule_id: 規則 ID

        Returns:
            告警規則，如果不存在則返回 None
        """
        doc = self._rules_collection.get(rule_id)

        if doc is None:
            return None

        return AlertRule(
            rule_id=doc["rule_id"],
            rule_name=doc["rule_name"],
            service_name=doc["service_name"],
            rule_type=doc["rule_type"],
            threshold=doc["threshold"],
            comparison=doc.get("comparison", ">"),
            severity=AlertSeverity(doc["severity"]),
            enabled=doc.get("enabled", True),
            duration=doc.get("duration"),
            cooldown=doc.get("cooldown", 300),
            notification_channels=doc.get("notification_channels", []),
            metadata=doc.get("metadata", {}),
        )

    def list_alert_rules(
        self,
        service_name: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> List[AlertRule]:
        """
        列出告警規則

        Args:
            service_name: 服務名稱過濾（可選）
            enabled: 是否啟用過濾（可選）

        Returns:
            告警規則列表
        """
        filters: Dict[str, Any] = {}
        if service_name is not None and service_name != "*":
            filters["service_name"] = service_name
        if enabled is not None:
            filters["enabled"] = enabled

        docs = self._rules_collection.find(filters)

        rules = []
        for doc in docs:
            try:
                rule = AlertRule(
                    rule_id=doc["rule_id"],
                    rule_name=doc["rule_name"],
                    service_name=doc["service_name"],
                    rule_type=doc["rule_type"],
                    threshold=doc["threshold"],
                    comparison=doc.get("comparison", ">"),
                    severity=AlertSeverity(doc["severity"]),
                    enabled=doc.get("enabled", True),
                    duration=doc.get("duration"),
                    cooldown=doc.get("cooldown", 300),
                    notification_channels=doc.get("notification_channels", []),
                    metadata=doc.get("metadata", {}),
                )
                rules.append(rule)
            except Exception as e:
                self._logger.warning(
                    f"Failed to parse alert rule: rule_id={doc.get('rule_id')}, error={str(e)}"
                )

        return rules

    def update_alert_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[AlertRule]:
        """
        更新告警規則

        Args:
            rule_id: 規則 ID
            updates: 更新字段

        Returns:
            更新後的告警規則，如果不存在則返回 None
        """
        doc = self._rules_collection.get(rule_id)

        if doc is None:
            return None

        # 更新字段
        for key, value in updates.items():
            if key in ["rule_id", "created_at"]:
                continue  # 不允許更新這些字段
            doc[key] = value

        doc["updated_at"] = datetime.utcnow().isoformat()

        self._rules_collection.update(rule_id, doc)

        self._logger.info(f"Alert rule updated: rule_id={rule_id}")

        return self.get_alert_rule(rule_id)

    def delete_alert_rule(self, rule_id: str) -> bool:
        """
        刪除告警規則

        Args:
            rule_id: 規則 ID

        Returns:
            是否成功刪除
        """
        try:
            self._rules_collection.delete(rule_id)
            self._logger.info(f"Alert rule deleted: rule_id={rule_id}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to delete alert rule: rule_id={rule_id}, error={str(e)}")
            return False

    def check_and_trigger_alerts(
        self, service_status: ServiceStatusModel, health_check: ServiceHealthCheck
    ) -> List[ServiceAlertModel]:
        """
        檢查並觸發告警

        Args:
            service_status: 服務狀態
            health_check: 健康檢查結果

        Returns:
            觸發的告警列表
        """
        triggered_alerts = []

        # 獲取適用於該服務的啟用規則
        rules = self.list_alert_rules(service_name=service_status.service_name, enabled=True)

        # 也獲取通用規則（service_name = "*"）
        global_rules = self.list_alert_rules(service_name="*", enabled=True)
        rules.extend(global_rules)

        for rule in rules:
            # 檢查規則是否適用
            if rule.service_name != "*" and rule.service_name != service_status.service_name:
                continue

            # 檢查是否在冷卻期
            if self._is_in_cooldown(rule, service_status.service_name):
                continue

            # 評估規則
            should_trigger = self._evaluate_rule(rule, service_status, health_check)

            if should_trigger:
                alert = self._create_alert(rule, service_status, health_check)
                if alert:
                    triggered_alerts.append(alert)

        return triggered_alerts

    def _evaluate_rule(
        self,
        rule: AlertRule,
        service_status: ServiceStatusModel,
        health_check: ServiceHealthCheck,
    ) -> bool:
        """
        評估規則是否應該觸發

        Args:
            rule: 告警規則
            service_status: 服務狀態
            health_check: 健康檢查結果

        Returns:
            是否應該觸發告警
        """
        if rule.rule_type == "service_offline":
            # 服務離線規則
            if service_status.status != "running":
                return True
            return False

        elif rule.rule_type == "response_time":
            # 響應時間規則
            response_time = health_check.response_time_ms
            if response_time is None:
                return False
            return self._compare_value(response_time, rule.comparison, rule.threshold)

        elif rule.rule_type == "error_rate":
            # 錯誤率規則（需要從 metadata 中獲取）
            error_count = service_status.metadata.get("error_count", 0)
            request_count = service_status.metadata.get("request_count", 0)
            if request_count == 0:
                return False
            error_rate = (error_count / request_count) * 100
            return self._compare_value(error_rate, rule.comparison, rule.threshold)

        elif rule.rule_type == "cpu_usage":
            # CPU 使用率規則
            cpu_usage = service_status.metadata.get("cpu_usage")
            if cpu_usage is None:
                return False
            return self._compare_value(cpu_usage, rule.comparison, rule.threshold)

        elif rule.rule_type == "memory_usage":
            # 內存使用量規則
            memory_usage = service_status.metadata.get("memory_usage")
            if memory_usage is None:
                return False
            return self._compare_value(memory_usage, rule.comparison, rule.threshold)

        return False

    def _compare_value(self, current: float, comparison: str, threshold: float) -> bool:
        """比較值與閾值"""
        if comparison == ">":
            return current > threshold
        elif comparison == "<":
            return current < threshold
        elif comparison == ">=":
            return current >= threshold
        elif comparison == "<=":
            return current <= threshold
        elif comparison == "==":
            return abs(current - threshold) < 0.001  # 浮點數比較
        elif comparison == "!=":
            return abs(current - threshold) >= 0.001
        return False

    def _is_in_cooldown(self, rule: AlertRule, service_name: str) -> bool:
        """
        檢查規則是否在冷卻期

        Args:
            rule: 告警規則
            service_name: 服務名稱

        Returns:
            是否在冷卻期
        """
        # 查找最近觸發的告警
        filters = {
            "rule_id": rule.rule_id,
            "service_name": service_name,
            "status": "active",
        }

        alerts = self._alerts_collection.find(filters, limit=1)

        for alert_doc in alerts:
            triggered_at = datetime.fromisoformat(alert_doc["triggered_at"])
            cooldown_end = triggered_at + timedelta(seconds=rule.cooldown or 300)

            if datetime.utcnow() < cooldown_end:
                return True

        return False

    def _create_alert(
        self,
        rule: AlertRule,
        service_status: ServiceStatusModel,
        health_check: ServiceHealthCheck,
    ) -> Optional[ServiceAlertModel]:
        """
        創建告警

        Args:
            rule: 告警規則
            service_status: 服務狀態
            health_check: 健康檢查結果

        Returns:
            創建的告警
        """
        # 生成告警 ID
        alert_id = (
            f"alert_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{service_status.service_name}"
        )

        # 生成標題和消息
        title, message, current_value, threshold = self._generate_alert_content(
            rule, service_status, health_check
        )

        alert = ServiceAlertModel(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            service_name=service_status.service_name,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            title=title,
            message=message,
            triggered_at=datetime.utcnow(),
            current_value=current_value,
            threshold=threshold,
            metadata={
                "service_type": service_status.service_type,
                "health_status": health_check.health_status,
            },
        )

        # 保存到數據庫
        doc = {
            "_key": alert_id,
            "alert_id": alert.alert_id,
            "rule_id": alert.rule_id,
            "service_name": alert.service_name,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "title": alert.title,
            "message": alert.message,
            "triggered_at": alert.triggered_at.isoformat(),
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            "acknowledged_by": alert.acknowledged_by,
            "resolution_notes": alert.resolution_notes,
            "current_value": alert.current_value,
            "threshold": alert.threshold,
            "metadata": alert.metadata,
        }

        self._alerts_collection.insert(doc, overwrite=True)

        self._logger.warning(
            f"Service alert triggered: alert_id={alert_id}, service_name={service_status.service_name}, "
            f"severity={rule.severity.value}, rule_type={rule.rule_type}"
        )

        # 發送通知（異步處理）
        self._send_notifications(alert, rule.notification_channels)

        return alert

    def _generate_alert_content(
        self,
        rule: AlertRule,
        service_status: ServiceStatusModel,
        health_check: ServiceHealthCheck,
    ) -> tuple[str, str, Optional[float], Optional[float]]:
        """生成告警標題和消息"""
        service_name = service_status.service_name

        if rule.rule_type == "service_offline":
            title = f"{service_name} 服務離線"
            message = f"{service_name} 服務在 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} 檢測到離線"
            return title, message, None, None

        elif rule.rule_type == "response_time":
            response_time = health_check.response_time_ms or 0
            title = f"{service_name} 響應時間過長"
            message = f"{service_name} 響應時間 {response_time:.2f}ms 超過閾值 {rule.threshold}ms"
            return title, message, response_time, rule.threshold

        elif rule.rule_type == "error_rate":
            error_count = service_status.metadata.get("error_count", 0)
            request_count = service_status.metadata.get("request_count", 0)
            error_rate = (error_count / request_count * 100) if request_count > 0 else 0
            title = f"{service_name} 錯誤率過高"
            message = (
                f"{service_name} 錯誤率 {error_rate:.2f}% 超過閾值 {rule.threshold}% "
                f"(錯誤數: {error_count}, 請求數: {request_count})"
            )
            return title, message, error_rate, rule.threshold

        elif rule.rule_type == "cpu_usage":
            cpu_usage = service_status.metadata.get("cpu_usage", 0)
            title = f"{service_name} CPU 使用率過高"
            message = f"{service_name} CPU 使用率 {cpu_usage:.2f}% 超過閾值 {rule.threshold}%"
            return title, message, cpu_usage, rule.threshold

        elif rule.rule_type == "memory_usage":
            memory_usage = service_status.metadata.get("memory_usage", 0)
            title = f"{service_name} 內存使用量過高"
            message = f"{service_name} 內存使用量 {memory_usage:.2f}MB 超過閾值 {rule.threshold}MB"
            return title, message, memory_usage, rule.threshold

        title = f"{service_name} 告警觸發"
        message = f"告警規則 {rule.rule_name} 已觸發"
        return title, message, None, rule.threshold

    def _send_notifications(self, alert: ServiceAlertModel, channels: List[str]) -> None:
        """發送通知（異步處理）"""
        # TODO: 實現實際的通知發送邏輯（郵件、Webhook、系統通知等）
        self._logger.info(
            f"Notification sent for alert: alert_id={alert.alert_id}, channels={channels}"
        )

    def list_alerts(
        self,
        service_name: Optional[str] = None,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        limit: Optional[int] = None,
    ) -> List[ServiceAlertModel]:
        """
        列出告警

        Args:
            service_name: 服務名稱過濾（可選）
            status: 狀態過濾（可選）
            severity: 嚴重程度過濾（可選）
            limit: 限制返回數量（可選）

        Returns:
            告警列表
        """
        filters: Dict[str, Any] = {}
        if service_name:
            filters["service_name"] = service_name
        if status:
            filters["status"] = status.value
        if severity:
            filters["severity"] = severity.value

        docs = self._alerts_collection.find(filters, limit=limit, sort=[("triggered_at", -1)])

        alerts = []
        for doc in docs:
            try:
                alert = ServiceAlertModel(
                    id=doc["_key"],
                    alert_id=doc["alert_id"],
                    rule_id=doc["rule_id"],
                    service_name=doc["service_name"],
                    severity=AlertSeverity(doc["severity"]),
                    status=AlertStatus(doc["status"]),
                    title=doc["title"],
                    message=doc["message"],
                    triggered_at=datetime.fromisoformat(doc["triggered_at"]),
                    resolved_at=(
                        datetime.fromisoformat(doc["resolved_at"])
                        if doc.get("resolved_at")
                        else None
                    ),
                    acknowledged_at=(
                        datetime.fromisoformat(doc["acknowledged_at"])
                        if doc.get("acknowledged_at")
                        else None
                    ),
                    acknowledged_by=doc.get("acknowledged_by"),
                    resolution_notes=doc.get("resolution_notes"),
                    current_value=doc.get("current_value"),
                    threshold=doc.get("threshold"),
                    metadata=doc.get("metadata", {}),
                )
                alerts.append(alert)
            except Exception as e:
                self._logger.warning(
                    f"Failed to parse alert: alert_id={doc.get('alert_id')}, error={str(e)}"
                )

        return alerts

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> Optional[ServiceAlertModel]:
        """
        確認告警

        Args:
            alert_id: 告警 ID
            acknowledged_by: 確認人（用戶 ID）

        Returns:
            更新後的告警，如果不存在則返回 None
        """
        doc = self._alerts_collection.get(alert_id)

        if doc is None:
            return None

        doc["status"] = AlertStatus.ACKNOWLEDGED.value
        doc["acknowledged_at"] = datetime.utcnow().isoformat()
        doc["acknowledged_by"] = acknowledged_by

        self._alerts_collection.update(alert_id, doc)

        return self._document_to_alert_model(doc)

    def resolve_alert(
        self, alert_id: str, resolution_notes: Optional[str] = None
    ) -> Optional[ServiceAlertModel]:
        """
        解決告警

        Args:
            alert_id: 告警 ID
            resolution_notes: 解決說明（可選）

        Returns:
            更新後的告警，如果不存在則返回 None
        """
        doc = self._alerts_collection.get(alert_id)

        if doc is None:
            return None

        doc["status"] = AlertStatus.RESOLVED.value
        doc["resolved_at"] = datetime.utcnow().isoformat()
        if resolution_notes:
            doc["resolution_notes"] = resolution_notes

        self._alerts_collection.update(alert_id, doc)

        return self._document_to_alert_model(doc)

    def _document_to_alert_model(self, doc: Dict[str, Any]) -> ServiceAlertModel:
        """將文檔轉換為告警模型"""
        return ServiceAlertModel(
            id=doc["_key"],
            alert_id=doc["alert_id"],
            rule_id=doc["rule_id"],
            service_name=doc["service_name"],
            severity=AlertSeverity(doc["severity"]),
            status=AlertStatus(doc["status"]),
            title=doc["title"],
            message=doc["message"],
            triggered_at=datetime.fromisoformat(doc["triggered_at"]),
            resolved_at=(
                datetime.fromisoformat(doc["resolved_at"]) if doc.get("resolved_at") else None
            ),
            acknowledged_at=(
                datetime.fromisoformat(doc["acknowledged_at"])
                if doc.get("acknowledged_at")
                else None
            ),
            acknowledged_by=doc.get("acknowledged_by"),
            resolution_notes=doc.get("resolution_notes"),
            current_value=doc.get("current_value"),
            threshold=doc.get("threshold"),
            metadata=doc.get("metadata", {}),
        )


# 單例模式
_service: Optional[ServiceAlertService] = None


def get_service_alert_service() -> ServiceAlertService:
    """獲取 ServiceAlertService 實例（單例模式）"""
    global _service
    if _service is None:
        _service = ServiceAlertService()
    return _service
