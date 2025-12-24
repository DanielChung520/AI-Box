# 代碼功能說明: GenAI 多租戶（Tenant/Org）政策與 Secrets 管理 API
# 創建日期: 2025-12-13 23:34:17 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-13 23:34:17 (UTC+8)

"""GenAI Tenant config API.

- Policy：非敏感，可查詢/更新
- Secrets：敏感，只提供寫入/刪除（不回傳明文）

多租戶辨識：`X-Tenant-ID`（或 user.metadata.tenant_id）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.core.response import APIResponse
from services.api.models.genai_tenant_policy import GenAITenantPolicyUpdate
from services.api.services.genai_tenant_policy_service import get_genai_tenant_policy_service
from system.security.dependencies import require_any_permission
from system.security.models import Permission, User

router = APIRouter()


class TenantSecretsUpsertRequest(BaseModel):
    keys: dict[str, str] = Field(default_factory=dict, description="provider -> api_key（不會回傳明文）")


@router.get(
    "/genai/tenants/{tenant_id}/policy",
    status_code=http_status.HTTP_200_OK,
)
async def get_tenant_policy(
    tenant_id: str,
    user: User = Depends(
        require_any_permission(Permission.ALL.value, Permission.AGENT_MANAGE.value)
    ),
) -> JSONResponse:
    service = get_genai_tenant_policy_service()
    policy = service.get_policy(tenant_id=tenant_id)
    if policy is None:
        return APIResponse.success(
            data=None,
            message="Tenant policy not set",
        )
    return APIResponse.success(data=policy.model_dump(mode="json"))


@router.put(
    "/genai/tenants/{tenant_id}/policy",
    status_code=http_status.HTTP_200_OK,
)
async def upsert_tenant_policy(
    tenant_id: str,
    payload: GenAITenantPolicyUpdate,
    user: User = Depends(
        require_any_permission(Permission.ALL.value, Permission.AGENT_MANAGE.value)
    ),
) -> JSONResponse:
    _ = user
    service = get_genai_tenant_policy_service()
    policy = service.upsert_policy(tenant_id=tenant_id, update=payload)
    return APIResponse.success(data=policy.model_dump(mode="json"))


@router.put(
    "/genai/tenants/{tenant_id}/secrets",
    status_code=http_status.HTTP_200_OK,
)
async def upsert_tenant_secrets(
    tenant_id: str,
    payload: TenantSecretsUpsertRequest,
    user: User = Depends(
        require_any_permission(Permission.ALL.value, Permission.AGENT_MANAGE.value)
    ),
) -> JSONResponse:
    _ = user
    service = get_genai_tenant_policy_service()
    for provider, key in (payload.keys or {}).items():
        prov = str(provider).strip().lower()
        if not prov or not str(key).strip():
            continue
        service.set_tenant_secret(tenant_id=tenant_id, provider=prov, api_key=str(key))

    return APIResponse.success(data=None, message="Tenant secrets updated")


@router.delete(
    "/genai/tenants/{tenant_id}/secrets/{provider}",
    status_code=http_status.HTTP_200_OK,
)
async def delete_tenant_secret(
    tenant_id: str,
    provider: str,
    user: User = Depends(
        require_any_permission(Permission.ALL.value, Permission.AGENT_MANAGE.value)
    ),
) -> JSONResponse:
    _ = user
    service = get_genai_tenant_policy_service()
    service.delete_tenant_secret(tenant_id=tenant_id, provider=provider)
    return APIResponse.success(data=None, message="Tenant secret deleted")
