# 代碼功能說明: Text-to-SQL 轉換服務
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-07

"""Text-to-SQL 轉換服務 - 將自然語言直接轉換為 SQL"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from agents.task_analyzer.models import LLMProvider
from llm.clients.factory import get_client

logger = logging.getLogger(__name__)


def load_schema_from_registry(schema_path: str = None) -> Dict[str, Any]:
    """從 schema_registry.json 加載 Schema 定義"""
    if schema_path is None:
        schema_path = ai_box_root / "datalake-system" / "metadata" / "schema_registry.json"

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        logger.info(f"已加載 Schema 定義: {len(schema.get('tables', {}))} 個表格")
        return schema
    except Exception as e:
        logger.error(f"加載 Schema 失敗: {e}")
        return {}


def generate_schema_prompt(schema: Dict[str, Any]) -> str:
    """根據 Schema 定義生成 Prompt"""

    prompt_parts = []
    prompt_parts.append("=== 資料庫 Schema ===\n")

    # 表格選擇規則
    prompt_parts.append("【表格選擇規則】")
    prompt_parts.append("- 查詢「料號、品名、規格」→ 使用 ima_file（物料主檔）")
    prompt_parts.append("- 查詢「庫存數量、倉庫、儲位」→ 使用 img_file（庫存明細檔）")
    prompt_parts.append("- 查詢「採購單、收料」→ 使用 pmm_file, pmn_file, rvb_file")
    prompt_parts.append("- 查詢「供應商」→ 使用 pmc_file")
    prompt_parts.append("- 查詢「客戶」→ 使用 cmc_file")
    prompt_parts.append("- 查詢「訂單」→ 使用 coptc_file, coptd_file")
    prompt_parts.append("- 查詢「價格」→ 使用 prc_file")
    prompt_parts.append("- 查詢「倉庫代號」→ 使用 imd_file")
    prompt_parts.append("")

    # 表格定義
    tables = schema.get("tables", {})
    for table_name, table_info in tables.items():
        prompt_parts.append(f"【{table_info.get('tiptop_name', table_name)}】{table_name}")
        for col in table_info.get("columns", []):
            col_desc = f"- {col['id']}: {col['name']}"
            if col.get("description"):
                col_desc += f" ({col['description']})"
            prompt_parts.append(col_desc)
        prompt_parts.append("")

    # Parquet 路徑
    prompt_parts.append("【Parquet 路徑】")
    prompt_parts.append("s3://tiptop-raw/raw/v1/{table}/year=*/month=*/data.parquet")
    prompt_parts.append("使用 hive_partitioning=true")
    prompt_parts.append("")

    # SQL 範例
    prompt_parts.append("【SQL 範例】")
    prompt_parts.append("")
    prompt_parts.append("範例 1 - 查詢料件主檔：")
    prompt_parts.append('"料號 10-0001 的品名"')
    prompt_parts.append(
        "SQL: SELECT ima01, ima02 FROM read_parquet('s3://tiptop-raw/raw/v1/ima_file/year=*/month=*/data.parquet', hive_partitioning=true) WHERE ima01 = '10-0001' LIMIT 10"
    )
    prompt_parts.append("")
    prompt_parts.append("範例 2 - 查詢所有成品：")
    prompt_parts.append('"查詢料號開頭為 10- 的成品"')
    prompt_parts.append(
        "SQL: SELECT ima01, ima02 FROM read_parquet('s3://tiptop-raw/raw/v1/ima_file/year=*/month=*/data.parquet', hive_partitioning=true) WHERE ima01 LIKE '10-%' AND ima08 = 'M' LIMIT 20"
    )
    prompt_parts.append("")
    prompt_parts.append("範例 3 - 查詢所有原料：")
    prompt_parts.append('"查詢所有原料"')
    prompt_parts.append(
        "SQL: SELECT ima01, ima02 FROM read_parquet('s3://tiptop-raw/raw/v1/ima_file/year=*/month=*/data.parquet', hive_partitioning=true) WHERE ima08 = 'P' LIMIT 20"
    )
    prompt_parts.append("")
    prompt_parts.append("範例 4 - 查詢庫存：")
    prompt_parts.append('"W01 原料倉的庫存"')
    prompt_parts.append(
        "SQL: SELECT img01, img02, img03, img10 FROM read_parquet('s3://tiptop-raw/raw/v1/img_file/year=*/month=*/data.parquet', hive_partitioning=true) WHERE img02 = 'W01' LIMIT 20"
    )
    prompt_parts.append("")
    prompt_parts.append("範例 5 - 查詢供應商：")
    prompt_parts.append('"查詢所有供應商"')
    prompt_parts.append(
        "SQL: SELECT pmc01, pmc03 FROM read_parquet('s3://tiptop-raw/raw/v1/pmc_file/year=*/month=*/data.parquet', hive_partitioning=true) LIMIT 20"
    )
    prompt_parts.append("")
    prompt_parts.append("範例 6 - 查詢客戶：")
    prompt_parts.append('"查詢所有客戶"')
    prompt_parts.append(
        "SQL: SELECT cmc01, cmc02 FROM read_parquet('s3://tiptop-raw/raw/v1/cmc_file/year=*/month=*/data.parquet', hive_partitioning=true) LIMIT 20"
    )
    prompt_parts.append("")
    prompt_parts.append("範例 7 - 採購進貨統計：")
    prompt_parts.append('"RM05-008 上月買進多少"')
    prompt_parts.append(
        "SQL: SELECT pmn04, ima02, SUM(CAST(pnm20 AS DECIMAL)) as total_qty FROM read_parquet('s3://tiptop-raw/raw/v1/pmn_file/year=*/month=*/data.parquet', hive_partitioning=true) LEFT JOIN read_parquet('s3://tiptop-raw/raw/v1/pmm_file/year=*/month=*/data.parquet', hive_partitioning=true) ON pmn01 = pmm01 LEFT JOIN read_parquet('s3://tiptop-raw/raw/v1/ima_file/year=*/month=*/data.parquet', hive_partitioning=true) ON pmn04 = ima01 WHERE pmn04 = 'RM05-008' AND pmm02 >= DATE '2024-12-01' AND pmm02 < DATE '2025-02-01' GROUP BY pmn04, ima02"
    )
    prompt_parts.append("")
    prompt_parts.append("範例 8 - 每月統計：")
    prompt_parts.append('"2024年RM05-008每月的採購進貨筆數"')
    prompt_parts.append(
        "SQL: SELECT DATE_TRUNC('month', CAST(pmm02 AS DATE)) as month, COUNT(*) as procurement_count FROM read_parquet('s3://tiptop-raw/raw/v1/pmn_file/year=*/month=*/data.parquet', hive_partitioning=true) LEFT JOIN read_parquet('s3://tiptop-raw/raw/v1/pmm_file/year=*/month=*/data.parquet', hive_partitioning=true) ON pmn01 = pmm01 WHERE pmn04 = 'RM05-008' AND CAST(pmm02 AS DATE) >= DATE '2024-01-01' AND CAST(pmm02 AS DATE) < DATE '2025-01-01' GROUP BY DATE_TRUNC('month', CAST(pmm02 AS DATE)) ORDER BY month"
    )
    prompt_parts.append("")
    prompt_parts.append("範例 9 - 所有負庫存：")
    prompt_parts.append('"列出所有負庫存的物料"')
    prompt_parts.append(
        "SQL: SELECT img01, img02, img03, img10 FROM read_parquet('s3://tiptop-raw/raw/v1/img_file/year=*/month=*/data.parquet', hive_partitioning=true) WHERE CAST(img10 AS DECIMAL) < 0 LIMIT 50"
    )
    prompt_parts.append("")
    prompt_parts.append("範例 10 - 按月份統計訂單：")
    prompt_parts.append('"按月份統計訂單數量"')
    prompt_parts.append(
        "SQL: SELECT DATE_TRUNC('month', CAST(coptc03 AS DATE)) AS month, COUNT(*) AS order_count FROM read_parquet('s3://tiptop-raw/raw/v1/coptc_file/year=*/month=*/data.parquet', hive_partitioning=true) GROUP BY DATE_TRUNC('month', CAST(coptc03 AS DATE)) ORDER BY month"
    )
    prompt_parts.append("")
    prompt_parts.append("範例 11 - 按供應商統計：")
    prompt_parts.append('"按供應商統計採購單數量"')
    prompt_parts.append(
        "SQL: SELECT pmm04 AS supplier, COUNT(*) AS order_count FROM read_parquet('s3://tiptop-raw/raw/v1/pmm_file/year=*/month=*/data.parquet', hive_partitioning=true) GROUP BY pmm04 ORDER BY order_count DESC"
    )
    prompt_parts.append("")
    prompt_parts.append("範例 12 - 按客戶統計訂單：")
    prompt_parts.append('"按客戶統計訂單金額"')
    prompt_parts.append(
        "SQL: SELECT coptc02 AS customer, SUM(CAST(coptd20 AS DECIMAL) * CAST(coptd30 AS DECIMAL)) AS total_amount FROM read_parquet('s3://tiptop-raw/raw/v1/coptc_file/year=*/month=*/data.parquet', hive_partitioning=true) AS coptc LEFT JOIN read_parquet('s3://tiptop-raw/raw/v1/coptd_file/year=*/month=*/data.parquet', hive_partitioning=true) AS coptd ON coptc.coptc01 = coptd.coptd01 GROUP BY coptc02 ORDER BY total_amount DESC"
    )
    prompt_parts.append("")

    # 重要規則
    prompt_parts.append("【重要】")
    prompt_parts.append("- **日期欄位類型是 VARCHAR，必須使用 CAST 轉換**")
    prompt_parts.append("- 錯誤写法：DATE_TRUNC('month', pmm02) (❌)")
    prompt_parts.append("- 正確認识：DATE_TRUNC('month', CAST(pmm02 AS DATE)) (✅)")
    prompt_parts.append("- 錯誤写法：pmm02 >= DATE '2024-01-01' (❌)")
    prompt_parts.append("- 正確認识：CAST(pmm02 AS DATE) >= DATE '2024-01-01' (✅)")
    prompt_parts.append("- GROUP BY 必須包含 DATE_TRUNC 完整表達式，不能只寫別名")
    prompt_parts.append("- 錯誤写法：GROUP BY month (❌ where month is an alias)")
    prompt_parts.append("- 正確認识：GROUP BY DATE_TRUNC('month', CAST(coptc03 AS DATE)) (✅)")
    prompt_parts.append("- 關聯表用 LEFT JOIN")
    prompt_parts.append("- GROUP BY 要包含所有非聚合欄位")
    prompt_parts.append("- 只返回 SQL，不要其他說明")
    prompt_parts.append("")

    # 嚴格要求 - 路徑格式
    prompt_parts.append("【嚴格要求 - 路徑格式】")
    prompt_parts.append("- 必須使用：year=*/month=*/data.parquet")
    prompt_parts.append("- 禁止使用：*/*/data.parquet 或 */*/*/data.parquet")
    prompt_parts.append("- 錯誤格式：s3://tiptop-raw/raw/v1/pmn_file/*/*/data.parquet (❌)")
    prompt_parts.append(
        "- 正確認识：s3://tiptop-raw/raw/v1/pmn_file/year=*/month=*/data.parquet (✅)"
    )
    prompt_parts.append("")

    # 嚴格要求 - Hive Partitioning
    prompt_parts.append("【嚴格要求 - Hive Partitioning】")
    prompt_parts.append("- 使用 hive_partitioning=true (不是 =>)")
    prompt_parts.append("- 錯誤語法：hive_partitioning => true (❌)")
    prompt_parts.append("- 正確認识：hive_partitioning=true (✅)")

    return "\n".join(prompt_parts)


class TextToSQLService:
    """Text-to-SQL 轉換服務 - 直接理解自然語言生成 SQL"""

    def __init__(self, llm_provider: Optional[LLMProvider] = None, schema_path: str = None):
        self._llm_provider = llm_provider or LLMProvider.OLLAMA
        self._llm_client = None
        self._logger = logger

        # 從 schema_registry.json 加載 Schema
        self._schema = load_schema_from_registry(schema_path)
        self._schema_prompt = generate_schema_prompt(self._schema)

    def _get_llm_client(self):
        """獲取 LLM client"""
        if self._llm_client is None:
            self._llm_client = get_client(self._llm_provider)
        return self._llm_client

    async def generate_sql(self, instruction: str) -> Dict[str, Any]:
        """直接從自然語言生成 SQL

        Args:
            instruction: 用戶輸入（自然語言）

        Returns:
            {'success': bool, 'sql': str, 'error': str}
        """
        try:
            client = self._get_llm_client()

            prompt = f"""{self._schema_prompt}

用戶問題：{instruction}

請直接生成可執行的 DuckDB SQL 查詢語句。

要求：
1. 只返回 SQL，不需要任何說明
2. 使用 DuckDB Parquet語法：read_parquet('s3://tiptop-raw/raw/v1/{{table}}/year=*/month=*/data.parquet', hive_partitioning=true)
3. 正確關聯表格（pmn ↔ pmm 用 pmn01=pmm01）
4. 正確處理日期欄位（可能是 VARCHAR，需要 CAST）
5. 如果用戶說"每月"，添加 GROUP BY DATE_TRUNC('month', 日期欄位)
6. 如果結果多於 10 筆，添加 LIMIT 10

SQL：
"""

            response = await client.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=800,
            )

            sql = response.get("text", "") or response.get("content", "")
            sql = sql.strip()
            sql = sql.replace("```sql", "").replace("```", "").strip()

            return {
                "success": True,
                "sql": sql,
                "error": None,
            }

        except Exception as e:
            self._logger.error(f"Text-to-SQL 失敗: {e}")
            return {
                "success": False,
                "sql": None,
                "error": str(e),
            }

    async def convert(self, natural_language: str, **kwargs) -> Dict[str, Any]:
        """轉換自然語言為 SQL（兼容舊接口）"""
        return await self.generate_sql(natural_language)
