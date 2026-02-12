#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema Registry 上傳腳本

功能說明:
    解析 schema_registry.json 檔案，將 Schema 定義上傳至 Qdrant 和 ArangoDB。
    - Qdrant: 存儲表格描述、概念定義、向量化檢索
    - ArangoDB: 存儲實體節點和關係邊，支援圖遍歷查詢

創建日期: 2026-02-09
創建人: Daniel Chung
"""

import sys
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import yaml
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

from arango.client import ArangoClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class UploadConfig:
    """上傳配置"""

    qdrant_host: str
    qdrant_port: int
    qdrant_collection: str
    arangodb_host: str
    arangodb_port: int
    arangodb_username: str
    arangodb_password: str
    arangodb_database: str
    arangodb_collection_prefix: str
    embedding_model: str
    embedding_dimension: int


class SchemaUploader:
    """Schema 上傳器"""

    def __init__(self, config: UploadConfig):
        self.config = config
        self.qdrant_client = None
        self.arango_client = None
        self.arango_db = None

    def initialize_clients(self):
        """初始化客戶端連接"""
        logger.info("初始化客戶端連接...")

        # Qdrant 連接
        self.qdrant_client = QdrantClient(
            host=self.config.qdrant_host, port=self.config.qdrant_port
        )

        # ArangoDB 連接
        host_url = f"http://{self.config.arangodb_host}:{self.config.arangodb_port}"
        self.arango_client = ArangoClient(hosts=host_url)
        self.arango_db = self.arango_client.db(
            self.config.arangodb_database,
            username=self.config.arangodb_username,
            password=self.config.arangodb_password,
        )

        self.arango_db = self.arango_client.db(
            self.config.arangodb_database,
            username=self.config.arangodb_username,
            password=self.config.arangodb_password,
        )

        logger.info("客戶端連接初始化完成")

    def ensure_collections(self):
        """確保必要的 Collection 存在"""
        logger.info("確保 Collection 存在...")

        # Qdrant Collection
        try:
            self.qdrant_client.get_collection(self.config.qdrant_collection)
            logger.info(f"Qdrant Collection '{self.config.qdrant_collection}' 已存在")
        except Exception:
            logger.info(f"創建 Qdrant Collection '{self.config.qdrant_collection}'")
            self.qdrant_client.create_collection(
                collection_name=self.config.qdrant_collection,
                vectors_config=VectorParams(
                    size=self.config.embedding_dimension, distance=Distance.COSINE
                ),
            )

        # ArangoDB Collections
        entities_collection = f"{self.config.arangodb_collection_prefix}entities"
        relationships_collection = f"{self.config.arangodb_collection_prefix}relationships"

        # entities collection
        if not self.arango_db.has_collection(entities_collection):
            self.arango_db.create_collection(entities_collection)
            logger.info(f"創建 ArangoDB Collection '{entities_collection}'")
        else:
            logger.info(f"ArangoDB Collection '{entities_collection}' 已存在")

        # relationships collection
        if not self.arango_db.has_collection(relationships_collection):
            self.arango_db.create_collection(relationships_collection)
            logger.info(f"創建 ArangoDB Collection '{relationships_collection}'")
        else:
            logger.info(f"ArangoDB Collection '{relationships_collection}' 已存在")

    def load_schema(self, schema_path: str) -> Dict[str, Any]:
        """載入 Schema Registry JSON"""
        logger.info(f"載入 Schema Registry: {schema_path}")

        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        system_info = schema.get("system", {})
        logger.info(f"System: {system_info.get('system_id', 'unknown')}")

        return schema

    def generate_text_representation(self, schema: Dict[str, Any]) -> List[Dict[str, str]]:
        """生成 Schema 的文字表示，用於向量化"""
        texts = []

        system_info = schema.get("system", {})
        system_id = system_info.get("system_id", "unknown")
        system_name = system_info.get("system_name", "")

        # 表格描述
        tables = schema.get("tables", {})
        for table_name, table_info in tables.items():
            tiptop_name = table_info.get("tiptop_name", "")
            columns = table_info.get("columns", [])

            col_descs = []
            for col in columns:
                col_desc = f"{col['name']}({col['id']})"
                if col.get("description"):
                    col_desc += f" - {col['description']}"
                col_descs.append(col_desc)

            text = f"{tiptop_name} {table_name}, 欄位: {', '.join(col_descs)}"
            texts.append(
                {
                    "type": "table",
                    "system_id": system_id,
                    "system_name": system_name,
                    "name": table_name,
                    "tiptop_name": tiptop_name,
                    "text": text,
                }
            )

        # 概念描述
        concepts = schema.get("concepts", {})
        for concept_name, concept_info in concepts.items():
            description = concept_info.get("description", "")
            mappings = concept_info.get("mappings", {})

            mapping_descs = []
            for key, mapping in mappings.items():
                keywords = mapping.get("keywords", [])
                target_field = mapping.get("target_field", "")
                mapping_descs.append(f"{key}: {', '.join(keywords)} -> {target_field}")

            text = f"{description}, 映射: {'; '.join(mapping_descs)}"
            texts.append(
                {
                    "type": "concept",
                    "system_id": system_id,
                    "system_name": system_name,
                    "name": concept_name,
                    "text": text,
                }
            )

        # 意圖模板描述
        intents = schema.get("intent_templates", {})
        for intent_name, intent_info in intents.items():
            description = intent_info.get("description", "")
            primary_table = intent_info.get("primary_table", "")
            examples = intent_info.get("examples", [])

            text = f"{description}, 主要表格: {primary_table}, 範例: {'; '.join(examples[:3])}"
            texts.append(
                {
                    "type": "intent",
                    "system_id": system_id,
                    "system_name": system_name,
                    "name": intent_name,
                    "text": text,
                }
            )

        return texts

    def generate_vectors(self, texts: List[Dict[str, str]]) -> List[List[float]]:
        """生成文字的向量化"""
        # TODO: 集成 Embedding 服務
        # 這裡使用簡化的向量化，未來替換為 Ollama/nomic-embed-text

        # 模擬: 使用文字長度和字符作為特徵
        import hashlib

        vectors = []
        for item in texts:
            text = item.get("text", "")
            # 生成固定維度的向量
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            vector = [(hash_val % 100) / 100.0 for _ in range(self.config.embedding_dimension)]
            vectors.append(vector)

        return vectors

    def upload_to_qdrant(self, texts: List[Dict[str, str]], vectors: List[List[float]]):
        """上傳至 Qdrant"""
        logger.info(f"上傳至 Qdrant: {len(texts)} 筆")

        points = []
        for idx, (item, vector) in enumerate(zip(texts, vectors)):
            point = PointStruct(
                id=idx,
                vector=vector,
                payload={
                    "type": item["type"],
                    "system_id": item["system_id"],
                    "system_name": item["system_id"],
                    "name": item["name"],
                    "tiptop_name": item.get("tiptop_name", ""),
                    "text": item["text"],
                },
            )
            points.append(point)

        self.qdrant_client.upsert(collection_name=self.config.qdrant_collection, points=points)

        logger.info(f"已上傳 {len(points)} 筆至 Qdrant")

    def upload_to_arangodb(self, schema: Dict[str, Any]):
        """上傳至 ArangoDB"""
        logger.info("上傳至 ArangoDB...")

        system_info = schema.get("system", {})
        system_id = system_info.get("system_id", "unknown")
        tables = schema.get("tables", {})
        concepts = schema.get("concepts", {})
        relationships = schema.get("table_relationships", {})

        entities_collection = f"{self.config.arangodb_collection_prefix}entities"
        relationships_collection = f"{self.config.arangodb_collection_prefix}relationships"

        entities_coll = self.arango_db.collection(entities_collection)
        relationships_coll = self.arango_db.collection(relationships_collection)

        # 清空現有數據（可選：改為增量更新）
        entities_coll.truncate()
        relationships_coll.truncate()
        logger.info("已清空現有數據")

        # 創建表格節點
        table_keys = {}
        for table_name, table_info in tables.items():
            key = f"{table_name}_{system_id}"
            doc = {
                "_key": key,
                "type": "table",
                "system_id": system_id,
                "name": table_name,
                "tiptop_name": table_info.get("tiptop_name", ""),
                "columns": table_info.get("columns", []),
            }
            entities_coll.insert(doc)
            table_keys[table_name] = key
            logger.debug(f"創建表格節點: {key}")

        # 創建概念節點
        for concept_name, concept_info in concepts.items():
            key = f"{concept_name}_{system_id}"
            doc = {
                "_key": key,
                "type": "concept",
                "system_id": system_id,
                "name": concept_name,
                "description": concept_info.get("description", ""),
                "mappings": concept_info.get("mappings", {}),
            }
            entities_coll.insert(doc)
            logger.debug(f"創建概念節點: {key}")

        # 創建關係邊
        edge_count = 0
        for from_field, to_field in relationships.items():
            from_parts = from_field.split(".")
            to_parts = to_field.split(".")

            if len(from_parts) >= 2 and len(to_parts) >= 2:
                from_table = from_parts[0]
                from_col = from_parts[1]
                to_table = to_parts[0]
                to_col = to_parts[1]

                from_key = table_keys.get(from_table)
                to_key = table_keys.get(to_table)

                if from_key and to_key:
                    edge_doc = {
                        "_from": f"{entities_collection}/{from_key}",
                        "_to": f"{entities_collection}/{to_key}",
                        "type": "references",
                        "from_field": from_col,
                        "to_field": to_col,
                        "system_id": system_id,
                    }
                    relationships_coll.insert(edge_doc)
                    edge_count += 1

        logger.info(f"已創建 {edge_count} 條關係邊")

    def upload(self, schema_path: str):
        """執行上傳"""
        logger.info(f"開始上傳 Schema: {schema_path}")

        # 初始化客戶端
        self.initialize_clients()

        # 確保 Collection 存在
        self.ensure_collections()

        # 載入 Schema
        schema = self.load_schema(schema_path)

        # 生成文字表示
        texts = self.generate_text_representation(schema)

        # 生成向量
        vectors = self.generate_vectors(texts)

        # 上傳至 Qdrant
        self.upload_to_qdrant(texts, vectors)

        # 上傳至 ArangoDB
        self.upload_to_arangodb(schema)

        logger.info("Schema 上傳完成")


def load_config(config_path: str) -> UploadConfig:
    """載入配置"""
    # 支援相對路徑
    if not os.path.isabs(config_path):
        base_dir = Path(__file__).parent.parent.parent / "datalake-system" / "metadata" / "config"
        full_path = base_dir / config_path
        if full_path.exists():
            config_path = str(full_path)
        else:
            cwd_config = Path.cwd() / "metadata" / "config" / config_path
            if cwd_config.exists():
                config_path = str(cwd_config)

    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = yaml.safe_load(f)

    qdrant = config_dict.get("qdrant", {})
    arangodb = config_dict.get("arangodb", {})
    embedding = config_dict.get("embedding", {})

    return UploadConfig(
        qdrant_host=qdrant.get("host", "localhost"),
        qdrant_port=qdrant.get("port", 6333),
        qdrant_collection=qdrant.get("collection_name", "schema_registry"),
        arangodb_host=arangodb.get("host", "localhost"),
        arangodb_port=arangodb.get("port", 8529),
        arangodb_username=arangodb.get("username", "root"),
        arangodb_password=arangodb.get("password", ""),
        arangodb_database=arangodb.get("database", "schema_registry_db"),
        arangodb_collection_prefix=arangodb.get("collection_prefix", "schema_"),
        embedding_model=embedding.get("model", "nomic-embed-text:latest"),
        embedding_dimension=embedding.get("dimension", 1024),
    )


def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description="Schema Registry 上傳腳本")
    parser.add_argument(
        "--config", "-c", default="config/schema_rag_config.yaml", help="配置文件路徑"
    )
    parser.add_argument("--schema", "-s", required=True, help="Schema Registry JSON 檔案路徑")

    args = parser.parse_args()

    # 載入配置
    config = load_config(args.config)

    # 執行上傳
    uploader = SchemaUploader(config)
    uploader.upload(args.schema)


if __name__ == "__main__":
    main()
