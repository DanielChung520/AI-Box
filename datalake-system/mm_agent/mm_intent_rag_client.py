# 代碼功能說明: MM-Agent Intent RAG Client
# 創建日期: 2026-02-28
# 創建人: AI-Box 開發團隊
# 最後修改日期: 2026-03-01 - 修復使用 Qdrant 向量檢索

"""MM-Agent Intent RAG 客戶端 - 使用 Qdrant 向量庫進行意圖分類"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

_m_m_intent_rag_client: Optional["MMIntentRAGClient"] = None


class MMIntentRAGClient:
    """MM-Agent Intent RAG 客戶端 - 使用 Qdrant 向量檢索"""

    COLLECTION_NAME = "mm_intents_rag"
    VECTOR_SIZE = 4096  # qwen3-embedding dimension

    def __init__(self):
        self._qdrant_client = None
        self._embedding_service = None
        self._intents_file = Path(__file__).resolve().parent.parent / "data" / "MMIntentsRAG.json"
        self._load_intents()

    def _load_intents(self):
        """從 JSON 文件加載意圖（用於獲取 system_intent_mapping）"""
        try:
            with open(self._intents_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._system_intent_mapping = data.get("system_intent_mapping", {})
            logger.info(f"[MMIntentRAG] 已加載 {len(self._system_intent_mapping)} 個系統意圖映射")
        except Exception as e:
            logger.warning(f"[MMIntentRAG] 加載意圖失敗: {e}")
            self._system_intent_mapping = {}
            self._intents_list = []
            self._intents_dict = {}  # intent_name -> intent_data
    
    def _load_intents(self):
        """從 JSON 文件加載意圖（用於獲取 system_intent_mapping 和 intents）"""
        try:
            with open(self._intents_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._system_intent_mapping = data.get("system_intent_mapping", {})
            self._intents_list = data.get("intents", [])
            
            # 構建 intent_name -> intent_data 的映射
            self._intents_dict = {}
            for intent in self._intents_list:
                intent_name = intent.get("intent_name")
                if intent_name:
                    self._intents_dict[intent_name] = intent
            
            logger.info(f"[MMIntentRAG] 已加載 {len(self._system_intent_mapping)} 個系統意圖映射")
            logger.info(f"[MMIntentRAG] 已加載 {len(self._intents_list)} 個意圖定義")
        except Exception as e:
            logger.warning(f"[MMIntentRAG] 加載意圖失敗: {e}")
            self._system_intent_mapping = {}
            self._intents_list = []
            self._intents_dict = {}

    def get_intent_details(self, intent_name: str) -> Optional[Dict[str, Any]]:
        """獲取意圖的詳細信息，包括 responsibility_type
        
        Args:
            intent_name: 意圖名稱
            
        Returns:
            意圖詳細信息字典，如果未找到返回 None
        """
        return self._intents_dict.get(intent_name)
    
    def get_responsibility_type(self, intent_name: str) -> Optional[str]:
        """從意圖名稱獲取 responsibility_type
        
        Args:
            intent_name: 意圖名稱
            
        Returns:
            responsibility_type，如果未找到返回 None
        """
        intent_data = self._intents_dict.get(intent_name)
        if intent_data:
            return intent_data.get("responsibility_type")
        return None

    def _get_qdrant_client(self):
        """獲取 Qdrant 客戶端"""
        if self._qdrant_client is None:
            try:
                from qdrant_client import QdrantClient

                qdrant_host = os.getenv("QDRANT_HOST", "localhost")
                qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
                self._qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
                logger.info(f"[MMIntentRAG] 連接到 Qdrant: {qdrant_host}:{qdrant_port}")
            except Exception as e:
                logger.warning(f"[MMIntentRAG] Qdrant 連接失敗: {e}")
                return None
        return self._qdrant_client

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """獲取文本的向量化"""
        if self._embedding_service is None:
            try:
                from services.api.services.embedding_service import get_embedding_service

                self._embedding_service = get_embedding_service()
            except ImportError:
                logger.warning("[MMIntentRAG] 無法導入 embedding_service")
                return None

        # 使用 embedding service
        try:
            import asyncio
            
            # 嘗試使用現有的事件循環
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果已有循環在運行，創建一個新的任務
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run, 
                            self._embedding_service.generate_embedding(text)
                        )
                        return future.result()
            except RuntimeError:
                # 沒有運行中的循環，可以直接使用
                return asyncio.run(self._embedding_service.generate_embedding(text))
        except Exception as e:
            logger.warning(f"[MMIntentRAG] Embedding 生成失敗: {e}")
            return None
        """獲取文本的向量化"""
        if self._embedding_service is None:
            try:
                from services.api.services.embedding_service import get_embedding_service

                self._embedding_service = get_embedding_service()
            except ImportError:
                logger.warning("[MMIntentRAG] 無法導入 embedding_service")
                return None

        # 使用 embedding service
        try:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._embedding_service.generate_embedding(text))
            finally:
                loop.close()
        except Exception as e:
            logger.warning(f"[MMIntentRAG] Embedding 生成失敗: {e}")
            return None

    def classify_intent(
        self,
        query: str,
        top_k: int = 1,
        min_score: float = 0.5,
    ) -> Optional[str]:
        """使用 Qdrant 向量檢索進行意圖分類"""
        logger.info(f"[MMIntentRAG] 開始分類: {query[:50]}...")

        # 1. 生成查詢向量
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            logger.warning("[MMIntentRAG] 無法生成查詢向量，分類失敗")
            return None

        # 2. 連接 Qdrant 進行搜索
        client = self._get_qdrant_client()
        if client is None:
            logger.warning("[MMIntentRAG] 無法連接 Qdrant，分類失敗")
            return None

        try:
            # 3. 搜索最相似的意圖
            search_results = client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=query_embedding,
                limit=top_k,
                score_threshold=min_score,
            )

            if not search_results.points:
                logger.warning("[MMIntentRAG] 未找到匹配的意圖")
                return None

            # 4. 返回最佳匹配
            best_result = search_results.points[0]
            intent_name = best_result.payload.get("intent_name")
            score = best_result.score

            logger.info(f"[MMIntentRAG] 匹配結果: {intent_name} (score={score:.3f})")
            return intent_name

        except Exception as e:
            logger.error(f"[MMIntentRAG] Qdrant 搜索失敗: {e}")
            return None

    def classify_return_mode(
        self,
        query: str,
        top_k: int = 1,
        min_score: float = 0.3,
    ) -> Optional[str]:
        """使用 Qdrant 向量檢索進行 return_mode 分類"""
        logger.info(f"[MMIntentRAG] 開始分類 return_mode: {query[:50]}...")

        # 過濾只匹配 return_mode 相關的意圖
        return_mode_intents = ["RETURN_SUMMARY", "RETURN_LIST"]

        # 生成查詢向量
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            logger.warning("[MMIntentRAG] 無法生成查詢向量，分類失敗")
            return None

        # 連接 Qdrant 進行搜索
        client = self._get_qdrant_client()
        if client is None:
            logger.warning("[MMIntentRAG] 無法連接 Qdrant，分類失敗")
            return None

        try:
            # 搜索所有意圖
            search_results = client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=query_embedding,
                limit=5,  # 取前5個結果
                score_threshold=min_score,
            )

            if not search_results.points:
                logger.warning("[MMIntentRAG] 未找到匹配的 return_mode")
                return None

            # 找到第一個 return_mode 相關的意圖
            for result in search_results.points:
                intent_name = result.payload.get("intent_name")
                if intent_name in return_mode_intents:
                    score = result.score
                    logger.info(f"[MMIntentRAG] return_mode 匹配結果: {intent_name} (score={score:.3f})")
                    return intent_name

            logger.info("[MMIntentRAG] 未找到 return_mode 匹配，使用預設 summary")
            return None

        except Exception as e:
            logger.error(f"[MMIntentRAG] Qdrant 搜索失敗: {e}")
            return None

    def get_system_intent(self, rag_intent: str) -> str:
            return None

    def get_system_intent(self, rag_intent: str) -> str:
        """根據 RAG 意圖獲取系統意圖"""
        return self._system_intent_mapping.get(rag_intent, "SIMPLE_QUERY")


def get_mm_intent_rag_client() -> MMIntentRAGClient:
    """獲取 MM Intent RAG 客戶端單例"""
    global _m_m_intent_rag_client
    if _m_m_intent_rag_client is None:
        _m_m_intent_rag_client = MMIntentRAGClient()
    return _m_m_intent_rag_client
