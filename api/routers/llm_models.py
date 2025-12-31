# 代碼功能說明: LLM 模型管理 API 路由
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""LLM 模型管理 API - 提供模型列表、創建、更新、刪除等操作"""

from typing import Optional

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
from system.security.dependencies import get_current_user
from system.security.models import User

router = APIRouter(prefix="/models", tags=["LLM Models"])


@router.get("", status_code=status.HTTP_200_OK)
async def get_models(
    provider: Optional[str] = None,
    status_filter: Optional[str] = None,
    capability: Optional[str] = None,
    search: Optional[str] = None,
    include_discovered: bool = True,
    include_favorite_status: bool = True,
    limit: int = 1000,  # 增加默認限制，確保返回所有模型
    offset: int = 0,
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

        return APIResponse.success(
            data={
                "models": [model.model_dump(mode="json", exclude_none=True) for model in models],
                "total": len(models),
            },
            message="Models retrieved successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


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
        config_service.set_api_key(provider_enum, request.api_key)

        return APIResponse.success(
            data={"provider": provider, "has_api_key": True},
            message="Provider API key set successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
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
        API key 狀態（不包含實際 key）
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
        status_obj = config_service.get_status(provider_enum)

        if not status_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider config for '{provider}' not found",
            )

        return APIResponse.success(
            data={"status": status_obj.model_dump(exclude_none=True)},
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
        success = config_service.delete_api_key(provider_enum)

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
