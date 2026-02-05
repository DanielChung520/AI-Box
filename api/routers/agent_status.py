"""
代碼功能說明: AI 狀態 SSE API - 推送 AI 執行狀態給前端
創建日期: 2026-02-02
創建人: OpenCode AI
最後修改日期: 2026-02-04
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from typing import AsyncGenerator, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/agent-status", tags=["Agent Status"])

# 使用 List 存儲事件歷史，支持多個 SSE 連接
_agent_status_events: Dict[str, List[dict]] = {}
_agent_status_queues: Dict[str, asyncio.Queue] = {}


class AgentStatusEvent(BaseModel):
    """AI 狀態事件"""

    request_id: str = Field(..., description="請求 ID")
    step: str = Field(..., description="當前步驟名稱")
    status: str = Field(..., description="狀態: processing/completed/error")
    message: str = Field(..., description="狀態描述")
    progress: float = Field(default=0.0, ge=0, le=1, description="進度 0-1")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


async def _start_tracking_internal(request_id: str) -> None:
    """開始狀態追蹤"""
    if request_id not in _agent_status_events:
        _agent_status_events[request_id] = []
    if request_id not in _agent_status_queues:
        _agent_status_queues[request_id] = asyncio.Queue()


async def _publish_status_internal(request_id: str, event: AgentStatusEvent) -> None:
    """發布狀態事件"""
    event_dict = event.model_dump()

    # 存儲到事件歷史
    if request_id in _agent_status_events:
        _agent_status_events[request_id].append(event_dict)

    # 發送到隊列（通知所有訂閱者）
    if request_id in _agent_status_queues:
        try:
            await _agent_status_queues[request_id].put(event_dict)
        except Exception as e:
            print(f"[SSE] publish error: {e}", flush=True, file=sys.stderr)


async def generate_status_stream(
    request_id: str,
) -> AsyncGenerator[str, None]:
    """生成 SSE 格式的狀態事件流"""
    print(f"[SSE] stream started: {request_id}", flush=True, file=sys.stderr)

    # 確保追蹤已啟動
    await _start_tracking_internal(request_id)

    # 獲取事件歷史（之前的連接可能已經發布了事件）
    events_history = _agent_status_events.get(request_id, [])

    # 獲取或創建隊列
    if request_id not in _agent_status_queues:
        _agent_status_queues[request_id] = asyncio.Queue()
    queue = _agent_status_queues[request_id]

    sent_event_ids: set = set()  # 追蹤已發送的事件

    try:
        # 首先發送歷史事件
        for i, event in enumerate(events_history):
            event_id = f"{event['request_id']}-{i}"
            if event_id not in sent_event_ids:
                print(f"[SSE] yield history: {event['step']}", flush=True, file=sys.stderr)
                yield json.dumps(event)
                sent_event_ids.add(event_id)

        # 然後等待新事件
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=5.0)
                event = AgentStatusEvent.model_validate_json(data)
                event_id = f"{event.request_id}-{len(events_history)}"

                # 防止重複發送
                if event_id not in sent_event_ids:
                    print(f"[SSE] yield: {event.step}", flush=True, file=sys.stderr)
                    yield json.dumps(event.model_dump())
                    sent_event_ids.add(event_id)
                    events_history.append(data)

                if event.status == "completed" or event.status == "error":
                    break
            except asyncio.TimeoutError:
                heartbeat = AgentStatusEvent(
                    request_id=request_id,
                    step="heartbeat",
                    status="processing",
                    message="AI 正在處理...",
                    progress=0,
                )
                yield json.dumps(heartbeat.model_dump())
    finally:
        print(f"[SSE] stream ended: {request_id}", flush=True, file=sys.stderr)
        # 清理資源
        if request_id in _agent_status_queues:
            del _agent_status_queues[request_id]
        if request_id in _agent_status_events:
            del _agent_status_events[request_id]


@router.get("/stream/{request_id}")
async def stream_agent_status(
    request_id: str,
) -> EventSourceResponse:
    """SSE 狀態流端點"""
    print(f"[SSE] stream endpoint: {request_id}", flush=True, file=sys.stderr)
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
        print(f"[SSE] error: {e}", flush=True, file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))


class StartStatusRequest(BaseModel):
    request_id: str


@router.post("/start")
async def start_status_tracking(
    request: StartStatusRequest,
) -> dict:
    """開始追蹤狀態"""
    await _start_tracking_internal(request.request_id)
    return {"status": "started", "request_id": request.request_id}


@router.post("/event")
async def send_status_event(
    event: AgentStatusEvent,
) -> dict:
    """發送狀態事件"""
    await _publish_status_internal(event.request_id, event)
    return {"status": "published", "request_id": event.request_id}


@router.post("/end")
async def end_status_tracking(
    request_id: str,
) -> dict:
    """結束追蹤"""
    if request_id in _agent_status_queues:
        del _agent_status_queues[request_id]
    if request_id in _agent_status_events:
        del _agent_status_events[request_id]
    return {"status": "ended", "request_id": request_id}
