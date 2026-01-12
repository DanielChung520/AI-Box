# 代碼功能說明: Observation Collector 數據模型
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Observation Collector 數據模型定義

符合 GRO 規範的 Observation Summary 模型。
"""

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class FanInMode(str, Enum):
    """Fan-in 模式枚舉"""

    ALL = "all"
    ANY = "any"
    QUORUM = "quorum"


class ObservationSummary(BaseModel):
    """Observation Summary 模型（符合 GRO 規範）"""

    success_rate: float = Field(..., description="成功率（0.0-1.0）", ge=0.0, le=1.0)
    blocking_issues: bool = Field(..., description="是否有阻塞問題")
    lowest_confidence: float = Field(..., description="最低置信度（0.0-1.0）", ge=0.0, le=1.0)
    observations: List[Dict[str, Any]] = Field(default_factory=list, description="觀察結果列表")
    total_count: int = Field(..., description="總觀察數量", ge=0)
    success_count: int = Field(..., description="成功數量", ge=0)
    failure_count: int = Field(..., description="失敗數量", ge=0)
    partial_count: int = Field(..., description="部分成功數量", ge=0)
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="問題列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")
