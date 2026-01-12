# 代碼功能說明: Knowledge Ontology Agent 單元測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Knowledge Ontology Agent 單元測試

測試 Knowledge Ontology Agent 的核心功能：知識圖譜構建、查詢和 GraphRAG 功能。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.builtin.knowledge_ontology_agent.agent import KnowledgeOntologyAgent
from agents.services.protocol.base import AgentServiceRequest, AgentServiceStatus


class TestKnowledgeOntologyAgent:
    """Knowledge Ontology Agent 測試類"""

    @pytest.fixture
    def kg_agent(self):
        """創建 KnowledgeOntologyAgent 實例"""
        with patch("agents.builtin.knowledge_ontology_agent.agent.KGBuilderService") as mock_kg:
            mock_service = MagicMock()
            mock_kg.return_value = mock_service
            with patch(
                "agents.builtin.knowledge_ontology_agent.agent.GraphRAGService"
            ) as mock_graphrag:
                mock_graphrag_service = MagicMock()
                mock_graphrag.return_value = mock_graphrag_service
                return KnowledgeOntologyAgent(
                    kg_service=mock_service, graphrag_service=mock_graphrag_service
                )

    @pytest.fixture
    def sample_triples(self):
        """創建示例三元組"""
        return [
            {
                "subject": {"text": "實體1", "type": "Person", "start": 0, "end": 3},
                "object": {"text": "實體2", "type": "Organization", "start": 5, "end": 8},
                "relation": {"type": "works_for"},
                "confidence": 0.9,
                "context": "測試上下文",
            }
        ]

    @pytest.mark.asyncio
    async def test_execute_build_from_triples(self, kg_agent, sample_triples):
        """測試從三元組構建知識圖譜"""
        request = AgentServiceRequest(
            task_id="test-task-001",
            task_type="knowledge_ontology",
            task_data={
                "action": "build_from_triples",
                "triples": sample_triples,
                "file_id": "test-file-001",
            },
        )

        # Mock KGBuilderService 的 build_from_triples 方法
        kg_agent._kg_service.build_from_triples = AsyncMock(
            return_value={
                "entities_created": 2,
                "relations_created": 1,
                "total_triples": 1,
            }
        )

        response = await kg_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True
        assert response.result["action"] == "build_from_triples"

    @pytest.mark.asyncio
    async def test_execute_list_triples(self, kg_agent):
        """測試查詢三元組"""
        request = AgentServiceRequest(
            task_id="test-task-002",
            task_type="knowledge_ontology",
            task_data={
                "action": "list_triples",
                "file_id": "test-file-001",
                "limit": 10,
            },
        )

        # Mock KGBuilderService 的 list_triples_by_file_id 方法
        kg_agent._kg_service.list_triples_by_file_id = MagicMock(
            return_value={"total": 5, "triples": []}
        )

        response = await kg_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True
        assert response.result["action"] == "list_triples"

    @pytest.mark.asyncio
    async def test_execute_get_entity(self, kg_agent):
        """測試獲取實體"""
        request = AgentServiceRequest(
            task_id="test-task-003",
            task_type="knowledge_ontology",
            task_data={
                "action": "get_entity",
                "entity_id": "entities/test-entity-001",
            },
        )

        # Mock KGBuilderService 的 get_entity 方法
        kg_agent._kg_service.get_entity = MagicMock(
            return_value={"_key": "test-entity-001", "name": "測試實體", "type": "Person"}
        )

        response = await kg_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True
        assert response.result["action"] == "get_entity"

    @pytest.mark.asyncio
    async def test_execute_get_neighbors(self, kg_agent):
        """測試獲取實體鄰居"""
        request = AgentServiceRequest(
            task_id="test-task-004",
            task_type="knowledge_ontology",
            task_data={
                "action": "get_neighbors",
                "entity_id": "entities/test-entity-001",
                "limit": 10,
            },
        )

        # Mock KGBuilderService 的 get_entity_neighbors 方法
        kg_agent._kg_service.get_entity_neighbors = MagicMock(return_value=[])

        response = await kg_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True
        assert response.result["action"] == "get_neighbors"

    @pytest.mark.asyncio
    async def test_execute_get_subgraph(self, kg_agent):
        """測試獲取實體子圖"""
        request = AgentServiceRequest(
            task_id="test-task-005",
            task_type="knowledge_ontology",
            task_data={
                "action": "get_subgraph",
                "entity_id": "entities/test-entity-001",
                "max_depth": 2,
            },
        )

        # Mock KGBuilderService 的 get_entity_subgraph 方法
        kg_agent._kg_service.get_entity_subgraph = MagicMock(return_value=[])

        response = await kg_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True
        assert response.result["action"] == "get_subgraph"

    @pytest.mark.asyncio
    async def test_execute_graphrag_query_entity_retrieval(self, kg_agent):
        """測試 GraphRAG 查詢（實體檢索）"""
        request = AgentServiceRequest(
            task_id="test-task-006",
            task_type="knowledge_ontology",
            task_data={
                "action": "graphrag_query",
                "query_type": "entity_retrieval",
                "query_params": {"entity_name": "測試實體", "limit": 10},
            },
        )

        # Mock GraphRAGService 的 entity_retrieval 方法
        kg_agent._graphrag_service.entity_retrieval = AsyncMock(
            return_value={"entities": [], "total": 0}
        )

        response = await kg_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True
        assert response.result["action"] == "graphrag_query"

    @pytest.mark.asyncio
    async def test_execute_graphrag_query_relation_path(self, kg_agent):
        """測試 GraphRAG 查詢（關係路徑）"""
        request = AgentServiceRequest(
            task_id="test-task-007",
            task_type="knowledge_ontology",
            task_data={
                "action": "graphrag_query",
                "query_type": "relation_path",
                "query_params": {
                    "from_entity": "實體1",
                    "to_entity": "實體2",
                    "max_depth": 3,
                },
            },
        )

        # Mock GraphRAGService 的 relation_path_query 方法
        kg_agent._graphrag_service.relation_path_query = AsyncMock(
            return_value={"paths": [], "total": 0}
        )

        response = await kg_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_graphrag_query_subgraph_extraction(self, kg_agent):
        """測試 GraphRAG 查詢（子圖提取）"""
        request = AgentServiceRequest(
            task_id="test-task-008",
            task_type="knowledge_ontology",
            task_data={
                "action": "graphrag_query",
                "query_type": "subgraph_extraction",
                "query_params": {"center_entity": "實體1", "max_depth": 2},
            },
        )

        # Mock GraphRAGService 的 subgraph_extraction 方法
        kg_agent._graphrag_service.subgraph_extraction = AsyncMock(
            return_value={"subgraph": [], "entities": [], "relations": []}
        )

        response = await kg_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self, kg_agent):
        """測試未知操作"""
        request = AgentServiceRequest(
            task_id="test-task-009",
            task_type="knowledge_ontology",
            task_data={"action": "unknown_action"},
        )

        response = await kg_agent.execute(request)

        assert response.status == "failed"
        assert response.result["success"] is False
        assert "Unknown action" in response.result["error"]

    @pytest.mark.asyncio
    async def test_health_check(self, kg_agent):
        """測試健康檢查"""
        # Mock list_entities
        kg_agent._kg_service.list_entities = MagicMock(return_value=[])

        status = await kg_agent.health_check()
        assert status == AgentServiceStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_get_capabilities(self, kg_agent):
        """測試獲取服務能力"""
        capabilities = await kg_agent.get_capabilities()

        assert capabilities["agent_id"] == "knowledge_ontology_agent"
        assert capabilities["agent_type"] == "dedicated_service"
        assert "build_from_triples" in capabilities["capabilities"]
        assert "graphrag_query" in capabilities["capabilities"]


class TestGraphRAGService:
    """GraphRAG Service 測試類"""

    @pytest.fixture
    def graphrag_service(self):
        """創建 GraphRAGService 實例"""
        with patch("agents.builtin.knowledge_ontology_agent.graphrag.KGBuilderService") as mock_kg:
            mock_service = MagicMock()
            mock_kg.return_value = mock_service
            from agents.builtin.knowledge_ontology_agent.graphrag import GraphRAGService

            return GraphRAGService(kg_service=mock_service)

    @pytest.mark.asyncio
    async def test_entity_retrieval(self, graphrag_service):
        """測試實體檢索"""
        # Mock list_entities
        graphrag_service._kg_service.list_entities = MagicMock(
            return_value=[
                {"_key": "entity-1", "name": "測試實體", "type": "Person"},
                {"_key": "entity-2", "name": "其他實體", "type": "Organization"},
            ]
        )

        result = await graphrag_service.entity_retrieval("測試", limit=10)

        assert "entities" in result
        assert len(result["entities"]) > 0

    @pytest.mark.asyncio
    async def test_relation_path_query(self, graphrag_service):
        """測試關係路徑查詢"""
        # Mock list_entities 和 AQL 執行
        graphrag_service._kg_service.list_entities = MagicMock(
            return_value=[
                {"_key": "entity-1", "_id": "entities/entity-1", "name": "實體1"},
                {"_key": "entity-2", "_id": "entities/entity-2", "name": "實體2"},
            ]
        )

        # Mock AQL 執行
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter([{"path": ["實體1", "實體2"], "length": 1}]))
        graphrag_service._kg_service.client.db.aql.execute = MagicMock(return_value=mock_cursor)

        result = await graphrag_service.relation_path_query("實體1", "實體2", max_depth=3)

        assert "paths" in result
        assert result["from_entity"] == "實體1"
        assert result["to_entity"] == "實體2"

    @pytest.mark.asyncio
    async def test_subgraph_extraction(self, graphrag_service):
        """測試子圖提取"""
        # Mock list_entities 和 get_entity_subgraph
        graphrag_service._kg_service.list_entities = MagicMock(
            return_value=[{"_key": "entity-1", "_id": "entities/entity-1", "name": "中心實體"}]
        )
        graphrag_service._kg_service.get_entity_subgraph = MagicMock(return_value=[])

        result = await graphrag_service.subgraph_extraction("中心實體", max_depth=2, limit=50)

        assert "subgraph" in result
        assert result["center_entity"] == "中心實體"

    def test_calculate_entity_similarity(self, graphrag_service):
        """測試實體相似度計算"""
        entity1 = {"name": "測試實體"}
        entity2 = {"name": "測試實體"}
        entity3 = {"name": "其他實體"}

        similarity1 = graphrag_service.calculate_entity_similarity(entity1, entity2)
        similarity2 = graphrag_service.calculate_entity_similarity(entity1, entity3)

        assert similarity1 == 1.0
        assert similarity2 < similarity1

    def test_evaluate_relation_strength(self, graphrag_service):
        """測試關係強度評估"""
        relation1 = {"confidence": 0.9, "weight": 0.8}
        relation2 = {"confidence": 0.5, "weight": 0.4}

        strength1 = graphrag_service.evaluate_relation_strength(relation1)
        strength2 = graphrag_service.evaluate_relation_strength(relation2)

        assert strength1 > strength2
        assert 0.0 <= strength1 <= 1.0
        assert 0.0 <= strength2 <= 1.0

    def test_analyze_graph_paths(self, graphrag_service):
        """測試圖譜路徑分析"""
        paths = [["實體1", "實體2"], ["實體1", "實體3", "實體2"]]

        analysis = graphrag_service.analyze_graph_paths(paths, "實體1")

        assert analysis["total_paths"] == 2
        assert analysis["avg_path_length"] > 0
        assert analysis["max_path_length"] >= analysis["min_path_length"]
