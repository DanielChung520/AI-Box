# -*- coding: utf-8 -*-
"""
Data-Agent-JP mm_master API 路由

端點：
- GET /api/v1/mm-master/items - 取得所有料號
- GET /api/v1/mm-master/items/{item_no} - 取得單一料號
- GET /api/v1/mm-master/warehouses - 取得所有倉庫
- GET /api/v1/mm-master/warehouses/{wh_no} - 取得單一倉庫
- GET /api/v1/mm-master/workstations - 取得所有工作站
- GET /api/v1/mm-master/workstations/{ws_id} - 取得單一工作站
- GET /api/v1/mm-master/stats - 取得統計資訊

建立日期: 2026-02-10
建立人: Daniel Chung
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from database.arangodb.mm_master_client import (
    get_mm_master_client,
    ItemDocument,
    WarehouseDocument,
    WorkstationDocument,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/items")
async def get_items(
    limit: int = Query(default=100, ge=1, le=1000, description="返回數量上限"),
    offset: int = Query(default=0, ge=0, description="跳過數量"),
) -> dict:
    """
    取得所有料號

    Returns:
        dict: 料號清單
    """
    try:
        client = get_mm_master_client()
        items = client.get_all_items(limit=limit, offset=offset)
        return {
            "status": "success",
            "data": [item.to_doc() for item in items],
            "count": len(items),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Failed to get items: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get items: {str(e)}")


@router.get("/items/{item_no}")
async def get_item(item_no: str) -> dict:
    """
    取得單一料號

    Args:
        item_no: 料號

    Returns:
        dict: 料號資料
    """
    try:
        client = get_mm_master_client()
        item = client.get_item(item_no)

        if item is None:
            raise HTTPException(status_code=404, detail=f"Item not found: {item_no}")

        return {
            "status": "success",
            "data": item.to_doc(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get item {item_no}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get item: {str(e)}")


@router.get("/warehouses")
async def get_warehouses(
    limit: int = Query(default=100, ge=1, le=500, description="返回數量上限"),
    offset: int = Query(default=0, ge=0, description="跳過數量"),
) -> dict:
    """
    取得所有倉庫

    Returns:
        dict: 倉庫清單
    """
    try:
        client = get_mm_master_client()
        warehouses = client.get_all_warehouses(limit=limit, offset=offset)
        return {
            "status": "success",
            "data": [wh.to_doc() for wh in warehouses],
            "count": len(warehouses),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Failed to get warehouses: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get warehouses: {str(e)}")


@router.get("/warehouses/{warehouse_no}")
async def get_warehouse(warehouse_no: str) -> dict:
    """
    取得單一倉庫

    Args:
        warehouse_no: 倉庫代碼

    Returns:
        dict: 倉庫資料
    """
    try:
        client = get_mm_master_client()
        warehouse = client.get_warehouse(warehouse_no)

        if warehouse is None:
            raise HTTPException(status_code=404, detail=f"Warehouse not found: {warehouse_no}")

        return {
            "status": "success",
            "data": warehouse.to_doc(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get warehouse {warehouse_no}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get warehouse: {str(e)}")


@router.get("/workstations")
async def get_workstations(
    limit: int = Query(default=100, ge=1, le=500, description="返回數量上限"),
    offset: int = Query(default=0, ge=0, description="跳過數量"),
) -> dict:
    """
    取得所有工作站

    Returns:
        dict: 工作站清單
    """
    try:
        client = get_mm_master_client()
        workstations = client.get_all_workstations(limit=limit, offset=offset)
        return {
            "status": "success",
            "data": [ws.to_doc() for ws in workstations],
            "count": len(workstations),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Failed to get workstations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workstations: {str(e)}")


@router.get("/workstations/{workstation_id}")
async def get_workstation(workstation_id: str) -> dict:
    """
    取得單一工作站

    Args:
        workstation_id: 工作站 ID

    Returns:
        dict: 工作站資料
    """
    try:
        client = get_mm_master_client()
        workstation = client.get_workstation(workstation_id)

        if workstation is None:
            raise HTTPException(status_code=404, detail=f"Workstation not found: {workstation_id}")

        return {
            "status": "success",
            "data": workstation.to_doc(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workstation {workstation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workstation: {str(e)}")


@router.get("/stats")
async def get_stats() -> dict:
    """
    取得統計資訊

    Returns:
        dict: 統計資訊
    """
    try:
        client = get_mm_master_client()
        counts = client.count_by_type()

        return {
            "status": "success",
            "data": {
                "total_documents": sum(counts.values()),
                "by_type": counts,
            },
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/validate/item/{item_no}")
async def validate_item(item_no: str) -> dict:
    """
    驗證料號是否存在

    Args:
        item_no: 料號

    Returns:
        dict: 驗證結果
    """
    try:
        client = get_mm_master_client()
        is_valid, item = client.validate_item(item_no)

        return {
            "status": "success",
            "valid": is_valid,
            "data": item.to_doc() if item else None,
        }
    except Exception as e:
        logger.error(f"Failed to validate item {item_no}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate item: {str(e)}")


@router.get("/validate/warehouse/{warehouse_no}")
async def validate_warehouse(warehouse_no: str) -> dict:
    """
    驗證倉庫是否存在

    Args:
        warehouse_no: 倉庫代碼

    Returns:
        dict: 驗證結果
    """
    try:
        client = get_mm_master_client()
        is_valid, warehouse = client.validate_warehouse(warehouse_no)

        return {
            "status": "success",
            "valid": is_valid,
            "data": warehouse.to_doc() if warehouse else None,
        }
    except Exception as e:
        logger.error(f"Failed to validate warehouse {warehouse_no}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate warehouse: {str(e)}")


@router.get("/validate/workstation/{workstation_id}")
async def validate_workstation(workstation_id: str) -> dict:
    """
    驗證工作站是否存在

    Args:
        workstation_id: 工作站 ID

    Returns:
        dict: 驗證結果
    """
    try:
        client = get_mm_master_client()
        is_valid, workstation = client.validate_workstation(workstation_id)

        return {
            "status": "success",
            "valid": is_valid,
            "data": workstation.to_doc() if workstation else None,
        }
    except Exception as e:
        logger.error(f"Failed to validate workstation {workstation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate workstation: {str(e)}")


@router.get("/health")
async def health_check() -> dict:
    """
    健康檢查

    Returns:
        dict: 健康狀態
    """
    try:
        client = get_mm_master_client()
        health = client.health_check()
        return health
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
