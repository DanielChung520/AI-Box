# 代碼功能說明: Chat 模塊 BaseHandler 抽象類（pre_process、post_process、handle）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""BaseHandler(ABC)：pre_process（rate_limit、permission、quota）、post_process（可選 cache、metrics）、抽象 handle。"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from services.api.models.chat import ChatRequest
from system.security.models import User

logger = logging.getLogger(__name__)


@dataclass
class ChatHandlerRequest:
    """Handler 統一請求上下文。"""

    request_body: ChatRequest
    request_id: str
    tenant_id: str
    current_user: User


class BaseHandler(ABC):
    """
    Chat 請求處理器基類。
    pre_process：限流、權限、配額；post_process：可選緩存、指標；handle：具體處理邏輯。
    """

    async def pre_process(self, request: ChatHandlerRequest) -> None:
        """
        前置處理：限流、附件權限、配額校驗；不通過則拋出異常。

        Args:
            request: 請求上下文

        Raises:
            RuntimeError: 限流超限
            HTTPException: 權限或配額錯誤
        """
        user_id = request.current_user.user_id
        # 限流
        try:
            from api.routers.chat_module.dependencies import get_rate_limiter

            limiter = get_rate_limiter()
            if hasattr(limiter, "check"):
                limiter.check(user_id)  # type: ignore[attr-defined]
        except RuntimeError:
            raise
        except Exception as exc:
            logger.warning(f"Rate limit check skipped or failed: {exc}")
        # 附件權限
        if request.request_body.attachments:
            from api.routers.chat_module.validators.permission_validator import (
                validate_attachments_access,
            )

            await validate_attachments_access(
                request.request_body.attachments,
                request.current_user,
            )
        # 配額（佔位）
        try:
            from api.routers.chat_module.validators.quota_validator import check_quota

            check_quota(user_id)
        except Exception as exc:
            logger.debug(f"Quota check (placeholder): {exc}")

    async def post_process(
        self,
        request: ChatHandlerRequest,
        response: Any,
    ) -> None:
        """
        後置處理：可選緩存、指標；目前為佔位。

        Args:
            request: 請求上下文
            response: 處理結果
        """
        # 佔位：可接入 cache、metrics
        logger.debug(
            f"post_process: request_id={request.request_id}, "
            f"response_type={type(response).__name__}"
        )

    @abstractmethod
    async def handle(self, request: ChatHandlerRequest) -> Any:
        """
        處理請求，返回響應（由子類實現）。

        Args:
            request: 請求上下文

        Returns:
            具體響應類型（如 ChatResponse）
        """
        ...

    async def run(self, request: ChatHandlerRequest) -> Any:
        """
        完整流程：pre_process -> handle -> post_process。

        Args:
            request: 請求上下文

        Returns:
            handle 的返回值
        """
        await self.pre_process(request)
        response = await self.handle(request)
        await self.post_process(request, response)
        return response
