# 代碼功能說明: Intent DSL 匹配器 - 基於 L1 語義理解輸出匹配 Intent
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Intent DSL 匹配器

基於 L1 層級的語義理解輸出（topics, entities, action_signals）匹配 Intent DSL。
"""

from __future__ import annotations

import logging
from typing import List, Optional

from agents.task_analyzer.intent_registry import IntentRegistry, get_intent_registry
from agents.task_analyzer.models import IntentDSL, SemanticUnderstandingOutput

logger = logging.getLogger(__name__)

# Fallback Intent（當無法匹配任何 Intent 時使用）
FALLBACK_INTENT_NAME = "general_query"


class IntentMatcher:
    """Intent DSL 匹配器

    基於 L1 語義理解輸出匹配 Intent DSL。
    """

    def __init__(self, intent_registry: Optional[IntentRegistry] = None):
        """
        初始化 Intent Matcher

        Args:
            intent_registry: Intent Registry 實例，如果為 None 則使用單例
        """
        self.intent_registry = intent_registry or get_intent_registry()
        self._logger = logger

    def match_intent(
        self, semantic_output: SemanticUnderstandingOutput, user_query: str = ""
    ) -> Optional[IntentDSL]:
        """
        基於 L1 語義理解輸出匹配 Intent（v4.0 更新：使用 SemanticUnderstandingOutput）

        Args:
            semantic_output: L1 層級的語義理解輸出（SemanticUnderstandingOutput）
            user_query: 用戶查詢（可選，用於額外上下文）

        Returns:
            匹配的 Intent DSL，如果無法匹配則返回 None
        """
        # 提取語義信息
        topics = semantic_output.topics or []
        entities = semantic_output.entities or []
        action_signals = semantic_output.action_signals or []

        # 獲取所有啟用的 Intent
        intents = self.intent_registry.list_intents(is_active=True, default_version=True)

        if not intents:
            self._logger.warning("No active intents found in registry")
            return None

        # 計算匹配分數
        best_match: Optional[IntentDSL] = None
        best_score = 0.0

        for intent in intents:
            score = self._calculate_match_score(
                intent, topics, entities, action_signals, user_query
            )
            if score > best_score:
                best_score = score
                best_match = intent

        # 如果最佳匹配分數低於閾值，返回 None（將使用 Fallback Intent）
        MATCH_THRESHOLD = 0.3
        if best_score < MATCH_THRESHOLD:
            self._logger.debug(
                f"Best match score {best_score:.2f} below threshold {MATCH_THRESHOLD}, "
                "will use fallback intent"
            )
            return None

        self._logger.info(
            f"Matched intent: {best_match.name} (score: {best_score:.2f})"
        )
        return best_match

    def _calculate_match_score(
        self,
        intent: IntentDSL,
        topics: List[str],
        entities: List[str],
        action_signals: List[str],
        user_query: str,
    ) -> float:
        """
        計算 Intent 匹配分數

        Args:
            intent: Intent DSL 定義
            topics: 主題列表
            entities: 實體列表
            action_signals: 動作信號列表
            user_query: 用戶查詢

        Returns:
            匹配分數（0.0-1.0）
        """
        score = 0.0

        # 1. 基於 Intent 描述匹配（關鍵詞匹配）
        intent_text = f"{intent.name} {intent.description or ''} {intent.domain} {intent.target or ''}".lower()
        query_text = f"{' '.join(topics)} {' '.join(entities)} {' '.join(action_signals)} {user_query}".lower()

        # 計算關鍵詞重疊
        intent_words = set(intent_text.split())
        query_words = set(query_text.split())
        if intent_words:
            word_overlap = len(intent_words & query_words) / len(intent_words)
            score += word_overlap * 0.4  # 權重 40%

        # 2. 基於 Action Signals 匹配
        if action_signals:
            # 將 action_signals 與 intent name/description 進行匹配
            action_text = " ".join(action_signals).lower()
            intent_keywords = [
                "create",
                "modify",
                "edit",
                "delete",
                "design",
                "analyze",
                "generate",
                "review",
                "refactor",
            ]
            action_keywords = [kw for kw in intent_keywords if kw in action_text]
            intent_keywords_in_name = [
                kw for kw in intent_keywords if kw in intent.name.lower()
            ]
            if action_keywords and intent_keywords_in_name:
                action_match = len(set(action_keywords) & set(intent_keywords_in_name)) / max(
                    len(action_keywords), 1
                )
                score += action_match * 0.3  # 權重 30%

        # 3. 基於 Entities 匹配（匹配 target agent）
        if entities and intent.target:
            entity_text = " ".join(entities).lower()
            if intent.target.lower() in entity_text:
                score += 0.2  # 權重 20%

        # 4. 基於 Topics 匹配（匹配 domain）
        if topics:
            topic_text = " ".join(topics).lower()
            domain_keywords = {
                "system_architecture": ["system", "architecture", "design", "document"],
                "code_generation": ["code", "programming", "development"],
                "data_analysis": ["data", "analysis", "analytics"],
            }
            domain_keywords_list = domain_keywords.get(intent.domain, [])
            topic_match = sum(1 for kw in domain_keywords_list if kw in topic_text)
            if domain_keywords_list:
                score += (topic_match / len(domain_keywords_list)) * 0.1  # 權重 10%

        return min(score, 1.0)  # 確保分數不超過 1.0

    def get_fallback_intent(self) -> Optional[IntentDSL]:
        """
        獲取 Fallback Intent（v4.0 完善版）

        Returns:
            Fallback Intent DSL，如果不存在則返回 None
        """
        try:
            # 首先嘗試獲取指定的 Fallback Intent
            fallback = self.intent_registry.get_intent_by_name(FALLBACK_INTENT_NAME)
            if fallback and fallback.is_active:
                self._logger.debug(f"Using fallback intent: {FALLBACK_INTENT_NAME}")
                return fallback
        except Exception as e:
            self._logger.warning(f"Failed to get fallback intent '{FALLBACK_INTENT_NAME}': {e}")

        # 如果指定的 Fallback Intent 不存在，嘗試創建一個默認的 Fallback Intent
        try:
            from agents.task_analyzer.models import IntentCreate

            # 創建默認的 general_query intent
            fallback_create = IntentCreate(
                name=FALLBACK_INTENT_NAME,
                domain="general",
                target=None,
                output_format=["General Response"],
                depth="Basic",
                version="1.0.0",
                default_version=True,
                description="通用查詢 Intent，用於無法匹配特定 Intent 的情況",
                metadata={"is_fallback": True},
            )
            fallback = self.intent_registry.create_intent(fallback_create)
            self._logger.info(f"Created default fallback intent: {FALLBACK_INTENT_NAME}")
            return fallback
        except ValueError:
            # Intent 已存在，但可能不是默認版本，嘗試獲取
            try:
                fallback = self.intent_registry.get_intent(FALLBACK_INTENT_NAME, "1.0.0")
                if fallback and fallback.is_active:
                    return fallback
            except Exception as e:
                self._logger.warning(f"Failed to get fallback intent after creation attempt: {e}")

        # 最後嘗試：獲取第一個啟用的 Intent 作為 Fallback
        intents = self.intent_registry.list_intents(is_active=True, default_version=True)
        if intents:
            self._logger.warning(
                f"Fallback intent '{FALLBACK_INTENT_NAME}' not available, using first active intent: {intents[0].name}"
            )
            return intents[0]

        self._logger.error("No fallback intent available and no active intents found")
        return None
