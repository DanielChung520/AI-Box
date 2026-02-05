# 代碼功能說明: Entity Memory 實體提取器
# 創建日期: 2026-02-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-04

"""Entity Memory 實體提取模組

提供多種實體提取策略：
1. 規則基礎提取 - 專有名詞模式匹配
2. LLM 提取 - 使用 LLM 識別實體
3. 用戶指示提取 - 檢測「幫我記住」等模式
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from .models import EntityMemory, EntityType

logger = logging.getLogger(__name__)

# 停用詞列表
STOPWORDS = {
    # 系統/功能相關
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
    "一下",
    "一下",
    "這些",
    "那些",
    # 問候語
    "你好",
    "早安",
    "午安",
    "晚安",
    "嗨",
    "hi",
    "hello",
    "hey",
    "謝謝",
    "感謝",
    "感恩",
    "再見",
    "拜拜",
    "bye",
    # 常見動詞
    "請問",
    "請教",
    "告訴",
    "說明",
    "解釋",
    # 時間相關
    "今天",
    "昨天",
    "明天",
    "後天",
    # 數字相關
    "一",
    "二",
    "三",
    "四",
    "五",
    "六",
    "七",
    "八",
    "九",
    "十",
    # 常用形容詞
    "好",
    "壞",
    "多",
    "少",
    "大",
    "小",
    "新",
    "舊",
}

# 專有名詞模式
PROPER_NOUN_PATTERNS = [
    # 英文系統/產品名稱
    (r"\b[A-Z][a-zA-Z0-9_-]+\b", "english_product"),
    # RM 料號模式
    (r"RM[A-Za-z0-9]{2,}-[A-Za-z0-9]{3,}", "part_number"),
    # 中文組織名稱結尾
    (r"[\u4e00-\u9fff]{2,10}(公司|組織|機構|大學|學院|醫院|銀行|飯店|餐廳|協會)", "org_name"),
    # 中文產品名稱結尾
    (r"[\u4e00-\u9fff]{2,10}(系統|平台|工具|框架|庫|服務|引擎|模型|代理|機器人)", "product_name"),
    # 技術術語
    (r"[\u4e00-\u9fff]{2,8}(API|SDK|UI|UX|AI|ML|LLM|RAG|DB|DB|SQL|NoSQL)", "tech_term"),
    # 混合英文中文
    (r"[A-Za-z0-9]+[\u4e00-\u9fff]+", "mixed_name"),
]


class ExtractionCandidate(BaseModel):
    """實體提取候選"""

    value: str
    start: int
    end: int
    pattern_type: str = "general"
    confidence: float = 0.5


class EntityExtractor:
    """實體提取器"""

    def __init__(self):
        # 用戶指示模式
        self._remember_patterns = [
            # 標準「幫我記住」模式
            (
                r"(?:幫我|請你|必須|要|應該)\s*(?:記住|記得|記錄|存下)\s*(?:這個|那個)?\s*(.+?)(?:\s|$|，|。|？|!)",
                1.0,
            ),
            # 「這很重要」模式
            (
                r"這(?:很|非常|十分)\s*重要[，,]\s*(?:請|要|必須)\s*(?:記住|記得|記錄)\s*(?:這?個)?\s*(.+?)(?:\s|$|，|。|？|!)",
                1.0,
            ),
            # 「請記住」模式
            (r"請(?:記住|記得|記錄)\s*(?:這?個)?\s*(.+?)(?:\s|$|，|。|？|!)", 1.0),
            # 「記住這個」模式
            (r"記住(?:這|那)\s*個?\s*(.+?)(?:\s|$|，|。|？|!)", 0.9),
            # 「這是X」模式（需要記住）
            (r"這(?:是|叫|為)\s*(.+?)(?:\s|，|。|？|!|$)", 0.8),
        ]

        # 排除模式（這些不是需要記憶的實體）
        self._exclude_patterns = [
            r"^[一二三四五六七八九十百千萬億]$",  # 單個數字
            r"^[東南西北]$",  # 單個方向
            r"^(好|壞|多|少|大|小)$",  # 簡單形容詞
            r"^[你您我他她它]$",  # 代詞
        ]

        # 系統實體關鍵詞（已經是種子數據，不需要重複學習）
        self._system_entities = {
            "ai-box",
            "ai_box",
            "mm-agent",
            "ka-agent",
            "orchestrator",
            "arangodb",
            "qdrant",
            "chromadb",
            "redis",
            "seaweedfs",
            "ollama",
            "fastapi",
            "react",
            "langgraph",
            "langchain",
            "chatgpt",
            "claude",
            "gemini",
            "deepseek",
        }

    async def extract_from_text(
        self,
        text: str,
        user_id: str,
        existing_entities: Optional[List[EntityMemory]] = None,
    ) -> List[EntityMemory]:
        """
        從文本中提取實體

        Args:
            text: 輸入文本
            user_id: 用戶 ID
            existing_entities: 現有的實體列表（用於去重）

        Returns:
            提取的實體列表
        """
        candidates = []

        # Step 1: 使用多種策略提取候選
        rule_candidates = await self._extract_by_rules(text)
        candidates.extend(rule_candidates)

        # Step 2: 使用 LLM 提取（如果可用）
        llm_candidates = await self._extract_by_llm(text)
        candidates.extend(llm_candidates)

        # Step 3: 去重並過濾
        unique_entities = await self._deduplicate_and_filter(
            candidates=candidates,
            user_id=user_id,
            existing_entities=existing_entities or [],
        )

        logger.info(f"Extracted {len(unique_entities)} entities from text")
        return unique_entities

    async def _extract_by_rules(self, text: str) -> List[ExtractionCandidate]:
        """使用規則基礎方法提取實體"""
        candidates = []

        # 方法 1: 專有名詞模式匹配
        for pattern, pattern_type in PROPER_NOUN_PATTERNS:
            for match in re.finditer(pattern, text):
                value = match.group()
                start = match.start()
                end = match.end()

                # 過濾短暫無意義的匹配
                if len(value) < 2:
                    continue

                # 檢查是否為系統實體
                if value.lower() in self._system_entities:
                    continue

                candidates.append(
                    ExtractionCandidate(
                        value=value,
                        start=start,
                        end=end,
                        pattern_type=pattern_type,
                        confidence=0.7,
                    )
                )

        # 方法 2: 連續中文字符串（基礎 NER）
        chinese_pattern = r"[\u4e00-\u9fff]{2,10}"
        for match in re.finditer(chinese_pattern, text):
            value = match.group()

            # 跳過停用詞
            if value in STOPWORDS:
                continue

            # 跳過數字開頭的
            if re.match(r"^\d", value):
                continue

            candidates.append(
                ExtractionCandidate(
                    value=value,
                    start=match.start(),
                    end=match.end(),
                    pattern_type="chinese_noun",
                    confidence=0.6,
                )
            )

        return candidates

    async def _extract_by_llm(self, text: str) -> List[ExtractionCandidate]:
        """使用 LLM 提取實體"""
        candidates = []

        # 檢查是否有 LLM 服務可用
        try:
            from llm.moe.moe_manager import LLMMoEManager

            moe = LLMMoEManager()
        except ImportError:
            logger.debug("LLM service not available, skipping LLM extraction")
            return candidates

        prompt = f"""請從以下文本中提取需要長期記憶的實體名稱（人名、地名、組織名、產品名、系統名等）。

只提取明確提到的實體名稱，不需要解釋。

文本：
{text}

請以 JSON 格式回覆：
{{
  "entities": [
    {{"name": "實體名稱", "confidence": 0.0-1.0}}
  ]
}}

如果沒有需要記憶的實體，回覆 {{
  "entities": []
}}"""

        try:
            moe.select_model("semantic_understanding")
            response = await moe.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=500,
            )

            if response:
                response_text = (
                    response.get("text")
                    if isinstance(response, dict)
                    else getattr(response, "text", str(response))
                )
                if response_text:
                    try:
                        data = json.loads(response_text)
                        for entity_data in data.get("entities", []):
                            name = entity_data.get("name", "").strip()
                            if name and len(name) >= 2:
                                candidates.append(
                                    ExtractionCandidate(
                                        value=name,
                                        start=-1,
                                        end=-1,
                                        pattern_type="llm",
                                        confidence=entity_data.get("confidence", 0.8),
                                    )
                                )
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse LLM response: {response_text}")

        except Exception as e:
            logger.debug(f"LLM extraction failed: {e}")

        return candidates

    async def _deduplicate_and_filter(
        self,
        candidates: List[ExtractionCandidate],
        user_id: str,
        existing_entities: List[EntityMemory],
    ) -> List[EntityMemory]:
        """去重並過濾候選，轉換為 EntityMemory"""
        # 現有實體的標準化集合（用於去重）
        existing_values = {e.entity_value for e in existing_entities}
        existing_values_lower = {e.entity_value.lower() for e in existing_entities}

        # 去重：合併相同值，保留最高置信度
        value_map: Dict[str, ExtractionCandidate] = {}
        for candidate in candidates:
            normalized = candidate.value.lower().strip()
            if normalized not in value_map:
                value_map[normalized] = candidate
            else:
                # 取較高置信度
                if candidate.confidence > value_map[normalized].confidence:
                    value_map[normalized] = candidate

        # 過濾並轉換為 EntityMemory
        entities = []
        for normalized, candidate in value_map.items():
            value = candidate.value.strip()

            # 跳過已在現有列表中的實體
            if value in existing_values or value.lower() in existing_values_lower:
                continue

            # 跳過排除模式
            if self._should_exclude(value):
                continue

            # 跳過過短或過長的
            if len(value) < 2 or len(value) > 30:
                continue

            # 創建 EntityMemory
            entity = EntityMemory(
                entity_value=value,
                entity_type=EntityType.ENTITY_NOUN,
                user_id=user_id,
                confidence=candidate.confidence,
                status="review",  # 待審核
                attributes={
                    "source": "auto_extract",
                    "pattern_type": candidate.pattern_type,
                    "extraction_confidence": candidate.confidence,
                },
            )
            entities.append(entity)

        return entities

    def _should_exclude(self, value: str) -> bool:
        """判斷是否應該排除"""
        # 排除模式檢查
        for pattern in self._exclude_patterns:
            if re.match(pattern, value):
                return True

        # 停用詞檢查
        if value in STOPWORDS:
            return True

        # 純數字檢查
        if re.match(r"^\d+$", value):
            return True

        # 純符號檢查
        if re.match(r"^[\s\W]+$", value):
            return True

        return False

    async def detect_remember_intent(self, text: str) -> Optional[str]:
        """
        檢測用戶明確指示（「幫我記住」等）

        Args:
            text: 輸入文本

        Returns:
            要記住的實體名稱，或 None
        """
        for pattern, weight in self._remember_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entity_value = match.group(1).strip()

                # 清理常見的無意義詞
                entity_value = re.sub(r"^(?:是|叫做|叫|為)\s*", "", entity_value).strip()

                # 移除末尾的標點符號
                entity_value = re.sub(r"[，,。.！!？?]$", "", entity_value).strip()

                # 跳過過短或過長的
                if 1 < len(entity_value) <= 30 and not self._should_exclude(entity_value):
                    logger.info(f"Detected remember intent: {entity_value}")
                    return entity_value

        return None

    async def is_new_entity(
        self,
        entity_value: str,
        user_id: str,
        storage: Any,
    ) -> bool:
        """
        判斷是否為新實體

        Args:
            entity_value: 實體名稱
            user_id: 用戶 ID
            storage: 存儲服務

        Returns:
            是否為新實體
        """
        # 檢查精確匹配
        existing = await storage.get_entity_by_value(entity_value, user_id)
        if existing:
            return False

        # 檢查模糊匹配
        normalized = entity_value.lower().strip()
        all_entities = await storage.list_user_entities(user_id, limit=100)

        for entity in all_entities:
            if entity.entity_value.lower() == normalized:
                return False

        return True

    async def extract_entities_from_conversation(
        self,
        conversation: List[Dict[str, str]],
        user_id: str,
    ) -> List[EntityMemory]:
        """
        從對話歷史中提取所有實體

        Args:
            conversation: 對話歷史 [{"role": "user"|"assistant", "content": "..."}]
            user_id: 用戶 ID

        Returns:
            提取的實體列表
        """
        all_entities = []

        for message in conversation:
            if message.get("role") == "user":
                content = message.get("content", "")
                entities = await self.extract_from_text(content, user_id)
                all_entities.extend(entities)

        # 去重
        seen = set()
        unique_entities = []
        for entity in all_entities:
            key = (entity.entity_value.lower(), entity.user_id)
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)

        return unique_entities


# 全局實例
_entity_extractor: Optional[EntityExtractor] = None


def get_entity_extractor() -> EntityExtractor:
    """獲取 Entity Extractor 實例"""
    global _entity_extractor
    if _entity_extractor is None:
        _entity_extractor = EntityExtractor()
    return _entity_extractor


def reset_entity_extractor() -> None:
    """重置 Entity Extractor 實例"""
    global _entity_extractor
    _entity_extractor = None
