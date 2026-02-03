# 代碼功能說明: 異步 Chat 請求存儲（request_id、status、result）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""存儲異步請求狀態與結果（MVP 記憶體；可後續換 Redis）。"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class AsyncRequestRecord:
    """單條異步請求記錄。"""

    request_id: str
    status: str  # pending | running | completed | failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    priority: str = "normal"
    task_id: Optional[str] = None
    executor: str = "memory"
    request_body: Optional[Dict[str, Any]] = None  # 用於 retry 還原 ChatRequest
    tenant_id: Optional[str] = None


_store: Dict[str, AsyncRequestRecord] = {}
_lock = asyncio.Lock()


def _iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(tz=timezone.utc).isoformat()


async def create_async_request(
    priority: str = "normal",
    task_id: Optional[str] = None,
    request_body: Optional[Dict[str, Any]] = None,
    tenant_id: Optional[str] = None,
) -> str:
    """
    創建異步請求記錄，返回 request_id。

    Returns:
        request_id
    """
    request_id = str(uuid.uuid4())
    async with _lock:
        _store[request_id] = AsyncRequestRecord(
            request_id=request_id,
            status="pending",
            result=None,
            error=None,
            created_at=_iso_now(),
            updated_at=_iso_now(),
            priority=priority,
            task_id=task_id,
            executor="memory",
            request_body=request_body,
            tenant_id=tenant_id,
        )
    return request_id


async def get_async_request(request_id: str) -> Optional[AsyncRequestRecord]:
    """查詢異步請求狀態與結果。"""
    async with _lock:
        return _store.get(request_id)


async def set_async_request_status(
    request_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """更新異步請求狀態與結果。"""
    async with _lock:
        rec = _store.get(request_id)
        if rec:
            rec.status = status
            rec.result = result
            rec.error = error
            rec.updated_at = _iso_now()


async def run_async_chat_task(
    request_id: str,
    request_body: Any,
    tenant_id: str,
    current_user: Any,
) -> None:
    """
    執行 pipeline.process 並更新 store（可被 Worker 或 start_async_chat_background 調用）。
    """
    from api.routers.chat_module.dependencies import get_chat_pipeline
    from api.routers.chat_module.handlers.base import ChatHandlerRequest

    await set_async_request_status(request_id, "running")
    try:
        pipeline = get_chat_pipeline()
        handler_req = ChatHandlerRequest(
            request_body=request_body,
            request_id=request_id,
            tenant_id=tenant_id,
            current_user=current_user,
        )
        response = await pipeline.process(handler_req)
        await set_async_request_status(
            request_id, "completed", result=response.model_dump(mode="json")
        )
    except Exception as exc:
        logger.exception(f"Async chat task failed: request_id={request_id}")
        await set_async_request_status(request_id, "failed", error=str(exc))


def start_async_chat_background(
    request_id: str,
    request_body: Any,
    tenant_id: str,
    current_user: Any,
) -> None:
    """
    在後台執行 pipeline.process 並更新 store（由 asyncio.create_task 調用）。
    需在已有事件循環的上下文中調用。
    """
    import asyncio

    asyncio.create_task(
        run_async_chat_task(request_id, request_body, tenant_id, current_user)
    )


async def set_async_request_priority(request_id: str, priority: str) -> bool:
    """更新優先級；存在則返回 True。"""
    async with _lock:
        rec = _store.get(request_id)
        if rec:
            rec.priority = priority
            rec.updated_at = _iso_now()
            return True
    return False


def record_to_response(rec: AsyncRequestRecord) -> Dict[str, Any]:
    """轉為 API 響應體。"""
    return {
        "request_id": rec.request_id,
        "status": rec.status,
        "result": rec.result,
        "error": rec.error,
        "priority": rec.priority,
        "task_id": rec.task_id,
        "executor": rec.executor,
        "created_at": rec.created_at,
        "updated_at": rec.updated_at,
    }
