# 代碼功能說明: Security Manager Agent 數據模型
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""Security Manager Agent 數據模型定義"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """風險等級"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityManagerRequest(BaseModel):
    """安全管理请求模型"""

    action: str = Field(..., description="操作类型（assess, check_permission, audit, analyze）")
    agent_id: Optional[str] = Field(None, description="Agent ID（用于权限检查）")
    resource_type: Optional[str] = Field(None, description="资源类型")
    resource_name: Optional[str] = Field(None, description="资源名称")
    operation: Optional[str] = Field(None, description="操作类型")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class RiskAssessmentResult(BaseModel):
    """风险评估结果模型"""

    risk_level: RiskLevel = Field(..., description="风险等级")
    score: float = Field(..., description="风险分数（0-1）")
    factors: List[str] = Field(default_factory=list, description="风险因素列表")
    recommendations: List[str] = Field(default_factory=list, description="安全建议列表")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


class PermissionCheckResult(BaseModel):
    """權限檢查結果（用於內部權限檢查）"""

    allowed: bool = Field(..., description="是否允許")
    reason: Optional[str] = Field(None, description="如果不允許，說明原因")


class SecurityCheckRequest(BaseModel):
    """安全檢查請求

    用於 Orchestrator 調用 Security Agent 進行權限檢查。
    """

    admin_id: str = Field(..., description="管理員用戶 ID")
    intent: Dict[str, Any] = Field(..., description="ConfigIntent（由 Orchestrator 傳遞）")
    context: Optional[Dict[str, Any]] = Field(
        None, description="額外上下文（IP、User Agent、trace_id 等）"
    )


class SecurityCheckResult(BaseModel):
    """安全檢查結果

    用於 Security Agent 返回權限檢查和風險評估結果。
    """

    allowed: bool = Field(..., description="是否允許執行")
    reason: Optional[str] = Field(None, description="如果不允許，說明原因")
    requires_double_check: bool = Field(default=False, description="是否需要二次確認")
    risk_level: str = Field(default="low", description="風險級別：low/medium/high")
    audit_context: Dict[str, Any] = Field(default_factory=dict, description="審計上下文")


class SecurityManagerResponse(BaseModel):
    """安全管理响应模型"""

    success: bool = Field(..., description="是否成功")
    action: str = Field(..., description="执行的操作类型")
    allowed: Optional[bool] = Field(None, description="是否允许访问")
    risk_assessment: Optional[RiskAssessmentResult] = Field(None, description="风险评估结果")
    audit_result: Optional[Dict[str, Any]] = Field(None, description="审计结果")
    analysis: Optional[Dict[str, Any]] = Field(None, description="分析结果")
    message: Optional[str] = Field(None, description="响应消息")
    error: Optional[str] = Field(None, description="错误信息")


class ConfigRiskAssessmentResult(BaseModel):
    """配置操作風險評估結果（用於配置操作的風險評估）"""

    risk_level: str = Field(..., description="風險級別：low/medium/high")
    requires_double_check: bool = Field(default=False, description="是否需要二次確認")
