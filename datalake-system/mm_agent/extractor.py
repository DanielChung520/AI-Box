# 代碼功能說明: 結構化提取器
# 創建日期: 2026-02-05
# 創建人: AI-Box 開發團隊
# 最後修改日期: 2026-02-06

"""Extractor - 結構化提取器

職責：
1. 理解意圖 + 提取參數
2. 指代消解（可選）
3. 澄清處理（可選）

技術：
- LLM（一次調用，輸出JSON）
- 規則引擎（快速提取）
- 指代消解（CoreferenceResolver）
- TimeExtractor（獨立時間提取模組）
- 澄清機制（Clarification）
"""

import json
import logging
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ClarificationIssue:
    """澄清問題"""

    field: str
    issue_type: str  # missing / ambiguous / invalid
    message: str
    suggestion: Optional[str] = None


@dataclass
class ClarificationResult:
    """澄清結果"""

    need_clarification: bool = False
    question: Optional[str] = None
    issues: List[ClarificationIssue] = field(default_factory=list)
    resolved_spec: Optional[Dict[str, Any]] = None


class Extractor:
    """結構化提取器 - LLM理解 + 參數提取 + 指代消解

    特點：
    - 一次 LLM 調用完成理解 + 提取
    - 輸出結構化 JSON（QuerySpec 格式）
    - 可選指代消解（CoreferenceResolver）
    - 可選澄清機制（Clarification）
    """

    # 歧義詞列表
    AMBIGUOUS_TERMS = {
        "這個": "請說明具體是哪一個",
        "那個": "請說明具體是哪一個",
        "它": "請提供具體料號",
        "上次": "請提供具體時間或料號",
        "最近": "請明確時間範圍（如最近7天）",
        "一些": "請提供具體數量或料號",
        "大概": "請提供準確信息",
    }

    # 必填字段（按意圖類型）
    REQUIRED_FIELDS = {
        "QUERY_STOCK": ["material_id"],
        "QUERY_PURCHASE": ["material_id"],
        "QUERY_SALES": ["material_id"],
        "ANALYZE_SHORTAGE": ["material_category"],
        "GENERATE_ORDER": ["material_id"],
    }

    # 系統 Prompt
    SYSTEM_PROMPT = """你是庫存管理系統助手。

你的任務：根據用戶輸入，提取查詢參數。

【可用意圖類型】
- QUERY_STOCK：查詢庫存
- QUERY_PURCHASE：查詢採購交易
- QUERY_SALES：查詢銷售交易
- ANALYZE_SHORTAGE：缺料分析
- GENERATE_ORDER：生成訂單

【時間表達映射】
- 「本月」「這個月」→ time_type: "this_month"
- 「上月」「上個月」→ time_type: "last_month"
- 「今年」「本年」→ time_type: "this_year"
- 「去年」→ time_type: "last_year"
- 「最近7天」→ time_type: "last_week"
- 「YYYY-MM-DD」→ time_type: "specific_date", time_value: "YYYY-MM-DD"
- 「YYYY-MM-DD 到 YYYY-MM-DD」→ time_type: "date_range", time_value: "YYYY-MM-DD ~ YYYY-MM-DD"

【交易類型映射】
- 「採購」「買進」「進貨」「收料」→ transaction_type: "101"
- 「入庫」「完工入庫」→ transaction_type: "102"
- 「領料」「生產領料」→ transaction_type: "201"
- 「銷售」「賣出」「出貨」→ transaction_type: "202"
- 「報廢」「報損」→ transaction_type: "301"

【物料類別映射】
- 「塑料件」「塑膠件」→ material_category: "plastic"
- 「金屬件」「金屬」→ material_category: "metal"
- 「成品」→ material_category: "finished"
- 「原料」→ material_category: "raw"

【料號模式】
- RM05-008, W01-1234, A1B2-3456
- 格式：大寫字母2-4位 + 數字2-6位 + 可選-數字2-6位

【重要規則】
1. 只輸出 JSON，不要有其他內容
2. 如果無法確定意圖，使用 QUERY_PURCHASE
3. 如果用戶只說「庫存」，使用 QUERY_STOCK
4. 如果用戶只說「採購」或「買進」，使用 QUERY_PURCHASE
5. 如果用戶只說「銷售」或「賣出」，使用 QUERY_SALES
6. 沒有提到的參數設為 null

【輸出格式】
```json
{
  "intent": "QUERY_PURCHASE",
  "material_id": null,
  "warehouse": null,
  "time_type": "this_month",
  "time_value": null,
  "transaction_type": null,
  "material_category": null,
  "aggregation": null,
  "order_by": null,
  "limit": 100,
  "confidence": 1.0,
  "missing_fields": []
}
```
"""

    def __init__(
        self,
        llm_client=None,
        schema_registry=None,
        coreference_resolver=None,
        enable_clarification: bool = True,
        time_extractor=None,
    ):
        """初始化提取器

        Args:
            llm_client: LLM 客戶端（可選）
            schema_registry: Schema Registry（可選）
            coreference_resolver: 指代消解器（可選）
            enable_clarification: 是否啟用澄清機制（默認啟用）
            time_extractor: TimeExtractor 實例（可選，默認使用獨立模組）
        """
        self._llm_client = llm_client
        self._schema_registry = schema_registry
        self._coreference_resolver = coreference_resolver
        self._enable_clarification = enable_clarification
        self._time_extractor = time_extractor
        self._logger = logger

    def _get_llm_client(self):
        """獲取 LLM 客戶端"""
        if self._llm_client is None:
            try:
                from llm.clients.factory import get_client
                from agents.task_analyzer.models import LLMProvider

                self._llm_client = get_client(LLMProvider.OLLAMA)
            except Exception as e:
                self._logger.warning(f"無法獲取 LLM 客戶端: {e}")
                return None
        return self._llm_client

    def _get_schema_hints(self) -> str:
        """獲取 Schema 提示"""
        if self._schema_registry is None:
            return ""

        try:
            metadata = self._schema_registry.get_metadata()
            return f"\n【Schema信息】\n{json.dumps(metadata, ensure_ascii=False, indent=2)}"
        except Exception as e:
            self._logger.warning(f"獲取 Schema 失敗: {e}")
            return ""

    def _get_time_extractor(self):
        """獲取 TimeExtractor"""
        if self._time_extractor is None:
            try:
                from mm_agent.time_extractor import TimeExtractor

                self._time_extractor = TimeExtractor()
            except Exception as e:
                self._logger.warning(f"無法獲取 TimeExtractor: {e}")
                return None
        return self._time_extractor

    def _extract_part_number(self, text: str) -> Optional[str]:
        """提取料號"""
        patterns = [
            r"([A-Z]{2,4}-?\d{2,6}(?:-\d{2,6})?)",
            r"([A-Z]{2,4}\d{2,6}(?:-\d{2,6})?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """提取 YYYY-MM-DD 格式日期"""
        pattern = r"(\d{4}-\d{2}-\d{2})"
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return None

    def _extract_date_range(self, text: str) -> Optional[str]:
        """提取日期範圍"""
        pattern = r"(\d{4}-\d{2}-\d{2})\s*[至到]\s*(\d{4}-\d{2}-\d{2})"
        match = re.search(pattern, text)
        if match:
            return f"{match.group(1)} ~ {match.group(2)}"
        return None

    async def extract(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """提取查詢參數

        Args:
            user_input: 用戶輸入
            context: 上下文（用於指代消解）
            conversation_history: 對話歷史（用於指代消解）

        Returns:
            Dict: 結構化參數（QuerySpec 格式）
        """
        # 步驟 1：指代消解（可選）
        resolved_input = user_input
        if self._coreference_resolver and context:
            try:
                from mm_agent.coreference_resolver import ResolutionResult

                coref_result = self._coreference_resolver.resolve(
                    current_query=user_input,
                    context_entities=context or {},
                    conversation_history=conversation_history or [],
                )

                if coref_result.resolved:
                    resolved_input = coref_result.resolved_query
                    self._logger.info(f"指代消解: {user_input} -> {resolved_input}")
            except Exception as e:
                self._logger.warning(f"指代消解失敗: {e}")

        # 步驟 2：規則引擎快速提取
        spec = self._fast_extract(resolved_input)

        # 步驟 3：LLM 理解意圖
        llm_spec = await self._llm_extract(resolved_input)

        # 步驟 4：合併結果
        merged = self._merge(spec, llm_spec)

        # 步驟 5：設置意圖
        if not merged.get("intent"):
            merged["intent"] = self._guess_intent(resolved_input)

        # 步驟 6：澄清檢查（可選）
        if self._enable_clarification:
            clarification = self._check_clarification(merged, user_input)
            merged["_clarification"] = {
                "need_clarification": clarification.need_clarification,
                "question": clarification.question,
                "issues": [vars(i) for i in clarification.issues],
            }

        self._logger.info(f"提取結果: {merged}")
        return merged

    def _fast_extract(self, text: str) -> Dict[str, Any]:
        """快速提取（規則引擎）"""
        spec: Dict[str, Any] = {
            "material_id": None,
            "time_type": None,
            "time_value": None,
            "transaction_type": None,
        }

        # 提取料號
        part_number = self._extract_part_number(text)
        if part_number:
            spec["material_id"] = part_number

        # 使用 TimeExtractor 提取時間（優先於手動提取）
        time_extractor = self._get_time_extractor()
        if time_extractor:
            time_match = time_extractor.extract(text)
            if time_match:
                spec["time_type"] = time_match.time_type
                spec["time_value"] = time_match.time_value
            else:
                # 回退到手動提取（兼容性）
                self._fast_extract_time(text, spec)
        else:
            # 回退到手動提取
            self._fast_extract_time(text, spec)

        # 提取交易類型
        if any(kw in text for kw in ["採購", "買進", "進貨", "收料"]):
            spec["transaction_type"] = "101"
        elif any(kw in text for kw in ["銷售", "賣出", "出貨"]):
            spec["transaction_type"] = "202"

        return spec

    def _fast_extract_time(self, text: str, spec: Dict[str, Any]) -> None:
        """快速提取時間（手動回退）"""
        # 提取日期
        date = self._extract_date(text)
        if date:
            spec["time_type"] = "specific_date"
            spec["time_value"] = date
            return

        # 提取日期範圍
        date_range = self._extract_date_range(text)
        if date_range:
            spec["time_type"] = "date_range"
            spec["time_value"] = date_range
            return

        # 提取時間表達式（注意：長表達式必須在前）
        if any(kw in text for kw in ["上上月", "前第二個月", "上月之前", "上上個月"]):
            spec["time_type"] = "last_2_months"
        elif any(kw in text for kw in ["上上週", "前第二周", "上週之前", "上上星期"]):
            spec["time_type"] = "last_2_weeks"
        elif any(kw in text for kw in ["上月", "上個月"]):
            spec["time_type"] = "last_month"
        elif any(kw in text for kw in ["本月", "這個月"]):
            spec["time_type"] = "this_month"
        elif any(kw in text for kw in ["去年"]):
            spec["time_type"] = "last_year"
        elif any(kw in text for kw in ["今年", "本年"]):
            spec["time_type"] = "this_year"
        elif any(
            kw in text for kw in ["最近7天", "上週", "上星期", "最近一週", "最近一周", "過去一週"]
        ):
            spec["time_type"] = "last_week"
        elif any(kw in text for kw in ["上上月", "前第二個月", "上月之前"]):
            spec["time_type"] = "last_2_months"
        elif any(kw in text for kw in ["上上週", "前第二周", "上週之前"]):
            spec["time_type"] = "last_2_weeks"

    async def _llm_extract(self, user_input: str) -> Dict[str, Any]:
        """LLM 提取"""
        client = self._get_llm_client()
        if not client:
            return {}

        # 構建 Prompt
        schema_hints = self._get_schema_hints()
        full_prompt = f"{self.SYSTEM_PROMPT}\n{schema_hints}\n\n【用戶輸入】\n{user_input}"

        try:
            result = await client.generate(
                full_prompt,
                temperature=0.1,
                max_tokens=1000,
            )

            text = result.get("text", "")
            json_text = self._extract_json(text)

            if json_text:
                return json.loads(json_text)

        except Exception as e:
            self._logger.warning(f"LLM 提取失敗: {e}")

        return {}

    def _merge(self, spec: Dict, llm_spec: Dict) -> Dict[str, Any]:
        """合併規則和 LLM 結果"""
        merged = spec.copy()

        # LLM 補充意圖和複雜參數
        for key, value in llm_spec.items():
            if value is not None and value != "":
                if key not in spec or spec[key] is None:
                    merged[key] = value
                elif key == "intent":
                    merged[key] = value

        return merged

    def _guess_intent(self, text: str) -> str:
        """猜測意圖"""
        text_lower = text.lower()

        if any(kw in text_lower for kw in ["庫存", "存量", "還有多少", "有多少"]):
            return "QUERY_STOCK"
        elif any(kw in text_lower for kw in ["採購", "買進", "進貨", "收料"]):
            return "QUERY_PURCHASE"
        elif any(kw in text_lower for kw in ["銷售", "賣出", "出貨"]):
            return "QUERY_SALES"
        elif any(kw in text_lower for kw in ["缺料", "不足", "不夠"]):
            return "ANALYZE_SHORTAGE"
        elif any(kw in text_lower for kw in ["訂單", "採購單", "請購"]):
            return "GENERATE_ORDER"

        return "QUERY_PURCHASE"

    def _extract_json(self, text: str) -> str:
        """從 LLM 輸出中提取 JSON"""
        # 移除 markdown 代碼塊
        text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```\s*", "", text)

        # 查找 JSON
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:
            return text[start : end + 1]

        return ""

    def _check_clarification(
        self, spec: Dict[str, Any], original_input: str
    ) -> ClarificationResult:
        """檢查是否需要澄清"""
        issues: List[ClarificationIssue] = []
        intent = spec.get("intent", "QUERY_PURCHASE")

        # 檢查必填字段
        required_fields = self.REQUIRED_FIELDS.get(intent, [])
        for field in required_fields:
            if not spec.get(field):
                issues.append(
                    ClarificationIssue(
                        field=field,
                        issue_type="missing",
                        message=f"缺少必要字段: {field}",
                        suggestion=self._get_field_suggestion(field),
                    )
                )

        # 檢查歧義詞
        for term, question in self.AMBIGUOUS_TERMS.items():
            if term in original_input:
                issues.append(
                    ClarificationIssue(
                        field="general",
                        issue_type="ambiguous",
                        message=question,
                    )
                )

        # 如果有問題，生成澄清問題
        if issues:
            question = self._generate_clarification_question(issues, spec)
            return ClarificationResult(
                need_clarification=True,
                question=question,
                issues=issues,
                resolved_spec=spec,
            )

        return ClarificationResult()

    def _get_field_suggestion(self, field: str) -> str:
        """獲取字段建議"""
        suggestions = {
            "material_id": "如：RM05-008、RM06-010",
            "material_category": "如：塑料件、金屬件、成品",
            "warehouse": "如：原料倉、成品倉",
            "time_type": "如：本月、上月、去年",
        }
        return suggestions.get(field, "")

    def _generate_clarification_question(
        self, issues: List[ClarificationIssue], spec: Dict[str, Any]
    ) -> str:
        """生成澄清問題"""
        questions = []

        for issue in issues:
            if issue.issue_type == "missing":
                questions.append(issue.suggestion or issue.message)
            elif issue.issue_type == "ambiguous":
                questions.append(issue.message)

        if len(questions) == 1:
            return f"請提供：{questions[0]}"
        elif len(questions) > 1:
            return "請提供以下信息：\n" + "\n".join(f"- {q}" for q in questions)

        return "請明確您的需求"

    def extract_sync(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """同步提取（封裝異步方法）"""
        import asyncio

        return asyncio.run(
            self.extract(
                user_input=user_input,
                context=context,
                conversation_history=conversation_history,
            )
        )
