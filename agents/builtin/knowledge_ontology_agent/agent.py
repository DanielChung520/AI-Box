# 代碼功能說明: Knowledge Ontology Agent 實現
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Knowledge Ontology Agent 實現 - 知識圖譜和 Ontology 專屬服務 Agent"""

import logging
from typing import Any, Dict, Optional

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)
from database.arangodb import ArangoDBClient
from genai.api.models.triple_models import Triple
from genai.api.services.kg_builder_service import KGBuilderService

from .graphrag import GraphRAGService
from .models import (
    GraphRAGQueryRequest,
    GraphRAGQueryResponse,
    KnowledgeOntologyAgentRequest,
    KnowledgeOntologyAgentResponse,
)

logger = logging.getLogger(__name__)


class KnowledgeOntologyAgent(AgentServiceProtocol):
    """Knowledge Ontology Agent - 知識圖譜和 Ontology 專屬服務 Agent

    提供知識圖譜相關服務：
    - 從三元組構建知識圖譜（build_from_triples）
    - 查詢三元組（list_triples）
    - 獲取實體（get_entity）
    - 獲取實體鄰居（get_neighbors）
    - 獲取實體子圖（get_subgraph）
    - GraphRAG 查詢（graphrag_query）
    """

    def __init__(
        self,
        kg_service: Optional[KGBuilderService] = None,
        graphrag_service: Optional[GraphRAGService] = None,
        client: Optional[ArangoDBClient] = None,
    ):
        """
        初始化 Knowledge Ontology Agent

        Args:
            kg_service: 知識圖譜構建服務（可選，如果不提供則自動創建）
            graphrag_service: GraphRAG 服務（可選，如果不提供則自動創建）
            client: ArangoDB 客戶端（可選，如果不提供則自動創建）
        """
        self._kg_service = kg_service or KGBuilderService(client=client)
        self._graphrag_service = graphrag_service or GraphRAGService(
            kg_service=self._kg_service, client=client
        )
        self._logger = logger

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        執行知識圖譜任務

        Args:
            request: Agent 服務請求

        Returns:
            Agent 服務響應
        """
        try:
            # 解析請求數據
            task_data = request.task_data
            ko_request = KnowledgeOntologyAgentRequest(**task_data)
            action = ko_request.action

            # 根據操作類型執行相應功能
            if action == "build_from_triples":
                result = await self._handle_build_from_triples(ko_request)
            elif action == "list_triples":
                result = await self._handle_list_triples(ko_request)
            elif action == "get_entity":
                result = await self._handle_get_entity(ko_request)
            elif action == "get_neighbors":
                result = await self._handle_get_neighbors(ko_request)
            elif action == "get_subgraph":
                result = await self._handle_get_subgraph(ko_request)
            elif action == "graphrag_query":
                result = await self._handle_graphrag_query(ko_request)
            else:
                result = KnowledgeOntologyAgentResponse(
                    success=False,
                    action=action,
                    error=f"Unknown action: {action}",
                )

            # 構建響應
            return AgentServiceResponse(
                task_id=request.task_id,
                status="completed" if result.success else "failed",
                result=result.model_dump(),
                error=result.error,
                metadata=request.metadata,
            )

        except Exception as e:
            self._logger.error(f"Knowledge Ontology Agent execution failed: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,
                error=str(e),
                metadata=request.metadata,
            )

    async def _handle_build_from_triples(
        self, request: KnowledgeOntologyAgentRequest
    ) -> KnowledgeOntologyAgentResponse:
        """處理從三元組構建知識圖譜請求"""
        if not request.triples:
            return KnowledgeOntologyAgentResponse(
                success=False,
                action="build_from_triples",
                error="triples is required for build_from_triples action",
            )

        try:
            # 轉換三元組數據
            triples = [Triple(**t) for t in request.triples]

            # 調用 KGBuilderService
            result = await self._kg_service.build_from_triples(
                triples=triples,
                file_id=request.file_id,
                user_id=request.user_id,
                min_confidence=request.min_confidence or 0.5,
                core_node_threshold=request.core_node_threshold or 0.9,
                enable_judgment=request.enable_judgment
                if request.enable_judgment is not None
                else True,
            )

            return KnowledgeOntologyAgentResponse(
                success=True,
                action="build_from_triples",
                result=result,
            )

        except Exception as e:
            self._logger.error(f"Build from triples failed: {e}")
            return KnowledgeOntologyAgentResponse(
                success=False,
                action="build_from_triples",
                error=str(e),
            )

    async def _handle_list_triples(
        self, request: KnowledgeOntologyAgentRequest
    ) -> KnowledgeOntologyAgentResponse:
        """處理查詢三元組請求"""
        if not request.file_id:
            return KnowledgeOntologyAgentResponse(
                success=False,
                action="list_triples",
                error="file_id is required for list_triples action",
            )

        try:
            # 調用 KGBuilderService
            result = self._kg_service.list_triples_by_file_id(
                file_id=request.file_id,
                limit=request.limit or 100,
                offset=request.offset or 0,
            )

            return KnowledgeOntologyAgentResponse(
                success=True,
                action="list_triples",
                result=result,
            )

        except Exception as e:
            self._logger.error(f"List triples failed: {e}")
            return KnowledgeOntologyAgentResponse(
                success=False,
                action="list_triples",
                error=str(e),
            )

    async def _handle_get_entity(
        self, request: KnowledgeOntologyAgentRequest
    ) -> KnowledgeOntologyAgentResponse:
        """處理獲取實體請求"""
        if not request.entity_id:
            return KnowledgeOntologyAgentResponse(
                success=False,
                action="get_entity",
                error="entity_id is required for get_entity action",
            )

        try:
            # 調用 KGBuilderService
            entity = self._kg_service.get_entity(request.entity_id)

            if not entity:
                return KnowledgeOntologyAgentResponse(
                    success=False,
                    action="get_entity",
                    error=f"Entity not found: {request.entity_id}",
                )

            return KnowledgeOntologyAgentResponse(
                success=True,
                action="get_entity",
                result={"entity": entity},
            )

        except Exception as e:
            self._logger.error(f"Get entity failed: {e}")
            return KnowledgeOntologyAgentResponse(
                success=False,
                action="get_entity",
                error=str(e),
            )

    async def _handle_get_neighbors(
        self, request: KnowledgeOntologyAgentRequest
    ) -> KnowledgeOntologyAgentResponse:
        """處理獲取實體鄰居請求"""
        if not request.entity_id:
            return KnowledgeOntologyAgentResponse(
                success=False,
                action="get_neighbors",
                error="entity_id is required for get_neighbors action",
            )

        try:
            # 調用 KGBuilderService
            neighbors = self._kg_service.get_entity_neighbors(
                entity_id=request.entity_id,
                relation_types=request.relation_types,
                limit=request.limit or 20,
            )

            return KnowledgeOntologyAgentResponse(
                success=True,
                action="get_neighbors",
                result={"neighbors": neighbors},
            )

        except Exception as e:
            self._logger.error(f"Get neighbors failed: {e}")
            return KnowledgeOntologyAgentResponse(
                success=False,
                action="get_neighbors",
                error=str(e),
            )

    async def _handle_get_subgraph(
        self, request: KnowledgeOntologyAgentRequest
    ) -> KnowledgeOntologyAgentResponse:
        """處理獲取實體子圖請求"""
        if not request.entity_id:
            return KnowledgeOntologyAgentResponse(
                success=False,
                action="get_subgraph",
                error="entity_id is required for get_subgraph action",
            )

        try:
            # 調用 KGBuilderService
            subgraph = self._kg_service.get_entity_subgraph(
                entity_id=request.entity_id,
                max_depth=request.max_depth or 2,
                limit=request.limit or 50,
            )

            return KnowledgeOntologyAgentResponse(
                success=True,
                action="get_subgraph",
                result={"subgraph": subgraph},
            )

        except Exception as e:
            self._logger.error(f"Get subgraph failed: {e}")
            return KnowledgeOntologyAgentResponse(
                success=False,
                action="get_subgraph",
                error=str(e),
            )

    async def _handle_graphrag_query(
        self, request: KnowledgeOntologyAgentRequest
    ) -> KnowledgeOntologyAgentResponse:
        """處理 GraphRAG 查詢請求"""
        if not request.query_type:
            return KnowledgeOntologyAgentResponse(
                success=False,
                action="graphrag_query",
                error="query_type is required for graphrag_query action",
            )

        try:
            # 構建 GraphRAG 查詢請求
            graphrag_request = GraphRAGQueryRequest(
                query_type=request.query_type,
                entity_name=request.query_params.get("entity_name")
                if request.query_params
                else None,
                from_entity=request.query_params.get("from_entity")
                if request.query_params
                else None,
                to_entity=request.query_params.get("to_entity") if request.query_params else None,
                center_entity=request.query_params.get("center_entity")
                if request.query_params
                else None,
                max_depth=request.query_params.get("max_depth", 2) if request.query_params else 2,
                limit=request.query_params.get("limit", 50) if request.query_params else 50,
                relation_types=request.query_params.get("relation_types")
                if request.query_params
                else None,
            )

            # 根據查詢類型執行相應功能
            if graphrag_request.query_type == "entity_retrieval":
                if not graphrag_request.entity_name:
                    return KnowledgeOntologyAgentResponse(
                        success=False,
                        action="graphrag_query",
                        error="entity_name is required for entity_retrieval query",
                    )
                result = await self._graphrag_service.entity_retrieval(
                    entity_name=graphrag_request.entity_name,
                    limit=graphrag_request.limit,
                )
            elif graphrag_request.query_type == "relation_path":
                if not graphrag_request.from_entity or not graphrag_request.to_entity:
                    return KnowledgeOntologyAgentResponse(
                        success=False,
                        action="graphrag_query",
                        error="from_entity and to_entity are required for relation_path query",
                    )
                result = await self._graphrag_service.relation_path_query(
                    from_entity=graphrag_request.from_entity,
                    to_entity=graphrag_request.to_entity,
                    relation_types=graphrag_request.relation_types,
                    max_depth=graphrag_request.max_depth,
                )
            elif graphrag_request.query_type == "subgraph_extraction":
                if not graphrag_request.center_entity:
                    return KnowledgeOntologyAgentResponse(
                        success=False,
                        action="graphrag_query",
                        error="center_entity is required for subgraph_extraction query",
                    )
                result = await self._graphrag_service.subgraph_extraction(
                    center_entity=graphrag_request.center_entity,
                    max_depth=graphrag_request.max_depth,
                    limit=graphrag_request.limit,
                    relation_types=graphrag_request.relation_types,
                )
            else:
                return KnowledgeOntologyAgentResponse(
                    success=False,
                    action="graphrag_query",
                    error=f"Unknown query_type: {graphrag_request.query_type}",
                )

            # 構建 GraphRAG 響應
            graphrag_response = GraphRAGQueryResponse(
                query_type=graphrag_request.query_type,
                entities=result.get("entities", []),
                relations=result.get("relations", []),
                paths=result.get("paths"),
                subgraph=result.get("subgraph"),
                metadata=result.get("metadata", {}),
            )

            return KnowledgeOntologyAgentResponse(
                success=True,
                action="graphrag_query",
                result=graphrag_response.model_dump(),
            )

        except Exception as e:
            self._logger.error(f"GraphRAG query failed: {e}")
            return KnowledgeOntologyAgentResponse(
                success=False,
                action="graphrag_query",
                error=str(e),
            )

    async def health_check(self) -> AgentServiceStatus:
        """
        健康檢查

        Returns:
            服務狀態
        """
        try:
            # 檢查 KGBuilderService 是否可用
            if self._kg_service is None:
                return AgentServiceStatus.UNAVAILABLE

            # 檢查 ArangoDB 連接
            if self._kg_service.client is None or self._kg_service.client.db is None:
                return AgentServiceStatus.UNAVAILABLE

            # 嘗試查詢實體列表（簡單的健康檢查）
            try:
                self._kg_service.list_entities(limit=1, offset=0)
                return AgentServiceStatus.AVAILABLE
            except Exception:
                return AgentServiceStatus.ERROR

        except Exception:
            return AgentServiceStatus.UNAVAILABLE

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        獲取服務能力

        Returns:
            服務能力描述
        """
        return {
            "agent_id": "knowledge_ontology_agent",
            "agent_type": "dedicated_service",
            "name": "Knowledge Ontology Agent",
            "description": "知識圖譜和 Ontology 專屬服務 Agent，提供知識圖譜構建、查詢和 GraphRAG 功能",
            "capabilities": [
                "build_from_triples",  # 從三元組構建知識圖譜
                "list_triples",  # 查詢三元組
                "get_entity",  # 獲取實體
                "get_neighbors",  # 獲取實體鄰居
                "get_subgraph",  # 獲取實體子圖
                "graphrag_query",  # GraphRAG 查詢
            ],
            "graphrag_features": [
                "entity_retrieval",  # 實體檢索
                "relation_path",  # 關係路徑查詢
                "subgraph_extraction",  # 子圖提取
                "entity_similarity",  # 實體相似度計算
                "relation_strength",  # 關係強度評估
                "path_analysis",  # 路徑分析
            ],
        }
