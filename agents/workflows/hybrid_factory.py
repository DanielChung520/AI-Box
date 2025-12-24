# 代碼功能說明: 混合模式工作流工廠
# 創建日期: 2025-11-26 23:00 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 23:00 (UTC+8)

"""建立混合模式工作流實例的工廠。"""

from __future__ import annotations

from agents.workflows.base import WorkflowFactoryProtocol, WorkflowRequestContext
from agents.workflows.hybrid_orchestrator import HybridOrchestrator


class HybridWorkflowFactory(WorkflowFactoryProtocol):
    """依據設定建立混合模式 workflow。"""

    def __init__(self):
        """初始化混合模式工作流工廠。"""
        pass

    def build_workflow(self, request_ctx: WorkflowRequestContext) -> HybridOrchestrator:
        """
        構建混合模式工作流實例。

        Args:
            request_ctx: 請求上下文

        Returns:
            HybridOrchestrator 實例
        """
        # 從 workflow_config 獲取策略配置
        workflow_config = request_ctx.workflow_config or {}
        primary_mode = workflow_config.get("primary_workflow", "autogen")
        fallback_modes = workflow_config.get("fallback_workflows", ["langgraph"])

        # 轉換工作流類型字符串為模式字符串
        mode_mapping = {
            "autogen": "autogen",
            "langchain": "langgraph",
            "langgraph": "langgraph",
            "crewai": "crewai",
        }
        primary_mode = mode_mapping.get(primary_mode, "autogen")
        fallback_modes = [mode_mapping.get(f, "langgraph") for f in fallback_modes]

        return HybridOrchestrator(
            request_ctx=request_ctx,
            primary_mode=primary_mode,
            fallback_modes=fallback_modes,
        )
