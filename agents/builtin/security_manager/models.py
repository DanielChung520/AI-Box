# 代碼功能說明: Security Manager Agent 數據模型
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Security Manager Agent 數據模型定義"""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """風險等級"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityManagerRequest(BaseModel):
    """安全管理请求模型"""

    action: str = Field(
        ..., description="操作类型（assess, check_permission, audit, analyze）"
    )
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
