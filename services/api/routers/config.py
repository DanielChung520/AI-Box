# 代碼功能說明: Config API 路由
# 創建日期: 2025-12-18 19:39:14 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18 19:39:14 (UTC+8)

"""Config API 路由

提供 Config 的 CRUD API 端點和有效配置查詢。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from services.api.models.config import ConfigCreate, ConfigModel, ConfigUpdate, EffectiveConfig
from services.api.services.config_store_service import get_config_store_service

router = APIRouter(prefix="/configs", tags=["Config"])


@router.get("/effective", response_model=EffectiveConfig)
async def get_effective_config(
    scope: str = Query(..., description="配置範圍，如 genai.policy"),
    tenant_id: str = Query(..., description="租戶 ID"),
    user_id: Optional[str] = Query(None, description="用戶 ID"),
) -> EffectiveConfig:
    """獲取有效配置（合併 system → tenant → user）"""
    service = get_config_store_service()
    try:
        return service.get_effective_config(scope, tenant_id, user_id=user_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/system", response_model=ConfigModel)
async def get_system_config(
    scope: str = Query(..., description="配置範圍"),
) -> ConfigModel:
    """獲取系統配置"""
    service = get_config_store_service()
    config = service.get_config(scope, tenant_id=None, user_id=None)
    if not config:
        raise HTTPException(status_code=404, detail=f"System config not found: {scope}")
    return config


@router.get("/tenant/{tenant_id}", response_model=ConfigModel)
async def get_tenant_config(
    tenant_id: str,
    scope: str = Query(..., description="配置範圍"),
) -> ConfigModel:
    """獲取租戶配置"""
    service = get_config_store_service()
    config = service.get_config(scope, tenant_id=tenant_id, user_id=None)
    if not config:
        raise HTTPException(
            status_code=404, detail=f"Tenant config not found: {scope} for tenant {tenant_id}"
        )
    return config


@router.post("", status_code=201)
async def create_config(
    config: ConfigCreate,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    user_id: Optional[str] = Query(None, description="用戶 ID"),
) -> Dict[str, Any]:
    """創建配置"""
    service = get_config_store_service()
    try:
        config_id = service.save_config(config, tenant_id=tenant_id, user_id=user_id)
        return {"id": config_id, "message": "Config saved successfully"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{config_id}", response_model=ConfigModel)
async def update_config(
    config_id: str,
    updates: ConfigUpdate,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    user_id: Optional[str] = Query(None, description="用戶 ID"),
) -> ConfigModel:
    """更新配置"""
    service = get_config_store_service()
    try:
        return service.update_config(config_id, updates, tenant_id=tenant_id, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{config_id}")
async def delete_config(
    config_id: str,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    hard_delete: bool = Query(False, description="是否硬刪除"),
) -> Dict[str, str]:
    """刪除配置"""
    service = get_config_store_service()
    try:
        success = service.delete_config(config_id, tenant_id=tenant_id, hard_delete=hard_delete)
        if not success:
            raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")
        return {"message": "Config deleted successfully"}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
