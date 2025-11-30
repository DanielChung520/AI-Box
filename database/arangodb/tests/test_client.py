# 代碼功能說明: ArangoDB 客戶端與封裝單元測試
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 22:58 (UTC+8)

"""ArangoDB 客戶端/集合/圖操作單元測試（使用內存假件）。"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, List, Optional

import pytest

from database.arangodb import (
    ArangoCollection,
    ArangoDBClient,
    ArangoDBSettings,
    ArangoGraph,
)


class FakeCursor:
    def __init__(self, results: List[Dict[str, Any]]):
        self._results = results

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return iter(self._results)

    def count(self) -> int:
        return len(self._results)


class FakeAQL:
    def __init__(self):
        self.should_raise = False
        self.last_query = None

    def execute(self, query: str, **_: Any) -> FakeCursor:
        if self.should_raise:
            raise RuntimeError("AQL failed")
        self.last_query = query
        return FakeCursor([{"result": True}])


class FakeCollectionBackend:
    def __init__(self, name: str):
        self.name = name
        self.edge = False
        self._docs: Dict[str, Dict[str, Any]] = {}

    def insert(self, document: Any, return_new: bool = False):
        docs = document if isinstance(document, list) else [document]
        for doc in docs:
            self._docs[doc["_key"]] = doc
        return docs[0] if not isinstance(document, list) else docs

    def get(self, key: str, **_: Any):
        return self._docs.get(key)

    def update(self, document: Dict[str, Any], **_: Any):
        self._docs[document["_key"]].update(document)
        return document

    def replace(self, document: Dict[str, Any], **_: Any):
        self._docs[document["_key"]] = document
        return document

    def delete(self, document: Any, **_: Any):
        keys = document if isinstance(document, list) else [document]
        for key in keys:
            key_id = key if isinstance(key, str) else key["_key"]
            self._docs.pop(key_id, None)
        return True

    def find(
        self, filters: Optional[Dict[str, Any]] = None, **_: Any
    ) -> Iterable[Dict[str, Any]]:
        filters = filters or {}
        for doc in self._docs.values():
            if all(doc.get(k) == v for k, v in filters.items()):
                yield doc

    def count(self) -> int:
        return len(self._docs)

    def truncate(self):
        self._docs.clear()
        return True


class FakeGraphBackend:
    def __init__(self, name: str):
        self.name = name
        self.vertex_collections: Dict[str, FakeCollectionBackend] = {}
        self.edges: Dict[str, Dict[str, Any]] = {}

    def create_vertex_collection(self, name: str):
        self.vertex_collections.setdefault(name, FakeCollectionBackend(name))

    def create_edge_definition(self, **_: Any):
        return True

    def insert_vertex(self, collection: str, vertex: Dict[str, Any]):
        self.vertex_collections.setdefault(
            collection, FakeCollectionBackend(collection)
        )
        self.vertex_collections[collection]._docs[vertex["_key"]] = vertex
        return vertex

    def vertex(self, vertex_id: str):
        collection, key = vertex_id.split("/", 1)
        return self.vertex_collections.get(
            collection, FakeCollectionBackend(collection)
        )._docs.get(key)

    def insert_edge(
        self, collection: str, edge: Dict[str, Any], from_vertex: str, to_vertex: str
    ):
        edge_doc = edge.copy()
        edge_doc["_from"] = from_vertex
        edge_doc["_to"] = to_vertex
        self.edges.setdefault(collection, {})[
            edge_doc.get("_key", f"{from_vertex}-{to_vertex}")
        ] = edge_doc
        return edge_doc


class FakeDatabase:
    def __init__(self):
        self._collections: Dict[str, FakeCollectionBackend] = {}
        self._graphs: Dict[str, FakeGraphBackend] = {}
        self.aql = FakeAQL()

    def has_collection(self, name: str) -> bool:
        return name in self._collections

    def create_collection(self, name: str, edge: bool = False):
        col = FakeCollectionBackend(name)
        col.edge = edge
        self._collections[name] = col

    def collection(self, name: str) -> FakeCollectionBackend:
        return self._collections[name]

    def delete_collection(self, name: str, ignore_missing: bool = False):
        if name not in self._collections and not ignore_missing:
            raise KeyError("missing")
        self._collections.pop(name, None)

    def collections(self) -> List[Dict[str, str]]:
        return [{"name": name} for name in self._collections]

    def list_collections(self):
        return self.collections()

    def has_graph(self, name: str) -> bool:
        return name in self._graphs

    def create_graph(
        self, name: str, edge_definitions: Optional[List[Dict[str, Any]]] = None
    ):
        graph = FakeGraphBackend(name)
        if edge_definitions:
            for edge in edge_definitions:
                graph.create_edge_definition(**edge)
        self._graphs[name] = graph

    def graph(self, name: str) -> FakeGraphBackend:
        return self._graphs[name]


@pytest.fixture
def fake_db() -> FakeDatabase:
    return FakeDatabase()


@pytest.fixture
def arango_client(fake_db: FakeDatabase) -> ArangoDBClient:
    settings = ArangoDBSettings(host="localhost", port=8529, database="test_db")
    client = ArangoDBClient(settings=settings, connect_on_init=False)
    client.db = fake_db  # type: ignore[assignment]
    client.client = object()  # type: ignore[assignment]
    return client


@pytest.fixture
def test_collection(arango_client: ArangoDBClient) -> ArangoCollection:
    backend = arango_client.get_or_create_collection("test_collection")
    return ArangoCollection(backend)


def test_get_or_create_collection(arango_client: ArangoDBClient):
    collection = arango_client.get_or_create_collection("entities")
    assert collection.name == "entities"
    # second call should not create duplicates
    same = arango_client.get_or_create_collection("entities")
    assert same is collection


def test_list_and_delete_collections(arango_client: ArangoDBClient):
    arango_client.get_or_create_collection("c1")
    arango_client.get_or_create_collection("c2")
    names = arango_client.list_collections()
    assert "c1" in names and "c2" in names
    arango_client.delete_collection("c1")
    assert "c1" not in arango_client.list_collections()


def test_collection_crud_operations(test_collection: ArangoCollection):
    test_collection.insert({"_key": "doc1", "name": "Demo", "type": "test"})
    assert test_collection.count() == 1
    doc = test_collection.get("doc1")
    assert doc is not None
    assert doc["name"] == "Demo"
    test_collection.update({"_key": "doc1", "name": "Updated"})
    updated_doc = test_collection.get("doc1")
    assert updated_doc is not None
    assert updated_doc["name"] == "Updated"
    results = list(test_collection.find(filters={"type": "test"}))
    assert len(results) == 1
    test_collection.delete("doc1")
    assert test_collection.count() == 0


def test_graph_operations(arango_client: ArangoDBClient):
    graph_backend = arango_client.get_or_create_graph(
        "kg",
        edge_definitions=[
            {
                "edge_collection": "relations",
                "from_vertex_collections": ["entities"],
                "to_vertex_collections": ["entities"],
            }
        ],
    )
    arango_graph = ArangoGraph(graph_backend)
    arango_graph.create_vertex_collection("entities")
    arango_graph.insert_vertex("entities", {"_key": "node1", "name": "Node 1"})
    vertex = arango_graph.get_vertex("entities/node1")
    assert vertex is not None
    assert vertex["name"] == "Node 1"


def test_execute_aql(arango_client: ArangoDBClient):
    result = arango_client.execute_aql(
        "FOR doc IN @@col RETURN doc", bind_vars={"@col": "entities"}
    )
    assert result["results"][0]["result"] is True
    assert result["count"] is None


def test_execute_aql_error(arango_client: ArangoDBClient):
    if arango_client.db:
        arango_client.db.aql.should_raise = True  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError):
        arango_client.execute_aql(
            "FOR doc IN @@col RETURN doc", bind_vars={"@col": "entities"}
        )


def test_heartbeat(arango_client: ArangoDBClient):
    status = arango_client.heartbeat()
    assert status["status"] == "healthy"
    arango_client.db = None
    unhealthy = arango_client.heartbeat()
    assert unhealthy["status"] == "unhealthy"
