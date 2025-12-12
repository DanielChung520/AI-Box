# 代碼功能說明: Planning Agent 數據模型
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Planning Agent 數據模型定義"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class PlanStepStatus(str, Enum):
    """計劃步驟狀態"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStep(BaseModel):
    """計劃步驟"""

    step_id: str = Field(..., description="步驟ID")
    step_number: int = Field(..., description="步驟編號")
    description: str = Field(..., description="步驟描述")
    action: str = Field(..., description="執行動作")
    dependencies: List[str] = Field(
        default_factory=list, description="依賴的步驟ID列表"
    )
    status: PlanStepStatus = Field(
        default=PlanStepStatus.PENDING, description="步驟狀態"
    )
    result: Optional[Dict[str, Any]] = Field(None, description="步驟結果")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


class PlanRequest(BaseModel):
    """計劃請求模型"""

    task: str = Field(..., description="任務描述")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    requirements: Optional[List[str]] = Field(None, description="要求列表")
    constraints: Optional[List[str]] = Field(None, description="約束條件列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


class PlanResult(BaseModel):
    """計劃結果模型"""

    plan_id: str = Field(..., description="計劃ID")
    task: str = Field(..., description="任務描述")
    steps: List[PlanStep] = Field(default_factory=list, description="計劃步驟列表")
    estimated_duration: Optional[int] = Field(None, description="預估執行時間（秒）")
    feasibility_score: float = Field(..., ge=0.0, le=1.0, description="可行性評分")
    created_at: datetime = Field(default_factory=datetime.now, description="創建時間")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")
