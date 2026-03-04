# 代码功能说明: OrchestratorIntentRAG Qdrant Client
# 创建日期: 2026-02-27
# 创建人: Daniel Chung
# 最后修改日期: 2026-02-27

"""OrchestratorIntentRAG Qdrant Client

用於 Orchestrator 層的意圖分類向量檢索

優先級規則：
- 當混合意圖時，以業務意圖為優先
- BUSINESS_QUERY, BUSINESS_ACTION, AGENT_WORK > GENERAL_QA > GREETING, THANKS, CHITCHAT
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any

import numpy as np

logger = logging.getLogger(__name__)

# Collection 配置
COLLECTION_NAME = "orchestrator_intent_rag"
VECTOR_SIZE = 4096  # qwen3-embedding dimension

# 業務意圖（最高優先級）
BUSINESS_INTENTS = {"BUSINESS_QUERY", "BUSINESS_ACTION", "AGENT_WORK"}


class IntentStrategy(Enum):
    """意圖處理策略"""

    DIRECT_RESPONSE = "direct_response"  # 直接回覆
    KNOWLEDGE_RAG = "knowledge_rag"  # 知識庫檢索
    ROUTE_TO_AGENT = "route_to_agent"  # 轉發到業務 Agent
    ROUTE_TO_SPECIFIC_AGENT = "route_to_specific_agent"  # 轉發到指定 Agent


@dataclass
class IntentResult:
    """意圖分類結果"""

    intent_name: str
    description: str
    priority: int
    action_strategy: IntentStrategy
    response_template: str
    score: float


class OrchestratorIntentRAG:
    """Orchestrator 意圖分類 RAG 客戶端"""

    def __init__(
        self,
        qdrant_client=None,
        embedding_service=None,
        threshold: float = 0.6,
    ):
        """初始化

        Args:
            qdrant_client: Qdrant 客戶端（可選）
            embedding_service: 向量化服務（可選）
            threshold: 置信度閾值
        """
        self._qdrant_client = qdrant_client
        self._embedding_service = embedding_service
        self.threshold = threshold
        self._initialized = False

    async def _ensure_initialized(self):
        """確保客戶端已初始化"""
        if self._initialized:
            return

        # 初始化 Qdrant 客戶端
        if self._qdrant_client is None:
            try:
                from database.qdrant.client import get_qdrant_client

                self._qdrant_client = get_qdrant_client()
            except Exception as e:
                logger.warning(f"無法連接 Qdrant: {e}，將使用備份方案")

        # 初始化向量化服務
        if self._embedding_service is None:
            try:
                from services.api.services.embedding_service import get_embedding_service

                self._embedding_service = get_embedding_service()
            except Exception as e:
                logger.warning(f"無法獲取向量化服務: {e}")

        self._initialized = True

    async def classify(self, user_input: str) -> IntentResult:
        """分類用戶輸入

        Args:
            user_input: 用戶輸入文本

        Returns:
            IntentResult: 分類結果
        """
        await self._ensure_initialized()

        # 1. 獲取用戶輸入的向量
        user_embedding = await self._get_embedding(user_input)

        if user_embedding is None:
            # 無法獲取向量化，使用備份方案
            return await self._fallback_classify(user_input)

        # 2. 如果有 Qdrant，從 Qdrant 檢索多個結果
        if self._qdrant_client is not None:
            try:
                results = self._qdrant_client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=user_embedding,
                    limit=5,  # 獲取更多結果用於優先級判斷
                    with_payload=True,
                ).points

                if results:
                    # 3. 應用優先級規則：業務意圖優先
                    return self._apply_priority_rule(results)

            except Exception as e:
                logger.warning(f"Qdrant 檢索失敗: {e}，使用備份方案")

        # 4. 備份方案
        return await self._fallback_classify(user_input)

    def _apply_priority_rule(self, results) -> IntentResult:
        """應用優先級規則：業務意圖優先

        規則：
        - 如果最高分是業務意圖，直接返回
        - 如果最高分是非業務，但結果中有業務意圖且分數接近，返回業務意圖
        - 否則返回最高分結果
        """
        if not results:
            return IntentResult(
                intent_name="UNKNOWN",
                description="無法識別",
                priority=99,
                action_strategy=IntentStrategy.DIRECT_RESPONSE,
                response_template="",
                score=0.0,
            )

        top_result = results[0]
        top_intent = top_result.payload.get("intent_name")
        top_score = top_result.score

        # 如果最高分就是業務意圖，直接返回
        if top_intent in BUSINESS_INTENTS and top_score >= self.threshold:
            return self._result_to_intent_result(top_result)

        # 檢查結果中是否有業務意圖
        for r in results:
            intent = r.payload.get("intent_name")
            score = r.score

            if intent in BUSINESS_INTENTS and score >= self.threshold * 0.8:
                # 業務意圖分數不低於閾值的 80%，以業務為優先
                logger.info(
                    f"[Priority Rule] 混合意圖檢測: top={top_intent}({top_score:.2f}), "
                    f"business={intent}({score:.2f}) → 選擇業務"
                )
                return self._result_to_intent_result(r)

        # 沒有業務意圖或分數太低，返回最高分結果
        return self._result_to_intent_result(top_result)

    def _result_to_intent_result(self, result) -> IntentResult:
        """將 Qdrant 結果轉換為 IntentResult"""
        return IntentResult(
            intent_name=result.payload.get("intent_name", "UNKNOWN"),
            description=result.payload.get("description", ""),
            priority=result.payload.get("priority", 99),
            action_strategy=IntentStrategy(
                result.payload.get("action_strategy", "direct_response")
            ),
            response_template=result.payload.get("response_template", ""),
            score=result.score,
        )

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """獲取文本的向量表示"""
        if self._embedding_service is None:
            return None

        try:
            return await self._embedding_service.generate_embedding(text)
        except Exception as e:
            logger.warning(f"向量化失敗: {e}")
            return None

    async def _fallback_classify(self, user_input: str) -> IntentResult:
        """備份分類方案（使用簡單的關鍵詞匹配）

        當 Qdrant 不可用時使用
        """
        from agents.task_analyzer.semantic_intent_classifier import (
            SemanticIntentClassifier,
            get_semantic_intent_classifier,
        )

        classifier = get_semantic_intent_classifier()
        category = await classifier.classify(user_input)

        # 映射到 IntentResult
        strategy_map = {
            "GREETING": IntentStrategy.DIRECT_RESPONSE,
            "THANKS": IntentStrategy.DIRECT_RESPONSE,
            "CHITCHAT": IntentStrategy.DIRECT_RESPONSE,
            "GENERAL_QA": IntentStrategy.KNOWLEDGE_RAG,
            "BUSINESS_QUERY": IntentStrategy.ROUTE_TO_AGENT,
            "BUSINESS_ACTION": IntentStrategy.ROUTE_TO_AGENT,
            "AGENT_WORK": IntentStrategy.ROUTE_TO_SPECIFIC_AGENT,
        }

        # 優先級映射（數字越小越高）
        priority_map = {
            "BUSINESS_QUERY": 1,
            "BUSINESS_ACTION": 1,
            "AGENT_WORK": 1,
            "GENERAL_QA": 2,
            "GREETING": 3,
            "THANKS": 3,
            "CHITCHAT": 3,
        }

        return IntentResult(
            intent_name=category.value,
            description=category.name,
            priority=priority_map.get(category.value, 99),
            action_strategy=strategy_map.get(category.value, IntentStrategy.DIRECT_RESPONSE),
            response_template="",
            score=0.5,
        )

    def is_business_intent(self, result: IntentResult) -> bool:
        """判斷是否為業務意圖"""
        return result.intent_name in BUSINESS_INTENTS

    def needs_agent_selection(self, result: IntentResult) -> bool:
        """判斷是否需要選擇 Agent"""
        return (
            result.intent_name in BUSINESS_INTENTS
            and result.action_strategy == IntentStrategy.ROUTE_TO_AGENT
        )

    def sync_classify(self, user_input: str) -> IntentResult:
        """同步版本的 classify（用於同步上下文）"""
        try:
            # 嘗試獲取現有的 event loop
            try:
                loop = asyncio.get_running_loop()
                # 如果已經在 async 上下文中，在新線程中運行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.classify(user_input))
                    return future.result()
            except RuntimeError:
                # 沒有運行中的 loop，創建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self.classify(user_input))
                loop.close()
                return result
        except Exception as e:
            logger.warning(f"sync_classify failed: {e}")
            # 返回預設業務意圖（保守策略）
            return IntentResult(
                intent_name="BUSINESS_QUERY",
                description="Classification failed",
                priority=1,
                action_strategy=IntentStrategy.ROUTE_TO_AGENT,
                response_template="",
                score=0.0,
            )


# 全局單例
_intent_rag: Optional[OrchestratorIntentRAG] = None


def get_orchestrator_intent_rag() -> OrchestratorIntentRAG:
    """獲取 OrchestratorIntentRAG 單例"""
    global _intent_rag
    if _intent_rag is None:
        _intent_rag = OrchestratorIntentRAG()
    return _intent_rag
