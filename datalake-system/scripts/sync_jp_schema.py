#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Data-Agent-JP Schema Sync 腳本
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

"""同步 JP Schema 到 Qdrant 和 ArangoDB"""

import json
import sys
import os
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from arango import ArangoClient


def load_json_file(filepath: str) -> dict:
    """載入 JSON 檔案"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_qdrant_client() -> QdrantClient:
    """獲取 Qdrant 客戶端"""
    return QdrantClient(host="localhost", port=6333)


def get_arangodb_client() -> ArangoClient:
    """獲取 ArangoDB 客戶端"""
    return ArangoClient()


def sync_to_qdrant(
    concepts_path: str,
    intents_path: str,
    collection_prefix: str = "jp_",
    system_id: str = "tiptop_jp",
):
    """同步到 Qdrant"""
    print("\n📦 同步到 Qdrant...")

    try:
        client = get_qdrant_client()
    except Exception as e:
        print(f"  ❌ Qdrant 連接失敗: {e}")
        return

    concepts_collection = f"{collection_prefix}concepts"
    intents_collection = f"{collection_prefix}intents"

    try:
        client.get_collection(collection_name=concepts_collection)
        print(f"  ✅ Collection 已存在: {concepts_collection}")
    except Exception:
        print(f"  📝 建立 Collection: {concepts_collection}")
        client.create_collection(
            collection_name=concepts_collection,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )

    try:
        client.get_collection(collection_name=intents_collection)
        print(f"  ✅ Collection 已存在: {intents_collection}")
    except Exception:
        print(f"  📝 建立 Collection: {intents_collection}")
        client.create_collection(
            collection_name=intents_collection,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )

    concepts_data = load_json_file(concepts_path)
    intents_data = load_json_file(intents_path)

    concepts = concepts_data.get("concepts", {})
    intents = intents_data.get("intents", {})

    import hashlib

    def generate_vector(text: str) -> list:
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(hash_val % 100) / 100.0 for _ in range(1024)]

    concept_points = []
    for idx, (name, concept) in enumerate(concepts.items()):
        description = concept.get("description", "")
        labels = concept.get("labels", [])
        text = f"{name}: {description}, 標籤: {', '.join(labels)}"
        concept_points.append(
            PointStruct(
                id=idx,
                vector=generate_vector(text),
                payload={
                    "type": "concept",
                    "system_id": system_id,
                    "name": name,
                    "description": description,
                    "labels": labels,
                    "text": text,
                },
            )
        )

    if concept_points:
        client.upsert(collection_name=concepts_collection, points=concept_points)
        print(f"  ✅ 上傳 {len(concept_points)} concepts")

    intent_points = []
    for idx, (name, intent) in enumerate(intents.items()):
        description = intent.get("description", "")
        text = f"{name}: {description}"
        intent_points.append(
            PointStruct(
                id=idx,
                vector=generate_vector(text),
                payload={
                    "type": "intent",
                    "system_id": system_id,
                    "name": name,
                    "description": description,
                    "text": text,
                },
            )
        )

    if intent_points:
        client.upsert(collection_name=intents_collection, points=intent_points)
        print(f"  ✅ 上傳 {len(intent_points)} intents")


def sync_to_arangodb(bindings_path: str, system_id: str = "tiptop_jp"):
    """同步到 ArangoDB"""
    print("\n📦 同步到 ArangoDB...")

    bindings_data = load_json_file(bindings_path)
    bindings = bindings_data.get("bindings", {})

    try:
        client = get_arangodb_client()
    except Exception as e:
        print(f"  ❌ ArangoDB 連接失敗: {e}")
        return

    db = client.db("ai_box_kg", username="root", password="ai_box_arangodb_password")

    bindings_collection_name = "jp_bindings"

    try:
        if not db.has_collection(bindings_collection_name):
            print(f"  📝 建立 Collection: {bindings_collection_name}")
            db.create_collection(bindings_collection_name)
    except Exception as e:
        print(f"  ⚠️ Collection 檢查失敗 (可能需要權限): {e}")
        print(f"  📝 嘗試建立 Collection...")
        try:
            db.create_collection(bindings_collection_name)
        except Exception as e2:
            print(f"  ❌ 建立 Collection 失敗: {e2}")
            return

    collection = db.collection(bindings_collection_name)
    collection.truncate()

    docs = []
    for concept_name, datasource_bindings in bindings.items():
        for datasource, binding in datasource_bindings.items():
            doc = {
                "_key": f"{concept_name}_{datasource}",
                "concept_name": concept_name,
                "datasource": datasource,
                "table": binding.get("table", ""),
                "column": binding.get("column", ""),
                "aggregation": binding.get("aggregation", ""),
                "operator": binding.get("operator", "="),
                "system_id": system_id,
            }
            docs.append(doc)

    if docs:
        collection.insert_many(docs)
        print(f"  ✅ 上傳 {len(docs)} bindings")


def main():
    """主程式"""
    script_dir = Path(__file__).resolve().parent
    metadata_dir = script_dir.parent / "metadata" / "systems" / "tiptop_jp"

    concepts_path = metadata_dir / "concepts.json"
    intents_path = metadata_dir / "intents.json"
    bindings_path = metadata_dir / "bindings.json"

    print("=" * 60)
    print("  Data-Agent-JP Schema Sync Tool")
    print("=" * 60)
    print(f"\n📁 Metadata 目錄: {metadata_dir}")

    if not concepts_path.exists():
        print(f"  ❌ Concepts 檔案不存在: {concepts_path}")
        return 1

    if not intents_path.exists():
        print(f"  ❌ Intents 檔案不存在: {intents_path}")
        return 1

    if not bindings_path.exists():
        print(f"  ❌ Bindings 檔案不存在: {bindings_path}")
        return 1

    sync_to_qdrant(str(concepts_path), str(intents_path), system_id="tiptop_jp")
    sync_to_arangodb(str(bindings_path), system_id="tiptop_jp")

    print("\n" + "=" * 60)
    print("  ✅ Schema Sync 完成!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
