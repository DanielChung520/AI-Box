"""
代碼功能說明: 流式傳輸 API - 支持 WebSocket/SSE 流式傳輸
創建日期: 2025-12-20 12:30:07 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-20 12:30:07 (UTC+8)
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator, Optional

import structlog
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.api.services.editing_session_service import (
    get_editing_session_service,
)
from system.security.dependencies import get_current_tenant_id, get_current_user
from system.security.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/streaming", tags=["Streaming"])


# ============================================================================
# Request/Response Models
# ============================================================================


class StreamingRequest(BaseModel):
    """流式傳輸請求"""

    session_id: str = Field(..., description="Session ID")
    request_id: Optional[str] = Field(None, description="請求 ID（可選）")


# ============================================================================
# Stream Protocol
# ============================================================================

# 流式傳輸協議格式：
# - 每個消息以 "data: " 開頭（SSE 格式）
# - JSON 格式：{"type": "patch_start|patch_chunk|patch_end|error", "data": {...}}
# - 類型說明：
#   - patch_start: 開始新的 patch
#   - patch_chunk: patch 數據塊
#   - patch_end: patch 結束
#   - error: 錯誤信息


async def _generate_streaming_patches(
    *,
    session_id: str,
    request_id: str,
) -> AsyncGenerator[str, None]:
    """生成流式 patch 數據

    從 Agent 系統獲取流式數據並轉換為 SSE 格式。
    """
    try:
        # 發送開始消息
        yield f"data: {json.dumps({'type': 'patch_start', 'data': {'request_id': request_id}})}\n\n"

        # 嘗試從 Agent 系統獲取流式數據
        # 首先檢查是否有對應的編輯請求
        agent_result = None
        try:
            from services.api.services.editing_session_service import get_editing_session_service

            session_service = get_editing_session_service()
            session = session_service.get_session(session_id=session_id)

            if session:
                # 從 Session metadata 中獲取最後的執行結果
                last_request_id = session.metadata.get("last_request_id")
                if last_request_id == request_id:
                    agent_result = session.metadata.get("last_result")
                    if agent_result:
                        logger.info(
                            "using_agent_result_for_streaming",
                            session_id=session_id,
                            request_id=request_id,
                        )
        except Exception as exc:
            logger.warning(
                "failed_to_get_agent_streaming_data",
                session_id=session_id,
                request_id=request_id,
                error=str(exc),
            )

        # 如果從 Agent 獲取了結果，使用它；否則使用模擬數據
        if agent_result and isinstance(agent_result, dict):
            # 嘗試從 Agent 結果中提取 Search-and-Replace 格式的數據
            patches_data = agent_result.get("patches") or agent_result.get("result", {}).get("patches")
            if patches_data:
                # 將 patches 轉換為 JSON 字符串並流式發送
                patches_json = json.dumps({"patches": patches_data})
                # 分塊發送
                chunk_size = 50
                for i in range(0, len(patches_json), chunk_size):
                    chunk = patches_json[i : i + chunk_size]
                    yield f"data: {json.dumps({'type': 'patch_chunk', 'data': {'chunk': chunk}})}\n\n"
                    await asyncio.sleep(0.05)  # 較短的延遲

                # 發送結束消息
                yield f"data: {json.dumps({'type': 'patch_end', 'data': {'request_id': request_id}})}\n\n"
                return

        # 暫時使用模擬數據（待 Agent 系統支持流式響應後替換）
        # 實際應該：
        # 1. 從 Session metadata 中獲取 request_id
        # 2. 查詢 Agent 執行結果
        # 3. 如果 Agent 支持流式響應，監聽流式數據
        # 4. 解析 Search-and-Replace 格式的數據
        # 5. 逐塊發送給前端

        # 模擬數據塊（模擬 Agent 生成的 Search-and-Replace 格式）
        chunks = [
            '{"patches": [{"search_block": "',
            "Hello",
            " world",
            '", "replace_block": "',
            "Hello",
            " universe",
            '"}]}',
        ]

        for chunk in chunks:
            yield f"data: {json.dumps({'type': 'patch_chunk', 'data': {'chunk': chunk}})}\n\n"
            # 模擬延遲（實際應該根據 Agent 響應速度調整）
            await asyncio.sleep(0.1)

        # 發送結束消息
        yield f"data: {json.dumps({'type': 'patch_end', 'data': {'request_id': request_id}})}\n\n"

    except Exception as exc:
        logger.error("streaming_error", session_id=session_id, error=str(exc))
        yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(exc)}})}\n\n"


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/editing/{session_id}/stream")
async def stream_editing_patches(
    session_id: str,
    request_id: Optional[str] = None,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """SSE 流式傳輸端點

    用於接收編輯 patch 的流式數據（Server-Sent Events 格式）。
    """
    try:
        session_service = get_editing_session_service()

        # 驗證 Session
        session = session_service.get_session(session_id=session_id)
        if session is None:
            return StreamingResponse(
                iter(
                    [
                        f"data: {json.dumps({'type': 'error', 'data': {'error': 'Session not found'}})}\n\n"
                    ]
                ),
                media_type="text/event-stream",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 驗證用戶權限
        if session.user_id != current_user.user_id or session.tenant_id != tenant_id:
            return StreamingResponse(
                iter(
                    [
                        f"data: {json.dumps({'type': 'error', 'data': {'error': 'Session access denied'}})}\n\n"
                    ]
                ),
                media_type="text/event-stream",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 生成 request_id（如果未提供）
        if not request_id:
            import uuid

            request_id = str(uuid.uuid4())

        # 返回 SSE 流
        return StreamingResponse(
            _generate_streaming_patches(session_id=session_id, request_id=request_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁用 Nginx 緩衝
            },
        )
    except Exception as exc:
        logger.error("streaming_endpoint_error", session_id=session_id, error=str(exc))
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'data': {'error': str(exc)}})}\n\n"]),
            media_type="text/event-stream",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
