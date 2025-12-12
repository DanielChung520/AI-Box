# 代碼功能說明: LangChain/Graph Context Recorder
# 創建日期: 2025-11-26 20:07 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 20:07 (UTC+8)

"""提供簡易 Context Recorder，支援 Redis 或記憶體儲存。"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import redis  # type: ignore[import-untyped]

from agents.workflows.settings import LangChainGraphSettings

logger = logging.getLogger(__name__)


class ContextRecorder:
    """負責儲存與讀取工作流上下文狀態。"""

    def __init__(
        self, *, redis_url: Optional[str], namespace: str, ttl_seconds: int
    ) -> None:
        self._namespace = namespace
        self._ttl = ttl_seconds
        self._memory_store: Dict[str, Dict[str, Any]] = {}
        self._redis = None
        if redis_url:
            try:
                self._redis = redis.Redis.from_url(redis_url)
            except Exception as exc:  # pragma: no cover - redis 啟動失敗時 fallback
                logger.warning(
                    "Context Recorder 初始化 Redis 失敗，使用記憶體儲存: %s", exc
                )

    def _key(self, task_id: str) -> str:
        return f"{self._namespace}:{task_id}"

    def save(self, task_id: str, state: Dict[str, Any]) -> None:
        if self._redis:
            payload = json.dumps(
                state, default=lambda obj: getattr(obj, "__dict__", str(obj))
            )
            self._redis.setex(self._key(task_id), self._ttl, payload)
        else:
            self._memory_store[task_id] = state

    def load(self, task_id: str) -> Optional[Dict[str, Any]]:
        if self._redis:
            raw = self._redis.get(self._key(task_id))
            if not raw:
                return None
            if isinstance(raw, bytes):
                return json.loads(raw.decode("utf-8"))
            # 處理其他類型（如 str）
            return json.loads(raw)  # type: ignore[arg-type]
        return self._memory_store.get(task_id)


def build_context_recorder(settings: LangChainGraphSettings) -> ContextRecorder:
    """根據設定建立 Context Recorder。"""

    redis_url = (
        settings.state_store.redis_url
        if settings.state_store.backend.lower() == "redis"
        else None
    )
    return ContextRecorder(
        redis_url=redis_url,
        namespace=f"{settings.state_store.namespace}:context",
        ttl_seconds=settings.state_store.ttl_seconds,
    )
