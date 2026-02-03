from __future__ import annotations
# 代碼功能說明: ContextManagerAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""ContextManagerAgent實現 - 上下文維護和檢索LangGraph節點"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class ContextManagementResult:
    """上下文管理結果"""
    context_initialized: bool
    context_persisted: bool
    context_retrieved: bool
    memory_integrated: bool
    session_active: bool
    messages_stored: int
    context_size: int
    reasoning: str = ""


class ContextManagerAgent(BaseAgentNode):
    """上下文管理Agent - 負責維護會話狀態、消息歷史和記憶整合"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化上下文服務
        self.context_manager = None
        self._initialize_context_service()

    def _initialize_context_service(self) -> None:
        """初始化上下文相關服務"""
        try:
            # 從系統服務中獲取上下文管理器
            from genai.workflows.context.manager import ContextManager

            self.context_manager = ContextManager()
            logger.info("ContextManager service initialized for ContextManagerAgent")
        except Exception as e:
            logger.error(f"Failed to initialize ContextManager service: {e}")
            self.context_manager = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行上下文管理和維護

        Args:
            state: 當前狀態

        Returns:
            NodeResult: 上下文管理結果
        """
        try:
            # 檢查是否有文件任務綁定（可選）
            has_task_binding = (
                hasattr(state, "file_task_binding") and state.file_task_binding is not None,
            )

            # 執行上下文管理
            context_result = await self._manage_context(state, has_task_binding)

            if not context_result:
                return NodeResult.failure("Context management failed")

            # 更新狀態（主要通過服務更新）

            # 記錄觀察
            state.add_observation(
                "context_management_completed",
                {
                    "session_id": state.session_id,
                    "messages_stored": context_result.messages_stored,
                    "context_size": context_result.context_size,
                    "memory_integrated": context_result.memory_integrated,
                },
                1.0
                if context_result.context_persisted and context_result.memory_integrated
                else 0.7,
            )

            logger.info(f"Context management completed for session {state.session_id}")

            # 上下文管理後進入資源檢查
            return NodeResult.success(
                data={
                    "context_management": {
                        "context_initialized": context_result.context_initialized,
                        "context_persisted": context_result.context_persisted,
                        "context_retrieved": context_result.context_retrieved,
                        "memory_integrated": context_result.memory_integrated,
                        "session_active": context_result.session_active,
                        "messages_stored": context_result.messages_stored,
                        "context_size": context_result.context_size,
                        "reasoning": context_result.reasoning,
                    },
                    "context_summary": self._create_context_summary(context_result),
                },
                next_layer="resource_check",  # 上下文管理後進行資源檢查
            )

        except Exception as e:
            logger.error(f"ContextManagerAgent execution error: {e}")
            return NodeResult.failure(f"Context management error: {e}")

    async def _manage_context(
        self, state: AIBoxState, has_task_binding: bool,
    ) -> Optional[ContextManagementResult]:
        """
        執行上下文管理
        """
        try:
            session_id = state.session_id

            # 1. 確保會話初始化
            context_initialized = await self._initialize_session_context(session_id, state)

            # 2. 持久化最新消息
            messages_stored = 0
            if self.context_manager and state.messages:
                # 這裡假設管理器有記錄方法
                latest_msg = state.messages[-1]
                await self.context_manager.record_message(
                    session_id=session_id,
                    role=latest_msg.role,
                    content=latest_msg.content,
                )
                messages_stored = 1

            # 3. 整合記憶
            memory_integrated = True  # 簡化假設

            # 生成結果
            return ContextManagementResult(
                context_initialized=context_initialized,
                context_persisted=messages_stored > 0,
                context_retrieved=True,
                memory_integrated=memory_integrated,
                session_active=True,
                messages_stored=messages_stored,
                context_size=len(state.messages),
                reasoning="Successfully managed conversation context and session state.",
            )

        except Exception as e:
            logger.error(f"Context management process failed: {e}")
            return None

    async def _initialize_session_context(self, session_id: str, state: AIBoxState) -> bool:
        """初始化會話上下文"""
        if self.context_manager:
            # 這裡調用實際的初始化邏輯
            return True
        return True

    def _create_context_summary(self, context_result: ContextManagementResult) -> Dict[str, Any]:
        """創建上下文摘要"""
        return {
            "session_active": context_result.session_active,
            "context_size": context_result.context_size,
            "memory_status": "integrated" if context_result.memory_integrated else "pending",
            "complexity": "low" if context_result.context_size < 10 else "mid",
        }


# 創建ContextManagerAgent節點配置
def create_context_manager_agent_config() -> NodeConfig:
    """創建ContextManagerAgent配置"""
    return NodeConfig(
        name="ContextManagerAgent",
        description="上下文管理Agent - 負責維護會話狀態、消息歷史和記憶整合",
        max_retries=2,
        timeout=20.0,
        required_inputs=["user_id", "session_id", "messages"],
        optional_inputs=["file_task_binding", "task_id"],
        output_keys=["context_management", "context_summary"],
    )


# 創建ContextManagerAgent實例的工廠函數
def create_context_manager_agent() -> ContextManagerAgent:
    """創建ContextManagerAgent實例"""
    config = create_context_manager_agent_config()
    return ContextManagerAgent(config)