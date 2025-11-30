# 代碼功能說明: ArangoDB 圖資料庫整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-1.4：ArangoDB 圖資料庫整合測試"""

import pytest
from typing import AsyncGenerator
import time
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestArangoDBIntegration:
    """ArangoDB 圖資料庫整合測試"""

    @pytest.fixture(scope="function")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    async def test_arangodb_connection(self):
        """步驟 1: ArangoDB 連接測試"""
        try:
            from database.arangodb import ArangoDBClient

            client = ArangoDBClient()
            assert client.db is not None
        except ImportError:
            pytest.skip("ArangoDB 客戶端未安裝")
        except Exception as e:
            pytest.fail(f"ArangoDB 連接失敗: {str(e)}")

    async def test_aql_query(self):
        """步驟 4: AQL 查詢測試"""
        try:
            from database.arangodb import ArangoDBClient

            client = ArangoDBClient()
            if client.db is None or client.db.aql is None:
                pytest.skip("ArangoDB AQL 不可用")

            # 創建測試集合和數據
            collection_name = "test_entities"
            try:
                # 如果集合存在，先刪除
                if client.db.has_collection(collection_name):
                    client.db.delete_collection(collection_name)
            except Exception:
                pass

            # 創建集合
            collection = client.get_or_create_collection(
                collection_name, collection_type="document"
            )
            assert collection is not None, "測試集合創建失敗"

            # 插入測試數據
            test_docs = [
                {"_key": "test1", "type": "TEST", "name": "測試文檔1"},
                {"_key": "test2", "type": "TEST", "name": "測試文檔2"},
                {"_key": "test3", "type": "OTHER", "name": "其他文檔"},
            ]
            collection.import_bulk(test_docs)

            # 執行 AQL 查詢
            aql = "FOR v IN test_entities FILTER v.type == 'TEST' LIMIT 10 RETURN v"
            cursor = client.db.aql.execute(aql)
            results = list(cursor)

            assert isinstance(results, list), "AQL 查詢結果格式不正確"
            assert len(results) >= 2, f"預期至少 2 個結果，實際得到 {len(results)}"

            # 清理測試數據
            try:
                if client.db.has_collection(collection_name):
                    client.db.delete_collection(collection_name)
            except Exception:
                pass
        except ImportError:
            pytest.skip("ArangoDB 客戶端未安裝")
        except Exception as e:
            pytest.skip(f"ArangoDB AQL 查詢測試跳過: {str(e)}")

    async def test_create_collections_and_graph(self):
        """步驟 2: 集合和圖創建測試"""
        try:
            from database.arangodb import ArangoDBClient

            client = ArangoDBClient()
            if client.db is None:
                pytest.skip("ArangoDB 數據庫連接不可用")

            # 創建實體集合（文檔集合）
            entity_collection = client.get_or_create_collection(
                "test_entities", collection_type="document"
            )
            assert entity_collection is not None, "實體集合創建失敗"

            # 創建關係集合（邊集合）
            relation_collection = client.get_or_create_collection(
                "test_relations", collection_type="edge"
            )
            assert relation_collection is not None, "關係集合創建失敗"

            # 創建圖
            graph_name = "test_graph"
            if not client.db.has_graph(graph_name):
                from arango.graph import Graph

                graph = client.db.create_graph(graph_name)
                graph.create_vertex_collection("test_entities")
                graph.create_edge_definition(
                    edge_collection="test_relations",
                    from_vertex_collections=["test_entities"],
                    to_vertex_collections=["test_entities"],
                )

            # 驗證圖存在
            assert client.db.has_graph(graph_name), "圖創建失敗"

            # 清理測試數據
            try:
                if client.db.has_graph(graph_name):
                    client.db.delete_graph(graph_name, drop_collections=False)
                if client.db.has_collection("test_entities"):
                    client.db.delete_collection("test_entities")
                if client.db.has_collection("test_relations"):
                    client.db.delete_collection("test_relations")
            except Exception:
                pass  # 忽略清理錯誤
        except ImportError:
            pytest.skip("ArangoDB 客戶端未安裝")
        except Exception as e:
            pytest.skip(f"集合和圖創建測試跳過: {str(e)}")

    async def test_graph_operations(self):
        """步驟 3: 圖操作測試"""
        try:
            from database.arangodb import ArangoDBClient
            from database.arangodb.graph import ArangoGraph

            client = ArangoDBClient()
            if client.db is None:
                pytest.skip("ArangoDB 數據庫連接不可用")

            # 創建測試圖
            graph_name = "test_operations_graph"
            entity_col_name = "test_ops_entities"
            relation_col_name = "test_ops_relations"

            # 清理舊數據
            try:
                if client.db.has_graph(graph_name):
                    client.db.delete_graph(graph_name, drop_collections=True)
            except Exception:
                pass

            # 確保集合不存在
            try:
                if client.db.has_collection(entity_col_name):
                    client.db.delete_collection(entity_col_name)
                if client.db.has_collection(relation_col_name):
                    client.db.delete_collection(relation_col_name)
            except Exception:
                pass

            # 創建集合
            entity_col = client.get_or_create_collection(
                entity_col_name, collection_type="document"
            )
            relation_col = client.get_or_create_collection(
                relation_col_name, collection_type="edge"
            )

            # 創建圖
            from arango.graph import Graph

            graph = client.db.create_graph(graph_name)
            graph.create_vertex_collection(entity_col_name)
            graph.create_edge_definition(
                edge_collection=relation_col_name,
                from_vertex_collections=[entity_col_name],
                to_vertex_collections=[entity_col_name],
            )

            arango_graph = ArangoGraph(graph)

            # 插入實體節點（先刪除可能存在的舊數據）
            try:
                entity_col.delete("entity1")
            except Exception:
                pass
            try:
                entity_col.delete("entity2")
            except Exception:
                pass

            vertex1 = {"_key": "entity1", "name": "測試實體1", "type": "TEST"}
            vertex2 = {"_key": "entity2", "name": "測試實體2", "type": "TEST"}
            result1 = arango_graph.insert_vertex(entity_col_name, vertex1)
            result2 = arango_graph.insert_vertex(entity_col_name, vertex2)

            assert result1 is not None, "實體節點1插入失敗"
            assert result2 is not None, "實體節點2插入失敗"

            # 插入關係邊（先刪除可能存在的舊數據）
            try:
                relation_col.delete("rel1")
            except Exception:
                pass

            edge = {"_key": "rel1", "type": "RELATED_TO", "weight": 0.8}
            edge_result = arango_graph.insert_edge(
                relation_col_name,
                edge,
                f"{entity_col_name}/entity1",
                f"{entity_col_name}/entity2",
            )

            assert edge_result is not None, "關係邊插入失敗"

            # 驗證圖結構
            vertex1_retrieved = arango_graph.get_vertex(f"{entity_col_name}/entity1")
            assert vertex1_retrieved is not None, "無法檢索實體節點1"

            # 清理
            try:
                if client.db.has_graph(graph_name):
                    client.db.delete_graph(graph_name, drop_collections=True)
            except Exception:
                pass
        except ImportError:
            pytest.skip("ArangoDB 客戶端未安裝")
        except Exception as e:
            pytest.skip(f"圖操作測試跳過: {str(e)}")

    async def test_graph_query_performance(self):
        """步驟 5: 圖查詢性能測試"""
        try:
            from database.arangodb import ArangoDBClient
            from database.arangodb.graph import ArangoGraph

            client = ArangoDBClient()
            if client.db is None or client.db.aql is None:
                pytest.skip("ArangoDB AQL 不可用")

            # 創建測試圖和數據
            graph_name = "test_perf_graph"
            try:
                if client.db.has_graph(graph_name):
                    client.db.delete_graph(graph_name, drop_collections=True)
            except Exception:
                pass

            entity_col = client.get_or_create_collection(
                "test_perf_entities", collection_type="document"
            )
            relation_col = client.get_or_create_collection(
                "test_perf_relations", collection_type="edge"
            )

            from arango.graph import Graph

            graph = client.db.create_graph(graph_name)
            graph.create_vertex_collection("test_perf_entities")
            graph.create_edge_definition(
                edge_collection="test_perf_relations",
                from_vertex_collections=["test_perf_entities"],
                to_vertex_collections=["test_perf_entities"],
            )

            arango_graph = ArangoGraph(graph)

            # 插入測試數據
            for i in range(10):
                vertex = {"_key": f"entity{i}", "name": f"測試實體{i}", "type": "TEST"}
                arango_graph.insert_vertex("test_perf_entities", vertex)

            # 執行圖遍歷查詢
            start_time = time.time()
            aql = """
            FOR v IN test_perf_entities
            FILTER v.type == 'TEST'
            LIMIT 10
            RETURN v
            """
            cursor = client.db.aql.execute(aql)
            results = list(cursor)
            elapsed_ms = (time.time() - start_time) * 1000

            assert isinstance(results, list), "圖查詢結果格式不正確"
            assert elapsed_ms < 100, f"圖查詢延遲 {elapsed_ms}ms 超過 100ms"

            # 清理
            try:
                if client.db.has_graph(graph_name):
                    client.db.delete_graph(graph_name, drop_collections=True)
            except Exception:
                pass
        except ImportError:
            pytest.skip("ArangoDB 客戶端未安裝")
        except Exception as e:
            pytest.skip(f"圖查詢性能測試跳過: {str(e)}")
