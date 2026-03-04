#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intent RAG 同步腳本
- 載入 MM-Agent 意圖分類場景庫 metadata
- 生成向量嵌入並存儲到 Qdrant 向量資料庫
- 提供同步功能，當 metadata 調整時可重新同步

使用方式:
    python sync_intent.py

    # 強制重新同步（重建 collection）
    python sync_intent.py --rebuild

    # 指定自定義 metadata 路徑
    python sync_intent.py --path /custom/path/intents.json

    # 測試檢索
    python sync_intent.py --test "庫房QC20有哪些料號"
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

script_dir = Path(__file__).parent
DEFAULT_INTENTS_DIR = script_dir
DEFAULT_INTENTS_FILE = "mm_agent_intents.json"
COLLECTION_NAME = "mm_agent_intents"

ai_box_root = script_dir.parent.parent
sys.path.insert(0, str(ai_box_root))


class IntentRAGStore:
    """Intent RAG 向量存儲管理器 - 使用 Qdrant"""

    def __init__(
        self,
        intents_file: Path,
        collection_name: str = COLLECTION_NAME,
    ):
        self.intents_file = intents_file
        self.collection_name = collection_name
        self.qdrant_client = None
        self.embedding_model = None

        self.metadata = self._load_metadata()
        self.scenarios = self.metadata.get("scenarios", [])

    def _load_metadata(self) -> Dict[str, Any]:
        if not self.intents_file.exists():
            raise FileNotFoundError(f"Intent metadata not found: {self.intents_file}")

        with open(self.intents_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        logger.info(f"Loaded {len(metadata.get('scenarios', []))} intent scenarios")
        return metadata

    def _init_qdrant(self):
        """初始化 Qdrant 客戶端"""
        from database.qdrant.client import get_qdrant_client

        self.qdrant_client = get_qdrant_client()
        logger.info("Qdrant client initialized")

    def _init_embedding_model(self):
        """初始化 embedding 模型"""
        try:
            from sentence_transformers import SentenceTransformer

            self.embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            logger.info("SentenceTransformer embedding model loaded")
        except ImportError:
            logger.warning("SentenceTransformer not available, using fallback")
            self.embedding_model = None

    def _generate_embedding(self, text: str) -> List[float]:
        if self.embedding_model:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        else:
            import hashlib
            hash_obj = hashlib.sha256(text.encode())
            hash_bytes = hash_obj.digest()
            result = []
            for i in range(256):
                byte_val = hash_bytes[i % len(hash_bytes)]
                result.append(float(byte_val) / 255.0)
            return result

    def _ensure_collection(self, vector_size: int = 384):
        """確保 Qdrant collection 存在"""
        from qdrant_client.models import Distance, VectorParams

        collections = self.qdrant_client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if self.collection_name not in collection_names:
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            logger.info(f"Created collection: {self.collection_name}")
        else:
            logger.info(f"Collection already exists: {self.collection_name}")

    def sync(self, rebuild: bool = False):
        """同步 intent scenarios 到 Qdrant"""
        logger.info(f"Starting intent RAG sync (rebuild={rebuild})")

        self._init_qdrant()
        self._init_embedding_model()

        vector_size = 384 if self.embedding_model else 256

        if rebuild:
            try:
                self.qdrant_client.delete_collection(collection_name=self.collection_name)
                logger.info(f"Deleted collection: {self.collection_name}")
            except Exception as e:
                logger.warning(f"Collection delete failed (may not exist): {e}")

        self._ensure_collection(vector_size=vector_size)

        from qdrant_client.models import PointStruct

        points = []
        for idx, scenario in enumerate(self.scenarios):
            scenario_id = scenario["id"]
            user_input = scenario["user_input"]
            intent = scenario["intent"]
            category = scenario["category"]

            embedding = self._generate_embedding(user_input)

            payload = {
                "scenario_id": scenario_id,
                "intent": intent,
                "category": category,
                "layer": scenario.get("layer", 2),
                "sub_type": scenario.get("sub_type", ""),
                "description": scenario.get("intent_description", ""),
                "user_input": user_input,
            }

            points.append(PointStruct(id=idx, vector=embedding, payload=payload))

        if points:
            self.qdrant_client.upsert(collection_name=self.collection_name, points=points)
            logger.info(f"Indexed {len(points)} intent scenarios to Qdrant")

        metadata_copy_path = script_dir.parent / "vector_stores" / "intents" / "metadata.json"
        metadata_copy_path.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_copy_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved metadata copy to {metadata_copy_path}")

        logger.info("Intent RAG sync completed!")

        return {
            "total_scenarios": len(points),
            "collection": self.collection_name,
        }

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """檢索相似的 intent scenarios"""
        if self.qdrant_client is None:
            self._init_qdrant()
            self._init_embedding_model()

        query_embedding = self._generate_embedding(query)

        results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
            score_threshold=min_score if min_score > 0 else None,
            with_payload=True,
        ).points

        retrieved = []
        for result in results:
            payload = result.payload
            retrieved.append(
                {
                    "id": payload.get("id"),
                    "score": result.score,
                    "query": payload.get("user_input"),
                    "intent": payload.get("intent"),
                    "category": payload.get("category"),
                    "description": payload.get("description"),
                }
            )

        return retrieved


def main():
    parser = argparse.ArgumentParser(description="Intent RAG 同步工具 (Qdrant)")
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="自定義 intent metadata JSON 路徑",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="強制重建 collection",
    )
    parser.add_argument(
        "--test",
        type=str,
        default=None,
        help="測試檢索功能，傳入查詢字串",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="檢索返回的結果數量（預設 3）",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="最小相似度閾值（預設 0.0）",
    )

    args = parser.parse_args()

    if args.path:
        intents_file = Path(args.path)
    else:
        intents_file = DEFAULT_INTENTS_DIR / DEFAULT_INTENTS_FILE

    store = IntentRAGStore(
        intents_file=intents_file,
        collection_name=COLLECTION_NAME,
    )

    if args.test:
        print(f"\n=== Testing Intent RAG ===\n")
        print(f"Query: {args.test}\n")

        try:
            sync_result = store.sync(rebuild=args.rebuild)
            print(f"Sync result: {sync_result}\n")
        except Exception as e:
            logger.warning(f"Sync failed: {e}")

        results = store.retrieve(
            query=args.test,
            top_k=args.top_k,
            min_score=args.min_score,
        )

        print(f"=== Top {len(results)} Results ===\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. [{result['intent']}] {result['query']}")
            print(f"   Score: {result['score']:.4f}")
            print(f"   Category: {result['category']}")
            print(f"   Description: {result['description']}")
            print()

        return

    print(f"\n=== Intent RAG Sync (Qdrant) ===\n")
    print(f"Intents file: {intents_file}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Rebuild: {args.rebuild}\n")

    result = store.sync(rebuild=args.rebuild)

    print(f"=== Sync Result ===\n")
    print(f"Total scenarios: {result['total_scenarios']}")
    print(f"Collection: {result['collection']}")
    print(f"\n✅ Intent RAG sync completed!")


if __name__ == "__main__":
    main()
