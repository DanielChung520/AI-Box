"""
代碼功能說明: 文件生成（Doc Generation）request store（Redis 優先 + memory fallback，含 abort flag）
創建日期: 2025-12-14 10:27:19 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-14 10:27:19 (UTC+8)
"""

from __future__ import annotations

import json
import time
from threading import Lock
from typing import Optional

import structlog

from database.redis.client import get_redis_client
from services.api.models.doc_generation_request import DocGenRequestRecord, DocGenStatus

logger = structlog.get_logger(__name__)


class DocGenRequestStoreService:
    def __init__(self, *, ttl_seconds: int = 60 * 60 * 24) -> None:
        self._ttl_seconds = max(int(ttl_seconds), 60)
        self._redis = None
        try:
            self._redis = get_redis_client()
        except Exception as exc:  # noqa: BLE001
            logger.warning("doc_gen_store_redis_unavailable", error=str(exc))

        self._lock = Lock()
        self._fallback: dict[str, DocGenRequestRecord] = {}
        self._fallback_abort: dict[str, bool] = {}

    @staticmethod
    def _request_key(request_id: str) -> str:
        return f"doc:gen:request:{request_id}"

    @staticmethod
    def _abort_key(request_id: str) -> str:
        return f"doc:gen:abort:{request_id}"

    def create(self, record: DocGenRequestRecord) -> None:
        record.updated_at_ms = time.time() * 1000.0
        key = self._request_key(record.request_id)

        if self._redis is not None:
            try:
                self._redis.set(  # type: ignore[union-attr]
                    key,
                    record.model_dump_json(),
                    ex=self._ttl_seconds,
                )
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "doc_gen_store_redis_set_failed",
                    request_id=record.request_id,
                    error=str(exc),
                )

        with self._lock:
            self._fallback[record.request_id] = record

    def get(self, *, request_id: str) -> Optional[DocGenRequestRecord]:
        key = self._request_key(request_id)

        if self._redis is not None:
            try:
                raw = self._redis.get(key)  # type: ignore[union-attr]
                if raw is None:
                    return None
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="ignore")
                if not isinstance(raw, str):
                    raw = str(raw)
                data = json.loads(raw)
                return DocGenRequestRecord.model_validate(data)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "doc_gen_store_redis_get_failed",
                    request_id=request_id,
                    error=str(exc),
                )

        with self._lock:
            return self._fallback.get(request_id)

    def update(
        self,
        *,
        request_id: str,
        status: Optional[DocGenStatus] = None,
        record: Optional[DocGenRequestRecord] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[DocGenRequestRecord]:
        current = record or self.get(request_id=request_id)
        if current is None:
            return None

        if status is not None:
            current.status = status
        if error_code is not None:
            current.error_code = error_code
        if error_message is not None:
            current.error_message = error_message

        current.updated_at_ms = time.time() * 1000.0
        self.create(current)
        return current

    def set_abort(self, *, request_id: str) -> None:
        key = self._abort_key(request_id)
        if self._redis is not None:
            try:
                self._redis.set(key, "1", ex=self._ttl_seconds)  # type: ignore[union-attr]
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "doc_gen_store_redis_abort_set_failed",
                    request_id=request_id,
                    error=str(exc),
                )

        with self._lock:
            self._fallback_abort[request_id] = True

    def is_aborted(self, *, request_id: str) -> bool:
        key = self._abort_key(request_id)
        if self._redis is not None:
            try:
                raw = self._redis.get(key)  # type: ignore[union-attr]
                if raw is None:
                    return False
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="ignore")
                return str(raw) == "1"
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "doc_gen_store_redis_abort_get_failed",
                    request_id=request_id,
                    error=str(exc),
                )

        with self._lock:
            return bool(self._fallback_abort.get(request_id, False))


_service: Optional[DocGenRequestStoreService] = None


def get_doc_generation_request_store_service() -> DocGenRequestStoreService:
    global _service
    if _service is None:
        _service = DocGenRequestStoreService()
    return _service


def reset_doc_generation_request_store_service() -> None:
    global _service
    _service = None
