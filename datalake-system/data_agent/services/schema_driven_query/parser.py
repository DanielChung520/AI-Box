# -*- coding: utf-8 -*-
"""
Data-Agent-JP NLQ 解析器

功能：
- 解析自然語言查詢（NLQ）
- 識別意圖和參數（完全使用 RAG，不含正則表達式或硬編碼）

建立日期: 2026-02-10
建立人: Daniel Chung
最後修改日期: 2026-02-28

架構：
    NLQ → DA_IntentRAG（意圖識別）→ MasterRAG（參數提取）→ Generate SQL

[V4_EXCLUSIVE] 此模組已遷移到 v4/execute 端點

重要：
- 禁止使用正則表達式（re模組）
- 禁止硬編碼意圖或參數模式
- 所有意圖識別必須使用 DA_IntentRAG
- 所有參數提取必須使用 MasterRAG

"""

import logging
import hashlib
import time
from typing import Dict, Any, Optional, List
from collections import OrderedDict
from threading import Lock

from .config import get_config
from .models import ParsedIntent


logger = logging.getLogger(__name__)


class LRUCache:
    """簡單 LRU 快取"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.cache: OrderedDict = OrderedDict()
        self.lock = Lock()

    def _make_key(self, nlq: str) -> str:
        """產生快取 key"""
        return hashlib.md5(nlq.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Dict]:
        """取得快取"""
        with self.lock:
            if key not in self.cache:
                return None

            entry = self.cache[key]
            # 檢查 TTL
            if time.time() - entry["timestamp"] > self.ttl:
                del self.cache[key]
                return None

            # 移到末尾（最近使用）
            self.cache.move_to_end(key)
            return entry["data"]

    def set(self, key: str, data: Dict):
        """設定快取"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
            elif len(self.cache) >= self.max_size:
                # 移除最舊的項目
                self.cache.popitem(last=False)

            self.cache[key] = {"data": data, "timestamp": time.time()}

    def clear(self):
        """清除快取"""
        with self.lock:
            self.cache.clear()

    @property
    def size(self) -> int:
        return len(self.cache)


# 全域 LLM 回應快取
_llm_cache = LRUCache(max_size=500, ttl_seconds=7200)


class UltraFastParser:
    """
    超快解析器 - 純 RAG 匹配，不使用正則表達式或硬編碼

    流程：
    1. 調用 DA_IntentRAG 識別意圖
    2. 參數由後續的 MasterRAG 提取（不在此處處理）
    """

    # [V4_EXCLUSIVE] 最低置信度閾值
    MIN_CONFIDENCE_THRESHOLD = 0.3

    @classmethod
    def parse(cls, nlq: str) -> Optional[ParsedIntent]:
        """使用 DA_IntentRAG 解析 NLQ

        Args:
            nlq: 自然語言查詢

        Returns:
            ParsedIntent: 解析後的意圖（只包含意圖，參數為空）
            None: 如果 RAG 無法識別意圖
        """
        logger.info(f"[UltraFastParser] Starting RAG-based parse for: {nlq}")

        # [V4_EXCLUSIVE] 只使用 DA_IntentRAG 進行意圖識別
        try:
            from .da_intent_rag import DA_IntentRAG

            rag = DA_IntentRAG.get_instance_sync()
            rag_result = rag.match_intent_sync(nlq)

            if rag_result and rag_result.confidence >= cls.MIN_CONFIDENCE_THRESHOLD:
                logger.info(
                    f"[DA_IntentRAG] Matched: {rag_result.intent}, "
                    f"confidence: {rag_result.confidence:.2f}"
                )
                # [V4_EXCLUSIVE] 只返回意圖，參數由 MasterRAG 提取
                return ParsedIntent(
                    intent=rag_result.intent,
                    confidence=rag_result.confidence,
                    params={},  # [V4_EXCLUSIVE] 參數由後續流程（MasterRAG）提取
                    token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    limit=100,
                    offset=0,
                )
            else:
                logger.warning(
                    f"[DA_IntentRAG] No match or low confidence: "
                    f"confidence={rag_result.confidence if rag_result else 0}"
                )
                return None

        except Exception as e:
            logger.error(f"[DA_IntentRAG] Failed: {e}", exc_info=True)
            return None


# [V4_EXCLUSIVE] 保留 LLMNLQParser 以供回退，但標記為 deprecated
# 長期應該完全移除，使用 RAG 替代
class NLQParser:
    """
    [DEPRECATED] 自然語言查詢解析器（基礎類）
    建議使用 UltraFastParser + MasterRAG
    """

    def __init__(self, config: Optional[Any] = None):
        self.config = config or get_config().llm


# [V4_EXCLUSIVE] 標記為 deprecated，長期應移除
class LLMNLQParser(NLQParser):
    """
    [DEPRECATED] LLM 自然語言查詢解析器
    """

    def __init__(self, config: Optional[Any] = None, skip_validation: bool = False):
        super().__init__(config)
        self.skip_validation = skip_validation
        self._intents = None
        self._load_intents()

    def _load_intents(self):
        """從 intents.json 載入"""
        from .loaders import get_schema_loader
        from .config import get_config

        loader = get_schema_loader(get_config())
        self._intents = loader.load_intents()

    def load_intents(self, intents):
        """載入意圖"""
        self._intents = intents

    def parse(self, query: str) -> ParsedIntent:
        """解析查詢"""
        # ... deprecated code
        pass


class SimpleNLQParser(NLQParser):
    """
    [DEPRECATED] 簡單解析器
    """

    def __init__(self, config: Optional[Any] = None, skip_validation: bool = False):
        super().__init__(config)
        self.skip_validation = skip_validation
        self._intents = None
        self._load_intents()

    def _load_intents(self):
        """從 intents.json 載入"""
        from .loaders import get_schema_loader
        from .config import get_config

        loader = get_schema_loader(get_config())
        self._intents = loader.load_intents()

    def load_intents(self, intents):
        """載入意圖"""
        self._intents = intents

    def parse(self, query: str) -> ParsedIntent:
        """解析查詢"""
        # ... deprecated code
        pass
