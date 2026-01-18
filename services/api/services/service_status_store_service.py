# 代碼功能說明: ServiceStatus 存儲服務 - 提供服務狀態的 CRUD 操作
# 創建日期: 2026-01-17 17:13 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 17:13 UTC+8

"""ServiceStatus Store Service

提供服務狀態的 CRUD 操作，包括狀態更新、查詢、歷史記錄等功能。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.service_status import ServiceStatusHistoryModel, ServiceStatusModel

logger = structlog.get_logger(__name__)

SERVICE_STATUS_COLLECTION = "service_status"
SERVICE_STATUS_HISTORY_COLLECTION = "service_status_history"


def _document_to_model(doc: Dict[str, Any]) -> ServiceStatusModel:
    """將 ArangoDB document 轉換為 ServiceStatusModel"""
    return ServiceStatusModel(
        id=doc.get("_key"),
        service_name=doc.get("service_name"),
        service_type=doc.get("service_type"),
        status=doc.get("status"),
        health_status=doc.get("health_status"),
        port=doc.get("port"),
        pid=doc.get("pid"),
        host=doc.get("host", "localhost"),
        last_check_at=(
            datetime.fromisoformat(doc["last_check_at"]) if doc.get("last_check_at") else None
        ),
        last_success_at=(
            datetime.fromisoformat(doc["last_success_at"]) if doc.get("last_success_at") else None
        ),
        check_interval=doc.get("check_interval", 30),
        metadata=doc.get("metadata", {}),
    )


def _document_to_history_model(doc: Dict[str, Any]) -> ServiceStatusHistoryModel:
    """將 ArangoDB document 轉換為 ServiceStatusHistoryModel"""
    return ServiceStatusHistoryModel(
        id=doc.get("_key"),
        service_name=doc.get("service_name"),
        status=doc.get("status"),
        health_status=doc.get("health_status"),
        timestamp=(
            datetime.fromisoformat(doc["timestamp"]) if doc.get("timestamp") else datetime.utcnow()
        ),
        metadata=doc.get("metadata", {}),
    )


class ServiceStatusStoreService:
    """ServiceStatus 存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 ServiceStatus Store Service

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collections 存在
        status_collection = self._client.get_or_create_collection(SERVICE_STATUS_COLLECTION)
        history_collection = self._client.get_or_create_collection(
            SERVICE_STATUS_HISTORY_COLLECTION
        )
        self._status_collection = ArangoCollection(status_collection)
        self._history_collection = ArangoCollection(history_collection)
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        if self._client.db is None:
            return

        status_collection = self._client.db.collection(SERVICE_STATUS_COLLECTION)
        history_collection = self._client.db.collection(SERVICE_STATUS_HISTORY_COLLECTION)

        # 獲取現有索引
        status_indexes = status_collection.indexes()
        history_indexes = history_collection.indexes()

        status_existing_fields = {
            (
                tuple(idx.get("fields", []))
                if isinstance(idx.get("fields"), list)
                else idx.get("fields")
            )
            for idx in status_indexes
        }

        history_existing_fields = {
            (
                tuple(idx.get("fields", []))
                if isinstance(idx.get("fields"), list)
                else idx.get("fields")
            )
            for idx in history_indexes
        }

        # service_status Collection 索引
        # service_name 唯一索引
        service_name_fields = ("service_name",)
        if service_name_fields not in status_existing_fields:
            status_collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["service_name"],
                    "unique": True,
                    "name": "idx_service_status_service_name",
                }
            )

        # status 索引
        status_fields = ("status",)
        if status_fields not in status_existing_fields:
            status_collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["status"],
                    "name": "idx_service_status_status",
                }
            )

        # health_status 索引
        health_status_fields = ("health_status",)
        if health_status_fields not in status_existing_fields:
            status_collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["health_status"],
                    "name": "idx_service_status_health_status",
                }
            )

        # last_check_at 索引
        last_check_fields = ("last_check_at",)
        if last_check_fields not in status_existing_fields:
            status_collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["last_check_at"],
                    "name": "idx_service_status_last_check",
                }
            )

        # service_status_history Collection 索引
        # service_name + timestamp 複合索引
        service_timestamp_fields = ("service_name", "timestamp")
        if service_timestamp_fields not in history_existing_fields:
            history_collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["service_name", "timestamp"],
                    "name": "idx_service_status_history_service_timestamp",
                }
            )

        # TTL 索引（30 天自動清理）
        timestamp_ttl_fields = ("timestamp",)
        if timestamp_ttl_fields not in history_existing_fields:
            try:
                history_collection.add_index(
                    {
                        "type": "ttl",
                        "fields": ["timestamp"],
                        "expireAfter": 2592000,  # 30 天（秒）
                        "name": "idx_service_status_history_ttl",
                    }
                )
            except Exception as e:
                self._logger.warning(f"Failed to create TTL index: {e}")

    def update_service_status(
        self,
        service_name: str,
        status: str,
        health_status: str,
        metadata: Optional[Dict[str, Any]] = None,
        port: Optional[int] = None,
        pid: Optional[int] = None,
        host: str = "localhost",
    ) -> ServiceStatusModel:
        """
        更新服務狀態

        Args:
            service_name: 服務名稱
            status: 運行狀態
            health_status: 健康狀態
            metadata: 元數據
            port: 端口號
            pid: 進程ID
            host: 主機地址

        Returns:
            更新後的服務狀態模型
        """
        now = datetime.utcnow().isoformat()
        existing = self._status_collection.get(service_name)

        # 從 SERVICE_CONFIGS 獲取服務類型（如果存在）
        from services.api.services.service_monitor_service import SERVICE_CONFIGS

        service_config = SERVICE_CONFIGS.get(service_name, {})
        service_type = service_config.get("type", "unknown")

        doc: Dict[str, Any] = {
            "_key": service_name,
            "service_name": service_name,
            "service_type": service_type,
            "status": status,
            "health_status": health_status,
            "port": port or service_config.get("port"),
            "pid": pid,
            "host": host,
            "last_check_at": now,
            "check_interval": 30,
            "metadata": metadata or {},
        }

        # 如果狀態為 healthy 或 running，更新 last_success_at
        if health_status == "healthy" or status == "running":
            doc["last_success_at"] = now
        elif existing:
            # 保留現有的 last_success_at
            doc["last_success_at"] = existing.get("last_success_at")

        if existing:
            # 更新
            doc["created_at"] = existing.get("created_at", now)
            self._status_collection.update(doc)
        else:
            # 創建
            doc["created_at"] = now
            self._status_collection.insert(doc)

        # 保存歷史記錄
        self._save_status_history(service_name, status, health_status, metadata or {})

        return _document_to_model(doc)

    def _save_status_history(
        self,
        service_name: str,
        status: str,
        health_status: str,
        metadata: Dict[str, Any],
    ) -> None:
        """保存狀態歷史記錄"""
        try:
            history_key = f"history_{datetime.utcnow().isoformat()}_{uuid.uuid4().hex[:8]}"
            history_doc: Dict[str, Any] = {
                "_key": history_key,
                "service_name": service_name,
                "status": status,
                "health_status": health_status,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata,
            }
            self._history_collection.insert(history_doc)
        except Exception as e:
            # 歷史記錄失敗不影響主流程
            self._logger.warning(f"Failed to save status history: {e}")

    def get_service_status(self, service_name: str) -> Optional[ServiceStatusModel]:
        """
        獲取服務狀態

        Args:
            service_name: 服務名稱

        Returns:
            服務狀態模型，如果不存在則返回 None
        """
        doc = self._status_collection.get(service_name)
        if doc is None:
            return None
        return _document_to_model(doc)

    def list_all_services(self) -> List[ServiceStatusModel]:
        """
        列出所有服務狀態

        Returns:
            服務狀態列表
        """
        results = self._status_collection.find({})
        return [_document_to_model(doc) for doc in results]

    def get_service_history(
        self,
        service_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = 100,
    ) -> List[ServiceStatusHistoryModel]:
        """
        獲取服務狀態歷史記錄

        Args:
            service_name: 服務名稱
            start_time: 開始時間
            end_time: 結束時間
            limit: 限制返回數量

        Returns:
            歷史記錄列表
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        # 構建 AQL 查詢
        aql = """
        FOR doc IN service_status_history
        FILTER doc.service_name == @service_name
        """
        bind_vars: Dict[str, Any] = {"service_name": service_name}

        if start_time:
            aql += " AND doc.timestamp >= @start_time"
            bind_vars["start_time"] = start_time.isoformat()

        if end_time:
            aql += " AND doc.timestamp <= @end_time"
            bind_vars["end_time"] = end_time.isoformat()

        aql += " SORT doc.timestamp DESC"

        if limit:
            aql += " LIMIT @limit"
            bind_vars["limit"] = limit

        aql += " RETURN doc"

        try:
            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            results = list(cursor)
            return [_document_to_history_model(doc) for doc in results]
        except Exception as e:
            self._logger.error(f"Failed to get service history: {e}", exc_info=True)
            return []


def get_service_status_store_service(
    client: Optional[ArangoDBClient] = None,
) -> ServiceStatusStoreService:
    """
    獲取 ServiceStatus Store Service 實例（單例模式）

    Args:
        client: ArangoDB 客戶端（可選）

    Returns:
        ServiceStatusStoreService 實例
    """
    global _service
    if _service is None:
        _service = ServiceStatusStoreService(client)
    return _service


_service: Optional[ServiceStatusStoreService] = None
