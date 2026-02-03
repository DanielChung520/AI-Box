# 代碼功能說明: Chat 模塊 Handlers（BaseHandler、SyncHandler 等）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""Handlers 層：base、sync_handler、stream_handler、batch_handler。"""

from api.routers.chat_module.handlers.base import BaseHandler, ChatHandlerRequest
from api.routers.chat_module.handlers.sync_handler import SyncHandler
from api.routers.chat_module.handlers.stream_handler import StreamHandler

from . import base
from . import sync_handler
from . import stream_handler

__all__ = [
    "base",
    "sync_handler",
    "stream_handler",
    "BaseHandler",
    "ChatHandlerRequest",
    "SyncHandler",
    "StreamHandler",
]
