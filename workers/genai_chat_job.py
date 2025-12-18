"""
代碼功能說明: RQ Job - 執行 GenAI Chat 非同步請求（供長任務/Agent 使用）
創建日期: 2025-12-13 22:26:20 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 23:34:17 (UTC+8)
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from services.api.models.chat import ChatRequest
from system.security.models import User


def run_genai_chat_request(
    request_id: str,
    request_dict: Dict[str, Any],
    tenant_id: str,
    user_dict: Dict[str, Any],
) -> None:
    """RQ 入口：同步函數包一層 asyncio.run。"""

    # 延遲 import，避免 worker 啟動時拉入過多依賴
    from api.routers.chat import _run_async_request

    request_body = ChatRequest.model_validate(request_dict)
    current_user = User(**user_dict)

    asyncio.run(
        _run_async_request(
            request_id=str(request_id),
            request_body=request_body,
            tenant_id=str(tenant_id),
            current_user=current_user,
        )
    )
