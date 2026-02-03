# 代碼功能說明: Data-Agent HTTP 客戶端
# 創建日期: 2026-01-29
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-31 UTC+8

"""Data-Agent HTTP 客戶端（同步版本，兼容 Streamlit）"""

from datetime import datetime
from typing import Any, Dict

import httpx

from dashboard.config import DATA_AGENT_URL


def call_data_agent_sync(
    natural_language: str,
    action: str = "query_datalake",
    **kwargs: Any,
) -> Dict[str, Any]:
    """同步調用 Data-Agent 進行查詢

    Args:
        natural_language: 自然語言查詢
        action: Data-Agent action (text_to_sql / query_datalake / execute_query /
                execute_sql_on_datalake)
        **kwargs: 其他參數

    Returns:
        Data-Agent 響應結果
    """
    task_data: Dict[str, Any] = {"action": action}

    if action == "text_to_sql":
        task_data.update(
            {
                "natural_language": natural_language,
                "database_type": kwargs.get("database_type", "postgresql"),
                "schema_info": kwargs.get("schema_info"),
                "intent_analysis": kwargs.get("intent_analysis"),
            }
        )
    elif action == "query_datalake":
        task_data.update(
            {
                "bucket": kwargs.get("bucket", "tiptop-raw"),
                "key": kwargs.get("key", ""),
                "query_type": kwargs.get("query_type", "table"),
            }
        )
    elif action == "execute_query":
        task_data.update({"sql_query": kwargs.get("sql_query", "")})
    elif action == "execute_sql_on_datalake":
        task_data.update({"sql_query_datalake": kwargs.get("sql_query_datalake", "")})

    request_body = {
        "task_id": f"dashboard_query_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "task_type": kwargs.get("task_type", "data_query"),
        "task_data": task_data,
        "metadata": {
            "source": "tiptop_dashboard",
            "timestamp": datetime.now().isoformat(),
        },
    }

    try:
        with httpx.Client(timeout=90.0) as http_client:
            response = http_client.post(
                DATA_AGENT_URL,
                json=request_body,
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        return {"error": "Data-Agent 請求超時"}
    except httpx.HTTPStatusError as e:
        return {"error": f"Data-Agent HTTP 錯誤: {e.response.status_code}"}
    except Exception as e:
        return {"error": f"Data-Agent 調用失敗: {str(e)}"}


async def call_data_agent(
    natural_language: str,
    action: str = "query_datalake",
    **kwargs: Any,
) -> Dict[str, Any]:
    """異步調用 Data-Agent（已棄用，請使用同步版本）"""
    return call_data_agent_sync(natural_language, action=action, **kwargs)
