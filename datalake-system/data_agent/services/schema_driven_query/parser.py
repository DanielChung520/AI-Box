# -*- coding: utf-8 -*-
"""
Data-Agent-JP NLQ 解析器

功能：
- 解析自然語言查詢（NLQ）
- 識別意圖和參數
- 支援 Master Data Validation
- 新增分頁功能（LIMIT/OFFSET）
- 新增 LLM 回應快取

建立日期: 2026-02-10
建立人: Daniel Chung
最後修改日期: 2026-02-14
"""

import json
import logging
import re
import httpx
import hashlib
import time
from typing import Dict, Any, Optional, List
from collections import OrderedDict
from threading import Lock

from .config import get_config, LLMConfig
from .models import ParsedIntent, IntentDefinition, IntentsContainer
from .master_loader import MasterDataLoader, get_master_loader
from .exceptions import (
    ItemNotFoundError,
    WarehouseNotFoundError,
    WorkstationNotFoundError,
    ValidationError,
)

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


class PaginationExtractor:
    """分頁參數提取器"""

    @staticmethod
    def extract(nlq: str, default_limit: int = 100) -> Dict[str, int]:
        """
        從 NLQ 中提取分頁參數

        Args:
            nlq: 自然語言查詢
            default_limit: 預設 LIMIT 值

        Returns:
            Dict: {"limit": int, "offset": int}
        """
        result: Dict[str, int] = {"limit": default_limit, "offset": 0}
        found_limit = False

        limit_patterns = [
            (r"限制.*?(?:每.*?(?:頁|面|顯示))?.*?(\d+).*?(?:條|筆|筆資料)?", "normal"),
            (r"只.*?顯.*?示.*?(\d+).*?(?:條|筆|筆資料)?", "normal"),
            (r"最.*?多.*?(\d+).*?(?:條|筆)?", "normal"),
            (r"前.*?(\d+).*?(?:條|筆|筆資料)?", "normal"),
            (r"(\d+).*?(?:條|筆).*?(?:而.*?已)?", "normal"),
        ]

        for pattern, style in limit_patterns:
            match = re.search(pattern, nlq, re.IGNORECASE)
            if match:
                num_str = match.group(1)
                if num_str and num_str.strip():
                    result["limit"] = int(num_str.strip())
                    break

        offset_patterns = [
            (r"跳.*?過.*?(?:前.*?)?(\d+).*?(?:筆|頁)?", "skip"),
            (r"偏.*?移.*?(\d+).*?(?:筆|頁)?", "offset"),
            (r"翻.*?到.*?(?:第.*?)?(\d+).*?(?:頁|面)?", "page"),
            (r"第.*?(\d+).*?(?:頁|面)", "page"),
        ]

        for pattern, style in offset_patterns:
            match = re.search(pattern, nlq, re.IGNORECASE)
            if match:
                num_str = match.group(1)
                if num_str and num_str.strip():
                    offset = int(num_str.strip())
                    if style == "page":
                        offset = (offset - 1) * (result["limit"] or default_limit)
                    result["offset"] = offset
                    break

        if result["limit"] is None:
            result["limit"] = default_limit

        result["limit"] = min(result["limit"], 1000)

        logger.debug(f"Pagination extracted: {result}")
        return result


class IntentPreprocessor:
    """意圖預處理器 - 快速判斷查詢類型"""

    INTENT_CATEGORIES = {
        "INVENTORY": ["庫存", "在庫", "料號", "stock", "inventory"],
        "WORK_ORDER": ["工單", "WO", "work order", "製造工單"],
        "MANUFACTURING": ["製造", "工序", "工作站", "進捗"],
        "SHIPPING": ["出貨", "出荷", "出貨通知"],
        "PRICE": ["售價", "單價", "價格"],
        "QUALITY": ["品質", "不良", "報廢", "重工"],
    }

    @staticmethod
    def categorize(nlq: str) -> str:
        nlq_lower = nlq.lower()
        scores = {}
        for category, keywords in IntentPreprocessor.INTENT_CATEGORIES.items():
            score = sum(1 for kw in keywords if kw.lower() in nlq_lower)
            if score > 0:
                scores[category] = score
        if scores:
            best = max(scores.items(), key=lambda x: x[1])
            return best[0]
        return "OTHER"

    @staticmethod
    def get_table_hint(category: str) -> str:
        hints = {
            "INVENTORY": "INAG_T: INAG001=料號, INAG004=倉庫, INAG008=庫存",
            "WORK_ORDER": "SFCA_T: SFCADOCNO=工單號, SFCA003=產量",
            "MANUFACTURING": "SFCB_T: SFCB004=工序, SFCB011=工作站",
            "SHIPPING": "XMDG_T: XMDGDOCNO=單據號, XMDGSTUS=狀態",
            "PRICE": "XMDU_T: XMDU011=單價",
        }
        return hints.get(category, "使用簡單查詢")


class UltraFastParser:
    """超快解析器 - 純規則匹配，完全不呼叫 LLM"""

    INTENT_PATTERNS = {
        "QUERY_INVENTORY": [
            (r"庫存", 0.8),
            (r"在庫", 0.8),
            (r"料號", 0.7),
            (r"倉庫", 0.7),
            (r"stock|inventory", 0.6),
        ],
        "QUERY_WORK_ORDER_COUNT": [
            (r"工單", 0.8),
            (r"WO\b", 0.8),
            (r"work order", 0.6),
            (r"工單數量", 0.85),
            (r"工單總數", 0.85),
        ],
        "QUERY_MANUFACTURING_PROGRESS": [
            (r"製造進捗", 0.9),
            (r"工序進捗", 0.9),
            (r"生產進度", 0.8),
        ],
        "QUERY_SHIPPING": [
            (r"出貨", 0.8),
            (r"出荷", 0.8),
            (r"出貨通知", 0.85),
            (r"出貨記錄", 0.85),
            (r"出貨單", 0.85),
            (r"出貨數量", 0.85),
            (r"出貨金額", 0.85),
        ],
        "QUERY_STATS": [
            (r"統計", 0.7),
            (r"有多少", 0.6),
            (r"數量", 0.5),
            (r"金額", 0.5),
            (r"按.*統計", 0.6),
            (r"按.*分類", 0.6),
        ],
    }

    PARAM_PATTERNS = {
        "ITEM_NO": r"\b([A-Z0-9]{15,})\b",
        "WAREHOUSE_NO": r"\b([0-9]{4})\b",
        "MO_DOC_NO": r"([A-Z]{3}-[A-Z0-9]{2,}-\d{8,})",
    }

    @classmethod
    def parse(cls, nlq: str) -> Optional[ParsedIntent]:
        """快速解析（完全不呼叫 LLM）"""
        nlq_lower = nlq.lower()

        # 匹配意圖
        best_intent = None
        best_score = 0

        for intent, patterns in cls.INTENT_PATTERNS.items():
            for pattern, base_score in patterns:
                if re.search(pattern, nlq_lower):
                    score = base_score + (0.1 if re.search(pattern, nlq) else 0)
                    if score > best_score:
                        best_score = score
                        best_intent = intent

        if not best_intent or best_score < 0.5:
            return None

        # 提取參數
        params = {}

        # 提取料號
        item_match = re.search(cls.PARAM_PATTERNS["ITEM_NO"], nlq)
        if item_match:
            params["ITEM_NO"] = item_match.group(1)

        # 提取工單號
        wo_match = re.search(cls.PARAM_PATTERNS["MO_DOC_NO"], nlq)
        if wo_match:
            params["MO_DOC_NO"] = wo_match.group(1)

        # 提取倉庫編號
        warehouse_matches = re.findall(cls.PARAM_PATTERNS["WAREHOUSE_NO"], nlq)
        if warehouse_matches and "ITEM_NO" not in params:
            params["WAREHOUSE_NO"] = warehouse_matches[0]

        # 提取時間
        year_match = re.search(r"(202[0-9])年", nlq)
        if year_match:
            params["TIME_RANGE"] = {"type": "YEAR", "year": int(year_match.group(1))}

        return ParsedIntent(
            intent=best_intent,
            confidence=best_score,
            params=params,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            limit=100,
            offset=0,
        )


class NLQParser:
    """
    自然語言查詢解析器（基礎類）

    使用 LLM 解析 NLQ，返回意圖和參數
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or get_config().llm
        self._intents: Optional[IntentsContainer] = None

    def load_intents(self, intents: IntentsContainer):
        """載入意圖定義"""
        self._intents = intents

    def _build_prompt(self, nlq: str) -> str:
        """建構 Prompt（超簡化版 + 意圖預處理）"""
        if not self._intents:
            raise ValueError("Intents not loaded")

        # 意圖預處理
        category = IntentPreprocessor.categorize(nlq)
        table_hint = IntentPreprocessor.get_table_hint(category)

        # 簡化意圖列表
        intents_map = {
            "QUERY_INVENTORY": ["庫存查詢"],
            "QUERY_WORK_ORDER": ["工單查詢"],
            "QUERY_MANUFACTURING_PROGRESS": ["製造進度"],
            "QUERY_SHIPPING": ["出貨查詢"],
            "QUERY_STATS": ["統計分析"],
        }

        intents_str = " | ".join([f"{k}:{v[0]}" for k, v in intents_map.items()])

        return f"""分析NLQ: {nlq}

意圖類型: {intents_str}

{table_hint}

返回JSON: {{"intent":"意圖名","confidence":0.0-1.0,"params":{{"PARAM":"值"}}}}"""


class LLMNLQParser(NLQParser):
    """LLM NLQ 解析器"""

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        master_loader: Optional[MasterDataLoader] = None,
        skip_validation: bool = False,
    ):
        super().__init__(config)
        self._master_loader = master_loader or get_master_loader()
        self._skip_validation = skip_validation
        self._pagination_extractor = PaginationExtractor()

    def _validate_params(self, params: Dict[str, Any]) -> List[ValidationError]:
        """驗證參數"""
        errors = []

        if "ITEM_NO" in params:
            item_no = str(params["ITEM_NO"])
            is_valid, item_data, suggestions = self._master_loader.validate_item(item_no)
            if not is_valid:
                errors.append(ItemNotFoundError(item_no, suggestions))

        if "WAREHOUSE_NO" in params:
            warehouse_no = str(params["WAREHOUSE_NO"])
            is_valid, wh_data, suggestions = self._master_loader.validate_warehouse(warehouse_no)
            if not is_valid:
                errors.append(WarehouseNotFoundError(warehouse_no, suggestions))

        if "WORKSTATION" in params:
            workstation_id = str(params["WORKSTATION"])
            is_valid, ws_data, suggestions = self._master_loader.validate_workstation(
                workstation_id
            )
            if not is_valid:
                errors.append(WorkstationNotFoundError(workstation_id, suggestions))

        return errors

    def parse(
        self,
        nlq: str,
        skip_validation: Optional[bool] = None,
    ) -> ParsedIntent:
        """
        解析自然語言查詢（使用快取）

        Args:
            nlq: 自然語言查詢
            skip_validation: 是否跳過驗證

        Returns:
            ParsedIntent: 解析後的意圖
        """
        global _llm_cache

        skip_validation = skip_validation if skip_validation is not None else self._skip_validation

        # 檢查快取
        cache_key = _llm_cache._make_key(nlq)
        cached_result = _llm_cache.get(cache_key)
        if cached_result:
            logger.info(f"LLM cache hit for: {nlq[:30]}...")
            return ParsedIntent(
                intent=cached_result.get("intent", ""),
                confidence=cached_result.get("confidence", 0.0),
                params=cached_result.get("params", {}),
                token_usage={
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cache_hit": True,
                },
                limit=cached_result.get("limit", 100),
                offset=cached_result.get("offset", 0),
            )

        prompt = self._build_prompt(nlq)

        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    f"{self.config.endpoint}/api/generate",
                    json={
                        "model": self.config.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.03, "num_predict": 200},
                    },
                )
                response.raise_for_status()
                result = response.json()

            text = result.get("response", "").strip()
            text = text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(text)

            token_usage = {
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "completion_tokens": result.get("eval_count", 0),
                "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
            }

            params = parsed.get("params", {})
            validation_errors = []

            # Master Data Validation
            if not skip_validation:
                validation_errors = self._validate_params(params)
                if validation_errors:
                    raise ValidationError(
                        message="Entity 驗證失敗",
                        details={
                            "errors": [
                                {"type": e.entity_type, "value": e.entity_value}
                                for e in validation_errors
                            ]
                        },
                    )

            # 提取分頁參數
            pagination = self._pagination_extractor.extract(nlq)

            # 快取結果
            cache_data = {
                "intent": parsed.get("intent", ""),
                "confidence": parsed.get("confidence", 0.0),
                "params": params,
                "limit": pagination.get("limit"),
                "offset": pagination.get("offset"),
            }
            _llm_cache.set(cache_key, cache_data)

            return ParsedIntent(
                intent=parsed.get("intent", ""),
                confidence=parsed.get("confidence", 0.0),
                params=params,
                token_usage=token_usage,
                limit=pagination.get("limit"),
                offset=pagination.get("offset"),
                validation_errors=[str(e) for e in validation_errors]
                if validation_errors
                else None,
            )

        except (json.JSONDecodeError, httpx.HTTPError) as e:
            logger.error(f"LLM parsing failed: {e}")
            return ParsedIntent(intent="", confidence=0.0, params={})


class SimpleNLQParser:
    """簡單 NLQ 解析器（規則匹配）"""

    INTENT_PATTERNS = {
        "QUERY_INVENTORY": ["庫存", "在庫", "手持", "stock", "inventory", "料號"],
        "QUERY_INVENTORY_BY_WAREHOUSE": ["倉庫別在庫", "倉庫別庫存", "倉庫的庫存", "每個倉庫"],
        "QUERY_WORK_ORDER_COUNT": [
            "工單總數",
            "工單數量",
            "工單有多少",
            "多少工單",
            "工單 Count",
            "工單 count",
            "WO總數",
            "WO數量",
        ],
        "QUERY_WORK_ORDER": ["工單", "WO", "work order", "工別", "製造工單"],
        "QUERY_WORKSTATION_OUTPUT": ["工作站產出", "機台產出", "產出"],
        "QUERY_MANUFACTURING_PROGRESS": ["製造進捗", "工序進捗", "生產進度", "進步"],
        "QUERY_WORKSTATION_OUTPUT": ["工作站產出", "機台產出", "產出"],
        "QUERY_QUALITY": ["品質", "quality", "不良", "pqc", "報廢", "重工"],
        "QUERY_OUTSOURCING": ["外包", "委外", "outsourcing"],
        "QUERY_SHIPPING": ["出貨", "出荷", "ship", "出貨通知"],
        "QUERY_SHIPPING_BY_CUSTOMER": ["客戶別出貨", "客戶別出荷"],
        "QUERY_SHIPPING_DETAILS": ["出貨明细", "出荷明细"],
        "QUERY_PRICE_APPROVAL": ["售價", "單價", "價格", "price"],
        "QUERY_PRICE_DETAILS": ["售價明细", "單價明细"],
        "QUERY_CUSTOMER_PRICE": ["客戶售價", "客戶單價"],
        "QUERY_STATS": ["統計", "統計每個", "有多少", "數量分布", "種類數量"],
    }

    def __init__(
        self,
        intents: Optional[IntentsContainer] = None,
        master_loader: Optional[MasterDataLoader] = None,
        skip_validation: bool = False,
    ):
        self._intents = intents
        self._master_loader = master_loader or get_master_loader()
        self._skip_validation = skip_validation
        self._pagination_extractor = PaginationExtractor()

    def load_intents(self, intents: IntentsContainer):
        """載入意圖定義"""
        self._intents = intents

    def _extract_value(self, text: str, pattern: str) -> Optional[str]:
        """提取值"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if groups:
                return groups[0]
        return None

    def _validate_params(self, params: Dict[str, Any]) -> List[ValidationError]:
        """驗證參數"""
        errors = []

        if "ITEM_NO" in params:
            item_no = str(params["ITEM_NO"])
            is_valid, item_data, suggestions = self._master_loader.validate_item(item_no)
            if not is_valid:
                errors.append(ItemNotFoundError(item_no, suggestions))

        if "WAREHOUSE_NO" in params:
            warehouse_no = str(params["WAREHOUSE_NO"])
            is_valid, wh_data, suggestions = self._master_loader.validate_warehouse(warehouse_no)
            if not is_valid:
                errors.append(WarehouseNotFoundError(warehouse_no, suggestions))

        if "WORKSTATION" in params:
            workstation_id = str(params["WORKSTATION"])
            is_valid, ws_data, suggestions = self._master_loader.validate_workstation(
                workstation_id
            )
            if not is_valid:
                errors.append(WorkstationNotFoundError(workstation_id, suggestions))

        return errors

    def parse(
        self,
        nlq: str,
        skip_validation: Optional[bool] = None,
    ) -> ParsedIntent:
        """
        解析自然語言查詢（規則匹配）

        Args:
            nlq: 自然語言查詢
            skip_validation: 是否跳過驗證

        Returns:
            ParsedIntent: 解析後的意圖
        """
        skip_validation = skip_validation if skip_validation is not None else self._skip_validation
        nlq_lower = nlq.lower()
        params = {}
        validation_errors = []

        # 識別意圖
        intent = None
        for intent_name, keywords in self.INTENT_PATTERNS.items():
            for keyword in keywords:
                if keyword in nlq_lower:
                    intent = intent_name
                    break
            if intent:
                break

        # 預設為庫存查詢
        if not intent:
            part_match = re.search(r"\b(\d{15,})\b", nlq)
            if part_match:
                params["ITEM_NO"] = part_match.group(1)

            all_numbers = re.findall(r"\b(\d{4})\b", nlq)
            for num in all_numbers:
                if "ITEM_NO" not in params or params["ITEM_NO"] != num:
                    params["WAREHOUSE_NO"] = num
                    break

            if params:
                intent = "QUERY_INVENTORY"
        else:
            # 提取料號
            part_match = re.search(r"\b(\d{15,})\b", nlq)
            if part_match:
                params["ITEM_NO"] = part_match.group(1)

            # 提取倉庫
            all_numbers = re.findall(r"\b(\d{4})\b", nlq)
            for num in all_numbers:
                if "ITEM_NO" not in params or params["ITEM_NO"] != num:
                    params["WAREHOUSE_NO"] = num
                    break

        if not intent:
            return ParsedIntent(intent="UNKNOWN", confidence=0.0, params={})

        # 提取年份
        year_match = re.search(r"(202[0-9])年", nlq)
        if year_match:
            params["TIME_RANGE"] = {"type": "YEAR", "year": int(year_match.group(1))}

        # 提取分頁參數
        pagination = self._pagination_extractor.extract(nlq)

        # Master Data Validation
        if not skip_validation:
            validation_errors = self._validate_params(params)
            if validation_errors:
                raise ValidationError(
                    message="Entity 驗證失敗",
                    details={
                        "errors": [
                            {"type": e.entity_type, "value": e.entity_value}
                            for e in validation_errors
                        ]
                    },
                )

        return ParsedIntent(
            intent=intent,
            confidence=0.8 if params else 0.6,
            params=params,
            limit=pagination.get("limit"),
            offset=pagination.get("offset"),
            validation_errors=[str(e) for e in validation_errors] if validation_errors else None,
        )


def get_parser(parser_type: str = "simple") -> Any:
    """獲取解析器"""
    if parser_type == "llm":
        return LLMNLQParser()
    return SimpleNLQParser()
