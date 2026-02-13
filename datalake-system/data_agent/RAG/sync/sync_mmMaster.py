#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_mmMaster.py

Master Data 同步腳本

功能：
- 從 JSON 檔案同步到 ArangoDB (mm_master)
- 從 JSON 檔案同步到 Qdrant (mmMasterRAG)
- 支援全量同步和增量同步
- 記錄同步狀態

使用方法：
    python sync_mmMaster.py --full      # 全量同步
    python sync_mmMaster.py --delta     # 增量同步
    python sync_mmMaster.py --arangodb  # 只同步 ArangoDB
    python sync_mmMaster.py --qdrant    # 只同步 Qdrant

建立日期: 2026-02-10
建立人: Daniel Chung
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("sync_mmMaster")


class SyncStats:
    """同步統計"""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.end_time: Optional[datetime] = None
        self.items_sync: int = 0
        self.warehouses_sync: int = 0
        self.workstations_sync: int = 0
        self.items_vectors: int = 0
        self.warehouses_vectors: int = 0
        self.workstations_vectors: int = 0
        self.errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (self.end_time - self.start_time).total_seconds()
            if self.end_time
            else None,
            "items": {
                "documents": self.items_sync,
                "vectors": self.items_vectors,
            },
            "warehouses": {
                "documents": self.warehouses_sync,
                "vectors": self.warehouses_vectors,
            },
            "workstations": {
                "documents": self.workstations_sync,
                "vectors": self.workstations_vectors,
            },
            "total_documents": self.items_sync + self.warehouses_sync + self.workstations_sync,
            "total_vectors": self.items_vectors
            + self.warehouses_vectors
            + self.workstations_vectors,
            "errors": self.errors,
        }


class MasterDataSync:
    """Master Data 同步器"""

    def __init__(
        self,
        metadata_path: str = None,
        embedding_model=None,
    ):
        """
        初始化同步器

        Args:
            metadata_path: Master Data 檔案路徑
            embedding_model: 向量化模型（需有 encode 方法）
        """
        # 更新 metadata_path 以適應新的目錄結構
        # script_dir = data_agent/RAG/sync/
        # 需要找到 datalake-system/metadata/
        if metadata_path is None:
            script_dir = Path(__file__).resolve().parent
            datalake_root = script_dir.parent.parent.parent
            metadata_path = datalake_root / "metadata"

        self.metadata_path = Path(metadata_path)
        self.embedding_model = embedding_model
        self.stats = SyncStats()

    def load_json(self, filename: str) -> Dict[str, Any]:
        """載入 JSON 檔案"""
        filepath = self.metadata_path / filename
        logger.info(f"Loading: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def sync_arangodb(self, recreate: bool = False) -> Dict[str, int]:
        """
        同步到 ArangoDB

        Args:
            recreate: 是否重新建立 Collection

        Returns:
            Dict: 同步統計
        """
        from database.arangodb.mm_master_client import (
            get_mm_master_client,
            ItemDocument,
            WarehouseDocument,
            WorkstationDocument,
        )

        logger.info("Syncing to ArangoDB...")

        try:
            client = get_mm_master_client()

            if recreate:
                logger.info("Recreating ArangoDB collection...")
                db = client.client.db
                collection_name = "mm_master"
                if db.has_collection(collection_name):
                    db.delete_collection(collection_name)
                db.create_collection(collection_name)
                client._collection = None

            client.ensure_indexes()

            items_result = self._sync_items(client)
            warehouses_result = self._sync_warehouses(client)
            workstations_result = self._sync_workstations(client)

            return {
                "items": items_result,
                "warehouses": warehouses_result,
                "workstations": workstations_result,
            }

        except Exception as e:
            logger.error(f"ArangoDB sync failed: {e}")
            self.stats.errors.append(f"ArangoDB: {str(e)}")
            return {"items": {}, "warehouses": {}, "workstations": {}}

    def _sync_items(self, client) -> Dict[str, int]:
        """同步料號到 ArangoDB"""
        data = self.load_json("item_master.json")

        items = []
        for item_data in data.get("items", []):
            item = ItemDocument(
                item_no=item_data.get("item_no", ""),
                location_count=item_data.get("location_count", 0),
                total_stock=item_data.get("total_stock", 0),
            )
            items.append(item)

        if items:
            result = client.bulk_upsert_items(items)
            self.stats.items_sync = result.get("success", 0)
            logger.info(f"Synced {self.stats.items_sync} items to ArangoDB")

        return {"success": self.stats.items_sync, "failed": len(items) - self.stats.items_sync}

    def _sync_warehouses(self, client) -> Dict[str, int]:
        """同步倉庫到 ArangoDB"""
        data = self.load_json("warehouse_master.json")

        warehouses = []
        for wh_data in data.get("warehouses", []):
            warehouse = WarehouseDocument(
                warehouse_no=wh_data.get("warehouse_no", ""),
                record_count=wh_data.get("record_count", 0),
                distinct_items=wh_data.get("distinct_items", 0),
                total_stock=wh_data.get("total_stock", 0),
            )
            warehouses.append(warehouse)

        if warehouses:
            result = client.bulk_upsert_warehouses(warehouses)
            self.stats.warehouses_sync = result.get("success", 0)
            logger.info(f"Synced {self.stats.warehouses_sync} warehouses to ArangoDB")

        return {
            "success": self.stats.warehouses_sync,
            "failed": len(warehouses) - self.stats.warehouses_sync,
        }

    def _sync_workstations(self, client) -> Dict[str, int]:
        """同步工作站到 ArangoDB"""
        data = self.load_json("workstation_master.json")

        workstations = []
        for ws_data in data.get("workstations", []):
            workstation = WorkstationDocument(
                workstation_id=ws_data.get("workstation_id", ""),
                record_count=ws_data.get("record_count", 0),
                total_good_in=ws_data.get("total_good_in", 0.0),
                total_good_out=ws_data.get("total_good_out", 0.0),
                total_scrap=ws_data.get("total_scrap", 0),
                total_rework_in=ws_data.get("total_rework_in", 0),
                total_rework_out=ws_data.get("total_rework_out", 0),
                total_wip=ws_data.get("total_wip", 0.0),
                yield_rate=ws_data.get("yield_rate", 0.0),
            )
            workstations.append(workstation)

        if workstations:
            result = client.bulk_upsert_workstations(workstations)
            self.stats.workstations_sync = result.get("success", 0)
            logger.info(f"Synced {self.stats.workstations_sync} workstations to ArangoDB")

        return {
            "success": self.stats.workstations_sync,
            "failed": len(workstations) - self.stats.workstations_sync,
        }

    def sync_qdrant(self, recreate: bool = False) -> Dict[str, int]:
        """
        同步到 Qdrant

        Args:
            recreate: 是否重新建立 Collection

        Returns:
            Dict: 同步統計
        """
        from database.qdrant.mm_master_rag_client import (
            get_mm_master_rag_client,
            ItemEmbedding,
            WarehouseEmbedding,
            WorkstationEmbedding,
        )

        logger.info("Syncing to Qdrant...")

        if self.embedding_model is None:
            logger.warning("No embedding model provided, skipping Qdrant sync")
            return {"items": {}, "warehouses": {}, "workstations": {}}

        try:
            client = get_mm_master_rag_client()
            client.ensure_collection(recreate=recreate)

            items_result = self._sync_item_vectors(client)
            warehouses_result = self._sync_warehouse_vectors(client)
            workstations_result = self._sync_workstation_vectors(client)

            return {
                "items": items_result,
                "warehouses": warehouses_result,
                "workstations": workstations_result,
            }

        except Exception as e:
            logger.error(f"Qdrant sync failed: {e}")
            self.stats.errors.append(f"Qdrant: {str(e)}")
            return {"items": {}, "warehouses": {}, "workstations": {}}

    def _sync_item_vectors(self, client) -> Dict[str, int]:
        """同步料號向量到 Qdrant"""
        data = self.load_json("item_master.json")

        embeddings = []
        for item_data in data.get("items", []):
            item = ItemEmbedding(
                item_no=item_data.get("item_no", ""),
                item_name=item_data.get("item_name"),
                spec=item_data.get("spec"),
                searchable_text=f"{item_data.get('item_name', '')} {item_data.get('spec', '')} {item_data.get('item_no', '')}",
            )
            embeddings.append(item)

        if embeddings:
            texts = [e.searchable_text for e in embeddings]
            vectors = self.embedding_model.encode(texts).tolist()

            count = client.upsert_items(embeddings, vectors)
            self.stats.items_vectors = count
            logger.info(f"Synced {count} item vectors to Qdrant")

        return {
            "success": self.stats.items_vectors,
            "failed": len(embeddings) - self.stats.items_vectors,
        }

    def _sync_warehouse_vectors(self, client) -> Dict[str, int]:
        """同步倉庫向量到 Qdrant"""
        data = self.load_json("warehouse_master.json")

        embeddings = []
        for wh_data in data.get("warehouses", []):
            warehouse = WarehouseEmbedding(
                warehouse_no=wh_data.get("warehouse_no", ""),
                warehouse_name=wh_data.get("warehouse_name"),
                location=wh_data.get("location"),
                searchable_text=f"{wh_data.get('warehouse_name', '')} {wh_data.get('location', '')} {wh_data.get('warehouse_no', '')}",
            )
            embeddings.append(warehouse)

        if embeddings:
            texts = [e.searchable_text for e in embeddings]
            vectors = self.embedding_model.encode(texts).tolist()

            count = client.upsert_warehouses(embeddings, vectors)
            self.stats.warehouses_vectors = count
            logger.info(f"Synced {count} warehouse vectors to Qdrant")

        return {
            "success": self.stats.warehouses_vectors,
            "failed": len(embeddings) - self.stats.warehouses_vectors,
        }

    def _sync_workstation_vectors(self, client) -> Dict[str, int]:
        """同步工作站向量到 Qdrant"""
        data = self.load_json("workstation_master.json")

        embeddings = []
        for ws_data in data.get("workstations", []):
            workstation = WorkstationEmbedding(
                workstation_id=ws_data.get("workstation_id", ""),
                workstation_name=ws_data.get("workstation_name"),
                line=ws_data.get("line"),
                searchable_text=f"{ws_data.get('workstation_name', '')} {ws_data.get('line', '')} {ws_data.get('workstation_id', '')}",
            )
            embeddings.append(workstation)

        if embeddings:
            texts = [e.searchable_text for e in embeddings]
            vectors = self.embedding_model.encode(texts).tolist()

            count = client.upsert_workstations(embeddings, vectors)
            self.stats.workstations_vectors = count
            logger.info(f"Synced {count} workstation vectors to Qdrant")

        return {
            "success": self.stats.workstations_vectors,
            "failed": len(embeddings) - self.stats.workstations_vectors,
        }

    def sync_all(self, recreate: bool = False) -> Dict[str, Any]:
        """
        同步到所有儲存

        Args:
            recreate: 是否重新建立

        Returns:
            Dict: 同步結果
        """
        logger.info("Starting full sync...")

        arangodb_result = self.sync_arangodb(recreate=recreate)
        qdrant_result = self.sync_qdrant(recreate=recreate)

        self.stats.end_time = datetime.now(timezone.utc)

        result = {
            "status": "completed" if not self.stats.errors else "completed_with_errors",
            "arangodb": arangodb_result,
            "qdrant": qdrant_result,
            "statistics": self.stats.to_dict(),
        }

        logger.info(f"Sync completed: {result['status']}")
        logger.info(
            f"Total documents: {self.stats.items_sync + self.stats.warehouses_sync + self.stats.workstations_sync}"
        )
        logger.info(
            f"Total vectors: {self.stats.items_vectors + self.stats.warehouses_vectors + self.stats.workstations_vectors}"
        )

        return result

    def log_sync_status(self, filepath: str = None):
        """記錄同步狀態"""
        if filepath is None:
            filepath = self.metadata_path / "sync_status.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.stats.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"Sync status logged to: {filepath}")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="Master Data Sync Tool")
    parser.add_argument("--full", action="store_true", help="Full sync (ArangoDB + Qdrant)")
    parser.add_argument("--delta", action="store_true", help="Delta sync (only changes)")
    parser.add_argument("--arangodb", action="store_true", help="Only sync ArangoDB")
    parser.add_argument("--qdrant", action="store_true", help="Only sync Qdrant")
    parser.add_argument("--recreate", action="store_true", help="Recreate collections")
    parser.add_argument("--embedding-model", type=str, default=None, help="Embedding model name")

    args = parser.parse_args()

    if not any([args.full, args.delta, args.arangodb, args.qdrant]):
        args.full = True

    logger.info(f"Arguments: {args}")

    embedding_model = None
    if args.embedding_model:
        try:
            import sentence_transformers

            embedding_model = sentence_transformers.SentenceTransformer(args.embedding_model)
            logger.info(f"Loaded embedding model: {args.embedding_model}")
        except ImportError:
            logger.warning("sentence-transformers not installed, skipping vector sync")

    sync = MasterDataSync(embedding_model=embedding_model)

    try:
        if args.arangodb:
            result = sync.sync_arangodb(recreate=args.recreate)
        elif args.qdrant:
            result = sync.sync_qdrant(recreate=args.recreate)
        else:
            result = sync.sync_all(recreate=args.recreate)

        sync.log_sync_status()

        print("\n" + "=" * 50)
        print("SYNC RESULT")
        print("=" * 50)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("=" * 50)

        return 0 if result["status"] == "completed" else 1

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
