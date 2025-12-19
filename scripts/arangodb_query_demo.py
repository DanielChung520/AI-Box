# 代碼功能說明: ArangoDB 查詢示範腳本
# 創建日期: 2025-11-25 22:58 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 22:58 (UTC+8)

"""執行常用的知識圖譜查詢以驗證 SDK 功能。"""

from __future__ import annotations

import argparse
import json
from typing import List

import structlog

from database.arangodb import ArangoDBClient, load_arangodb_settings
from database.arangodb import queries as kg_queries

LOGGER = structlog.get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Demo queries against the AI-Box knowledge graph.")
    parser.add_argument(
        "--vertex", required=True, help="起始頂點 ID（例如 entities/agent_planning）"
    )
    parser.add_argument(
        "--relation-types",
        nargs="*",
        default=None,
        help="篩選的關係 type（可傳多個）",
    )
    parser.add_argument("--limit", type=int, default=10, help="查詢結果上限")
    parser.add_argument(
        "--config",
        default=None,
        help="自訂 config.json 路徑，預設自動尋找",
    )
    return parser.parse_args()


def pretty_print(title: str, payload: List[dict]) -> None:
    LOGGER.info(title, rows=len(payload))
    print(json.dumps(payload, ensure_ascii=False, indent=2))  # noqa: T201


def main() -> None:
    args = parse_args()
    settings = load_arangodb_settings(args.config) if args.config else load_arangodb_settings()
    client = ArangoDBClient(settings=settings)

    neighbors = kg_queries.fetch_neighbors(
        client,
        args.vertex,
        relation_types=args.relation_types,
        limit=args.limit,
    )
    pretty_print("neighbors", neighbors)

    subgraph = kg_queries.fetch_subgraph(
        client,
        args.vertex,
        max_depth=2,
        limit=args.limit,
    )
    pretty_print("subgraph", subgraph)

    same_type_filters = {}
    if args.relation_types:
        same_type_filters["type"] = args.relation_types
    entities = kg_queries.filter_entities(client, filters=same_type_filters, limit=args.limit)
    pretty_print("entity_scan", entities)

    client.close()


if __name__ == "__main__":
    main()
