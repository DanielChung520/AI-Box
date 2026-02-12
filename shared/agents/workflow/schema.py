# Agent Workflow Schema 定義
# 所有 Agent 公用的工作流 Schema（持久化到 ArangoDB）
# 創建日期: 2026-02-08

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class WorkflowStatus(str, Enum):
    """工作流狀態"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(str, Enum):
    """步驟狀態"""

    PENDING = "pending"
    DISPATCHED = "dispatched"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CompensationStatus(str, Enum):
    """補償狀態"""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class SagaStep(BaseModel):
    """Saga 步驟定義"""

    step_id: int = Field(..., description="步驟 ID")
    action_type: str = Field(..., description="行動類型")
    description: str = Field(..., description="步驟描述")
    instruction: str = Field(default="", description="詳細執行指令")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="行動參數")

    # 補償定義
    compensation_type: Optional[str] = Field(None, description="補償類型")
    compensation_params: Dict[str, Any] = Field(default_factory=dict, description="補償參數")

    # 執行狀態
    status: StepStatus = Field(default=StepStatus.PENDING, description="步驟狀態")
    result_key: Optional[str] = Field(None, description="結果存儲鍵")
    retry_count: int = Field(default=0, description="重試次數")
    max_retries: int = Field(default=3, description="最大重試次數")


class CompensationAction(BaseModel):
    """補償動作定義"""

    action_id: str = Field(
        default_factory=lambda: f"COMP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}",
        description="補償動作 ID",
    )
    step_id: int = Field(..., description="關聯的步驟 ID")
    action_type: str = Field(..., description="原動作類型")
    compensation_type: str = Field(..., description="補償類型")
    params: Dict[str, Any] = Field(default_factory=dict, description="補償參數")
    status: CompensationStatus = Field(default=CompensationStatus.PENDING, description="補償狀態")
    executed_at: Optional[datetime] = Field(None, description="執行時間")
    error: Optional[str] = Field(None, description="執行錯誤")


class WorkflowState(BaseModel):
    """工作流狀態（持久化到 ArangoDB）"""

    workflow_id: str = Field(
        default_factory=lambda: f"WF-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}",
        description="工作流唯一標識",
    )
    session_id: str = Field(..., description="用戶會話 ID")
    user_id: Optional[str] = Field(None, description="用戶 ID")
    instruction: str = Field(..., description="原始指令")
    task_type: str = Field(default="general", description="任務類型")

    # 計劃
    plan: Optional[Dict[str, Any]] = Field(None, description="原始計劃")
    steps: List[SagaStep] = Field(default_factory=list, description="Saga 步驟列表")

    # 執行狀態
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING, description="工作流狀態")
    current_step: int = Field(default=0, description="當前步驟")
    completed_steps: List[int] = Field(default_factory=list, description="已完成的步驟")
    failed_steps: List[int] = Field(default_factory=list, description="失敗的步驟")
    skipped_steps: List[int] = Field(default_factory=list, description="跳過的步驟")

    # 結果
    results: Dict[str, Any] = Field(default_factory=dict, description="步驟結果")
    final_response: Optional[str] = Field(None, description="最終回覆")
    error: Optional[str] = Field(None, description="錯誤信息")

    # Saga 補償
    compensations: List[CompensationAction] = Field(
        default_factory=list, description="補償動作列表"
    )
    compensation_history: List[Dict] = Field(default_factory=list, description="補償歷史")

    # 用戶交互
    waiting_for_user: bool = Field(default=False, description="是否等待用戶確認")
    user_response: Optional[str] = Field(None, description="用戶回覆")

    # 心跳
    last_heartbeat: Optional[datetime] = Field(None, description="最後心跳時間")

    # 時間戳
    created_at: datetime = Field(default_factory=datetime.utcnow, description="創建時間")
    updated_at: Optional[datetime] = Field(None, description="更新時間")
    completed_at: Optional[datetime] = Field(None, description="完成時間")

    class Config:
        use_enum_values = True


class WorkflowEvent(BaseModel):
    """工作流事件（審計日誌）"""

    event_id: str = Field(
        default_factory=lambda: f"EVT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}",
        description="事件 ID",
    )
    workflow_id: str = Field(..., description="工作流 ID")
    event_type: str = Field(..., description="事件類型")
    step_id: Optional[int] = Field(None, description="步驟 ID")
    from_status: Optional[str] = Field(None, description="原狀態")
    to_status: Optional[str] = Field(None, description="新狀態")
    details: Dict[str, Any] = Field(default_factory=dict, description="事件詳情")
    actor: str = Field(default="system", description="觸發者")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="時間戳")


class CreateWorkflowRequest(BaseModel):
    """創建工作流請求"""

    instruction: str = Field(..., description="用戶指令")
    session_id: str = Field(..., description="會話 ID")
    user_id: Optional[str] = Field(None, description="用戶 ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文")


class ExecuteStepRequest(BaseModel):
    """執行步驟請求"""

    step_id: int = Field(..., description="步驟 ID")
    user_response: Optional[str] = Field(None, description="用戶回覆（用於確認步驟）")


class WorkflowResponse(BaseModel):
    """工作流 API 回覆"""

    success: bool
    workflow: Optional[WorkflowState] = None
    error: Optional[str] = None


class StepExecutionRequest(BaseModel):
    """步驟執行請求（RQ 任務）"""

    workflow_id: str
    step_id: int
    action_type: str
    instruction: str
    parameters: Dict[str, Any]
    compensation_key: str
    retry_count: int = 0
