# 代碼功能說明: 語義轉譯 Agent
# 創建日期: 2026-02-05
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-05

"""語義轉譯 Agent - 使用 LLM 將自然語言轉換為語義結構"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ai_box_root))

from llm.clients.factory import get_client
from agents.task_analyzer.models import LLMProvider

from .translation_models import (
    SemanticTranslationResult,
    ConceptMapping as ConceptMappingModel,
    SchemaBinding,
    Constraints,
    Validation,
)

from .services.schema_registry import get_schema_registry, SchemaRegistry

logger = logging.getLogger(__name__)


class SemanticTranslatorAgent:
    """語義轉譯 Agent - 從 Schema Registry 動態載入 Concepts 與 Intent Templates"""

    INTENT_ENUM = [
        "QUERY_STOCK",  # 庫存查詢
        "QUERY_PURCHASE",  # 採購查詢
        "QUERY_SALES",  # 銷售查詢
        "ANALYZE_SHORTAGE",  # 缺料分析
        "GENERATE_ORDER",  # 生成訂單
        "QUERY_SUPPLIER",  # 供應商查詢
        "QUERY_CUSTOMER",  # 客戶查詢
        "CLARIFICATION",  # 需要澄清
    ]

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        schema_registry_path: Optional[str] = None,
        use_rules_engine: bool = True,
    ) -> None:
        """初始化語義轉譯 Agent

        Args:
            llm_provider: LLM 提供商（可選，默認 OLLAMA）
            schema_registry_path: Schema Registry 路徑（可選）
            use_rules_engine: 是否同時使用規則引擎（快速匹配）
        """
        self._llm_provider = llm_provider or LLMProvider.OLLAMA
        self._llm_client = None
        self._schema_registry_path = schema_registry_path
        self._use_rules_engine = use_rules_engine
        self._logger = logger

        # 初始化 Schema Registry
        self._schema_registry = get_schema_registry(schema_registry_path)

        # 快取 Prompt 結構（避免每次重新序列化）
        self._prompt_cache = {
            "metadata": None,
            "concepts": None,
            "templates": None,
            "intent_list": ", ".join(self.INTENT_ENUM),
        }
        self._cache_initialized = False

        # 快速路徑：簡單查詢模式（無需 LLM）
        self._simple_patterns = [
            (r"^[A-Z]{2,4}-?\d{2,6}.*上月.*$", "QUERY_PURCHASE"),
            (r"^[A-Z]{2,4}-?\d{2,6}.*本月.*$", "QUERY_PURCHASE"),
            (r"^[A-Z]{2,4}-?\d{2,6}.*庫存.*$", "QUERY_STOCK"),
            (r"^[A-Z]{2,4}-?\d{2,6}.*庫存還有多少.*$", "QUERY_STOCK"),
            (r"^[A-Z]{2,4}-?\d{2,6}.*上月賣出.*$", "QUERY_SALES"),
            (r"^上月.*買進.*$", "QUERY_PURCHASE"),
            (r"^本月.*買進.*$", "QUERY_PURCHASE"),
            (r"^上月.*賣出.*$", "QUERY_SALES"),
        ]

    def _get_llm_client(self):
        """獲取 LLM 客戶端（延遲初始化）"""
        if self._llm_client is None:
            try:
                self._llm_client = get_client(self._llm_provider)
            except Exception as e:
                self._logger.warning(f"無法初始化 LLM 客戶端: {e}")
                try:
                    self._llm_client = get_client(LLMProvider.QWEN)
                except Exception as e2:
                    self._logger.error(f"無法初始化備用 LLM 客戶端: {e2}")
        return self._llm_client

    def _find_concepts_with_rules(self, text: str) -> List[ConceptMappingModel]:
        """使用規則引擎查找概念（快速匹配）"""
        concepts = []
        text_lower = text.lower()

        for concept_name, concept in self._schema_registry.get_all_concepts().items():
            for mapping_key, mapping in concept.mappings.items():
                for keyword in mapping.keywords:
                    if keyword.lower() in text_lower:
                        concepts.append(
                            ConceptMappingModel(
                                canonical_id=concept_name, source_terms=[keyword], confidence=0.9
                            )
                        )
                        break

        return concepts

    def _extract_part_number(self, text: str) -> Optional[str]:
        """使用規則引擎提取料號"""
        import re

        patterns = [
            r"([A-Z]{2,4}-?\d{2,6}(?:-\d{2,6})?)",
            r"([A-Z]{2,4}\d{2,6}(?:-\d{2,6})?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None

    def _extract_quantity(self, text: str) -> Optional[int]:
        """使用規則引擎提取數量"""
        import re

        patterns = [
            r"(\d+)\s*(?:個|件|PCS|pcs|kg|KG|公斤)",
            r"(?:合計|總計|共)\s*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """使用規則引擎提取 YYYY-MM-DD 格式的日期"""
        import re

        patterns = [
            r"(\d{4}-\d{2}-\d{2})",  # 2024-04-14
            r"(\d{4}/\d{2}/\d{2})",  # 2024/04/14
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_date_range(self, text: str) -> Optional[Dict[str, str]]:
        """提取日期範圍"""
        import re

        pattern = r"(\d{4}-\d{2}-\d{2})\s*[至到]\s*(\d{4}-\d{2}-\d{2})"
        match = re.search(pattern, text)
        if match:
            return {"start": match.group(1), "end": match.group(2)}
        return None

    def _init_prompt_cache(self):
        """初始化 Prompt 快取（只執行一次）"""
        if self._cache_initialized:
            return

        self._prompt_cache["metadata"] = json.dumps(
            self._schema_registry.get_metadata(), ensure_ascii=False, indent=2
        )

        concepts = self._schema_registry.get_all_concepts()
        concepts_json = {}
        for name, concept in concepts.items():
            concepts_json[name] = {
                "description": concept.description,
                "mappings": {
                    k: {
                        "keywords": v.keywords,
                        "target_field": v.target_field,
                        "operator": v.operator,
                    }
                    for k, v in concept.mappings.items()
                },
            }
        self._prompt_cache["concepts"] = json.dumps(concepts_json, ensure_ascii=False, indent=2)

        templates = self._schema_registry.get_all_intent_templates()
        templates_json = {}
        for name, template in templates.items():
            templates_json[name] = {
                "description": template.description,
                "intent_type": template.intent_type,
                "primary_table": template.primary_table,
                "required_fields": template.required_fields,
                "optional_fields": template.optional_fields,
                "examples": template.examples,
            }
        self._prompt_cache["templates"] = json.dumps(templates_json, ensure_ascii=False, indent=2)

        self._cache_initialized = True

    def _try_fast_path(self, user_input: str) -> Optional[SemanticTranslationResult]:
        """快速路徑：簡單查詢直接返回（無需 LLM）"""
        import re

        for pattern, intent in self._simple_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                self._logger.info(f"快速路徑匹配: {intent}")

                extracted_part = self._extract_part_number(user_input)

                if intent == "QUERY_PURCHASE":
                    time_range = (
                        {"type": "last_month"} if "上月" in user_input else {"type": "this_month"}
                    )
                elif intent == "QUERY_SALES":
                    time_range = (
                        {"type": "last_month"} if "上月" in user_input else {"type": "this_month"}
                    )
                else:
                    time_range = None

                constraints = Constraints(
                    material_id=extracted_part,
                    time_range=time_range,
                )

                intent_template = self._schema_registry.get_intent_template(intent)
                schema_binding = SchemaBinding(
                    primary_table=intent_template.primary_table if intent_template else "",
                    tables=[intent_template.primary_table] if intent_template else [],
                )

                return SemanticTranslationResult(
                    intent=intent,
                    concepts=[],
                    schema_binding=schema_binding,
                    constraints=constraints,
                    validation=Validation(requires_confirmation=False),
                    raw_text=user_input,
                )

        return None

    def _build_prompt(self, user_input: str) -> str:
        """構建 LLM Prompt（使用快取）"""
        self._init_prompt_cache()

        schema_content = self._prompt_cache["metadata"]
        concepts_json = self._prompt_cache["concepts"]
        templates_json = self._prompt_cache["templates"]
        intent_list = self._prompt_cache["intent_list"]

        prompt = f"""你是一個「企業 ERP 語義轉譯 Agent」，負責將使用者的自然語言，
轉換為「結構化、可驗證、可對齊資料 Schema 的語義結果」。

你必須嚴格遵守以下原則：
1. 不猜測不存在於 Schema 中的資料表或欄位
2. 不直接生成 SQL
3. 不輸出自然語言解釋，僅輸出 JSON
4. 所有語義必須對齊到「Canonical Concept」，而不是表名或欄位名
5. 若資訊不足，必須明確標註 requires_confirmation = true

【系統元數據】
<SCHEMA_METADATA>
{schema_content}
</SCHEMA_METADATA>

【Canonical Concepts（詞彙轉譯對照表）】
<CONCEPTS>
{json.dumps(concepts_json, ensure_ascii=False, indent=2)}
</CONCEPTS>

【Intent Templates（意圖模板）】
<TEMPLATES>
{json.dumps(templates_json, ensure_ascii=False, indent=2)}
</TEMPLATES>

可用的意圖類型（必須嚴格使用）：
{intent_list}

你的任務是：
根據「使用者輸入」，完成以下步驟並輸出結果：

【步驟 1：詞彙轉譯（Lexical Mapping）】
- 將使用者用語對齊為 Canonical Concept
- 記錄所有識別到的概念與原始用詞

【步驟 2：意圖分類（Intent Classification）】
- 從意圖類型列表中選擇最匹配的一個
- 如果無法確定，使用 "CLARIFICATION"

【步驟 3：Schema 對齊（Schema Binding）】
- 根據意圖類型選擇對應的 Intent Template
- 列出可能需要的資料表與欄位

【步驟 4：完整性檢查（Validation）】
- 判斷是否缺少關鍵條件
- 若缺少，標註 requires_confirmation = true

【重要提示】
- 如果使用者提到「採購」、「買進」、「進貨」，自動設置 transaction_type = "101"
- 如果使用者提到「銷售」、「賣出」、「出貨」，自動設置 transaction_type = "202"
- 如果使用者提到「入庫」、「完工入庫」，自動設置 transaction_type = "102"
- 如果使用者提到「領料」、「生產領料」，自動設置 transaction_type = "201"
- 如果使用者提到「報廢」，自動設置 transaction_type = "301"
- 如果使用者提到「料號」（如 RM05-008），自動提取到 material_id

【輸出格式（嚴格遵守）】
請僅輸出以下 JSON 結構：

{{
  "intent": "",
  "concepts": [
    {{
      "canonical_id": "",
      "source_terms": [],
      "confidence": 0.0
    }}
  ],
  "constraints": {{
    "material_id": null,
    "inventory_location": null,
    "material_category": null,
    "transaction_type": null,
    "time_range": null,
    "quantity": null,
    "warehouse": null
  }},
  "schema_binding": {{
    "intent_template": "",
    "primary_table": "",
    "tables": [],
    "columns": []
  }},
  "validation": {{
    "requires_confirmation": false,
    "missing_fields": [],
    "notes": ""
  }}
}}

現在開始處理以下使用者輸入：
「{user_input}」"""

        return prompt

    async def translate(self, user_input: str) -> SemanticTranslationResult:
        """將自然語言轉換為語義結構"""
        try:
            # Step 0: 快速路徑（簡單查詢無需 LLM）
            if self._use_rules_engine:
                fast_result = self._try_fast_path(user_input)
                if fast_result:
                    self._logger.info(f"快速路徑成功: {fast_result.intent}")
                    return fast_result

            # Step 1: 使用規則引擎進行快速匹配
            rule_concepts = []
            if self._use_rules_engine:
                rule_concepts = self._find_concepts_with_rules(user_input)
                self._logger.info(f"規則引擎識別到 {len(rule_concepts)} 個概念")

            # Step 2: 使用 LLM 進行語義理解
            client = self._get_llm_client()
            if not client:
                raise RuntimeError("LLM client is not available")

            prompt = self._build_prompt(user_input)

            self._logger.info(f"語義轉譯開始: {user_input[:50]}...")
            result = await client.generate(
                prompt,
                temperature=0.3,
                max_tokens=2000,
            )

            # 提取 JSON
            json_text = self._extract_json(result.get("text", ""))
            if not json_text:
                raise RuntimeError("LLM 未返回有效的 JSON")

            # 解析 JSON
            json_data = json.loads(json_text)

            # 構建概念列表（合併規則引擎與 LLM 的結果）
            all_concepts = self._merge_concepts(rule_concepts, json_data.get("concepts", []))

            # 從 LLM 結果提取約束條件
            llm_constraints = json_data.get("constraints", {})

            # 處理 time_range 類型（LLM 可能返回字串）
            if "time_range" in llm_constraints and isinstance(llm_constraints["time_range"], str):
                time_str = llm_constraints["time_range"]

                # 處理相對時間
                if time_str == "last_month":
                    llm_constraints["time_range"] = {"type": "last_month"}
                elif time_str == "this_month":
                    llm_constraints["time_range"] = {"type": "this_month"}
                elif time_str == "this_year":
                    llm_constraints["time_range"] = {"type": "this_year"}
                elif time_str == "last_year":
                    llm_constraints["time_range"] = {"type": "last_year"}
                elif time_str.isdigit() and len(time_str) == 4:
                    # 處理純年份字串，如 "2024"
                    llm_constraints["time_range"] = {
                        "type": "date_range",
                        "start": f"{time_str}-01-01",
                        "end": f"{time_str}-12-31",
                    }
                elif "-" in time_str and len(time_str) == 4:
                    # 處理年份前綴，如 "2024-05"
                    llm_constraints["time_range"] = {
                        "type": "date_range",
                        "start": f"{time_str}-01",
                        "end": f"{time_str}-12",
                    }

            # 使用規則引擎提取具體日期（YYYY-MM-DD 格式）
            extracted_date = self._extract_date(user_input)
            if extracted_date:
                llm_constraints["time_range"] = {"type": "specific_date", "date": extracted_date}

            # 使用規則引擎提取日期範圍
            extracted_range = self._extract_date_range(user_input)
            if extracted_range:
                llm_constraints["time_range"] = {
                    "type": "date_range",
                    "start": extracted_range["start"],
                    "end": extracted_range["end"],
                }

            # 使用規則引擎提取料號（更準確）
            if not llm_constraints.get("material_id"):
                extracted_part = self._extract_part_number(user_input)
                if extracted_part:
                    llm_constraints["material_id"] = extracted_part

            # 使用規則引擎提取數量
            if not llm_constraints.get("quantity"):
                extracted_qty = self._extract_quantity(user_input)
                if extracted_qty:
                    llm_constraints["quantity"] = extracted_qty

            # 從 LLM 結果提取 Schema 綁定
            schema_binding_data = json_data.get("schema_binding", {})

            # 獲取意圖模板
            intent_name = json_data.get("intent", "CLARIFICATION")
            intent_template = self._schema_registry.get_intent_template(intent_name)

            # 驗證約束
            validation_result = self._schema_registry.validate_constraints(
                intent_name, llm_constraints
            )

            # 構建 Validation 物件
            validation = Validation(
                requires_confirmation=validation_result.get("valid") is False,
                missing_fields=validation_result.get("missing_fields", []),
                notes=validation_result.get("error_message", ""),
            )

            # 構建 SchemaBinding 物件
            schema_binding = SchemaBinding(
                primary_table=schema_binding_data.get("primary_table")
                or (intent_template.primary_table if intent_template else ""),
                tables=schema_binding_data.get("tables", []),
                columns=schema_binding_data.get("columns", []),
            )

            # 構建 Constraints 物件
            constraints = Constraints(
                material_id=llm_constraints.get("material_id"),
                inventory_location=llm_constraints.get("inventory_location")
                or llm_constraints.get("warehouse"),
                time_range=llm_constraints.get("time_range"),
                material_category=llm_constraints.get("material_category"),
                transaction_type=llm_constraints.get("transaction_type"),
                quantity=llm_constraints.get("quantity"),
            )

            # 檢測是否需要複雜統計（LLM 生成 SQL）
            user_input_lower = user_input.lower()
            complex_keywords = [
                "每月",
                "每個月",
                "每月份",
                "每日",
                "每天",
                "每季",
                "每季度",
                "每供應商",
                "每客戶",
                "每筆",
                "按月",
                "按日",
                "按季",
                "各月份",
                "各供應商",
                "各客戶",
                "統計",
                "分析",
                "趨勢",
            ]
            need_llm_sql = any(kw in user_input for kw in complex_keywords)

            return SemanticTranslationResult(
                intent=intent_name,
                concepts=all_concepts,
                schema_binding=schema_binding,
                constraints=constraints,
                validation=validation,
                raw_text=user_input,
            )

        except Exception as e:
            self._logger.error(f"語義轉譯失敗: {e}", exc_info=True)
            return SemanticTranslationResult(
                intent="CLARIFICATION",
                concepts=[],
                schema_binding=SchemaBinding(),
                constraints=Constraints(),
                validation=Validation(
                    requires_confirmation=True,
                    missing_fields=[],
                    notes=f"轉譯失敗: {str(e)}",
                ),
                raw_text=user_input,
            )

    def _merge_concepts(
        self, rule_concepts: List[ConceptMappingModel], llm_concepts: List[Dict]
    ) -> List[ConceptMappingModel]:
        """合併規則引擎與 LLM 識別的概念"""
        merged = {}

        for concept in rule_concepts:
            merged[concept.canonical_id] = concept

        for concept_data in llm_concepts:
            cid = concept_data.get("canonical_id", "")
            if cid and cid not in merged:
                merged[cid] = ConceptMappingModel(
                    canonical_id=cid,
                    source_terms=concept_data.get("source_terms", []),
                    confidence=concept_data.get("confidence", 0.7),
                )

        return list(merged.values())

    def _extract_json(self, text: str) -> str:
        """從 LLM 輸出中提取 JSON"""
        text = text.replace("```json", "").replace("```", "")

        start_idx = text.find("{")
        end_idx = text.rfind("}")

        if start_idx == -1 or end_idx == -1:
            return ""

        return text[start_idx : end_idx + 1]

    def translate_sync(self, user_input: str) -> SemanticTranslationResult:
        """同步版本的語義轉譯（供非 async 環境使用）"""
        import asyncio

        return asyncio.run(self.translate(user_input))


if __name__ == "__main__":
    import asyncio

    async def main():
        agent = SemanticTranslatorAgent(use_rules_engine=True)

        test_cases = [
            "RM05-008 上月買進多少",
            "查詢 W01 倉庫的塑料件庫存",
            "這個料號庫存還有多少",
            "上月採購數量",
        ]

        for test_input in test_cases:
            print("\n" + "=" * 70)
            print(f"輸入: {test_input}")
            print("=" * 70)

            result = await agent.translate(test_input)

            print(f"\n意圖: {result.intent}")
            print(f"概念映射: {len(result.concepts)} 個")
            for concept in result.concepts:
                print(
                    f"  - {concept.canonical_id}: {concept.source_terms} ({concept.confidence:.2f})"
                )

            print(f"\n約束條件:")
            print(f"  - 料號: {result.constraints.material_id}")
            print(f"  - 倉庫: {result.constraints.inventory_location}")
            print(f"  - 物料類別: {result.constraints.material_category}")

            print(f"\n驗證:")
            print(f"  - 需要確認: {result.validation.requires_confirmation}")
            print(f"  - 缺少欄位: {result.validation.missing_fields}")

    asyncio.run(main())
