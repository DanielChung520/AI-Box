# 代碼功能說明: Message Bus 數據模型
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Message Bus 數據模型定義

符合 GRO 規範的 Message Contracts。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """消息類型枚舉"""

    TASK_DISPATCH = "TASK_DISPATCH"
    TASK_RESULT = "TASK_RESULT"
    HEARTBEAT = "HEARTBEAT"
    OBSERVATION_SUMMARY = "OBSERVATION_SUMMARY"


class GlobalEnvelope(BaseModel):
    """全局信封（符合 GRO 規範）"""

    spec_version: str = Field(default="1.0", description="規範版本")
    react_id: str = Field(..., description="ReAct session ID", min_length=8)
    iteration: int = Field(default=0, description="迭代次數", ge=0)
    trace: Dict[str, Any] = Field(
        default_factory=dict,
        description="追蹤信息（包含 correlation_id、parent_task_id 等）",
    )
    timestamps: Dict[str, str] = Field(
        default_factory=lambda: {"created_at": datetime.utcnow().isoformat()},
        description="時間戳",
    )


class TaskDispatch(BaseModel):
    """任務派發消息（符合 GRO 規範）"""

    message_type: MessageType = Field(default=MessageType.TASK_DISPATCH)
    react_id: str = Field(..., description="ReAct session ID", min_length=8)
    iteration: int = Field(default=0, description="迭代次數", ge=0)
    task_id: str = Field(..., description="任務 ID", min_length=8)
    delegate_to: str = Field(..., description="委派給的 Agent 類型")
    objective: str = Field(..., description="任務目標")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")
    success_criteria: List[str] = Field(default_factory=list, description="成功標準")
    timeout_sec: int = Field(default=300, description="超時時間（秒）", ge=1, le=86400)
    policy: Dict[str, Any] = Field(default_factory=dict, description="政策配置")
    correlation_id: Optional[str] = Field(None, description="關聯 ID")
    parent_task_id: Optional[str] = Field(None, description="父任務 ID")


class TaskResult(BaseModel):
    """任務結果消息（符合 GRO 規範）"""

    message_type: MessageType = Field(default=MessageType.TASK_RESULT)
    react_id: str = Field(..., description="ReAct session ID", min_length=8)
    task_id: str = Field(..., description="任務 ID", min_length=8)
    agent_id: str = Field(..., description="Agent ID")
    status: str = Field(..., description="狀態（success/partial/failed）")
    result: Dict[str, Any] = Field(default_factory=dict, description="結果")
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="問題列表")
    confidence: float = Field(default=1.0, description="置信度", ge=0.0, le=1.0)
    execution_meta: Dict[str, Any] = Field(default_factory=dict, description="執行元數據")
    correlation_id: Optional[str] = Field(None, description="關聯 ID")
