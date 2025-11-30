# 代碼功能說明: ArangoDB 客戶端封裝
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 22:58 (UTC+8)

"""ArangoDB 客戶端封裝，提供連線管理、重試與健康檢查功能。"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import structlog
from arango import ArangoClient
from arango.database import StandardDatabase
from arango.http import DefaultHTTPClient
from tenacity import Retrying, stop_after_attempt, wait_exponential

from .settings import ArangoDBSettings, load_arangodb_settings

logger = structlog.get_logger(__name__)


class ArangoDBClient:
    """ArangoDB 客戶端封裝類"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        *,
        settings: Optional[ArangoDBSettings] = None,
        http_client: Optional[DefaultHTTPClient] = None,
        connect_on_init: bool = True,
    ):
        """
        初始化 ArangoDB 客戶端。

        Args:
            host: 覆寫設定檔中的主機
            port: 覆寫設定檔中的埠
            username: ArangoDB 使用者（預設讀取環境變數）
            password: ArangoDB 密碼（預設讀取環境變數）
            database: 覆寫設定檔中的資料庫名稱
            settings: 自訂設定物件
            http_client: 自訂 HTTP client（可置換為測試假件）
            connect_on_init: 建構時是否立即建立連線
        """
        base_settings = settings or load_arangodb_settings()
        self.settings = base_settings.with_overrides(
            host=host,
            port=port,
            database=database,
        )
        self.username = username or os.getenv(
            self.settings.credentials.username, "root"
        )
        self.password = password or os.getenv(
            self.settings.credentials.password,
            "ai_box_arangodb_password",
        )

        self.client: Optional[ArangoClient] = None
        self.db: Optional[StandardDatabase] = None
        self._http_client = http_client or self._build_http_client()
        self.logger = logger.bind(
            host=self.settings.host,
            port=self.settings.port,
            database=self.settings.database,
        )

        if connect_on_init:
            self._connect_with_retry()

    # --------------------------------------------------------------------- #
    # 內部流程
    # --------------------------------------------------------------------- #
    def _build_http_client(self) -> DefaultHTTPClient:
        """建立帶有連線池與逾時設定的 HTTP client。"""
        retry_attempts = (
            self.settings.retry.max_attempts if self.settings.retry.enabled else 1
        )
        return DefaultHTTPClient(
            request_timeout=self.settings.request_timeout,
            retry_attempts=retry_attempts,
            backoff_factor=self.settings.retry.backoff_factor,
            pool_connections=self.settings.pool.connections,
            pool_maxsize=self.settings.pool.max_size,
            pool_timeout=self.settings.pool.timeout,
        )

    def _connect_with_retry(self) -> None:
        """依設定重試策略建立連線。"""
        if not self.settings.retry.enabled or self.settings.retry.max_attempts <= 1:
            self._connect()
            return

        retry_runner = Retrying(
            stop=stop_after_attempt(self.settings.retry.max_attempts),
            wait=wait_exponential(
                multiplier=self.settings.retry.backoff_factor,
                max=self.settings.retry.max_backoff_seconds,
            ),
            reraise=True,
        )
        for attempt in retry_runner:
            with attempt:
                self._connect()

    def _connect(self) -> None:
        """建立 ArangoDB 連線。"""
        verify_override: Optional[Any] = None
        if self.settings.tls.enabled or self.settings.protocol == "https":
            verify_override = self.settings.tls.ca_file or self.settings.tls.verify

        try:
            self.client = ArangoClient(
                hosts=self.settings.base_url,
                http_client=self._http_client,
                verify_override=verify_override,
                request_timeout=self.settings.request_timeout,
            )
            sys_db = self.client.db(
                "_system",
                username=self.username or "",
                password=self.password or "",
            )
            if not sys_db.has_database(self.settings.database):
                sys_db.create_database(self.settings.database)
                self.logger.info("created_database", database=self.settings.database)

            self.db = self.client.db(
                self.settings.database,
                username=self.username or "",
                password=self.password or "",
            )
            self.logger.info("connected")
        except Exception as exc:
            self.logger.error("connect_failed", error=str(exc))
            raise

    def ensure_connection(self) -> None:
        """若尚未建立連線則立即連線。"""
        if not self.client or not self.db:
            self._connect_with_retry()

    # --------------------------------------------------------------------- #
    # 公開方法
    # --------------------------------------------------------------------- #
    def get_or_create_collection(
        self,
        name: str,
        collection_type: str = "document",
    ):
        """獲取或創建集合。"""
        self.ensure_connection()
        if not self.db:
            raise RuntimeError("Database connection not established")
        try:
            if not self.db.has_collection(name):
                if collection_type == "edge":
                    self.db.create_collection(name, edge=True)
                else:
                    self.db.create_collection(name)
                self.logger.info("collection_created", name=name, type=collection_type)
            collection = self.db.collection(name)
            return collection
        except Exception as exc:
            self.logger.error("collection_error", name=name, error=str(exc))
            raise

    def delete_collection(self, name: str, ignore_missing: bool = False) -> None:
        """刪除集合。"""
        self.ensure_connection()
        if not self.db:
            raise RuntimeError("Database connection not established")
        try:
            self.db.delete_collection(name, ignore_missing=ignore_missing)
            self.logger.info("collection_deleted", name=name)
        except Exception as exc:
            self.logger.error("collection_delete_failed", name=name, error=str(exc))
            raise

    def list_collections(self, exclude_system: bool = True) -> List[str]:
        """列出集合名稱。"""
        self.ensure_connection()
        if not self.db:
            raise RuntimeError("Database connection not established")
        try:
            collections = self.db.collections()
            # 處理可能的異步/批次作業結果
            if not isinstance(collections, list):
                # ArangoDB 可能返回異步作業，這裡簡化處理
                collections = []  # type: ignore[assignment]
            if exclude_system:
                return [
                    col["name"]
                    for col in collections  # type: ignore[union-attr]
                    if not col["name"].startswith("_")
                ]
            return [col["name"] for col in collections]  # type: ignore[union-attr]
        except Exception as exc:
            self.logger.error("list_collections_failed", error=str(exc))
            raise

    def get_or_create_graph(
        self, name: str, edge_definitions: Optional[List[Dict[str, Any]]] = None
    ):
        """獲取或創建圖。"""
        self.ensure_connection()
        if not self.db:
            raise RuntimeError("Database connection not established")
        try:
            if not self.db.has_graph(name):
                self.db.create_graph(name, edge_definitions=edge_definitions)
                self.logger.info("graph_created", name=name)
            return self.db.graph(name)
        except Exception as exc:
            self.logger.error("graph_error", name=name, error=str(exc))
            raise

    def execute_aql(
        self,
        query: str,
        bind_vars: Optional[Dict[str, Any]] = None,
        batch_size: Optional[int] = None,
        count: bool = False,
        full_count: bool = False,
    ) -> Dict[str, Any]:
        """執行 AQL 查詢。"""
        self.ensure_connection()
        if not self.db:
            raise RuntimeError("Database connection not established")
        try:
            cursor = self.db.aql.execute(
                query,
                bind_vars=bind_vars or {},
                batch_size=batch_size,
                count=count,
                full_count=full_count,
            )
            # 處理可能的異步/批次作業結果
            if not isinstance(cursor, (list, tuple)) and hasattr(cursor, "__iter__"):
                results = list(cursor)  # type: ignore[arg-type]
            else:
                results = cursor if isinstance(cursor, list) else []
            cursor_count = (
                cursor.count() if hasattr(cursor, "count") and count else None
            )  # type: ignore[union-attr]
            self.logger.debug(
                "aql_executed",
                rows=len(results),
                count=cursor_count,
            )
            return {"results": results, "count": cursor_count}
        except Exception as exc:
            self.logger.error("aql_failed", error=str(exc))
            raise

    def heartbeat(self) -> Dict[str, Any]:
        """檢查服務器健康狀態。"""
        try:
            self.ensure_connection()
            if not self.db:
                return {
                    "status": "unhealthy",
                    "error": "Database connection not established",
                }
            self.db.collections()  # 使用 collections() 而不是 list_collections()
            return {"status": "healthy", "database": self.settings.database}
        except Exception as exc:
            self.logger.error("heartbeat_failed", error=str(exc))
            return {"status": "unhealthy", "error": str(exc)}

    def close(self) -> None:
        """關閉連線。"""
        self.db = None
        self.client = None
        self.logger.info("connection_closed")
