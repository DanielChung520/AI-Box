# 代碼功能說明: MoE API 路由
# 創建日期: 2026-01-20
# 創建人: Daniel Chung

"""MoE (Mixture of Experts) API 路由 - 模型選擇和配置管理"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from llm.moe.moe_manager import LLMMoEManager
from llm.moe.scene_routing import get_moe_config_loader
from system.security.dependencies import get_current_user
from system.security.models import User

router = APIRouter(prefix="/moe", tags=["MoE"])


def get_moe_manager() -> LLMMoEManager:
    """獲取 MoE 管理器實例"""
    return LLMMoEManager()


MoEDep = Annotated[LLMMoEManager, Depends(get_moe_manager)]
UserDep = Annotated[User | None, Depends(get_current_user)]


def _make_response(data: Any, message: str = "Success") -> JSONResponse:
    """創建成功的 API 響應"""
    return JSONResponse(
        content={
            "success": True,
            "message": message,
            "data": data,
        },
        status_code=status.HTTP_200_OK,
    )


@router.get("/scenes")
async def list_scenes(
    moe: MoEDep,
) -> JSONResponse:
    """
    獲取所有可用的 MoE 場景

    Returns:
        場景列表，每個場景包含名稱和是否可編輯
    """
    scenes = moe.get_available_scenes()
    loader = get_moe_config_loader()

    result: List[Dict[str, Any]] = []
    for scene in scenes:
        config = loader.get_scene_config(scene)
        result.append(
            {
                "scene": scene,
                "frontend_editable": config.frontend_editable if config else False,
            }
        )

    return _make_response(result)


@router.get("/scenes/{scene}/config")
async def get_scene_config(
    scene: str,
    moe: MoEDep,
) -> JSONResponse:
    """
    獲取特定場景的配置

    Args:
        scene: 場景名稱（如 chat, embedding, knowledge_graph_extraction）

    Returns:
        場景配置，包含優先級列表和用戶偏好設置
    """
    config = moe.get_scene_config(scene)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene '{scene}' not found",
        )

    priority_list = [
        {
            "model": p.model,
            "context_size": p.context_size,
            "max_tokens": p.max_tokens,
            "temperature": p.temperature,
            "timeout": p.timeout,
            "retries": p.retries,
            "rpm": p.rpm,
            "concurrency": p.concurrency,
            "dimension": p.dimension,
        }
        for p in config.priority
    ]

    return _make_response(
        {
            "scene": config.scene,
            "frontend_editable": config.frontend_editable,
            "user_default": config.user_default,
            "priority": priority_list,
        }
    )


@router.post("/select")
async def select_model(
    scene: str = Query(..., description="場景名稱"),
    user_id: Optional[str] = Query(None, description="用戶 ID"),
    current_user: UserDep = None,
    moe: MoEDep = None,
) -> JSONResponse:
    """
    根據場景選擇最佳模型

    選擇邏輯：
    1. 環境變數（最高優先級）
    2. 用戶偏好（如果已設置且場景允許）
    3. 配置的優先級列表（第一個可用模型）

    Args:
        scene: 場景名稱
        user_id: 用戶 ID（可選，用於用戶偏好）

    Returns:
        選擇的模型配置
    """
    if moe is None:
        moe = get_moe_manager()

    effective_user_id = user_id
    if effective_user_id is None and current_user:
        effective_user_id = current_user.user_id

    result = moe.select_model(scene, user_id=effective_user_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No model configuration found for scene '{scene}'",
        )

    return _make_response(result.to_dict())


@router.get("/select")
async def select_model_get(
    scene: str = Query(..., description="場景名稱"),
    user_id: Optional[str] = Query(None, description="用戶 ID"),
    current_user: UserDep = None,
    moe: MoEDep = None,
) -> JSONResponse:
    """
    根據場景選擇最佳模型（GET 方法）

    與 POST /select 功能相同，但使用 GET 方法
    """
    if moe is None:
        moe = get_moe_manager()

    effective_user_id = user_id
    if effective_user_id is None and current_user:
        effective_user_id = current_user.user_id

    result = moe.select_model(scene, user_id=effective_user_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No model configuration found for scene '{scene}'",
        )

    return _make_response(result.to_dict())


@router.get("/features")
async def get_features(
    moe: MoEDep = None,
) -> JSONResponse:
    """
    獲取 MoE 功能開關狀態

    Returns:
        功能開關配置
    """
    loader = get_moe_config_loader()

    return _make_response(
        {
            "user_preference_enabled": loader.is_user_preference_enabled(),
            "adaptive_learning_enabled": loader.is_feature_enabled("adaptive_learning_enabled"),
            "cost_tracking_enabled": loader.is_feature_enabled("cost_tracking_enabled"),
            "auto_fallback_enabled": loader.is_auto_fallback_enabled(),
        }
    )


# ===================== 用戶偏好 API =====================

from services.api.services.moe_user_preference_service import get_moe_user_preference_service


@router.get("/user-preferences")
async def get_user_preferences(
    user_id: Optional[str] = Query(None, description="用戶 ID"),
    current_user: UserDep = None,
) -> JSONResponse:
    """
    獲取用戶所有場景的模型偏好

    Args:
        user_id: 用戶 ID（可選，默認使用當前登錄用戶）

    Returns:
        用戶偏好列表
    """
    effective_user_id = user_id
    if effective_user_id is None and current_user:
        effective_user_id = current_user.user_id

    if not effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID is required",
        )

    service = get_moe_user_preference_service()
    preferences = service.get_all_preferences(effective_user_id)

    return _make_response(
        {
            "user_id": effective_user_id,
            "preferences": preferences,
        }
    )


@router.get("/user-preferences/{scene}")
async def get_user_preference(
    scene: str,
    user_id: Optional[str] = Query(None, description="用戶 ID"),
    current_user: UserDep = None,
) -> JSONResponse:
    """
    獲取用戶在特定場景的模型偏好

    Args:
        scene: 場景名稱
        user_id: 用戶 ID（可選，默認使用當前登錄用戶）

    Returns:
        用戶偏好
    """
    effective_user_id = user_id
    if effective_user_id is None and current_user:
        effective_user_id = current_user.user_id

    if not effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID is required",
        )

    service = get_moe_user_preference_service()
    preference = service.get_preference(effective_user_id, scene)

    if preference is None:
        return _make_response(
            {
                "user_id": effective_user_id,
                "scene": scene,
                "model": None,
                "has_preference": False,
            }
        )

    return _make_response(
        {
            **preference,
            "has_preference": True,
        }
    )


@router.put("/user-preferences/{scene}")
async def set_user_preference(
    scene: str,
    model: str = Query(..., description="偏好的模型名稱"),
    user_id: Optional[str] = Query(None, description="用戶 ID"),
    current_user: UserDep = None,
) -> JSONResponse:
    """
    設置用戶在特定場景的模型偏好

    Args:
        scene: 場景名稱
        model: 偏好的模型名稱
        user_id: 用戶 ID（可選，默認使用當前登錄用戶）

    Returns:
        設置的偏好
    """
    effective_user_id = user_id
    if effective_user_id is None and current_user:
        effective_user_id = current_user.user_id

    if not effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID is required",
        )

    service = get_moe_user_preference_service()
    preference = service.set_preference(effective_user_id, scene, model)

    return _make_response(
        {
            "message": "Preference set successfully",
            "preference": preference,
        }
    )


@router.delete("/user-preferences/{scene}")
async def delete_user_preference(
    scene: str,
    user_id: Optional[str] = Query(None, description="用戶 ID"),
    current_user: UserDep = None,
) -> JSONResponse:
    """
    刪除用戶在特定場景的模型偏好

    Args:
        scene: 場景名稱
        user_id: 用戶 ID（可選，默認使用當前登錄用戶）

    Returns:
        刪除結果
    """
    effective_user_id = user_id
    if effective_user_id is None and current_user:
        effective_user_id = current_user.user_id

    if not effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID is required",
        )

    service = get_moe_user_preference_service()
    success = service.delete_preference(effective_user_id, scene)

    if success:
        return _make_response(
            {
                "message": f"Preference for scene '{scene}' deleted successfully",
            }
        )
    else:
        return _make_response(
            {
                "message": f"No preference found for scene '{scene}'",
            }
        )
