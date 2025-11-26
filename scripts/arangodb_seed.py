# 代碼功能說明: ArangoDB 知識圖譜匯入腳本
# 創建日期: 2025-11-25 22:58 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 22:58 (UTC+8)

"""根據 schema/seed 檔案建立或重置 ArangoDB 知識圖譜資料。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import structlog
import yaml  # type: ignore[import-untyped]

from databases.arangodb import (
    ArangoCollection,
    ArangoDBClient,
    ArangoGraph,
    load_arangodb_settings,
)
from databases.arangodb.settings import clear_arangodb_settings_cache

LOGGER = structlog.get_logger(__name__)
DEFAULT_DATASET_ROOT = Path(__file__).resolve().parents[1] / "datasets" / "arangodb"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed ArangoDB knowledge graph data.")
    parser.add_argument(
        "--seed-file",
        type=Path,
        default=DEFAULT_DATASET_ROOT / "seed_data.json",
        help="Seed JSON 檔案位置",
    )
    parser.add_argument(
        "--schema-file",
        type=Path,
        default=DEFAULT_DATASET_ROOT / "schema.yml",
        help="Schema YAML 檔案位置",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="自訂 config.json 路徑（若未提供則自動尋找）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="僅顯示將執行的操作，不實際寫入資料。",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="清空目標集合與圖後再匯入。",
    )
    return parser.parse_args()


def load_schema(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def load_seed_data(path: Path) -> Dict[str, List[Dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def ensure_collections(
    client: ArangoDBClient, schema: Dict[str, Any]
) -> Dict[str, ArangoCollection]:
    collections: Dict[str, ArangoCollection] = {}
    for name, cfg in schema.get("collections", {}).items():
        col_type = cfg.get("type", "document")
        collections[name] = ArangoCollection(
            client.get_or_create_collection(name, col_type)
        )
    return collections


def ensure_graph(client: ArangoDBClient, schema: Dict[str, Any]) -> ArangoGraph:
    graph_cfg = schema.get("graph", {})
    return ArangoGraph(
        client.get_or_create_graph(
            graph_cfg.get("name", "knowledge_graph"), graph_cfg.get("edge_definitions")
        )
    )


def reset_collections(collections: Dict[str, ArangoCollection], dry_run: bool) -> None:
    for name, collection in collections.items():
        if dry_run:
            LOGGER.info("dry_run_reset", collection=name)
        else:
            collection.truncate()
            LOGGER.info("collection_reset", collection=name)


def seed_entities(
    collection: ArangoCollection, entities: List[Dict[str, Any]], dry_run: bool
) -> None:
    if not entities:
        return
    if dry_run:
        LOGGER.info("dry_run_insert_entities", count=len(entities))
        return
    collection.insert(entities)
    LOGGER.info("entities_seeded", count=len(entities))


def seed_relations(
    graph: ArangoGraph, relations: List[Dict[str, Any]], dry_run: bool
) -> None:
    if not relations:
        return
    if dry_run:
        LOGGER.info("dry_run_insert_relations", count=len(relations))
        return
    for rel in relations:
        edge = {k: v for k, v in rel.items() if k not in {"_from", "_to"}}
        graph.insert_edge("relations", edge, rel["_from"], rel["_to"])
    LOGGER.info("relations_seeded", count=len(relations))


def main() -> None:
    args = parse_args()

    if args.config:
        clear_arangodb_settings_cache()
        settings = load_arangodb_settings(args.config, force_reload=True)
    else:
        settings = load_arangodb_settings()

    client = ArangoDBClient(settings=settings)
    schema = load_schema(args.schema_file)
    seed_payload = load_seed_data(args.seed_file)

    collections = ensure_collections(client, schema)
    graph = ensure_graph(client, schema)

    if args.reset:
        reset_collections(collections, args.dry_run)

    seed_entities(
        collections["entities"], seed_payload.get("entities", []), args.dry_run
    )
    seed_relations(graph, seed_payload.get("relations", []), args.dry_run)

    client.close()


if __name__ == "__main__":
    main()
