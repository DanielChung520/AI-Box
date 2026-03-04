#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代碼功能說明: OrchestratorIntentRAG 同步腳本
功能：將 OrchestratorIntentRAG.json 同步到 Qdrant 向量庫
創建日期: 2026-02-27
創建人: Daniel Chung
最後修改日期: 2026-02-27
"""

import argparse
import json
import logging
import sys
import os
import sys
from pathlib import Path

# 將項目根目錄添加到 sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, List, Any, Optional

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    VectorParams,
    Distance,
)

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 預設路徑（相對於腳本所在目錄）
DEFAULT_JSON_PATH = Path(__file__).parent / "MMIntentsRAG.json"
COLLECTION_NAME = "mm_intents_rag"
COLLECTION_NAME = "orchestrator_intent_rag"
VECTOR_SIZE = 4096  # qwen3-embedding dimension


def get_embedding_service():
    """取得向量化服務"""
    try:
        from services.api.services.embedding_service import get_embedding_service as _get

        return _get()
    except ImportError:
        logger.warning("無法導入 embedding_service，使用模擬向量化")
        return None


def generate_mock_embedding(text: str, dimension: int = VECTOR_SIZE) -> List[float]:
    """生成模擬向量化（當無法使用真實服務時）"""
    import hashlib

    hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
    np.random.seed(hash_val % (2**32))
    return np.random.randn(dimension).tolist()


async def get_embeddings_batch(
    texts: List[str], embedding_service: Optional[Any] = None
) -> List[List[float]]:
    """批量獲取向量化"""
    if embedding_service is None:
        return [generate_mock_embedding(text) for text in texts]

    embeddings = []
    for text in texts:
        try:
            embedding = await embedding_service.generate_embedding(text)
            embeddings.append(embedding)
        except Exception as e:
            logger.warning(f"向量化失敗: {text[:30]}..., 使用模擬向量: {e}")
            embeddings.append(generate_mock_embedding(text))

    return embeddings


def load_intent_config(json_path: Path) -> Dict[str, Any]:
    """載入意圖配置"""
    logger.info(f"載入配置: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    logger.info(f"配置版本: {config.get('version')}")
    logger.info(f"意圖數量: {len(config.get('intents', {}))}")

    return config


def prepare_points(config: Dict[str, Any], embeddings: List[List[float]]) -> List[PointStruct]:
    """準備 Qdrant Points"""
    intents = config.get("intents", {})
    points = []
    point_id = 0

    example_metadata = []

    for intent_name, intent_config in intents.items():
        examples_by_lang = intent_config.get("examples", {})

        for lang, examples in examples_by_lang.items():
            for example in examples:
                example_metadata.append(
                    {
                        "intent_name": intent_name,
                        "description": intent_config.get("description", ""),
                        "priority": intent_config.get("priority", 99),
                        "action_strategy": intent_config.get("action_strategy", ""),
                        "response_template": intent_config.get("response_template", ""),
                        "language": lang,
                        "example_text": example,
                    }
                )

    if len(embeddings) != len(example_metadata):
        raise ValueError(
            f"向量化數量 ({len(embeddings)}) 與示例數量 ({len(example_metadata)}) 不匹配"
        )

    for i, (embedding, metadata) in enumerate(zip(embeddings, example_metadata)):
        points.append(PointStruct(id=point_id + i, vector=embedding, payload=metadata))

    logger.info(f"準備了 {len(points)} 個 Points")

    return points


async def sync_to_qdrant(
    json_path: Path,
    qdrant_host: str = "localhost",
    qdrant_port: int = 6333,
    qdrant_api_key: Optional[str] = None,
    recreate_collection: bool = False,
) -> bool:
    """同步到 Qdrant"""

    # 1. 載入配置
    config = load_intent_config(json_path)

    # 2. 收集所有示例文本
    intents = config.get("intents", {})
    all_examples = []

    for intent_name, intent_config in intents.items():
        examples_by_lang = intent_config.get("examples", {})
        for lang, examples in examples_by_lang.items():
            for example in examples:
                all_examples.append(example)

    logger.info(f"總共 {len(all_examples)} 個示例")

    # 3. 獲取向量化
    logger.info("開始向量化...")
    embedding_service = get_embedding_service()

    try:
        embeddings = await get_embeddings_batch(all_examples, embedding_service)
        logger.info(f"向量化完成: {len(embeddings)} 個向量")
    except Exception as e:
        logger.error(f"向量化失敗: {e}")
        return False

    # 4. 準備 Points
    points = prepare_points(config, embeddings)

    # 5. 連接 Qdrant
    logger.info(f"連接 Qdrant: {qdrant_host}:{qdrant_port}")

    if qdrant_api_key:
        client = QdrantClient(host=qdrant_host, port=qdrant_port, api_key=qdrant_api_key)
    else:
        client = QdrantClient(host=qdrant_host, port=qdrant_port)

    # 6. 檢查/創建 Collection
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]

    if COLLECTION_NAME in collection_names:
        if recreate_collection:
            logger.info(f"刪除舊 Collection: {COLLECTION_NAME}")
            client.delete_collection(collection_name=COLLECTION_NAME)
        else:
            logger.info(f"Collection 已存在: {COLLECTION_NAME}")

    if COLLECTION_NAME not in collection_names or recreate_collection:
        logger.info(f"創建 Collection: {COLLECTION_NAME}")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )

    # 7. 上傳 Points
    logger.info(f"上傳 {len(points)} Points 到 Qdrant...")

    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        logger.info(f"上傳進度: {min(i + batch_size, len(points))}/{len(points)}")

    # 8. 驗證
    collection_info = client.get_collection(collection_name=COLLECTION_NAME)
    logger.info(f"同步完成！Collection: {COLLECTION_NAME}, Points: {collection_info.points_count}")

    return True


def query_intent(
    user_query: str,
    qdrant_host: str = "localhost",
    qdrant_port: int = 6333,
    qdrant_api_key: Optional[str] = None,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """查詢用戶輸入的意圖"""

    # 連接 Qdrant
    if qdrant_api_key:
        client = QdrantClient(host=qdrant_host, port=qdrant_port, api_key=qdrant_api_key)
    else:
        client = QdrantClient(host=qdrant_host, port=qdrant_port)

    # 獲取 embedding
    embedding_service = get_embedding_service()
    if embedding_service:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        embedding = loop.run_until_complete(embedding_service.generate_embedding(user_query))
    else:
        embedding = generate_mock_embedding(user_query)

    # 搜尋 - 使用 query_points
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=embedding,
        limit=top_k,
        with_payload=True,
    ).points

    # 整理結果
    output = []
    for r in results:
        output.append(
            {
                "intent_name": r.payload.get("intent_name"),
                "description": r.payload.get("description"),
                "priority": r.payload.get("priority"),
                "action_strategy": r.payload.get("action_strategy"),
                "score": r.score,
                "example": r.payload.get("example_text"),
            }
        )

    return output


async def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="OrchestratorIntentRAG 同步工具")
    parser.add_argument(
        "--json-path",
        type=Path,
        default=DEFAULT_JSON_PATH,
        help=f"JSON 配置文件路徑 (預設: {DEFAULT_JSON_PATH})",
    )
    parser.add_argument("--host", default=os.getenv("QDRANT_HOST", "localhost"), help="Qdrant 主機")
    parser.add_argument(
        "--port", type=int, default=int(os.getenv("QDRANT_PORT", "6333")), help="Qdrant 端口"
    )
    parser.add_argument("--api-key", default=os.getenv("QDRANT_API_KEY"), help="Qdrant API Key")
    parser.add_argument(
        "--recreate", action="store_true", help="重新創建 Collection（會刪除舊數據）"
    )
    parser.add_argument("--query", type=str, help="查詢模式：輸入查詢文本進行測試")
    parser.add_argument("--top-k", type=int, default=3, help="返回前 K 個結果")

    args = parser.parse_args()

    # 查詢模式
    if args.query:
        results = query_intent(
            args.query,
            qdrant_host=args.host,
            qdrant_port=args.port,
            qdrant_api_key=args.api_key,
            top_k=args.top_k,
        )

        print(f"\n查詢: {args.query}")
        print("=" * 60)
        for i, r in enumerate(results, 1):
            print(f"{i}. {r['intent_name']} (score: {r['score']:.3f})")
            print(f"   策略: {r['action_strategy']}")
            print(f"   示例: {r['example']}")
            print()

        return

    # 同步模式
    if not args.json_path.exists():
        logger.error(f"配置文件不存在: {args.json_path}")
        sys.exit(1)

    success = await sync_to_qdrant(
        json_path=args.json_path,
        qdrant_host=args.host,
        qdrant_port=args.port,
        qdrant_api_key=args.api_key,
        recreate_collection=args.recreate,
    )

    if success:
        logger.info("同步成功！")
    else:
        logger.error("同步失敗！")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
