# 代碼功能說明: Task Cleanup Agent 數據模型
# 創建日期: 2026-01-23 10:30 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-23 12:50 UTC+8

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CleanupTarget(BaseModel):
    user_id: str = Field(..., description="目標用戶 ID (Email)") 
    task_id: Optional[str] = Field(None, description="特定任務 ID，若為 None 則清理用戶所有數據")


class CleanupStats(BaseModel):
    user_tasks: int = 0
    file_metadata: int = 0
    entities: int = 0
    relations: int = 0
    qdrant_collections: int = 0
    seaweedfs_directories: int = 0


class CleanupAnalysis(BaseModel):
    """LLM 分析結果"""
    urgency: str = Field(default="medium", description="緊急性: high/medium/low") 
    risk_level: str = Field(default="medium", description="風險等級: high/medium/low") 
    analysis: str = Field(default="", description="分析描述") 
    recommendation: str = Field(default="", description="清理建議")


class CleanupPlan(BaseModel):
    """LLM 生成的清理計劃"""
    steps: List[str] = Field(default_factory=list, description="清理步驟列表") 
    estimated_impact: str = Field(default="", description="預估影響") 
    warnings: List[str] = Field(default_factory=list, description="警告信息")


class CleanupVerification(BaseModel):
    """LLM 驗證結果"""
    is_complete: bool = Field(default=False, description="清理是否完整") 
    findings: str = Field(default="", description="驗證發現") 
    suggestions: List[str] = Field(default_factory=list, description="建議")


class CleanupResponse(BaseModel):
    success: bool
    message: str
    stats: Optional[CleanupStats] = None
    analysis: Optional[CleanupAnalysis] = None
    plan: Optional[CleanupPlan] = None
    verification: Optional[CleanupVerification] = None
    todo_list: Optional[List[str]] = None
    audit_record_id: Optional[str] = None


# --- AOGA Governance Models ---


class AOGAReasoning(BaseModel):
    model: str
    analysis: str
    risk_level: str
    plan_steps: List[str]


class AOGAApproval(BaseModel):
    required: bool
    approver: Optional[str] = None
    approved_at: Optional[str] = None
    approval_mode: Literal["explicit", "implicit"] = "explicit" 
    approval_token: Optional[str] = None


class AOGAExecution(BaseModel):
    mode: Literal["function", "agent"] = "function" 
    function_name: str
    result: str = "pending" 
    details: Dict[str, Any] = Field(default_factory=dict)


class AOGAAuditRecord(BaseModel):
    """符合 AOGA 架構的不可篡改審計日誌模型"""
    record_id: str = Field(..., description="唯一的審計記錄 ID") 
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat()) 
    actor: str
    action_type: str
    intent: str

    reasoning: Optional[AOGAReasoning] = None
    approval: Optional[AOGAApproval] = None
    execution: Optional[AOGAExecution] = None

    compliance_tags: List[str] = Field(default_factory=list) 
    content_hash: Optional[str] = None  # SHA-256 integrity hash