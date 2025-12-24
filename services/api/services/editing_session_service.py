"""
代碼功能說明: 編輯 Session 管理服務（Redis 優先 + memory fallback）
創建日期: 2025-12-20 12:30:07 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-20 12:30:07 (UTC+8)
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, Optional

import structlog

from database.redis.client import get_redis_client

logger = structlog.get_logger(__name__)


@dataclass
class EditingSession:
    """編輯 Session 數據模型"""

    session_id: str
    doc_id: str
    user_id: str
    tenant_id: str
    created_at_ms: float = field(default_factory=lambda: time.time() * 1000.0)
    updated_at_ms: float = field(default_factory=lambda: time.time() * 1000.0)
    expires_at_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "session_id": self.session_id,
            "doc_id": self.doc_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "created_at_ms": self.created_at_ms,
            "updated_at_ms": self.updated_at_ms,
            "expires_at_ms": self.expires_at_ms,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EditingSession:
        """從字典創建"""
        return cls(
            session_id=data["session_id"],
            doc_id=data["doc_id"],
            user_id=data["user_id"],
            tenant_id=data["tenant_id"],
            created_at_ms=data.get("created_at_ms", time.time() * 1000.0),
            updated_at_ms=data.get("updated_at_ms", time.time() * 1000.0),
            expires_at_ms=data.get("expires_at_ms"),
            metadata=data.get("metadata", {}),
        )

    def is_expired(self) -> bool:
        """檢查 Session 是否已過期"""
        if self.expires_at_ms is None:
            return False
        return time.time() * 1000.0 > self.expires_at_ms


class EditingSessionService:
    """編輯 Session 管理服務"""

    def __init__(self, *, ttl_seconds: int = 60 * 60) -> None:  # 默認 1 小時
        self._ttl_seconds = max(int(ttl_seconds), 60)
        self._redis: Optional[Any] = None
        try:
            self._redis = get_redis_client()
        except Exception as exc:  # noqa: BLE001
            logger.warning("editing_session_redis_unavailable", error=str(exc))

        self._lock = Lock()
        self._fallback: Dict[str, EditingSession] = {}

    @staticmethod
    def _session_key(session_id: str) -> str:
        """生成 Session Redis key"""
        return f"editing:session:{session_id}"

    def create_session(
        self,
        *,
        doc_id: str,
        user_id: str,
        tenant_id: str,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EditingSession:
        """創建新的編輯 Session

        Args:
            doc_id: 文檔 ID
            user_id: 用戶 ID
            tenant_id: 租戶 ID
            ttl_seconds: Session 過期時間（秒），如果為 None 則使用默認值
            metadata: 額外的元數據

        Returns:
            EditingSession: 創建的 Session 對象
        """
        session_id = str(uuid.uuid4())
        now_ms = time.time() * 1000.0
        expires_at_ms = (
            (now_ms + (ttl_seconds or self._ttl_seconds) * 1000.0)
            if (ttl_seconds or self._ttl_seconds) > 0
            else None
        )

        session = EditingSession(
            session_id=session_id,
            doc_id=doc_id,
            user_id=user_id,
            tenant_id=tenant_id,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
            expires_at_ms=expires_at_ms,
            metadata=metadata or {},
        )

        key = self._session_key(session_id)
        ttl = ttl_seconds or self._ttl_seconds

        if self._redis is not None:
            try:
                self._redis.set(  # type: ignore[union-attr]
                    key,
                    json.dumps(session.to_dict()),
                    ex=ttl,
                )
                logger.info("editing_session_created", session_id=session_id, doc_id=doc_id)
                return session
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "editing_session_redis_set_failed",
                    session_id=session_id,
                    error=str(exc),
                )

        # Fallback 到內存存儲
        with self._lock:
            self._fallback[session_id] = session
        logger.info("editing_session_created_fallback", session_id=session_id, doc_id=doc_id)
        return session

    def get_session(self, *, session_id: str) -> Optional[EditingSession]:
        """獲取 Session

        Args:
            session_id: Session ID

        Returns:
            EditingSession 或 None（如果不存在或已過期）
        """
        key = self._session_key(session_id)

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
                session = EditingSession.from_dict(data)
                if session.is_expired():
                    # 過期的 Session 自動刪除
                    self.delete_session(session_id=session_id)
                    return None
                return session
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "editing_session_redis_get_failed",
                    session_id=session_id,
                    error=str(exc),
                )

        # Fallback 到內存存儲
        with self._lock:
            session = self._fallback.get(session_id)
            if session is None:
                return None
            if session.is_expired():
                del self._fallback[session_id]
                return None
            return session

    def update_session(
        self,
        *,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        extend_ttl: bool = True,
    ) -> Optional[EditingSession]:
        """更新 Session

        Args:
            session_id: Session ID
            metadata: 要更新的元數據（會合併到現有元數據）
            extend_ttl: 是否延長 TTL

        Returns:
            更新後的 EditingSession 或 None（如果不存在）
        """
        session = self.get_session(session_id=session_id)
        if session is None:
            return None

        session.updated_at_ms = time.time() * 1000.0

        if metadata is not None:
            session.metadata.update(metadata)

        if extend_ttl and session.expires_at_ms is not None:
            session.expires_at_ms = time.time() * 1000.0 + self._ttl_seconds * 1000.0

        key = self._session_key(session_id)
        ttl = self._ttl_seconds

        if self._redis is not None:
            try:
                self._redis.set(  # type: ignore[union-attr]
                    key,
                    json.dumps(session.to_dict()),
                    ex=ttl,
                )
                return session
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "editing_session_redis_update_failed",
                    session_id=session_id,
                    error=str(exc),
                )

        # Fallback 到內存存儲
        with self._lock:
            self._fallback[session_id] = session
        return session

    def delete_session(self, *, session_id: str) -> bool:
        """刪除 Session

        Args:
            session_id: Session ID

        Returns:
            True 如果刪除成功，False 如果 Session 不存在
        """
        key = self._session_key(session_id)

        if self._redis is not None:
            try:
                deleted = self._redis.delete(key)  # type: ignore[union-attr]
                if deleted > 0:
                    logger.info("editing_session_deleted", session_id=session_id)
                    return True
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "editing_session_redis_delete_failed",
                    session_id=session_id,
                    error=str(exc),
                )

        # Fallback 到內存存儲
        with self._lock:
            if session_id in self._fallback:
                del self._fallback[session_id]
                logger.info("editing_session_deleted_fallback", session_id=session_id)
                return True
        return False

    def cleanup_expired_sessions(self) -> int:
        """清理過期的 Session（僅內存存儲）

        Returns:
            清理的 Session 數量
        """
        cleaned = 0
        with self._lock:
            expired_ids = [
                session_id for session_id, session in self._fallback.items() if session.is_expired()
            ]
            for session_id in expired_ids:
                del self._fallback[session_id]
                cleaned += 1

        if cleaned > 0:
            logger.info("editing_sessions_cleaned", count=cleaned)
        return cleaned


# 全局服務實例
_editing_session_service: Optional[EditingSessionService] = None


def get_editing_session_service() -> EditingSessionService:
    """獲取編輯 Session 服務實例（單例模式）"""
    global _editing_session_service
    if _editing_session_service is None:
        _editing_session_service = EditingSessionService()
    return _editing_session_service
