# -*- coding: utf-8 -*-
"""
Data-Agent-JP Sync API 路由

端點：
- POST /api/v1/mm-master/sync - 手動觸發同步
- GET /api/v1/mm-master/sync/status - 取得同步狀態

建立日期: 2026-02-10
建立人: Daniel Chung
"""

import logging
import threading
from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()

_sync_lock = threading.Lock()
_sync_thread: Optional[threading.Thread] = None
_last_sync_result: Optional[Dict[str, Any]] = None
_sync_in_progress: bool = False


class SyncRequest(BaseModel):
    """同步請求"""

    recreate: bool = False
    sync_arangodb: bool = True
    sync_qdrant: bool = True


class SyncResponse(BaseModel):
    """同步響應"""

    status: str
    message: str
    task_id: Optional[str] = None


def run_sync_background(
    recreate: bool = False,
    sync_arangodb: bool = True,
    sync_qdrant: bool = True,
):
    """在背景執行同步"""
    global _sync_in_progress, _last_sync_result

    try:
        import sys

        sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

        from datalake_system.scripts.sync_mmMaster import MasterDataSync

        embedding_model = None

        sync = MasterDataSync(embedding_model=embedding_model)

        result = {"status": "pending"}

        if sync_arangodb and sync_qdrant:
            result = sync.sync_all(recreate=recreate)
        elif sync_arangodb:
            result["arangodb"] = sync.sync_arangodb(recreate=recreate)
        elif sync_qdrant:
            result["qdrant"] = sync.sync_qdrant(recreate=recreate)

        sync.log_sync_status()
        _last_sync_result = result

    except Exception as e:
        logger.error(f"Background sync failed: {e}")
        _last_sync_result = {"status": "error", "error": str(e)}
    finally:
        _sync_in_progress = False


@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(request: SyncRequest) -> SyncResponse:
    """
    手動觸發同步

    Args:
        request: 同步請求

    Returns:
        SyncResponse: 同步響應
    """
    global _sync_in_progress

    if _sync_in_progress:
        return SyncResponse(
            status="warning",
            message="Sync already in progress",
        )

    with _sync_lock:
        if _sync_in_progress:
            return SyncResponse(
                status="warning",
                message="Sync already in progress (concurrent check)",
            )

        _sync_in_progress = True

    thread = threading.Thread(
        target=run_sync_background,
        kwargs={
            "recreate": request.recreate,
            "sync_arangodb": request.sync_arangodb,
            "sync_qdrant": request.sync_qdrant,
        },
        daemon=True,
    )
    thread.start()

    return SyncResponse(
        status="started",
        message="Sync started in background",
        task_id=f"sync_{thread.ident}",
    )


@router.get("/sync/status")
async def get_sync_status() -> Dict[str, Any]:
    """
    取得同步狀態

    Returns:
        dict: 同步狀態
    """
    return {
        "in_progress": _sync_in_progress,
        "last_result": _last_sync_result,
    }


@router.get("/sync/last-result")
async def get_last_sync_result() -> Dict[str, Any]:
    """
    取得上次同步結果

    Returns:
        dict: 上次同步結果
    """
    if _last_sync_result is None:
        return {
            "status": "no_sync",
            "message": "No sync has been performed yet",
        }

    return _last_sync_result
