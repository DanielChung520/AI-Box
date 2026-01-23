# 代碼功能說明: MoE Metrics API 路由
# 創建日期: 2026-01-20
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-20

"""MoE Metrics API

提供 MoE 相關的監控指標 endpoint：
- GET /api/v1/moe/metrics - 返回 MoE metrics（Prometheus 格式）
- GET /api/v1/moe/metrics/summary - 返回 MoE metrics 摘要
"""

from typing import Any, Dict

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from llm.moe.moe_manager import LLMMoEManager

router = APIRouter(prefix="/moe/metrics", tags=["MoE Metrics"])


@router.get("")
async def get_moe_metrics() -> Response:
    """
    返回 MoE 指標（Prometheus 格式）

    Returns:
        Response: Prometheus 格式的指標數據
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@router.get("/summary")
async def get_moe_metrics_summary() -> Dict[str, Any]:
    """
    返回 MoE metrics 摘要（JSON 格式）

    Returns:
        Dict[str, Any]: MoE metrics 摘要
    """
    try:
        moe_manager = LLMMoEManager()

        routing_metrics = moe_manager.get_routing_metrics()

        scenes = moe_manager.get_available_scenes()

        summary = {
            "scenes": scenes,
            "scene_count": len(scenes),
            "routing_metrics": routing_metrics,
        }

        return summary

    except Exception as e:
        return {
            "scenes": [],
            "scene_count": 0,
            "routing_metrics": {},
            "error": str(e),
        }


@router.get("/scenes/{scene}")
async def get_scene_metrics(scene: str) -> Dict[str, Any]:
    """
    返回特定場景的 metrics

    Args:
        scene: 場景名稱

    Returns:
        Dict[str, Any]: 場景 metrics
    """
    try:
        moe_manager = LLMMoEManager()

        scene_config = moe_manager.get_scene_config(scene)
        if not scene_config:
            return {"error": f"Scene not found: {scene}"}

        routing_metrics = moe_manager.get_routing_metrics()

        scene_metrics = {
            "scene": scene,
            "config": {
                "priority": [
                    {
                        "model": m.model,
                        "context_size": m.context_size,
                        "max_tokens": m.max_tokens,
                        "temperature": m.temperature,
                        "timeout": m.timeout,
                    }
                    for m in scene_config.priority
                ]
            },
            "routing_metrics": routing_metrics.get("provider_metrics", {}),
        }

        return scene_metrics

    except Exception as e:
        return {"error": str(e)}
