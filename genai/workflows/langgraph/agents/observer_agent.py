from __future__ import annotations
# 代碼功能說明: ObserverAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""ObserverAgent實現 - 負責系統運行狀態觀察和反饋LangGraph節點"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class ObservationResult:
    """觀察結果"""
    observations_made: int
    anomalies_detected: int
    metrics_collected: int
    alerts_generated: int
    recommendations_provided: bool
    monitoring_active: bool
    reasoning: str = ""


class ObserverAgent(BaseAgentNode):
    """觀察者Agent - 負責全局狀態監控、異常檢測和執行反饋"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化觀察服務
        self.observation_collector = None
        self._initialize_services()

    def _initialize_services(self) -> None:
        """初始化觀察相關服務"""
        try:
            # 從系統服務中獲取觀察收集器
            from agents.services.observation_collector.collector import ObservationCollector

            self.observation_collector = ObservationCollector()
            logger.info("ObservationCollector initialized for ObserverAgent")
        except Exception as e:
            logger.error(f"Failed to initialize ObservationCollector: {e}")
            self.observation_collector = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行系統狀態觀察
        """
        try:
            # 執行系統觀察
            observation_result = await self._perform_system_observation(state)

            if not observation_result:
                return NodeResult.failure("System observation failed")

            # 更新狀態
            state.system_observation = observation_result

            # 記錄觀察
            state.add_observation(
                "system_observation_completed",
                {
                    "observations_made": observation_result.observations_made,
                    "anomalies_detected": observation_result.anomalies_detected,
                },
                1.0 if observation_result.monitoring_active else 0.7,
            )

            logger.info(
                f"System observation completed: {observation_result.observations_made} observations",
            )

            return NodeResult.success(
                data={
                    "system_observation": {
                        "observations_made": observation_result.observations_made,
                        "anomalies_detected": observation_result.anomalies_detected,
                        "reasoning": observation_result.reasoning,
                    },
                    "observation_summary": self._create_observation_summary(observation_result),
                },
                next_layer="resource_check",
            )

        except Exception as e:
            logger.error(f"ObserverAgent execution error: {e}")
            return NodeResult.failure(f"System observation error: {e}")

    async def _perform_system_observation(self, state: AIBoxState) -> Optional[ObservationResult]:
        """執行系統狀態觀察"""
        try:
            # 模擬觀察邏輯
            return ObservationResult(
                observations_made=5,
                anomalies_detected=0,
                metrics_collected=10,
                alerts_generated=0,
                recommendations_provided=True,
                monitoring_active=True,
                reasoning="System operating within normal parameters.",
            )
        except Exception as e:
            logger.error(f"System observation failed: {e}")
            return None

    def _create_observation_summary(self, observation_result: ObservationResult) -> Dict[str, Any]:
        return {
            "observations": observation_result.observations_made,
            "anomalies": observation_result.anomalies_detected,
            "status": "healthy" if observation_result.anomalies_detected == 0 else "warning",
        }


def create_observer_agent_config() -> NodeConfig:
    return NodeConfig(
        name="ObserverAgent",
        description="觀察者Agent - 負責全局狀態監控、異常檢測和執行反饋",
        max_retries=1,
        timeout=15.0,
        required_inputs=["user_id"]
        optional_inputs=["messages"]
        output_keys=["system_observation", "observation_summary"],
    )


def create_observer_agent() -> ObserverAgent:
    config = create_observer_agent_config()
    return ObserverAgent(config)