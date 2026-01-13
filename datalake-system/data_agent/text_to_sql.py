# 代碼功能說明: Text-to-SQL 轉換服務
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Text-to-SQL 轉換服務 - 將自然語言轉換為 SQL 查詢"""

import logging
import re
from typing import Any, Dict, List, Optional

from agents.task_analyzer.models import LLMProvider
from llm.clients.factory import get_client

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
    ) -> Dict[str, Any]:
        """
        將自然語言轉換為 SQL

        Args:
            natural_language: 自然語言查詢
            database_type: 數據庫類型（postgresql/mysql/sqlite）
            schema_info: 數據庫 Schema 信息（可選）
            context: 上下文信息（可選）

        Returns:
            轉換結果，包含 SQL 查詢、參數、置信度等
        """
        try:
            client = self._get_llm_client()
            if not client:
                raise RuntimeError("LLM client is not available")

            # 構建提示詞
            prompt = self._build_prompt(natural_language, database_type, schema_info)

            # 調用 LLM 生成 SQL
            result = await client.generate(
                prompt,
                temperature=0.3,  # 較低溫度以獲得更穩定的 SQL
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
        schema_info: Optional[Dict[str, Any]],
    ) -> str:
        """構建 LLM 提示詞"""
        prompt = f"""請將以下自然語言查詢轉換為 {database_type.upper()} SQL 查詢。

自然語言查詢：
{natural_language}

"""

        if schema_info:
            prompt += f"""數據庫 Schema 信息：
{self._format_schema_info(schema_info)}

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

        支持兩種格式：
        1. {"tables": [{"name": "users", "columns": [...]}]}  # 列表格式
        2. {"tables": {"users": {"columns": [...]}}}  # 字典格式
        """
        formatted = []
        tables = schema_info.get("tables")

        if tables is None:
            return ""

        # 處理字典格式：{"tables": {"users": {"columns": [...]}}}
        if isinstance(tables, dict):
            for table_name, table_info in tables.items():
                formatted.append(f"表 {table_name}:")
                columns = table_info.get("columns", [])
                for col in columns:
                    # 處理字符串列表格式：["id", "name", "age"]
                    if isinstance(col, str):
                        formatted.append(f"  - {col}")
                    # 處理字典格式：{"name": "id", "type": "string"}
                    elif isinstance(col, dict):
                        col_name = col.get("name", "")
                        col_type = col.get("type", "")
                        formatted.append(f"  - {col_name} ({col_type})")

        # 處理列表格式：{"tables": [{"name": "users", "columns": [...]}]}
        elif isinstance(tables, list):
            for table in tables:
                table_name = table.get("name", "")
                columns = table.get("columns", [])
                formatted.append(f"表 {table_name}:")
                for col in columns:
                    # 處理字符串列表格式
                    if isinstance(col, str):
                        formatted.append(f"  - {col}")
                    # 處理字典格式
                    elif isinstance(col, dict):
                        col_name = col.get("name", "")
                        col_type = col.get("type", "")
                        formatted.append(f"  - {col_name} ({col_type})")

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
