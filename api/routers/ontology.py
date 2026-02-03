# 代碼功能說明: Ontology API 路由（方案 B：Agent 知識庫上架）
# 創建日期: 2026-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-27 24:45 UTC+8

"""Ontology API - 依 task_id 查詢、匯入 Ontology（前端統一上架方案 B）"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, status, UploadFile
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.ontology import OntologyCreate
from services.api.services.ontology_store_service import get_ontology_store_service
from system.security.dependencies import get_current_user
from system.security.models import Permission, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ontologies", tags=["Ontology"])

REQUIRED_ONTOLOGY_KEYS = (
    "type",
    "name",
    "version",
    "ontology_name",
    "entity_classes",
    "object_properties",
)


async def _require_system_admin(user: User = Depends(get_current_user)) -> User:
    """僅 systemAdmin 或具 Permission.ALL 的用戶可訪問 Ontology 匯入等管理操作。"""
    from system.security.config import get_security_settings

    settings = get_security_settings()
    if getattr(settings, "should_bypass_auth", False):
        return user
    if not getattr(getattr(settings, "rbac", None), "enabled", True):
        return user
    if user.has_permission(Permission.ALL.value):
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions. Required: system_admin or ontology management.",
    )


def _validate_ontology_json(data: Dict[str, Any], filename: str) -> List[str]:
    """驗證 Ontology JSON 格式與必填屬性，回傳錯誤訊息列表。"""
    errs: List[str] = []
    for key in REQUIRED_ONTOLOGY_KEYS:
        if key not in data:
            errs.append(f"{filename}: 缺少必填屬性 '{key}'")
            continue
        val = data[key]
        if key == "type" and val not in ("base", "domain", "major"):
            errs.append(f"{filename}: 'type' 須為 base/domain/major")
        elif key in ("entity_classes", "object_properties") and not isinstance(val, list):
            errs.append(f"{filename}: '{key}' 須為陣列")
    return errs


@router.get("", status_code=status.HTTP_200_OK)
async def list_ontologies_by_task_id(
    task_id: Optional[str] = Query(None, description="Agent 代碼（如 KA-Agent、MM-Agent）"),
    limit: int = Query(50, ge=1, le=100, description="返回數量上限"),
) -> JSONResponse:
    """依 task_id 查詢關聯 Ontology，供前端判斷是否已有 Ontology（方案 B）。"""
    if not task_id or not task_id.strip():
        return APIResponse.success(
            data={"items": [], "has_any": False},
            message="未提供 task_id",
        )
    try:
        svc = get_ontology_store_service()
        items = svc.list_ontologies_by_task_id(task_id=task_id.strip(), limit=limit)
        return APIResponse.success(
            data={
                "items": [
                    {
                        "id": m.id,
                        "type": m.type,
                        "name": m.name,
                        "version": m.version,
                        "ontology_name": m.ontology_name,
                    }
                    for m in items
                ],
                "has_any": len(items) > 0,
            },
        )
    except Exception as e:
        logger.exception("list_ontologies_by_task_id failed: task_id=%s", task_id)
        return APIResponse.error(
            message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_ontologies(
    files: List[UploadFile] = File(..., description="Ontology JSON 檔案"),
    current_user: User = Depends(_require_system_admin),
) -> JSONResponse:
    """上傳並匯入 Ontology JSON 檔案（僅 systemAdmin/授權用戶）。"""
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="請選擇至少一個檔案")
    imported: List[str] = []
    errors: List[str] = []
    svc = get_ontology_store_service()

    for uf in files:
        fn = uf.filename or "unknown"
        if not fn.lower().endswith(".json"):
            errors.append(f"{fn}: 僅支援 .json 檔案")
            continue
        try:
            raw = await uf.read()
            try:
                data = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as e:
                errors.append(f"{fn}: JSON 格式錯誤 — {e}")
                continue
            if not isinstance(data, dict):
                errors.append(f"{fn}: 根須為 JSON 物件")
                continue
            errs = _validate_ontology_json(data, fn)
            if errs:
                errors.extend(errs)
                continue
            oc = OntologyCreate(
                type=data["type"],
                name=data["name"],
                version=data["version"],
                default_version=data.get("default_version", False),
                ontology_name=data["ontology_name"],
                description=data.get("description"),
                author=data.get("author"),
                last_modified=data.get("last_modified"),
                inherits_from=data.get("inherits_from") or [],
                compatible_domains=data.get("compatible_domains") or [],
                tags=data.get("tags") or [],
                use_cases=data.get("use_cases") or [],
                entity_classes=data.get("entity_classes") or [],
                object_properties=data.get("object_properties") or [],
                metadata=data.get("metadata") or {},
                tenant_id=data.get("tenant_id"),
            )
            oid = svc.save_ontology(oc, tenant_id=oc.tenant_id, changed_by=current_user.user_id)
            imported.append(oid)
        except Exception as e:
            logger.exception("import ontology file failed: %s", fn)
            errors.append(f"{fn}: {e}")

    if errors and not imported:
        return APIResponse.error(
            message="Ontology 驗證或匯入失敗",
            details={"errors": errors},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return APIResponse.success(
        data={"imported": imported, "errors": errors},
        message=f"已匯入 {len(imported)} 個 Ontology"
        + (f"，{len(errors)} 個失敗" if errors else ""),
        status_code=status.HTTP_201_CREATED,
    )
