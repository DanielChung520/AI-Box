# 代碼功能說明: ArangoDB 查詢封裝測試
# 創建日期: 2025-11-25 22:58 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 22:58 (UTC+8)

"""測試 queries.py 中的查詢封裝。"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from database.arangodb import queries


class DummyClient:
    def __init__(self):
        self.last_call: Dict[str, Any] = {}

    def execute_aql(self, query: str, bind_vars: Dict[str, Any]):
        self.last_call = {"query": query, "bind_vars": bind_vars}
        return {"results": [{"ok": True}]}


def test_fetch_neighbors_calls_aql_with_expected_bindings():
    client = DummyClient()
    result = queries.fetch_neighbors(
        client,
        "entities/agent_planning",
        edge_collection="relations",
        direction="outbound",
        relation_types=["handles"],
        limit=5,
    )
    assert result == [{"ok": True}]
    assert client.last_call["bind_vars"]["relation_types"] == ["handles"]
    assert client.last_call["bind_vars"]["limit"] == 5


def test_fetch_subgraph_direction_validation():
    client = DummyClient()
    with pytest.raises(ValueError):
        queries.fetch_subgraph(client, "entities/agent_planning", direction="invalid")


def test_filter_entities_supports_list_filters():
    client = DummyClient()
    result = queries.filter_entities(
        client,
        collection="entities",
        filters={"type": ["agent", "task"], "owner": "AI-Core"},
        limit=10,
        offset=5,
        sort_field="updated_at",
        sort_desc=True,
    )
    assert result == [{"ok": True}]
    bind_vars = client.last_call["bind_vars"]
    assert bind_vars["limit"] == 10
    assert bind_vars["offset"] == 5
    assert "doc.type IN" in client.last_call["query"]
