# 代碼功能說明: LINE Bot 服務模組初始化
# 創建日期: 2026-03-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-03

"""LINE Bot 服務模組

處理 LINE Messaging API 的 Webhook 事件，
並與 AI-Box Chat API 整合。
"""

from line_integration.line_bot.client import LineBotClient, get_line_bot_client

__all__ = ["LineBotClient", "get_line_bot_client"]
