"""
代碼功能說明: GenAI Chat 非同步 request store（Redis 優先 + memory fallback），支援狀態查詢與 abort flag（MVP）
創建日期: 2025-12-13 22:26:20 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 22:26:20 (UTC+8)
"""

from __future__ import annotations

import json
import time
from threading import Lock
from typing import Any, Dict, Optional

import structlog

from database.redis.client import get_redis_client
from services.api.models.genai_request import GenAIChatRequestRecord, GenAIRequestStatus

logger = structlog.get_logger(__name__)


class GenAIChatRequestStoreService:
    """request_id 為核心的 request store（MVP）。"""

    def __init__(self, *, ttl_seconds: int = 60 * 60 * 24) -> None:
        self._ttl_seconds = max(int(ttl_seconds), 60)
        self._redis = None
        try:
            self._redis = get_redis_client()
        except Exception as exc:  # noqa: BLE001
            logger.warning("genai_chat_request_store_redis_unavailable", error=str(exc))

        self._lock = Lock()
        self._fallback: Dict[str, GenAIChatRequestRecord] = {}
        self._fallback_abort: Dict[str, bool] = {}

    @staticmethod
    def _request_key(request_id: str) -> str:
        return f"genai:chat:request:{request_id}"

    @staticmethod
    def _abort_key(request_id: str) -> str:
        return f"genai:chat:abort:{request_id}"

    def create(self, record: GenAIChatRequestRecord) -> None:
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
                    "genai_chat_request_store_redis_set_failed",
                    request_id=record.request_id,
                    error=str(exc),
                )

        with self._lock:
            self._fallback[record.request_id] = record

    def get(self, *, request_id: str) -> Optional[GenAIChatRequestRecord]:
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
                return GenAIChatRequestRecord.model_validate(data)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "genai_chat_request_store_redis_get_failed",
                    request_id=request_id,
                    error=str(exc),
                )

        with self._lock:
            return self._fallback.get(request_id)

    def update(
        self,
        *,
        request_id: str,
        status: Optional[GenAIRequestStatus] = None,
        response: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[GenAIChatRequestRecord]:
        record = self.get(request_id=request_id)
        if record is None:
            return None

        if status is not None:
            record.status = status
        if response is not None:
            record.response = response
        if error_code is not None:
            record.error_code = error_code
        if error_message is not None:
            record.error_message = error_message

        record.updated_at_ms = time.time() * 1000.0
        self.create(record)
        return record

    def set_abort(self, *, request_id: str) -> None:
        key = self._abort_key(request_id)
        if self._redis is not None:
            try:
                self._redis.set(key, "1", ex=self._ttl_seconds)  # type: ignore[union-attr]
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "genai_chat_request_store_redis_abort_set_failed",
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
                    "genai_chat_request_store_redis_abort_get_failed",
                    request_id=request_id,
                    error=str(exc),
                )

        with self._lock:
            return bool(self._fallback_abort.get(request_id, False))


_service: Optional[GenAIChatRequestStoreService] = None


def get_genai_chat_request_store_service() -> GenAIChatRequestStoreService:
    global _service
    if _service is None:
        _service = GenAIChatRequestStoreService()
    return _service


def reset_genai_chat_request_store_service() -> None:
    global _service
    _service = None
