# 代碼功能說明: LLM 模型管理 API 路由
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-25 20:57 UTC+8

"""LLM 模型管理 API - 提供模型列表、創建、更新、刪除等操作"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.core.response import APIResponse
from services.api.models.llm_model import (
    LLMModelCreate,
    LLMModelQuery,
    LLMModelUpdate,
    LLMProvider,
    ModelStatus,
)
from services.api.services.llm_model_service import get_llm_model_service
from system.security.dependencies import get_current_tenant_id, get_current_user
from system.security.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["LLM Models"])


@router.get("", status_code=status.HTTP_200_OK)
async def get_models(
    provider: Optional[str] = None,
    status_filter: Optional[str] = None,
    capability: Optional[str] = None,
    search: Optional[str] = None,
    include_discovered: bool = True,
    include_favorite_status: bool = True,
    include_inactive: bool = False,  # 是否包含未激活的模型（用於管理界面）
    limit: int = 1000,  # 增加默認限制，確保返回所有模型
    offset: int = 0,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取模型列表（包含數據庫模型和動態發現的 Ollama 模型）

    Args:
        provider: 提供商篩選
        status_filter: 狀態篩選
        capability: 能力篩選
        search: 搜索關鍵詞
        include_discovered: 是否包含動態發現的 Ollama 模型
        include_favorite_status: 是否包含用戶收藏狀態
        limit: 返回數量限制
        offset: 偏移量
        current_user: 當前用戶

    Returns:
        模型列表（包含收藏狀態）
    """
    try:
        from services.api.models.llm_model import ModelCapability

        query_provider = LLMProvider(provider) if provider else None
        query_status = ModelStatus(status_filter) if status_filter else None
        query_capability = ModelCapability(capability) if capability else None

        query = LLMModelQuery(
            provider=query_provider,
            status=query_status,
            capability=query_capability,
            search=search,
            limit=limit,
            offset=offset,
        )

        service = get_llm_model_service()

        if include_discovered:
            # 使用新的方法，包含動態發現
            models = await service.get_all_with_discovery(
                query=query,
                user_id=current_user.user_id,
                tenant_id=tenant_id,
                include_favorite_status=include_favorite_status,
                include_discovered=True,
            )
        else:
            # 只從數據庫獲取
            models = service.get_all(query)

            # 如果需要，添加收藏狀態
            if include_favorite_status:
                from services.api.services.user_preference_service import (
                    get_user_preference_service,
                )

                pref_service = get_user_preference_service()
                favorite_ids = set(pref_service.get_favorite_models(user_id=current_user.user_id))

                # 標記收藏狀態
                for i, model in enumerate(models):
                    is_favorite = model.model_id in favorite_ids
                    if is_favorite:
                        try:
                            models[i] = model.model_copy(update={"is_favorite": True})
                        except (AttributeError, TypeError):
                            # Fallback: 直接設置屬性
                            model.is_favorite = True
                            models[i] = model

        # 根據 include_inactive 參數決定是否過濾未激活的模型
        # 注意：is_active 字段在 get_all_with_discovery 中已經設置
        if include_inactive:
            # 管理界面：返回所有模型（包括未激活的）
            filtered_models = models
        else:
            # 用戶界面：只返回激活的模型
            filtered_models = [
                model for model in models if getattr(model, "is_active", True) is True
            ]

        return APIResponse.success(
            data={
                "models": [
                    model.model_dump(mode="json", exclude_none=True) for model in filtered_models
                ],
                "total": len(filtered_models),
            },
            message="Models retrieved successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


# ===================== 場景相關 API（須在 /{model_id} 之前，避免 scenes 被當成 model_id） =====================


@router.get("/scenes", status_code=status.HTTP_200_OK)
async def get_scenes() -> JSONResponse:
    """
    獲取所有可用的 MoE 場景列表

    Returns:
        場景列表，每個場景包含名稱和是否可編輯
    """
    try:
        from llm.moe.scene_routing import get_moe_config_loader

        loader = get_moe_config_loader()
        scenes = loader.get_all_scenes()

        result = []
        for scene in scenes:
            config = loader.get_scene_config(scene)
            result.append(
                {
                    "scene": scene,
                    "frontend_editable": config.frontend_editable if config else False,
                    "user_default": config.user_default if config else None,
                }
            )

        return APIResponse.success(
            data={"scenes": result, "total": len(result)},
            message="Scenes retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get("/scene/{scene_name}", status_code=status.HTTP_200_OK)
async def get_models_by_scene(
    scene_name: str,
    include_favorite_status: bool = True,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    根據場景獲取模型列表（按優先級排序）

    Args:
        scene_name: 場景名稱（如 chat, semantic_understanding, task_analysis 等）
        include_favorite_status: 是否包含用戶收藏狀態
        tenant_id: 租戶 ID
        current_user: 當前用戶

    Returns:
        場景的模型列表（按優先級排序）
    """
    try:
        from llm.moe.scene_routing import get_moe_config_loader
        from services.api.services.llm_model_service import get_llm_model_service
        from services.api.services.user_preference_service import get_user_preference_service
        from services.api.services.simplified_model_service import get_simplified_model_service

        # 修改時間：2026-01-24 - 支持前端模型簡化策略
        if scene_name == "chat":
            simplified_service = get_simplified_model_service()
            if simplified_service.is_enabled():
                simplified_models = simplified_service.get_simplified_models()
                models_result = simplified_service.convert_to_llm_model_format(simplified_models)

                # 設置 frontend_editable 為 False，避免用戶誤操作
                return APIResponse.success(
                    data={
                        "scene": scene_name,
                        "frontend_editable": False,
                        "user_default": "auto",
                        "models": models_result,
                        "total": len(models_result),
                        "is_simplified": True,
                    },
                    message=f"Simplified models for scene '{scene_name}' retrieved successfully",
                )

        loader = get_moe_config_loader()
        scene_config = loader.get_scene_config(scene_name)

        if not scene_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scene '{scene_name}' not found",
            )

        # 獲取場景的模型優先級列表
        priority_list = scene_config.priority

        # 獲取模型服務
        model_service = get_llm_model_service()

        # 構建模型列表（按優先級排序）
        models_result = []
        model_ids_seen = set()

        # 先添加優先級列表中的模型
        for idx, model_config in enumerate(priority_list):
            model_id = model_config.model
            if model_id in model_ids_seen:
                continue

            model_ids_seen.add(model_id)

            # 嘗試從數據庫獲取模型信息
            db_model = model_service.get_by_id(model_id)
            if db_model:
                model_dict = db_model.model_dump(mode="json", exclude_none=True)
            else:
                # 如果數據庫中沒有，創建一個基本模型對象
                model_dict = {
                    "model_id": model_id,
                    "name": model_id,
                    "provider": "ollama",  # 默認假設是 Ollama 模型
                    "status": "active",
                    "capabilities": ["chat", "text_generation"],
                }

            # 添加場景特定的配置信息
            model_dict["order"] = idx + 1  # 優先級順序
            model_dict["scene_config"] = {
                "context_size": model_config.context_size,
                "max_tokens": model_config.max_tokens,
                "temperature": model_config.temperature,
                "timeout": model_config.timeout,
                "retries": model_config.retries,
                "rpm": model_config.rpm,
                "concurrency": model_config.concurrency,
                "dimension": model_config.dimension,
                "cost_per_1k_input": model_config.cost_per_1k_input,
                "cost_per_1k_output": model_config.cost_per_1k_output,
            }

            models_result.append(model_dict)

        # 如果需要，添加收藏狀態
        if include_favorite_status:
            pref_service = get_user_preference_service()
            favorite_ids = set(pref_service.get_favorite_models(user_id=current_user.user_id))

            for model_dict in models_result:
                m_id = model_dict.get("model_id")
                if m_id and m_id in favorite_ids:
                    model_dict["is_favorite"] = True

        return APIResponse.success(
            data={
                "scene": scene_name,
                "frontend_editable": scene_config.frontend_editable,
                "user_default": scene_config.user_default,
                "models": models_result,
                "total": len(models_result),
            },
            message=f"Models for scene '{scene_name}' retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


# ===================== 單模型 CRUD =====================


@router.get("/{model_id}", status_code=status.HTTP_200_OK)
async def get_model(model_id: str) -> JSONResponse:
    """
    獲取單個模型

    Args:
        model_id: 模型 ID

    Returns:
        模型對象
    """
    try:
        service = get_llm_model_service()
        model = service.get_by_id(model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Model '{model_id}' not found"
            )

        return APIResponse.success(
            data={"model": model.model_dump(mode="json", exclude_none=True)},
            message="Model retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_model(
    model: LLMModelCreate,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    創建模型（需要管理員權限）

    Args:
        model: 模型創建請求
        current_user: 當前用戶

    Returns:
        創建的模型對象
    """
    # TODO: 添加管理員權限檢查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    try:
        service = get_llm_model_service()
        created_model = service.create(model)

        return APIResponse.success(
            data={"model": created_model.model_dump(mode="json", exclude_none=True)},
            message="Model created successfully",
            status_code=status.HTTP_201_CREATED,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.put("/{model_id}", status_code=status.HTTP_200_OK)
async def update_model(
    model_id: str,
    update: LLMModelUpdate,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    更新模型（需要管理員權限）

    Args:
        model_id: 模型 ID
        update: 更新請求
        current_user: 當前用戶

    Returns:
        更新後的模型對象
    """
    # TODO: 添加管理員權限檢查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    try:
        service = get_llm_model_service()
        updated_model = service.update(model_id, update)
        if not updated_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Model '{model_id}' not found"
            )

        return APIResponse.success(
            data={"model": updated_model.model_dump(mode="json", exclude_none=True)},
            message="Model updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.delete("/{model_id}", status_code=status.HTTP_200_OK)
async def delete_model(
    model_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    刪除模型（需要管理員權限）

    Args:
        model_id: 模型 ID
        current_user: 當前用戶

    Returns:
        刪除結果
    """
    # TODO: 添加管理員權限檢查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    try:
        service = get_llm_model_service()
        success = service.delete(model_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Model '{model_id}' not found"
            )

        return APIResponse.success(data={"deleted": True}, message="Model deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


# Provider API Key 管理端點
class ProviderAPIKeyRequest(BaseModel):
    """Provider API Key 設置請求"""

    api_key: str = Field(..., description="API key（明文，將被加密存儲）")


@router.post("/providers/{provider}/api-key", status_code=status.HTTP_200_OK)
async def set_provider_api_key(
    provider: str,
    request: ProviderAPIKeyRequest,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    設置 Provider API key（需要管理員權限）

    Args:
        provider: Provider 名稱
        request: API key 請求體
        current_user: 當前用戶

    Returns:
        設置結果
    """
    # TODO: 添加管理員權限檢查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    try:
        from services.api.services.llm_provider_config_service import (
            get_llm_provider_config_service,
        )

        provider_enum = LLMProvider(provider)
        config_service = get_llm_provider_config_service()
        config_service.set_api_key(provider_enum, request.api_key, user_id=current_user.user_id)

        return APIResponse.success(
            data={"provider": provider, "has_api_key": True},
            message="Provider API key set successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


class ProviderConfigUpdateRequest(BaseModel):
    """Provider 完整配置更新請求"""

    api_key: Optional[str] = Field(None, description="API key（明文，將被加密存儲）")
    base_url: Optional[str] = Field(None, description="API 基礎 URL")
    api_version: Optional[str] = Field(None, description="API 版本")
    timeout: Optional[float] = Field(None, description="請求超時時間（秒）")
    max_retries: Optional[int] = Field(None, description="最大重試次數")
    default_model: Optional[Dict[str, Any]] = Field(None, description="默認模型配置")
    metadata: Optional[Dict[str, Any]] = Field(None, description="額外元數據")


@router.put("/providers/{provider}/config", status_code=status.HTTP_200_OK)
async def update_provider_config(
    provider: str,
    request: ProviderConfigUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    更新 Provider 完整配置（需要管理員權限）

    Args:
        provider: Provider 名稱
        request: 配置更新請求
        current_user: 當前用戶

    Returns:
        更新後的配置
    """
    # TODO: 添加管理員權限檢查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    try:
        from services.api.models.llm_provider_config import (
            LLMProviderModelConfig,
            LLMProviderConfigUpdate,
        )
        from services.api.services.llm_provider_config_service import (
            get_llm_provider_config_service,
        )

        provider_enum = LLMProvider(provider)
        config_service = get_llm_provider_config_service()

        # 構建更新對象
        update = LLMProviderConfigUpdate(
            api_key=request.api_key,
            base_url=request.base_url,
            api_version=request.api_version,
            timeout=request.timeout,
            max_retries=request.max_retries,
            default_model=(
                LLMProviderModelConfig(**request.default_model) if request.default_model else None
            ),
            metadata=request.metadata,
        )

        updated_config = config_service.update(provider_enum, update, user_id=current_user.user_id)
        if not updated_config:
            # 如果配置不存在，創建新配置
            from services.api.models.llm_provider_config import (
                LLMProviderConfigCreate,
                LLMProviderModelConfig,
            )

            create = LLMProviderConfigCreate(
                provider=provider_enum,
                api_key=request.api_key,
                base_url=request.base_url,
                api_version=request.api_version,
                timeout=request.timeout,
                max_retries=request.max_retries,
                default_model=(
                    LLMProviderModelConfig(**request.default_model)
                    if request.default_model
                    else None
                ),
                metadata=request.metadata or {},
            )
            updated_config = config_service.create(create, user_id=current_user.user_id)

        return APIResponse.success(
            data={
                "provider": provider,
                "base_url": updated_config.base_url,
                "has_api_key": updated_config.has_api_key,
                "default_model": (
                    updated_config.default_model.model_dump(mode="json")
                    if updated_config.default_model
                    else None
                ),
            },
            message="Provider config updated successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get("/providers/status", status_code=status.HTTP_200_OK)
async def get_all_providers_status(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    批量獲取所有 Provider 的 API key 狀態（需要管理員權限）

    Args:
        current_user: 當前用戶

    Returns:
        所有 Provider 的狀態列表
    """
    try:
        from services.api.models.llm_model import LLMProvider
        from services.api.services.llm_provider_config_service import (
            get_default_base_url,
            get_llm_provider_config_service,
        )

        config_service = get_llm_provider_config_service()
        providers = [
            LLMProvider.OPENAI,
            LLMProvider.GOOGLE,
            LLMProvider.XAI,
            LLMProvider.ANTHROPIC,
            LLMProvider.ALIBABA,
            LLMProvider.CHATGLM,
            LLMProvider.VOLCANO,
            LLMProvider.MISTRAL,
            LLMProvider.DEEPSEEK,
        ]

        statuses: list[Dict[str, Any]] = []
        for provider_enum in providers:
            try:
                status_obj = config_service.get_status(provider_enum)
                if status_obj:
                    statuses.append(status_obj.model_dump(mode="json", exclude_none=True))
                else:
                    # 如果配置不存在，返回默認狀態
                    default_base_url = get_default_base_url(provider_enum)
                    statuses.append(
                        {
                            "provider": provider_enum.value,
                            "has_api_key": False,
                            "base_url": default_base_url,
                            "default_model": None,
                        }
                    )
            except Exception as e:
                # 單個 Provider 失敗不影響其他
                logger.warning(f"Failed to get status for {provider_enum.value}: {str(e)}")
                default_base_url = get_default_base_url(provider_enum)
                statuses.append(
                    {
                        "provider": provider_enum.value,
                        "has_api_key": False,
                        "base_url": default_base_url,
                        "default_model": None,
                    }
                )

        return APIResponse.success(
            data={"statuses": statuses, "total": len(statuses)},
            message="All providers status retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to get all providers status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get("/providers/{provider}/api-key", status_code=status.HTTP_200_OK)
async def get_provider_api_key_status(
    provider: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取 Provider API key 狀態（需要管理員權限，不返回實際 key）

    Args:
        provider: Provider 名稱
        current_user: 當前用戶

    Returns:
        API key 狀態（不包含實際 key）。如果配置不存在，返回默認狀態（has_api_key: false）
    """
    # TODO: 添加管理員權限檢查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    try:
        from services.api.services.llm_provider_config_service import (
            get_llm_provider_config_service,
        )

        provider_enum = LLMProvider(provider)
        config_service = get_llm_provider_config_service()
        # get_status 會自動創建包含默認 base_url 的配置（如果不存在）
        status_obj = config_service.get_status(provider_enum)

        if not status_obj:
            # 如果仍然為 None（可能是沒有默認 base_url 的 provider），返回錯誤
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider '{provider}' not found and no default base URL available",
            )

        return APIResponse.success(
            data={"status": status_obj.model_dump(mode="json", exclude_none=True)},
            message="Provider API key status retrieved successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.delete("/providers/{provider}/api-key", status_code=status.HTTP_200_OK)
async def delete_provider_api_key(
    provider: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    刪除 Provider API key（需要管理員權限）

    Args:
        provider: Provider 名稱
        current_user: 當前用戶

    Returns:
        刪除結果
    """
    # TODO: 添加管理員權限檢查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    try:
        from services.api.services.llm_provider_config_service import (
            get_llm_provider_config_service,
        )

        provider_enum = LLMProvider(provider)
        config_service = get_llm_provider_config_service()
        success = config_service.delete_api_key(provider_enum, user_id=current_user.user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider config for '{provider}' not found",
            )

        return APIResponse.success(
            data={"deleted": True}, message="Provider API key deleted successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


class ProviderVerifyRequest(BaseModel):
    """Provider 驗證請求"""

    api_key: Optional[str] = Field(None, description="要測試的 API key（可選）")


@router.post("/providers/{provider}/verify", status_code=status.HTTP_200_OK)
async def verify_provider_connectivity(
    provider: str,
    request: Optional[ProviderVerifyRequest] = None,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    驗證 Provider 連通性（需要管理員權限）

    Args:
        provider: Provider 名稱
        request: 驗證請求（可包含臨時 API Key）
        current_user: 當前用戶

    Returns:
        驗證結果
    """
    # TODO: 添加管理員權限檢查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    try:
        from services.api.services.llm_provider_config_service import (
            get_llm_provider_config_service,
        )

        provider_enum = LLMProvider(provider)
        config_service = get_llm_provider_config_service()

        api_key = request.api_key if request else None
        result = await config_service.verify_provider_config(provider_enum, api_key=api_key)

        if result["success"]:
            return APIResponse.success(data=result, message=result["message"])
        else:
            return APIResponse.error(message=result["message"], details=result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to verify provider {provider}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
