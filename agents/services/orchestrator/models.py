# 代碼功能說明: Agent Orchestrator 數據模型
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28 10:30:00 UTC+8

"""Agent Orchestrator 數據模型定義

注意：此模組中的 AgentInfo 已被 AgentRegistryInfo 替代。
保留 AgentInfo 僅為向後兼容，新代碼應使用 AgentRegistryInfo。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# 從 Registry 導入 AgentRegistryInfo 和 AgentStatus
from agents.services.registry.models import AgentRegistryInfo


class TaskStatus(str, Enum):
    """任務狀態枚舉"""

    PENDING = "pending"  # 待處理
    ASSIGNED = "assigned"  # 已分配
    RUNNING = "running"  # 運行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失敗
    CANCELLED = "cancelled"  # 已取消


# 向後兼容：保留 AgentInfo 作為 AgentRegistryInfo 的別名
# 新代碼應直接使用 AgentRegistryInfo
AgentInfo = AgentRegistryInfo  # type: ignore[misc,assignment]


class TaskRequest(BaseModel):
    """任務請求模型"""

    task_id: str = Field(..., description="任務ID")
    task_type: str = Field(..., description="任務類型")
    task_data: Dict[str, Any] = Field(..., description="任務數據")
    required_agents: Optional[List[str]] = Field(None, description="需要的Agent列表")
    priority: int = Field(default=0, description="優先級")
    timeout: Optional[int] = Field(None, description="超時時間（秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


class TaskResult(BaseModel):
    """任務結果模型"""

    task_id: str = Field(..., description="任務ID")
    status: TaskStatus = Field(..., description="任務狀態")
    result: Optional[Dict[str, Any]] = Field(None, description="任務結果")
    error: Optional[str] = Field(None, description="錯誤信息")
    agent_id: Optional[str] = Field(None, description="執行的Agent ID")
    started_at: Optional[datetime] = Field(None, description="開始時間")
    completed_at: Optional[datetime] = Field(None, description="完成時間")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


class AgentRegistrationRequest(BaseModel):
    """Agent 註冊請求模型"""

    agent_id: str = Field(..., description="Agent ID")
    agent_type: str = Field(..., description="Agent 類型")
    capabilities: List[str] = Field(default_factory=list, description="能力列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


class ValidationResult(BaseModel):
    """驗證結果模型

    用於第一層預檢的驗證結果。
    """

    valid: bool = Field(..., description="驗證是否通過")
    reason: Optional[str] = Field(None, description="驗證失敗的原因（如果驗證失敗）")


class TodoItem(BaseModel):
    """Todo 項目模型

    用於任務規劃和編排的單個 todo 項目。
    """

    todo_id: str = Field(..., description="Todo ID")
    description: str = Field(..., description="Todo 描述")
    agent_id: Optional[str] = Field(None, description="負責的 Agent ID")
    capability: Optional[str] = Field(None, description="所需能力")
    priority: int = Field(default=0, description="優先級（數字越大優先級越高）")
    depends_on: List[str] = Field(default_factory=list, description="依賴的 Todo ID 列表")
    estimated_duration: Optional[int] = Field(None, description="預估執行時間（秒）")
    status: str = Field(default="pending", description="狀態：pending, in_progress, completed, failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


class TaskPlan(BaseModel):
    """任務計劃模型

    包含完整任務分解後的 todo 列表和執行計劃。
    """

    plan_id: str = Field(..., description="計劃 ID")
    instruction: str = Field(..., description="原始指令")
    todos: List[TodoItem] = Field(default_factory=list, description="Todo 列表（已排序）")
    total_estimated_duration: Optional[int] = Field(None, description="總預估執行時間（秒）")
    reasoning: Optional[str] = Field(None, description="規劃理由")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="創建時間")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")
