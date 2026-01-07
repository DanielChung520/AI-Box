"""
代碼功能說明: 流式傳輸 API - 支持 WebSocket/SSE 流式傳輸
創建日期: 2025-12-20 12:30:07 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2026-01-06
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator, Optional

import structlog
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.api.services.editing_session_service import get_editing_session_service
from system.security.dependencies import get_current_tenant_id, get_current_user
from system.security.models import User

logger = structlog.get_logger(__name__)

# 向後兼容：如果 ConfigStoreService 不可用，使用舊的配置方式
try:
    from services.api.services.config_store_service import ConfigStoreService

    _streaming_config_service: Optional[ConfigStoreService] = None

    def get_streaming_config_service() -> ConfigStoreService:
        """獲取配置存儲服務實例（單例模式）"""
        global _streaming_config_service
        if _streaming_config_service is None:
            _streaming_config_service = ConfigStoreService()
        return _streaming_config_service

    STREAMING_CONFIG_STORE_AVAILABLE = True
except ImportError:
    STREAMING_CONFIG_STORE_AVAILABLE = False
    logger.warning("ConfigStoreService 不可用，流式輸出將使用默認 chunk_size=50")


def get_streaming_chunk_size() -> int:
    """
    獲取流式輸出分塊大小（從 ArangoDB system_configs 讀取）

    Returns:
        流式輸出分塊大小（字符數），默認 50
    """
    # 優先從 ArangoDB system_configs 讀取
    if STREAMING_CONFIG_STORE_AVAILABLE:
        try:
            config_service = get_streaming_config_service()
            config = config_service.get_config("streaming", tenant_id=None)
            if config and config.config_data:
                chunk_size = config.config_data.get("chunk_size", 50)
                return int(chunk_size)
        except Exception as e:
            logger.warning(
                "failed_to_load_streaming_config_from_arangodb",
                error=str(e),
                message="從 ArangoDB 讀取流式輸出配置失敗，使用默認值 50",
            )

    # 默認值
    return 50


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
            # 修改時間：2026-01-06 - 優化從 Agent 結果中提取 Search-and-Replace 格式的數據
            # Agent 結果格式：{"patch_kind": "search_replace", "patch_payload": {...}, "summary": "...", ...}
            patch_kind = agent_result.get("patch_kind", "")
            patch_payload = agent_result.get("patch_payload", {})

            # 提取 patches 數據
            patches_data = None
            if patch_kind == "search_replace" and isinstance(patch_payload, dict):
                # Search-and-Replace 格式：patch_payload 包含 "patches" 鍵
                patches_data = patch_payload.get("patches")
            elif isinstance(agent_result.get("patches"), list):
                # 兼容舊格式：直接從 result 中獲取 patches
                patches_data = agent_result.get("patches")
            elif isinstance(agent_result.get("result"), dict):
                # 兼容格式：從 result.patches 獲取
                patches_data = agent_result.get("result", {}).get("patches")

            if patches_data and isinstance(patches_data, list) and len(patches_data) > 0:
                # 驗證 patches 格式
                valid_patches = []
                for patch in patches_data:
                    if (
                        isinstance(patch, dict)
                        and "search_block" in patch
                        and "replace_block" in patch
                    ):
                        valid_patches.append(
                            {
                                "search_block": patch["search_block"],
                                "replace_block": patch["replace_block"],
                            }
                        )

                if valid_patches:
                    # 將 patches 轉換為 JSON 字符串並流式發送
                    patches_json = json.dumps({"patches": valid_patches})
                    # 性能優化：根據數據大小動態調整 chunk_size 和延遲
                    chunk_size = get_streaming_chunk_size()
                    # 對於小數據（< 10KB），減少延遲以提高響應速度
                    data_size_kb = len(patches_json.encode("utf-8")) / 1024
                    delay = 0.01 if data_size_kb < 10 else 0.05

                    for i in range(0, len(patches_json), chunk_size):
                        chunk = patches_json[i : i + chunk_size]
                        yield f"data: {json.dumps({'type': 'patch_chunk', 'data': {'chunk': chunk}})}\n\n"
                        # 性能優化：減少不必要的延遲
                        if i + chunk_size < len(patches_json):
                            await asyncio.sleep(delay)

                    # 發送結束消息
                    yield f"data: {json.dumps({'type': 'patch_end', 'data': {'request_id': request_id}})}\n\n"
                    logger.info(
                        "streaming_patches_completed",
                        session_id=session_id,
                        request_id=request_id,
                        patch_count=len(valid_patches),
                    )
                    return
                else:
                    logger.warning(
                        "no_valid_patches_found",
                        session_id=session_id,
                        request_id=request_id,
                        patches_data=patches_data,
                    )
            else:
                logger.warning(
                    "patches_data_not_found_or_invalid",
                    session_id=session_id,
                    request_id=request_id,
                    patch_kind=patch_kind,
                    has_patch_payload=bool(patch_payload),
                )

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
