# 代碼功能說明: AutoGen Workflow 工廠
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""建立 AutoGen Workflow 實例的工廠。"""

from __future__ import annotations

from typing import Optional

from agents.workflows.base import (
    WorkflowFactoryProtocol,
    WorkflowRequestContext,
)
from agents.autogen.workflow import AutoGenWorkflow
from agents.autogen.config import (
    AutoGenSettings,
    load_autogen_settings,
)


class AutoGenWorkflowFactory(WorkflowFactoryProtocol):
    """依據設定建立 AutoGen workflow。"""

    def __init__(self, settings: Optional[AutoGenSettings] = None) -> None:
        """
        初始化 AutoGen Workflow Factory。

        Args:
            settings: AutoGen 設定（可選）
        """
        self._settings = settings or load_autogen_settings()

    def build_workflow(self, request_ctx: WorkflowRequestContext) -> AutoGenWorkflow:
        """
        構建 AutoGen Workflow 實例。

        Args:
            request_ctx: 請求上下文

        Returns:
            AutoGenWorkflow 實例
        """
        return AutoGenWorkflow(
            settings=self._settings,
            request_ctx=request_ctx,
        )
