from __future__ import annotations
# 代碼功能說明: ClarificationAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""ClarificationAgent實現 - 負責處理用戶指令澄清LangGraph節點"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class ClarificationResult:
    """澄清結果"""
    clarification_needed: bool
    clarification_message: str
    unclear_aspects: List[str]
    suggested_questions: List[str]
    context_provided: Dict[str, Any]
    reasoning: str = ""


class ClarificationAgent(BaseAgentNode):
    """澄清Agent - 負責生成澄清請求和引導用戶"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        處理澄清請求
        """
        try:
            # 生成澄清請求
            clarification_result = self._generate_clarification_request(state)

            # 更新狀態
            state.clarification_details = clarification_result

            # 記錄觀察
            state.add_observation(
                "clarification_required",
                {
                    "clarification_needed": clarification_result.clarification_needed,
                    "unclear_aspects_count": len(clarification_result.unclear_aspects),
                    "suggested_questions_count": len(clarification_result.suggested_questions),
                },
                0.3,
            )

            logger.info(f"Clarification requested for user {state.user_id}")

            # 澄清是終止狀態
            return NodeResult.success(
                data={
                    "clarification": {
                        "clarification_needed": clarification_result.clarification_needed,
                        "clarification_message": clarification_result.clarification_message,
                        "unclear_aspects": clarification_result.unclear_aspects,
                        "suggested_questions": clarification_result.suggested_questions,
                        "context_provided": clarification_result.context_provided,
                        "reasoning": clarification_result.reasoning,
                    },
                    "clarification_summary": self._create_clarification_summary(
                        clarification_result,
                    ),
                },
                next_layer=None,
            )

        except Exception as e:
            logger.error(f"ClarificationAgent execution error: {e}")
            return NodeResult.failure(f"Clarification error: {e}")

    def _generate_clarification_request(self, state: AIBoxState) -> ClarificationResult:
        """生成澄清請求"""
        # 簡單的邏輯：如果有語義分析但信心低，則生成請求
        semantic_analysis = getattr(state, "semantic_analysis", None)
        certainty = getattr(semantic_analysis, "certainty", 1.0)

        message = "抱歉，我不確定您的具體需求。能否請您提供更多資訊？"
        unclear_aspects = ["整體意圖"]

        if certainty < 0.4:
            message = "您的請求可能有多種理解方式，請澄清您的具體目標。"
            unclear_aspects.append("任務目標")

        return ClarificationResult(
            clarification_needed=True,
            clarification_message=message,
            unclear_aspects=unclear_aspects,
            suggested_questions=["我想分析這份文件", "我想修改這份文件"],
            context_provided={"certainty": certainty},
            reasoning=f"Based on low certainty score: {certainty}",
        )

    def _create_clarification_summary(
        self, clarification_result: ClarificationResult,
    ) -> Dict[str, Any]:
        return {
            "clarification_needed": clarification_result.clarification_needed,
            "unclear_aspects": clarification_result.unclear_aspects,
            "suggested_questions_count": len(clarification_result.suggested_questions),
        }


def create_clarification_agent_config() -> NodeConfig:
    return NodeConfig(
        name="ClarificationAgent",
        description="澄清Agent - 負責生成澄清請求和引導用戶",
        max_retries=1,
        timeout=15.0,
        required_inputs=["user_id", "session_id"],
        optional_inputs=["semantic_analysis", "messages"],
        output_keys=["clarification", "clarification_summary"],
    )


def create_clarification_agent() -> ClarificationAgent:
    config = create_clarification_agent_config()
    return ClarificationAgent(config)
