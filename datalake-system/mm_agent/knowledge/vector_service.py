# 代碼功能說明: 向量檢索服務
# 創建日期: 2026-02-01
# 創建人: Daniel Chung

"""向量檢索服務 - 從 Qdrant 檢索相似的意圖模版"""

import logging
from typing import Any, Dict, List, Optional

import sys
from pathlib import Path

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from database.qdrant.client import get_qdrant_client
from qdrant_client.models import Distance, PointStruct, VectorParams, Filter

logger = logging.getLogger(__name__)


class VectorSearchService:
    """向量檢索服務"""

    def __init__(self):
        """初始化向量檢索服務"""
        self._client = None
        self._collection_name = "data_agent_intents"
        self._embedding_model = "nomic-embed-text:latest"
        self._embedding_dimension = 768

    async def initialize(self):
        """初始化服務"""
        try:
            self._client = get_qdrant_client()

            # 檢查集合是否存在
            collections = self._client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self._collection_name not in collection_names:
                logger.warning(f"集合不存在: {self._collection_name}")
                # 創建集合（如果不存在）
                self._client.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=VectorParams(
                        size=self._embedding_dimension,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"創建集合: {self._collection_name}")

            logger.info("向量檢索服務已初始化", collection_name=self._collection_name)
        except Exception as e:
            logger.error(f"初始化失敗: {e}", exc_info=True)
            raise

    async def search_intents(
        self,
        query: str,
        collection: Optional[str] = None,
        top_k: int = 5,
        score_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """搜索意圖模版

        Args:
            query: 用戶查詢（需要向量化）
            collection: Qdrant collection 名稱
            top_k: 返回前 K 個結果
            score_threshold: 相似度閾值

        Returns:
            相似意圖列表
        """
        collection = collection or self._collection_name

        try:
            # 生成查詢向量
            query_vector = await self._embed_query(query)

            if not query_vector:
                logger.warning("無法生成查詢向量", query=query)
                return []

            # 執行向量搜索
            search_result = self._client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
                with_payload=True,
            )

            # 解析結果
            results = []
            for point in search_result:
                payload = point.payload or {}

                results.append(
                    {
                        "id": point.id,
                        "score": point.score,
                        "payload": {
                            "id": payload.get("id", ""),
                            "query": payload.get("query", ""),
                            "sql": payload.get("sql", ""),
                            "type": payload.get("type", ""),
                        },
                    }
                )

            logger.info(
                "向量檢索完成",
                query=query,
                collection=collection,
                top_k=top_k,
                results_count=len(results),
            )

            return results

        except Exception as e:
            logger.error(f"向量檢索失敗: {e}", exc_info=True)
            raise

    async def get_intent_templates(
        self,
        intent_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """獲取意圖模版

        Args:
            intent_type: 意圖類型（如 query_inventory、statistics）

        Returns:
            意圖模版列表
        """
        try:
            # 滾動檢索所有點
            scroll_result = self._client.scroll(
                collection_name=self._collection_name,
                limit=1000,
                with_payload=True,
            )

            results = []
            for point in scroll_result[0]:
                payload = point.payload or {}

                # 過濾意圖類型
                if intent_type and payload.get("type") != intent_type:
                    continue

                results.append(
                    {
                        "id": point.id,
                        "payload": {
                            "id": payload.get("id", ""),
                            "query": payload.get("query", ""),
                            "sql": payload.get("sql", ""),
                            "type": payload.get("type", ""),
                        },
                    }
                )

            logger.info(
                "獲取意圖模版",
                intent_type=intent_type,
                total_count=len(results),
            )

            return results

        except Exception as e:
            logger.error(f"獲取意圖模版失敗: {e}", exc_info=True)
            raise

    async def _embed_query(self, text: str) -> Optional[List[float]]:
        """生成查詢向量

        Args:
            text: 查詢文本

        Returns:
            向量（如果生成失敗則返回 None）
        """
        try:
            # 使用 Ollama 生成向量
            import httpx
            from dotenv import load_dotenv

            load_dotenv(dotenv_path=ai_box_root / ".env")

            ollama_url = "http://localhost:11434"
            embed_url = f"{ollama_url}/api/embeddings"

            response = await httpx.AsyncClient(timeout=10).post(
                embed_url,
                json={
                    "model": self._embedding_model,
                    "prompt": text,
                },
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
            else:
                logger.error(f"Ollama 向量化失敗: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"向量化失敗: {e}", exc_info=True)
            return None

    async def get_inventory_intents(
        self,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """獲取庫存查詢相關意圖

        Args:
            top_k: 返回前 K 個結果

        Returns:
            庫存相關意圖列表
        """
        # 搜索庫存相關意圖
        results = await self.search_intents(
            query="庫存查詢",
            collection=self._collection_name,
            top_k=top_k,
        )

        return results

    async def get_statistics_intents(
        self,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """獲取統計相關意圖

        Args:
            top_k: 返回前 K 個結果

        Returns:
            統計相關意圖列表
        """
        # 搜索統計相關意圖
        results = await self.search_intents(
            query="統計查詢",
            collection=self._collection_name,
            top_k=top_k,
        )

        return results


if __name__ == "__main__":
    import asyncio

    async def test_vector_service():
        """測試向量檢索服務"""
        service = VectorSearchService()

        try:
            await service.initialize()

            # 測試 1：搜索庫存意圖
            print("\n" + "=" * 70)
            print("測試 1：搜索庫存意圖")
            print("=" * 70)

            inventory_results = await service.get_inventory_intents(top_k=3)
            print(f"庫存意圖數量: {len(inventory_results)}")
            for i, result in enumerate(inventory_results, 1):
                print(f"  {i}. {result['payload']['query']} (score: {result['score']:.3f})")

            # 測試 2：搜索統計意圖
            print("\n" + "=" * 70)
            print("測試 2：搜索統計意圖")
            print("=" * 70)

            stats_results = await service.get_statistics_intents(top_k=3)
            print(f"統計意圖數量: {len(stats_results)}")
            for i, result in enumerate(stats_results, 1):
                print(f"  {i}. {result['payload']['query']} (score: {result['score']:.3f})")

            # 測試 3：獲取所有意圖模版
            print("\n" + "=" * 70)
            print("測試 3：獲取所有意圖模版")
            print("=" * 70)

            all_intents = await service.get_intent_templates()
            print(f"總意圖數量: {len(all_intents)}")

            # 統計意圖類型
            intent_types = {}
            for intent in all_intents:
                intent_type = intent["payload"]["type"]
                intent_types[intent_type] = intent_types.get(intent_type, 0) + 1

            print("意圖類型分佈:")
            for intent_type, count in intent_types.items():
                print(f"  - {intent_type}: {count}")

        except Exception as e:
            logger.error(f"測試失敗: {e}", exc_info=True)
            raise

    asyncio.run(test_vector_service())
