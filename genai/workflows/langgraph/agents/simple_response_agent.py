from __future__ import annotations
# 代碼功能說明: SimpleResponseAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""SimpleResponseAgent實現 - 負責處理簡單對話回應"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class SimpleResponseResult:
    """簡單回應結果"""
    response_generated: bool
    response_type: str
    response_content: str
    confidence: float
    follow_up_suggestions: List[str]
    reasoning: str = ""


class SimpleResponseAgent(BaseAgentNode):
    """簡單回應Agent - 處理簡單對話和問候"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        生成簡單回應
        """
        try:
            # 生成簡單回應
            response_result = await self._generate_simple_response(state)

            # 更新狀態
            state.simple_response = response_result
            state.final_response = response_result.response_content
            state.execution_status = "completed"

            # 記錄觀察
            state.add_observation(
                "simple_response_generated",
                {
                    "response_generated": response_result.response_generated,
                    "response_type": response_result.response_type,
                    "confidence": response_result.confidence,
                    "follow_up_suggestions_count": len(response_result.follow_up_suggestions),
                },
                response_result.confidence,
            )

            logger.info(
                f"Simple response generated for user {state.user_id}: {response_result.response_type}",
            )

            # 簡單回應是終止狀態
            return NodeResult.success(
                data={
                    "simple_response": {
                        "response_generated": response_result.response_generated,
                        "response_type": response_result.response_type,
                        "response_content": response_result.response_content,
                        "confidence": response_result.confidence,
                        "follow_up_suggestions": response_result.follow_up_suggestions,
                        "reasoning": response_result.reasoning,
                    },
                    "response_summary": self._create_response_summary(response_result),
                },
                next_layer=None,
            )

        except Exception as e:
            logger.error(f"SimpleResponseAgent execution error: {e}")
            return NodeResult.failure(f"Simple response error: {e}")

    async def _generate_simple_response(self, state: AIBoxState) -> SimpleResponseResult:
        """生成簡單回應"""
        try:
            _user_message = self._get_latest_user_message(state)
            semantic_result = getattr(state, "semantic_analysis", None)
            modality = getattr(semantic_result, "modality", "conversation")

            response_content = (
                "我明白了您的意思。AI-Box致力於為您提供最好的AI助手體驗。您想要深入了解哪個方面呢？",
            )
            response_type = "conversation"
            confidence = 0.8
            follow_up_suggestions = ["系統功能介紹", "使用指南"]

            if modality == "question":
                response_type = "question_response"
                response_content = (
                    "我理解您的問題。為了給您更準確的答案，能否請您提供更多詳細資訊？",
                )

            return SimpleResponseResult(
                response_generated=True,
                response_type=response_type,
                response_content=response_content,
                confidence=confidence,
                follow_up_suggestions=follow_up_suggestions,
                reasoning=f"Based on {modality} modality",
            )

        except Exception as e:
            logger.error(f"Failed to generate simple response: {e}")
            return SimpleResponseResult(
                response_generated=True,
                response_type="error_fallback",
                response_content="抱歉，我現在遇到了一些技術問題。",
                confidence=0.5,
                follow_up_suggestions=[],
                reasoning=str(e)
            )

    def _get_latest_user_message(self, state: AIBoxState) -> str:
        for message in reversed(state.messages):
            if message.role == "user":
                return message.content
        return ""
    def _create_response_summary(self, response_result: SimpleResponseResult) -> Dict[str, Any]:
        return {
            "response_generated": response_result.response_generated,
            "response_type": response_result.response_type,
            "confidence": response_result.confidence,
        }


def create_simple_response_agent_config() -> NodeConfig:
    return NodeConfig(
        name="SimpleResponseAgent",
        description="簡單回應Agent - 處理簡單對話和問候",
        max_retries=1,
        timeout=15.0,
        required_inputs=["user_id", "session_id"],
        optional_inputs=["semantic_analysis", "messages"],
        output_keys=["simple_response", "response_summary"],
    )


def create_simple_response_agent() -> SimpleResponseAgent:
    config = create_simple_response_agent_config()
    return SimpleResponseAgent(config)
