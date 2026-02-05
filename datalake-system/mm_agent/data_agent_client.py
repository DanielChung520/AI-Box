# 代碼功能說明: Data-Agent 客戶端
# 創建日期: 2026-01-31
# 創建人: Daniel Chung

"""Data-Agent 客戶端 - 統一調用 Data-Agent API"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

from agents.services.protocol.base import AgentServiceRequest

logger = logging.getLogger(__name__)


class DataAgentClient:
    """Data-Agent 客戶端 - 調用 Data-Agent API"""

    def __init__(self, service_url: Optional[str] = None):
        """初始化 Data-Agent 客戶端

        Args:
            service_url: Data-Agent 服務 URL（默認從環境變數讀取）
        """
        self._service_url = service_url or os.getenv(
            "DATA_AGENT_SERVICE_URL", "http://localhost:8004"
        )
        self._api_path = "/execute"
        self._timeout = 30.0
        self._logger = logger

    async def execute_action(
        self,
        action: str,
        parameters: Dict[str, Any],
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """執行 Data-Agent 操作

        Args:
            action: 操作類型（text_to_sql/execute_query/execute_sql_on_datalake 等）
            parameters: 操作參數
            user_id: 用戶 ID
            tenant_id: 租戶 ID
            timeout: 超時時間（秒）

        Returns:
            操作結果
        """
        request_data = {
            "action": action,
            **parameters,
            "user_id": user_id,
            "tenant_id": tenant_id,
        }

        return await self._call_api(request_data, timeout)

    async def text_to_sql(
        self,
        natural_language: str,
        schema_info: Optional[Dict[str, Any]] = None,
        intent_analysis: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """自然語言轉 SQL

        Args:
            natural_language: 自然語言查詢
            schema_info: 數據庫 Schema 信息
            intent_analysis: 意圖分析結果
            user_id: 用戶 ID
            tenant_id: 租戶 ID

        Returns:
            SQL 查詢結果
        """
        return await self.execute_action(
            action="text_to_sql",
            parameters={
                "natural_language": natural_language,
                "schema_info": schema_info,
                "intent_analysis": intent_analysis,
            },
            user_id=user_id,
            tenant_id=tenant_id,
        )

    async def execute_sql_on_datalake(
        self,
        sql_query: str,
        max_rows: int = 100,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """在 Datalake 上執行 SQL 查詢

        Args:
            sql_query: SQL 查詢語句
            max_rows: 最大返回行數
            user_id: 用戶 ID
            tenant_id: 租戶 ID
            timeout: 超時時間（秒）

        Returns:
            查詢結果
        """
        return await self.execute_action(
            action="execute_sql_on_datalake",
            parameters={
                "sql_query_datalake": sql_query,
                "max_rows": max_rows,
            },
            user_id=user_id,
            tenant_id=tenant_id,
            timeout=timeout,
        )

    async def query_datalake(
        self,
        bucket: str,
        key: str,
        query_type: str = "exact",
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """查詢 Datalake 數據

        Args:
            bucket: Bucket 名稱
            key: 數據鍵
            query_type: 查詢類型（exact/fuzzy）
            filters: 過濾條件
            user_id: 用戶 ID
            tenant_id: 租戶 ID

        Returns:
            查詢結果
        """
        return await self.execute_action(
            action="query_datalake",
            parameters={
                "bucket": bucket,
                "key": key,
                "query_type": query_type,
                "filters": filters,
            },
            user_id=user_id,
            tenant_id=tenant_id,
        )

    async def _call_api(
        self,
        request_data: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """調用 Data-Agent API

        Args:
            request_data: 請求數據
            timeout: 超時時間（秒）

        Returns:
            API 響應結果
        """
        url = f"{self._service_url}{self._api_path}"
        timeout = timeout or self._timeout

        action = request_data.get("action", "")
        self._logger.debug(f"調用 Data-Agent API: action={action}, url={url}")

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    json={
                        "task_id": f"mm-agent-{action}",
                        "task_type": "data_agent",
                        "task_data": request_data,
                        "metadata": {},
                    },
                )

                if response.status_code != 200:
                    error_msg = (
                        f"Data-Agent API 調用失敗: HTTP {response.status_code}, {response.text}"
                    )
                    self._logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                    }

                result = response.json()

                if not isinstance(result, dict):
                    return {
                        "success": False,
                        "error": f"Data-Agent API 響應格式錯誤: {type(result)}",
                    }

                if result.get("status") == "completed":
                    task_result = result.get("result", {})
                    if isinstance(task_result, dict):
                        if task_result.get("success", False):
                            inner_result = task_result.get("result", task_result)
                            if isinstance(inner_result, dict) and "rows" in inner_result:
                                return inner_result
                            return task_result
                        else:
                            return {
                                "success": False,
                                "error": task_result.get("error", "Data-Agent 操作失敗"),
                            }
                    return task_result
                else:
                    return {
                        "success": False,
                        "error": result.get("error", "Data-Agent 操作失敗"),
                    }

        except httpx.TimeoutException:
            error_msg = "Data-Agent API 調用超時"
            self._logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except httpx.RequestError as e:
            error_msg = f"Data-Agent API 請求錯誤: {e}"
            self._logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Data-Agent API 調用失敗: {e}"
            self._logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}


async def create_data_agent_client() -> DataAgentClient:
    """創建 Data-Agent 客戶端（異步工廠方法）

    Returns:
        DataAgentClient 實例
    """
    return DataAgentClient()


if __name__ == "__main__":
    import sys

    async def test_client():
        """測試 Data-Agent 客戶端"""
        client = DataAgentClient()

        print("=" * 60)
        print("測試 Data-Agent 客戶端")
        print("=" * 60)

        print("\n1. 測試 text_to_sql:")
        result = await client.text_to_sql(
            natural_language="查詢 RM05-008 的庫存數量",
            schema_info={"tables": ["img_file"]},
        )
        print(f"   成功: {result.get('success')}")
        if result.get("success"):
            print(f"   SQL: {result.get('result', {}).get('sql_query', 'N/A')[:100]}")
        else:
            print(f"   錯誤: {result.get('error')}")

        print("\n2. 測試 execute_sql_on_datalake:")
        result = await client.execute_sql_on_datalake(
            sql_query="SELECT img01, img02, img04 FROM img_file WHERE img01 = 'RM05-008' LIMIT 10",
            max_rows=10,
        )
        print(f"   成功: {result.get('success')}")
        if result.get("success"):
            print(f"   行數: {result.get('row_count', 0)}")
        else:
            print(f"   錯誤: {result.get('error')}")

        print("\n測試完成")

    try:
        asyncio.run(test_client())
    except KeyboardInterrupt:
        print("\n測試中斷")
        sys.exit(0)
