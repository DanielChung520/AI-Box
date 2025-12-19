# 代碼功能說明: Workflow Factory Router
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""根據工作流類型路由到對應的 Workflow Factory。"""

from __future__ import annotations

import logging
from typing import Optional

from agents.task_analyzer.models import WorkflowType
from agents.workflows.base import WorkflowFactoryProtocol, WorkflowRequestContext, WorkflowRunner
from agents.workflows.hybrid_factory import HybridWorkflowFactory
from agents.workflows.langchain_graph_factory import LangChainWorkflowFactory

logger = logging.getLogger(__name__)

# 延遲導入以避免循環依賴
_crewai_factory: Optional[WorkflowFactoryProtocol] = None
_autogen_factory: Optional[WorkflowFactoryProtocol] = None
_hybrid_factory: Optional[WorkflowFactoryProtocol] = None


def _get_crewai_factory() -> WorkflowFactoryProtocol:
    """獲取 CrewAI Workflow Factory（延遲導入）。"""
    global _crewai_factory
    if _crewai_factory is None:
        from agents.crewai.factory import CrewAIWorkflowFactory

        _crewai_factory = CrewAIWorkflowFactory()
    return _crewai_factory


def _get_autogen_factory() -> WorkflowFactoryProtocol:
    """獲取 AutoGen Workflow Factory（延遲導入）。"""
    global _autogen_factory
    if _autogen_factory is None:
        from agents.autogen.factory import AutoGenWorkflowFactory

        _autogen_factory = AutoGenWorkflowFactory()
    return _autogen_factory


class WorkflowFactoryRouter:
    """工作流工廠路由器。"""

    def __init__(self):
        """初始化工作流工廠路由器。"""
        self._langchain_factory = LangChainWorkflowFactory()
        self._hybrid_factory = HybridWorkflowFactory()
        self._factories: dict[WorkflowType, WorkflowFactoryProtocol] = {
            WorkflowType.LANGCHAIN: self._langchain_factory,
            WorkflowType.CREWAI: _get_crewai_factory(),
            WorkflowType.AUTOGEN: _get_autogen_factory(),
            WorkflowType.HYBRID: self._hybrid_factory,
        }

    def get_factory(self, workflow_type: WorkflowType) -> Optional[WorkflowFactoryProtocol]:
        """
        獲取對應的工作流工廠。

        Args:
            workflow_type: 工作流類型

        Returns:
            工作流工廠，如果不存在則返回 None
        """
        factory = self._factories.get(workflow_type)
        if factory is None:
            logger.warning(f"No factory found for workflow type: {workflow_type.value}")
        return factory

    def build_workflow(
        self,
        workflow_type: WorkflowType,
        request_ctx: WorkflowRequestContext,
    ) -> Optional[WorkflowRunner]:
        """
        構建工作流實例。

        Args:
            workflow_type: 工作流類型
            request_ctx: 請求上下文

        Returns:
            工作流實例，如果構建失敗則返回 None
        """
        factory = self.get_factory(workflow_type)
        if not factory:
            return None

        try:
            workflow = factory.build_workflow(request_ctx)
            logger.info(f"Built {workflow_type.value} workflow for task: {request_ctx.task_id}")
            return workflow
        except Exception as exc:
            logger.error(f"Failed to build {workflow_type.value} workflow: {exc}", exc_info=True)
            return None


# 全局實例
_router: Optional[WorkflowFactoryRouter] = None


def get_workflow_factory_router() -> WorkflowFactoryRouter:
    """獲取全局工作流工廠路由器實例。"""
    global _router
    if _router is None:
        _router = WorkflowFactoryRouter()
    return _router
