# 代碼功能說明: Knowledge Signal Mapper - 語義觀測結果 → 治理事件判斷
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""Knowledge Signal Mapper - 純規則、可審計、不可漂移的映射層

定位：
- ❗ 它不是語義理解
- ❗ 它不是 intent 分類
- ❗ 它不是搜尋
- ✅ 它是「語義觀測結果 → 治理事件判斷」

職責：
將 L1 Semantic Understanding 的輸出映射為 Knowledge Signal，
這是唯一允許觸發 KA-Agent 的物件。

設計原則：
1. 純規則映射（無 LLM、無向量）
2. 可審計（每一條規則都可 debug）
3. 不可漂移（deterministic）
"""

import logging
from enum import Enum
from typing import List, Optional

from agents.task_analyzer.models import SemanticUnderstandingOutput

logger = logging.getLogger(__name__)


class KnowledgeType(str, Enum):
    """知識類型"""

    ARCHITECTURAL = "architectural"  # 架構性知識
    PROCEDURAL = "procedural"  # 流程性知識
    FACTUAL = "factual"  # 事實性知識
    OPERATIONAL = "operational"  # 操作性知識


class StabilityEstimate(str, Enum):
    """穩定性估計"""

    LOW = "low"
    MID = "mid"
    HIGH = "high"


class KnowledgeSignal:
    """Knowledge Signal Schema - 唯一允許觸發 KA-Agent 的物件

    這不是 LLM 輸出，是 deterministic mapper 產生的。
    """

    is_knowledge_event: bool = False
    knowledge_type: Optional[KnowledgeType] = None
    stability_estimate: Optional[StabilityEstimate] = None
    reuse_potential: float = 0.0  # 0.0-1.0
    skill_candidate: bool = False
    confidence: float = 0.0  # 0.0-1.0
    reason_codes: List[str] = []  # 用於 debug 和 audit

    def __init__(
        self,
        is_knowledge_event: bool = False,
        knowledge_type: Optional[KnowledgeType] = None,
        stability_estimate: Optional[StabilityEstimate] = None,
        reuse_potential: float = 0.0,
        skill_candidate: bool = False,
        confidence: float = 0.0,
        reason_codes: Optional[List[str]] = None,
    ):
        self.is_knowledge_event = is_knowledge_event
        self.knowledge_type = knowledge_type
        self.stability_estimate = stability_estimate
        self.reuse_potential = reuse_potential
        self.skill_candidate = skill_candidate
        self.confidence = confidence
        self.reason_codes = reason_codes or []

    def to_dict(self) -> dict:
        """轉換為字典（用於序列化）"""
        return {
            "is_knowledge_event": self.is_knowledge_event,
            "knowledge_type": self.knowledge_type.value if self.knowledge_type else None,
            "stability_estimate": (
                self.stability_estimate.value if self.stability_estimate else None
            ),
            "reuse_potential": self.reuse_potential,
            "skill_candidate": self.skill_candidate,
            "confidence": self.confidence,
            "reason_codes": self.reason_codes,
        }

    def __repr__(self) -> str:
        return (
            f"KnowledgeSignal("
            f"is_knowledge_event={self.is_knowledge_event}, "
            f"knowledge_type={self.knowledge_type}, "
            f"stability={self.stability_estimate}, "
            f"reuse_potential={self.reuse_potential:.2f}, "
            f"confidence={self.confidence:.2f}, "
            f"reasons={self.reason_codes}"
            f")"
        )


class KnowledgeSignalMapper:
    """Knowledge Signal Mapper - 純規則映射器"""

    def __init__(self):
        """初始化映射器"""
        self.logger = logger

    def map(self, semantic_output: SemanticUnderstandingOutput) -> KnowledgeSignal:
        """
        將語義理解輸出映射為 Knowledge Signal

        Args:
            semantic_output: L1 語義理解輸出

        Returns:
            Knowledge Signal
        """
        signal = KnowledgeSignal()

        # Rule Group A: 是否為 Knowledge Event
        is_knowledge_event, event_score, event_reasons = self._check_knowledge_event(
            semantic_output
        )
        signal.is_knowledge_event = is_knowledge_event
        signal.reason_codes.extend(event_reasons)

        if not is_knowledge_event:
            # 如果不是知識事件，直接返回
            return signal

        # Rule Group B: Knowledge Type 判斷
        knowledge_type, type_reasons = self._determine_knowledge_type(semantic_output)
        signal.knowledge_type = knowledge_type
        signal.reason_codes.extend(type_reasons)

        # Rule Group C: 穩定性估計
        stability, stability_reasons = self._estimate_stability(semantic_output)
        signal.stability_estimate = stability
        signal.reason_codes.extend(stability_reasons)

        # Rule Group D: 重用潛力
        reuse_potential, reuse_reasons = self._calculate_reuse_potential(semantic_output, stability)
        signal.reuse_potential = reuse_potential
        signal.reason_codes.extend(reuse_reasons)

        # Rule Group E: Skill Candidate 判斷
        skill_candidate, skill_reasons = self._check_skill_candidate(signal)
        signal.skill_candidate = skill_candidate
        signal.reason_codes.extend(skill_reasons)

        # 設置 confidence（基於語義理解的 certainty）
        signal.confidence = semantic_output.certainty

        self.logger.info(
            f"Knowledge Signal mapped: {signal}, "
            f"from semantic_output: topics={semantic_output.topics}, "
            f"action_signals={semantic_output.action_signals}"
        )

        return signal

    def _check_knowledge_event(
        self, semantic_output: SemanticUnderstandingOutput
    ) -> tuple[bool, int, List[str]]:
        """
        Rule Group A: 是否為 Knowledge Event

        條件：
        - modality ∈ {instruction, explanation} → +1
        - action_signals 含 define / design / formalize → +1
        - topics 含 system / architecture / agent / policy → +1
        - certainty ≥ 0.8 → +1

        規則：score ≥ 2 → is_knowledge_event = true
        （降低閾值以支持知識查詢場景：query/inform + knowledge_base/documents + high certainty）
        """
        score = 0
        reasons = []

        # 條件 1: modality
        # 對於知識查詢，question 也應該被視為知識事件
        if semantic_output.modality in ["instruction", "explanation", "question"]:
            score += 1
            reasons.append(f"MODALITY_{semantic_output.modality.upper()}")
            self.logger.debug(
                f"Knowledge Signal Mapper: Modality matched - modality={semantic_output.modality}, "
                f"score={score}"
            )
        else:
            self.logger.debug(
                f"Knowledge Signal Mapper: Modality not matched - modality={semantic_output.modality}"
            )

        # 條件 2: action_signals
        knowledge_actions = [
            "define",
            "design",
            "formalize",
            "specify",
            "document",
            "query",  # 查詢知識庫
            "search",  # 搜索知識庫
            "retrieve",  # 檢索知識
            "inform",  # 告知（查詢結果）
        ]
        has_knowledge_action = any(
            action in semantic_output.action_signals for action in knowledge_actions
        )
        if has_knowledge_action:
            score += 1
            matched_actions = [a for a in semantic_output.action_signals if a in knowledge_actions]
            reasons.append(f"KNOWLEDGE_ACTION:{','.join(matched_actions)}")
            self.logger.debug(
                f"Knowledge Signal Mapper: Action signals matched - "
                f"action_signals={semantic_output.action_signals}, matched={matched_actions}, score={score}"
            )
        else:
            self.logger.debug(
                f"Knowledge Signal Mapper: Action signals not matched - "
                f"action_signals={semantic_output.action_signals}, knowledge_actions={knowledge_actions}"
            )

        # 條件 3: topics
        knowledge_topics = [
            "system",
            "architecture",
            "agent",
            "policy",
            "design",
            "specification",
            "framework",
            "process",
            "workflow",
            "knowledge",  # 知識相關
            "knowledge_base",  # 知識庫
            "document",  # 文檔
            "documents",  # 文檔（複數）
            "file",  # 文件
            "data",  # 數據
            "知識",  # 繁體：專業知識、知識庫等
            "知识",  # 簡體
            "專業知識",  # 物料管理員專業知識等
            "专业知识",  # 簡體
        ]
        has_knowledge_topic = any(
            any(kt in topic.lower() for kt in knowledge_topics) for topic in semantic_output.topics
        )
        if has_knowledge_topic:
            score += 1
            matched_topics = [
                t for t in semantic_output.topics if any(kt in t.lower() for kt in knowledge_topics)
            ]
            reasons.append(f"KNOWLEDGE_TOPIC:{','.join(matched_topics)}")
            self.logger.debug(
                f"Knowledge Signal Mapper: Topics matched - topics={semantic_output.topics}, "
                f"matched={matched_topics}, score={score}"
            )
        else:
            self.logger.debug(
                f"Knowledge Signal Mapper: Topics not matched - topics={semantic_output.topics}, "
                f"knowledge_topics={knowledge_topics}"
            )

        # 條件 4: certainty
        if semantic_output.certainty >= 0.8:
            score += 1
            reasons.append(f"HIGH_CERTAINTY:{semantic_output.certainty:.2f}")
            self.logger.debug(
                f"Knowledge Signal Mapper: Certainty matched - certainty={semantic_output.certainty}, "
                f"score={score}"
            )
        else:
            self.logger.debug(
                f"Knowledge Signal Mapper: Certainty not matched - certainty={semantic_output.certainty}"
            )

        # 降低閾值：對於知識查詢（query/inform + knowledge_base/documents），score >= 2 即可
        # 這樣可以正確識別"告訴我你的知識庫有多少文件"這類查詢
        is_knowledge_event = score >= 2

        self.logger.info(
            f"Knowledge Signal Mapper: Rule Group A result - score={score}, "
            f"is_knowledge_event={is_knowledge_event}, reasons={reasons}"
        )

        return is_knowledge_event, score, reasons

    def _determine_knowledge_type(
        self, semantic_output: SemanticUnderstandingOutput
    ) -> tuple[Optional[KnowledgeType], List[str]]:
        """
        Rule Group B: Knowledge Type 判斷

        條件：
        - topics 含 architecture / system / framework → architectural
        - action_signals 含 process / workflow / step → procedural
        - entities 以名詞事實為主 → factual
        - action_signals 含 config / operate / deploy → operational

        只能選一個，衝突時依 priority table
        Priority: architectural > procedural > operational > factual
        """

        # 檢查 architectural
        architectural_keywords = ["architecture", "system", "framework", "design"]
        has_architectural = any(
            keyword in topic.lower()
            for topic in semantic_output.topics
            for keyword in architectural_keywords
        )
        if has_architectural:
            return KnowledgeType.ARCHITECTURAL, ["ARCHITECTURAL_TOPIC"]

        # 檢查 procedural
        procedural_actions = ["process", "workflow", "step", "procedure", "method"]
        has_procedural = any(
            action in semantic_output.action_signals for action in procedural_actions
        )
        if has_procedural:
            return KnowledgeType.PROCEDURAL, ["PROCEDURAL_ACTION"]

        # 檢查 operational
        operational_actions = ["config", "operate", "deploy", "execute", "run"]
        has_operational = any(
            action in semantic_output.action_signals for action in operational_actions
        )
        if has_operational:
            return KnowledgeType.OPERATIONAL, ["OPERATIONAL_ACTION"]

        # 默認：factual（實體以名詞事實為主）
        return KnowledgeType.FACTUAL, ["FACTUAL_DEFAULT"]

    def _estimate_stability(
        self, semantic_output: SemanticUnderstandingOutput
    ) -> tuple[StabilityEstimate, List[str]]:
        """
        Rule Group C: 穩定性估計

        條件：
        - action_signals 含 define / formalize → high
        - action_signals 含 adjust / tweak → mid
        - modality = question → low
        """
        reasons = []

        # 檢查 high stability
        high_stability_actions = ["define", "formalize", "specify", "document"]
        has_high_stability = any(
            action in semantic_output.action_signals for action in high_stability_actions
        )
        if has_high_stability:
            reasons.append("HIGH_STABILITY_ACTION")
            return StabilityEstimate.HIGH, reasons

        # 檢查 mid stability
        mid_stability_actions = ["adjust", "tweak", "modify", "update"]
        has_mid_stability = any(
            action in semantic_output.action_signals for action in mid_stability_actions
        )
        if has_mid_stability:
            reasons.append("MID_STABILITY_ACTION")
            return StabilityEstimate.MID, reasons

        # 檢查 low stability (question)
        if semantic_output.modality == "question":
            reasons.append("QUESTION_MODALITY")
            return StabilityEstimate.LOW, reasons

        # 默認：mid
        reasons.append("DEFAULT_MID")
        return StabilityEstimate.MID, reasons

    def _calculate_reuse_potential(
        self,
        semantic_output: SemanticUnderstandingOutput,
        stability: StabilityEstimate,
    ) -> tuple[float, List[str]]:
        """
        Rule Group D: 重用潛力計算

        數值計算：
        +0.3 if topics 為 system / agent / architecture
        +0.3 if entities 為 generic（非 instance）
        +0.2 if stability = high
        +0.2 if certainty ≥ 0.85

        上限 1.0
        """
        reuse_potential = 0.0
        reasons = []

        # 條件 1: system / agent / architecture topics
        generic_topics = ["system", "agent", "architecture", "framework", "design"]
        has_generic_topic = any(
            any(gt in topic.lower() for gt in generic_topics) for topic in semantic_output.topics
        )
        if has_generic_topic:
            reuse_potential += 0.3
            reasons.append("GENERIC_TOPIC")

        # 條件 2: generic entities（非 instance，這裡簡化判斷）
        # 如果 entities 不包含具體文件名、ID 等，視為 generic
        has_generic_entity = len(semantic_output.entities) > 0 and not any(
            entity.endswith((".md", ".py", ".json", ".txt")) or "/" in entity
            for entity in semantic_output.entities
        )
        if has_generic_entity:
            reuse_potential += 0.3
            reasons.append("GENERIC_ENTITY")

        # 條件 3: high stability
        if stability == StabilityEstimate.HIGH:
            reuse_potential += 0.2
            reasons.append("HIGH_STABILITY")

        # 條件 4: high certainty
        if semantic_output.certainty >= 0.85:
            reuse_potential += 0.2
            reasons.append(f"HIGH_CERTAINTY:{semantic_output.certainty:.2f}")

        # 上限 1.0
        reuse_potential = min(reuse_potential, 1.0)

        return reuse_potential, reasons

    def _check_skill_candidate(self, signal: KnowledgeSignal) -> tuple[bool, List[str]]:
        """
        Rule Group E: Skill Candidate 判斷

        條件：
        - is_knowledge_event = true
        - knowledge_type ∈ {procedural, operational}
        - reuse_potential ≥ 0.7
        """
        reasons = []

        if not signal.is_knowledge_event:
            return False, reasons

        if signal.knowledge_type not in [
            KnowledgeType.PROCEDURAL,
            KnowledgeType.OPERATIONAL,
        ]:
            return False, reasons

        if signal.reuse_potential < 0.7:
            return False, reasons

        reasons.append("SKILL_CANDIDATE")
        return True, reasons


# 全局單例
_knowledge_signal_mapper: Optional[KnowledgeSignalMapper] = None


def get_knowledge_signal_mapper() -> KnowledgeSignalMapper:
    """獲取 Knowledge Signal Mapper 實例（單例模式）"""
    global _knowledge_signal_mapper
    if _knowledge_signal_mapper is None:
        _knowledge_signal_mapper = KnowledgeSignalMapper()
    return _knowledge_signal_mapper


def reset_knowledge_signal_mapper() -> None:
    """重置 Knowledge Signal Mapper 實例（用於測試）"""
    global _knowledge_signal_mapper
    _knowledge_signal_mapper = None
