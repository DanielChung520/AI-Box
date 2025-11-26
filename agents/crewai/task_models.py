# 代碼功能說明: Task 數據模型定義
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""定義 Task 相關的數據模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任務狀態枚舉。"""

    PENDING = "pending"  # 待處理
    IN_PROGRESS = "in_progress"  # 進行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失敗
    CANCELLED = "cancelled"  # 已取消


class TaskPriority(str, Enum):
    """任務優先級枚舉。"""

    LOW = "low"  # 低優先級
    MEDIUM = "medium"  # 中優先級
    HIGH = "high"  # 高優先級
    URGENT = "urgent"  # 緊急


class CrewTask(BaseModel):
    """任務定義。"""

    task_id: str = Field(..., description="任務 ID")
    crew_id: str = Field(..., description="隊伍 ID")
    description: str = Field(..., description="任務描述")
    assigned_agent: Optional[str] = Field(default=None, description="分配的 Agent 角色")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任務狀態")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="任務優先級")
    created_at: datetime = Field(default_factory=datetime.now, description="創建時間")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新時間")
    started_at: Optional[datetime] = Field(default=None, description="開始時間")
    completed_at: Optional[datetime] = Field(default=None, description="完成時間")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


class TaskResult(BaseModel):
    """任務執行結果。"""

    task_id: str = Field(..., description="任務 ID")
    status: TaskStatus = Field(..., description="任務狀態")
    output: Any = Field(default=None, description="任務輸出")
    error: Optional[str] = Field(default=None, description="錯誤信息")
    execution_time: float = Field(default=0.0, description="執行時間（秒）")
    token_usage: int = Field(default=0, description="Token 使用量")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


@dataclass
class TaskHistoryEntry:
    """任務歷史條目。"""

    task_id: str
    status: TaskStatus
    timestamp: datetime
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典。"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "metadata": self.metadata,
        }
