# 代碼功能說明: CrewAI Workflow 工廠
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""建立 CrewAI Workflow 實例的工廠。"""

from __future__ import annotations

from typing import Optional

from agents.workflows.base import (
    WorkflowFactoryProtocol,
    WorkflowRequestContext,
)
from agents.crewai.workflow import CrewAIWorkflow
from agents.crewai.settings import (
    CrewAISettings,
    load_crewai_settings,
)


class CrewAIWorkflowFactory(WorkflowFactoryProtocol):
    """依據設定建立 CrewAI workflow。"""

    def __init__(self, settings: Optional[CrewAISettings] = None) -> None:
        """
        初始化 CrewAI Workflow Factory。

        Args:
            settings: CrewAI 設定（可選）
        """
        self._settings = settings or load_crewai_settings()

    def build_workflow(self, request_ctx: WorkflowRequestContext) -> CrewAIWorkflow:
        """
        構建 CrewAI Workflow 實例。

        Args:
            request_ctx: 請求上下文

        Returns:
            CrewAIWorkflow 實例
        """
        return CrewAIWorkflow(
            settings=self._settings,
            request_ctx=request_ctx,
        )
