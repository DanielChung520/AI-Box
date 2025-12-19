# 代碼功能說明: GenAI 使用者設定（LLM API Keys）管理 API
# 創建日期: 2025-12-13 23:34:17 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-13 23:34:17 (UTC+8)

"""GenAI user config API.

- 支援使用者自帶 API key（per-tenant/per-user 隔離）
- API 只回傳狀態，不回傳明文 key
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.genai_user_llm_secret import (
    GenAIUserLLMSecretStatusResponse,
    GenAIUserLLMSecretUpsertRequest,
)
from services.api.services.genai_user_llm_secret_service import get_genai_user_llm_secret_service
from system.security.dependencies import get_current_tenant_id, get_current_user
from system.security.models import User

router = APIRouter()


@router.get(
    "/genai/user/secrets/status",
    status_code=http_status.HTTP_200_OK,
)
async def get_user_secret_status(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    service = get_genai_user_llm_secret_service()
    providers = sorted(service.list_configured_providers(tenant_id=tenant_id, user_id=user.user_id))

    return APIResponse.success(
        data=GenAIUserLLMSecretStatusResponse(
            tenant_id=tenant_id,
            user_id=user.user_id,
            configured_providers=providers,
        ).model_dump(mode="json"),
        message="OK",
    )


@router.put(
    "/genai/user/secrets",
    status_code=http_status.HTTP_200_OK,
)
async def upsert_user_secrets(
    payload: GenAIUserLLMSecretUpsertRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    service = get_genai_user_llm_secret_service()
    for provider, api_key in (payload.keys or {}).items():
        prov = str(provider).strip().lower()
        key = str(api_key).strip()
        if not prov or not key:
            continue
        service.upsert(tenant_id=tenant_id, user_id=user.user_id, provider=prov, api_key=key)

    return APIResponse.success(data=None, message="User secrets updated")


@router.delete(
    "/genai/user/secrets/{provider}",
    status_code=http_status.HTTP_200_OK,
)
async def delete_user_secret(
    provider: str,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    service = get_genai_user_llm_secret_service()
    service.delete(tenant_id=tenant_id, user_id=user.user_id, provider=provider)
    return APIResponse.success(data=None, message="User secret deleted")
