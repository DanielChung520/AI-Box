# 代碼功能說明: Prometheus Metrics 端點（WBS-2.4: 監控與日誌）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""Prometheus Metrics 端點

提供 Prometheus 格式的指標數據供監控系統抓取。
"""

from __future__ import annotations

from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter()


@router.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """
    獲取 Prometheus 格式的指標數據

    Returns:
        Prometheus 格式的指標數據
    """
    return generate_latest(), {"Content-Type": CONTENT_TYPE_LATEST}
