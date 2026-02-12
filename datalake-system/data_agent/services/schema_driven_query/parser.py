# -*- coding: utf-8 -*-
"""
Data-Agent-JP NLQ 解析器

功能：
- 解析自然語言查詢（NLQ）
- 識別意圖和參數
- 支援 Master Data Validation
- 新增分頁功能（LIMIT/OFFSET）

建立日期: 2026-02-10
建立人: Daniel Chung
最後修改日期: 2026-02-11
"""

import json
import logging
import re
import httpx
from typing import Dict, Any, Optional, List

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
        """建構 Prompt"""
        if not self._intents:
            raise ValueError("Intents not loaded")

        intent_descriptions = []
        for name, intent in self._intents.intents.items():
            desc = f"""
### {name}
- 描述: {intent.description}
- 可用過濾器: {", ".join(intent.input.filters) or "無"}
- 必需過濾器: {", ".join(intent.input.required_filters) or "無"}
- 可用指標: {", ".join(intent.output.metrics) or "無"}
- 可用維度: {", ".join(intent.output.dimensions) or "無"}
"""
            intent_descriptions.append(desc)

        return f"""你是一個 SQL 查詢意圖解析器。

## 可用意圖
{"".join(intent_descriptions)}

## 用戶查詢
{nlq}

## 輸出格式
返回 JSON:
{{
  "intent": "意圖名稱",
  "confidence": 0.0-1.0,
  "params": {{"PARAM_NAME": "參數值"}}
}}

## 規則
1. 只選擇可用意圖之一
2. 參數名稱必須對應 filters
3. 無法識別時 confidence 設為 0.0"""


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
        解析自然語言查詢

        Args:
            nlq: 自然語言查詢
            skip_validation: 是否跳過驗證

        Returns:
            ParsedIntent: 解析後的意圖
        """
        skip_validation = skip_validation if skip_validation is not None else self._skip_validation
        prompt = self._build_prompt(nlq)

        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    f"{self.config.endpoint}/api/generate",
                    json={
                        "model": self.config.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 500},
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
        "QUERY_WORK_ORDER": ["工單", "WO", "work order", "工別", "製造工單"],
        "QUERY_MANUFACTURING_PROGRESS": ["製造進捗", "工序進捗", "生產進度", "進度"],
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
