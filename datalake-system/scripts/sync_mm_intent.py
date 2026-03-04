#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代碼功能說明: MMIntentsRAG 同步腳本
功能：將 MMIntentsRAG.json 同步到 Qdrant 向量庫
創建日期: 2026-02-27
創建人: Daniel Chung
最後修改日期: 2026-02-27
"""

import argparse
import json
import logging
import sys
import os
from pathlib import Path

# 將項目根目錄添加到 sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, List, Any, Optional

import numpy as np
from qdrant_client import QdrantClient

# 配置日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 配置
COLLECTION_NAME = "mm_intents_rag"
VECTOR_SIZE = 4096  # qwen3-embedding dimension
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))


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

    logger.info(f"配置版本: {config.get('version', 'unknown')}")
    logger.info(f"領域: {config.get('domain', 'unknown')}")

    # 解析意圖列表
    intents = config.get("intents", [])
    logger.info(f"意圖數量: {len(intents)}")

    # 統計示例數量
    total_examples = sum(len(intent.get("examples", [])) for intent in intents)
    logger.info(f"總共 {total_examples} 個示例")

    return config


async def sync_mm_intents(
    json_path: Path,
    recreate: bool = False,
    batch_size: int = 50,
) -> bool:
    """同步意圖數據到 Qdrant"""

    # 載入配置
    config = load_intent_config(json_path)
    intents = config.get("intents", [])

    if not intents:
        logger.error("沒有找到意圖配置")
        return False

    # 準備所有示例文本
    all_examples = []
    for intent in intents:
        intent_name = intent.get("intent_name", "")
        description = intent.get("description", "")
        examples = intent.get("examples", [])

        for example in examples:
            all_examples.append(
                {
                    "intent_name": intent_name,
                    "description": description,
                    "text": example,
                }
            )

    logger.info(f"總共 {len(all_examples)} 個示例需要向量化")

    # 向量化
    logger.info("開始向量化...")
    embedding_service = get_embedding_service()

    texts = [item["text"] for item in all_examples]
    embeddings = await get_embeddings_batch(texts, embedding_service)
    logger.info(f"向量化完成: {len(embeddings)} 個向量")

    # 準備 Points
    points = []
    for idx, (item, embedding) in enumerate(zip(all_examples, embeddings)):
        point = {
            "id": idx + 1,
            "vector": embedding,
            "payload": {
                "intent_name": item["intent_name"],
                "description": item["description"],
                "text": item["text"],
            },
        }
        points.append(point)

    logger.info(f"準備了 {len(points)} 個 Points")

    # 連接 Qdrant
    logger.info(f"連接 Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # 檢查 Collection 是否存在
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]

    if COLLECTION_NAME in collection_names:
        if recreate:
            logger.info(f"刪除舊 Collection: {COLLECTION_NAME}")
            client.delete_collection(collection_name=COLLECTION_NAME)
        else:
            logger.info(f"Collection {COLLECTION_NAME} 已存在，跳過上傳")
            return True

    # 創建 Collection
    logger.info(f"創建 Collection: {COLLECTION_NAME}")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "size": VECTOR_SIZE,
            "distance": "Cosine",
        },
    )

    # 上傳 Points
    logger.info(f"上傳 {len(points)} Points 到 Qdrant...")

    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch,
            wait=True,
        )
        logger.info(f"上傳進度: {i + len(batch)}/{len(points)}")

    # 驗證
    collection_info = client.get_collection(collection_name=COLLECTION_NAME)
    logger.info(f"同步完成！Collection: {COLLECTION_NAME}, Points: {collection_info.points_count}")

    return True


def main():
    parser = argparse.ArgumentParser(description="同步 MMIntentsRAG 到 Qdrant")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="刪除並重建 Collection",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="批量上傳大小 (預設: 50)",
    )
    parser.add_argument(
        "--json-path",
        type=str,
        default=None,
        help="JSON 檔案路徑",
    )

    args = parser.parse_args()

    # 確定 JSON 路徑
    if args.json_path:
        json_path = Path(args.json_path)
    else:
        # 預設路徑
        json_path = Path(__file__).parent.parent / "data" / "MMIntentsRAG.json"

    if not json_path.exists():
        logger.error(f"JSON 檔案不存在: {json_path}")
        sys.exit(1)

    # 執行同步
    import asyncio

    success = asyncio.run(
        sync_mm_intents(json_path, recreate=args.recreate, batch_size=args.batch_size)
    )

    if success:
        logger.info("同步成功！")
    else:
        logger.error("同步失敗！")
        sys.exit(1)


if __name__ == "__main__":
    main()
