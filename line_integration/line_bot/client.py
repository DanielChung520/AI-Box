# 代碼功能說明: LINE Bot 客戶端 - 處理 LINE 訊息和 Webhook
# 創建日期: 2026-03-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-03

"""LINE Bot 服務模組

處理 LINE Messaging API 的 Webhook 事件，
並與 AI-Box Agent 整合。
"""

import logging
import os
from typing import Any, Dict, Optional

import httpx
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage

from line_integration.agents.base import AgentType
from line_integration.line_bot.router import get_agent_router
from line_integration.storage import get_chat_store

logger = logging.getLogger(__name__)


class LineBotClient:
    """LINE Bot 客戶端類別

    處理 LINE Webhook 事件，並將訊息轉發到 AI-Box Agent。
    每個 LINE 用戶會有獨立的持久化會話。
    """

    def __init__(
        self,
        channel_access_token: str,
        channel_secret: str,
    ):
        """初始化 LINE Bot 客戶端

        Args:
            channel_access_token: LINE Channel Access Token
            channel_secret: LINE Channel Secret
        """
        self.channel_access_token = channel_access_token
        self.channel_secret = channel_secret

        # 初始化 LINE Bot API
        self.api = LineBotApi(channel_access_token)
        self.handler = WebhookHandler(channel_secret)

        # 初始化存儲和路由器
        self.chat_store = get_chat_store()
        self.agent_router = get_agent_router()

        # 註冊事件處理器
        self._register_handlers()

    def _register_handlers(self) -> None:
        """註冊 LINE 事件處理器"""

        # 使用裝飾器方式註冊
        @self.handler.add(MessageEvent, message=TextMessage)
        def handle_text_message(event: MessageEvent):
            """處理文字訊息"""
            # 這裡需要同步調用異步函數
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果在異步環境中，創建任務
                    asyncio.create_task(self._handle_text_message(event))
                else:
                    loop.run_until_complete(self._handle_text_message(event))
            except Exception as e:
                logger.error(f"Error handling text message: {e}", exc_info=True)

    async def _handle_text_message(self, event: MessageEvent) -> None:
        """處理文字訊息

        Args:
            event: LINE MessageEvent
        """
        user_id = event.source.user_id
        text = event.message.text

        logger.info(f"Received text message from {user_id}: {text}")

        # 獲取或創建會話
        session = self._get_or_create_session(user_id)
        session_id = session["session_id"]
        agent_type = session.get("agent_type", AgentType.MM_AGENT)

        # 儲存用戶訊息
        self.chat_store.add_message(
            session_id=session_id,
            role="user",
            content=text,
        )

        # 獲取對話歷史
        history = self.chat_store.get_conversation_history(session_id, limit=10)

        # 調用 Agent
        try:
            response = await self.agent_router.route(
                agent_type=agent_type,
                instruction=text,
                session_id=session_id,
                user_id=user_id,
                conversation_history=history,
            )

            # 解析 Agent 回覆
            content = self._parse_agent_response(response)

            # 儲存機器人回覆
            self.chat_store.add_message(
                session_id=session_id,
                role="assistant",
                content=content,
            )

            # 回覆訊息到 LINE
            self.api.reply_message(event.reply_token, TextMessage(text=content))

        except Exception as e:
            logger.error(f"Error calling Agent: {e}", exc_info=True)
            # 發送錯誤訊息
            self.api.reply_message(
                event.reply_token, TextMessage(text="抱歉，處理您的訊息時發生錯誤。")
            )

    def _get_or_create_session(self, user_id: str) -> Dict[str, Any]:
        """獲取或創建用戶會話

        Args:
            user_id: LINE 用戶 ID

        Returns:
            會話資訊
        """
        # 嘗試獲取現有會話
        session = self.chat_store.get_session_by_user(user_id)

        if session is None:
            # 創建新會話（預設使用 MM-Agent）
            session = self.chat_store.create_session(
                user_id=user_id,
                agent_type=AgentType.MM_AGENT,
            )
            logger.info(f"Created new session for user {user_id}")

        return session

    def _parse_agent_response(self, response: Dict[str, Any]) -> str:
        """解析 Agent 回覆

        Args:
            response: Agent 回覆

        Returns:
            回覆內容
        """
        # 嘗試多種可能的回覆格式
        if isinstance(response, dict):
            # 格式 1: result.content
            content = response.get("result", {}).get("content")
            if content:
                return content

            # 格式 2: result.message
            content = response.get("result", {}).get("message")
            if content:
                return content

            # 格式 3: 直接 content
            content = response.get("content")
            if content:
                return content

            # 格式 4: status error
            if response.get("status") == "error":
                return response.get("message", "無法處理您的請求")

        return "無法處理您的請求"

    def handle_webhook(self, body: bytes, signature: str) -> Dict[str, Any]:
        """處理 LINE Webhook 請求

        Args:
            body: Webhook 請求體（原始 bytes）
            signature: X-Line-Signature header

        Returns:
            處理結果

        Raises:
            InvalidSignatureError: signature 驗證失敗
        """
        try:
            self.handler.handle(body, signature)
            return {"status": "ok", "message": "Webhook handled successfully"}
        except InvalidSignatureError as e:
            logger.error(f"Invalid signature: {e}")
            raise
        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            raise


# 單例實例
_line_bot_client: Optional[LineBotClient] = None


def get_line_bot_client() -> LineBotClient:
    """獲取 LINE Bot 客戶端單例

    Returns:
        LineBotClient 實例
    """
    global _line_bot_client

    if _line_bot_client is None:
        channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        channel_secret = os.getenv("LINE_CHANNEL_SECRET")

        if not channel_access_token or not channel_secret:
            raise ValueError("LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET must be set")

        _line_bot_client = LineBotClient(
            channel_access_token=channel_access_token,
            channel_secret=channel_secret,
        )

    return _line_bot_client
