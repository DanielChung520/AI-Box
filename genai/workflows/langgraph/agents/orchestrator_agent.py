from __future__ import annotations
# 代碼功能說明: OrchestratorAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""OrchestratorAgent實現 - 任務編排和調度LangGraph節點"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class TaskOrchestrationResult:
    """任務編排結果"""
    orchestration_success: bool
    task_dag_created: bool
    execution_plan_generated: bool
    agent_scheduled: bool
    task_id: Optional[str] = None
    execution_status: str = "pending" 
    scheduled_agents: List[Dict[str, Any]] = None
    task_dependencies: List[Dict[str, Any]] = None
    estimated_duration: Optional[float] = None
    resource_utilization: Dict[str, Any] = None
    reasoning: str = "
    def __post_init__(self):
        if self.scheduled_agents is None:
            self.scheduled_agents = []
        if self.task_dependencies is None:
            self.task_dependencies = []
        if self.resource_utilization is None:
            self.resource_utilization = {}


class OrchestratorAgent(BaseAgentNode):
    """任務編排Agent - 負責任務調度和執行計劃生成"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化編排服務
        self.orchestrator = None
        self.task_tracker = None
        self._initialize_services()

    def _initialize_services(self) -> None:
        """初始化編排相關服務"""
        try:
            # 初始化Agent Orchestrator
            from agents.services.orchestrator.orchestrator import AgentOrchestrator

            self.orchestrator = AgentOrchestrator()

            # 初始化Task Tracker
            from agents.services.orchestrator.task_tracker import TaskTracker

            self.task_tracker = TaskTracker()

            logger.info("OrchestratorAgent services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OrchestratorAgent services: {e}")
            self.orchestrator = None
            self.task_tracker = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行任務編排和調度
        """
        try:
            # 檢查策略驗證結果是否存在
            policy_result = getattr(state, "policy_verification", None)

            # 執行任務編排
            orchestration_result = await self._orchestrate_tasks(policy_result, state)

            if not orchestration_result:
                return NodeResult.failure("Task orchestration failed")

            # 更新狀態
            state.task_orchestration = orchestration_result

            # 記錄觀察
            state.add_observation(
                "task_orchestration_completed",
                {
                    "orchestration_success": orchestration_result.orchestration_success,
                    "task_dag_created": orchestration_result.task_dag_created,
                    "agent_scheduled": orchestration_result.agent_scheduled,
                    "task_id": orchestration_result.task_id,
                    "execution_status": orchestration_result.execution_status,
                    "scheduled_agents_count": len(orchestration_result.scheduled_agents),
                },
                1.0 if orchestration_result.orchestration_success else 0.0,
            )

            logger.info(
                f"Task orchestration completed for user {state.user_id}: success={orchestration_result.orchestration_success}",
            )

            # 決定下一步
            next_layer = self._determine_next_layer(orchestration_result, state)

            return NodeResult.success(
                data={
                    "task_orchestration": {
                        "orchestration_success": orchestration_result.orchestration_success,
                        "task_dag_created": orchestration_result.task_dag_created,
                        "execution_plan_generated": orchestration_result.execution_plan_generated,
                        "agent_scheduled": orchestration_result.agent_scheduled,
                        "task_id": orchestration_result.task_id,
                        "execution_status": orchestration_result.execution_status,
                        "scheduled_agents": orchestration_result.scheduled_agents,
                        "task_dependencies": orchestration_result.task_dependencies,
                        "estimated_duration": orchestration_result.estimated_duration,
                        "resource_utilization": orchestration_result.resource_utilization,
                        "reasoning": orchestration_result.reasoning,
                    },
                    "orchestration_summary": self._create_orchestration_summary(
                        orchestration_result,
                    ),
                },
                next_layer=next_layer,
            )

        except Exception as e:
            logger.error(f"OrchestratorAgent execution error: {e}")
            return NodeResult.failure(f"Task orchestration error: {e}")

    async def _orchestrate_tasks(
        self, policy_result: Any, state: AIBoxState,
    ) -> Optional[TaskOrchestrationResult]:
        """
        執行任務編排
        """
        try:
            task_id = f"task_{state.task_id or 'default'}"

            # 識別意圖
            intent_analysis = getattr(state, "intent_analysis", None)
            intent_name = getattr(intent_analysis, "intent_name", "general_query")

            # 模擬編排邏輯
            scheduled_agents = []
            if intent_name == "document_analysis":
                scheduled_agents.append({"agent_id": "rag-agent", "priority": 1})
            elif intent_name == "content_creation":
                scheduled_agents.append({"agent_id": "md-editor", "priority": 1})

            success = len(scheduled_agents) > 0

            return TaskOrchestrationResult(
                orchestration_success=success,
                task_dag_created=True,
                execution_plan_generated=True,
                agent_scheduled=success,
                task_id=task_id,
                execution_status="scheduled" if success else "failed",
                scheduled_agents=scheduled_agents,
                estimated_duration=60.0,
                reasoning=f"Orchestrated {len(scheduled_agents)} agents for {intent_name}.",
            )

        except Exception as e:
            logger.error(f"Task orchestration failed: {e}")
            return None

    def _determine_next_layer(
        self, orchestration_result: TaskOrchestrationResult, state: AIBoxState,
    ) -> str:
        """決定下一步層次"""
        if not orchestration_result.orchestration_success:
            return "clarification"

        return "task_execution"

    def _create_orchestration_summary(
        self, orchestration_result: TaskOrchestrationResult,
    ) -> Dict[str, Any]:
        return {
            "orchestration_success": orchestration_result.orchestration_success,
            "scheduled_agents_count": len(orchestration_result.scheduled_agents),
            "estimated_duration": orchestration_result.estimated_duration,
            "complexity": "mid",
        }


def create_orchestrator_agent_config() -> NodeConfig:
    return NodeConfig(
        name="OrchestratorAgent",
        description="任務編排Agent - 負責任務調度和執行計劃生成",
        max_retries=2,
        timeout=25.0,
        required_inputs=["user_id", "session_id"],
        optional_inputs=["task_id", "policy_verification", "messages"],
        output_keys=["task_orchestration", "orchestration_summary"],
    )


def create_orchestrator_agent() -> OrchestratorAgent:
    config = create_orchestrator_agent_config()
    return OrchestratorAgent(config)