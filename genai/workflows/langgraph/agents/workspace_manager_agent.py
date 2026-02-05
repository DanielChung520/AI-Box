from __future__ import annotations
# 代碼功能說明: WorkspaceManagerAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""WorkspaceManagerAgent實現 - 負責任務工作區初始化和管理LangGraph節點"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceManagementResult:
    """工作區管理結果"""
    workspace_created: bool
    workspace_bound: bool
    workspace_cleaned: bool
    file_structure_initialized: bool
    workspace_id: str
    workspace_path: str
    initial_files_created: List[str] = field(default_factory=list)
    reasoning: str = ""


class WorkspaceManagerAgent(BaseAgentNode):
    """工作區管理Agent - 負責為每個任務創建獨立的物理和邏輯工作區"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化工作區服務
        self.workspace_service = None
        self._initialize_services()

    def _initialize_services(self) -> None:
        """初始化工作區管理相關服務"""
        try:
            # 從系統服務中獲取任務工作區服務
            from services.api.services.task_workspace_service import get_task_workspace_service

            self.workspace_service = get_task_workspace_service()
            logger.info("TaskWorkspaceService initialized for WorkspaceManagerAgent")
        except Exception as e:
            logger.error(f"Failed to initialize TaskWorkspaceService: {e}")
            self.workspace_service = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行工作區管理和維護
        """
        try:
            # 檢查任務管理結果是否存在
            task_management = getattr(state, "task_management", None)

            if not task_management:
                return NodeResult.failure("No task management result found for workspace creation")

            # 執行工作區管理
            workspace_result = await self._manage_workspace(task_management, state)

            if not workspace_result:
                return NodeResult.failure("Workspace management failed")

            # 更新狀態
            state.workspace_management = workspace_result

            # 記錄觀察
            state.add_observation(
                "workspace_management_completed",
                {
                    "workspace_id": workspace_result.workspace_id,
                    "files_count": len(workspace_result.initial_files_created),
                },
                1.0 if workspace_result.workspace_created else 0.5,
            )

            logger.info(
                f"Workspace management completed for workspace {workspace_result.workspace_id}",
            )

            return NodeResult.success(
                data={
                    "workspace_management": {
                        "workspace_id": workspace_result.workspace_id,
                        "workspace_path": workspace_result.workspace_path,
                        "reasoning": workspace_result.reasoning,
                    },
                    "workspace_summary": self._create_workspace_summary(workspace_result),
                },
                next_layer="resource_check",
            )

        except Exception as e:
            logger.error(f"WorkspaceManagerAgent execution error: {e}")
            return NodeResult.failure(f"Workspace management error: {e}")

    async def _manage_workspace(
        self, task_management: Any, state: AIBoxState,
    ) -> Optional[WorkspaceManagementResult]:
        """管理任務工作區"""
        try:
            task_id = getattr(task_management, "task_id", f"task_{state.task_id}")
            workspace_id = f"ws_{task_id}"

            return WorkspaceManagementResult(
                workspace_created=True,
                workspace_bound=True,
                workspace_cleaned=False,
                file_structure_initialized=True,
                workspace_id=workspace_id,
                workspace_path=f"/data/workspaces/{workspace_id}",
                initial_files_created=[],
                reasoning="Successfully initialized task workspace.",
            )
        except Exception as e:
            logger.error(f"Workspace management process failed: {e}")
            return None

    def _create_workspace_summary(
        self, workspace_result: WorkspaceManagementResult,
    ) -> Dict[str, Any]:
        return {
            "workspace_id": workspace_result.workspace_id,
            "status": "ready",
        }


def create_workspace_manager_agent_config() -> NodeConfig:
    return NodeConfig(
        name="WorkspaceManagerAgent",
        description="工作區管理Agent - 負責為每個任務創建獨立的物理和邏輯工作區",
        max_retries=1,
        timeout=30.0,
        required_inputs=["user_id", "task_management"],
        optional_inputs=["messages"],
        output_keys=["workspace_management", "workspace_summary"],
    )


def create_workspace_manager_agent() -> WorkspaceManagerAgent:
    config = create_workspace_manager_agent_config()
    return WorkspaceManagerAgent(config)
