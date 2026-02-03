#!/usr/bin/env python3
"""
意圖分析服務

功能：
1. 完整性檢查 - 確認查詢是否包含必要資訊
2. Tokenization - 分詞處理
3. 意圖識別 - 識別模糊詞彙並轉換為精確意圖
4. 語義描述 - 生成精確的查詢描述
5. RAG 整合 - 使用向量資料庫增強意圖識別

使用方式：
    from data_agent.intent_analyzer import IntentAnalyzer

    analyzer = IntentAnalyzer()
    result = analyzer.analyze("查W01庫房每個料號存量")
"""

import re
import requests
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance


class QueryIntent(Enum):
    """查詢意圖類型"""

    QUERY_INVENTORY = "query_inventory"
    QUERY_ORDER = "query_order"
    QUERY_PRICE = "query_price"
    QUERY_TRANSACTION = "query_transaction"
    QUERY_ITEM = "query_item"
    CALCULATE_SUM = "calculate_sum"
    CALCULATE_AVG = "calculate_avg"
    CALCULATE_COUNT = "calculate_count"
    CALCULATE_MAX = "calculate_max"
    CALCULATE_MIN = "calculate_min"
    STATISTICS = "statistics"
    UNKNOWN = "unknown"


RAG_CONFIG = {
    "qdrant_url": "http://localhost:6333",
    "collection_name": "data_agent_intents",
    "embedding_endpoint": "http://localhost:11434/api/embeddings",
    "embedding_model": "qwen3-embedding:latest",
    "vector_dim": 4096,
    "similarity_threshold": 0.75,
}


class TimeGranularity(Enum):
    """時間粒度"""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    RANGE = "range"
    NONE = "none"


@dataclass
class Token:
    """分詞結果"""

    word: str
    pos: str  # 詞性
    meaning: str = ""  # 語義
    is_ambiguous: bool = False  # 是否為模糊詞彙


@dataclass
class IntentAnalysisResult:
    """意圖分析結果"""

    original_query: str
    tokens: List[Token] = field(default_factory=list)

    query_intent: QueryIntent = QueryIntent.UNKNOWN
    intent_description: str = ""
    table: str = ""
    subject: str = ""
    subject_value: str = ""
    warehouse: str = ""
    warehouse_condition: str = ""

    aggregation: str = ""
    has_group_by: bool = False
    group_by_field: str = ""
    has_order_by: bool = False
    order_by_field: str = ""
    order_direction: str = ""
    limit: int = 0

    has_time_filter: bool = False
    time_granularity: TimeGranularity = TimeGranularity.NONE
    time_start: str = ""
    time_end: str = ""

    is_complete: bool = True
    missing_info: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    precise_description: str = ""

    rag_score: float = 0.0
    rag_matched_template: str = ""
    used_rag: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "query_intent": self.query_intent.value,
            "intent_description": self.intent_description,
            "table": self.table,
            "subject": self.subject,
            "subject_value": self.subject_value,
            "warehouse": self.warehouse,
            "aggregation": self.aggregation,
            "has_group_by": self.has_group_by,
            "is_complete": self.is_complete,
            "missing_info": self.missing_info,
            "precise_description": self.precise_description,
            "rag_score": self.rag_score,
            "rag_matched_template": self.rag_matched_template,
            "used_rag": self.used_rag,
        }


class IntentAnalyzer:
    """意圖分析器"""

    def __init__(self):
        from data_agent.code_dictionary import CodeDictionary

        self._rag_client = None
        self._rag_initialized = False
        self.code_dict = CodeDictionary()

        self.ambiguous_mappings = {
            # 數量相關
            "總計": {"agg": "SUM", "meaning": "計算總和"},
            "總共": {"agg": "SUM", "meaning": "計算總和"},
            "總量": {"agg": "SUM", "meaning": "計算總和"},
            "總數": {"agg": "SUM", "meaning": "計算總和"},
            "合計": {"agg": "SUM", "meaning": "計算總和"},
            # 平均相關
            "平均": {"agg": "AVG", "meaning": "計算平均值"},
            "均": {"agg": "AVG", "meaning": "計算平均值"},
            # 數量相關
            "幾個": {"agg": "COUNT", "meaning": "計算數量"},
            "多少筆": {"agg": "COUNT", "meaning": "計算筆數"},
            "筆數": {"agg": "COUNT", "meaning": "計算筆數"},
            "有幾筆": {"agg": "COUNT", "meaning": "計算筆數"},
            # 最大最小
            "最多": {"agg": "MAX", "meaning": "找出最大值"},
            "最高": {"agg": "MAX", "meaning": "找出最大值"},
            "最大": {"agg": "MAX", "meaning": "找出最大值"},
            "最少": {"agg": "MIN", "meaning": "找出最小值"},
            "最低": {"agg": "MIN", "meaning": "找出最小值"},
            "最小": {"agg": "MIN", "meaning": "找出最小值"},
            # 排序相關
            "前幾筆": {"order": "DESC", "limit": 5, "meaning": "取前 N 筆"},
            "前十名": {"order": "DESC", "limit": 10, "meaning": "取前 10 名"},
            "前五名": {"order": "DESC", "limit": 5, "meaning": "取前 5 名"},
            "最後": {"order": "ASC", "limit": 1, "meaning": "取最後一筆"},
            "最新": {"order": "DESC", "limit": 1, "meaning": "取最新一筆"},
            # 庫存相關
            "庫存量": {"field": "img10", "meaning": "庫存數量欄位"},
            "庫存": {"table": "img_file", "meaning": "庫存表"},
            "存量": {"field": "img10", "meaning": "庫存數量"},
            "料號": {"field": "img01", "meaning": "料號欄位"},
            "品名": {"field": "ima02", "meaning": "品名欄位"},
            "庫房": {"meaning": "倉庫"},
            "每個": {"meaning": "分組查詢"},
        }

        # 倉庫代碼映射
        self.warehouse_patterns = [
            (r"W0[1-5]", "W01", "W02", "W03", "W04", "W05"),
            (r"原料倉", "W01", "原料倉庫"),
            (r"成品倉", "W03", "成品倉庫"),
            (r"半成品倉", "W02", "半成品倉庫"),
        ]

        self.table_keywords = {
            "img_file": ["庫存", "存量", "倉", "w0", "w1", "w2", "w3"],
            "ima_file": ["品名", "規格", "料件", "物料"],
            "tlf_file": [
                "交易",
                "異動",
                "採購",
                "進貨",
                "收料",
                "收貨",
                "出庫",
                "入庫",
                "領料",
                "報廢",
            ],
            "coptc_file": ["訂單", "出貨", "客戶"],
            "coptd_file": ["訂單明細", "訂單項目"],
            "prc_file": ["單價", "價格", "訂價"],
            "pmm_file": ["採購單", "採購"],
            "pmn_file": ["採購單身", "採購明細"],
            "rvb_file": ["收料單", "收料"],
            "cmc_file": ["客戶主檔", "客戶"],
            "pmc_file": ["供應商", "Vendor"],
        }

    def _init_rag_client(self):
        """初始化 RAG 客戶端"""
        if self._rag_initialized:
            return

        try:
            self._rag_client = QdrantClient(url=RAG_CONFIG["qdrant_url"])
            self._rag_initialized = True
        except Exception as e:
            self._rag_client = None

    def _get_embedding(self, text: str):
        """獲取文本嵌入向量"""
        try:
            payload = {"model": RAG_CONFIG["embedding_model"], "prompt": text}
            response = requests.post(RAG_CONFIG["embedding_endpoint"], json=payload, timeout=60)
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception:
            return None

    def query_rag(self, query: str, top_k: int = 3):
        """查詢 RAG 系統"""
        self._init_rag_client()

        if not self._rag_client:
            return []

        try:
            embedding = self._get_embedding(query)
            if not embedding:
                return []

            results = self._rag_client.query_points(
                collection_name=RAG_CONFIG["collection_name"], query=embedding, limit=top_k
            )

            rag_results = []
            for r in results.points:
                if r.payload:
                    payload = dict(r.payload) if hasattr(r.payload, "items") else r.payload
                    rag_results.append(
                        {
                            "query": str(payload.get("query", "")),
                            "sql": str(payload.get("sql", "")),
                            "type": str(payload.get("type", "")),
                            "score": r.score,
                        }
                    )

            return rag_results
        except Exception:
            return []

    def tokenize(self, query: str) -> List[Token]:
        """分詞處理 - 支援中英文混合查詢"""
        tokens = []

        # 清理查詢
        query = query.strip()

        # 移除常見的查詢開頭詞
        prefix_patterns = [
            r"^查詢\s*",
            r"^查\s*",
            r"^看\s*",
            r"^顯示\s*",
            r"^列出\s*",
            r"^找\s*",
        ]
        for pattern in prefix_patterns:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE)

        # 分割中英文和數字
        # 使用更智能的分詞：按詞彙模式匹配
        pattern = r"([Ww]0[1-5])|\b(\d{2}-\d{4})\b|(\d{4}[年/\-]\d{1,2}[月/\-]?\d{0,2})|([^\s]+)"
        matches = re.findall(pattern, query)

        words = []
        for match in matches:
            # match 是 tuple，取非空的部分
            word = next((m for m in match if m), "")
            if word:
                words.append(word)

        for word in words:
            if not word:
                continue

            token = Token(word=word, pos=self._guess_pos(word), meaning="", is_ambiguous=False)

            # 檢查是否為模糊詞彙
            if word in self.ambiguous_mappings:
                mapping = self.ambiguous_mappings[word]
                token.is_ambiguous = True
                token.meaning = mapping.get("meaning", "")
            else:
                # 檢查是否包含模糊詞彙
                for amb_word, mapping in self.ambiguous_mappings.items():
                    if amb_word in word:
                        token.is_ambiguous = True
                        token.meaning = mapping.get("meaning", "")
                        break

            tokens.append(token)

        return tokens

    def _guess_pos(self, word: str) -> str:
        """猜測詞性"""
        # 數字
        if re.match(r"^\d+$", word):
            return "NUMBER"

        # 日期
        if re.match(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", word):
            return "DATE"

        # 料號格式
        if re.match(r"^\d{2}-\d{4}$", word) or re.match(r"^RM\d{2}-\d{3}$", word):
            return "ITEM_CODE"

        # 倉庫代碼
        if re.match(r"^W0[1-5]$", word, re.IGNORECASE):
            return "WAREHOUSE"

        # 關鍵詞
        if word in ["查詢", "找", "看", "顯示"]:
            return "VERB_QUERY"

        return "UNKNOWN"

    def analyze(self, query: str, use_rag_fallback: bool = True) -> IntentAnalysisResult:
        """完整意圖分析（支持 RAG 混合模式）"""
        result = IntentAnalysisResult(original_query=query)

        result.tokens = self.tokenize(query)

        self._recognize_intent(query, result)

        self._recognize_entities(query, result)

        self._recognize_aggregation(query, result)

        self._recognize_time_filter(query, result)

        self._check_completeness(result)

        self._generate_precise_description(result)

        if use_rag_fallback:
            self._apply_rag_fallback(query, result)

        return result

    def _apply_rag_fallback(self, query: str, result: IntentAnalysisResult):
        """應用 RAG 作為規則引擎的 fallback"""
        rag_results = self.query_rag(query, top_k=1)

        if not rag_results:
            return

        best_match = rag_results[0]
        similarity = best_match["score"]

        result.rag_score = similarity
        result.rag_matched_template = best_match["query"]

        if similarity >= RAG_CONFIG["similarity_threshold"]:
            result.used_rag = True
            result.warnings.append(
                f"🤖 RAG 匹配 (相似度: {similarity:.2%}): 「{best_match['query']}」"
            )

            if best_match["sql"]:
                result.precise_description += f" | RAG-SQL: {best_match['sql']}"

    def _recognize_intent(self, query: str, result: IntentAnalysisResult):
        """識別主要意圖"""
        query_lower = query.lower()

        # 庫存相關意圖
        if any(kw in query_lower for kw in ["庫存", "存量", "倉庫", "w0", "w1", "w2", "w3"]):
            if any(kw in query_lower for kw in ["總計", "合計", "總量", "平均", "統計"]):
                result.query_intent = QueryIntent.STATISTICS
                result.intent_description = "統計庫存"
            else:
                result.query_intent = QueryIntent.QUERY_INVENTORY
                result.intent_description = "查詢庫存"

        # 採購交易相關意圖（需在訂單之前判斷）
        elif any(kw in query_lower for kw in ["採購", "進貨", "收料", "收貨"]):
            result.query_intent = QueryIntent.QUERY_TRANSACTION
            result.intent_description = "查詢採購交易"
            result.table = "tlf_file"

        # 交易相關意圖
        elif any(kw in query_lower for kw in ["交易", "異動"]):
            result.query_intent = QueryIntent.QUERY_TRANSACTION
            result.intent_description = "查詢交易記錄"
            result.table = "tlf_file"

        # 訂單相關意圖
        elif any(kw in query_lower for kw in ["訂單", "出貨", "客戶"]):
            result.query_intent = QueryIntent.QUERY_ORDER
            result.intent_description = "查詢訂單"
            result.table = "coptc_file"

        # 價格相關意圖
        elif any(kw in query_lower for kw in ["單價", "價格", "訂價"]):
            result.query_intent = QueryIntent.QUERY_PRICE
            result.intent_description = "查詢價格"
            result.table = "prc_file"

        # 計算相關意圖
        elif any(kw in query_lower for kw in ["總計", "合計", "總量", "總數"]):
            result.query_intent = QueryIntent.CALCULATE_SUM
            result.intent_description = "計算總和"
        elif "平均" in query_lower:
            result.query_intent = QueryIntent.CALCULATE_AVG
            result.intent_description = "計算平均值"
        elif any(kw in query_lower for kw in ["多少筆", "幾個", "筆數"]):
            result.query_intent = QueryIntent.CALCULATE_COUNT
            result.intent_description = "計算數量"
        elif any(kw in query_lower for kw in ["最高", "最多", "最大"]):
            result.query_intent = QueryIntent.CALCULATE_MAX
            result.intent_description = "計算最大值"
        elif any(kw in query_lower for kw in ["最低", "最少", "最小"]):
            result.query_intent = QueryIntent.CALCULATE_MIN
            result.intent_description = "計算最小值"

        else:
            result.query_intent = QueryIntent.QUERY_INVENTORY
            result.intent_description = "一般查詢"

    def _recognize_entities(self, query: str, result: IntentAnalysisResult):
        """識別實體（表、欄位、值）- 整合 CodeDictionary"""
        query_upper = query.upper()
        query_lower = query.lower()

        for table, keywords in self.table_keywords.items():
            if any(kw.upper() in query_upper for kw in keywords):
                result.table = table
                break

        if not result.table:
            if result.query_intent in [QueryIntent.QUERY_INVENTORY, QueryIntent.STATISTICS]:
                result.table = "img_file"
            elif result.query_intent == QueryIntent.QUERY_ORDER:
                result.table = "coptc_file"
            elif result.query_intent == QueryIntent.QUERY_PRICE:
                result.table = "prc_file"

        item_codes = re.findall(r"\b\d{6}\b", query)
        if item_codes:
            result.warnings.append(
                f"料號格式可能錯誤：{item_codes[0]}（正確格式：XX-XXXX，如 10-0001）"
            )

        item_codes_valid = re.findall(r"\b\d{2}-\d{4}\b", query)
        if item_codes_valid:
            for code in item_codes_valid:
                if re.match(r"^\d{2}-\d{4}$", code):
                    result.subject = "item_code"
                    result.subject_value = code
                    break

        warehouse_match = re.search(r"[Ww]0([1-5])", query)
        if warehouse_match:
            warehouse_num = warehouse_match.group(1)
            code = f"W0{warehouse_num}"
            result.warehouse = code

            code_info = self.code_dict.lookup(code)
            if code_info:
                warehouse_name = code_info.get("name", code_info.get("type", ""))
                result.warnings.append(f"📖 代碼字典：{code} → {warehouse_name}")

                if not result.table:
                    result.table = code_info.get("table", "img_file")

            warehouse_context_keywords = ["庫存", "存量", "庫房", "倉庫", "存貨", "料號", "物料"]
            has_context = any(kw in query_lower for kw in warehouse_context_keywords)

            if not has_context:
                result.warnings.append(
                    f"⚠️ 已根據上下文識別為倉庫代碼：{code}（建議明確指定「倉庫」或「庫房」）"
                )
        else:
            error_warehouse = re.search(r"[Ww]0([06-9])", query)
            if error_warehouse:
                invalid_code = f"W0{error_warehouse.group(1)}"
                result.warnings.append(f"倉庫代碼無效：{invalid_code}（正確格式：W01-W05）")

        if re.search(r"[Ww]0[1-5].*[,，].*[Ww]0[1-5]", query):
            warehouses = re.findall(r"([Ww])0([1-5])", query)
            result.warehouse_condition = "IN"

    def _recognize_aggregation(self, query: str, result: IntentAnalysisResult):
        """識別聚合/計算意圖"""
        query_lower = query.lower()

        # 識別「各倉庫」- 按倉庫分組統計
        if "各倉庫" in query_lower:
            result.has_group_by = True
            result.group_by_field = "img02"
            result.warehouse = "各倉庫"
            # 如果沒有指定聚合，預設為 SUM
            if not result.aggregation:
                result.aggregation = "SUM"

        # 識別聚合函數
        if any(kw in query_lower for kw in ["總計", "合計", "總量", "總數", "總"]):
            result.aggregation = "SUM"
            if not result.has_group_by:
                # 根據上下文決定分組欄位
                if "各倉庫" in query_lower:
                    result.group_by_field = "img02"
                else:
                    result.has_group_by = True
                    result.group_by_field = "img01"
        elif "平均" in query_lower:
            result.aggregation = "AVG"
            if not result.has_group_by:
                if "各倉庫" in query_lower:
                    result.group_by_field = "img02"
                else:
                    result.has_group_by = True
        elif any(kw in query_lower for kw in ["多少筆", "幾個", "筆數"]):
            result.aggregation = "COUNT"
            if not result.has_group_by:
                if "各倉庫" in query_lower:
                    result.group_by_field = "img02"
                else:
                    result.has_group_by = True
        elif any(kw in query_lower for kw in ["最高", "最多", "最大"]):
            result.aggregation = "MAX"
        elif any(kw in query_lower for kw in ["最低", "最少", "最小"]):
            result.aggregation = "MIN"

        # 識別「每個」- 表示需要分組查詢
        if "每個" in query_lower and not result.has_group_by:
            result.has_group_by = True
            result.group_by_field = "img01"
            if not result.aggregation:
                result.aggregation = "SUM"

        # 識別排序
        if any(kw in query_lower for kw in ["前", "最多", "最高", "最大"]):
            result.has_order_by = True
            result.order_by_field = "img10"
            result.order_direction = "DESC"
            limit_match = re.search(r"前(\d+)個", query)
            if limit_match:
                result.limit = int(limit_match.group(1))
            else:
                result.limit = 10
        elif any(kw in query_lower for kw in ["後", "最少", "最低", "最小"]):
            result.has_order_by = True
            result.order_by_field = "img10"
            result.order_direction = "ASC"

    def _recognize_time_filter(self, query: str, result: IntentAnalysisResult):
        """識別時間過濾"""
        # 簡單的時間模式匹配
        year_month = re.search(r"(\d{4})[年/\-](\d{1,2})", query)
        if year_month:
            result.has_time_filter = True
            result.time_granularity = TimeGranularity.MONTH
            result.time_start = f"{year_month.group(1)}-{year_month.group(2).zfill(2)}-01"

        # 查詢「最近」
        if "最近" in query:
            day_match = re.search(r"最近(\d+)天", query)
            if day_match:
                result.has_time_filter = True
                result.time_granularity = TimeGranularity.DAY
                result.time_start = f"-{day_match.group(1)} days"

    def _check_completeness(self, result: IntentAnalysisResult):
        """完整性檢查"""
        # 檢查必要欄位
        if result.query_intent == QueryIntent.QUERY_INVENTORY:
            if not result.table:
                result.missing_info.append("未識別到查詢的資料表")
            if result.aggregation:
                pass
            else:
                if not result.subject_value and not result.warehouse:
                    result.warnings.append("未指定具體的料號或倉庫，可能返回大量數據")

        # 檢查危險操作
        query = result.original_query.lower()
        dangerous_keywords = ["drop", "delete", "truncate", "update", "insert"]
        if any(kw in query for kw in dangerous_keywords):
            result.is_complete = False
            result.missing_info.append("檢測到危險關鍵字，請確認是否為誤操作")

        # 檢查是否有格式警告（倉庫代碼無效、料號格式錯誤等）
        format_warnings = [w for w in result.warnings if "無效" in w]
        if format_warnings:
            result.is_complete = False
            for w in format_warnings:
                result.missing_info.append(w)

        # 設定完整性
        result.is_complete = len(result.missing_info) == 0

    def _generate_precise_description(self, result: IntentAnalysisResult):
        """生成精確描述"""
        parts = []

        # 意圖
        parts.append(f"意圖：{result.intent_description}")

        # 查詢表
        if result.table:
            parts.append(f"資料表：{result.table}")

        # 聚合
        if result.aggregation:
            agg_map = {
                "SUM": "計算總和",
                "AVG": "計算平均值",
                "COUNT": "計算數量",
                "MAX": "找出最大值",
                "MIN": "找出最小值",
            }
            parts.append(f"聚合方式：{agg_map.get(result.aggregation, result.aggregation)}")

            if result.has_group_by and result.group_by_field:
                parts.append(f"分組依據：{result.group_by_field}")

        # 篩選條件
        filters = []
        if result.warehouse:
            if result.warehouse_condition == "IN":
                filters.append(f"倉庫 IN ({result.warehouse})")
            else:
                filters.append(f"倉庫 = {result.warehouse}")
        if result.subject_value:
            filters.append(f"料號 = {result.subject_value}")

        if filters:
            parts.append(f"篩選條件：{' AND '.join(filters)}")

        # 排序
        if result.has_order_by:
            direction = "降序" if result.order_direction == "DESC" else "升序"
            parts.append(f"排序：{result.order_by_field} {direction}")
            if result.limit:
                parts.append(f"限制：取前 {result.limit} 筆")

        # 時間
        if result.has_time_filter:
            parts.append(f"時間範圍：{result.time_granularity.value}")

        # 警告
        if result.warnings:
            parts.append(f"⚠️ 警告：{'；'.join(result.warnings)}")

        result.precise_description = " | ".join(parts)


# 測試
if __name__ == "__main__":
    analyzer = IntentAnalyzer()

    test_queries = [
        "查W01 庫房每個料號存量",
        "計算料號 10-0001 的總庫存量",
        "查詢各倉庫的平均庫存量",
        "列出前 10 個庫存最多的物料",
        "統計 2025 年 1 月的交易筆數",
    ]

    for query in test_queries:
        print("=" * 60)
        print(f"查詢：{query}")
        print("=" * 60)

        result = analyzer.analyze(query)

        print(f"\n分詞結果：")
        for token in result.tokens:
            amb = " ⚠️" if token.is_ambiguous else ""
            print(f"  - {token.word} ({token.pos}){amb}")

        print(f"\n意圖分析：")
        print(f"  - 意圖類型：{result.query_intent.value}")
        print(f"  - 意圖描述：{result.intent_description}")
        print(f"  - 資料表：{result.table}")
        print(f"  - 聚合：{result.aggregation}")
        print(f"  - 倉庫：{result.warehouse}")
        print(f"  - 分組：{result.has_group_by} ({result.group_by_field})")
        print(f"  - 排序：{result.has_order_by} {result.order_direction} {result.limit}")
        print(f"  - 完整性：{'✅ 完整' if result.is_complete else '❌ 不完整'}")
        if result.warnings:
            print(f"  - 警告：{'；'.join(result.warnings)}")

        print(f"\n精確描述：")
        print(f"  {result.precise_description}")
        print()
