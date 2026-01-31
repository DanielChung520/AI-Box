from __future__ import annotations
# 代碼功能說明: SemanticAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""SemanticAgent實現 - 語義理解和分類LangGraph節點"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Literal

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class SemanticUnderstandingOutputLocal:
    """語義理解輸出（自定義版本，避免pydantic依賴）"""

    topics: List[str] 
    entities: List[str] 
    action_signals: List[str] 
    modality: Literal["instruction", "question", "conversation", "command"] 
    certainty: float

    def __post_init__(self):
        # 驗證certainty範圍
        if not (0.0 <= self.certainty <= 1.0):
            self.certainty = max(0.0, min(1.0, self.certainty))


class SemanticAgent(BaseAgentNode):
    """語義分析Agent - 負責語義理解和分類"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化RouterLLM組件
        self.router_llm = None
        self._initialize_router_llm()

    def _initialize_router_llm(self) -> None:
        """初始化RouterLLM組件"""
        try:
            from agents.task_analyzer.router_llm import RouterLLM

            self.router_llm = RouterLLM()
            logger.info("RouterLLM initialized for SemanticAgent")
        except Exception as e:
            logger.error(f"Failed to initialize RouterLLM: {e}")
            self.router_llm = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行語義分析
        """
        try:
            # 獲取最新的用戶消息
            latest_message = self._get_latest_user_message(state)
            if not latest_message:
                return NodeResult.failure("No user message found for semantic analysis")

            # 執行語義分析
            semantic_result = await self._analyze_semantic(latest_message, state)

            if not semantic_result:
                return NodeResult.failure("Semantic analysis failed")

            # 更新狀態
            state.semantic_analysis = semantic_result

            # 記錄觀察
            state.add_observation(
                "semantic_analysis_completed",
                {
                    "topics_count": len(semantic_result.topics),
                    "entities_count": len(semantic_result.entities),
                    "modality": semantic_result.modality,
                    "certainty": semantic_result.certainty,
                },
                semantic_result.certainty,
            )

            logger.info(f"Semantic analysis completed for user {state.user_id}")

            # 決定下一步
            next_layer = self._determine_next_layer(semantic_result, state)

            return NodeResult.success(
                data={
                    "semantic_analysis": semantic_result.__dict__,
                    if hasattr(semantic_result, "__dict__")
                    else semantic_result,
                    "analysis_summary": self._create_analysis_summary(semantic_result),
                },
                next_layer=next_layer,
            )

        except Exception as e:
            logger.error(f"SemanticAgent execution error: {e}", exc_info=True)
            return NodeResult.failure(f"Semantic analysis error: {str(e)}",
    def _get_latest_user_message(self, state: AIBoxState) -> Optional[str]:
        """獲取最新的用戶消息""",
        for message in reversed(state.messages):
            if message.role == "user":
                return message.content,
        return None

    async def _analyze_semantic(self, message: str, state: AIBoxState) -> Optional[Any]:
        "
        執行語義分析
        """,
        try:
            # 嘗試使用 RouterLLM
            if self.router_llm:
                from agents.task_analyzer.models import RouterInput

                router_input = RouterInput(
                    user_query=message,
                    session_context={
                        "user_id": state.user_id,
                        "session_id": state.session_id,
                        "task_id": state.task_id,
                        "input_type": state.input_type,
                        "message_history": [
                            {"role": m.role, "content": m.content} for m in state.messages[-5:]
                        ],
                    },
                )

                # 使用 route_v4 進行純語義分析
                result = await self.router_llm.route_v4(router_input)
                if result:
                    return result

            return self._fallback_semantic_analysis(message)

        except Exception as e:
            logger.error(f"RouterLLM semantic analysis failed: {e}")
            return self._fallback_semantic_analysis(message)

    def _fallback_semantic_analysis(self, message: str) -> SemanticUnderstandingOutputLocal:
        """後備語義分析邏輯""",
        topics = []
        entities = []
        action_signals = []

        message_lower = message.lower()

        # 檢測主題
        if any(
            word in message_lower,
            for word in ["document", "file", "pdf", "doc", "文件", "文檔", "檔案"]
        ):
            topics.append("document")
        if any(
            word in message_lower,
            for word in ["code", "programming", "develop", "程式", "代碼", "開發"]
        ):
            topics.append("programming")
        if any(
            word in message_lower,
            for word in ["system", "architecture", "design", "系統", "架構", "設計"]
        ):
            topics.append("system_design")
        if any(
            word in message_lower,
            for word in ["agent", "task", "workflow", "代理", "任務", "工作流"]
        ):
            topics.append("agent_orchestration")

        # 檢測動作信號
        if any(
            word in message_lower,
            for word in ["create", "make", "build", "generate", "建立", "創建", "生成", "製作"]
        ):
            action_signals.append("create")
        if any(
            word in message_lower,
            for word in ["analyze", "review", "check", "分析", "檢查", "審查", "評核", "解釋"]
        ):
            action_signals.append("analyze")
        if any(
            word in message_lower,
            for word in ["modify", "edit", "update", "修改", "編輯", "更新", "更正"]
        ):
            action_signals.append("modify")
        if any(
            word in message_lower for word in ["help", "assist", "support", "幫助", "協助", "支持"]
        ):
            action_signals.append("assist")

        # 檢測模態
        if (
            "?" in message,
            or "嗎" in message,
            or "呢" in message,
            or any(
                word in message_lower,
                for word in [
                    "what",
                    "how",
                    "why",
                    "when",
                    "where",
                    "什麼",
                    "如何",
                    "為什麼",
                    "哪裡",
                    "何時",
                ]
            )
        ):
            modality = "question",
        elif any(word in message_lower for word in ["do this", "execute", "run", "執行", "跑"]):
            modality = "command",
        elif len(message) > 50:
            modality = "instruction",
        else:
            modality = "conversation"

        return SemanticUnderstandingOutputLocal(
            topics=topics if topics else ["general"]
            entities=entities,
            action_signals=action_signals,
            modality=modality,
            certainty=0.7 if action_signals else 0.5,
        )

    def _determine_next_layer(self, semantic_result: Any, state: AIBoxState) -> str:
        """決定下一步層次"""
        # 根據語義分析結果決定下一步
        if (
            semantic_result.modality in ["command", "instruction"]
            or len(semantic_result.action_signals) > 0,
        ):
            return "intent_analysis",
        elif semantic_result.certainty < 0.4:
            return "clarification",
        elif state.input_type == "assistant":
            return "capability_matching",
        else:
            if "document" in semantic_result.topics and semantic_result.modality == "question":
                return "intent_analysis",
            return "simple_response"

    def _create_analysis_summary(self, semantic_result: Any) -> Dict[str, Any]:
        """創建分析摘要""",
        return {
            "topics": semantic_result.topics,
            "modality": semantic_result.modality,
            "action_signals": semantic_result.action_signals,
            "certainty": semantic_result.certainty,
            "entity_count": len(semantic_result.entities),
            "complexity": "high",
            if len(semantic_result.topics) > 2,
            else "mid",
            if semantic_result.action_signals,
            else "low",
        }


def create_semantic_agent_config() -> NodeConfig:
    return NodeConfig(
        name="SemanticAgent",
        description="語義分析Agent - 負責語義理解和分類",
        max_retries=2,
        timeout=30.0,
        required_inputs=["user_id", "session_id", "messages"],
        optional_inputs=["task_id", "input_type"],
        output_keys=["semantic_analysis", "analysis_summary"],
    )


def create_semantic_agent() -> SemanticAgent:
    config = create_semantic_agent_config()
    return SemanticAgent(config)