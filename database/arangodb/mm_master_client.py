# -*- coding: utf-8 -*-
"""
Data-Agent-JP mm_master ArangoDB Client

mm_master Collection 的 CRUD 操作

建立日期: 2026-02-10
建立人: Daniel Chung
最後修改日期: 2026-02-10
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from database.arangodb.client import ArangoDBClient

logger = logging.getLogger(__name__)

COLLECTION_NAME = "mm_master"


@dataclass
class ItemDocument:
    """料號文件"""

    item_no: str
    location_count: int = 0
    total_stock: int = 0
    item_name: Optional[str] = None
    category: Optional[str] = None
    spec: Optional[str] = None
    unit: Optional[str] = None
    last_updated: Optional[str] = None

    def to_doc(self) -> Dict[str, Any]:
        return {
            "_key": f"ITEM_{self.item_no}",
            "type": "item",
            "item_no": self.item_no,
            "location_count": self.location_count,
            "total_stock": self.total_stock,
            "item_name": self.item_name,
            "category": self.category,
            "spec": self.spec,
            "unit": self.unit,
            "last_updated": self.last_updated or datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def from_doc(cls, doc: Dict[str, Any]) -> "ItemDocument":
        return cls(
            item_no=doc.get("item_no", ""),
            location_count=doc.get("location_count", 0),
            total_stock=doc.get("total_stock", 0),
            item_name=doc.get("item_name"),
            category=doc.get("category"),
            spec=doc.get("spec"),
            unit=doc.get("unit"),
            last_updated=doc.get("last_updated"),
        )


@dataclass
class WarehouseDocument:
    """倉庫文件"""

    warehouse_no: str
    record_count: int = 0
    distinct_items: int = 0
    total_stock: int = 0
    warehouse_name: Optional[str] = None
    location: Optional[str] = None
    capacity: Optional[int] = None
    last_updated: Optional[str] = None

    def to_doc(self) -> Dict[str, Any]:
        return {
            "_key": f"WH_{self.warehouse_no}",
            "type": "warehouse",
            "warehouse_no": self.warehouse_no,
            "record_count": self.record_count,
            "distinct_items": self.distinct_items,
            "total_stock": self.total_stock,
            "warehouse_name": self.warehouse_name,
            "location": self.location,
            "capacity": self.capacity,
            "last_updated": self.last_updated or datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def from_doc(cls, doc: Dict[str, Any]) -> "WarehouseDocument":
        return cls(
            warehouse_no=doc.get("warehouse_no", ""),
            record_count=doc.get("record_count", 0),
            distinct_items=doc.get("distinct_items", 0),
            total_stock=doc.get("total_stock", 0),
            warehouse_name=doc.get("warehouse_name"),
            location=doc.get("location"),
            capacity=doc.get("capacity"),
            last_updated=doc.get("last_updated"),
        )


@dataclass
class WorkstationDocument:
    """工作站文件"""

    workstation_id: str
    record_count: int = 0
    total_good_in: float = 0.0
    total_good_out: float = 0.0
    total_scrap: int = 0
    total_rework_in: int = 0
    total_rework_out: int = 0
    total_wip: float = 0.0
    yield_rate: float = 0.0
    workstation_name: Optional[str] = None
    line: Optional[str] = None
    last_updated: Optional[str] = None

    def to_doc(self) -> Dict[str, Any]:
        return {
            "_key": f"WS_{self.workstation_id}",
            "type": "workstation",
            "workstation_id": self.workstation_id,
            "record_count": self.record_count,
            "total_good_in": self.total_good_in,
            "total_good_out": self.total_good_out,
            "total_scrap": self.total_scrap,
            "total_rework_in": self.total_rework_in,
            "total_rework_out": self.total_rework_out,
            "total_wip": self.total_wip,
            "yield_rate": self.yield_rate,
            "workstation_name": self.workstation_name,
            "line": self.line,
            "last_updated": self.last_updated or datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def from_doc(cls, doc: Dict[str, Any]) -> "WorkstationDocument":
        return cls(
            workstation_id=doc.get("workstation_id", ""),
            record_count=doc.get("record_count", 0),
            total_good_in=doc.get("total_good_in", 0.0),
            total_good_out=doc.get("total_good_out", 0.0),
            total_scrap=doc.get("total_scrap", 0),
            total_rework_in=doc.get("total_rework_in", 0),
            total_rework_out=doc.get("total_rework_out", 0),
            total_wip=doc.get("total_wip", 0.0),
            yield_rate=doc.get("yield_rate", 0.0),
            workstation_name=doc.get("workstation_name"),
            line=doc.get("line"),
            last_updated=doc.get("last_updated"),
        )


class MMMasterClient:
    """
    mm_master Collection Client

    提供 Item、Warehouse、Workstation 的 CRUD 操作
    """

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 Client

        Args:
            client: ArangoDB Client（可選，若未提供則自動建立）
        """
        self._client = client
        self._collection = None

    @property
    def client(self) -> ArangoDBClient:
        """取得 ArangoDB Client"""
        if self._client is None:
            self._client = ArangoDBClient()
        return self._client

    @property
    def collection(self):
        """取得 Collection"""
        if self._collection is None:
            db = self.client.db
            if not db.has_collection(COLLECTION_NAME):
                db.create_collection(COLLECTION_NAME)
            self._collection = db.collection(COLLECTION_NAME)
        return self._collection

    def ensure_indexes(self):
        """建立索引"""
        try:
            self.collection.add_index({"type": "hash", "fields": ["item_no"]})
            self.collection.add_index({"type": "hash", "fields": ["warehouse_no"]})
            self.collection.add_index({"type": "hash", "fields": ["workstation_id"]})
            self.collection.add_index({"type": "hash", "fields": ["type"]})
            logger.info(f"Indexes ensured for {COLLECTION_NAME}")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

    def upsert_item(self, item: ItemDocument) -> bool:
        """新增或更新料號"""
        try:
            doc = item.to_doc()
            self.collection.update(doc)
            logger.debug(f"Upserted item: {item.item_no}")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert item {item.item_no}: {e}")
            return False

    def upsert_warehouse(self, warehouse: WarehouseDocument) -> bool:
        """新增或更新倉庫"""
        try:
            doc = warehouse.to_doc()
            self.collection.update(doc)
            logger.debug(f"Upserted warehouse: {warehouse.warehouse_no}")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert warehouse {warehouse.warehouse_no}: {e}")
            return False

    def upsert_workstation(self, workstation: WorkstationDocument) -> bool:
        """新增或更新工作站"""
        try:
            doc = workstation.to_doc()
            self.collection.update(doc)
            logger.debug(f"Upserted workstation: {workstation.workstation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert workstation {workstation.workstation_id}: {e}")
            return False

    def bulk_upsert_items(self, items: List[ItemDocument]) -> Dict[str, int]:
        """批量新增或更新料號"""
        success = 0
        failed = 0
        docs = [item.to_doc() for item in items]
        try:
            self.collection.import_bulk(docs)
            success = len(docs)
            logger.info(f"Bulk upserted {success} items")
        except Exception as e:
            logger.error(f"Bulk upsert items failed: {e}")
            failed = len(docs)
        return {"success": success, "failed": failed}

    def bulk_upsert_warehouses(self, warehouses: List[WarehouseDocument]) -> Dict[str, int]:
        """批量新增或更新倉庫"""
        success = 0
        failed = 0
        docs = [wh.to_doc() for wh in warehouses]
        try:
            self.collection.import_bulk(docs)
            success = len(docs)
            logger.info(f"Bulk upserted {success} warehouses")
        except Exception as e:
            logger.error(f"Bulk upsert warehouses failed: {e}")
            failed = len(docs)
        return {"success": success, "failed": failed}

    def bulk_upsert_workstations(self, workstations: List[WorkstationDocument]) -> Dict[str, int]:
        """批量新增或更新工作站"""
        success = 0
        failed = 0
        docs = [ws.to_doc() for ws in workstations]
        try:
            self.collection.import_bulk(docs)
            success = len(docs)
            logger.info(f"Bulk upserted {success} workstations")
        except Exception as e:
            logger.error(f"Bulk upsert workstations failed: {e}")
            failed = len(docs)
        return {"success": success, "failed": failed}

    def get_item(self, item_no: str) -> Optional[ItemDocument]:
        """取得料號"""
        try:
            doc = self.collection.get(f"ITEM_{item_no}")
            return ItemDocument.from_doc(doc) if doc else None
        except Exception as e:
            logger.debug(f"Item not found: {item_no}")
            return None

    def get_warehouse(self, warehouse_no: str) -> Optional[WarehouseDocument]:
        """取得倉庫"""
        try:
            doc = self.collection.get(f"WH_{warehouse_no}")
            return WarehouseDocument.from_doc(doc) if doc else None
        except Exception as e:
            logger.debug(f"Warehouse not found: {warehouse_no}")
            return None

    def get_workstation(self, workstation_id: str) -> Optional[WorkstationDocument]:
        """取得工作站"""
        try:
            doc = self.collection.get(f"WS_{workstation_id}")
            return WorkstationDocument.from_doc(doc) if doc else None
        except Exception as e:
            logger.debug(f"Workstation not found: {workstation_id}")
            return None

    def get_all_items(self, limit: int = 1000, offset: int = 0) -> List[ItemDocument]:
        """取得所有料號"""
        try:
            cursor = self.client.db.aql.execute(
                f"""
                FOR doc IN {COLLECTION_NAME}
                FILTER doc.type == 'item'
                LIMIT @limit OFFSET @offset
                RETURN doc
                """,
                bind_vars={"limit": limit, "offset": offset},
            )
            return [ItemDocument.from_doc(doc) for doc in cursor]
        except Exception as e:
            logger.error(f"Failed to get all items: {e}")
            return []

    def get_all_warehouses(self, limit: int = 500, offset: int = 0) -> List[WarehouseDocument]:
        """取得所有倉庫"""
        try:
            cursor = self.client.db.aql.execute(
                f"""
                FOR doc IN {COLLECTION_NAME}
                FILTER doc.type == 'warehouse'
                LIMIT @limit OFFSET @offset
                RETURN doc
                """,
                bind_vars={"limit": limit, "offset": offset},
            )
            return [WarehouseDocument.from_doc(doc) for doc in cursor]
        except Exception as e:
            logger.error(f"Failed to get all warehouses: {e}")
            return []

    def get_all_workstations(self, limit: int = 500, offset: int = 0) -> List[WorkstationDocument]:
        """取得所有工作站"""
        try:
            cursor = self.client.db.aql.execute(
                f"""
                FOR doc IN {COLLECTION_NAME}
                FILTER doc.type == 'workstation'
                LIMIT @limit OFFSET @offset
                RETURN doc
                """,
                bind_vars={"limit": limit, "offset": offset},
            )
            return [WorkstationDocument.from_doc(doc) for doc in cursor]
        except Exception as e:
            logger.error(f"Failed to get all workstations: {e}")
            return []

    def validate_item(self, item_no: str) -> tuple[bool, Optional[ItemDocument]]:
        """驗證料號是否存在"""
        item = self.get_item(item_no)
        return item is not None, item

    def validate_warehouse(self, warehouse_no: str) -> tuple[bool, Optional[WarehouseDocument]]:
        """驗證倉庫是否存在"""
        warehouse = self.get_warehouse(warehouse_no)
        return warehouse is not None, warehouse

    def validate_workstation(
        self, workstation_id: str
    ) -> tuple[bool, Optional[WorkstationDocument]]:
        """驗證工作站是否存在"""
        workstation = self.get_workstation(workstation_id)
        return workstation is not None, workstation

    def count_by_type(self) -> Dict[str, int]:
        """取得各類型文件數量"""
        try:
            cursor = self.client.db.aql.execute(
                f"""
                FOR doc IN {COLLECTION_NAME}
                COLLECT type = doc.type WITH COUNT INTO count
                RETURN {{"type": type, "count": count}}
                """
            )
            return {r["type"]: r["count"] for r in cursor}
        except Exception as e:
            logger.error(f"Failed to count by type: {e}")
            return {}

    def delete_all(self) -> int:
        """刪除所有文件（危險操作）"""
        try:
            cursor = self.client.db.aql.execute(
                f"FOR doc IN {COLLECTION_NAME} REMOVE doc IN {COLLECTION_NAME}"
            )
            return cursor.statistics().get("writesExecuted", 0)
        except Exception as e:
            logger.error(f"Failed to delete all: {e}")
            return 0

    def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        try:
            stats = self.count_by_type()
            return {
                "status": "healthy",
                "collection": COLLECTION_NAME,
                "counts": stats,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# Singleton instance
_mm_master_client: Optional[MMMasterClient] = None


def get_mm_master_client() -> MMMasterClient:
    """取得 mm_master Client Singleton"""
    global _mm_master_client
    if _mm_master_client is None:
        _mm_master_client = MMMasterClient()
    return _mm_master_client
