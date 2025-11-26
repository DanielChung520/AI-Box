# 代碼功能說明: LangChain/Graph Workflow 工廠
# 創建日期: 2025-11-26 20:07 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 20:07 (UTC+8)

"""建立 LangChain/Graph Workflow 實例的工廠。"""

from __future__ import annotations

from typing import Optional

from agents.workflows.base import (
    WorkflowFactoryProtocol,
    WorkflowRequestContext,
)
from agents.workflows.langchain_graph import LangChainGraphWorkflow
from agents.workflows.langchain_graph.telemetry import WorkflowTelemetryCollector
from agents.workflows.settings import (
    LangChainGraphSettings,
    load_langchain_graph_settings,
)


class LangChainWorkflowFactory(WorkflowFactoryProtocol):
    """依據設定建立 LangChain/Graph workflow。"""

    def __init__(self, settings: Optional[LangChainGraphSettings] = None) -> None:
        self._settings = settings or load_langchain_graph_settings()

    def build_workflow(
        self, request_ctx: WorkflowRequestContext
    ) -> LangChainGraphWorkflow:
        telemetry = WorkflowTelemetryCollector(
            enabled_metrics=self._settings.telemetry.emit_metrics,
            enabled_traces=self._settings.telemetry.emit_traces,
            enabled_logs=self._settings.telemetry.emit_logs,
        )
        return LangChainGraphWorkflow(
            settings=self._settings,
            request_ctx=request_ctx,
            telemetry=telemetry,
        )
