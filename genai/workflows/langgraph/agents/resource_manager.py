from __future__ import annotations
# 代碼功能說明: ResourceManager實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""ResourceManager實現 - 資源檢查和分配LangGraph節點"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class ResourceAllocationResult:
    """資源分配結果"""
    resource_checks_passed: bool
    agent_resources_allocated: List[Dict[str, Any]]
    tool_resources_allocated: List[Dict[str, Any]]
    model_resources_allocated: List[Dict[str, Any]]
    storage_resources_allocated: List[Dict[str, Any]]
    allocation_confidence: float
    resource_constraints: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


class ResourceManager(BaseAgentNode):
    """資源管理Agent - 負責核心組件、工具和模型的資源可用性檢查和預分配"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化資源服務
        self.resource_controller = None
        self.policy_service = None
        self._initialize_services()

    def _initialize_services(self) -> None:
        """初始化資源管理相關服務"""
        try:
            # 從系統服務中獲取資源控制器
            from agents.services.resource_controller import get_resource_controller

            self.resource_controller = get_resource_controller()

            # 初始化策略服務（用於配額檢查）
            from agents.task_analyzer.policy_service import get_policy_service

            self.policy_service = get_policy_service()

            logger.info("ResourceManager services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ResourceManager services: {e}")
            self.resource_controller = None
            self.policy_service = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行資源檢查和分配
        """
        try:
            # 檢查能力分析結果是否存在
            capability_result = getattr(state, "capability_analysis", None)

            # 執行資源檢查和分配
            allocation_result = await self._allocate_resources(capability_result, state)

            if not allocation_result:
                return NodeResult.failure("Resource allocation failed")

            # 更新狀態
            state.resource_allocation = allocation_result

            # 記錄觀察
            state.add_observation(
                "resource_allocation_completed",
                {
                    "checks_passed": allocation_result.resource_checks_passed,
                    "agent_resources_count": len(allocation_result.agent_resources_allocated),
                    "tool_resources_count": len(allocation_result.tool_resources_allocated),
                    "model_resources_count": len(allocation_result.model_resources_allocated),
                },
                allocation_result.allocation_confidence,
            )

            logger.info(
                f"Resource allocation completed for user {state.user_id}: checks_passed={allocation_result.resource_checks_passed}",
            )

            # 決定下一步
            next_layer = self._determine_next_layer(allocation_result, state)

            return NodeResult.success(
                data={
                    "resource_allocation": {
                        "agent_resources": allocation_result.agent_resources_allocated,
                        "tool_resources": allocation_result.tool_resources_allocated,
                        "model_resources": allocation_result.model_resources_allocated,
                        "storage_resources": allocation_result.storage_resources_allocated,
                        "resource_checks_passed": allocation_result.resource_checks_passed,
                        "allocation_confidence": allocation_result.allocation_confidence,
                        "resource_constraints": allocation_result.resource_constraints,
                        "reasoning": allocation_result.reasoning,
                    },
                    "resource_summary": self._create_resource_summary(allocation_result),
                },
                next_layer=next_layer,
            )

        except Exception as e:
            logger.error(f"ResourceManager execution error: {e}")
            return NodeResult.failure(f"Resource allocation error: {e}")

    async def _allocate_resources(
        self, capability_result: Any, state: AIBoxState,
    ) -> Optional[ResourceAllocationResult]:
        """分配資源"""
        try:
            # 模擬資源分配邏輯
            agent_resources = []
            if capability_result and capability_result.matched_agents:
                for agent in capability_result.matched_agents:
                    agent_resources.append({**agent, "status": "allocated"})

            return ResourceAllocationResult(
                resource_checks_passed=True,
                agent_resources_allocated=agent_resources,
                tool_resources_allocated=[],
                model_resources_allocated=[{"model_id": "default", "status": "allocated"}],
                storage_resources_allocated=[],
                allocation_confidence=1.0,
                reasoning="Successfully allocated all required resources.",
            )
        except Exception as e:
            logger.error(f"Resource allocation process failed: {e}")
            return None

    def _determine_next_layer(
        self, allocation_result: ResourceAllocationResult, state: AIBoxState,
    ) -> str:
        """決定下一步層次"""
        if not allocation_result.resource_checks_passed:
            return "clarification"

        return "policy_verification"

    def _create_resource_summary(
        self, allocation_result: ResourceAllocationResult,
    ) -> Dict[str, Any]:
        return {
            "checks_passed": allocation_result.resource_checks_passed,
            "agents_allocated": len(allocation_result.agent_resources_allocated),
            "confidence": allocation_result.allocation_confidence,
            "complexity": "low",
        }


def create_resource_manager_config() -> NodeConfig:
    return NodeConfig(
        name="ResourceManager",
        description="資源管理Agent - 負責核心組件、工具和模型的資源可用性檢查和預分配",
        max_retries=1,
        timeout=30.0,
        required_inputs=["user_id"],
        optional_inputs=["capability_analysis", "messages"],
        output_keys=["resource_allocation", "resource_summary"],
    )


def create_resource_manager() -> ResourceManager:
    config = create_resource_manager_config()
    return ResourceManager(config)
