# 代碼功能說明: State Store 數據模型
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""State Store 數據模型定義

符合 GRO 規範的 ReAct 狀態和 Decision Log 模型。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReactStateType(str, Enum):
    """ReAct 狀態類型枚舉"""

    AWARENESS = "AWARENESS"
    PLANNING = "PLANNING"
    DELEGATION = "DELEGATION"
    OBSERVATION = "OBSERVATION"
    DECISION = "DECISION"


class DecisionAction(str, Enum):
    """決策動作枚舉（符合 GRO 規範）"""

    COMPLETE = "complete"
    RETRY = "retry"
    EXTEND_PLAN = "extend_plan"
    ESCALATE = "escalate"


class DecisionOutcome(str, Enum):
    """決策結果枚舉"""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class Decision(BaseModel):
    """決策模型（符合 GRO 規範）"""

    action: DecisionAction = Field(..., description="決策動作")
    reason: Optional[str] = Field(None, description="決策理由")
    next_state: ReactStateType = Field(..., description="下一個狀態")


class ReactState(BaseModel):
    """ReAct 狀態模型（符合 GRO 規範）"""

    react_id: str = Field(..., description="ReAct session ID", min_length=8)
    iteration: int = Field(..., description="迭代次數", ge=0)
    state: ReactStateType = Field(..., description="當前狀態")
    input_signature: Dict[str, Any] = Field(default_factory=dict, description="輸入簽名（命令分類、風險等級等）")
    observations: Optional[Dict[str, Any]] = Field(None, description="觀察結果（OBSERVATION 狀態時使用）")
    decision: Optional[Decision] = Field(None, description="決策結果（DECISION 狀態時使用）")
    plan: Optional[Dict[str, Any]] = Field(None, description="任務計劃（PLANNING 狀態時使用）")
    delegations: Optional[List[Dict[str, Any]]] = Field(
        None, description="任務派發列表（DELEGATION 狀態時使用）"
    )
    correlation_id: Optional[str] = Field(None, description="關聯 ID（用於跨系統追蹤）")
    parent_task_id: Optional[str] = Field(None, description="父任務 ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="時間戳")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（用於持久化）"""
        result = {
            "react_id": self.react_id,
            "iteration": self.iteration,
            "state": self.state.value,
            "input_signature": self.input_signature,
            "correlation_id": self.correlation_id,
            "parent_task_id": self.parent_task_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

        if self.observations is not None:
            result["observations"] = self.observations

        if self.decision is not None:
            result["decision"] = {
                "action": self.decision.action.value,
                "reason": self.decision.reason,
                "next_state": self.decision.next_state.value,
            }

        if self.plan is not None:
            result["plan"] = self.plan

        if self.delegations is not None:
            result["delegations"] = self.delegations

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReactState":
        """從字典創建 ReactState 對象"""
        # 解析 decision
        decision = None
        if "decision" in data and data["decision"]:
            decision_data = data["decision"]
            decision = Decision(
                action=DecisionAction(decision_data["action"]),
                reason=decision_data.get("reason"),
                next_state=ReactStateType(decision_data["next_state"]),
            )

        # 解析 timestamp
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            react_id=data["react_id"],
            iteration=data["iteration"],
            state=ReactStateType(data["state"]),
            input_signature=data.get("input_signature", {}),
            observations=data.get("observations"),
            decision=decision,
            plan=data.get("plan"),
            delegations=data.get("delegations"),
            correlation_id=data.get("correlation_id"),
            parent_task_id=data.get("parent_task_id"),
            timestamp=timestamp,
            metadata=data.get("metadata", {}),
        )


class DecisionLog(BaseModel):
    """Decision Log 模型（符合 GRO 規範）"""

    react_id: str = Field(..., description="ReAct session ID", min_length=8)
    iteration: int = Field(..., description="迭代次數", ge=0)
    state: ReactStateType = Field(..., description="狀態")
    input_signature: Dict[str, Any] = Field(default_factory=dict, description="輸入簽名")
    observations: Optional[Dict[str, Any]] = Field(None, description="觀察結果")
    decision: Decision = Field(..., description="決策結果")
    outcome: DecisionOutcome = Field(..., description="決策結果（success/failure/partial）")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="時間戳")
    correlation_id: Optional[str] = Field(None, description="關聯 ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（用於持久化）"""
        return {
            "react_id": self.react_id,
            "iteration": self.iteration,
            "state": self.state.value,
            "input_signature": self.input_signature,
            "observations": self.observations,
            "decision": {
                "action": self.decision.action.value,
                "reason": self.decision.reason,
                "next_state": self.decision.next_state.value,
            },
            "outcome": self.outcome.value,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionLog":
        """從字典創建 DecisionLog 對象"""
        # 解析 decision
        decision_data = data["decision"]
        decision = Decision(
            action=DecisionAction(decision_data["action"]),
            reason=decision_data.get("reason"),
            next_state=ReactStateType(decision_data["next_state"]),
        )

        # 解析 timestamp
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            react_id=data["react_id"],
            iteration=data["iteration"],
            state=ReactStateType(data["state"]),
            input_signature=data.get("input_signature", {}),
            observations=data.get("observations"),
            decision=decision,
            outcome=DecisionOutcome(data["outcome"]),
            timestamp=timestamp,
            correlation_id=data.get("correlation_id"),
            metadata=data.get("metadata", {}),
        )
