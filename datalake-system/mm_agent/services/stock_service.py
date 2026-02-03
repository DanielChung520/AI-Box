# 代碼功能說明: 庫存查詢服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-31

"""庫存查詢服務 - 通過 Data-Agent 查詢庫存信息"""

import logging
import os
from typing import Any, Dict, Optional

from agents.services.protocol.base import AgentServiceRequest

from mm_agent.data_agent_client import DataAgentClient

logger = logging.getLogger(__name__)


class StockService:
    """庫存查詢服務 - 通過 Data-Agent 查詢庫存信息"""

    def __init__(
        self,
        data_agent_client: Optional[DataAgentClient] = None,
    ) -> None:
        """初始化庫存查詢服務

        Args:
            data_agent_client: Data-Agent 客戶端（可選，如果不提供則自動創建）
        """
        self._data_agent_client = data_agent_client or DataAgentClient()
        self._logger = logger

    async def query_stock_info(
        self,
        part_number: str,
        warehouse: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """查詢庫存信息

        Args:
            part_number: 料號
            warehouse: 倉庫代碼（可選）
            user_id: 用戶 ID（可選）

        Returns:
            庫存信息

        Raises:
            ValueError: 查詢失敗或庫存不存在時拋出異常
        """
        try:
            where_conditions = [f"img01 = '{part_number}'"]
            if warehouse:
                where_conditions.append(f"img02 = '{warehouse}'")

            where_clause = " AND ".join(where_conditions)
            sql_query = f"""
                SELECT img01 as part_number, img02 as warehouse,
                       img04 as quantity, img05 as unit,
                       img09 as last_update
                FROM img_file
                WHERE {where_clause}
                LIMIT 10
            """

            result = await self._data_agent_client.execute_sql_on_datalake(
                sql_query=sql_query,
                max_rows=10,
                user_id=user_id,
            )

            if not result.get("success"):
                error_msg = result.get("error", "查詢庫存信息失敗")
                raise ValueError(f"查詢庫存信息失敗: {error_msg}")

            rows = result.get("rows", [])
            if not rows:
                raise ValueError(f"查無此料號的庫存資料: {part_number}")

            stock_info = rows[0]
            return stock_info

        except ValueError:
            raise
        except Exception as e:
            self._logger.error(f"查詢庫存信息失敗: part_number={part_number}, error={e}")
            raise ValueError(f"查詢庫存信息失敗: {e}")

    async def query_transactions(
        self,
        part_number: str,
        tlf19: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """查詢交易歷史

        Args:
            part_number: 料號
            tlf19: 交易類別（101/102/201/202/301）
            start_date: 開始日期
            end_date: 結束日期
            user_id: 用戶 ID
            limit: 最大返回行數

        Returns:
            交易歷史列表
        """
        try:
            where_conditions = [f"tlf02 = '{part_number}'"]

            if tlf19:
                where_conditions.append(f"tlf19 = '{tlf19}'")

            if start_date:
                where_conditions.append(f"tlf11 >= '{start_date}'")

            if end_date:
                where_conditions.append(f"tlf11 <= '{end_date}'")

            where_clause = " AND ".join(where_conditions)
            sql_query = f"""
                SELECT tlf01 as seq, tlf02 as part_number, tlf19 as transaction_type,
                       tlf11 as trans_date, tlf13 as quantity, tlf14 as unit,
                       tlf17 as warehouse, tlf20 as source
                FROM tlf_file
                WHERE {where_clause}
                ORDER BY tlf11 DESC
                LIMIT {limit}
            """

            result = await self._data_agent_client.execute_sql_on_datalake(
                sql_query=sql_query,
                max_rows=limit,
                user_id=user_id,
            )

            if not result.get("success"):
                error_msg = result.get("error", "查詢交易歷史失敗")
                raise ValueError(f"查詢交易歷史失敗: {error_msg}")

            rows = result.get("rows", [])
            total_quantity = sum(row.get("quantity", 0) for row in rows)

            return {
                "transactions": rows,
                "total_quantity": total_quantity,
                "count": len(rows),
            }

        except ValueError:
            raise
        except Exception as e:
            self._logger.error(f"查詢交易歷史失敗: part_number={part_number}, error={e}")
            raise ValueError(f"查詢交易歷史失敗: {e}")

    async def query_purchase(
        self,
        part_number: str,
        month: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """查詢採購進貨記錄（tlf19=101）

        Args:
            part_number: 料號
            month: 月份（格式: YYYY-MM）
            user_id: 用戶 ID

        Returns:
            採購進貨記錄
        """
        try:
            date_condition = ""
            if month:
                date_condition = f"AND tlf11 LIKE '{month}%'"

            sql_query = f"""
                SELECT tlf01 as seq, tlf02 as part_number, tlf11 as trans_date,
                       tlf13 as quantity, tlf14 as unit, tlf17 as warehouse
                FROM tlf_file
                WHERE tlf02 = '{part_number}'
                  AND tlf19 = '101'
                  {date_condition}
                ORDER BY tlf11 DESC
                LIMIT 50
            """

            result = await self._data_agent_client.execute_sql_on_datalake(
                sql_query=sql_query,
                max_rows=50,
                user_id=user_id,
            )

            if not result.get("success"):
                error_msg = result.get("error", "查詢採購記錄失敗")
                raise ValueError(f"查詢採購記錄失敗: {error_msg}")

            rows = result.get("rows", [])
            total_quantity = sum(row.get("quantity", 0) for row in rows)

            return {
                "transactions": rows,
                "total_quantity": total_quantity,
                "transaction_type": "101",
                "transaction_description": "採購進貨",
            }

        except ValueError:
            raise
        except Exception as e:
            self._logger.error(f"查詢採購記錄失敗: part_number={part_number}, error={e}")
            raise ValueError(f"查詢採購記錄失敗: {e}")

    async def query_sales(
        self,
        part_number: str,
        month: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """查詢銷售出庫記錄（tlf19=202）

        Args:
            part_number: 料號
            month: 月份（格式: YYYY-MM）
            user_id: 用戶 ID

        Returns:
            銷售出庫記錄
        """
        try:
            date_condition = ""
            if month:
                date_condition = f"AND tlf11 LIKE '{month}%'"

            sql_query = f"""
                SELECT tlf01 as seq, tlf02 as part_number, tlf11 as trans_date,
                       tlf13 as quantity, tlf14 as unit, tlf17 as warehouse
                FROM tlf_file
                WHERE tlf02 = '{part_number}'
                  AND tlf19 = '202'
                  {date_condition}
                ORDER BY tlf11 DESC
                LIMIT 50
            """

            result = await self._data_agent_client.execute_sql_on_datalake(
                sql_query=sql_query,
                max_rows=50,
                user_id=user_id,
            )

            if not result.get("success"):
                error_msg = result.get("error", "查詢銷售記錄失敗")
                raise ValueError(f"查詢銷售記錄失敗: {error_msg}")

            rows = result.get("rows", [])
            total_quantity = sum(row.get("quantity", 0) for row in rows)

            return {
                "transactions": rows,
                "total_quantity": total_quantity,
                "transaction_type": "202",
                "transaction_description": "銷售出庫",
            }

        except ValueError:
            raise
        except Exception as e:
            self._logger.error(f"查詢銷售記錄失敗: part_number={part_number}, error={e}")
            raise ValueError(f"查詢銷售記錄失敗: {e}")


if __name__ == "__main__":
    import asyncio

    async def test_stock_service():
        """測試庫存查詢服務"""
        service = StockService()

        print("=" * 60)
        print("測試庫存查詢服務")
        print("=" * 60)

        print("\n1. 測試查詢庫存:")
        try:
            result = await service.query_stock_info("RM05-008")
            print(f"   成功: {result}")
        except ValueError as e:
            print(f"   預期錯誤: {e}")

        print("\n2. 測試查詢採購:")
        try:
            result = await service.query_purchase("RM05-008", month="2026-01")
            print(f"   成功: total_quantity={result.get('total_quantity')}")
        except ValueError as e:
            print(f"   預期錯誤: {e}")

        print("\n測試完成")

    asyncio.run(test_stock_service())
