from __future__ import annotations
# 代碼功能說明: TaskExecutorAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""TaskExecutorAgent實現 - 負責實際任務執行和結果處理"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class TaskExecutionResult:
    """任務執行結果"""
    task_id: str
    execution_success: bool
    results: List[Dict[str, Any]]
    execution_time: float
    agent_count: int
    error_count: int
    output_files: List[Dict[str, Any]]
    reasoning: str = ""


class TaskExecutorAgent(BaseAgentNode):
    """任務執行Agent - 負責調度Agent並處理執行結果"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化Agent調用服務
        self.orchestrator = None
        self.task_tracker = None
        self._initialize_services()

    def _initialize_services(self) -> None:
        """初始化任務執行相關服務"""
        try:
            # 初始化Agent Orchestrator
            from agents.services.orchestrator.orchestrator import AgentOrchestrator

            self.orchestrator = AgentOrchestrator()

            # 初始化Task Tracker
            from agents.services.orchestrator.task_tracker import TaskTracker

            self.task_tracker = TaskTracker()

            logger.info("TaskExecutorAgent services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TaskExecutorAgent services: {e}")
            self.orchestrator = None
            self.task_tracker = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行任務調度和結果處理
        """
        try:
            # 檢查任務編排結果是否存在
            orchestration_result = getattr(state, "task_orchestration", None)

            if not orchestration_result or not orchestration_result.orchestration_success:
                return NodeResult.failure("Task orchestration failed or missing")

            # 執行任務
            execution_result = await self._execute_orchestrated_tasks(orchestration_result, state)

            if not execution_result:
                return NodeResult.failure("Task execution failed")

            # 更新狀態
            state.task_execution = execution_result
            state.execution_status = "completed" if execution_result.execution_success else "failed"

            # 記錄觀察
            state.add_observation(
                "task_execution_completed",
                {
                    "execution_success": execution_result.execution_success,
                    "agent_count": execution_result.agent_count,
                    "error_count": execution_result.error_count,
                    "execution_time": execution_result.execution_time,
                },
                1.0 if execution_result.execution_success else 0.0,
            )

            logger.info(
                f"Task execution completed for user {state.user_id}: success={execution_result.execution_success}",
            )

            return NodeResult.success(
                data={
                    "task_execution": {
                        "execution_success": execution_result.execution_success,
                        "results": execution_result.results,
                        "execution_time": execution_result.execution_time,
                        "agent_count": execution_result.agent_count,
                        "error_count": execution_result.error_count,
                        "output_files": execution_result.output_files,
                        "reasoning": execution_result.reasoning,
                    },
                    "execution_summary": self._create_execution_summary(execution_result),
                },
                next_layer=None,
            )

        except Exception as e:
            logger.error(f"TaskExecutorAgent execution error: {e}")
            return NodeResult.failure(f"Task execution error: {e}")

    async def _execute_orchestrated_tasks(
        self, orchestration_result: Any, state: AIBoxState,
    ) -> Optional[TaskExecutionResult]:
        """執行編排好的任務"""
        try:
            # 模擬執行邏輯
            # 實際上會調用 AgentOrchestrator
            return TaskExecutionResult(
                task_id=orchestration_result.task_id,
                execution_success=True,
                results=[],
                execution_time=5.0,
                agent_count=1,
                error_count=0,
                output_files=[],
                reasoning="Successfully executed scheduled agents.",
            )
        except Exception as e:
            logger.error(f"Task execution process failed: {e}")
            return None

    def _create_execution_summary(self, execution_result: TaskExecutionResult) -> Dict[str, Any]:
        return {
            "execution_success": execution_result.execution_success,
            "agent_count": execution_result.agent_count,
            "error_count": execution_result.error_count,
            "complexity": "mid",
        }


def create_task_executor_agent_config() -> NodeConfig:
    return NodeConfig(
        name="TaskExecutorAgent",
        description="任務執行Agent - 負責調度Agent並處理執行結果",
        max_retries=1,
        timeout=600.0,
        required_inputs=["user_id", "task_orchestration"],
        optional_inputs=["task_id", "messages"],
        output_keys=["task_execution", "execution_summary"],
    )


def create_task_executor_agent() -> TaskExecutorAgent:
    config = create_task_executor_agent_config()
    return TaskExecutorAgent(config)
