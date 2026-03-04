# 代碼功能說明: 存儲服務模組
# 創建日期: 2026-03-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-03

"""LINE Chat 存儲服務模組

提供 LINE 對話的持久化存儲功能。
"""

from line_integration.storage.chat_store import ChatStore, get_chat_store

__all__ = ["ChatStore", "get_chat_store"]
