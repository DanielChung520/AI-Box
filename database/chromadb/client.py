# 代碼功能說明: ChromaDB 客戶端封裝
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-22 22:16 UTC+8

"""ChromaDB 客戶端封裝，提供連接管理和基礎操作"""

import logging
import os
import threading
import time
from queue import Empty, LifoQueue
from typing import Any, Callable, Dict, List, Optional

from chromadb import Client, HttpClient, PersistentClient
from chromadb.config import Settings

from .exceptions import ChromaDBConnectionError, ChromaDBOperationError

logger = logging.getLogger(__name__)


class ChromaDBClient:
    """ChromaDB 客戶端封裝類"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        persist_directory: Optional[str] = None,
        mode: str = "http",
        pool_size: int = 4,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
        connection_timeout: float = 5.0,
    ):
        """
        初始化 ChromaDB 客戶端

        Args:
            host: ChromaDB 服務器地址（HTTP 模式）
            port: ChromaDB 服務器端口（HTTP 模式）
            persist_directory: 持久化目錄（持久化模式）
            mode: 連接模式，'http' 或 'persistent'
            pool_size: 連線池大小
            max_retries: 失敗時最大重試次數
            retry_backoff: 重試退避基準秒數
            connection_timeout: 取得連線的等待秒數
        """
        self.host = host or os.getenv("CHROMADB_HOST", "localhost")
        self.port = port or int(os.getenv("CHROMADB_PORT", "8001"))
        self.persist_directory = persist_directory or os.getenv(
            "CHROMADB_PERSIST_DIR", "./data/chroma_data"
        )
        self.mode = mode
        self.pool_size = max(pool_size, 1)
        self.max_retries = max(max_retries, 1)
        self.retry_backoff = max(retry_backoff, 0.1)
        self.connection_timeout = max(connection_timeout, 1.0)
        self.client: Optional[Any] = None  # type: ignore[assignment]
        self._pool: LifoQueue[Client] = LifoQueue(maxsize=self.pool_size)
        self._pool_lock = threading.Lock()
        self._current_clients = 0
        self._connect()

    def _connect(self) -> None:
        """建立 ChromaDB 連接並預熱連線池"""
        try:
            client = self._create_client()
            self.client = client
            self._pool.put(client)
            self._current_clients = 1
            logger.info("Primary ChromaDB client initialized")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise ChromaDBConnectionError(str(e)) from e

    def _create_client(self) -> Any:  # type: ignore[valid-type]
        """根據模式建立新的 ChromaDB 連線"""
        if self.mode == "http":
            if not self.host:
                raise ChromaDBConnectionError("Host is required for HTTP mode")
            # 修復 ChromaDB 1.10.0+ tenant 問題：明確指定 tenant 為空字符串
            try:
                return HttpClient(
                    host=self.host,
                    port=self.port or 8000,
                    tenant="",  # 明確指定 tenant 為空字符串，避免 default_tenant 錯誤
                    database="",  # 明確指定 database 為空字符串
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    ),
                )
            except TypeError:
                # 如果 HttpClient 不支持 tenant/database 參數（舊版本），使用原方式
                return HttpClient(
                    host=self.host,
                    port=self.port or 8000,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    ),
                )
        if self.mode == "persistent":
            if not self.persist_directory:
                raise ChromaDBConnectionError("Persist directory is required for persistent mode")
            os.makedirs(self.persist_directory, exist_ok=True)
            # 修復 ChromaDB 1.10.0+ tenant 問題：明確指定 tenant 為空字符串
            try:
                return PersistentClient(
                    path=self.persist_directory,
                    tenant="",  # 明確指定 tenant 為空字符串，避免 default_tenant 錯誤
                    database="",  # 明確指定 database 為空字符串
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    ),
                )
            except TypeError:
                # 如果 PersistentClient 不支持 tenant/database 參數（舊版本），使用原方式
                return PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    ),
                )
        raise ValueError(f"Unsupported mode: {self.mode}")

    def _acquire_client(self) -> Any:  # type: ignore[valid-type]
        """從連線池取得可用連線"""
        try:
            return self._pool.get_nowait()
        except Empty:
            with self._pool_lock:
                if self._current_clients < self.pool_size:
                    client = self._create_client()
                    self._current_clients += 1
                    logger.debug("Created new ChromaDB client for the pool")
                    return client
        # 等待既有連線釋放
        try:
            return self._pool.get(timeout=self.connection_timeout)
        except Empty as exc:
            raise ChromaDBConnectionError("No ChromaDB connections available") from exc

    def _release_client(self, client: Any) -> None:  # type: ignore[valid-type]
        """將連線歸還連線池"""
        if client is None:
            return
        try:
            self._pool.put_nowait(client)
        except Exception:
            # 池已滿，直接丟棄
            self._current_clients = max(self._current_clients - 1, 0)

    def _discard_client(self, client: Any) -> None:  # type: ignore[valid-type]
        """丟棄故障連線"""
        self._current_clients = max(self._current_clients - 1, 0)
        # HttpClient/PersistentClient 不需要顯式關閉，直接放掉

    def _execute(self, operation: str, func: Callable[[Any], Any]):  # type: ignore[valid-type]
        """統一的連線池執行與重試邏輯"""
        attempt = 0
        last_error: Optional[Exception] = None
        while attempt < self.max_retries:
            client = None
            try:
                client = self._acquire_client()
                result = func(client)
                self._release_client(client)
                return result
            except Exception as exc:
                last_error = exc
                attempt += 1
                logger.warning(
                    "ChromaDB operation '%s' failed (attempt %s/%s): %s",
                    operation,
                    attempt,
                    self.max_retries,
                    exc,
                )
                if client:
                    self._discard_client(client)
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff * attempt)
        logger.error("ChromaDB operation '%s' exhausted retries", operation)
        if last_error:
            raise ChromaDBOperationError(str(last_error)) from last_error
        raise ChromaDBOperationError(f"Operation {operation} failed without error information")

    def get_or_create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_function=None,
    ):
        """
        獲取或創建集合

        Args:
            name: 集合名稱
            metadata: 集合元數據
            embedding_function: 嵌入函數

        Returns:
            Collection 對象
        """
        if not self.client:
            raise ChromaDBConnectionError("ChromaDB client is not connected")

        def _op(acquired: Any):  # type: ignore[valid-type]
            # ChromaDB 不接受空字典作為 metadata，傳遞 None
            metadata_to_use = metadata if metadata and len(metadata) > 0 else None
            collection = acquired.get_or_create_collection(
                name=name,
                metadata=metadata_to_use,
                embedding_function=embedding_function,
            )
            logger.info(f"Collection '{name}' retrieved or created")
            return collection

        return self._execute("get_or_create_collection", _op)

    def delete_collection(self, name: str) -> None:
        """
        刪除集合

        Args:
            name: 集合名稱
        """
        if not self.client:
            raise ChromaDBConnectionError("ChromaDB client is not connected")

        def _op(acquired: Any):  # type: ignore[valid-type]
            acquired.delete_collection(name=name)
            logger.info(f"Collection '{name}' deleted")

        self._execute("delete_collection", _op)

    def list_collections(self) -> List[str]:
        """
        列出所有集合名稱

        Returns:
            集合名稱列表
        """
        if not self.client:
            raise ChromaDBConnectionError("ChromaDB client is not connected")

        def _op(acquired: Any):  # type: ignore[valid-type]
            collections = acquired.list_collections()
            return [col.name for col in collections]

        return self._execute("list_collections", _op)

    def reset(self) -> None:
        """重置資料庫（刪除所有數據）"""
        if not self.client:
            raise ChromaDBConnectionError("ChromaDB client is not connected")

        def _op(acquired: Any):  # type: ignore[valid-type]
            acquired.reset()
            logger.warning("ChromaDB database reset")

        self._execute("reset", _op)

    def heartbeat(self) -> Dict[str, Any]:
        """
        檢查服務器健康狀態

        Returns:
            健康狀態信息
        """
        if not self.client:
            raise ChromaDBConnectionError("ChromaDB client is not connected")

        def _http(acquired: Any):  # type: ignore[valid-type]
            response = acquired.heartbeat()
            return {"status": "healthy", "response": response}

        def _persistent(acquired: Any):  # type: ignore[valid-type]
            acquired.list_collections()
            return {"status": "healthy"}

        try:
            if self.mode == "http":
                return self._execute("heartbeat", _http)
            return self._execute("heartbeat", _persistent)
        except Exception as e:
            logger.error(f"Heartbeat check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def close(self) -> None:
        """關閉連接"""
        self.client = None
        while not self._pool.empty():
            try:
                self._pool.get_nowait()
            except Empty:
                break
        self._current_clients = 0
        logger.info("ChromaDB client pool closed")
