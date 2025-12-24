# 代碼功能說明: Workflow 基礎資料結構與協定
# 創建日期: 2025-11-26 20:07 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 20:07 (UTC+8)

"""定義工作流模組的基礎資料結構與協定。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol


@dataclass(slots=True)
class WorkflowRequestContext:
    """封裝建立工作流實例時需要的上下文。"""

    task_id: str
    task: str
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    workflow_config: Optional[Dict[str, Any]] = None


@dataclass(slots=True)
class WorkflowTelemetryEvent:
    """描述工作流在運行過程中的觀測事件。"""

    name: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowExecutionResult:
    """統一的工作流執行輸出。"""

    status: str
    output: Any
    reasoning: Optional[str] = None
    telemetry: list[WorkflowTelemetryEvent] = field(default_factory=list)
    state_snapshot: Optional[Dict[str, Any]] = None


class WorkflowFactoryProtocol(Protocol):
    """所有工作流工廠需遵循的介面。"""

    def build_workflow(self, request_ctx: WorkflowRequestContext) -> "WorkflowRunner":
        """建立對應工作流實例。"""


class WorkflowRunner(Protocol):
    """統一的工作流執行協定。"""

    async def run(self) -> WorkflowExecutionResult:
        """執行工作流並回傳結果。"""
