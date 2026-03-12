# 代碼功能說明: 料號查詢服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-12

"""料號查詢服務 - 通過 DT-Agent 直接查詢物料信息"""

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PartService:
    """料號查詢服務"""

    def __init__(
        self,
    ) -> None:
        """初始化料號查詢服務"""
        self._logger = logger

    async def query_part_info(
        self,
        part_number: str,
    ) -> Dict[str, Any]:
        """查詢物料信息

        直接調用 DT-Agent 的 /api/v1/dt-agent/execute 端點進行查詢。

        Args:
            part_number: 料號

        Returns:
            物料信息
        """
        try:
            import httpx

            # 直接調用 DT-Agent /api/v1/dt-agent/execute 端點
            data_agent_url = os.getenv("DT_AGENT_SERVICE_URL", os.getenv("DATA_AGENT_SERVICE_URL", "http://localhost:8005"))
            endpoint = f"{data_agent_url}/api/v1/dt-agent/execute"

            async with httpx.AsyncClient(timeout=60.0) as client:
                # 先嘗試供應商查詢
                response = await client.post(
                    endpoint,
                    json={
                        "task_id": f"part_query_{part_number}",
                        "task_type": "simple_query",
                        "task_data": {
                            "nlq": f"料號 {part_number} 的供應商是誰",
                            "module": "tiptop_jp",
                            "return_mode": "summary",
                        },
                    },
                )

                if response.status_code != 200:
                    raise ValueError(f"DT-Agent 調用失敗: HTTP {response.status_code}")

                result = response.json()

                if not result.get("success", False):
                    # 嘗試庫存查詢（回退）
                    stock_response = await client.post(
                        endpoint,
                        json={
                            "task_id": f"part_stock_{part_number}",
                            "task_type": "simple_query",
                            "task_data": {
                                "nlq": f"料號 {part_number} 的庫存數量",
                                "module": "tiptop_jp",
                                "return_mode": "summary",
                            },
                        },
                    )
                    stock_result = stock_response.json()
                    if stock_result.get("success", False):
                        stock_data = stock_result.get("data", [])
                        return {
                            "success": True,
                            "part_number": part_number,
                            "stock_info": stock_data,
                            "response": f"料號 {part_number} 查詢結果：\n庫存數據：{stock_data}",
                        }

                    raise ValueError(f"DT-Agent 查詢失敗: {result.get('message')}")

                # 提取查詢結果
                data = result.get("data", [])
                if not data:
                    # 嘗試庫存查詢（回退）
                    stock_response = await client.post(
                        endpoint,
                        json={
                            "task_id": f"part_stock_{part_number}",
                            "task_type": "simple_query",
                            "task_data": {
                                "nlq": f"料號 {part_number} 的庫存數量",
                                "module": "tiptop_jp",
                                "return_mode": "summary",
                            },
                        },
                    )
                    stock_result = stock_response.json()
                    if stock_result.get("success", False):
                        stock_data = stock_result.get("data", [])
                        return {
                            "success": True,
                            "part_number": part_number,
                            "stock_info": stock_data,
                            "response": f"料號 {part_number} 查詢結果：\n庫存數據：{stock_data}",
                        }

                    raise ValueError(f"查無料號 {part_number} 的資料")

                return {
                    "success": True,
                    "part_number": part_number,
                    "data": data,
                    "response": f"料號 {part_number} 查詢結果：\n{data}",
                }

        except Exception as e:
            self._logger.error(f"查詢物料信息失敗: part_number={part_number}, error={e}")
            raise
