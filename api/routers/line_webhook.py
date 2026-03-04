# 代碼功能說明: LINE Webhook API 路由
# 創建日期: 2026-03-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-03

"""LINE Webhook API 路由

處理 LINE Messaging API 的 Webhook 請求。
"""

import logging

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse
from linebot.exceptions import InvalidSignatureError

from line_integration.line_bot import get_line_bot_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/line", tags=["line"])


@router.post("/webhook")
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(None, alias="X-Line-Signature"),
) -> JSONResponse:
    """LINE Webhook 端點

    處理來自 LINE Platform 的 Webhook 請求。

    Args:
        request: FastAPI 請求對象
        x_line_signature: LINE 簽名驗證頭

    Returns:
        JSON 響應
    """
    # 獲取請求體（原始 bytes）
    body = await request.body()

    # 記錄調試信息
    logger.info(f"Received LINE webhook, signature: {x_line_signature}")
    logger.debug(f"Webhook body length: {len(body)} bytes")

    # 檢查簽名
    if not x_line_signature:
        logger.warning("Missing X-Line-Signature header")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Missing signature"},
        )

    try:
        # 獲取 LINE Bot 客戶端
        line_bot = get_line_bot_client()

        # 處理 Webhook
        result = line_bot.handle_webhook(body, x_line_signature)

        return JSONResponse(status_code=status.HTTP_200_OK, content=result)

    except InvalidSignatureError as e:
        logger.error(f"Invalid signature: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid signature"},
        )

    except ValueError as e:
        # 環境變數未設置
        logger.error(f"Configuration error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Bot not configured"},
        )

    except Exception as e:
        logger.error(f"Error handling webhook: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"},
        )


@router.get("/webhook")
async def line_webhook_verify() -> JSONResponse:
    """LINE Webhook 驗證端點

    用於 LINE Platform 驗證 Webhook URL 是否正確設定。

    Returns:
        JSON 響應
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ok",
            "message": "LINE Webhook endpoint is active",
        },
    )
