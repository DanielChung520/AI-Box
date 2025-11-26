# 代碼功能說明: Execution Agent 數據模型
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Execution Agent 數據模型定義"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ExecutionStatus(str, Enum):
    """執行狀態"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionRequest(BaseModel):
    """執行請求模型"""

    task: str = Field(..., description="任務描述")
    tool_name: Optional[str] = Field(None, description="工具名稱")
    tool_args: Optional[Dict[str, Any]] = Field(None, description="工具參數")
    plan_step_id: Optional[str] = Field(None, description="計劃步驟ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


class ExecutionResult(BaseModel):
    """執行結果模型"""

    execution_id: str = Field(..., description="執行ID")
    status: ExecutionStatus = Field(..., description="執行狀態")
    result: Optional[Dict[str, Any]] = Field(None, description="執行結果")
    error: Optional[str] = Field(None, description="錯誤信息")
    tool_name: Optional[str] = Field(None, description="使用的工具名稱")
    execution_time: Optional[float] = Field(None, description="執行時間（秒）")
    started_at: Optional[datetime] = Field(None, description="開始時間")
    completed_at: Optional[datetime] = Field(None, description="完成時間")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")
