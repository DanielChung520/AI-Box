# 代碼功能說明: BPA 語義分析器
# 創建日期: 2026-02-06
# 創建人: AI-Box 開發團隊

"""BPA 語義分析器 - 整合所有 Extractors"""

import re
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

from .intent_classifier import IntentClassifier, QueryIntent, TaskComplexity, IntentClassification

logger = logging.getLogger(__name__)


class ExtractionStatus(str, Enum):
    """提取狀態"""

    SUCCESS = "success"
    CLARIFICATION_NEEDED = "clarification_needed"
    NO_MATCH = "no_match"


@dataclass
class EntityExtraction:
    """實體提取結果"""

    entity_type: str
    value: str
    confidence: float = 1.0
    extraction_status: ExtractionStatus = ExtractionStatus.SUCCESS
    clarification_question: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    time_value: Optional[str] = None  # 用於時間提取的原始值


@dataclass
class SemanticAnalysis:
    """語義分析結果"""

    intent: QueryIntent
    complexity: TaskComplexity
    material_id: Optional[str] = None
    warehouse: Optional[str] = None
    time_type: Optional[str] = None
    time_value: Optional[str] = None
    transaction_type: Optional[str] = None
    material_category: Optional[str] = None
    confidence: float = 1.0
    needs_clarification: bool = False
    clarification_issues: List[Dict] = field(default_factory=list)
    raw_extractions: Dict[str, Any] = field(default_factory=dict)


class BPASemanticAnalyzer:
    """BPA 語義分析器

    整合所有 Extractors 進行語義分析：
    - TimeExtractor: 時間提取
    - MaterialCategoryExtractor: 物料類別提取
    - WarehouseExtractor: 倉庫提取
    - 料號正則提取
    - 交易類型提取

    澄清機制：
    - 模糊時間 → 回問用戶
    - 模糊物料 → 回問用戶
    - 缺失必填 → 回問用戶
    """

    def __init__(self):
        """初始化語義分析器"""
        self._intent_classifier = IntentClassifier()
        self._init_extractors()

    def _init_extractors(self):
        """初始化 Extractors"""
        try:
            from mm_agent.time_extractor import TimeExtractor

            self._time_extractor = TimeExtractor()
        except ImportError:
            self._time_extractor = None

        try:
            from mm_agent.material_category_extractor import MaterialCategoryExtractor

            self._material_extractor = MaterialCategoryExtractor()
        except ImportError:
            self._material_extractor = None

        try:
            from mm_agent.warehouse_extractor import WarehouseExtractor

            self._warehouse_extractor = WarehouseExtractor()
        except ImportError:
            self._warehouse_extractor = None

    def analyze(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict]] = None,
    ) -> SemanticAnalysis:
        """執行語義分析

        Args:
            user_input: 用戶輸入
            context: 上下文（用於指代消解）
            conversation_history: 對話歷史

        Returns:
            SemanticAnalysis: 語義分析結果
        """
        # 步驟 1: 意圖分類
        intent_result = self._intent_classifier.classify(user_input, context)

        # 步驟 2: 提取實體
        extractions = self._extract_entities(user_input)

        # 步驟 3: 檢查澄清需求
        clarification_issues = self._check_clarification_needed(
            intent=intent_result.intent,
            extractions=extractions,
            context=context,
        )

        # 步驟 4: 生成語義分析結果
        # 安全獲取 extraction 值
        material_id_ext = extractions.get("material_id")
        material_id_val = material_id_ext.value if material_id_ext else None

        warehouse_ext = extractions.get("warehouse")
        warehouse_val = warehouse_ext.value if warehouse_ext else None

        time_ext = extractions.get("time_type")
        time_type_val = time_ext.value if time_ext else None
        time_value_val = (
            time_ext.time_value
            if time_ext and hasattr(time_ext, "time_value") and time_ext.time_value
            else None
        )

        transaction_ext = extractions.get("transaction_type")
        transaction_val = transaction_ext.value if transaction_ext else None

        category_ext = extractions.get("material_category")
        category_val = category_ext.value if category_ext else None

        analysis = SemanticAnalysis(
            intent=intent_result.intent,
            complexity=intent_result.complexity,
            material_id=material_id_val,
            warehouse=warehouse_val,
            time_type=time_type_val,
            time_value=time_value_val,
            transaction_type=transaction_val,
            material_category=category_val,
            confidence=intent_result.confidence,
            needs_clarification=len(clarification_issues) > 0,
            clarification_issues=clarification_issues,
            raw_extractions={k: v.__dict__ for k, v in extractions.items()},
        )

        return analysis

    def _extract_entities(self, text: str) -> Dict[str, EntityExtraction]:
        """提取所有實體"""
        extractions = {}

        # 優先檢查：倉庫代碼 + 倉庫關鍵詞（如 W01 倉庫）
        # 注意：不用 \b 單詞邊界，因為中文環境下會有問題
        warehouse_pattern = r"(W\d{2})(?!\d)"
        warehouse_match = re.search(warehouse_pattern, text, re.IGNORECASE)

        if warehouse_match and any(kw in text for kw in ["倉庫", "倉", "庫", "區"]):
            # W01 倉庫 → 識別為倉庫
            w_code = warehouse_match.group(1)  # 完整代碼如 W01
            extractions["warehouse"] = EntityExtraction(
                entity_type="warehouse",
                value=w_code,
                confidence=0.95,
                extraction_status=ExtractionStatus.SUCCESS,
            )
            # 跳過時間提取，避免 W01 被識別為週
            logger.info(f"[SemanticAnalyzer] W01 識別為倉庫: {w_code}")

        # 提取料號
        material_id = self._extract_material_id(text)
        if material_id:
            extractions["material_id"] = material_id

        # 如果已經提取了倉庫，跳過時間提取
        if "warehouse" not in extractions:
            time_extraction = self._extract_time(text)
            if time_extraction:
                extractions["time_type"] = time_extraction

        # 如果還沒有倉庫，使用 WarehouseExtractor
        if "warehouse" not in extractions:
            warehouse_extraction = self._extract_warehouse(text)
            if warehouse_extraction:
                extractions["warehouse"] = warehouse_extraction

        # 提取交易類型
        transaction_extraction = self._extract_transaction_type(text)
        if transaction_extraction:
            extractions["transaction_type"] = transaction_extraction

        # 提取物料類別
        category_extraction = self._extract_material_category(text)
        if category_extraction:
            extractions["material_category"] = category_extraction

        return extractions

    def _extract_material_id(self, text: str) -> Optional[EntityExtraction]:
        """提取料號"""
        pattern = r"([A-Z]{2,4}-?\d{2,6}(?:-\d{2,6})?)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return EntityExtraction(
                entity_type="material_id",
                value=match.group(1).upper(),
                confidence=1.0,
            )
        return None

    def _extract_time(self, text: str) -> Optional[EntityExtraction]:
        """提取時間"""
        if not self._time_extractor:
            return self._fallback_extract_time(text)

        # 使用 TimeExtractor
        match, clarification = self._time_extractor.extract_with_clarification(text)

        if clarification.need_clarification:
            return EntityExtraction(
                entity_type="time_type",
                value="",
                confidence=0.5,
                extraction_status=ExtractionStatus.CLARIFICATION_NEEDED,
                clarification_question=clarification.question,
                suggestions=clarification.suggestions,
            )

        if match:
            return EntityExtraction(
                entity_type="time_type",
                value=match.time_type,
                confidence=1.0,
                extraction_status=ExtractionStatus.SUCCESS,
            )

        return None

    def _fallback_extract_time(self, text: str) -> Optional[EntityExtraction]:
        """備用時間提取"""
        time_patterns = {
            "specific_date": [r"(\d{4}-\d{2}-\d{2})", r"(\d{4}/\d{2}/\d{2})"],
            "date_range": [r"(\d{4}-\d{2}-\d{2})\s*[至到]\s*(\d{4}-\d{2}-\d{2})"],
            "last_month": ["上月", "上個月"],
            "this_month": ["本月", "這個月"],
            "last_year": ["去年"],
            "this_year": ["今年"],
        }

        for time_type, patterns in time_patterns.items():
            if isinstance(patterns, list):
                for pattern in patterns:
                    if re.search(pattern, text):
                        return EntityExtraction(
                            entity_type="time_type",
                            value=time_type,
                            confidence=0.8,
                        )
            else:
                if patterns in text:
                    return EntityExtraction(
                        entity_type="time_type",
                        value=time_type,
                        confidence=0.8,
                    )

        return None

    def _extract_warehouse(self, text: str) -> Optional[EntityExtraction]:
        """提取倉庫"""
        if not self._warehouse_extractor:
            return self._fallback_extract_warehouse(text)

        # 使用 WarehouseExtractor
        match, clarification = self._warehouse_extractor.extract_with_clarification(text)

        if clarification.need_clarification:
            return EntityExtraction(
                entity_type="warehouse",
                value="",
                confidence=0.5,
                extraction_status=ExtractionStatus.CLARIFICATION_NEEDED,
                clarification_question=clarification.question,
                suggestions=clarification.suggestions,
            )

        if match:
            return EntityExtraction(
                entity_type="warehouse",
                value=match.warehouse_code,
                confidence=1.0,
            )

        return None

    def _fallback_extract_warehouse(self, text: str) -> Optional[EntityExtraction]:
        """備用倉庫提取"""
        warehouse_keywords = {
            "RAW01": ["原料倉", "原材料"],
            "FIN01": ["成品倉", "成品"],
            "PKG01": ["包裝倉", "包材"],
        }

        for code, keywords in warehouse_keywords.items():
            if any(kw in text for kw in keywords):
                return EntityExtraction(
                    entity_type="warehouse",
                    value=code,
                    confidence=0.8,
                )

        return None

    def _extract_transaction_type(self, text: str) -> Optional[EntityExtraction]:
        """提取交易類型"""
        transaction_keywords = {
            "101": ["採購", "買進", "進貨", "收料"],
            "102": ["入庫", "完工入庫"],
            "201": ["領料", "生產領料"],
            "202": ["銷售", "賣出", "出貨"],
            "301": ["報廢", "報損"],
        }

        for code, keywords in transaction_keywords.items():
            if any(kw in text for kw in keywords):
                return EntityExtraction(
                    entity_type="transaction_type",
                    value=code,
                    confidence=1.0,
                )

        return None

    def _extract_material_category(self, text: str) -> Optional[EntityExtraction]:
        """提取物料類別"""
        if not self._material_extractor:
            return self._fallback_extract_category(text)

        # 使用 MaterialCategoryExtractor
        match, clarification = self._material_extractor.extract_with_clarification(text)

        if clarification.need_clarification:
            return EntityExtraction(
                entity_type="material_category",
                value="",
                confidence=0.5,
                extraction_status=ExtractionStatus.CLARIFICATION_NEEDED,
                clarification_question=clarification.question,
                suggestions=clarification.suggestions,
            )

        if match:
            return EntityExtraction(
                entity_type="material_category",
                value=match.category_code,
                confidence=1.0,
            )

        return None

    def _fallback_extract_category(self, text: str) -> Optional[EntityExtraction]:
        """備用類別提取"""
        category_keywords = {
            "plastic": ["塑料", "塑膠"],
            "metal": ["金屬", "五金"],
            "electronic": ["電子", "電路"],
            "raw": ["原料", "原材料"],
            "finished": ["成品", "製成品"],
        }

        for code, keywords in category_keywords.items():
            if any(kw in text for kw in keywords):
                return EntityExtraction(
                    entity_type="material_category",
                    value=code,
                    confidence=0.8,
                )

        return None

    def _check_clarification_needed(
        self,
        intent: QueryIntent,
        extractions: Dict[str, EntityExtraction],
        context: Optional[Dict],
    ) -> List[Dict]:
        """檢查是否需要澄清"""
        issues = []

        # 必填字段檢查（按意圖類型）
        # QUERY_STOCK: 倉庫庫存可以不指定料號（查整倉總量）
        required_fields = {
            QueryIntent.QUERY_STOCK: [],
            QueryIntent.QUERY_PURCHASE: ["material_id"],
            QueryIntent.QUERY_SALES: ["material_id"],
            QueryIntent.ANALYZE_SHORTAGE: ["material_category"],
            QueryIntent.GENERATE_ORDER: ["material_id"],
        }

        required = required_fields.get(intent, [])

        for field in required:
            extraction = extractions.get(field)
            if not extraction or not extraction.value:
                if (
                    extraction
                    and extraction.extraction_status == ExtractionStatus.CLARIFICATION_NEEDED
                ):
                    issues.append(
                        {
                            "field": field,
                            "type": "extraction_clarification",
                            "question": extraction.clarification_question,
                            "suggestions": extraction.suggestions,
                        }
                    )
                else:
                    issues.append(
                        {
                            "field": field,
                            "type": "missing",
                            "question": f"請提供{field}",
                        }
                    )

        # 已有上下文時，不需要澄清
        if context and not issues:
            return []

        return issues

    def get_supported_intents(self) -> List[str]:
        """獲取支持的意圖類型"""
        return [e.value for e in QueryIntent]

    def get_required_fields(self, intent: str) -> List[str]:
        """獲取意圖的必填字段"""
        intent_enum = QueryIntent(intent)
        required_fields = {
            QueryIntent.QUERY_STOCK: [],
            QueryIntent.QUERY_PURCHASE: ["material_id"],
            QueryIntent.QUERY_SALES: ["material_id"],
            QueryIntent.ANALYZE_SHORTAGE: ["material_category"],
            QueryIntent.GENERATE_ORDER: ["material_id"],
        }
        return required_fields.get(intent_enum, [])
