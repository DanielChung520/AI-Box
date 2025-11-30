# 代碼功能說明: Review Agent 數據模型
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Review Agent 數據模型定義"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ReviewStatus(str, Enum):
    """審查狀態"""

    PENDING = "pending"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class ReviewRequest(BaseModel):
    """審查請求模型"""

    result: Dict[str, Any] = Field(..., description="執行結果")
    expected: Optional[Dict[str, Any]] = Field(None, description="預期結果")
    criteria: Optional[List[str]] = Field(None, description="審查標準列表")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


class ReviewResult(BaseModel):
    """審查結果模型"""

    review_id: str = Field(..., description="審查ID")
    status: ReviewStatus = Field(..., description="審查狀態")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="質量評分")
    feedback: str = Field(..., description="審查反饋")
    suggestions: List[str] = Field(default_factory=list, description="改進建議列表")
    issues: List[str] = Field(default_factory=list, description="發現的問題列表")
    created_at: datetime = Field(default_factory=datetime.now, description="創建時間")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")
