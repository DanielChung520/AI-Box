# 代碼功能說明: LangChain/Graph Workflow 狀態定義
# 創建日期: 2025-11-26 20:07 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 20:07 (UTC+8)

"""定義 LangChain/Graph 工作流使用的狀態結構。"""

from __future__ import annotations

import operator
from typing import Any, Dict, List, Optional, TypedDict

from typing_extensions import Annotated, Literal

from agents.workflows.base import WorkflowTelemetryEvent


class LangGraphState(TypedDict, total=False):
    """提供給 LangGraph StateGraph 使用的狀態。"""

    task: str
    context: Dict[str, Any]
    plan: List[str]
    current_step: int
    outputs: Annotated[List[str], operator.add]
    route: Literal["standard", "deep_dive"]
    status: Literal["initialized", "planning", "executing", "review", "completed", "failed"]
    error: Optional[str]
    telemetry: Annotated[List[WorkflowTelemetryEvent], operator.add]


def build_initial_state(task: str, context: Optional[Dict[str, Any]] = None) -> LangGraphState:
    """建立 LangGraph 初始狀態。"""

    return LangGraphState(
        task=task,
        context=context or {},
        plan=[],
        current_step=0,
        outputs=[],
        route="standard",
        status="initialized",
        telemetry=[],
    )
