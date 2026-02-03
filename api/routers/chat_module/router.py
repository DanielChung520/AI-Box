"""
代碼功能說明: Chat 路由模塊化版本（新架構）
創建日期: 2026-01-28 12:40 UTC+8
創建人: Daniel Chung
最後修改日期: 2026-01-28 12:40 UTC+8

這是重構後的 Chat 路由，使用模塊化結構。
階段二 a：統一錯誤處理、驗證、SyncHandler。階段三：stream、batch、requests、archive、tasks。
"""

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from api.core.response import APIResponse
from api.routers.chat_module.handlers import StreamHandler, SyncHandler
from api.routers.chat_module.handlers.base import ChatHandlerRequest
from api.routers.chat_module.handlers.batch_handler import BatchHandler
from api.routers.chat_module.models.request import BatchChatRequest
from api.routers.chat_module.services.async_request_store import (
    create_async_request,
    get_async_request,
    record_to_response,
    set_async_request_priority,
    set_async_request_status,
    start_async_chat_background,
)
from api.routers.chat_module.services.observability import (
    get_chat_observability_recent,
    get_chat_observability_stats,
    get_chat_observability_trace,
    get_session_messages,
)
from api.routers.chat_module.services.session_service import archive_session
from api.routers.chat_module.utils.error_helper import ErrorHandler
from api.routers.chat_module.validators.request_validator import validate_chat_request
from services.api.models.chat import ChatRequest
from system.security.dependencies import get_current_tenant_id, get_current_user
from system.security.models import User

logger = logging.getLogger(__name__)

# 創建路由
router = APIRouter(prefix="/chat", tags=["Chat"])


# ==================== 階段二 a：統一異常處理（T2a.4） ====================
# 注意：APIRouter 不支持 @router.exception_handler，異常在端點內捕獲並轉為統一錯誤體


def _chat_error_to_json_response(
    request_id: str,
    exc: Exception,
) -> JSONResponse:
    """將異常轉為規格統一的錯誤體 JSONResponse。"""
    if isinstance(exc, HTTPException):
        content = (
            exc.detail
            if isinstance(exc.detail, dict)
            else {"message": str(exc.detail), "request_id": request_id}
        )
        return JSONResponse(status_code=exc.status_code, content=content)
    http_exc = ErrorHandler.create_http_exception(exc, request_id=request_id)
    content = (
        http_exc.detail
        if isinstance(http_exc.detail, dict)
        else {"detail": str(http_exc.detail), "request_id": request_id}
    )
    return JSONResponse(status_code=http_exc.status_code, content=content)


class FavoriteModelsUpdateRequest(BaseModel):
    """收藏模型更新請求（MVP）。"""

    model_ids: List[str] = Field(default_factory=list, description="收藏 model_id 列表")


# ==================== 主聊天入口（V2，經 SyncHandler + 驗證 + 統一錯誤處理） ====================


@router.post("", status_code=status.HTTP_200_OK)
async def chat_product_v2(
    request_body: ChatRequest,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    產品級 Chat 入口（V2）：先驗證請求，再經 SyncHandler（pre_process -> handle -> post_process）
    委派給 _process_chat_request；異常由 _chat_error_to_json_response 轉為統一錯誤體。
    """
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    step = "router.chat_product_v2"
    try:
        # T2a.5：先校驗請求，非法則 422
        validate_chat_request(request_body)
        # T2a.6：經 SyncHandler 處理（含限流、權限、配額、委派）
        handler = SyncHandler()
        handler_request = ChatHandlerRequest(
            request_body=request_body,
            request_id=request_id,
            tenant_id=tenant_id,
            current_user=current_user,
        )
        response = await handler.run(handler_request)
        response_data = response.model_dump(mode="json")
        return APIResponse.success(data=response_data, message="Chat success")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Chat error at step={step}: request_id={request_id}, "
            f"error_type={type(exc).__name__}, error={str(exc)[:200]}",
            exc_info=True,
        )
        return _chat_error_to_json_response(request_id, exc)


# ==================== 階段三：流式、批處理、異步請求、歸檔、任務治理 ====================


@router.post("/stream", status_code=status.HTTP_200_OK)
async def chat_stream_v2(
    request_body: ChatRequest,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """T3.1–T3.2：流式 Chat，返回 SSE 流。"""
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    try:
        validate_chat_request(request_body)
        handler = StreamHandler()
        handler_request = ChatHandlerRequest(
            request_body=request_body,
            request_id=request_id,
            tenant_id=tenant_id,
            current_user=current_user,
        )
        await handler.pre_process(handler_request)
        stream = handler.handle(handler_request)
        return StreamingResponse(
            stream,
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except HTTPException:
        raise
    except Exception as exc:
        return _chat_error_to_json_response(request_id, exc)


@router.post("/batch", status_code=status.HTTP_200_OK)
async def chat_batch_v2(
    body: BatchChatRequest,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """T3.3–T3.4：批處理 Chat，返回 batch_id、results、summary。"""
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    try:
        for req in body.requests:
            validate_chat_request(req)
        batch_handler = BatchHandler()
        result = await batch_handler.process(
            requests=body.requests,
            mode=body.mode,
            max_concurrent=body.max_concurrent,
            tenant_id=tenant_id,
            current_user=current_user,
        )
        return APIResponse.success(
            data=result.model_dump(mode="json"),
            message="Batch completed",
        )
    except HTTPException:
        raise
    except Exception as exc:
        return _chat_error_to_json_response(request_id, exc)


@router.post("/requests", status_code=status.HTTP_200_OK)
async def create_async_chat_request(
    request_body: ChatRequest,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """T3.5：異步 Chat 請求，返回 request_id。"""
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    try:
        validate_chat_request(request_body)
        req_id = await create_async_request(
            priority="normal",
            task_id=request_body.task_id,
            request_body=request_body.model_dump(mode="json"),
            tenant_id=tenant_id,
        )
        start_async_chat_background(req_id, request_body, tenant_id, current_user)
        rec = await get_async_request(req_id)
        data = record_to_response(rec) if rec else {"request_id": req_id, "status": "pending"}
        return APIResponse.success(
            data=data,
            message="Async request created",
        )
    except HTTPException:
        raise
    except Exception as exc:
        return _chat_error_to_json_response(request_id, exc)


@router.get("/requests/{request_id}", status_code=status.HTTP_200_OK)
async def get_async_chat_status(
    request_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """T3.6：查詢異步請求狀態與結果。"""
    rec = await get_async_request(request_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Request not found")
    return APIResponse.success(
        data=record_to_response(rec),
        message="OK",
    )


@router.post("/requests/{request_id}/retry", status_code=status.HTTP_200_OK)
async def retry_async_chat_request(
    request_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """T3.7：重試異步請求，更新狀態並重新入隊。"""
    rec = await get_async_request(request_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Request not found")
    if not rec.request_body or not rec.tenant_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot retry: original request payload not stored",
        )
    await set_async_request_status(request_id, "pending", result=None, error=None)
    from services.api.models.chat import ChatRequest

    body = ChatRequest.model_validate(rec.request_body)
    start_async_chat_background(request_id, body, rec.tenant_id, current_user)
    return APIResponse.success(
        data={"request_id": request_id, "status": "pending"},
        message="Retry queued",
    )


class PriorityUpdateRequest(BaseModel):
    """優先級更新請求體。"""

    priority: str = "normal"


@router.put("/requests/{request_id}/priority", status_code=status.HTTP_200_OK)
async def update_async_request_priority(
    request_id: str,
    body: PriorityUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """T3.8：更新異步請求優先級。"""
    priority = body.priority
    ok = await set_async_request_priority(request_id, priority)
    if not ok:
        raise HTTPException(status_code=404, detail="Request not found")
    rec = await get_async_request(request_id)
    return APIResponse.success(
        data=record_to_response(rec) if rec else {"request_id": request_id, "priority": priority},
        message="Priority updated",
    )


class ArchiveSessionRequest(BaseModel):
    """會話歸檔請求體。"""

    consolidate_memory: bool = True
    delete_messages: bool = False


@router.post("/sessions/{session_id}/archive", status_code=status.HTTP_200_OK)
async def archive_session_endpoint(
    session_id: str,
    body: ArchiveSessionRequest,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """T3.9–T3.10：會話歸檔。"""
    result = await archive_session(
        session_id=session_id,
        consolidate_memory=body.consolidate_memory,
        delete_messages=body.delete_messages,
        user_id=current_user.user_id,
    )
    return APIResponse.success(
        data={
            "session_id": result.session_id,
            "archive_id": result.archive_id,
            "message_count": result.message_count,
            "memory_consolidated": result.memory_consolidated,
            "archived_at": result.archived_at,
        },
        message="Session archived",
    )


# T3.11：任務治理端點（佔位，符合規格請求/響應格式）
@router.get("/tasks/{task_id}", status_code=status.HTTP_200_OK)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """任務治理：獲取任務狀態（佔位）。"""
    return APIResponse.success(
        data={
            "task_id": task_id,
            "status": "unknown",
            "decision_point": None,
            "task_steps": [],
            "user_decision_required": False,
        },
        message="OK",
    )


class TaskDecisionRequest(BaseModel):
    """任務決策請求體。"""

    decision: str = "approve"
    adjustments: List[dict] = Field(default_factory=list)
    reason: Optional[str] = None


@router.post("/tasks/{task_id}/decision", status_code=status.HTTP_200_OK)
async def submit_task_decision(
    task_id: str,
    body: TaskDecisionRequest,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """任務治理：提交用戶決策（佔位）。"""
    return APIResponse.success(
        data={"task_id": task_id, "decision": body.decision, "received": True},
        message="Decision received",
    )


class TaskAbortRequest(BaseModel):
    """任務中止請求體。"""

    reason: Optional[str] = None
    cleanup_resources: bool = True


@router.post("/tasks/{task_id}/abort", status_code=status.HTTP_200_OK)
async def abort_task(
    task_id: str,
    body: TaskAbortRequest,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """任務治理：中止任務（佔位）。"""
    return APIResponse.success(
        data={"task_id": task_id, "aborted": True, "reason": body.reason},
        message="Abort received",
    )


# ==================== 觀測性路由 ====================


@router.get("/observability/stats", status_code=status.HTTP_200_OK)
async def get_chat_observability_stats_endpoint(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """G5：產品級 Chat 指標彙總（JSON）。"""
    return get_chat_observability_stats(current_user=current_user)


@router.get("/observability/traces/{request_id}", status_code=status.HTTP_200_OK)
async def get_chat_observability_trace_endpoint(
    request_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """G5：依 request_id 回放事件序列（MVP：in-memory）。"""
    return get_chat_observability_trace(request_id=request_id, current_user=current_user)


@router.get("/observability/recent", status_code=status.HTTP_200_OK)
async def get_chat_observability_recent_endpoint(
    limit: int = 50,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    event: Optional[str] = None,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """G5：列出最近 N 筆事件（MVP：in-memory）。"""
    return get_chat_observability_recent(
        limit=limit,
        current_user=current_user,
        session_id=session_id,
        task_id=task_id,
        event=event,
    )


# ==================== 會話管理路由 ====================


@router.get("/sessions/{session_id}/messages", status_code=status.HTTP_200_OK)
async def get_session_messages_endpoint(
    session_id: str,
    limit: Optional[int] = None,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """G3：Session 回放（最小可用）。"""
    return get_session_messages(
        session_id=session_id,
        current_user=current_user,
        limit=limit,
    )


# ==================== 用戶偏好路由 ====================


@router.get("/preferences/models", status_code=status.HTTP_200_OK)
async def get_favorite_models(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取用戶收藏的模型列表"""
    user_id = current_user.user_id
    try:
        from services.api.services.user_preference_service import get_user_preference_service

        service = get_user_preference_service()
        model_ids = service.get_favorite_models(user_id=user_id)
        return APIResponse.success(
            data={"model_ids": model_ids, "user_id": user_id},
            message="Favorite models retrieved",
        )
    except Exception as exc:  # noqa: BLE001
        import structlog

        logger = structlog.get_logger(__name__)
        logger.warning(
            f"get_favorite_models_failed: error={str(exc)}, user_id={user_id}",
            exc_info=True,
        )
        return APIResponse.success(
            data={"model_ids": [], "user_id": user_id},
            message="Favorite models retrieved (fallback to empty list)",
        )


@router.put("/preferences/models", status_code=status.HTTP_200_OK)
async def set_favorite_models(
    request: FavoriteModelsUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """設置用戶收藏的模型列表"""
    user_id = current_user.user_id
    try:
        from services.api.services.user_preference_service import get_user_preference_service

        service = get_user_preference_service()
        service.set_favorite_models(user_id=user_id, model_ids=request.model_ids)
        return APIResponse.success(
            data={"model_ids": request.model_ids, "user_id": user_id},
            message="Favorite models updated",
        )
    except Exception as exc:  # noqa: BLE001
        import structlog

        logger = structlog.get_logger(__name__)
        logger.error(
            f"set_favorite_models_failed: error={str(exc)}, user_id={user_id}",
            exc_info=True,
        )
        raise
