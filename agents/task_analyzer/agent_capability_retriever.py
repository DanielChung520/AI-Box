# 代碼功能說明: Agent 能力檢索服務（RAG 增強）
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Agent 能力檢索服務 - 使用 RAG 進行語義匹配"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentCapabilityRetriever:
    """Agent 能力檢索服務 - 使用 RAG 進行語義匹配"""

    def __init__(self):
        """初始化 Agent 能力檢索服務"""
        self._hybrid_rag_service: Optional[Any] = None
        self._agent_capabilities_collection = "agent_capabilities"
        self._initialized = False

    def _get_hybrid_rag_service(self) -> Optional[Any]:
        """獲取 HybridRAGService（懶加載）"""
        if self._hybrid_rag_service is not None:
            return self._hybrid_rag_service

        try:
            from agents.infra.memory.aam.aam_core import AAMManager
            from genai.workflows.rag.hybrid_rag import HybridRAGService

            # 獲取 AAMManager 實例
            aam_manager = AAMManager.get_instance()
            if aam_manager is None:
                logger.warning("AAMManager not available, RAG retrieval disabled")
                return None

            # 創建 HybridRAGService
            self._hybrid_rag_service = HybridRAGService(aam_manager=aam_manager)
            logger.info("AgentCapabilityRetriever: HybridRAGService initialized")
            return self._hybrid_rag_service

        except Exception as e:
            logger.warning(f"Failed to initialize HybridRAGService: {e}, RAG retrieval disabled")
            return None

    async def retrieve_matching_agents(
        self,
        user_input: str,
        intent_type: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        使用 RAG 檢索匹配的 Agent

        Args:
            user_input: 用戶輸入
            intent_type: 意圖類型
            top_k: 返回前 K 個匹配結果

        Returns:
            匹配的 Agent 列表，每個包含 agent_id 和相似度分數
        """
        rag_service = self._get_hybrid_rag_service()
        if rag_service is None:
            logger.debug("RAG service not available, returning empty list")
            return []

        try:
            # 構建檢索查詢
            query = f"{user_input} {intent_type}"

            # 使用 HybridRAG 檢索
            # 注意：HybridRAGService 會從 AAM 檢索，但需要確保 agent_capabilities 文檔已存儲
            # 可以通過 metadata 過濾來限制檢索範圍
            results = rag_service.retrieve(
                query=query,
                top_k=top_k,
                min_relevance=0.5,  # 最小相關度閾值
            )

            # 過濾結果：只返回 agent_capabilities 命名空間的文檔
            filtered_results = []
            for result in results:
                result_metadata = result.get("metadata", {})
                # 檢查是否為 agent_capabilities 相關文檔
                if (
                    result_metadata.get("namespace") == "agent_capabilities"
                    or result_metadata.get("doc_type")
                    in ["agent_capability", "design_document", "specification", "architecture"]
                    or "agent" in result_metadata.get("doc_id", "").lower()
                ):
                    filtered_results.append(result)

            # 如果過濾後結果不足，使用原始結果
            if len(filtered_results) < top_k // 2:
                logger.debug(
                    f"Filtered results too few ({len(filtered_results)}), using original results"
                )
                filtered_results = results[:top_k]
            else:
                results = filtered_results[:top_k]

            # 提取 Agent ID 和相似度
            matching_agents = []
            for result in results:
                metadata = result.get("metadata", {})
                agent_id = metadata.get("agent_id")
                score = result.get("score", 0.0)

                if agent_id and score >= 0.5:  # 只返回相關度 >= 0.5 的結果
                    matching_agents.append(
                        {
                            "agent_id": agent_id,
                            "score": score,
                            "metadata": metadata,
                            "content": result.get("content", ""),
                        }
                    )

            logger.info(
                f"AgentCapabilityRetriever: Found {len(matching_agents)} matching agents "
                f"for query: {user_input[:50]}..."
            )

            return matching_agents

        except Exception as e:
            logger.error(f"Failed to retrieve matching agents: {e}", exc_info=True)
            return []

    def get_agent_descriptions(self) -> List[Dict[str, str]]:
        """
        獲取所有 Agent 的能力描述（用於構建 Prompt）

        Returns:
            Agent 描述列表，格式為 [{"agent_id": "...", "description": "..."}]
        """
        try:
            from agents.services.registry.registry import get_agent_registry

            registry = get_agent_registry()
            if registry is None:
                logger.warning("Agent Registry not available")
                return []

            # 獲取所有在線的 Agent（包括 System Agents）
            from agents.services.registry.models import AgentStatus

            agents = registry.list_agents(
                status=AgentStatus.ONLINE,
                include_system_agents=True,
            )

            descriptions = []
            for agent in agents:
                # 構建 Agent 描述
                capabilities_str = (
                    ", ".join(agent.capabilities) if agent.capabilities else "general"
                )
                description = f"{agent.agent_id}: {capabilities_str}"

                # 如果有 metadata，添加更多信息
                if agent.metadata:
                    agent_type = agent.metadata.get("agent_type", "")
                    if agent_type:
                        description += f" (type: {agent_type})"

                descriptions.append({"agent_id": agent.agent_id, "description": description})

            logger.debug(
                f"AgentCapabilityRetriever: Retrieved {len(descriptions)} agent descriptions"
            )
            return descriptions

        except Exception as e:
            logger.warning(f"Failed to get agent descriptions: {e}")
            return []
