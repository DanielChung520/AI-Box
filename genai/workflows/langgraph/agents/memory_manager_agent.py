from __future__ import annotations
# 代碼功能說明: MemoryManagerAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""MemoryManagerAgent實現 - 負責記憶同步和整合LangGraph節點"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class MemoryIntegrationResult:
    """記憶整合結果"""
    memory_initialized: bool
    memory_synchronized: bool
    memory_optimized: bool
    memory_integrated: bool
    memory_performance: float
    memory_usage: Dict[str, Any] 
    reasoning: str = ""


class MemoryManagerAgent(BaseAgentNode):
    """記憶管理Agent - 負責整合會話記憶、任務歷史和長期知識"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化記憶服務
        self.memory_manager = None
        self._initialize_memory_service()

    def _initialize_memory_service(self) -> None:
        """初始化記憶相關服務"""
        try:
            # 從系統服務中獲取記憶管理器
            from agents.infra.memory.manager import MemoryManager

            self.memory_manager = MemoryManager()
            logger.info("MemoryManager service initialized for MemoryManagerAgent")
        except Exception as e:
            logger.error(f"Failed to initialize MemoryManager service: {e}")
            self.memory_manager = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行記憶同步和整合
        """
        try:
            # 檢查是否有上下文管理結果
            context_result = getattr(state, "context_management", None)

            # 執行記憶整合
            memory_result = await self._integrate_memory_system(state, context_result)

            if not memory_result:
                return NodeResult.failure("Memory integration failed")

            # 記錄觀察
            state.add_observation(
                "memory_integration_completed",
                {
                    "session_id": state.session_id,
                    "memory_integrated": memory_result.memory_integrated,
                    "memory_performance": memory_result.memory_performance,
                },
                1.0 if memory_result.memory_integrated else 0.5,
            )

            logger.info(f"Memory integration completed for session {state.session_id}")

            # 記憶管理後進入資源檢查
            return NodeResult.success(
                data={
                    "memory_integration": {
                        "memory_initialized": memory_result.memory_initialized,
                        "memory_synchronized": memory_result.memory_synchronized,
                        "memory_optimized": memory_result.memory_optimized,
                        "memory_integrated": memory_result.memory_integrated,
                        "memory_performance": memory_result.memory_performance,
                        "memory_usage": memory_result.memory_usage,
                        "reasoning": memory_result.reasoning,
                    },
                    "memory_summary": self._create_memory_summary(memory_result),
                },
                next_layer="resource_check",
            )

        except Exception as e:
            logger.error(f"MemoryManagerAgent execution error: {e}")
            return NodeResult.failure(f"Memory integration error: {e}")

    async def _integrate_memory_system(
        self, state: AIBoxState, context_result: Any,
    ) -> Optional[MemoryIntegrationResult]:
        """整合記憶系統"""
        try:
            # 模擬記憶整合邏輯
            return MemoryIntegrationResult(
                memory_initialized=True,
                memory_synchronized=True,
                memory_optimized=True,
                memory_integrated=True,
                memory_performance=0.9,
                memory_usage={"active_keys": 10, "cache_size_kb": 25},
                reasoning="Successfully integrated all memory components.",
            )
        except Exception as e:
            logger.error(f"Memory integration process failed: {e}")
            return None

    def _create_memory_summary(self, memory_result: MemoryIntegrationResult) -> Dict[str, Any]:
        return {
            "memory_status": "integrated" if memory_result.memory_integrated else "pending",
            "performance": memory_result.memory_performance,
            "complexity": "low",
        }


def create_memory_manager_agent_config() -> NodeConfig:
    return NodeConfig(
        name="MemoryManagerAgent",
        description="記憶管理Agent - 負責整合會話記憶、任務歷史和長期知識",
        max_retries=2,
        timeout=20.0,
        required_inputs=["user_id", "session_id"],
        optional_inputs=["context_management", "messages"],
        output_keys=["memory_integration", "memory_summary"],
    )


def create_memory_manager_agent() -> MemoryManagerAgent:
    config = create_memory_manager_agent_config()
    return MemoryManagerAgent(config)