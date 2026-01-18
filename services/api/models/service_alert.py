# 代碼功能說明: ServiceAlert 數據模型
# 創建日期: 2026-01-17 19:41 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 19:41 UTC+8

"""ServiceAlert 數據模型定義"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class AlertSeverity(str, Enum):
    """告警嚴重程度枚舉"""

    CRITICAL = "critical"  # 嚴重：服務完全不可用
    HIGH = "high"  # 高：服務降級或部分功能不可用
    MEDIUM = "medium"  # 中：性能問題或警告
    LOW = "low"  # 低：輕微問題或信息性告警


class AlertStatus(str, Enum):
    """告警狀態枚舉"""

    ACTIVE = "active"  # 活躍：告警已觸發，未解決
    RESOLVED = "resolved"  # 已解決：問題已修復
    ACKNOWLEDGED = "acknowledged"  # 已確認：管理員已查看
    SUPPRESSED = "suppressed"  # 已抑制：手動關閉告警


class AlertRule(BaseModel):
    """告警規則模型"""

    rule_id: str = Field(description="規則 ID")
    rule_name: str = Field(description="規則名稱")
    service_name: str = Field(description="服務名稱（* 表示所有服務）")
    rule_type: str = Field(
        description="規則類型：service_offline/response_time/error_rate/cpu_usage/memory_usage"
    )
    threshold: float = Field(description="閾值")
    comparison: str = Field(default=">", description="比較操作符：>/</>=/<=/==/!=")
    severity: AlertSeverity = Field(description="嚴重程度")
    enabled: bool = Field(default=True, description="是否啟用")
    duration: Optional[int] = Field(default=None, description="持續時間（秒），超過此時間才觸發告警")
    cooldown: Optional[int] = Field(default=300, description="冷卻時間（秒），告警後多久才能再次觸發")
    notification_channels: List[str] = Field(
        default_factory=list, description="通知渠道列表：email/webhook/system"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")

    @field_validator("comparison")
    @classmethod
    def validate_comparison(cls, v: str) -> str:
        """驗證比較操作符"""
        valid_operators = [">", "<", ">=", "<=", "==", "!="]
        if v not in valid_operators:
            raise ValueError(f"comparison must be one of {valid_operators}")
        return v

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        """驗證規則類型"""
        valid_types = [
            "service_offline",
            "response_time",
            "error_rate",
            "cpu_usage",
            "memory_usage",
        ]
        if v not in valid_types:
            raise ValueError(f"rule_type must be one of {valid_types}")
        return v


class ServiceAlertModel(BaseModel):
    """ServiceAlert 數據模型"""

    id: Optional[str] = Field(default=None, description="Alert ID（_key）")
    alert_id: str = Field(description="告警 ID（唯一標識）")
    rule_id: str = Field(description="觸發的規則 ID")
    service_name: str = Field(description="服務名稱")
    severity: AlertSeverity = Field(description="嚴重程度")
    status: AlertStatus = Field(default=AlertStatus.ACTIVE, description="告警狀態")
    title: str = Field(description="告警標題")
    message: str = Field(description="告警消息")
    triggered_at: datetime = Field(description="觸發時間")
    resolved_at: Optional[datetime] = Field(default=None, description="解決時間")
    acknowledged_at: Optional[datetime] = Field(default=None, description="確認時間")
    acknowledged_by: Optional[str] = Field(default=None, description="確認人（用戶 ID）")
    resolution_notes: Optional[str] = Field(default=None, description="解決說明")
    current_value: Optional[float] = Field(default=None, description="當前值")
    threshold: Optional[float] = Field(default=None, description="閾值")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """驗證嚴重程度"""
        valid_severities = ["critical", "high", "medium", "low"]
        if v not in valid_severities:
            raise ValueError(f"severity must be one of {valid_severities}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """驗證告警狀態"""
        valid_statuses = ["active", "resolved", "acknowledged", "suppressed"]
        if v not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}")
        return v

    class Config:
        """Pydantic 配置"""

        json_schema_extra = {
            "example": {
                "id": "alert_123",
                "alert_id": "alert_20260117174100_fastapi",
                "rule_id": "rule_service_offline",
                "service_name": "fastapi",
                "severity": "critical",
                "status": "active",
                "title": "FastAPI 服務離線",
                "message": "FastAPI 服務在 2026-01-17 17:41:00 檢測到離線",
                "triggered_at": "2026-01-17T17:41:00Z",
                "current_value": None,
                "threshold": None,
                "metadata": {},
            }
        }


class AlertNotification(BaseModel):
    """告警通知模型"""

    notification_id: str = Field(description="通知 ID")
    alert_id: str = Field(description="告警 ID")
    channel: str = Field(description="通知渠道：email/webhook/system")
    recipient: str = Field(description="接收者（郵箱地址/URL/用戶ID）")
    sent_at: datetime = Field(description="發送時間")
    status: str = Field(default="pending", description="發送狀態：pending/sent/failed")
    error_message: Optional[str] = Field(default=None, description="錯誤信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")
