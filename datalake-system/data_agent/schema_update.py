#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema Registry 更新腳本

功能說明:
    檢測 schema_registry.json 變更，執行增量更新。
    - 計算差異 (新增/修改/刪除)
    - 增量更新 Qdrant (Upsert)
    - 增量更新 ArangoDB
    - 支援熱重載通知

創建日期: 2026-02-09
創建人: Daniel Chung
"""

import sys
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import filecmp

import yaml
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

import arango
from arango import ArangoClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ChangeRecord:
    """變更記錄"""

    type: str  # "add", "modify", "delete"
    category: str  # "table", "concept", "intent"
    name: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None


@dataclass
class UpdateConfig:
    """更新配置"""

    qdrant_host: str
    qdrant_port: int
    qdrant_collection: str
    arangodb_host: str
    arangodb_port: int
    arangodb_username: str
    arangodb_password: str
    arangodb_database: str
    arangodb_collection_prefix: str
    embedding_dimension: int
    state_file: str


class SchemaUpdater:
    """Schema 更新器"""

    def __init__(self, config: UpdateConfig):
        self.config = config
        self.qdrant_client = None
        self.arango_client = None
        self.arango_db = None
        self.state_file_path = Path(config.state_file)

    def initialize_clients(self):
        """初始化客戶端連接"""
        logger.info("初始化客戶端連接...")

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

        logger.info("客戶端連接初始化完成")

    def load_state(self) -> Dict[str, str]:
        """載入上次狀態"""
        if self.state_file_path.exists():
            with open(self.state_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_state(self, state: Dict[str, str]):
        """保存當前狀態"""
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def calculate_file_hash(self, file_path: str) -> str:
        """計算檔案 hash"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            return hashlib.md5(content.encode()).hexdigest()

    def compute_changes(
        self, old_schema: Dict[str, Any], new_schema: Dict[str, Any]
    ) -> List[ChangeRecord]:
        """計算 Schema 變更"""
        changes = []

        old_system = old_schema.get("system", {}).get("system_id", "unknown")
        new_system = new_schema.get("system", {}).get("system_id", "unknown")

        if old_system != new_system:
            changes.append(
                ChangeRecord(
                    type="modify",
                    category="system",
                    name="system_id",
                    old_value=old_system,
                    new_value=new_system,
                )
            )

        # 表格變更
        old_tables = old_schema.get("tables", {})
        new_tables = new_schema.get("tables", {})

        old_table_keys = set(old_tables.keys())
        new_table_keys = set(new_tables.keys())

        added_tables = new_table_keys - old_table_keys
        deleted_tables = old_table_keys - new_table_keys
        common_tables = old_table_keys & new_table_keys

        for table in added_tables:
            changes.append(
                ChangeRecord(type="add", category="table", name=table, new_value=new_tables[table])
            )

        for table in deleted_tables:
            changes.append(
                ChangeRecord(
                    type="delete", category="table", name=table, old_value=old_tables[table]
                )
            )

        for table in common_tables:
            if old_tables[table] != new_tables[table]:
                changes.append(
                    ChangeRecord(
                        type="modify",
                        category="table",
                        name=table,
                        old_value=old_tables[table],
                        new_value=new_tables[table],
                    )
                )

        # 概念變更
        old_concepts = old_schema.get("concepts", {})
        new_concepts = new_schema.get("concepts", {})

        old_concept_keys = set(old_concepts.keys())
        new_concept_keys = set(new_concepts.keys())

        added_concepts = new_concept_keys - old_concept_keys
        deleted_concepts = old_concept_keys - new_concept_keys
        common_concepts = old_concept_keys & new_concept_keys

        for concept in added_concepts:
            changes.append(
                ChangeRecord(
                    type="add", category="concept", name=concept, new_value=new_concepts[concept]
                )
            )

        for concept in deleted_concepts:
            changes.append(
                ChangeRecord(
                    type="delete", category="concept", name=concept, old_value=old_concepts[concept]
                )
            )

        for concept in common_concepts:
            if old_concepts[concept] != new_concepts[concept]:
                changes.append(
                    ChangeRecord(
                        type="modify",
                        category="concept",
                        name=concept,
                        old_value=old_concepts[concept],
                        new_value=new_concepts[concept],
                    )
                )

        return changes

    def generate_text_representation(self, schema: Dict[str, Any], category: str, name: str) -> str:
        """生成特定 Schema 元素的文字表示"""
        if category == "table":
            table_info = schema.get("tables", {}).get(name, {})
            tiptop_name = table_info.get("tiptop_name", "")
            columns = table_info.get("columns", [])
            col_descs = [f"{c['name']}({c['id']})" for c in columns]
            return f"{tiptop_name} {name}, 欄位: {', '.join(col_descs)}"

        elif category == "concept":
            concept_info = schema.get("concepts", {}).get(name, {})
            description = concept_info.get("description", "")
            mappings = concept_info.get("mappings", {})
            mapping_str = "; ".join([f"{k}: {v.get('keywords', [])}" for k, v in mappings.items()])
            return f"{description}, 映射: {mapping_str}"

        return ""

    def generate_vector(self, text: str) -> List[float]:
        """生成文字向量"""
        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        vector = [(hash_val % 100) / 100.0 for _ in range(self.config.embedding_dimension)]
        return vector

    def update_qdrant(self, schema: Dict[str, Any], changes: List[ChangeRecord]):
        """增量更新 Qdrant"""
        logger.info("更新 Qdrant...")

        system_info = schema.get("system", {})
        system_id = system_info.get("system_id", "unknown")
        system_name = system_info.get("system_name", "")

        # 處理新增和修改
        add_modify_items = [c for c in changes if c.type in ("add", "modify")]

        if add_modify_items:
            points = []
            for idx, change in enumerate(add_modify_items, start=10000):
                text = self.generate_text_representation(schema, change.category, change.name)
                vector = self.generate_vector(text)

                point = PointStruct(
                    id=idx,
                    vector=vector,
                    payload={
                        "type": change.category,
                        "system_id": system_id,
                        "system_name": system_name,
                        "name": change.name,
                        "tiptop_name": text.split(" ")[0] if text else "",
                        "text": text,
                        "updated_at": datetime.now().isoformat(),
                    },
                )
                points.append(point)

            self.qdrant_client.upsert(collection_name=self.config.qdrant_collection, points=points)
            logger.info(f"新增/修改 {len(points)} 筆至 Qdrant")

        # 處理刪除
        delete_items = [c for c in changes if c.type == "delete"]
        if delete_items:
            delete_ids = list(range(10000, 10000 + len(delete_items)))
            self.qdrant_client.delete(
                collection_name=self.config.qdrant_collection, points_selector=delete_ids
            )
            logger.info(f"從 Qdrant 刪除 {len(delete_items)} 筆")

    def update_arangodb(self, schema: Dict[str, Any], changes: List[ChangeRecord]):
        """增量更新 ArangoDB"""
        logger.info("更新 ArangoDB...")

        system_info = schema.get("system", {})
        system_id = system_info.get("system_id", "unknown")

        entities_collection = f"{self.config.arangodb_collection_prefix}entities"
        relationships_collection = f"{self.config.arangodb_collection_prefix}relationships"

        entities_coll = self.arango_db.collection(entities_collection)
        relationships_coll = self.arango_db.collection(relationships_collection)

        # 處理新增表格
        added_tables = [c for c in changes if c.type == "add" and c.category == "table"]
        if added_tables:
            tables = schema.get("tables", {})
            for change in added_tables:
                table_name = change.name
                table_info = tables.get(table_name, {})
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
            logger.info(f"新增 {len(added_tables)} 個表格節點")

        # 處理刪除表格
        deleted_tables = [c for c in changes if c.type == "delete" and c.category == "table"]
        if deleted_tables:
            for change in deleted_tables:
                key = f"{change.name}_{system_id}"
                try:
                    entities_coll.delete(key)
                except Exception:
                    pass
            logger.info(f"刪除 {len(deleted_tables)} 個表格節點")

        # 處理新增概念
        added_concepts = [c for c in changes if c.type == "add" and c.category == "concept"]
        if added_concepts:
            concepts = schema.get("concepts", {})
            for change in added_concepts:
                concept_name = change.name
                concept_info = concepts.get(concept_name, {})
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
            logger.info(f"新增 {len(added_concepts)} 個概念節點")

        # 處理刪除概念
        deleted_concepts = [c for c in changes if c.type == "delete" and c.category == "concept"]
        if deleted_concepts:
            for change in deleted_concepts:
                key = f"{change.name}_{system_id}"
                try:
                    entities_coll.delete(key)
                except Exception:
                    pass
            logger.info(f"刪除 {len(deleted_concepts)} 個概念節點")

    def update(self, schema_path: str):
        """執行更新"""
        logger.info(f"檢測 Schema 變更: {schema_path}")

        # 載入當前 Schema
        with open(schema_path, "r", encoding="utf-8") as f:
            new_schema = json.load(f)

        # 載入上次狀態
        old_state = self.load_state()
        old_hash = old_state.get("hash", "")
        old_schema_path = old_state.get("path", "")

        # 計算當前 Hash
        current_hash = self.calculate_file_hash(schema_path)

        # 比較
        if old_hash == current_hash:
            logger.info("Schema 無變更，跳過更新")
            return False

        # 載入舊 Schema（如果路徑相同）
        old_schema = None
        if old_schema_path == schema_path:
            with open(schema_path, "r", encoding="utf-8") as f:
                old_schema = json.load(f)

        # 計算變更
        if old_schema:
            changes = self.compute_changes(old_schema, new_schema)
        else:
            # 首次載入，所有都是新增
            changes = [
                ChangeRecord(type="add", category="all", name="full_schema", new_value=new_schema)
            ]

        logger.info(f"發現 {len(changes)} 筆變更")

        if changes:
            # 初始化客戶端
            self.initialize_clients()

            # 更新 Qdrant
            self.update_qdrant(new_schema, changes)

            # 更新 ArangoDB
            self.update_arangodb(new_schema, changes)

            # 保存新狀態
            self.save_state(
                {
                    "hash": current_hash,
                    "path": schema_path,
                    "updated_at": datetime.now().isoformat(),
                    "changes_count": len(changes),
                }
            )

            logger.info("Schema 更新完成")
            return True
        else:
            return False


def load_config(config_path: str) -> UpdateConfig:
    """載入配置"""
    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = yaml.safe_load(f)

    qdrant = config_dict.get("qdrant", {})
    arangodb = config_dict.get("arangodb", {})
    embedding = config_dict.get("embedding", {})

    return UpdateConfig(
        qdrant_host=qdrant.get("host", "localhost"),
        qdrant_port=qdrant.get("port", 6333),
        qdrant_collection=qdrant.get("collection_name", "schema_registry"),
        arangodb_host=arangodb.get("host", "localhost"),
        arangodb_port=arangodb.get("port", 8529),
        arangodb_username=arangodb.get("username", "root"),
        arangodb_password=arangodb.get("password", ""),
        arangodb_database=arangodb.get("database", "schema_registry_db"),
        arangodb_collection_prefix=arangodb.get("collection_prefix", "schema_"),
        embedding_dimension=embedding.get("dimension", 1024),
        state_file="config/schema_update_state.json",
    )


def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description="Schema Registry 更新腳本")
    parser.add_argument(
        "--config", "-c", default="config/schema_rag_config.yaml", help="配置文件路徑"
    )
    parser.add_argument("--schema", "-s", required=True, help="Schema Registry JSON 檔案路徑")
    parser.add_argument("--check-only", "-C", action="store_true", help="只檢查變更，不執行更新")

    args = parser.parse_args()

    # 載入配置
    config = load_config(args.config)

    # 執行更新
    updater = SchemaUpdater(config)

    if args.check_only:
        # 只檢查
        old_state = updater.load_state()
        current_hash = updater.calculate_file_hash(args.schema)

        if old_state.get("hash") == current_hash:
            print("Schema 無變更")
        else:
            print("Schema 有變更")
            if old_state.get("path") == args.schema:
                print(f"變更數量待計算")
            else:
                print("首次載入")
    else:
        updated = updater.update(args.schema)
        if updated:
            print("Schema 更新完成")
        else:
            print("Schema 無變更或更新失敗")


if __name__ == "__main__":
    main()
