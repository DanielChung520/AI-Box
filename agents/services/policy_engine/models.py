# 代碼功能說明: Policy Engine 數據模型
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Policy Engine 數據模型定義

符合 GRO 規範的政策模型。
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agents.services.state_store.models import Decision


class FanInMode(str, Enum):
    """Fan-in 模式枚舉"""

    ALL = "all"
    ANY = "any"
    QUORUM = "quorum"


class RetryPolicy(BaseModel):
    """重試策略"""

    max_retry: int = Field(..., description="最大重試次數", ge=0)
    backoff_sec: int = Field(..., description="退避時間（秒）", ge=0)


class FanInPolicy(BaseModel):
    """Fan-in 策略"""

    mode: FanInMode = Field(..., description="Fan-in 模式")
    threshold: float = Field(default=0.7, description="閾值（僅 quorum 模式使用）", ge=0.0, le=1.0)


class CapabilityPolicy(BaseModel):
    """能力策略"""

    allow: List[str] = Field(default_factory=list, description="允許的能力列表")
    forbid: List[str] = Field(default_factory=list, description="禁止的能力列表")


class PolicyDefaults(BaseModel):
    """政策默認值"""

    retry: RetryPolicy = Field(default_factory=lambda: RetryPolicy(max_retry=2, backoff_sec=30))
    fan_in: FanInPolicy = Field(
        default_factory=lambda: FanInPolicy(mode=FanInMode.ALL, threshold=0.7)
    )
    allow: List[str] = Field(default_factory=list, description="默認允許的能力列表")
    forbid: List[str] = Field(default_factory=list, description="默認禁止的能力列表")


class PolicyRule(BaseModel):
    """政策規則"""

    name: str = Field(..., description="規則名稱")
    priority: int = Field(default=100, description="優先級（數字越大越優先）")
    when: Dict[str, Any] = Field(default_factory=dict, description="條件表達式")
    then: Dict[str, Any] = Field(default_factory=dict, description="決策輸出")


class Policy(BaseModel):
    """政策模型"""

    spec_version: str = Field(default="1.0", description="規範版本")
    defaults: PolicyDefaults = Field(default_factory=PolicyDefaults, description="默認值")
    rules: List[PolicyRule] = Field(default_factory=list, description="規則列表")


class PolicyContext(BaseModel):
    """政策上下文（Policy Engine 的輸入）"""

    command: Dict[str, Any] = Field(default_factory=dict, description="命令分類")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="約束條件")
    plan: Optional[Dict[str, Any]] = Field(None, description="任務計劃（DAG metadata）")
    observations: List[Dict[str, Any]] = Field(default_factory=list, description="觀察結果列表")
    observation_summary: Dict[str, Any] = Field(default_factory=dict, description="Fan-in 匯整結果")
    retry_count: int = Field(default=0, description="重試次數", ge=0)
    capability_registry: Dict[str, Any] = Field(default_factory=dict, description="能力註冊表")


class EffectivePolicy(BaseModel):
    """有效政策（Policy Engine 的輸出）"""

    decision: Optional[Decision] = Field(None, description="決策結果")
    allow: List[str] = Field(default_factory=list, description="允許的能力列表")
    forbid: List[str] = Field(default_factory=list, description="禁止的能力列表")
    retry: Optional[RetryPolicy] = Field(None, description="重試策略")
    fan_in: Optional[FanInPolicy] = Field(None, description="Fan-in 策略")
    rule_hits: List[str] = Field(default_factory=list, description="命中的規則列表（用於審計）")
