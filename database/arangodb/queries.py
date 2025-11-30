# 代碼功能說明: ArangoDB 常用圖查詢
# 創建日期: 2025-11-25 22:58 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 22:58 (UTC+8)

"""定義 AI-Box 知識圖譜的常用查詢封裝。"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .client import ArangoDBClient

_ALLOWED_DIRECTIONS = {"outbound", "inbound", "any"}


def _normalize_direction(direction: str) -> str:
    """驗證並整理 AQL 遍歷方向。"""
    normalized = direction.lower()
    if normalized not in _ALLOWED_DIRECTIONS:
        raise ValueError(f"不支援的遍歷方向: {direction}")
    return normalized


def fetch_neighbors(
    client: ArangoDBClient,
    vertex_id: str,
    *,
    edge_collection: str = "relations",
    direction: str = "any",
    relation_types: Optional[Iterable[str]] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    取得指定頂點的鄰居與對應邊。

    Args:
        client: ArangoDBClient 實例
        vertex_id: 起始頂點 ID（collection/_key）
        edge_collection: 邊集合名稱
        direction: 遍歷方向 outbound/inbound/any
        relation_types: 若提供則只回傳指定 type 的關係
        limit: 回傳上限
    """
    traversal_direction = _normalize_direction(direction)
    query = f"""
        FOR v, e IN 1..1 {traversal_direction.upper()} @start_vertex @@edge_collection
            FILTER @relation_types == null OR e.type IN @relation_types
            LIMIT @limit
            RETURN {{
                vertex: v,
                edge: e
            }}
    """
    bind_vars: Dict[str, Any] = {
        "start_vertex": vertex_id,
        "@edge_collection": edge_collection,
        "relation_types": list(relation_types) if relation_types else None,
        "limit": limit,
    }
    result = client.execute_aql(query, bind_vars=bind_vars)
    return result["results"]


def fetch_subgraph(
    client: ArangoDBClient,
    start_vertex: str,
    *,
    edge_collection: str = "relations",
    direction: str = "any",
    max_depth: int = 2,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    擷取以 start_vertex 為中心的子圖。

    Args:
        client: ArangoDBClient 實例
        start_vertex: 根節點 ID
        edge_collection: 邊集合名稱
        direction: 遍歷方向
        max_depth: 最大深度
        limit: 路徑上限
    """
    traversal_direction = _normalize_direction(direction)
    query = f"""
        FOR v, e, p IN 1..@max_depth {traversal_direction.upper()}
        @start_vertex @@edge_collection
            LIMIT @limit
            RETURN {{
                path: p,
                vertex: v,
                edge: e
            }}
    """
    bind_vars = {
        "start_vertex": start_vertex,
        "@edge_collection": edge_collection,
        "max_depth": max_depth,
        "limit": limit,
    }
    return client.execute_aql(query, bind_vars=bind_vars)["results"]


def filter_entities(
    client: ArangoDBClient,
    *,
    collection: str = "entities",
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 20,
    offset: int = 0,
    sort_field: Optional[str] = None,
    sort_desc: bool = False,
) -> List[Dict[str, Any]]:
    """
    依欄位條件過濾實體集合。

    支援 list 值（使用 IN）與單值（使用 ==）。
    """
    filters = filters or {}
    conditions: List[str] = []
    bind_vars: Dict[str, Any] = {
        "@collection": collection,
        "limit": limit,
        "offset": offset,
    }

    for idx, (field, value) in enumerate(filters.items()):
        key = f"filter_{idx}"
        bind_vars[key] = value
        if isinstance(value, list):
            conditions.append(f"doc.{field} IN @{key}")
        else:
            conditions.append(f"doc.{field} == @{key}")

    filter_clause = ""
    if conditions:
        filter_clause = "FILTER " + " AND ".join(conditions)

    sort_clause = ""
    if sort_field:
        direction = "DESC" if sort_desc else "ASC"
        sort_clause = f"SORT doc.{sort_field} {direction}"

    query = f"""
        FOR doc IN @@collection
            {filter_clause}
            {sort_clause}
            LIMIT @offset, @limit
            RETURN doc
    """
    return client.execute_aql(query, bind_vars=bind_vars)["results"]
