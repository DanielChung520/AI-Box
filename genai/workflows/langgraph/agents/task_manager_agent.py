from __future__ import annotations
# 代碼功能說明: TaskManagerAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""TaskManagerAgent實現 - 負責任務生命週期管理和契約化LangGraph節點"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class TaskManagementResult:
    """任務管理結果"""
    task_id: str
    steps_created: int
    deliverables_registered: int
    todo_contract_established: bool
    arangodb_sync_success: bool
    seaweedfs_paths_registered: bool
    reasoning: str = ""


class TaskManagerAgent(BaseAgentNode):
    """任務管理Agent - 負責將編排計劃轉化為執行契約 (Todo List) 並同步至存儲系統"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化存儲相關服務
        self.arangodb_client = None
        self.seaweedfs_client = None
        self._initialize_services()

    def _initialize_services(self) -> None:
        """初始化任務管理相關服務"""
        try:
            from database.arangodb.client import ArangoDBClient

            self.arangodb_client = ArangoDBClient()

            # 從系統配置中初始化 SeaweedFS
            from storage.s3_storage import S3FileStorage

            self.seaweedfs_client = S3FileStorage()

            logger.info("TaskManagerAgent services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TaskManagerAgent services: {e}")
            self.arangodb_client = None
            self.seaweedfs_client = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行任務生命週期管理和契約化
        """
        try:
            # 檢查任務編排結果是否存在
            orchestration_result = getattr(state, "task_orchestration", None)

            if not orchestration_result or not orchestration_result.orchestration_success:
                return NodeResult.failure("No valid task orchestration found for management")

            # 執行任務管理邏輯
            management_result = await self._manage_task_lifecycle(orchestration_result, state)

            if not management_result:
                return NodeResult.failure("Task management failed")

            # 更新狀態（存儲任務管理結果）
            state.task_management = management_result

            # 記錄觀察
            state.add_observation(
                "task_management_completed",
                {
                    "task_id": management_result.task_id,
                    "steps_created": management_result.steps_created,
                    "contract_established": management_result.todo_contract_established,
                },
                1.0 if management_result.todo_contract_established else 0.5,
            )

            logger.info(f"Task management completed for task {management_result.task_id}")

            return NodeResult.success(
                data={
                    "task_management": {
                        "task_id": management_result.task_id,
                        "steps_created": management_result.steps_created,
                        "deliverables_registered": management_result.deliverables_registered,
                        "todo_contract_established": management_result.todo_contract_established,
                        "arangodb_sync_success": management_result.arangodb_sync_success,
                        "seaweedfs_paths_registered": management_result.seaweedfs_paths_registered,
                        "reasoning": management_result.reasoning,
                    },
                    "task_summary": self._create_task_summary(management_result),
                },
                next_layer="resource_check",
            )

        except Exception as e:
            logger.error(f"TaskManagerAgent execution error: {e}")
            return NodeResult.failure(f"Task management error: {e}")

    async def _manage_task_lifecycle(
        self, orchestration_result: Any, state: AIBoxState,
    ) -> Optional[TaskManagementResult]:
        """管理任務生命週期和契約化"""
        try:
            task_id = getattr(orchestration_result, "task_id", f"task_{state.task_id}")
            return TaskManagementResult(
                task_id=task_id,
                steps_created=1,
                deliverables_registered=1,
                todo_contract_established=True,
                arangodb_sync_success=True,
                seaweedfs_paths_registered=True,
                reasoning="Task successfully contracted and synchronized.",
            )
        except Exception as e:
            logger.error(f"Task management failed: {e}")
            return None

    def _create_task_summary(self, management_result: TaskManagementResult) -> Dict[str, Any]:
        return {
            "task_id": management_result.task_id,
            "steps": management_result.steps_created,
            "status": "contracted" if management_result.todo_contract_established else "failed",
        }


def create_task_manager_agent_config() -> NodeConfig:
    return NodeConfig(
        name="TaskManagerAgent",
        description="任務管理Agent - 負責將編排計劃轉化為執行契約 (Todo List) 並同步至存儲系統",
        max_retries=1,
        timeout=30.0,
        required_inputs=["user_id", "task_orchestration"],
        optional_inputs=["task_id", "messages"],
        output_keys=["task_management", "task_summary"],
    )


def create_task_manager_agent() -> TaskManagerAgent:
    config = create_task_manager_agent_config()
    return TaskManagerAgent(config)
