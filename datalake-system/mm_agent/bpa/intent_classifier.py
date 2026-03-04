# 代碼功能說明: BPA 意圖分類器
# 創建日期: 2026-02-05
# 創建人: AI-Box 開發團隊

"""BPA 意圖分類器 - 使用 RAG 進行語義意圖分類"""

# ============================================================
# LLM 配置
# --------------------------------------------------------
# 用於參數提取的 LLM 模型
# 要求：
#   - 支持 Ollama API (/api/generate)
#   - 支持中文理解
#   - 建議使用小型模型以提高響應速度
#   - 預設使用 llama3.2:3b-instruct-q4_0 (約 2GB)
# --------------------------------------------------------
PARAM_EXTRACTION_LLM = "llama3.2:3b-instruct-q4_0"
PARAM_EXTRACTION_LLM_TEMPERATURE = 0.1
PARAM_EXTRACTION_LLM_TIMEOUT = 30.0
# ============================================================

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class QueryIntent(str, Enum):
    """查詢意圖枚舉"""

    QUERY_STOCK = "QUERY_STOCK"
    QUERY_STOCK_HISTORY = "QUERY_STOCK_HISTORY"
    QUERY_PURCHASE = "QUERY_PURCHASE"
    QUERY_SALES = "QUERY_SALES"
    QUERY_WORKSTATION = "QUERY_WORKSTATION"
    ANALYZE_SHORTAGE = "ANALYZE_SHORTAGE"
    GENERATE_ORDER = "GENERATE_ORDER"
    CLARIFICATION = "CLARIFICATION"


class TaskComplexity(str, Enum):
    """任務複雜度枚舉"""

    SIMPLE = "simple"
    COMPLEX = "complex"


class IntentClassification(BaseModel):
    """意圖分類結果"""

    intent: QueryIntent
    complexity: TaskComplexity
    confidence: float = 1.0
    is_complex: bool = False
    needs_clarification: bool = False
    missing_fields: list = []


class IntentClassifier:
    """意圖分類器 - 完全使用 RAG，無硬編碼"""

    def classify(self, user_input: str, context: Optional[dict] = None) -> IntentClassification:
        """分類用戶意圖

        Args:
            user_input: 用戶輸入
            context: 上下文（可選）

        Returns:
            IntentClassification: 分類結果
        """
        # 1. 使用 MM_IntentRAG 進行語義意圖分類
        rag_intent = self._rag_classify(user_input)

        if rag_intent:
            intent = self._map_rag_intent_to_query_intent(rag_intent)
        else:
            # RAG 失敗，返回需要澄清
            intent = QueryIntent.CLARIFICATION

        # 2. 使用 LLM 提取參數 + MasterRAG 驗證
        extracted_params = self._search_params_with_masterrag(user_input)

        # 3. 檢查是否需要澄清
        needs_clarification, missing = self._检查需要澄清(
            intent, user_input, context, extracted_params
        )

        return IntentClassification(
            intent=intent,
            complexity=TaskComplexity.SIMPLE,
            confidence=0.95,
            is_complex=False,
            needs_clarification=needs_clarification,
            missing_fields=missing,
        )

    def _rag_classify(self, text: str) -> Optional[str]:
        """使用 MM_IntentRAG 進行語義意圖分類"""
        try:
            from ..mm_intent_rag_client import get_mm_intent_rag_client

            client = get_mm_intent_rag_client()
            return client.classify_intent(text)
        except Exception:
            return None

    def _map_rag_intent_to_query_intent(self, rag_intent: str) -> QueryIntent:
        """將 RAG 返回的意圖名稱映射到 QueryIntent"""
        intent_mapping = {
            "QUERY_INVENTORY": QueryIntent.QUERY_STOCK,
            "QUERY_INVENTORY_BY_WAREHOUSE": QueryIntent.QUERY_STOCK,
            "QUERY_STOCK": QueryIntent.QUERY_STOCK,
            "QUERY_STOCK_HISTORY": QueryIntent.QUERY_STOCK_HISTORY,
            "QUERY_PURCHASE": QueryIntent.QUERY_PURCHASE,
            "QUERY_SALES": QueryIntent.QUERY_SALES,
            "QUERY_WORK_ORDER": QueryIntent.QUERY_WORKSTATION,
            "QUERY_MANUFACTURING_PROGRESS": QueryIntent.QUERY_WORKSTATION,
            "ANALYZE_SHORTAGE": QueryIntent.ANALYZE_SHORTAGE,
            "GENERATE_ORDER": QueryIntent.GENERATE_ORDER,
        }
        return intent_mapping.get(rag_intent, QueryIntent.CLARIFICATION)

    def _search_params_with_masterrag(self, text: str) -> dict:
        """使用 LLM 提取參數 + MasterRAG 驗證"""
        params = {}

        try:
            # 步驟1: 使用 LLM 提取參數
            extracted = self._extract_params_with_llm(text)

            # 步驟2: 使用 MasterRAG 驗證參數
            from data_agent.services.schema_driven_query.master_loader import (
                validate_entity_with_rag,
            )

            if extracted.get("item_no"):
                is_valid, _, _ = validate_entity_with_rag("item", extracted["item_no"])
                if is_valid:
                    params["item_no"] = extracted["item_no"]

            if extracted.get("warehouse"):
                is_valid, _, _ = validate_entity_with_rag("warehouse", extracted["warehouse"])
                if is_valid:
                    params["warehouse"] = extracted["warehouse"]

            if extracted.get("workstation"):
                is_valid, _, _ = validate_entity_with_rag("workstation", extracted["workstation"])
                if is_valid:
                    params["workstation"] = extracted["workstation"]

        except Exception as e:
            pass

        return params

    def _extract_params_with_llm(self, text: str) -> dict:
        """使用小型 LLM (Ollama) 提取參數"""
        import json
        import httpx

        prompt = f"""從以下文本中提取參數。
文本：{text}

只返回以下 JSON 格式，不要其他文字：
{{"item_no": "料號或null", "warehouse": "倉庫編號或null", "workstation": "工作站或null"}}

例如：
- "查詢3000倉庫庫存" → {{"item_no": null, "warehouse": "3000", "workstation": null}}
- "查詢料號10-0001的庫存" → {{"item_no": "10-0001", "warehouse": null, "workstation": null}}
"""

        try:
            # 直接調用 Ollama API
            with httpx.Client(timeout=PARAM_EXTRACTION_LLM_TIMEOUT) as client:
                response = client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": PARAM_EXTRACTION_LLM,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": PARAM_EXTRACTION_LLM_TEMPERATURE,
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get("response", "")

                    # 找到 JSON 開始和結束
                    start = response_text.find("{")
                    end = response_text.rfind("}") + 1

                    if start >= 0 and end > start:
                        json_str = response_text[start:end]
                        params = json.loads(json_str)
                        return {
                            "item_no": params.get("item_no"),
                            "warehouse": params.get("warehouse"),
                            "workstation": params.get("workstation"),
                        }

        except Exception as e:
            pass

        return {}

    def _检查需要澄清(
        self, intent: QueryIntent, text: str, context: Optional[dict], extracted_params: dict
    ) -> tuple:
        """檢查是否需要澄清"""
        missing = []

        if intent == QueryIntent.QUERY_WORKSTATION:
            if not extracted_params.get("workstation"):
                missing.append("工作站編號")

        elif intent in [QueryIntent.QUERY_PURCHASE, QueryIntent.QUERY_SALES]:
            if not extracted_params.get("item_no"):
                missing.append("料號")

        elif intent == QueryIntent.QUERY_STOCK:
            if not extracted_params.get("item_no") and not extracted_params.get("warehouse"):
                missing.append("料號或倉庫")

        if context and not missing:
            return False, []

        return len(missing) > 0, missing
