"""
代碼功能說明: Chat 觀測性服務（新架構）
創建日期: 2026-01-28 12:40 UTC+8
創建人: Daniel Chung
最後修改日期: 2026-01-28 12:40 UTC+8

提取自 chat.py 的觀測性相關功能。
"""

from typing import Optional

from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from api.routers.chat_module.dependencies import get_context_manager
from services.api.services.genai_metrics_service import get_genai_metrics_service
from services.api.services.genai_trace_store_service import get_genai_trace_store_service
from system.security.models import User


def get_chat_observability_stats(current_user: User) -> JSONResponse:
    """
    G5：產品級 Chat 指標彙總（JSON）。

    Args:
        current_user: 當前用戶

    Returns:
        JSON 響應包含統計信息
    """
    metrics = get_genai_metrics_service()
    return APIResponse.success(
        data={"stats": metrics.get_stats(), "user_id": current_user.user_id},
        message="Chat observability stats retrieved",
    )


def get_chat_observability_trace(request_id: str, current_user: User) -> JSONResponse:
    """
    G5：依 request_id 回放事件序列（MVP：in-memory）。

    Args:
        request_id: 請求 ID
        current_user: 當前用戶

    Returns:
        JSON 響應包含追蹤事件
    """
    trace_store = get_genai_trace_store_service()
    events = trace_store.get_trace(request_id=str(request_id))
    return APIResponse.success(
        data={
            "request_id": request_id,
            "events": events,
            "user_id": current_user.user_id,
        },
        message="Chat trace retrieved",
    )


def get_chat_observability_recent(
    limit: int,
    current_user: User,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    event: Optional[str] = None,
) -> JSONResponse:
    """
    G5：列出最近 N 筆事件（MVP：in-memory）。

    Args:
        limit: 返回事件數量限制
        current_user: 當前用戶
        session_id: 會話 ID（可選）
        task_id: 任務 ID（可選）
        event: 事件類型（可選）

    Returns:
        JSON 響應包含最近的事件列表
    """
    trace_store = get_genai_trace_store_service()
    items = trace_store.list_recent(
        limit=limit,
        user_id=current_user.user_id,
        session_id=session_id,
        task_id=task_id,
        event=event,
    )
    return APIResponse.success(
        data={"events": items, "user_id": current_user.user_id},
        message="Recent chat observability events retrieved",
    )


def get_session_messages(
    session_id: str,
    current_user: User,
    limit: Optional[int] = None,
) -> JSONResponse:
    """
    G3：Session 回放（最小可用）。

    Args:
        session_id: 會話 ID
        current_user: 當前用戶
        limit: 消息數量限制（可選）

    Returns:
        JSON 響應包含會話消息
    """
    context_manager = get_context_manager()
    safe_limit = int(limit) if isinstance(limit, int) and limit and limit > 0 else None
    try:
        messages = context_manager.get_messages(session_id=session_id, limit=safe_limit)
        payload = [m.model_dump(mode="json") for m in messages]
    except Exception as exc:  # noqa: BLE001
        import structlog

        logger = structlog.get_logger(__name__)
        logger.warning(
            f"get_session_messages_failed: error={str(exc)}, "
            f"user_id={current_user.user_id}, session_id={session_id}"
        )
        payload = []
    return APIResponse.success(
        data={"session_id": session_id, "messages": payload},
        message="Session messages retrieved",
    )
