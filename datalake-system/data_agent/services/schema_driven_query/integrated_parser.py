# -*- coding: utf-8 -*-
"""
整合式查詢解析器

整合以下組件：
- EntityExtractor: 多語言實體提取
- PreValidator: 查詢前驗證
- ResponseBuilder: 結構化回應

功能：
- 意圖識別（L1 關鍵詞 → L2 正則 → L3 語義）
- 實體提取（多語言關鍵詞 + 正則 + 語義匹配）
- 預驗證（Schema、權限、範圍檢查）
- 結構化回應（SQL、數據、錯誤資訊）

建立日期: 2026-02-18
建立人: Daniel Chung
最後修改日期: 2026-02-18
"""

import json
import logging
import re
import uuid
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from .entity_extractor import EntityExtractor, ExtractedEntity
from .pre_validator import PreValidator, ValidationResult
from .response_builder import ResponseBuilder, StructuredResponse

logger = logging.getLogger(__name__)


# ============================================================================
# Intent Definitions
# ============================================================================


@dataclass
class IntentPattern:
    """意圖模式」"""

    intent: str
    patterns: List[Tuple[str, float]]  # (pattern, base_score)
    required_params: Optional[List[str]] = None  # 修正類型註解
    description: str = ""


# 意圖定義
INTENT_PATTERNS = [
    IntentPattern(
        intent="QUERY_INVENTORY",
        patterns=[
            (r"庫存", 0.8),
            (r"在庫", 0.8),
            (r"手持", 0.75),
            (r"料號", 0.7),
            (r"stock", 0.6),
            (r"inventory", 0.6),
        ],
        required_params=["ITEM_NO", "WAREHOUSE_NO"],
        description="查詢庫存",
    ),
    IntentPattern(
        intent="QUERY_WORK_ORDER",
        patterns=[
            (r"工單", 0.8),
            (r"WO\b", 0.8),
            (r"work order", 0.6),
            (r"製造工單", 0.85),
        ],
        required_params=["MO_DOC_NO"],
        description="查詢工單",
    ),
    IntentPattern(
        intent="QUERY_MANUFACTURING_PROGRESS",
        patterns=[
            (r"製造進捗", 0.9),
            (r"工序進捗", 0.9),
            (r"生產進度", 0.8),
            (r"進度", 0.7),
        ],
        required_params=["MO_DOC_NO"],
        description="查詢製造進度",
    ),
    IntentPattern(
        intent="QUERY_WORKSTATION_OUTPUT",
        patterns=[
            (r"工作站.*生產", 0.9),
            (r"工站.*生產", 0.9),
            (r"WC[0-9]+", 0.9),
            (r"WC[0-9]+-[0-9]+", 0.9),
            (r"哪個.*工作站", 0.85),
            (r"哪些.*工作站", 0.85),
            (r"工作站.*產出", 0.85),
        ],
        required_params=["WORKSTATION"],
        description="查詢工作站產出",
    ),
    IntentPattern(
        intent="QUERY_SHIPPING",
        patterns=[
            (r"出貨", 0.8),
            (r"出荷", 0.8),
            (r"出貨通知", 0.85),
            (r"ship", 0.6),
        ],
        required_params=[],
        description="查詢出貨",
    ),
    IntentPattern(
        intent="QUERY_STATS",
        patterns=[
            (r"統計", 0.7),
            (r"有多少", 0.6),
            (r"數量", 0.5),
            (r"金額", 0.5),
            (r"按.*統計", 0.6),
            (r"按.*分類", 0.6),
        ],
        required_params=[],
        description="統計分析",
    ),
]


# ============================================================================
# Integrated Parser
# =========================================================================---


class IntegratedQueryParser:
    """
    整合式查詢解析器

    整合 EntityExtractor、PreValidator、ResponseBuilder
    提供完整的查詢處理流程
    """

    def __init__(
        self,
        enable_semantic: bool = True,
        similarity_threshold: float = 0.7,
        intent_confidence_threshold: float = 0.6,
    ):
        """
        初始化

        Args:
            enable_semantic: 是否啟用語義匹配
            similarity_threshold: 語義相似度閾值
            intent_confidence_threshold: 意圖信心度閾值
        """
        self.entity_extractor = EntityExtractor(
            enable_semantic=enable_semantic,
            similarity_threshold=similarity_threshold,
        )
        self.prevalidator = PreValidator()
        self.intent_confidence_threshold = intent_confidence_threshold

    def _detect_intent(self, query: str) -> Tuple[str, float]:
        """
        偵測意圖（L1 關鍵詞匹配）

        Args:
            query: 用戶查詢

        Returns:
            Tuple[str, float]: (意圖, 信心度)
        """
        query_lower = query.lower()
        best_intent = None
        best_score = 0

        for intent_pattern in INTENT_PATTERNS:
            for pattern, base_score in intent_pattern.patterns:
                if re.search(pattern, query_lower):
                    # 如果中英文都匹配，增加信心度
                    score = base_score
                    if re.search(pattern, query):  # 精確匹配
                        score += 0.1

                    if score > best_score:
                        best_score = score
                        best_intent = intent_pattern.intent

        if best_intent and best_score >= 0.5:
            return best_intent, min(best_score, 1.0)

        return "UNKNOWN", 0.0

    async def _extract_entities_l2_l3(self, query: str, intent: str) -> Dict[str, str]:
        """
        使用 EntityExtractor 提取實體（L2 正則 + L3 語義）

        Args:
            query: 用戶查詢
            intent: 偵測到的意圖

        Returns:
            Dict[str, str]: 提取的實體 {類型: 值}
        """
        # 使用 EntityExtractor（異步方法）
        all_entities = await self.entity_extractor.extract(query)

        # 過濾出有實際值的實體（排除純關鍵詞標記）
        entities = []
        for entity in all_entities:
            # 排除純關鍵詞標記 [keyword]
            if (
                entity.strategy == "keyword"
                and entity.value.startswith("[")
                and entity.value.endswith("]")
            ):
                continue
            entities.append(entity)

        # 轉換為簡單格式 {類型: 值}
        result = {}
        for entity in entities:
            entity_type = entity.type
            entity_value = entity.value

            # 對於同一類型，保留信心度最高的
            if entity_type in result:
                existing_confidence = result.get(f"_confidence_{entity_type}", 0)
                if entity.confidence > existing_confidence:
                    result[entity_type] = entity_value
                    result[f"_confidence_{entity_type}"] = entity.confidence
            else:
                result[entity_type] = entity_value
                result[f"_confidence_{entity_type}"] = entity.confidence

        # 移除置信度標記
        confidence_markers = [k for k in result if k.startswith("_confidence_")]
        confidence_dict = {k.replace("_confidence_", ""): result[k] for k in confidence_markers}
        result = {k: v for k, v in result.items() if not k.startswith("_confidence_")}

        # 補充置信度資訊
        for entity_type, confidence in confidence_dict.items():
            result[f"_confidence_{entity_type}"] = confidence

        return result

    async def parse(
        self,
        query: str,
        task_id: Optional[str] = None,
    ) -> StructuredResponse:
        """
        解析查詢並返回結構化回應

        Args:
            query: 用戶查詢
            task_id: 任務 ID（可選，自動生成）

        Returns:
            StructuredResponse: 結構化回應
        """
        task_id = task_id or str(uuid.uuid4())
        builder = ResponseBuilder(task_id)

        try:
            # Step 1: 意圖偵測（L1）
            intent, intent_confidence = self._detect_intent(query)

            # Step 2: 實體提取（L2 + L3）
            entities = await self._extract_entities_l2_l3(query, intent)

            # Step 3: 預驗證
            validation_result = await self.prevalidator.validate(
                query=query,
                intent=intent,
                entities=entities,
                intent_confidence=intent_confidence,
            )

            # 如果驗證失敗，返回錯誤回應
            if not validation_result.valid:
                return ResponseBuilder.from_prevalidator_result(
                    task_id=task_id,
                    validation_result=validation_result,
                )

            # 驗證通過，構建成功回應
            return StructuredResponse(
                status="success",
                task_id=task_id,
                metadata={
                    "query": query,
                    "intent": intent,
                    "intent_confidence": intent_confidence,
                    "entities": entities,
                    "timestamp": __import__("time").time(),
                },
            )

        except Exception as e:
            logger.error(f"解析查詢時發生錯誤: {e}", exc_info=True)
            return builder.build_error(
                error_code="INTERNAL_ERROR",
                message="解析查詢時發生錯誤",
                exception=str(e),
            )

    def get_intent_info(self, intent: str) -> Optional[IntentPattern]:
        """獲取意圖資訊」"""
        for pattern in INTENT_PATTERNS:
            if pattern.intent == intent:
                return pattern
        return None

    def get_supported_intents(self) -> List[str]:
        """獲取支援的意圖列表」"""
        return [p.intent for p in INTENT_PATTERNS]


# ============================================================================
# Parser Factory
# ============================================================================


def get_integrated_parser(
    enable_semantic: bool = True,
    similarity_threshold: float = 0.7,
) -> IntegratedQueryParser:
    """獲取整合式解析器」"""
    return IntegratedQueryParser(
        enable_semantic=enable_semantic,
        similarity_threshold=similarity_threshold,
    )


# ============================================================================
# Demo
# ============================================================================


async def demo():
    """演示」"""
    parser = get_integrated_parser(enable_semantic=True, similarity_threshold=0.7)

    test_queries = [
        "能查出工作站WC77 生產那些料號嗎？",
        "我想查詢 8802 倉庫的庫存",
        "工站 WC01-A 生產什麼料號",
        "查詢工單 WO-ABC-12-12345678 的進度",
        "我想查庫存",  # 缺少必要參數
        "所有庫存",  # 範圍過大
    ]

    print("=" * 60)
    print("整合式查詢解析器演示")
    print("=" * 60)

    for query in test_queries:
        print(f"\n查詢: {query}")
        print("-" * 40)

        response = await parser.parse(query)

        import json

        print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))

        print("-" * 40)


if __name__ == "__main__":
    import asyncio

    asyncio.run(demo())
