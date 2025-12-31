# 代碼功能說明: System Config Agent 數據模型
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""System Config Agent 數據模型定義"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConfigOperationResult(BaseModel):
    """配置操作結果模型"""

    action: str = Field(..., description="操作類型（query/create/update/delete/list/rollback）")
    scope: str = Field(..., description="配置範圍")
    level: Optional[str] = Field(None, description="配置層級（system/tenant/user）")
    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(None, description="操作消息")
    config: Optional[Dict[str, Any]] = Field(None, description="配置數據（查詢/更新時返回）")
    changes: Optional[Dict[str, Any]] = Field(None, description="變更內容（更新時返回）")
    impact_analysis: Optional[Dict[str, Any]] = Field(None, description="影響分析（預覽時返回）")
    audit_log_id: Optional[str] = Field(None, description="審計日誌 ID")
    rollback_id: Optional[str] = Field(None, description="回滾 ID（用於回滾）")
    error: Optional[str] = Field(None, description="錯誤信息")


class ComplianceCheckResult(BaseModel):
    """合規性檢查結果模型"""

    valid: bool = Field(..., description="是否通過檢查")
    reason: Optional[str] = Field(None, description="檢查失敗原因")
    convergence_violations: List[str] = Field(default_factory=list, description="收斂規則違反列表")
    business_rule_violations: List[str] = Field(
        default_factory=list, description="業務規則違反列表"
    )
    details: Optional[Dict[str, Any]] = Field(None, description="詳細檢查信息")


class ConfigPreview(BaseModel):
    """配置預覽模型"""

    changes: Dict[str, Any] = Field(..., description="變更內容")
    impact_analysis: Dict[str, Any] = Field(..., description="影響分析")
    cost_change: Optional[Dict[str, Any]] = Field(None, description="成本變化")
    risk_level: str = Field(..., description="風險級別（low/medium/high）")
    confirmation_required: bool = Field(default=True, description="是否需要確認")


class RollbackResult(BaseModel):
    """回滾結果模型"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="回滾消息")
    rollback_id: str = Field(..., description="回滾 ID")
    restored_config: Optional[Dict[str, Any]] = Field(None, description="恢復的配置")


class InspectionIssue(BaseModel):
    """配置巡檢問題模型"""

    issue_type: str = Field(..., description="問題類型（convergence/consistency/security）")
    severity: str = Field(..., description="嚴重程度（high/medium/low）")
    scope: str = Field(..., description="配置範圍")
    level: Optional[str] = Field(None, description="配置層級（system/tenant/user）")
    tenant_id: Optional[str] = Field(None, description="租戶 ID（如果適用）")
    user_id: Optional[str] = Field(None, description="用戶 ID（如果適用）")
    description: str = Field(..., description="問題描述")
    affected_field: Optional[str] = Field(None, description="受影響的配置字段")
    current_value: Optional[Any] = Field(None, description="當前值")
    expected_value: Optional[Any] = Field(None, description="期望值")
    impact: Optional[str] = Field(None, description="影響說明")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="詳細信息")


class FixSuggestion(BaseModel):
    """修復建議模型"""

    issue_id: Optional[str] = Field(None, description="問題 ID")
    auto_fixable: bool = Field(default=False, description="是否可以自動修復")
    fix_action: str = Field(..., description="修復動作描述")
    fix_steps: List[str] = Field(default_factory=list, description="修復步驟列表")
    suggested_config: Optional[Dict[str, Any]] = Field(None, description="建議的配置值")
    risk_level: str = Field(default="low", description="修復風險級別（low/medium/high）")
    requires_confirmation: bool = Field(default=True, description="是否需要確認")
