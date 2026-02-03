"""
代碼功能說明: AI 狀態 SSE API - 推送 AI 執行狀態給前端
創建日期: 2026-02-02
創建人: OpenCode AI
最後修改日期: 2026-02-02
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from system.security.dependencies import get_current_tenant_id, get_current_user
from system.security.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/agent-status", tags=["Agent Status"])

_agent_status_subscribers: Dict[str, asyncio.Queue] = {}


class AgentStatusEvent(BaseModel):
    """AI 狀態事件"""

    request_id: str = Field(..., description="請求 ID")
    step: str = Field(..., description="當前步驟名稱")
    status: str = Field(..., description="狀態: processing/completed/error")
    message: str = Field(..., description="狀態描述")
    progress: float = Field(default=0.0, ge=0, le=1, description="進度 0-1")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


async def publish_status(request_id: str, event: AgentStatusEvent) -> None:
    """發布狀態事件給訂閱者"""
    if request_id in _agent_status_subscribers:
        try:
            await _agent_status_subscribers[request_id].put(event.model_dump_json())
        except Exception as e:
            logger.error("failed_to_publish_status", request_id=request_id, error=str(e))


async def generate_status_stream(
    request_id: str,
) -> AsyncGenerator[AgentStatusEvent, None]:
    """生成狀態事件流"""
    queue: asyncio.Queue = asyncio.Queue()

    if request_id not in _agent_status_subscribers:
        _agent_status_subscribers[request_id] = queue
    else:
        queue = _agent_status_subscribers[request_id]

    try:
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=30.0)
                event = AgentStatusEvent.model_validate_json(data)
                yield event
                if event.status == "completed" or event.status == "error":
                    break
            except asyncio.TimeoutError:
                yield AgentStatusEvent(
                    request_id=request_id,
                    step="heartbeat",
                    status="processing",
                    message="AI 正在思考...",
                    progress=0,
                )
    finally:
        if request_id in _agent_status_subscribers:
            del _agent_status_subscribers[request_id]


@router.get("/stream/{request_id}")
async def stream_agent_status(
    request_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """SSE 狀態流端點

    用於接收 AI 執行狀態的 Server-Sent Events 串流。
    """
    try:
        return EventSourceResponse(
            generate_status_stream(request_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.error("status_stream_error", request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_status_tracking(
    request_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """開始追蹤狀態"""
    _agent_status_subscribers[request_id] = asyncio.Queue()
    return {"status": "started", "request_id": request_id}


@router.post("/event")
async def send_status_event(
    event: AgentStatusEvent,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """發送狀態事件"""
    await publish_status(event.request_id, event)
    return {"status": "published", "request_id": event.request_id}


@router.post("/end")
async def end_status_tracking(
    request_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """結束追蹤狀態"""
    if request_id in _agent_status_subscribers:
        del _agent_status_subscribers[request_id]
    return {"status": "ended", "request_id": request_id}
