from __future__ import annotations
# 代碼功能說明: IntentAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""IntentAgent實現 - 意圖匹配和抽象LangGraph節點"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class IntentAnalysisResult:
    """意圖分析結果"""
    matched_intent: Optional[Any] = None  # IntentDSL 或 None
    intent_name: Optional[str] = None
    domain: Optional[str] = None
    target_agent: Optional[str] = None
    match_score: float = 0.0
    confidence: float = 0.0
    is_fallback: bool = False
    reasoning: str = ""

    def __post_init__(self):
        # 驗證分數範圍
        if not (0.0 <= self.match_score <= 1.0):
            self.match_score = max(0.0, min(1.0, self.match_score))
        if not (0.0 <= self.confidence <= 1.0):
            self.confidence = max(0.0, min(1.0, self.confidence))


class IntentAgent(BaseAgentNode):
    """意圖匹配Agent - 負責意圖識別和DSL匹配"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化IntentMatcher
        self.intent_matcher = None
        self._initialize_intent_matcher()

    def _initialize_intent_matcher(self) -> None:
        """初始化IntentMatcher組件"""
        try:
            from agents.task_analyzer.intent_matcher import IntentMatcher

            self.intent_matcher = IntentMatcher()
            logger.info("IntentMatcher initialized for IntentAgent")
        except Exception as e:
            logger.error(f"Failed to initialize IntentMatcher: {e}")
            self.intent_matcher = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行意圖匹配分析
        """
        try:
            # 檢查語義分析結果是否存在
            if not hasattr(state, "semantic_analysis") or not state.semantic_analysis:
                return NodeResult.failure("No semantic analysis found for intent matching")

            semantic_output = state.semantic_analysis

            # 執行意圖匹配
            intent_result = await self._match_intent(semantic_output, state)

            if not intent_result:
                return NodeResult.failure("Intent matching failed")

            # 更新狀態
            state.intent_analysis = intent_result

            # 記錄觀察
            state.add_observation(
                "intent_analysis_completed",
                {
                    "intent_name": intent_result.intent_name,
                    "domain": intent_result.domain,
                    "match_score": intent_result.match_score,
                    "confidence": intent_result.confidence,
                    "is_fallback": intent_result.is_fallback,
                },
                intent_result.confidence,
            )

            logger.info(
                f"Intent analysis completed for user {state.user_id}: {intent_result.intent_name}",
            )

            # 決定下一步
            next_layer = self._determine_next_layer(intent_result, state)

            return NodeResult.success(
                data={
                    "intent_analysis": {
                        "intent_name": intent_result.intent_name,
                        "domain": intent_result.domain,
                        "target_agent": intent_result.target_agent,
                        "match_score": intent_result.match_score,
                        "confidence": intent_result.confidence,
                        "is_fallback": intent_result.is_fallback,
                        "reasoning": intent_result.reasoning,
                    },
                    "intent_summary": self._create_intent_summary(intent_result),
                },
                next_layer=next_layer,
            )

        except Exception as e:
            logger.error(f"IntentAgent execution error: {e}")
            return NodeResult.failure(f"Intent analysis error: {e}")

    async def _match_intent(
        self, semantic_output: Any, state: AIBoxState,
    ) -> Optional[IntentAnalysisResult]:
        """
        執行意圖匹配
        """
        try:
            if not self.intent_matcher:
                return self._fallback_intent_analysis(semantic_output)

            # 獲取最新的用戶消息作為上下文
            latest_message = self._get_latest_user_message(state)

            # 使用IntentMatcher進行匹配
            matched_intent = self.intent_matcher.match_intent(semantic_output, latest_message)

            # 強制檢查：如果是文件相關且 matcher 返回了通用意圖，則修正它
            topics = getattr(semantic_output, "topics", [])
            if "document" in topics and (
                not matched_intent or matched_intent.name == "general_query",
            ):
                return self._fallback_intent_analysis(semantic_output)

            if matched_intent:
                # 成功匹配到Intent
                return IntentAnalysisResult(
                    matched_intent=matched_intent,
                    intent_name=matched_intent.name,
                    domain=matched_intent.domain,
                    target_agent=matched_intent.target,
                    match_score=0.8,
                    confidence=0.9,
                    is_fallback=False,
                    reasoning=f"Successfully matched intent '{matched_intent.name}'",
                ),
            else:
                return self._fallback_intent_analysis(semantic_output)

        except Exception as e:
            logger.error(f"IntentMatcher analysis failed: {e}")
            return self._fallback_intent_analysis(semantic_output)

    def _fallback_intent_analysis(self, semantic_output: Any) -> IntentAnalysisResult:
        """後備意圖分析邏輯"""
        topics = getattr(semantic_output, "topics", [])
        action_signals = getattr(semantic_output, "action_signals", [])
        modality = getattr(semantic_output, "modality", "conversation")

        intent_name = "general_query"
        domain = "general"
        confidence = 0.4

        if "document" in topics or any(s in action_signals for s in ["analyze", "review"]):
            intent_name = "document_analysis"
            domain = "knowledge_base"
            confidence = 0.8
        elif "create" in action_signals or "generate" in action_signals:
            intent_name = "content_creation"
            domain = "content"
            confidence = 0.7

        return IntentAnalysisResult(
            intent_name=intent_name,
            domain=domain,
            match_score=0.3,
            confidence=confidence,
            is_fallback=True,
            reasoning=f"Fallback analysis: inferred intent '{intent_name}'",
        )

    def _get_latest_user_message(self, state: AIBoxState) -> str:
        for message in reversed(state.messages):
            if message.role == "user":
                return message.content
        return ""
    def _determine_next_layer(self, intent_result: IntentAnalysisResult, state: AIBoxState) -> str:
        if intent_result.intent_name in [
            "system_design",
            "code_analysis",
            "content_creation",
            "document_analysis",
        ]:
            return "capability_matching"
        elif intent_result.intent_name == "general_query":
            return "simple_response",
        else:
            return "capability_matching"

    def _create_intent_summary(self, intent_result: IntentAnalysisResult) -> Dict[str, Any]:
        return {
            "intent": intent_result.intent_name,
            "domain": intent_result.domain,
            "confidence": intent_result.confidence,
            "complexity": "mid",
        }


def create_intent_agent_config() -> NodeConfig:
    return NodeConfig(
        name="IntentAgent",
        description="意圖匹配Agent - 負責意圖識別和DSL匹配",
        max_retries=2,
        timeout=25.0,
        required_inputs=["user_id", "session_id", "semantic_analysis"],
        optional_inputs=["task_id", "messages"],
        output_keys=["intent_analysis", "intent_summary"],
    )


def create_intent_agent() -> IntentAgent:
    config = create_intent_agent_config()
    return IntentAgent(config)