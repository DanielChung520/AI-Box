# 代碼功能說明: AAM 混合 RAG 服務
# 創建日期: 2025-11-28 21:54 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-05

"""AAM 混合 RAG 服務 - 實現向量檢索 + 圖檢索混合 RAG"""

from __future__ import annotations

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

from agents.infra.memory.aam.aam_core import AAMManager
from agents.infra.memory.aam.models import Memory, MemoryPriority, MemoryType
from agents.infra.memory.aam.realtime_retrieval import RealtimeRetrievalService
from genai.api.services.kg_builder_service import KGBuilderService
from genai.api.services.ner_service import NERService
from genai.workflows.rag.hybrid_rag_config import HybridRAGConfigService

logger = structlog.get_logger(__name__)


class RetrievalStrategy(str, Enum):
    """檢索策略枚舉"""

    VECTOR_FIRST = "vector_first"  # 向量優先
    GRAPH_FIRST = "graph_first"  # 圖優先
    HYBRID = "hybrid"  # 混合


class HybridRAGService:
    """混合 RAG 服務 - 整合向量檢索和圖檢索"""

    def __init__(
        self,
        aam_manager: AAMManager,
        retrieval_service: Optional[RealtimeRetrievalService] = None,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        vector_weight: Optional[float] = None,
        graph_weight: Optional[float] = None,
        max_workers: int = 4,
        config_service: Optional[HybridRAGConfigService] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """
        初始化混合 RAG 服務

        Args:
            aam_manager: AAM 管理器
            retrieval_service: 實時檢索服務
            strategy: 檢索策略
            vector_weight: 向量檢索權重（如果為 None，則從配置讀取）
            graph_weight: 圖檢索權重（如果為 None，則從配置讀取）
            max_workers: 並行檢索的最大工作線程數
            config_service: HybridRAGConfigService 實例（可選）
            tenant_id: 租戶 ID（用於多租戶配置）
            user_id: 用戶 ID（用於多租戶配置）
        """
        self.aam_manager = aam_manager
        self.retrieval_service = retrieval_service or RealtimeRetrievalService(aam_manager)
        self.strategy = strategy
        self.max_workers = max_workers
        self.logger = logger.bind(component="hybrid_rag")

        # 初始化配置服務
        self.config_service = config_service or HybridRAGConfigService()
        self.tenant_id = tenant_id
        self.user_id = user_id

        # 如果提供了權重，使用提供的權重；否則使用默認值（將在首次檢索時從配置讀取）
        if vector_weight is not None and graph_weight is not None:
            self.vector_weight = vector_weight
            self.graph_weight = graph_weight
            self._use_config_weights = False
        else:
            # 使用默認值，將在首次檢索時從配置讀取
            self.vector_weight = 0.6
            self.graph_weight = 0.4
            self._use_config_weights = True

        # 初始化圖譜檢索相關服務（懶加載）
        self._ner_service: Optional[NERService] = None
        self._kg_service: Optional[KGBuilderService] = None

        # 結果緩存
        self._cache: Dict[str, tuple[float, List[Dict[str, Any]]]] = {}

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        strategy: Optional[RetrievalStrategy] = None,
        min_relevance: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        執行混合 RAG 檢索

        Args:
            query: 查詢文本
            top_k: 返回結果數量
            strategy: 檢索策略（如果為 None 則使用默認策略）
            min_relevance: 最小相關度閾值

        Returns:
            RAG 結果列表，格式為 [{"content": "...", "metadata": {...}, "score": ...}]
        """
        start_time = time.time()
        strategy = strategy or self.strategy

        # 如果使用配置權重，從配置讀取權重
        if self._use_config_weights:
            weights = self.config_service.get_weights(
                query=query, tenant_id=self.tenant_id, user_id=self.user_id
            )
            self.vector_weight = weights["vector_weight"]
            self.graph_weight = weights["graph_weight"]
            self.logger.debug(
                "Weights loaded from config",
                vector_weight=self.vector_weight,
                graph_weight=self.graph_weight,
                query=query[:50],
            )

        try:
            # 根據策略執行檢索
            if strategy == RetrievalStrategy.VECTOR_FIRST:
                results = self._vector_first_retrieval(query, top_k, min_relevance)
            elif strategy == RetrievalStrategy.GRAPH_FIRST:
                results = self._graph_first_retrieval(query, top_k, min_relevance)
            else:  # HYBRID
                results = self._hybrid_retrieval(query, top_k, min_relevance)

            # 格式化結果供 LLM 使用
            formatted_results = self._format_for_llm(results)

            elapsed = (time.time() - start_time) * 1000
            self.logger.info(
                "Hybrid RAG retrieval completed",
                query=query[:50],
                count=len(formatted_results),
                strategy=strategy.value,
                elapsed_ms=elapsed,
            )

            return formatted_results
        except Exception as e:
            self.logger.error("Failed to perform hybrid RAG retrieval", error=str(e))
            return []

    def _vector_first_retrieval(self, query: str, top_k: int, min_relevance: float) -> List[Memory]:
        """向量優先檢索"""
        # 先執行向量檢索
        vector_results = self.retrieval_service.retrieve(
            query, limit=top_k, min_relevance=min_relevance
        )

        # 如果結果不足，再執行圖檢索補充
        if len(vector_results) < top_k:
            graph_results = self._graph_retrieval(query, top_k - len(vector_results))
            vector_results.extend(graph_results)

        return vector_results[:top_k]

    def _graph_first_retrieval(self, query: str, top_k: int, min_relevance: float) -> List[Memory]:
        """圖優先檢索"""
        # 先執行圖檢索
        graph_results = self._graph_retrieval(query, top_k)

        # 如果結果不足，再執行向量檢索補充
        if len(graph_results) < top_k:
            vector_results = self.retrieval_service.retrieve(
                query, limit=top_k - len(graph_results), min_relevance=min_relevance
            )
            graph_results.extend(vector_results)

        return graph_results[:top_k]

    def _hybrid_retrieval(self, query: str, top_k: int, min_relevance: float) -> List[Memory]:
        """混合檢索（並行執行向量和圖檢索，然後融合結果）"""
        results: List[Memory] = []

        # 並行執行向量和圖檢索
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交向量檢索任務
            vector_future = executor.submit(
                self.retrieval_service.retrieve,
                query,
                limit=top_k * 2,
                min_relevance=min_relevance,
            )

            # 提交圖檢索任務
            graph_future = executor.submit(self._graph_retrieval, query, top_k * 2)

            # 收集結果
            vector_results = vector_future.result(timeout=5.0)
            graph_results = graph_future.result(timeout=5.0)

        # 融合結果（加權合併、去重、排序）
        results = self._merge_results(vector_results, graph_results, top_k)

        return results

    def _graph_retrieval(self, query: str, limit: int) -> List[Memory]:
        """圖檢索（基於 ArangoDB 知識圖譜）"""
        try:
            # 1. 實體識別：使用 NER 服務從查詢中提取實體
            entities = self._extract_entities_from_query(query)

            if not entities:
                self.logger.debug("No entities found in query", query=query[:50])
                return []

            # 2. 實體匹配：在 ArangoDB 中查找匹配的實體
            matched_entities = self._find_matching_entities(entities, limit=limit * 2)

            if not matched_entities:
                self.logger.debug("No matching entities found in graph", query=query[:50])
                return []

            # 3. 圖遍歷：獲取實體的鄰居節點和子圖
            graph_results = []
            for entity in matched_entities[:limit]:
                # 構建正確的 entity_id 格式：entities/{_key}
                entity_key = entity.get("_key")
                entity_id_from_doc = entity.get("_id", "")

                if entity_id_from_doc:
                    # 如果已經有 _id，直接使用
                    entity_id = entity_id_from_doc
                elif entity_key:
                    # 如果只有 _key，構建完整的 entity_id
                    entity_id = f"entities/{entity_key}"
                else:
                    self.logger.debug(
                        "Entity missing _key and _id, skipping",
                        entity=entity.get("name", "unknown"),
                    )
                    continue

                self.logger.debug(
                    "Getting neighbors and subgraph for entity",
                    entity_id=entity_id,
                    entity_name=entity.get("name", "unknown"),
                )

                # 獲取鄰居節點（1度關係）
                try:
                    neighbors = self._get_kg_service().get_entity_neighbors(
                        entity_id=entity_id, limit=min(limit, 10)
                    )
                    self.logger.debug(
                        "Got neighbors for entity",
                        entity_id=entity_id,
                        neighbors_count=len(neighbors),
                    )
                    graph_results.extend(neighbors)

                    # 獲取子圖（N度關係，可選）
                    if len(graph_results) < limit:
                        subgraph = self._get_kg_service().get_entity_subgraph(
                            entity_id=entity_id,
                            max_depth=2,
                            limit=min(limit - len(graph_results), 20),
                        )
                        self.logger.debug(
                            "Got subgraph for entity",
                            entity_id=entity_id,
                            subgraph_count=len(subgraph),
                        )
                        graph_results.extend(subgraph)
                except Exception as e:
                    self.logger.warning(
                        "Failed to get entity neighbors/subgraph",
                        entity_id=entity_id,
                        error=str(e),
                    )
                    continue

            # 4. 結果格式化：將圖譜數據轉換為 Memory 格式
            memories = self._format_graph_results(graph_results, query, limit=limit)

            self.logger.info(
                "Graph retrieval completed",
                query=query[:50],
                entities_extracted=len(entities),
                matched_entities=len(matched_entities),
                graph_results=len(graph_results),
                memories=len(memories),
            )

            return memories

        except Exception as e:
            self.logger.error("Graph retrieval failed", query=query[:50], error=str(e))
            return []

    def _get_ner_service(self) -> NERService:
        """獲取 NER 服務實例（懶加載）"""
        if self._ner_service is None:
            self._ner_service = NERService()
        return self._ner_service

    def _get_kg_service(self) -> KGBuilderService:
        """獲取圖譜構建服務實例（懶加載）"""
        if self._kg_service is None:
            self._kg_service = KGBuilderService()
        return self._kg_service

    def _extract_entities_from_query(self, query: str) -> List[Any]:
        """從查詢中提取實體"""
        try:
            # 使用異步 NER 服務（需要轉換為同步）
            ner_service = self._get_ner_service()

            # 嘗試獲取當前事件循環
            try:
                asyncio.get_running_loop()
                # 如果事件循環正在運行，創建新線程執行異步任務
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, ner_service.extract_entities(query, ontology_rules=None)
                    )
                    entities = future.result(timeout=5.0)
            except RuntimeError:
                # 沒有運行中的事件循環，直接使用 asyncio.run
                entities = asyncio.run(ner_service.extract_entities(query, ontology_rules=None))

            return entities or []

        except Exception as e:
            self.logger.warning(
                "Failed to extract entities from query", query=query[:50], error=str(e)
            )
            return []

    def _find_matching_entities(self, entities: List[Any], limit: int = 20) -> List[Dict[str, Any]]:
        """在 ArangoDB 中查找匹配的實體（混合策略）"""
        matched_entities = []
        kg_service = self._get_kg_service()

        if kg_service.client is None or kg_service.client.db is None:
            self.logger.warning("ArangoDB client is not initialized")
            return []

        self.logger.debug(
            "Starting entity matching",
            entity_count=len(entities),
            limit=limit,
        )

        try:
            for i, entity in enumerate(entities):
                entity_text = entity.text if hasattr(entity, "text") else str(entity)
                entity_type = entity.label if hasattr(entity, "label") else None

                self.logger.debug(
                    "Processing entity",
                    entity_index=i + 1,
                    entity_text=entity_text,
                    entity_type=entity_type,
                    current_matches=len(matched_entities),
                )

                # 策略 1: 文字比對（精確匹配、模糊匹配）
                text_match_results = self._query_entities_by_text_match(
                    kg_service, entity_text, entity_type, limit
                )

                # 如果沒有結果且提供了類型，嘗試忽略類型匹配
                if len(text_match_results) == 0 and entity_type:
                    self.logger.debug(
                        "No results with type filter, trying without type",
                        entity_text=entity_text,
                        entity_type=entity_type,
                    )
                    text_match_results = self._query_entities_by_text_match(
                        kg_service, entity_text, None, limit
                    )

                self.logger.debug(
                    "Text match results",
                    entity_text=entity_text,
                    results_count=len(text_match_results),
                    matched_entity_names=[r.get("name") for r in text_match_results[:5]],
                )
                matched_entities.extend(text_match_results)

                # 如果結果不足，使用策略 2: 關鍵詞匹配
                if len(matched_entities) < limit:
                    keywords = self._extract_keywords(entity_text)
                    self.logger.debug(
                        "Extracted keywords",
                        entity_text=entity_text,
                        keywords=keywords,
                    )
                    keyword_results = self._query_entities_by_keywords(
                        kg_service, keywords, entity_type, limit - len(matched_entities)
                    )

                    # 如果關鍵詞匹配沒有結果且提供了類型，嘗試忽略類型
                    if len(keyword_results) == 0 and entity_type:
                        self.logger.debug(
                            "No keyword results with type filter, trying without type",
                            entity_text=entity_text,
                            entity_type=entity_type,
                        )
                        keyword_results = self._query_entities_by_keywords(
                            kg_service, keywords, None, limit - len(matched_entities)
                        )
                    self.logger.debug(
                        "Keyword match results",
                        entity_text=entity_text,
                        keywords=keywords,
                        results_count=len(keyword_results),
                        matched_entity_names=[r.get("name") for r in keyword_results[:5]],
                    )
                    # 去重
                    existing_keys = {r.get("_key") for r in matched_entities if r.get("_key")}
                    for result in keyword_results:
                        if result.get("_key") not in existing_keys:
                            matched_entities.append(result)
                            existing_keys.add(result.get("_key"))
                            if len(matched_entities) >= limit:
                                break

                # 策略 3: 語義匹配（未來實現）
                # if len(matched_entities) < limit:
                #     semantic_results = self._query_entities_by_semantic_match(
                #         kg_service, entity_text, entity_type, limit - len(matched_entities)
                #     )
                #     matched_entities.extend(semantic_results)

                if len(matched_entities) >= limit:
                    break

            self.logger.debug(
                "Entity matching completed",
                total_entities_processed=len(entities),
                total_matches=len(matched_entities),
                final_matches=len(matched_entities[:limit]),
            )

        except Exception as e:
            self.logger.error("Failed to find matching entities", error=str(e))

        return matched_entities[:limit]

    def _query_entities_by_text_match(
        self,
        kg_service: Any,
        entity_text: str,
        entity_type: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """策略 1: 文字比對（精確匹配、模糊匹配）"""
        try:
            if kg_service.client.db is None or kg_service.client.db.aql is None:
                return []

            # 构建 AQL 查询
            aql = """FOR doc IN entities
FILTER doc.name == @entity_name
   OR doc.name LIKE CONCAT("%", @entity_name, "%")
   OR CONTAINS(LOWER(doc.name), LOWER(@entity_name))"""
            bind_vars: Dict[str, Any] = {"entity_name": entity_text}

            if entity_type:
                aql += " AND doc.type == @entity_type"
                bind_vars["entity_type"] = entity_type

            aql += "\nRETURN doc"

            self.logger.debug(
                "Executing text match AQL query",
                entity_text=entity_text,
                entity_type=entity_type,
                aql=aql,
                bind_vars=bind_vars,
            )

            # 使用 ArangoDBClient 的 execute_aql 方法，它已經處理了 cursor 迭代
            all_results = []
            try:
                aql_result = kg_service.client.execute_aql(aql, bind_vars=bind_vars, count=False)
                all_results = aql_result.get("results", [])[:limit]
            except Exception as outer_error:
                # 外層錯誤處理
                error_str = str(outer_error)
                self.logger.debug(
                    "Text match query failed",
                    entity_text=entity_text,
                    error=error_str,
                )
                all_results = []

            # 在 Python 中限制结果数量
            results = all_results[:limit]
            self.logger.debug(
                "Text match query completed",
                entity_text=entity_text,
                results_count=len(results),
                matched_entity_names=[r.get("name") for r in results[:5]],
            )
            return results

        except Exception as e:
            # 忽略 'cursor count not enabled' 错误，这是警告不是致命错误
            error_str = str(e)
            if "cursor count not enabled" in error_str.lower():
                # 这个错误不影响功能，只是警告
                self.logger.debug(
                    "Cursor count not enabled (non-fatal)",
                    entity_text=entity_text,
                )
            else:
                self.logger.warning(
                    "Text match query failed",
                    entity_text=entity_text,
                    error=error_str,
                )
            return []

    def _extract_keywords(self, text: str) -> List[str]:
        """從文本中提取關鍵詞（混合策略：提取完整詞語 + 拆分為子詞）"""
        keywords = []

        # 移除常見的停用詞和連接詞
        stop_words = {
            "的",
            "和",
            "与",
            "及",
            "或",
            "是",
            "在",
            "有",
            "为",
            "了",
            "就",
            "也",
            "都",
            "还",
            "又",
            "但",
            "而",
            "如果",
            "因为",
            "所以",
        }

        import re

        # 策略 1: 提取完整的中文字符序列（長度 >= 2）
        chinese_words = re.findall(r"[\u4e00-\u9fff]{2,}", text)
        for word in chinese_words:
            if word not in stop_words and word not in keywords:
                keywords.append(word)

        # 策略 2: 如果文本較長（> 4 字），拆分成子詞
        # 例如：「中国预制菜产业」-> 「中国」、「预制菜」、「产业」
        if len(text) > 4:
            chars = list(text)
            # 提取 2-3 字詞（優先）
            for length in [3, 2]:  # 先提取 3 字詞，再提取 2 字詞
                for i in range(len(chars) - length + 1):
                    word = "".join(chars[i : i + length])
                    if word not in stop_words and word not in keywords:
                        keywords.append(word)
                        if len(keywords) >= 15:  # 增加關鍵詞數量限制
                            break
                if len(keywords) >= 15:
                    break

        # 策略 3: 如果仍然沒有關鍵詞，使用滑動窗口提取
        if not keywords:
            chars = list(text)
            for i in range(len(chars) - 1):
                for j in range(i + 2, min(i + 5, len(chars) + 1)):  # 2-4 字詞
                    word = "".join(chars[i:j])
                    if word not in stop_words and word not in keywords:
                        keywords.append(word)
                        if len(keywords) >= 15:
                            break
                if len(keywords) >= 15:
                    break

        # 策略 4: 確保至少有一些關鍵詞（即使只有 2 個字符）
        if not keywords and len(text) >= 2:
            chars = list(text)
            for i in range(len(chars) - 1):
                word = "".join(chars[i : i + 2])
                if word not in stop_words and word not in keywords:
                    keywords.append(word)
                    if len(keywords) >= 10:
                        break

        self.logger.debug(
            "Keywords extracted",
            text=text[:50],
            keywords=keywords,
        )

        return keywords[:15]  # 增加關鍵詞數量限制

    def _query_entities_by_keywords(
        self,
        kg_service: Any,
        keywords: List[str],
        entity_type: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """策略 2: 關鍵詞匹配"""
        matched_entities = []

        try:
            if kg_service.client.db is None or kg_service.client.db.aql is None:
                return []

            for keyword in keywords:
                if len(matched_entities) >= limit:
                    break

                # 使用關鍵詞進行模糊匹配（改進的匹配策略）
                # 優先匹配長關鍵詞，使用更靈活的匹配方式
                aql = """FOR doc IN entities
FILTER doc.name LIKE CONCAT(@keyword, "%")
   OR doc.name LIKE CONCAT("%", @keyword)
   OR doc.name LIKE CONCAT("%", @keyword, "%")
   OR CONTAINS(LOWER(doc.name), LOWER(@keyword))
   OR CONTAINS(LOWER(@keyword), LOWER(doc.name))"""
                bind_vars: Dict[str, Any] = {"keyword": keyword}

                if entity_type:
                    aql += " AND doc.type == @entity_type"
                    bind_vars["entity_type"] = entity_type

                aql += "\nRETURN doc"

                self.logger.debug(
                    "Executing keyword match AQL query",
                    keyword=keyword,
                    entity_type=entity_type,
                    aql=aql,
                    bind_vars=bind_vars,
                )

                # 使用 ArangoDBClient 的 execute_aql 方法，它已經處理了 cursor 迭代
                try:
                    aql_result = kg_service.client.execute_aql(
                        aql, bind_vars=bind_vars, count=False
                    )
                    results = aql_result.get("results", [])[:limit]
                except Exception as outer_error:
                    # 外層錯誤處理
                    error_str = str(outer_error)
                    self.logger.debug(
                        "Keyword match query failed, continuing with next keyword",
                        keyword=keyword,
                        error=error_str,
                    )
                    results = []
                    # 繼續處理下一個關鍵詞，不中斷整個流程

                self.logger.debug(
                    "Keyword match query completed",
                    keyword=keyword,
                    results_count=len(results),
                    matched_entity_names=[r.get("name") for r in results[:5]],
                )

                # 去重
                existing_keys = {r.get("_key") for r in matched_entities if r.get("_key")}
                for result in results:
                    if result.get("_key") not in existing_keys:
                        matched_entities.append(result)
                        existing_keys.add(result.get("_key"))
                        if len(matched_entities) >= limit:
                            break

        except Exception as e:
            # 忽略 'cursor count not enabled' 错误，这是警告不是致命错误
            error_str = str(e)
            if "cursor count not enabled" in error_str.lower():
                # 这个错误不影响功能，只是警告
                self.logger.debug(
                    "Cursor count not enabled (non-fatal)",
                    keywords=keywords,
                )
            else:
                self.logger.warning(
                    "Keyword match query failed",
                    keywords=keywords,
                    error=error_str,
                )

        return matched_entities[:limit]

    def _expand_entities_by_relations(
        self,
        entities: List[Dict[str, Any]],
        kg_service: Any,
        depth: int = 1,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        通過關係擴展實體列表

        Args:
            entities: 原始實體列表
            kg_service: 圖譜構建服務
            depth: 擴展深度（默認為 1，只擴展直接關係）
            limit: 擴展後的實體數量限制

        Returns:
            擴展後的實體列表（包括原始實體和通過關係找到的實體）
        """
        expanded_entities = list(entities)  # 複製原始實體列表
        seen_entity_keys = {e.get("_key") for e in entities if e.get("_key")}

        if kg_service.client is None or kg_service.client.db is None:
            self.logger.warning("ArangoDB client is not initialized for relation expansion")
            return expanded_entities

        try:
            for entity in entities:
                if len(expanded_entities) >= limit:
                    break

                entity_id = entity.get("_id") or f"entities/{entity.get('_key')}"

                # 查詢實體的關係
                aql = """FOR rel IN relations
FILTER rel._from == @entity_id OR rel._to == @entity_id
RETURN DISTINCT {
    entity_id: (rel._from == @entity_id ? rel._to : rel._from),
    relation_type: rel.type
}"""
                bind_vars = {"entity_id": entity_id}

                try:
                    cursor = kg_service.client.db.aql.execute(aql, bind_vars=bind_vars)
                    related_entity_ids = []
                    it = iter(cursor)
                    while True:
                        try:
                            rel = next(it)
                            related_id = rel.get("entity_id", "")
                            if related_id and related_id not in related_entity_ids:
                                related_entity_ids.append(related_id)
                        except StopIteration:
                            break

                    # 獲取相關實體的詳細信息
                    for related_id in related_entity_ids[:5]:  # 限制每個實體的擴展數量
                        if len(expanded_entities) >= limit:
                            break

                        try:
                            # 從 entities 集合中獲取實體
                            entity_key_from_id = (
                                related_id.split("/")[-1] if "/" in related_id else related_id
                            )
                            if entity_key_from_id in seen_entity_keys:
                                continue

                            related_entity = kg_service.client.db.collection("entities").get(
                                entity_key_from_id
                            )
                            if (
                                related_entity
                                and related_entity.get("_key") not in seen_entity_keys
                            ):
                                expanded_entities.append(related_entity)
                                seen_entity_keys.add(related_entity.get("_key"))
                                self.logger.debug(
                                    "Entity expanded by relation",
                                    original_entity=entity.get("name"),
                                    expanded_entity=related_entity.get("name"),
                                )
                        except Exception as e:
                            self.logger.debug(
                                "Failed to get related entity",
                                related_id=related_id,
                                error=str(e),
                            )

                except Exception as e:
                    self.logger.debug(
                        "Failed to query relations for entity",
                        entity_id=entity_id,
                        error=str(e),
                    )

            self.logger.debug(
                "Entity expansion completed",
                original_count=len(entities),
                expanded_count=len(expanded_entities),
            )

        except Exception as e:
            self.logger.warning("Failed to expand entities by relations", error=str(e))

        return expanded_entities[:limit]

    def _query_entities_by_semantic_match(
        self,
        kg_service: Any,
        entity_text: str,
        entity_type: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """策略 3: 語義匹配（未來實現）"""
        # TODO: 實現語義匹配
        # 1. 為實體名稱生成向量
        # 2. 使用向量相似度搜索
        # 3. 返回語義相關的實體
        self.logger.debug("Semantic match not implemented yet", entity_text=entity_text[:50])
        return []

    def _format_graph_results(
        self, graph_results: List[Dict[str, Any]], query: str, limit: int = 10
    ) -> List[Memory]:
        """將圖譜數據轉換為 Memory 格式"""
        memories: List[Memory] = []
        seen_triples: set[str] = set()

        self.logger.debug(
            "Formatting graph results",
            input_count=len(graph_results),
            query=query[:50],
            limit=limit,
        )

        # 如果 graph_results 為空，記錄警告
        if not graph_results:
            self.logger.warning(
                "No graph results to format",
                query=query[:50],
            )
            return memories

        for i, result in enumerate(graph_results):
            try:
                # 處理鄰居節點結果
                if "vertex" in result and "edge" in result:
                    vertex = result.get("vertex", {})
                    edge = result.get("edge", {})

                    # 構建三元組文本
                    source_entity = vertex.get("name", "未知實體")
                    relation_type = edge.get("type", "相關")
                    target_entity = edge.get("_to", "")

                    # 獲取目標實體名稱（如果可能）
                    if target_entity:
                        try:
                            kg_service = self._get_kg_service()
                            if kg_service.client and kg_service.client.db:
                                target_doc = kg_service.client.db.collection("entities").get(
                                    target_entity.split("/")[-1]
                                    if "/" in target_entity
                                    else target_entity
                                )
                                if target_doc:
                                    target_entity = target_doc.get("name", target_entity)
                        except Exception:
                            pass

                    # 構建內容文本
                    content = f"{source_entity} - {relation_type} - {target_entity}"

                    # 生成唯一標識（基於三元組）
                    triple_key = f"{source_entity}|{relation_type}|{target_entity}"
                    if triple_key in seen_triples:
                        continue
                    seen_triples.add(triple_key)

                    # 計算相關度分數（基於實體匹配度）
                    relevance_score = 0.7  # 默認分數
                    if (
                        query.lower() in source_entity.lower()
                        or query.lower() in str(target_entity).lower()
                    ):
                        relevance_score = 0.9

                    # 創建 Memory 對象
                    memory = Memory(
                        memory_id=str(uuid.uuid4()),
                        content=content,
                        metadata={
                            "source": "graph",
                            "entity_id": vertex.get("_key", ""),
                            "relation_type": relation_type,
                            "file_id": vertex.get("file_id", ""),
                            "entity_type": vertex.get("type", ""),
                        },
                        memory_type=MemoryType.LONG_TERM,
                        priority=MemoryPriority.MEDIUM,
                        relevance_score=relevance_score,
                    )

                    memories.append(memory)

                # 處理子圖結果
                elif "path" in result:
                    path = result.get("path", {})
                    vertices = path.get("vertices", [])
                    edges = path.get("edges", [])

                    if len(vertices) >= 2 and len(edges) >= 1:
                        # 構建路徑文本
                        path_texts = []
                        for i, edge in enumerate(edges):
                            if i < len(vertices) - 1:
                                source = vertices[i].get("name", "未知")
                                relation = edge.get("type", "相關")
                                target = vertices[i + 1].get("name", "未知")
                                path_texts.append(f"{source} - {relation} - {target}")

                        content = " | ".join(path_texts)

                        # 生成唯一標識
                        path_key = "|".join(path_texts)
                        if path_key in seen_triples:
                            continue
                        seen_triples.add(path_key)

                        # 計算相關度分數
                        relevance_score = 0.6  # 路徑相關度稍低

                        # 創建 Memory 對象
                        memory = Memory(
                            memory_id=str(uuid.uuid4()),
                            content=content,
                            metadata={
                                "source": "graph",
                                "path_length": len(vertices),
                                "file_id": vertices[0].get("file_id", "") if vertices else "",
                            },
                            memory_type=MemoryType.LONG_TERM,
                            priority=MemoryPriority.MEDIUM,
                            relevance_score=relevance_score,
                        )

                        memories.append(memory)

            except Exception as e:
                self.logger.warning("Failed to format graph result", error=str(e))
                continue

            if len(memories) >= limit:
                break

        # 按相關度排序
        memories.sort(key=lambda m: m.relevance_score, reverse=True)

        return memories[:limit]

    def _merge_results(
        self, vector_results: List[Memory], graph_results: List[Memory], top_k: int
    ) -> List[Memory]:
        """合併向量和圖檢索結果"""
        # 去重（基於 memory_id）
        seen_ids: set[str] = set()
        merged: List[Memory] = []

        # 合併結果並應用權重
        for memory in vector_results:
            if memory.memory_id not in seen_ids:
                # 應用向量權重
                memory.relevance_score *= self.vector_weight
                merged.append(memory)
                seen_ids.add(memory.memory_id)

        for memory in graph_results:
            if memory.memory_id not in seen_ids:
                # 應用圖權重
                memory.relevance_score *= self.graph_weight
                merged.append(memory)
                seen_ids.add(memory.memory_id)
            else:
                # 如果已存在，增加相關度（融合）
                for m in merged:
                    if m.memory_id == memory.memory_id:
                        m.relevance_score += memory.relevance_score * self.graph_weight
                        break

        # 按相關度排序
        merged.sort(key=lambda m: m.relevance_score, reverse=True)

        return merged[:top_k]

    def _format_for_llm(self, memories: List[Memory]) -> List[Dict[str, Any]]:
        """格式化結果供 LLM 使用"""
        formatted = []
        for memory in memories:
            formatted.append(
                {
                    "content": memory.content,
                    "metadata": {
                        "memory_id": memory.memory_id,
                        "memory_type": memory.memory_type.value,
                        "priority": memory.priority.value,
                        **memory.metadata,
                    },
                    "score": memory.relevance_score,
                }
            )
        return formatted

    def update_strategy(self, strategy: RetrievalStrategy) -> None:
        """更新檢索策略"""
        self.strategy = strategy
        self.logger.info("Updated retrieval strategy", strategy=strategy.value)

    def update_weights(self, vector_weight: float, graph_weight: float) -> None:
        """更新檢索權重"""
        total = vector_weight + graph_weight
        if total > 0:
            self.vector_weight = vector_weight / total
            self.graph_weight = graph_weight / total
            self.logger.info(
                "Updated retrieval weights",
                vector_weight=self.vector_weight,
                graph_weight=self.graph_weight,
            )
