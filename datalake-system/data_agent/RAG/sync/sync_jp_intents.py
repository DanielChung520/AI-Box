#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 代碼功能說明: 同步 JP Intents 到 Qdrant 向量資料庫 (jp_intents collection)
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

"""
同步 JP Intent 定義到 Qdrant

讀取 metadata/systems/tiptop_jp/intents.json (16 intents)，
使用 EmbeddingManager (qwen3-embedding, 4096 dim) 生成向量，
上傳到 Qdrant collection `jp_intents`。

用法:
    python data_agent/RAG/sync/sync_jp_intents.py --recreate
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

# 確保 datalake-system 在 sys.path 中
_DATALAKE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_DATALAKE_ROOT))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from data_agent.services.schema_driven_query.embedding_manager import EmbeddingManager

logger = structlog.get_logger(__name__)

# === 常量 ===
COLLECTION_NAME = "jp_intents"
QDRANT_URL = "http://localhost:6333"
EMBEDDING_DIMENSION = 4096
METADATA_DIR = _DATALAKE_ROOT / "metadata" / "systems" / "tiptop_jp"


def load_json_file(filepath: Path) -> Dict[str, Any]:
    """載入 JSON 檔案"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def derive_source_tables(
    intent_filters: List[str],
    bindings: Dict[str, Any],
) -> List[str]:
    """
    從 bindings.json 推導 intent 的 source_tables

    Args:
        intent_filters: intent 的 input.filters 列表 (概念名稱)
        bindings: bindings.json 中的 bindings 字典

    Returns:
        去重後的 source table 列表
    """
    tables: set[str] = set()
    for concept_name in intent_filters:
        binding = bindings.get(concept_name, {})
        # 優先使用 DUCKDB binding
        duckdb_binding = binding.get("DUCKDB", {})
        if duckdb_binding:
            table = duckdb_binding.get("table", "")
            if table:
                tables.add(table)
        else:
            # Fallback: JP_TIPTOP_ERP binding
            jp_binding = binding.get("JP_TIPTOP_ERP", {})
            table = jp_binding.get("table", "")
            if table:
                tables.add(table)
    return sorted(tables)


async def embed_intents(
    intents: Dict[str, Dict[str, Any]],
) -> List[tuple[str, List[float]]]:
    """
    使用 EmbeddingManager 為每個 intent 的 description 生成嵌入向量

    Args:
        intents: intents.json 的 intents 字典

    Returns:
        [(intent_name, embedding), ...]
    """
    manager = EmbeddingManager(config={
        "primary": {
            "model": "qwen3-embedding:latest",
            "endpoint": "http://localhost:11434",
            "timeout": 60,
        }
    })
    results: List[tuple[str, List[float]]] = []

    for intent_name, intent_data in intents.items():
        description = intent_data.get("description", "")
        text = f"{intent_name}: {description}"
        logger.info("生成嵌入向量", intent=intent_name, text=text)

        embedding = await manager.embed(text)
        assert len(embedding) == EMBEDDING_DIMENSION, (
            f"Embedding 維度不符: 預期 {EMBEDDING_DIMENSION}, 實際 {len(embedding)}"
        )
        results.append((intent_name, embedding))

    return results


def create_collection(client: QdrantClient, recreate: bool = False) -> None:
    """建立或重建 Qdrant collection"""
    if recreate:
        try:
            client.delete_collection(COLLECTION_NAME)
            logger.info("已刪除舊 collection", collection=COLLECTION_NAME)
        except Exception:
            pass

    try:
        client.get_collection(COLLECTION_NAME)
        logger.info("Collection 已存在", collection=COLLECTION_NAME)
        return
    except Exception:
        pass

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIMENSION,
            distance=Distance.COSINE,
        ),
    )
    logger.info(
        "已建立 collection",
        collection=COLLECTION_NAME,
        dimension=EMBEDDING_DIMENSION,
    )


def upload_points(
    client: QdrantClient,
    intents: Dict[str, Dict[str, Any]],
    embeddings: List[tuple[str, List[float]]],
    bindings_data: Dict[str, Any],
) -> int:
    """
    上傳 PointStructs 到 Qdrant

    Args:
        client: Qdrant 客戶端
        intents: intents.json 的 intents 字典
        embeddings: [(intent_name, embedding), ...]
        bindings_data: bindings.json 全部資料

    Returns:
        上傳的點數量
    """
    bindings = bindings_data.get("bindings", {})
    points: List[PointStruct] = []

    for idx, (intent_name, embedding) in enumerate(embeddings):
        intent_data = intents[intent_name]
        description = intent_data.get("description", "")
        input_filters = intent_data.get("input", {}).get("filters", [])
        mart_table: Optional[str] = intent_data.get("mart_table")
        source_tables = derive_source_tables(input_filters, bindings)

        payload: Dict[str, Any] = {
            "intent_name": intent_name,
            "description": description,
            "input_filters": input_filters,
            "source_tables": source_tables,
        }
        if mart_table is not None:
            payload["mart_table"] = mart_table

        points.append(
            PointStruct(
                id=idx,
                vector=embedding,
                payload=payload,
            )
        )

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    logger.info("已上傳 points", count=len(points), collection=COLLECTION_NAME)
    return len(points)


async def main(recreate: bool = False) -> int:
    """主程式"""
    logger.info("=" * 60)
    logger.info("JP Intents Sync Tool")
    logger.info("=" * 60)

    # 載入 JSON 檔案
    intents_path = METADATA_DIR / "intents.json"
    bindings_path = METADATA_DIR / "bindings.json"

    if not intents_path.exists():
        logger.error("Intents 檔案不存在", path=str(intents_path))
        return 1

    if not bindings_path.exists():
        logger.error("Bindings 檔案不存在", path=str(bindings_path))
        return 1

    intents_data = load_json_file(intents_path)
    bindings_data = load_json_file(bindings_path)

    intents = intents_data.get("intents", {})
    intent_count = len(intents)
    logger.info("載入 intents", count=intent_count, path=str(intents_path))

    # 生成嵌入向量
    logger.info("開始生成嵌入向量（使用 qwen3-embedding, 4096 dim）...")
    embeddings = await embed_intents(intents)
    logger.info("嵌入向量生成完成", count=len(embeddings))

    # 建立/重建 Qdrant collection
    client = QdrantClient(url=QDRANT_URL)
    create_collection(client, recreate=recreate)

    # 上傳 points
    uploaded = upload_points(client, intents, embeddings, bindings_data)

    logger.info("=" * 60)
    logger.info(
        "JP Intents Sync 完成",
        collection=COLLECTION_NAME,
        uploaded=uploaded,
        dimension=EMBEDDING_DIMENSION,
    )
    logger.info("=" * 60)

    return 0


def parse_args() -> argparse.Namespace:
    """解析命令列參數"""
    parser = argparse.ArgumentParser(
        description="同步 JP Intent 定義到 Qdrant (jp_intents collection)"
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="刪除並重建 collection（預設：僅新增/更新）",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(asyncio.run(main(recreate=args.recreate)))
