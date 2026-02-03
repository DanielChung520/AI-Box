from __future__ import annotations
# 代碼功能說明: LongTermMemoryAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""LongTermMemoryAgent實現 - 負責長期記憶優化LangGraph節點"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class LongTermMemoryOptimizationResult:
    """長期記憶優化結果"""
    memory_consolidated: bool
    memory_pruned: bool
    memory_archived: bool
    memory_indexed: bool
    memory_health_score: float
    optimization_metrics: Dict[str, Any] = field(default_factory=dict) 
    reasoning: str = ""


class LongTermMemoryAgent(BaseAgentNode):
    """長期記憶Agent - 負責長期記憶的維護、修剪和索引優化"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化記憶優化服務
        self.memory_manager = None
        self._initialize_memory_service()

    def _initialize_memory_service(self) -> None:
        """初始化記憶相關服務"""
        try:
            # 從系統服務中獲取記憶管理器
            from agents.infra.memory.manager import MemoryManager

            self.memory_manager = MemoryManager()
            logger.info("MemoryManager service initialized for LongTermMemoryAgent")
        except Exception as e:
            logger.error(f"Failed to initialize MemoryManager service: {e}")
            self.memory_manager = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行長期記憶優化
        """
        try:
            # 檢查是否有記憶管理結果
            memory_result = getattr(state, "memory_management", None)

            # 執行記憶優化
            optimization_result = await self._optimize_long_term_memory(state, memory_result)

            if not optimization_result:
                return NodeResult.failure("Long-term memory optimization failed")

            # 記錄觀察
            state.add_observation(
                "long_term_memory_optimization_completed",
                {
                    "memory_consolidated": optimization_result.memory_consolidated,
                    "memory_pruned": optimization_result.memory_pruned,
                    "memory_archived": optimization_result.memory_archived,
                    "memory_indexed": optimization_result.memory_indexed,
                    "memory_health_score": optimization_result.memory_health_score,
                },
                optimization_result.memory_health_score,
            )

            logger.info(
                f"Long-term memory optimization completed with health score: {optimization_result.memory_health_score}",
            )

            # 長期記憶優化後進入資源檢查
            return NodeResult.success(
                data={
                    "long_term_memory_optimization": {
                        "memory_consolidated": optimization_result.memory_consolidated,
                        "memory_pruned": optimization_result.memory_pruned,
                        "memory_archived": optimization_result.memory_archived,
                        "memory_indexed": optimization_result.memory_indexed,
                        "memory_health_score": optimization_result.memory_health_score,
                        "optimization_metrics": optimization_result.optimization_metrics,
                        "reasoning": optimization_result.reasoning,
                    },
                    "memory_health_summary": self._create_memory_health_summary(
                        optimization_result,
                    ),
                },
                next_layer="resource_check",
            )

        except Exception as e:
            logger.error(f"LongTermMemoryAgent execution error: {e}")
            return NodeResult.failure(f"Long-term memory optimization error: {e}")

    async def _optimize_long_term_memory(
        self, state: AIBoxState, memory_result: Any,
    ) -> Optional[LongTermMemoryOptimizationResult]:
        """優化長期記憶系統"""
        try:
            # 模擬記憶優化邏輯
            return LongTermMemoryOptimizationResult(
                memory_consolidated=True,
                memory_pruned=False,
                memory_archived=True,
                memory_indexed=True,
                memory_health_score=0.95,
                optimization_metrics={"new_entries": 5, "total_entries": 150},
                reasoning="Long-term memory successfully indexed and archived.",
            )
        except Exception as e:
            logger.error(f"Memory optimization process failed: {e}")
            return None

    def _create_memory_health_summary(
        self, optimization_result: LongTermMemoryOptimizationResult,
    ) -> Dict[str, Any]:
        return {
            "health_score": optimization_result.memory_health_score,
            "consolidated": optimization_result.memory_consolidated,
            "indexed": optimization_result.memory_indexed,
            "complexity": "low",
        }


def create_long_term_memory_agent_config() -> NodeConfig:
    return NodeConfig(
        name="LongTermMemoryAgent",
        description="長期記憶Agent - 負責長期記憶的維護、修剪和索引優化",
        max_retries=1,
        timeout=30.0,
        required_inputs=["user_id"],
        optional_inputs=["memory_management", "messages"],
        output_keys=["long_term_memory_optimization", "memory_health_summary"],
    )


def create_long_term_memory_agent() -> LongTermMemoryAgent:
    config = create_long_term_memory_agent_config()
    return LongTermMemoryAgent(config)