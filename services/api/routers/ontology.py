# 代碼功能說明: Ontology API 路由
# 創建日期: 2025-12-18 19:39:14 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18 19:39:14 (UTC+8)

"""Ontology API 路由

提供 Ontology 的 CRUD API 端點。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.api.models.ontology import OntologyCreate, OntologyModel, OntologyUpdate
from services.api.services.ontology_store_service import get_ontology_store_service

router = APIRouter(prefix="/ontologies", tags=["Ontology"])


class OntologyListResponse(BaseModel):
    """Ontology 列表響應"""

    items: List[OntologyModel]
    total: int
    page: int
    page_size: int
    total_pages: int


class OntologyMergeRequest(BaseModel):
    """Ontology 合併請求"""

    domain_files: List[str]
    major_file: Optional[str] = None
    tenant_id: Optional[str] = None


@router.get("", response_model=OntologyListResponse)
async def list_ontologies(
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    type: Optional[str] = Query(None, description="Ontology 類型：base/domain/major"),
    name: Optional[str] = Query(None, description="名稱搜索"),
    is_active: Optional[bool] = Query(True, description="是否啟用"),
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(20, ge=1, le=100, description="每頁數量"),
) -> OntologyListResponse:
    """列表查詢 Ontology"""
    service = get_ontology_store_service()
    skip = (page - 1) * page_size

    ontologies = service.list_ontologies(
        tenant_id=tenant_id,
        type=type,
        name=name,
        is_active=is_active,
        skip=skip,
        limit=page_size,
    )

    # 簡化處理：總數計算需要額外的查詢
    total = len(ontologies)  # 這只是一個近似值
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return OntologyListResponse(
        items=ontologies,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{ontology_id}", response_model=OntologyModel)
async def get_ontology(
    ontology_id: str,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    version: Optional[str] = Query(None, description="版本號"),
) -> OntologyModel:
    """獲取單個 Ontology"""
    service = get_ontology_store_service()
    ontology = service.get_ontology(ontology_id, tenant_id=tenant_id)
    if not ontology:
        raise HTTPException(status_code=404, detail=f"Ontology not found: {ontology_id}")
    return ontology


@router.post("", status_code=201)
async def create_ontology(
    ontology: OntologyCreate,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
) -> Dict[str, Any]:
    """創建 Ontology"""
    service = get_ontology_store_service()
    try:
        ontology_id = service.save_ontology(ontology, tenant_id=tenant_id)
        return {"id": ontology_id, "message": "Ontology created successfully"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{ontology_id}", response_model=OntologyModel)
async def update_ontology(
    ontology_id: str,
    updates: OntologyUpdate,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
) -> OntologyModel:
    """更新 Ontology"""
    service = get_ontology_store_service()
    try:
        return service.update_ontology(ontology_id, updates, tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{ontology_id}")
async def delete_ontology(
    ontology_id: str,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    hard_delete: bool = Query(False, description="是否硬刪除"),
) -> Dict[str, str]:
    """刪除 Ontology"""
    service = get_ontology_store_service()
    try:
        success = service.delete_ontology(ontology_id, tenant_id=tenant_id, hard_delete=hard_delete)
        if not success:
            raise HTTPException(status_code=404, detail=f"Ontology not found: {ontology_id}")
        return {"message": "Ontology deleted successfully"}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/merge/query", response_model=Dict[str, Any])
async def merge_ontologies(
    domain_files: List[str] = Query(..., description="Domain 文件名列表"),
    major_file: Optional[str] = Query(None, description="Major 文件名"),
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
) -> Dict[str, Any]:
    """合併查詢 Ontology"""
    service = get_ontology_store_service()
    try:
        merged_rules = service.merge_ontologies(domain_files, major_file, tenant_id=tenant_id)
        return merged_rules
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
