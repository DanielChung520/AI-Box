# -*- coding: utf-8 -*-
"""
Data-Agent-JP Master Data Loader

載入並驗證 Master Data 檔案（item_master, warehouse_master, workstation_master）

建立日期: 2026-02-10
建立人: Daniel Chung
最後修改日期: 2026-02-10
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .exceptions import (
    ItemNotFoundError,
    WarehouseNotFoundError,
    WorkstationNotFoundError,
    MasterDataLoadError,
)

logger = logging.getLogger(__name__)


@dataclass
class ItemMaster:
    """料號主檔資料結構"""

    item_no: str
    location_count: int = 0
    total_stock: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_no": self.item_no,
            "location_count": self.location_count,
            "total_stock": self.total_stock,
        }


@dataclass
class WarehouseMaster:
    """倉庫主檔資料結構"""

    warehouse_no: str
    record_count: int = 0
    distinct_items: int = 0
    total_stock: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "warehouse_no": self.warehouse_no,
            "record_count": self.record_count,
            "distinct_items": self.distinct_items,
            "total_stock": self.total_stock,
        }


@dataclass
class WorkstationMaster:
    """工作站主檔資料結構"""

    workstation_id: str
    record_count: int = 0
    total_good_in: float = 0.0
    total_good_out: float = 0.0
    total_scrap: int = 0
    total_rework_in: int = 0
    total_rework_out: int = 0
    total_wip: float = 0.0
    yield_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workstation_id": self.workstation_id,
            "record_count": self.record_count,
            "total_good_in": self.total_good_in,
            "total_good_out": self.total_good_out,
            "total_scrap": self.total_scrap,
            "total_rework_in": self.total_rework_in,
            "total_rework_out": self.total_rework_out,
            "total_wip": self.total_wip,
            "yield_rate": self.yield_rate,
        }


@dataclass
class MasterDataStats:
    """Master Data 統計資訊"""

    total_items: int = 0
    total_warehouses: int = 0
    total_workstations: int = 0
    items_path: str = ""
    warehouses_path: str = ""
    workstations_path: str = ""
    last_loaded: Optional[str] = None


class MasterDataLoader:
    """
    Master Data 載入器

    功能：
    - 從 JSON 檔案載入 Master Data
    - 提供 Entity Validation（料號、倉庫、工作站）
    - 支援快取機制
    """

    def __init__(
        self,
        base_path: str = None,
        reload_on_request: bool = False,
    ):
        """
        初始化 Master Data Loader

        Args:
            base_path: Master Data 檔案基礎路徑
            reload_on_request: 是否每次請求都重新載入（用於開發環境）
        """
        if base_path is None:
            # 預設路徑：datalake-system/metadata
            base_path = Path(__file__).parent.parent.parent.parent / "metadata"

        self.base_path = Path(base_path)
        self.reload_on_request = reload_on_request

        self._items: Dict[str, ItemMaster] = {}
        self._warehouses: Dict[str, WarehouseMaster] = {}
        self._workstations: Dict[str, WorkstationMaster] = {}
        self._stats: Optional[MasterDataStats] = None
        self._loaded = False

    def _load_item_master(self) -> Dict[str, ItemMaster]:
        """載入料號主檔"""
        items_path = self.base_path / "item_master.json"

        if not items_path.exists():
            logger.warning(f"Item master file not found: {items_path}")
            return {}

        try:
            with open(items_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            items = {}
            for item_data in data.get("items", []):
                item = ItemMaster(
                    item_no=item_data.get("item_no", ""),
                    location_count=item_data.get("location_count", 0),
                    total_stock=item_data.get("total_stock", 0),
                )
                items[item.item_no] = item

            logger.info(f"Loaded {len(items)} items from {items_path}")
            return items

        except Exception as e:
            logger.error(f"Failed to load item master: {e}")
            raise MasterDataLoadError(str(items_path), str(e))

    def _load_warehouse_master(self) -> Dict[str, WarehouseMaster]:
        """載入倉庫主檔"""
        warehouses_path = self.base_path / "warehouse_master.json"

        if not warehouses_path.exists():
            logger.warning(f"Warehouse master file not found: {warehouses_path}")
            return {}

        try:
            with open(warehouses_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            warehouses = {}
            for wh_data in data.get("warehouses", []):
                wh = WarehouseMaster(
                    warehouse_no=wh_data.get("warehouse_no", ""),
                    record_count=wh_data.get("record_count", 0),
                    distinct_items=wh_data.get("distinct_items", 0),
                    total_stock=wh_data.get("total_stock", 0),
                )
                warehouses[wh.warehouse_no] = wh

            logger.info(f"Loaded {len(warehouses)} warehouses from {warehouses_path}")
            return warehouses

        except Exception as e:
            logger.error(f"Failed to load warehouse master: {e}")
            raise MasterDataLoadError(str(warehouses_path), str(e))

    def _load_workstation_master(self) -> Dict[str, WorkstationMaster]:
        """載入工作站主檔"""
        workstations_path = self.base_path / "workstation_master.json"

        if not workstations_path.exists():
            logger.warning(f"Workstation master file not found: {workstations_path}")
            return {}

        try:
            with open(workstations_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            workstations = {}
            for ws_data in data.get("workstations", []):
                ws = WorkstationMaster(
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
                workstations[ws.workstation_id] = ws

            logger.info(f"Loaded {len(workstations)} workstations from {workstations_path}")
            return workstations

        except Exception as e:
            logger.error(f"Failed to load workstation master: {e}")
            raise MasterDataLoadError(str(workstations_path), str(e))

    def load_all(self) -> MasterDataStats:
        """
        載入所有 Master Data

        Returns:
            MasterDataStats: 統計資訊
        """
        self._items = self._load_item_master()
        self._warehouses = self._load_warehouse_master()
        self._workstations = self._load_workstation_master()

        self._stats = MasterDataStats(
            total_items=len(self._items),
            total_warehouses=len(self._warehouses),
            total_workstations=len(self._workstations),
            items_path=str(self.base_path / "item_master.json"),
            warehouses_path=str(self.base_path / "warehouse_master.json"),
            workstations_path=str(self.base_path / "workstation_master.json"),
            last_loaded=self._get_timestamp(),
        )

        self._loaded = True
        logger.info(
            f"Master Data loaded: "
            f"items={self._stats.total_items}, "
            f"warehouses={self._stats.total_warehouses}, "
            f"workstations={self._stats.total_workstations}"
        )

        return self._stats

    def ensure_loaded(self):
        """確保資料已載入"""
        if not self._loaded or self.reload_on_request:
            self.load_all()

    def validate_item(self, item_no: str) -> tuple[bool, Optional[ItemMaster], List[str]]:
        """
        驗證料號是否存在

        Args:
            item_no: 料號

        Returns:
            tuple: (是否存在, 料號資料, 建議清單)
        """
        self.ensure_loaded()

        # 精確比對
        if item_no in self._items:
            return True, self._items[item_no], []

        # 模糊比對建議
        suggestions = self._find_similar_items(item_no)
        return False, None, suggestions

    def validate_warehouse(
        self, warehouse_no: str
    ) -> tuple[bool, Optional[WarehouseMaster], List[str]]:
        """
        驗證倉庫代碼是否存在

        Args:
            warehouse_no: 倉庫代碼

        Returns:
            tuple: (是否存在, 倉庫資料, 建議清單)
        """
        self.ensure_loaded()

        # 精確比對
        if warehouse_no in self._warehouses:
            return True, self._warehouses[warehouse_no], []

        # 模糊比對建議
        suggestions = self._find_similar_warehouses(warehouse_no)
        return False, None, suggestions

    def validate_workstation(
        self, workstation_id: str
    ) -> tuple[bool, Optional[WorkstationMaster], List[str]]:
        """
        驗證工作站 ID 是否存在

        Args:
            workstation_id: 工作站 ID

        Returns:
            tuple: (是否存在, 工作站資料, 建議清單)
        """
        self.ensure_loaded()

        # 精確比對
        if workstation_id in self._workstations:
            return True, self._workstations[workstation_id], []

        # 模糊比對建議
        suggestions = self._find_similar_workstations(workstation_id)
        return False, None, suggestions

    def _find_similar_items(self, item_no: str, limit: int = 5) -> List[str]:
        """找出相似的料號建議"""
        suggestions = []
        item_no_lower = item_no.lower()

        for existing_item in self._items.keys():
            if item_no_lower in existing_item.lower() or existing_item.lower() in item_no_lower:
                suggestions.append(existing_item)
                if len(suggestions) >= limit:
                    break

        return suggestions[:limit]

    def _find_similar_warehouses(self, warehouse_no: str, limit: int = 5) -> List[str]:
        """找出相似的倉庫代碼建議"""
        suggestions = []
        warehouse_no_lower = warehouse_no.lower()

        for existing_wh in self._warehouses.keys():
            if (
                warehouse_no_lower in existing_wh.lower()
                or existing_wh.lower() in warehouse_no_lower
            ):
                suggestions.append(existing_wh)
                if len(suggestions) >= limit:
                    break

        return suggestions[:limit]

    def _find_similar_workstations(self, workstation_id: str, limit: int = 5) -> List[str]:
        """找出相似的工作站 ID 建議"""
        suggestions = []
        ws_id_lower = workstation_id.lower()

        for existing_ws in self._workstations.keys():
            if ws_id_lower in existing_ws.lower() or existing_ws.lower() in ws_id_lower:
                suggestions.append(existing_ws)
                if len(suggestions) >= limit:
                    break

        return suggestions[:limit]

    def get_item(self, item_no: str) -> Optional[ItemMaster]:
        """取得料號資料"""
        self.ensure_loaded()
        return self._items.get(item_no)

    def get_warehouse(self, warehouse_no: str) -> Optional[WarehouseMaster]:
        """取得倉庫資料"""
        self.ensure_loaded()
        return self._warehouses.get(warehouse_no)

    def get_workstation(self, workstation_id: str) -> Optional[WorkstationMaster]:
        """取得工作站資料"""
        self.ensure_loaded()
        return self._workstations.get(workstation_id)

    def get_all_items(self) -> List[ItemMaster]:
        """取得所有料號"""
        self.ensure_loaded()
        return list(self._items.values())

    def get_all_warehouses(self) -> List[WarehouseMaster]:
        """取得所有倉庫"""
        self.ensure_loaded()
        return list(self._warehouses.values())

    def get_all_workstations(self) -> List[WorkstationMaster]:
        """取得所有工作站"""
        self.ensure_loaded()
        return list(self._workstations.values())

    def get_stats(self) -> MasterDataStats:
        """取得統計資訊"""
        self.ensure_loaded()
        return self._stats

    def _get_timestamp(self) -> str:
        """取得目前時間戳"""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    def reload(self):
        """重新載入所有資料"""
        self._loaded = False
        self.load_all()


# Singleton instance for global use
_master_loader: Optional[MasterDataLoader] = None


def get_master_loader(
    base_path: str = None,
    reload_on_request: bool = False,
) -> MasterDataLoader:
    """
    取得 Master Data Loader Singleton

    Args:
        base_path: Master Data 基礎路徑
        reload_on_request: 是否每次重新載入

    Returns:
        MasterDataLoader: Loader 實例
    """
    global _master_loader

    if _master_loader is None or reload_on_request:
        _master_loader = MasterDataLoader(
            base_path=base_path,
            reload_on_request=reload_on_request,
        )
        _master_loader.load_all()

    return _master_loader


def validate_entity(
    entity_type: str,
    entity_value: str,
    base_path: str = None,
) -> tuple[bool, Any, List[str]]:
    """
    驗證 Entity（便利函式）

    Args:
        entity_type: 實體類型 ("item", "warehouse", "workstation")
        entity_value: 實體值
        base_path: Master Data 基礎路徑

    Returns:
        tuple: (是否有效, 實體資料, 建議清單)
    """
    loader = get_master_loader(base_path=base_path)

    if entity_type == "item":
        return loader.validate_item(entity_value)
    elif entity_type == "warehouse":
        return loader.validate_warehouse(entity_value)
    elif entity_type == "workstation":
        return loader.validate_workstation(entity_value)
    else:
        raise ValueError(f"Unknown entity type: {entity_type}")


# =============================================================================
# masterRAG 整合：語意搜尋驗證
# =============================================================================


class MasterRAGValidator:
    """
    masterRAG 驗證器

    功能：
    - 先嘗試精確比對（master_loader）
    - 失敗時使用 masterRAG 語意搜尋
    - 返回語意相似的候選項目
    """

    def __init__(self, base_path: str = None):
        self._master_loader = MasterDataLoader(base_path=base_path)
        self._master_loader.load_all()
        self._embedding_model = None

    def _get_embedding_model(self):
        """取得 embedding model（Lazy loading）"""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Loaded embedding model: all-MiniLM-L6-v2")
            except ImportError:
                logger.warning(
                    "sentence-transformers not installed, falling back to exact match only"
                )
                return None
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
                return None
        return self._embedding_model

    def _get_master_rag_client(self):
        """取得 masterRAG client"""
        try:
            from database.qdrant.mm_master_rag_client import get_mm_master_rag_client

            return get_mm_master_rag_client()
        except Exception as e:
            logger.warning(f"Failed to get masterRAG client: {e}")
            return None

    def validate_item(
        self, item_no: str, use_semantic: bool = True
    ) -> tuple[bool, Optional[ItemMaster], List[str]]:
        """
        驗證料號（先精確，失敗時語意搜尋）

        Args:
            item_no: 料號
            use_semantic: 是否使用語意搜尋 fallback

        Returns:
            tuple: (是否有效, 料號資料, 建議清單)
        """
        # Step 1: 精確比對
        is_valid, data, suggestions = self._master_loader.validate_item(item_no)
        if is_valid:
            return is_valid, data, suggestions

        # Step 2: 失敗時使用語意搜尋
        if use_semantic:
            return self._semantic_search_item(item_no)

        return False, None, suggestions

    def validate_warehouse(
        self, warehouse_no: str, use_semantic: bool = True
    ) -> tuple[bool, Optional[WarehouseMaster], List[str]]:
        """
        驗證倉庫（先精確，失敗時語意搜尋）

        Args:
            warehouse_no: 倉庫代碼
            use_semantic: 是否使用語意搜尋 fallback

        Returns:
            tuple: (是否有效, 倉庫資料, 建議清單)
        """
        # Step 1: 精確比對
        is_valid, data, suggestions = self._master_loader.validate_warehouse(warehouse_no)
        if is_valid:
            return is_valid, data, suggestions

        # Step 2: 失敗時使用語意搜尋
        if use_semantic:
            return self._semantic_search_warehouse(warehouse_no)

        return False, None, suggestions

    def validate_workstation(
        self, workstation_id: str, use_semantic: bool = True
    ) -> tuple[bool, Optional[WorkstationMaster], List[str]]:
        """
        驗證工作站（先精確，失敗時語意搜尋）

        Args:
            workstation_id: 工作站 ID
            use_semantic: 是否使用語意搜尋 fallback

        Returns:
            tuple: (是否有效, 工作站資料, 建議清單)
        """
        # Step 1: 精確比對
        is_valid, data, suggestions = self._master_loader.validate_workstation(workstation_id)
        if is_valid:
            return is_valid, data, suggestions

        # Step 2: 失敗時使用語意搜尋
        if use_semantic:
            return self._semantic_search_workstation(workstation_id)

        return False, None, suggestions

    def _semantic_search_item(
        self, item_no: str, limit: int = 5
    ) -> tuple[bool, Optional[ItemMaster], List[str]]:
        """使用 masterRAG 語意搜尋料號"""
        model = self._get_embedding_model()
        client = self._get_master_rag_client()

        if model is None or client is None:
            # 無法使用語意搜尋，返回現有建議
            return False, None, self._master_loader.validate_item(item_no)[2]

        try:
            # 生成向量
            query_vector = model.encode(item_no).tolist()

            # 語意搜尋
            results = client.search_items(
                query_vector=query_vector,
                limit=limit,
                score_threshold=0.3,  # 降低閾值以獲得更多建議
            )

            if not results:
                return False, None, []

            # 提取建議清單
            suggestions = [
                r["payload"].get("item_no", "") for r in results if r["payload"].get("item_no")
            ]

            # 返回第一個高分結果作為建議
            top_result = results[0]
            payload = top_result.get("payload", {})

            logger.info(
                f"Semantic search for item '{item_no}': {len(suggestions)} results, top score: {top_result.get('score', 0):.2f}"
            )

            return False, None, suggestions

        except Exception as e:
            logger.warning(f"Semantic search failed for item '{item_no}': {e}")
            return False, None, []

    def _semantic_search_warehouse(
        self, warehouse_no: str, limit: int = 5
    ) -> tuple[bool, Optional[WarehouseMaster], List[str]]:
        """使用 masterRAG 語意搜尋倉庫"""
        model = self._get_embedding_model()
        client = self._get_master_rag_client()

        if model is None or client is None:
            return False, None, self._master_loader.validate_warehouse(warehouse_no)[2]

        try:
            query_vector = model.encode(warehouse_no).tolist()

            results = client.search_warehouses(
                query_vector=query_vector,
                limit=limit,
                score_threshold=0.3,
            )

            if not results:
                return False, None, []

            suggestions = [
                r["payload"].get("warehouse_no", "")
                for r in results
                if r["payload"].get("warehouse_no")
            ]

            logger.info(
                f"Semantic search for warehouse '{warehouse_no}': {len(suggestions)} results, top score: {results[0].get('score', 0):.2f}"
            )

            return False, None, suggestions

        except Exception as e:
            logger.warning(f"Semantic search failed for warehouse '{warehouse_no}': {e}")
            return False, None, []

    def _semantic_search_workstation(
        self, workstation_id: str, limit: int = 5
    ) -> tuple[bool, Optional[WorkstationMaster], List[str]]:
        """使用 masterRAG 語意搜尋工作站"""
        model = self._get_embedding_model()
        client = self._get_master_rag_client()

        if model is None or client is None:
            return False, None, self._master_loader.validate_workstation(workstation_id)[2]

        try:
            query_vector = model.encode(workstation_id).tolist()

            results = client.search_workstations(
                query_vector=query_vector,
                limit=limit,
                score_threshold=0.3,
            )

            if not results:
                return False, None, []

            suggestions = [
                r["payload"].get("workstation_id", "")
                for r in results
                if r["payload"].get("workstation_id")
            ]

            logger.info(
                f"Semantic search for workstation '{workstation_id}': {len(suggestions)} results, top score: {results[0].get('score', 0):.2f}"
            )

            return False, None, suggestions

        except Exception as e:
            logger.warning(f"Semantic search failed for workstation '{workstation_id}': {e}")
            return False, None, []


# Singleton instance
_master_rag_validator: Optional[MasterRAGValidator] = None


def get_master_rag_validator(base_path: str = None) -> MasterRAGValidator:
    """
    取得 MasterRAG Validator Singleton

    Args:
        base_path: Master Data 基礎路徑

    Returns:
        MasterRAGValidator: 驗證器實例
    """
    global _master_rag_validator

    if _master_rag_validator is None:
        _master_rag_validator = MasterRAGValidator(base_path=base_path)

    return _master_rag_validator


def validate_entity_with_rag(
    entity_type: str,
    entity_value: str,
    base_path: str = None,
    use_semantic: bool = True,
) -> tuple[bool, Any, List[str]]:
    """
    驗證 Entity（使用 masterRAG 增強）

    先嘗試精確比對，失敗時使用語意搜尋

    Args:
        entity_type: 實體類型 ("item", "warehouse", "workstation")
        entity_value: 實體值
        base_path: Master Data 基礎路徑
        use_semantic: 是否使用語意搜尋 fallback

    Returns:
        tuple: (是否有效, 實體資料, 建議清單)
    """
    validator = get_master_rag_validator(base_path=base_path)

    if entity_type == "item":
        return validator.validate_item(entity_value, use_semantic=use_semantic)
    elif entity_type == "warehouse":
        return validator.validate_warehouse(entity_value, use_semantic=use_semantic)
    elif entity_type == "workstation":
        return validator.validate_workstation(entity_value, use_semantic=use_semantic)
    else:
        raise ValueError(f"Unknown entity type: {entity_type}")
