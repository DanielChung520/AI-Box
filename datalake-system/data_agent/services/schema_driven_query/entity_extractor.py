# -*- coding: utf-8 -*-
"""
多語言實體提取器

職責：
- 從用戶查詢中提取實體（工作站、料號、倉庫等）
- 支援多語言（繁體中文、簡體中文、泰文、英文）
- 使用多策略：關鍵詞匹配 → 語義匹配

使用方式：
    extractor = EntityExtractor()
    entities = await extractor.extract(
        query="能查出工作站WC77 生產那些料號嗎？",
        language="zh-TW"
    )
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .embedding_manager import EmbeddingManager


class EntityType(Enum):
    """實體類型」"""

    WORKSTATION = "WORKSTATION"
    ITEM_NO = "ITEM_NO"
    WAREHOUSE_NO = "WAREHOUSE_NO"
    TIME_RANGE = "TIME_RANGE"
    MO_DOC_NO = "MO_DOC_NO"
    CUSTOMER_NO = "CUSTOMER_NO"
    LOCATION_NO = "LOCATION_NO"
    EXISTING_STOCKS = "EXISTING_STOCKS"
    ZERO_STOCKS = "ZERO_STOCKS"  # 庫存為零標記
    STATUS_CODE = "STATUS_CODE"  # 工單狀態碼


@dataclass
class ExtractedEntity:
    """提取的實體」"""

    type: str  # 實體類型
    value: str  # 實體值
    strategy: str  # 匹配策略: keyword | pattern | semantic
    confidence: float  # 信心度 0.0-1.0
    start: int  # 在查詢中的起始位置
    end: int  # 在查詢中的結束位置


class EntityExtractor:
    """多語言實體提取器」"""

    # L1: 多語言關鍵詞詞典
    KEYWORD_DICT = {
        "WORKSTATION": {
            "zh-TW": ["工作站", "工作中心", "工站", "機台", "工位", "WC", "ws"],
            "zh-CN": ["工作站", "工作中心", "工站", "机台", "工位", "WC", "ws"],
            "th": ["สถานี", "สถานีงาน", "สถานีการผลิต", "wc"],
            "en": ["workstation", "station", "wc", "ws", "work station"],
        },
        "ITEM_NO": {
            "zh-TW": ["料號", "產品", "件號", "編號", "品號", "料件"],
            "zh-CN": ["料号", "产品", "件号", "编号", "品号", "料件"],
            "th": ["รหัสสินค้า", "ชิ้น", "สินค้า", "pn", "item"],
            "en": ["item", "part", "product", "pn", "item number", "part number"],
        },
        "WAREHOUSE_NO": {
            "zh-TW": ["倉庫", "庫別", "倉別", "庫號", "WH", "W/H"],
            "zh-CN": ["仓库", "库别", "库号", "WH", "W/H"],
            "th": ["คลัง", "ที่เก็บ", "warehouse", "wh"],
            "en": ["warehouse", "location", "wh", "warehouse number"],
        },
        "TIME_RANGE": {
            "zh-TW": ["時間", "日期", "期間", "月份", "年", "這週", "上週", "本月"],
            "zh-CN": ["时间", "日期", "期间", "月份", "年", "这周", "上周", "本月"],
            "th": ["วันที่", "เวลา", "ช่วงเวลา", "เดือน", "ปี", "สัปดาห์นี้"],
            "en": ["date", "time", "period", "month", "year", "week", "this week", "last month"],
        },
        "MO_DOC_NO": {
            "zh-TW": ["工單", "工單號", "WO", "work order"],
            "zh-CN": ["工单", "工单号", "WO", "work order"],
            "th": ["ใบสั่งงาน", "WO", "work order"],
            "en": ["work order", "wo", "mo", "manufacturing order"],
        },
    }

    # L2: 正則模式
    PATTERN_DICT = {
        "WORKSTATION": [
            r"(WC[\w-]+)",  # WC77, WC01-A (without word boundary for Chinese text)
            r"(W[\d]{3}[\w-]*)",  # W001, W001-A
            r"(WS[\w-]+)",  # WS01
            r"(ST[\w-]+)",  # ST01
        ],
        "ITEM_NO": [
            r"([A-Z]{2}[\d]{2}[A-Z0-9]{8,})",  # 81199GG01080 (letter prefix)
            r"(\d{2}[A-Z0-9]{8,})",  # 81463GG01188 (digit prefix, 2 digits + alphanumeric)
            r"([A-Z]{2}[\d]{2}-[\d]{3,4})",  # RM05-008, AB12-3456 (letter-digit-hyphen format)
            r"([A-Z0-9]{10,})",  # 通用料號格式
        ],
        "WAREHOUSE_NO": [
            r"(?<![A-Z0-9])([A-Z]{0,2}[\d]{4})(?![A-Z0-9])",  # 8802, W01, WH01 (standalone)
            r"(WH[\d]{2,4})(?![A-Z0-9])",  # WH01, WH8802 (standalone)
        ],
        "MO_DOC_NO": [
            r"(WO-[A-Z0-9]+-[A-Z0-9]+-\d{8,})",  # WO-ABC-12-12345678 (完整格式)
            r"([A-Z]{2}-[\w]+-\d{8,})",  # WO-ABC-12345678
            r"(WO[-\s]?[\w]+)",  # WO-123
        ],
        "TIME_RANGE": [
            r"(\d{4}年\d{1,2}月)",  # 2025年1月
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",  # 2025/01/15
            r"(最近[一週|一週|一個月|一個月|一年])",  # 最近一週
        ],
        # 數量比較模式：低於/高於/大於/小於 + 數字
        "EXISTING_STOCKS": [
            r"(低於|低過|小於|少於)\s*(\d+\.?\d*)",  # 低於 1000, 小於 500
            r"(高於|高過|大於|多於)\s*(\d+\.?\d*)",  # 高於 1000, 大於 500
            r"<\s*(\d+\.?\d*)",  # < 1000
            r">\s*(\d+\.?\d*)",  # > 1000
            r"(為零|等於零|等於0|是零)|(沒有庫存|無庫存)",  # 為零、沒有庫存
        ],
        # 工單狀態碼
        "STATUS_CODE": [
            r"[,\s](M|F|C|N|Y|X)[,\s。]",  # M、F、C、N、Y、X 狀態碼
            r"狀態[ \t]*([MFCNYX])",  # 狀態 M
            r"狀態為[ \t]*([MFCNYX])",  # 狀態為 M
        ],
        # 庫存為零的標記實體
        "ZERO_STOCKS": [
            r"(為零|等於零|等於0|是零)|(沒有庫存|無庫存)|(庫存為零)",
        ],
    }

    def __init__(
        self,
        embedding_config: Optional[Dict[str, Any]] = None,
        concepts_file: Optional[str] = None,
        enable_semantic: bool = True,
        similarity_threshold: float = 0.7,
    ):
        """
        初始化實體提取器

        Args:
            embedding_config: Embedding 配置
            concepts_file: concepts.json 文件路徑
            enable_semantic: 是否啟用語義匹配
            similarity_threshold: 語義相似度閾值
        """
        self.embedding_manager = EmbeddingManager(embedding_config)
        self.concepts_file = concepts_file or self._default_concepts_file()
        self.concepts = self._load_concepts()
        self.enable_semantic = enable_semantic
        self.similarity_threshold = similarity_threshold

    def _default_concepts_file(self) -> str:
        """獲取預設 concepts 文件路徑」"""
        # entity_extractor.py 在 schema_driven_query/
        # concepts.json 在 metadata/systems/tiptop_jp/
        return str(Path(__file__).parent / "../../../metadata/systems/tiptop_jp/concepts.json")

    def _load_concepts(self) -> Dict[str, Any]:
        """載入概念定義」"""
        try:
            with open(self.concepts_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"警告：無法載入 concepts.json: {e}")
            return {}

    def extract_sync(self, query: str, language: str = "zh-TW") -> List[ExtractedEntity]:
        """
        同步提取實體（用於 UltraFastParser 整合）

        Args:
            query: 用戶查詢
            language: 語言代碼

        Returns:
            提取的實體列表
        """
        entities = []

        # L2: 正則模式匹配（最高優先級，提取實際值）
        pattern_entities = self._pattern_match(query)
        entities.extend(pattern_entities)

        # L1: 關鍵詞匹配（次優先級，識別意圖類型）
        keyword_entities = self._keyword_match(query, language)
        entities.extend(keyword_entities)

        # L3: 語義匹配（備用）- 跳過因為是同步方法
        # 如果需要語義匹配，請使用 async extract()

        # 去重和排序
        return self._deduplicate(entities)

    async def extract(self, query: str, language: str = "zh-TW") -> List[ExtractedEntity]:
        """
        提取實體

        Args:
            query: 用戶查詢
            language: 語言代碼

        Returns:
            提取的實體列表
        """
        entities = []

        # L2: 正則模式匹配（最高優先級，提取實際值）
        pattern_entities = self._pattern_match(query)
        entities.extend(pattern_entities)

        # L1: 關鍵詞匹配（次優先級，識別意圖類型）
        keyword_entities = self._keyword_match(query, language)
        entities.extend(keyword_entities)

        # L3: 語義匹配（備用，當 L1 和 L2 都沒有結果時）
        if self.enable_semantic and not keyword_entities and not pattern_entities:
            semantic_entities = await self._semantic_match(query, language)
            entities.extend(semantic_entities)

        # 去重和排序
        return self._deduplicate(entities)

    def _keyword_match(self, query: str, language: str) -> List[ExtractedEntity]:
        """關鍵詞匹配（識別實體類型，不提取值）」"""
        entities = []
        query_lower = query.lower()

        for entity_type, lang_keywords in self.KEYWORD_DICT.items():
            keywords = lang_keywords.get(language, []) + lang_keywords.get("en", [])

            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in query_lower:
                    # 找到位置
                    start = query_lower.find(keyword_lower)
                    end = start + len(keyword)

                    entities.append(
                        ExtractedEntity(
                            type=entity_type,
                            value=f"[{keyword}]",  # 用方括號標記這是關鍵詞，非實際值
                            strategy="keyword",
                            confidence=0.3,  # 較低的信心度
                            start=start,
                            end=end,
                        )
                    )

        return entities

    def _pattern_match(self, query: str) -> List[ExtractedEntity]:
        """正則模式匹配」"""
        entities = []

        # 特殊處理：EXISTING_STOCKS 數量比較（低於/高於 + 數字）
        stock_comparison_patterns = [
            (r"(低於|低過|小於|少於)\s*(\d+\.?\d*)", "<"),
            (r"(高於|高過|大於|多於)\s*(\d+\.?\d*)", ">"),
            (r"<\s*(\d+\.?\d*)", "<"),
            (r">\s*(\d+\.?\d*)", ">"),
            (r"小於\s*:?\s*(\d+\.?\d*)", "<"),
            (r"大於\s*:?\s*(\d+\.?\d*)", ">"),
        ]

        for pattern, operator in stock_comparison_patterns:
            match = re.search(pattern, query)
            if match:
                value = match.group(2)  # 提取數字部分
                entities.append(
                    ExtractedEntity(
                        type="EXISTING_STOCKS",
                        value=f"{operator}{value}",  # 存儲為 "<1000" 或 ">500"
                        strategy="pattern",
                        confidence=0.95,  # 高信心度
                        start=match.start(),
                        end=match.end(),
                    )
                )
                break  # 只匹配第一個數量比較

        # 特殊處理：ZERO_STOCKS（庫存為零）
        zero_stock_patterns = [
            r"庫存為零",
            r"為零",
            r"等於零",
            r"等於0",
            r"是零",
            r"沒有庫存",
            r"無庫存",
        ]
        for pattern in zero_stock_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                entities.append(
                    ExtractedEntity(
                        type="ZERO_STOCKS",
                        value="true",
                        strategy="pattern",
                        confidence=0.95,
                        start=match.start(),
                        end=match.end(),
                    )
                )
                break  # 只匹配第一個

        # 特殊處理：STATUS_CODE（工單狀態 M/F/C/N/Y/X）
        status_patterns = [
            r"[,\s]([MFCNYX])[,\s。]",  # M、F、C、N、Y、X 狀態碼
            r"狀態[ \t]*([MFCNYX])",  # 狀態 M
            r"狀態為[ \t]*([MFCNYX])",  # 狀態為 M
        ]
        for pattern in status_patterns:
            match = re.search(pattern, query)
            if match:
                value = match.group(1)  # 提取狀態碼
                entities.append(
                    ExtractedEntity(
                        type="STATUS_CODE",
                        value=value,
                        strategy="pattern",
                        confidence=0.95,
                        start=match.start(),
                        end=match.end(),
                    )
                )
                break  # 只匹配第一個

        # 處理 PATTERN_DICT 中的通用模式（ITEM_NO, WORKSTATION, MO_DOC_NO, TIME_RANGE）
        for entity_type, patterns in self.PATTERN_DICT.items():
            for pattern in patterns:
                match = re.search(pattern, query)
                if match:
                    value = match.group(1) if match.groups() else match.group(0)
                    entities.append(
                        ExtractedEntity(
                            type=entity_type,
                            value=value,
                            strategy="pattern",
                            confidence=0.9,
                            start=match.start(),
                            end=match.end(),
                        )
                    )
                    break  # 每種實體類型只匹配第一個

        return entities

    async def _semantic_match(self, query: str, language: str) -> List[ExtractedEntity]:
        """語義匹配（使用 Embedding）」"""
        # 構建候選概念
        candidates = {}
        for entity_type in self.KEYWORD_DICT.keys():
            # 從概念定義中獲取描述
            if entity_type in self.concepts.get("concepts", {}):
                desc = self.concepts["concepts"][entity_type].get("description", "")
                candidates[entity_type] = desc
            else:
                # 使用關鍵詞作為描述
                keywords = self.KEYWORD_DICT.get(entity_type, {}).get(language, [])
                candidates[entity_type] = ", ".join(keywords[:5])

        # 使用 Embedding 進行相似度搜索
        try:
            results = await self.embedding_manager.find_similar(
                query, candidates, top_k=3, threshold=0.6
            )
        except Exception as e:
            print(f"警告：語義匹配失敗: {e}")
            return []

        entities = []
        for entity_type, score in results:
            entities.append(
                ExtractedEntity(
                    type=entity_type,
                    value=query,  # 使用原始查詢作為值
                    strategy="semantic",
                    confidence=score,
                    start=0,
                    end=len(query),
                )
            )

        return entities

    def _deduplicate(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """去重（優先 pattern > keyword，保留信心度最高的）」"""
        # 策略優先級
        strategy_priority = {"pattern": 3, "keyword": 2, "semantic": 1}

        seen = {}
        result = []

        for entity in entities:
            key = entity.type

            # 如果是同一類型，優先選擇 pattern 策略
            if key in seen:
                existing = seen[key]
                existing_priority = strategy_priority.get(existing.strategy, 0)
                new_priority = strategy_priority.get(entity.strategy, 0)

                # 優先級策略：pattern > keyword > semantic
                if new_priority > existing_priority:
                    seen[key] = entity
                elif new_priority == existing_priority and entity.confidence > existing.confidence:
                    seen[key] = entity
            else:
                seen[key] = entity

        return list(seen.values())

    def get_extracted_value(
        self, entities: List[ExtractedEntity], entity_type: str
    ) -> Optional[str]:
        """獲取指定類型的實體值」"""
        for entity in entities:
            if entity.type == entity_type:
                return entity.value
        return None


async def demo():
    """演示」"""
    extractor = EntityExtractor()

    queries = [
        ("能查出工作站WC77 生產那些料號嗎？", "zh-TW"),
        ("工站 WC01-A 生產什麼料號", "zh-TW"),
        ("查詢 8802 倉庫的庫存", "zh-TW"),
        ("show me items at station WC77", "en"),
        ("工位 WC01-A 生產哪些料号", "zh-CN"),
    ]

    for query, lang in queries:
        print(f"\nQuery: {query} ({lang})")
        entities = await extractor.extract(query, lang)

        for entity in entities:
            print(f"  - {entity.type}: {entity.value} ({entity.strategy}, {entity.confidence:.2f})")


if __name__ == "__main__":
    import asyncio

    asyncio.run(demo())
