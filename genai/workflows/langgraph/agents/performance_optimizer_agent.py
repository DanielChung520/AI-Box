from __future__ import annotations
# 代碼功能說明: PerformanceOptimizerAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""PerformanceOptimizerAgent實現 - 負責系統性能監控和優化建議LangGraph節點"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """優化結果"""
    optimizations_applied: int
    cache_enabled: bool
    performance_improved: bool
    bottlenecks_identified: int
    recommendations_implemented: bool
    monitoring_setup: bool
    reasoning: str = ""


class PerformanceOptimizerAgent(BaseAgentNode):
    """性能優化Agent - 負責監控節點執行性能並應用自動優化策略"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行性能優化
        """
        try:
            # 執行性能優化
            optimization_result = await self._perform_performance_optimization(state)

            if not optimization_result:
                return NodeResult.failure("Performance optimization failed")

            # 更新狀態
            state.performance_optimization = optimization_result

            # 記錄觀察
            state.add_observation(
                "performance_optimization_completed",
                {
                    "optimizations_applied": optimization_result.optimizations_applied,
                    "performance_improved": optimization_result.performance_improved,
                },
                1.0 if optimization_result.performance_improved else 0.7,
            )

            logger.info(
                f"Performance optimization completed: {optimization_result.optimizations_applied} optimizations applied",
            )

            return NodeResult.success(
                data={
                    "performance_optimization": {
                        "optimizations_applied": optimization_result.optimizations_applied,
                        "cache_enabled": optimization_result.cache_enabled,
                        "performance_improved": optimization_result.performance_improved,
                        "reasoning": optimization_result.reasoning,
                    },
                    "optimization_summary": self._create_optimization_summary(optimization_result),
                },
                next_layer="resource_check",
            )

        except Exception as e:
            logger.error(f"PerformanceOptimizerAgent execution error: {e}")
            return NodeResult.failure(f"Performance optimization error: {e}")

    async def _perform_performance_optimization(
        self, state: AIBoxState,
    ) -> Optional[OptimizationResult]:
        """執行性能優化"""
        try:
            # 模擬優化邏輯
            return OptimizationResult(
                optimizations_applied=2,
                cache_enabled=True,
                performance_improved=True,
                bottlenecks_identified=0,
                recommendations_implemented=True,
                monitoring_setup=True,
                reasoning="Applied caching and parallel execution optimizations.",
            )
        except Exception as e:
            logger.error(f"Performance optimization process failed: {e}")
            return None

    def _create_optimization_summary(
        self, optimization_result: OptimizationResult,
    ) -> Dict[str, Any]:
        return {
            "applied": optimization_result.optimizations_applied,
            "status": "optimized",
        }


def create_performance_optimizer_agent_config() -> NodeConfig:
    return NodeConfig(
        name="PerformanceOptimizerAgent",
        description="性能優化Agent - 負責監控節點執行性能並應用自動優化策略",
        max_retries=1,
        timeout=20.0,
        required_inputs=["user_id"],
        optional_inputs=["messages"],
        output_keys=["performance_optimization", "optimization_summary"],
    )


def create_performance_optimizer_agent() -> PerformanceOptimizerAgent:
    config = create_performance_optimizer_agent_config()
    return PerformanceOptimizerAgent(config)
