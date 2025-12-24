# 代碼功能說明: ChromaDB 自訂例外
# 創建日期: 2025-11-25 21:25 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 21:25 (UTC+8)


class ChromaDBError(Exception):
    """ChromaDB 模組通用例外"""


class ChromaDBConnectionError(ChromaDBError):
    """連線建立或取得失敗"""


class ChromaDBOperationError(ChromaDBError):
    """資料庫操作失敗"""
