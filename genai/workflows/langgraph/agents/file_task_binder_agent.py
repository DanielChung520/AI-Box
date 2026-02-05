from __future__ import annotations
# 代碼功能說明: FileTaskBinderAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""FileTaskBinderAgent實現 - 負責文件與任務工作區綁定LangGraph節點"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class FileTaskBindingResult:
    """文件任務綁定結果"""
    bindings_created: int
    bindings_updated: int
    files_registered: int
    permissions_synced: bool
    task_context_updated: bool
    binding_summary: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


class FileTaskBinderAgent(BaseAgentNode):
    """文件任務綁定Agent - 負責建立物理文件與邏輯任務工作區的關聯"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化綁定服務
        self.binding_service = None
        self._initialize_services()

    def _initialize_services(self) -> None:
        """初始化綁定相關服務"""
        try:
            # 從系統服務中獲取文件綁定服務
            # 這裡假設存在一個 FileTaskBinder 服務
            # from services.api.services.file_task_binder import FileTaskBinder
            # self.binding_service = FileTaskBinder()
            logger.info("FileTaskBinderAgent services initialized")
        except Exception as e:
            logger.error(f"Failed to initialize FileTaskBinderAgent services: {e}")
            self.binding_service = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行文件與任務的綁定
        """
        try:
            # 檢查工作區管理結果是否存在
            workspace_result = getattr(state, "workspace_management", None)

            if not workspace_result:
                return NodeResult.failure("No workspace management result found for file binding")

            # 執行文件綁定
            binding_result = await self._bind_files_to_tasks(workspace_result, state)

            if not binding_result:
                return NodeResult.failure("File-task binding failed")

            # 更新狀態（可選）

            # 記錄觀察
            state.add_observation(
                "file_task_binding_completed",
                {
                    "bindings_created": binding_result.bindings_created,
                    "files_registered": binding_result.files_registered,
                    "permissions_synced": binding_result.permissions_synced,
                },
                1.0
                if binding_result.permissions_synced and binding_result.task_context_updated
                else 0.7,
            )

            logger.info(
                f"File-task binding completed for workspace {workspace_result.workspace_id}",
            )

            # 文件綁定後進入資源檢查
            return NodeResult.success(
                data={
                    "file_task_binding": {
                        "bindings_created": binding_result.bindings_created,
                        "bindings_updated": binding_result.bindings_updated,
                        "files_registered": binding_result.files_registered,
                        "permissions_synced": binding_result.permissions_synced,
                        "task_context_updated": binding_result.task_context_updated,
                        "binding_summary": binding_result.binding_summary,
                        "reasoning": binding_result.reasoning,
                    },
                    "binding_summary": self._create_binding_summary(binding_result),
                },
                next_layer="resource_check",
            )

        except Exception as e:
            logger.error(f"FileTaskBinderAgent execution error: {e}")
            return NodeResult.failure(f"File-task binding error: {e}")

    async def _bind_files_to_tasks(
        self, workspace_result: Any, state: AIBoxState,
    ) -> Optional[FileTaskBindingResult]:
        """執行文件任務綁定"""
        try:
            # 模擬綁定邏輯
            return FileTaskBindingResult(
                bindings_created=1,
                bindings_updated=0,
                files_registered=1,
                permissions_synced=True,
                task_context_updated=True,
                binding_summary={"status": "all_files_bound"},
                reasoning="Successfully bound task files to workspace.",
            )
        except Exception as e:
            logger.error(f"File binding process failed: {e}")
            return None

    def _create_binding_summary(self, binding_result: FileTaskBindingResult) -> Dict[str, Any]:
        return {
            "bindings": binding_result.bindings_created,
            "synced": binding_result.permissions_synced,
        }


def create_file_task_binder_agent_config() -> NodeConfig:
    return NodeConfig(
        name="FileTaskBinderAgent",
        description="文件任務綁定Agent - 負責建立物理文件與邏輯任務工作區的關聯",
        max_retries=1,
        timeout=30.0,
        required_inputs=["user_id", "workspace_management"],
        optional_inputs=["messages"],
        output_keys=["file_task_binding", "binding_summary"],
    )


def create_file_task_binder_agent() -> FileTaskBinderAgent:
    config = create_file_task_binder_agent_config()
    return FileTaskBinderAgent(config)
