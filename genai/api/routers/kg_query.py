# 代碼功能說明: 知識圖譜查詢路由
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""知識圖譜查詢路由 - 提供圖譜查詢 API 端點"""

from typing import Optional, List
from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from genai.api.services.kg_builder_service import KGBuilderService

router = APIRouter(prefix="/kg", tags=["Knowledge Graph Query"])

# 全局服務實例（懶加載）
_service: Optional[KGBuilderService] = None


def get_service() -> KGBuilderService:
    """獲取知識圖譜構建服務實例（單例模式）"""
    global _service
    if _service is None:
        _service = KGBuilderService()
    return _service


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: str) -> JSONResponse:
    """查詢實體"""
    service = get_service()

    entity = service.get_entity(entity_id)
    if entity is None:
        return APIResponse.error(
            message="實體不存在",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return APIResponse.success(data=entity)


@router.get("/entities")
async def list_entities(
    entity_type: Optional[str] = Query(None, description="實體類型篩選"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> JSONResponse:
    """查詢實體列表"""
    service = get_service()

    entities = service.list_entities(
        entity_type=entity_type, limit=limit, offset=offset
    )

    return APIResponse.success(
        data={
            "entities": entities,
            "total": len(entities),
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/relations")
async def list_relations(
    relation_type: Optional[str] = Query(None, description="關係類型篩選"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> JSONResponse:
    """查詢關係列表"""
    service = get_service()

    # 使用 AQL 查詢關係
    if service.client.db is None:
        return APIResponse.error(
            message="數據庫連接不可用",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    if service.client.db.aql is None:
        return APIResponse.error(
            message="AQL 不可用",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    aql = "FOR doc IN relations"
    bind_vars: dict = {}

    if relation_type:
        aql += " FILTER doc.type == @relation_type"
        bind_vars["relation_type"] = relation_type

    aql += " LIMIT @offset, @limit"
    bind_vars["offset"] = offset
    bind_vars["limit"] = limit

    cursor = service.client.db.aql.execute(aql, bind_vars=bind_vars)
    relations = list(cursor)

    return APIResponse.success(
        data={
            "relations": relations,
            "total": len(relations),
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/entities/{entity_id}/neighbors")
async def get_entity_neighbors(
    entity_id: str,
    relation_types: Optional[List[str]] = Query(None, description="關係類型篩選"),
    limit: int = Query(20, ge=1, le=100, description="返回數量限制"),
) -> JSONResponse:
    """獲取實體的鄰居節點"""
    service = get_service()

    neighbors = service.get_entity_neighbors(
        entity_id, relation_types=relation_types, limit=limit
    )

    return APIResponse.success(
        data={
            "entity_id": entity_id,
            "neighbors": neighbors,
            "total": len(neighbors),
        }
    )


@router.get("/entities/{entity_id}/subgraph")
async def get_entity_subgraph(
    entity_id: str,
    max_depth: int = Query(2, ge=1, le=5, description="最大深度"),
    limit: int = Query(50, ge=1, le=200, description="返回數量限制"),
) -> JSONResponse:
    """獲取實體的 N 度關係子圖"""
    service = get_service()

    subgraph = service.get_entity_subgraph(entity_id, max_depth=max_depth, limit=limit)

    return APIResponse.success(
        data={
            "entity_id": entity_id,
            "subgraph": subgraph,
            "max_depth": max_depth,
            "total": len(subgraph),
        }
    )
