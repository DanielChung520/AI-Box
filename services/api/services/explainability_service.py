# 代碼功能說明: AI決策可解釋性服務
# 創建日期: 2025-12-06 15:47 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 15:47 (UTC+8)

"""AI決策可解釋性服務 - 為AI決策生成解釋"""

from typing import Any, List, Optional

import structlog

from genai.api.models.ner_models import Entity
from genai.api.models.re_models import Relation
from genai.api.models.rt_models import RelationType

logger = structlog.get_logger(__name__)


class Explanation:
    """AI決策解釋"""

    def __init__(
        self,
        decision_type: str,
        decision: Any,
        confidence: float,
        explanation: str,
        evidence: Optional[List[str]] = None,
        context: Optional[str] = None,
    ):
        """
        初始化解釋

        Args:
            decision_type: 決策類型（ner, re, rt等）
            decision: 決策結果
            confidence: 置信度
            explanation: 解釋文本
            evidence: 證據列表
            context: 上下文
        """
        self.decision_type = decision_type
        self.decision = decision
        self.confidence = confidence
        self.explanation = explanation
        self.evidence = evidence or []
        self.context = context


class ExplainabilityService:
    """AI決策可解釋性服務"""

    def __init__(self):
        """初始化可解釋性服務"""
        self.logger = logger

    def explain_ner_result(self, entities: List[Entity], text: str) -> List[Explanation]:
        """
        為NER結果生成解釋

        Args:
            entities: 識別的實體列表
            text: 原始文本

        Returns:
            解釋列表
        """
        explanations: List[Explanation] = []

        for entity in entities:
            # 提取實體上下文
            start = max(0, entity.start - 20)
            end = min(len(text), entity.end + 20)
            context = text[start:end]

            explanation_text = (
                f"識別到實體「{entity.text}」，類型為「{entity.label}」。"
                f"置信度為 {entity.confidence:.2%}。"
                f"實體出現在文本位置 {entity.start}-{entity.end}。"
            )

            if entity.confidence < 0.7:
                explanation_text += "注意：置信度較低，可能需要人工確認。"

            explanations.append(
                Explanation(
                    decision_type="ner",
                    decision=entity,
                    confidence=entity.confidence,
                    explanation=explanation_text,
                    evidence=[f"文本片段：{context}"],
                    context=context,
                )
            )

        return explanations

    def explain_re_result(self, relations: List[Relation], text: str) -> List[Explanation]:
        """
        為關係抽取結果生成解釋

        Args:
            relations: 抽取的關係列表
            text: 原始文本

        Returns:
            解釋列表
        """
        explanations: List[Explanation] = []

        for relation in relations:
            explanation_text = (
                f"識別到關係：{relation.subject.text} ({relation.subject.label}) "
                f"「{relation.relation}」 {relation.object.text} ({relation.object.label})。"
                f"置信度為 {relation.confidence:.2%}。"
            )

            if relation.context:
                explanation_text += f"關係出現在上下文：{relation.context}"

            explanations.append(
                Explanation(
                    decision_type="re",
                    decision=relation,
                    confidence=relation.confidence,
                    explanation=explanation_text,
                    evidence=[f"上下文：{relation.context}"],
                    context=relation.context,
                )
            )

        return explanations

    def explain_rt_result(
        self, relation_types: List[RelationType], relation_text: str
    ) -> List[Explanation]:
        """
        為關係類型分類結果生成解釋

        Args:
            relation_types: 分類的關係類型列表
            relation_text: 關係文本

        Returns:
            解釋列表
        """
        explanations: List[Explanation] = []

        for rt in relation_types:
            explanation_text = f"關係「{relation_text}」被分類為「{rt.type}」，" f"置信度為 {rt.confidence:.2%}。"

            explanations.append(
                Explanation(
                    decision_type="rt",
                    decision=rt,
                    confidence=rt.confidence,
                    explanation=explanation_text,
                    evidence=[f"關係文本：{relation_text}"],
                    context=relation_text,
                )
            )

        return explanations

    def generate_summary(self, explanations: List[Explanation]) -> str:
        """
        生成解釋摘要

        Args:
            explanations: 解釋列表

        Returns:
            摘要文本
        """
        if not explanations:
            return "沒有可解釋的決策。"

        summary_parts = []
        summary_parts.append(f"共識別到 {len(explanations)} 個決策：")

        for i, exp in enumerate(explanations, 1):
            summary_parts.append(f"{i}. {exp.explanation}")

        return "\n".join(summary_parts)


# 全局服務實例（懶加載）
_explainability_service: Optional[ExplainabilityService] = None


def get_explainability_service() -> ExplainabilityService:
    """獲取可解釋性服務實例（單例模式）"""
    global _explainability_service
    if _explainability_service is None:
        _explainability_service = ExplainabilityService()
    return _explainability_service
