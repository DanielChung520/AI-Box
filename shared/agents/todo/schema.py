# 代碼功能說明: Agent Todo Schema 定義
# 創建日期: 2026-02-07
# 創建人: OpenCode AI
# 最後修改日期: 2026-02-07

"""Agent Todo Schema 定義 - AI-Box 與 MM-Agent 共享"""

from typing import Optional, List, Dict, Any, Set
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class TodoState(str, Enum):
    """Todo 狀態全集（不可擴充）"""

    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TodoType(str, Enum):
    """任務類型（正面表列）"""

    KNOWLEDGE_RETRIEVAL = "KNOWLEDGE_RETRIEVAL"
    DATA_QUERY = "DATA_QUERY"
    COMPUTATION = "COMPUTATION"
    RESPONSE_GENERATION = "RESPONSE_GENERATION"


class TodoPriority(str, Enum):
    """任務優先級"""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class StructuredError(BaseModel):
    """結構化錯誤"""

    code: str = Field(..., description="錯誤碼")
    message: str = Field(..., description="錯誤訊息")
    context: Optional[Dict[str, Any]] = Field(default=None, description="錯誤上下文")
    recoverable: bool = Field(default=False, description="是否可恢復")


class ExecutionResult(BaseModel):
    """執行結果結構"""

    success: bool = Field(..., description="是否成功")
    data: Optional[Dict[str, Any]] = Field(default=None, description="結果資料")
    error: Optional[StructuredError] = Field(default=None, description="結構化錯誤")
    observation: str = Field(default="", description="觀察記錄")


class Todo(BaseModel):
    """Todo 基礎結構"""

    todo_id: str = Field(
        default_factory=lambda: f"TODO-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}",
        description="唯一識別碼",
    )
    type: TodoType = Field(..., description="任務類型")
    state: TodoState = Field(default=TodoState.PENDING, description="當前狀態")
    priority: TodoPriority = Field(default=TodoPriority.NORMAL, description="優先級")
    owner_agent: str = Field(..., description="所屬 Agent")
    instruction: str = Field(..., description="執行指令")

    input: Dict[str, Any] = Field(default_factory=dict, description="輸入參數")
    result: Optional[ExecutionResult] = Field(default=None, description="執行結果")

    created_at: datetime = Field(default_factory=datetime.utcnow, description="建立時間")
    updated_at: Optional[datetime] = Field(default=None, description="更新時間")
    completed_at: Optional[datetime] = Field(default=None, description="完成時間")

    class Config:
        use_enum_values = True


class TodoWithHistory(Todo):
    """帶歷史記錄的 Todo"""

    history: List[Dict[str, Any]] = Field(default_factory=list, description="狀態歷史")


class TodoList(BaseModel):
    """Todo 列表"""

    todos: List[Todo]
    total: int
    page: int = 1
    page_size: int = 20


class CreateTodoRequest(BaseModel):
    """建立 Todo 請求"""

    type: TodoType
    priority: TodoPriority = TodoPriority.NORMAL
    owner_agent: str
    instruction: str
    input: Dict[str, Any] = Field(default_factory=dict)


class UpdateTodoRequest(BaseModel):
    """更新 Todo 請求"""

    state: Optional[TodoState] = None
    result: Optional[ExecutionResult] = None


class TodoResponse(BaseModel):
    """Todo API 回應"""

    success: bool
    todo: Optional[Todo] = None
    error: Optional[StructuredError] = None
