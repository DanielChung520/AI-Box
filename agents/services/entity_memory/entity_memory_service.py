# 代碼功能說明: Entity Memory 統一服務
# 創建日期: 2026-02-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-04

"""Entity Memory 統一服務 - 指代消解與實體記憶管理"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    EntityMemory,
    SessionContext,
    EntityType,
    CoreferenceResolution,
    CoreferenceResult,
)
from .entity_storage import EntityStorage, get_entity_storage
from .entity_extractor import EntityExtractor, get_entity_extractor

logger = logging.getLogger(__name__)

# 全局服務實例
_entity_memory_service: Optional[EntityMemoryService] = None


class EntityMemoryService:
    """Entity Memory 統一服務"""

    def __init__(
        self,
        storage: Optional[EntityStorage] = None,
        extractor: Optional[EntityExtractor] = None,
    ):
        self.storage = storage or get_entity_storage()
        self.extractor = extractor or get_entity_extractor()

        # 代詞到實體類型的映射
        self._coreference_patterns = {
            # 近程指代
            r"^這個$": {"type": "proximal", "weight": 1.0},
            r"^這個[的]?$": {"type": "proximal", "weight": 1.0},
            r"^它$": {"type": "proximal", "weight": 0.9},
            r"^它[的]?$": {"type": "proximal", "weight": 0.9},
            # 遠程指代
            r"^那個$": {"type": "distal", "weight": 0.8},
            r"^那個[的]?$": {"type": "distal", "weight": 0.8},
            r"^那$": {"type": "distal", "weight": 0.7},
            r"^它們?$": {"type": "plural", "weight": 0.8},
            # 人稱代詞
            r"^他$": {"type": "person", "weight": 0.8},
            r"^她$": {"type": "person", "weight": 0.8},
        }

    # ==================== 指代消解 ====================

    async def resolve_coreference(
        self,
        query: str,
        session_id: str,
        user_id: str,
    ) -> CoreferenceResult:
        """
        指代消解主接口

        Args:
            query: 用戶原始查詢
            session_id: 會話 ID
            user_id: 用戶 ID

        Returns:
            指代消解結果
        """
        try:
            # Step 1: 檢測查詢中的指代詞
            coreference_words = self._detect_coreference_words(query)

            if not coreference_words:
                # 沒有指代詞，直接返回原始查詢
                return CoreferenceResult(
                    original_query=query,
                    resolved_query=query,
                    resolutions=[],
                    confidence=1.0,
                    entities_found=[],
                )

            # Step 2: 獲取上下文中的實體
            session_entities = await self.storage.get_session_entities(session_id, limit=10)
            user_entities = await self.storage.list_user_entities(user_id, limit=20)

            # Step 3: 消解每個指代詞
            resolutions = []
            resolved_query = query
            entities_found = []
            total_confidence = 1.0

            for word, word_type, weight in coreference_words:
                resolution = await self._resolve_single_coreference(
                    coreference_word=word,
                    word_type=word_type,
                    weight=weight,
                    session_id=session_id,
                    session_entities=session_entities,
                    user_entities=user_entities,
                    user_id=user_id,
                )
                resolutions.append(resolution)

                if resolution.entity_id:
                    entities_found.append(resolution.entity_id)

                # 更新查詢
                resolved_query = resolved_query.replace(word, resolution.resolved_text)
                total_confidence *= resolution.confidence

            return CoreferenceResult(
                original_query=query,
                resolved_query=resolved_query,
                resolutions=resolutions,
                confidence=total_confidence,
                entities_found=list(set(entities_found)),
            )

        except Exception as e:
            logger.error(f"Coreference resolution failed: {e}", exc_info=True)
            return CoreferenceResult(
                original_query=query,
                resolved_query=query,
                resolutions=[],
                confidence=1.0,
                entities_found=[],
            )

    def _detect_coreference_words(
        self,
        query: str,
    ) -> List[Tuple[str, str, float]]:
        """
        檢測查詢中的指代詞

        Returns:
            List of (word, type, weight) tuples
        """
        results = []

        for pattern, info in self._coreference_patterns.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                word = match if isinstance(match, str) else match[0]
                results.append((word, info["type"], info["weight"]))

        return results

    async def _resolve_single_coreference(
        self,
        coreference_word: str,
        word_type: str,
        weight: float,
        session_id: str,
        session_entities: List[str],
        user_entities: List[EntityMemory],
        user_id: str,
    ) -> CoreferenceResolution:
        """
        消解單個指代詞
        """
        # 優先順序：
        # 1. 會話內最近提到的實體
        # 2. 用戶歷史上最常提及的實體
        # 3. 無法消解

        # 策略 1: 查找會話內的實體
        if session_entities:
            for entity_id in reversed(session_entities):  # 最近的在前
                entity = await self.storage.get_entity(entity_id, user_id)
                if entity:
                    return CoreferenceResolution(
                        original_text=coreference_word,
                        resolved_text=entity.entity_value,
                        entity_id=entity.entity_id,
                        source="session",
                        confidence=weight,
                    )

        # 策略 2: 查找用戶歷史上高頻提及的實體
        if user_entities:
            # 按提及次數排序
            sorted_entities = sorted(user_entities, key=lambda e: e.mention_count, reverse=True)
            if sorted_entities:
                top_entity = sorted_entities[0]
                return CoreferenceResolution(
                    original_text=coreference_word,
                    resolved_text=top_entity.entity_value,
                    entity_id=top_entity.entity_id,
                    source="long_term",
                    confidence=weight * 0.8,  # 置信度降低
                )

        # 無法消解，返回原詞
        return CoreferenceResolution(
            original_text=coreference_word,
            resolved_text=coreference_word,
            entity_id=None,
            source="unresolved",
            confidence=weight * 0.5,
        )

    # ==================== 實體提取與學習 ====================

    async def extract_and_store(
        self,
        text: str,
        session_id: str,
        user_id: str,
        auto_learn: bool = True,
    ) -> List[EntityMemory]:
        """
        從文本中提取並存儲實體

        Args:
            text: 輸入文本
            session_id: 會話 ID
            user_id: 用戶 ID
            auto_learn: 是否自動學習新實體

        Returns:
            提取的實體列表
        """
        extracted_entities = []

        try:
            remember_entity_value = await self.extractor.detect_remember_intent(text)
            if remember_entity_value:
                entity = await self.remember_entity(
                    entity_value=remember_entity_value,
                    user_id=user_id,
                    attributes={"source": "user_explicit"},
                )
                extracted_entities.append(entity)
                await self.storage.add_entity_to_session(session_id, entity.entity_id)
                logger.info(f"Explicit remember: {remember_entity_value}")
                return extracted_entities

            if auto_learn:
                existing_entities = await self.storage.list_user_entities(user_id, limit=100)
                new_entities = await self.extractor.extract_from_text(
                    text, user_id, existing_entities
                )
                for entity in new_entities:
                    await self.storage.store_entity(entity)
                    await self.storage.add_entity_to_session(session_id, entity.entity_id)
                    extracted_entities.append(entity)

                logger.info(f"Auto-learned {len(new_entities)} entities")

        except Exception as e:
            logger.error(f"Extract and store failed: {e}", exc_info=True)

        return extracted_entities

    def _detect_remember_intent(self, text: str) -> Optional[str]:
        """
        檢測用戶明確指示（「幫我記住」等）

        Returns:
            要記住的實體名稱，或 None
        """
        patterns = [
            r"(?:幫我|請你|記得)記住[的]?\s*(.+?)(?:\s|$|，|。)",
            r"(?:記住|記得)\s*(?:這個|那個)?\s*(.+?)(?:\s|$|，|。)",
            r"這很重要[，,]\s*(?:請|要|必須)\s*(?:記住|記得)\s*(.+?)(?:\s|$|，|。)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entity_value = match.group(1).strip()
                # 清理常見的無意義詞
                entity_value = re.sub(r"^(?:是|叫做|叫)\s*", "", entity_value).strip()
                if entity_value and len(entity_value) > 1:
                    return entity_value

        return None

    async def _extract_entities_from_text(
        self,
        text: str,
        user_id: str,
    ) -> List[EntityMemory]:
        """
        從文本中自動提取實體

        策略：
        1. 檢查是否已存在
        2. 提取新的潛在實體（簡單的連續中文字符串）
        3. 過濾常見詞
        """
        entities = []

        # 簡單的實體提取：查找連續的中文字符串或英文單詞
        # 這是一個基礎實現，未來可以改進為使用 NER 模型

        # 查找潛在實體（連續 2-10 個字符的中文或英文）
        potential_entities = re.findall(
            r"(?:[\u4e00-\u9fff]{2,10}|[a-zA-Z][a-zA-Z0-9_-]{1,20})",
            text,
        )

        # 過濾常見詞
        stopwords = {
            "系統",
            "功能",
            "幫助",
            "使用",
            "如何",
            "怎麼",
            "什麼",
            "這個",
            "那個",
            "可以",
            "需要",
            "現在",
            "這裡",
            "那裡",
            "您",
            "我",
            "我們",
            "你",
            "大家",
            "有人",
            "沒有人",
            "hello",
            "hi",
            "hey",
            "thanks",
            "thank",
        }

        seen_values = set()
        for entity_value in potential_entities:
            # 清理
            entity_value = entity_value.strip()

            # 跳過停用詞
            if entity_value in stopwords:
                continue

            # 跳過過短或過長的
            if len(entity_value) < 2 or len(entity_value) > 20:
                continue

            # 跳過已處理的
            if entity_value in seen_values:
                continue

            # 檢查是否已存在
            existing = await self.storage.get_entity_by_value(entity_value, user_id)
            if existing:
                seen_values.add(entity_value)
                continue

            # 創建新實體
            entity = EntityMemory(
                entity_value=entity_value,
                entity_type=EntityType.ENTITY_NOUN,
                user_id=user_id,
                confidence=0.7,  # 自動學習的置信度較低
                status="review",  # 待審核
            )

            entities.append(entity)
            seen_values.add(entity_value)

        return entities

    # ==================== 手動記憶 ====================

    async def remember_entity(
        self,
        entity_value: str,
        user_id: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> EntityMemory:
        """
        手動記住實體（用戶明確指示）

        Args:
            entity_value: 實體名稱
            user_id: 用戶 ID
            attributes: 額外屬性

        Returns:
            創建的實體對象
        """
        # 檢查是否已存在
        existing = await self.storage.get_entity_by_value(entity_value, user_id)
        if existing:
            # 更新提及時間
            await self.storage.update_entity_mention(existing.entity_id, user_id)
            return existing

        # 創建新實體
        entity = EntityMemory(
            entity_value=entity_value,
            entity_type=EntityType.ENTITY_NOUN,
            user_id=user_id,
            confidence=1.0,  # 用戶明確指示，置信度最高
            status="active",
            attributes=attributes or {},
        )

        await self.storage.store_entity(entity)
        logger.info(f"Entity remembered: {entity_value}")

        return entity

    # ==================== 實體查詢 ====================

    async def get_entity(
        self,
        entity_value: str,
        user_id: str,
    ) -> Optional[EntityMemory]:
        """獲取指定實體"""
        return await self.storage.get_entity_by_value(entity_value, user_id)

    async def search_entities(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
    ) -> List[EntityMemory]:
        """搜索實體"""
        return await self.storage.search_entities(query, user_id, limit)

    async def hybrid_search_entities(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        use_vector: bool = True,
    ) -> List[EntityMemory]:
        """
        混合搜尋實體（精確匹配 + 向量搜尋）

        Args:
            query: 查詢文本
            user_id: 用戶 ID
            limit: 返回數量限制
            use_vector: 是否使用向量搜尋

        Returns:
            匹配的實體列表
        """
        query_vector = None

        if use_vector:
            try:
                from llm.moe.moe_manager import LLMMoEManager

                moe = LLMMoEManager()
                moe.select_model("embedding")
                response = await moe.generate(
                    prompt=f"Generate embedding for: {query}",
                    temperature=0.0,
                    max_tokens=100,
                )
                if response:
                    response_text = (
                        response.get("text")
                        if isinstance(response, dict)
                        else getattr(response, "text", str(response))
                    )
                    if response_text:
                        import json

                        data = json.loads(response_text)
                        query_vector = data.get("embedding", None)
            except Exception as e:
                logger.debug(f"Vector generation failed: {e}, using exact match only")

        return await self.storage.hybrid_search_entities(
            query=query,
            query_vector=query_vector,
            user_id=user_id,
            limit=limit,
        )

    async def get_user_entities(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[EntityMemory]:
        """列出用戶的所有實體"""
        return await self.storage.list_user_entities(user_id, limit)

    # ==================== 會話管理 ====================

    async def update_session_context(
        self,
        session_id: str,
        user_id: str,
        entity_id: Optional[str] = None,
    ) -> SessionContext:
        """
        更新會話上下文

        Args:
            session_id: 會話 ID
            user_id: 用戶 ID
            entity_id: 新提到的實體 ID（可選）

        Returns:
            更新後的會話上下文
        """
        context = await self.storage.get_session_context(session_id)

        if context is None:
            context = SessionContext(
                session_id=session_id,
                user_id=user_id,
            )

        context.user_id = user_id
        context.last_activity = datetime.utcnow()

        if entity_id:
            if entity_id not in context.mentioned_entities:
                context.mentioned_entities.append(entity_id)
            context.last_referred_entity = entity_id

        await self.storage.store_session_context(session_id, context)
        return context


def get_entity_memory_service() -> EntityMemoryService:
    """獲取 Entity Memory Service 實例（單例模式）"""
    global _entity_memory_service
    if _entity_memory_service is None:
        _entity_memory_service = EntityMemoryService()
    return _entity_memory_service


def reset_entity_memory_service() -> None:
    """重置 Entity Memory Service 實例（主要用於測試）"""
    global _entity_memory_service
    _entity_memory_service = None
