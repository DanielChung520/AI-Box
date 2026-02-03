"""
代碼功能說明: Chat 路由模塊化結構（新架構）
創建日期: 2026-01-28 12:40 UTC+8
創建人: Daniel Chung
最後修改日期: 2026-01-28 12:40 UTC+8

此模塊提供重構後的 Chat API 路由結構，保留原有 chat.py 的向後兼容性。
"""

from api.routers.chat_module.router import router

__all__ = ["router"]
