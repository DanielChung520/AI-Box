# 代碼功能說明: v5 簡化版 LLM SQL 生成服務
# 創建日期: 2026-03-02
# 創建人: Daniel Chung
# 用途: v5 端點使用，直接調用 LLM 生成 SQL

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("MOE_CHAT_MODEL", "llama3.2:3b-instruct-q4_0")

# 模型路由配置
COMPLEX_MODEL = "gpt-oss:120b"
SIMPLE_MODEL = "llama3:8b"

COMPLEX_KEYWORDS = ["最大", "最多", "最少", "最低", "最高", "排序", "前", "名", "佔比", "比例", "比較"]

def select_model(nlq: str) -> str:
    for keyword in COMPLEX_KEYWORDS:
        if keyword in nlq:
            return COMPLEX_MODEL
    return SIMPLE_MODEL

# Schema 定义
SIMPLE_SCHEMA = """
## 可用表格：

### mart_inventory_wide（庫存資料）
  欄位名稱 | 類型 | 說明 |
|---------|------|------|
| item_no | VARCHAR | 料號 |
| warehouse_no | VARCHAR | 倉庫編號 |
| location_no | VARCHAR | 儲位 |
| unit | VARCHAR | 單位 |
| existing_stocks | DOUBLE | 現有庫存 |
"""

SYSTEM_PROMPT = f"""你是 SQL 專家。根據用戶的自然語言查詢，生成 DuckDB SQL。

{SIMPLE_SCHEMA}

## 重要規則：
1. 只使用上述表格的實際欄位名稱
2. 禁止使用任何其他欄位
3. 禁止使用 JOIN
4. 禁止使用子查詢
5. 簡單 SQL：SELECT * FROM table WHERE column = 'value'
6. 只使用 SELECT 語句（只讀）

## return_mode 參數：
- list: SELECT * FROM table WHERE condition LIMIT 1000
- summary: 使用 GROUP BY 聚合

## 輸出格式：
直接輸出 SQL，不要包含任何解釋或 markdown 標記。

## 範例：
- 輸入: "查詢料號 8021107404500002 的庫存"
- 輸出: SELECT * FROM mart_inventory_wide WHERE item_no = '8021107404500002' LIMIT 1000

- 輸入: "查詢每個倉庫的庫存總量"
- 輸出: SELECT warehouse_no, SUM(existing_stocks) as total FROM mart_inventory_wide GROUP BY warehouse_no

## Top-N 查詢（如最大/最多）：
- 「最大庫存的料號」→ GROUP BY item_no ORDER BY SUM(stock) DESC LIMIT 1
- 「前10名」→ ORDER BY SUM(stock) DESC LIMIT 10
"""

class SimpleLLMSQLGenerator:
    def __init__(
        self,
        ollama_host: str = DEFAULT_OLLAMA_HOST,
        model: str = DEFAULT_MODEL,
    ):
        self.ollama_host = ollama_host
        self.model = model
        self.client = httpx.Client(timeout=60.0)

    def generate_sql(
        self,
        nlq: str,
        return_mode: str = "summary",
        model: str = None,
    ) -> Dict[str, Any]:
        # 根據複雜度選擇模型
        selected_model = select_model(nlq) if not model else model
        
        user_prompt = f"用戶查詢：{nlq}\nreturn_mode：{return_mode}"

        try:
            response = self.client.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": selected_model,
                    "prompt": user_prompt,
                    "system": SYSTEM_PROMPT,
                    "stream": False,
                },
            )
            response.raise_for_status()
            result = response.json()
            sql = result.get("response", "").strip()
            
            # 清理 SQL
            sql = sql.replace("```sql", "").replace("```", "").strip()
            
            logger.info(f"v5 generated SQL: {sql[:100]}...")

            return {
                "status": "success",
                "sql": sql,
            }

        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

_generator = None

def get_llm_sql_generator() -> SimpleLLMSQLGenerator:
    global _generator
    if _generator is None:
        _generator = SimpleLLMSQLGenerator()
    return _generator
