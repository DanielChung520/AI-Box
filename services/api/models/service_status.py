# 代碼功能說明: ServiceStatus 數據模型
# 創建日期: 2026-01-17 17:13 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 17:13 UTC+8

"""ServiceStatus 數據模型定義"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class ServiceStatus(str, Enum):
    """服務運行狀態枚舉"""

    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"


class HealthStatus(str, Enum):
    """服務健康狀態枚舉"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class ServiceStatusModel(BaseModel):
    """ServiceStatus 數據模型"""

    id: Optional[str] = Field(default=None, description="Service ID（_key）")
    service_name: str = Field(description="服務名稱（唯一）")
    service_type: str = Field(description="服務類型（api/database/cache/worker等）")
    status: str = Field(description="運行狀態（running/stopped/error/unknown）")
    health_status: str = Field(description="健康狀態（healthy/unhealthy/degraded）")
    port: Optional[int] = Field(default=None, description="端口號")
    pid: Optional[int] = Field(default=None, description="進程ID")
    host: str = Field(default="localhost", description="主機地址")
    last_check_at: Optional[datetime] = Field(default=None, description="最後檢查時間")
    last_success_at: Optional[datetime] = Field(default=None, description="最後成功時間")
    check_interval: int = Field(default=30, description="檢查間隔（秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據（版本、運行時間、CPU、內存等）")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """驗證運行狀態"""
        valid_statuses = ["running", "stopped", "error", "unknown"]
        if v not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}")
        return v

    @field_validator("health_status")
    @classmethod
    def validate_health_status(cls, v: str) -> str:
        """驗證健康狀態"""
        valid_health_statuses = ["healthy", "unhealthy", "degraded"]
        if v not in valid_health_statuses:
            raise ValueError(f"health_status must be one of {valid_health_statuses}")
        return v

    class Config:
        """Pydantic 配置"""

        json_schema_extra = {
            "example": {
                "id": "fastapi",
                "service_name": "fastapi",
                "service_type": "api",
                "status": "running",
                "health_status": "healthy",
                "port": 8000,
                "pid": 8988,
                "host": "localhost",
                "last_check_at": "2026-01-17T17:13:00Z",
                "last_success_at": "2026-01-17T17:13:00Z",
                "check_interval": 30,
                "metadata": {
                    "version": "1.0.0",
                    "uptime": 3600,
                    "cpu_usage": 5.2,
                    "memory_usage": 128,
                    "request_count": 1000,
                    "error_count": 0,
                },
            }
        }


class ServiceStatusHistoryModel(BaseModel):
    """ServiceStatus 歷史記錄數據模型"""

    id: Optional[str] = Field(default=None, description="History ID（_key）")
    service_name: str = Field(description="服務名稱")
    status: str = Field(description="運行狀態")
    health_status: str = Field(description="健康狀態")
    timestamp: datetime = Field(description="時間戳")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="指標數據")


class ServiceHealthCheck(BaseModel):
    """服務健康檢查結果模型"""

    service_name: str = Field(description="服務名稱")
    status: str = Field(description="運行狀態")
    health_status: str = Field(description="健康狀態")
    response_time_ms: Optional[float] = Field(default=None, description="響應時間（毫秒）")
    error_message: Optional[str] = Field(default=None, description="錯誤信息（如果檢查失敗）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="檢查結果元數據")


class ServiceMetrics(BaseModel):
    """服務指標模型"""

    service_name: str = Field(description="服務名稱")
    cpu_usage: Optional[float] = Field(default=None, description="CPU 使用率（百分比）")
    memory_usage: Optional[float] = Field(default=None, description="內存使用量（MB）")
    request_count: Optional[int] = Field(default=None, description="請求數")
    error_count: Optional[int] = Field(default=None, description="錯誤數")
    response_time_avg: Optional[float] = Field(default=None, description="平均響應時間（毫秒）")
    uptime: Optional[int] = Field(default=None, description="運行時間（秒）")
    timestamp: datetime = Field(description="時間戳")
