# 代碼功能說明: 庫存服務存根（臨時解決方案）
# 創建日期: 2026-02-12
# 創建人: Daniel Chung

"""庫存服務 - 存根文件

此文件為臨時存根，用於讓 MM-Agent 正常載入。
StockService 的功能已由 Data-Agent 的 StructuredQueryHandler 接管。
"""


class StockService:
    """庫存服務存根"""

    def __init__(self):
        """初始化"""
        pass

    async def query_stock_info(self, part_number: str, user_id: str = None) -> dict:
        """查詢庫存信息

        注意：此方法已棄用，請使用 Data-Agent 的 StructuredQueryHandler
        """
        return {"success": False, "error": "StockService 已棄用，請使用 Data-Agent"}

    async def query_purchase(self, part_number: str, user_id: str = None) -> dict:
        """查詢採購記錄

        注意：此方法已棄用，請使用 Data-Agent 的 StructuredQueryHandler
        """
        return {"success": False, "error": "StockService 已棄用，請使用 Data-Agent"}
