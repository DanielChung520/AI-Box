# 代碼功能說明: Text-to-SQL 轉換服務
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-05

"""Text-to-SQL 轉換服務 - 將自然語言轉換為 SQL 查詢"""

import logging
import re
from typing import Any, Dict, List, Optional

import sys
from pathlib import Path

# 添加 datalake-system 到 Python 路徑
datalake_root = Path(__file__).resolve().parent.parent
if str(datalake_root) not in sys.path:
    sys.path.insert(0, str(datalake_root))

from agents.task_analyzer.models import LLMProvider
from llm.clients.factory import get_client

from mm_agent.services.schema_registry import get_schema_registry

logger = logging.getLogger(__name__)


class TextToSQLService:
    """Text-to-SQL 轉換服務"""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        初始化 Text-to-SQL 服務

        Args:
            llm_provider: LLM 提供商（可選，默認使用 OLLAMA）
        """
        self._llm_provider = llm_provider or LLMProvider.OLLAMA
        self._llm_client = None
        self._logger = logger

        # 初始化 Schema Registry（用於 SQL 生成）
        self._schema_registry = get_schema_registry()

    def _intent_to_constraints(self, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """將意圖分析結果轉換為約束條件"""
        constraints = {}

        # 映射意圖類型到 Schema Registry 的 intent
        intent_mapping = {
            "purchase": "QUERY_PURCHASE",
            "sales": "QUERY_SALES",
            "inventory": "QUERY_STOCK",
            "shortage": "ANALYZE_SHORTAGE",
        }
        intent_type = intent_analysis.get("intent_type", "")
        if intent_type in intent_mapping:
            constraints["_intent_name"] = intent_mapping[intent_type]

        # 料號
        if intent_analysis.get("material_id"):
            constraints["material_id"] = intent_analysis["material_id"]

        # 倉庫
        if intent_analysis.get("warehouse"):
            constraints["inventory_location"] = intent_analysis["warehouse"]

        # 物料類別
        if intent_analysis.get("material_category"):
            constraints["material_category"] = intent_analysis["material_category"]

        # 交易類型
        if intent_analysis.get("transaction_type"):
            constraints["transaction_type"] = intent_analysis["transaction_type"]

        # 時間範圍
        if intent_analysis.get("time_range"):
            time_range = intent_analysis["time_range"]
            if isinstance(time_range, dict):
                constraints["time_type"] = time_range.get("type")
            elif isinstance(time_range, str):
                constraints["time_type"] = time_range

        # 數量
        if intent_analysis.get("quantity"):
            constraints["quantity"] = intent_analysis["quantity"]

        return constraints

    def _generate_sql_from_schema_registry(self, intent_analysis: Dict[str, Any]) -> Optional[str]:
        """使用 Schema Registry 生成 SQL"""
        try:
            intent_name = intent_analysis.get("intent", "") or ""

            if not intent_name:
                return None

            # 映射舊意圖到新意圖
            intent_mapping = {
                "purchase": "QUERY_PURCHASE",
                "sales": "QUERY_SALES",
                "inventory": "QUERY_STOCK",
                "shortage": "ANALYZE_SHORTAGE",
            }
            schema_intent = intent_mapping.get(intent_name, intent_name)

            if schema_intent is None or schema_intent == "":
                return None

            # 轉換約束條件
            constraints = self._intent_to_constraints(intent_analysis)

            # 生成 SQL
            sql = self._schema_registry.generate_sql(schema_intent, constraints)

            self._logger.info(f"Schema Registry 生成 SQL: {sql[:100] if sql else 'None'}...")
            return sql

        except Exception as e:
            self._logger.warning(f"Schema Registry SQL 生成失敗: {e}")
            return None

    def _generate_sql_fallback(self, intent_analysis: Dict[str, Any]) -> str:
        """回退 SQL 生成（舊邏輯）"""
        table = intent_analysis.get("table", "img_file")
        group_by = intent_analysis.get("group_by", "")
        aggregation = intent_analysis.get("aggregation", "")
        filters = intent_analysis.get("filters", "")

        self._logger.info(
            f"使用回退邏輯生成 SQL: table={table}, group_by={group_by}, aggregation={aggregation}, filters={filters}"
        )

        # 生成 SQL
        if group_by and aggregation:
            sql_text = f"SELECT {group_by}, {aggregation}(img10) FROM {table}"
        elif aggregation:
            sql_text = f"SELECT {aggregation}(img10) FROM {table}"
        elif group_by:
            sql_text = f"SELECT {group_by} FROM {table}"
        else:
            sql_text = f"SELECT * FROM {table}"

        if filters:
            sql_text += f" WHERE {filters}"

        if group_by and aggregation:
            sql_text += f" GROUP BY {group_by}"

        self._logger.info(f"回退生成 SQL: {sql_text}")
        return sql_text

    def _get_llm_client(self):
        """獲取 LLM 客戶端（延遲初始化）"""
        if self._llm_client is None:
            try:
                self._llm_client = get_client(self._llm_provider)
            except Exception as e:
                self._logger.warning(f"Failed to initialize LLM client: {e}")
                # 嘗試使用備用提供商
                try:
                    self._llm_client = get_client(LLMProvider.QWEN)
                except Exception:
                    self._logger.error("No LLM client available")
        return self._llm_client

    async def convert(
        self,
        natural_language: str,
        database_type: str = "postgresql",
        schema_info: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        intent_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        將自然語言轉換為 SQL

        Args:
            natural_language: 自然語言查詢
            database_type: 數據庫類型（postgresql/mysql/sqlite）
            schema_info: 數據庫 Schema 信息（可選）
            context: 上下文信息（可選）
            intent_analysis: 意圖分析結果（可選，用於指導 LLM 生成 SQL）

        Returns:
            轉換結果，包含 SQL 查詢、參數、置信度等
        """
        try:
            client = self._get_llm_client()
            if not client:
                raise RuntimeError("LLM client is not available")

            self._logger.info(f"intent_analysis 接收: {intent_analysis}")

            # 優先使用 Schema Registry 生成 SQL
            if intent_analysis and intent_analysis.get("intent"):
                sql_from_registry = self._generate_sql_from_schema_registry(intent_analysis)
                if sql_from_registry:
                    self._logger.info(f"使用 Schema Registry 生成 SQL")
                    sql_text = sql_from_registry
                else:
                    # 回退到舊邏輯
                    self._logger.info("Schema Registry 生成失敗，回退到舊邏輯")
                    sql_text = self._generate_sql_fallback(intent_analysis)
            elif intent_analysis and intent_analysis.get("table"):
                # 回退到舊邏輯
                sql_text = self._generate_sql_fallback(intent_analysis)
            else:
                self._logger.info("意圖分析不完整，使用 LLM 翻譯")
                # 需要 LLM 翻譯自然語言
                prompt = self._build_prompt(natural_language, database_type, schema_info)
                result = await client.generate(
                    prompt,
                    temperature=0.3,
                    max_tokens=1000,
                )
                sql_text = result.get("text") or result.get("content", "")

            # 提取 SQL 查詢
            sql_query = self._extract_sql(sql_text)

            # 驗證和優化 SQL
            validated_sql, warnings = self._validate_sql(sql_query, database_type)

            # 提取參數
            parameters = self._extract_parameters(validated_sql)

            # 計算置信度（簡單實現）
            confidence = self._calculate_confidence(sql_query, natural_language)

            return {
                "sql_query": validated_sql,
                "parameters": parameters,
                "confidence": confidence,
                "explanation": self._generate_explanation(sql_query, natural_language),
                "warnings": warnings,
            }

        except Exception as e:
            self._logger.error(f"Text-to-SQL conversion failed: {e}")
            raise

    def _build_prompt(
        self,
        natural_language: str,
        database_type: str,
        schema_info: Optional[Dict[str, Any]] = None,
        intent_analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """構建 LLM 提示詞"""

        table = intent_analysis.get("table", "img_file") if intent_analysis else "img_file"
        group_by = intent_analysis.get("group_by", "") if intent_analysis else ""
        aggregation = intent_analysis.get("aggregation", "") if intent_analysis else ""
        filters = intent_analysis.get("filters", "") if intent_analysis else ""

        # 強制 SQL 格式
        sql_template = ""
        if group_by and aggregation:
            sql_template = f"SELECT {group_by}, {aggregation}(img10) FROM {table}"
        elif aggregation:
            sql_template = f"SELECT {aggregation}(img10) FROM {table}"
        elif group_by:
            sql_template = f"SELECT {group_by} FROM {table}"
        else:
            sql_template = f"SELECT * FROM {table}"

        if filters:
            sql_template += f" WHERE {filters}"

        if group_by and aggregation:
            sql_template += f" GROUP BY {group_by}"

        prompt = f"""{sql_template}"""

        return prompt

        # 添加意圖分析（如果提供）
        if intent_analysis:
            prompt += f"""【意圖分析結果】（必須嚴格遵守）：
- 意圖類型：{intent_analysis.get("intent_type", "query")}
- 描述：{intent_analysis.get("description", "")}
- 資料表：{intent_analysis.get("table", "")}
- 聚合方式：{intent_analysis.get("aggregation", "none")}（計算總和用 SUM）
- 分組欄位：{intent_analysis.get("group_by", "none")}（按此欄位分組）
- 篩選條件：{intent_analysis.get("filters", "none")}

嚴格按照以上意圖生成 SQL，不要自行解釈或添加額外條件！
如果意圖分析要求分組，必須使用 GROUP BY！
如果意圖分析要求聚合，必須使用相應的聚合函數！

"""

        if schema_info:
            prompt += f"""數據庫 Schema 信息（必須使用，不要使用通用表名）：
{self._format_schema_info(schema_info)}

重要：必須使用上述 Schema 中定義的表名和欄位！

"""

        prompt += """要求：
1. 只返回 SQL 查詢語句，不要包含其他解釋
2. 使用參數化查詢（使用 ? 或 $1, $2 等佔位符）
3. 確保 SQL 語法正確
4. 只使用 SELECT 查詢（不允許 DROP、DELETE、TRUNCATE 等危險操作）

SQL 查詢："""

        return prompt

    def _format_schema_info(self, schema_info: Dict[str, Any]) -> str:
        """格式化 Schema 信息

        支持多種格式：
        1. {"tables": {"users": {"columns": [...]}}}  # 字典格式（預期）
        2. {"img_file": {"columns": [...]}}  # 直接表名格式（Dashboard 傳遞）
        3. {"tables": [{"name": "users", "columns": [...]}]}  # 列表格式
        """
        formatted = []

        # 優先處理格式 1：{"tables": {...}}
        tables = schema_info.get("tables")

        # 處理格式 2：直接表名格式（如 {"img_file": {...}}）
        if tables is None:
            for table_name, table_info in schema_info.items():
                if isinstance(table_info, dict):
                    formatted.append(f"表 {table_name}:")
                    columns = table_info.get("columns", [])
                    for col in columns:
                        if isinstance(col, str):
                            formatted.append(f"  - {col}")
                        elif isinstance(col, dict):
                            col_id = col.get("id", col.get("name", ""))
                            col_type = col.get("type", "")
                            col_desc = col.get("description", "")
                            desc_str = f" - {col_desc}" if col_desc else ""
                            formatted.append(f"  - {col_id} ({col_type}){desc_str}")

        # 處理格式 1：{"tables": {"users": {...}}}
        elif isinstance(tables, dict):
            for table_name, table_info in tables.items():
                formatted.append(f"表 {table_name}:")
                columns = table_info.get("columns", [])
                for col in columns:
                    if isinstance(col, str):
                        formatted.append(f"  - {col}")
                    elif isinstance(col, dict):
                        col_id = col.get("id", col.get("name", ""))
                        col_type = col.get("type", "")
                        col_desc = col.get("description", "")
                        desc_str = f" - {col_desc}" if col_desc else ""
                        formatted.append(f"  - {col_id} ({col_type}){desc_str}")

        # 處理格式 3：{"tables": [...]}
        elif isinstance(tables, list):
            for table in tables:
                table_name = table.get("name", "")
                columns = table.get("columns", [])
                formatted.append(f"表 {table_name}:")
                for col in columns:
                    if isinstance(col, str):
                        formatted.append(f"  - {col}")
                    elif isinstance(col, dict):
                        col_id = col.get("id", col.get("name", ""))
                        col_type = col.get("type", "")
                        col_desc = col.get("description", "")
                        desc_str = f" - {col_desc}" if col_desc else ""
                        formatted.append(f"  - {col_id} ({col_type}){desc_str}")

        return "\n".join(formatted)

    def _extract_sql(self, text: str) -> str:
        """從 LLM 輸出中提取 SQL 查詢"""
        # 移除代碼塊標記
        text = re.sub(r"```sql\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```\s*", "", text)

        # 查找 SQL 關鍵字
        sql_keywords = ["SELECT", "WITH", "INSERT", "UPDATE"]
        lines = text.split("\n")
        sql_lines = []

        in_sql = False
        for line in lines:
            line_upper = line.strip().upper()
            if any(line_upper.startswith(kw) for kw in sql_keywords):
                in_sql = True
            if in_sql:
                sql_lines.append(line)
                # 如果遇到分號，結束 SQL
                if line.strip().endswith(";"):
                    break

        sql = "\n".join(sql_lines).strip()
        if not sql:
            # 如果沒有找到 SQL，返回整個文本
            sql = text.strip()

        # 移除末尾的分號（如果有的話）
        if sql.endswith(";"):
            sql = sql[:-1]

        return sql

    def _validate_sql(self, sql: str, database_type: str) -> tuple[str, List[str]]:
        """驗證和優化 SQL"""
        warnings: List[str] = []
        validated_sql = sql

        # 檢查危險操作
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"]
        sql_upper = sql.upper()
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                warnings.append(f"檢測到危險操作關鍵字: {keyword}")

        # 檢查 SQL 注入風險
        if "'" in sql or '"' in sql:
            # 檢查是否有未參數化的字符串
            if "?" not in sql and "$" not in sql:
                warnings.append("建議使用參數化查詢以防止 SQL 注入")

        # 基本語法檢查
        if not sql_upper.strip().startswith("SELECT"):
            warnings.append("只允許 SELECT 查詢")

        return validated_sql, warnings

    def _extract_parameters(self, sql: str) -> List[str]:
        """提取 SQL 參數"""
        parameters = []
        # 查找參數佔位符
        param_pattern = r"\?|\$(\d+)"
        matches = re.findall(param_pattern, sql)
        if matches:
            # 如果是數字參數（$1, $2），提取數字
            for match in matches:
                if match:
                    parameters.append(f"param_{match}")
                else:
                    parameters.append("param")
        return parameters

    def _calculate_confidence(self, sql: str, natural_language: str) -> float:
        """計算置信度（簡單實現）"""
        # 基本檢查
        if not sql or len(sql) < 10:
            return 0.3

        # 檢查是否包含 SELECT
        if "SELECT" not in sql.upper():
            return 0.2

        # 檢查 SQL 長度（太短可能不完整）
        if len(sql) < 20:
            return 0.5

        # 基本置信度
        confidence = 0.7

        # 如果有參數化查詢，提高置信度
        if "?" in sql or "$" in sql:
            confidence += 0.1

        # 如果有 WHERE 子句，提高置信度
        if "WHERE" in sql.upper():
            confidence += 0.1

        return min(1.0, confidence)

    def _generate_explanation(self, sql: str, natural_language: str) -> str:
        """生成 SQL 說明"""
        return f"將自然語言查詢「{natural_language}」轉換為 SQL: {sql[:100]}..."
