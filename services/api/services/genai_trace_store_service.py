"""
代碼功能說明: GenAI Trace Store（G5）- 以 request_id 為核心的事件回溯存儲（memory 優先，預留擴充）
創建日期: 2025-12-13 20:15:11 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 21:00:38 (UTC+8)
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict, dataclass, field
from threading import Lock
from typing import Any, Deque, Dict, List, Optional


@dataclass
class GenAITraceEvent:
    """G5：統一觀測事件結構（供 log / trace store / metrics 使用）。"""

    event: str

    request_id: str
    session_id: str
    task_id: Optional[str]
    user_id: str

    # routing
    provider: Optional[str] = None
    model: Optional[str] = None
    strategy: Optional[str] = None
    failover_used: Optional[bool] = None
    fallback_provider: Optional[str] = None

    # memory
    memory_hit_count: Optional[int] = None
    memory_sources: Optional[List[str]] = None
    retrieval_latency_ms: Optional[float] = None
    context_message_count: Optional[int] = None

    # latency
    total_latency_ms: Optional[float] = None
    llm_latency_ms: Optional[float] = None

    # token/cost
    token_input: Optional[int] = None
    token_output: Optional[int] = None
    cost: Optional[float] = None

    # outcome
    status: str = "ok"  # ok/error
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    created_at_ms: float = field(default_factory=lambda: time.time() * 1000.0)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GenAITraceStoreService:
    """以 request_id 為主鍵的 in-memory trace store（MVP）。"""

    def __init__(
        self,
        *,
        max_requests: int = 1000,
        max_events_per_request: int = 100,
        max_recent: int = 200,
    ) -> None:
        self._max_requests = max(max_requests, 1)
        self._max_events_per_request = max(max_events_per_request, 1)
        self._max_recent = max(max_recent, 1)

        self._lock = Lock()
        self._events_by_request: Dict[str, List[GenAITraceEvent]] = {}
        self._request_order: Deque[str] = deque()
        self._recent_events: Deque[GenAITraceEvent] = deque()

    def add_event(self, event: GenAITraceEvent) -> None:
        with self._lock:
            rid = event.request_id
            if rid not in self._events_by_request:
                self._events_by_request[rid] = []
                self._request_order.append(rid)

            events = self._events_by_request[rid]
            events.append(event)
            if len(events) > self._max_events_per_request:
                self._events_by_request[rid] = events[-self._max_events_per_request :]

            self._recent_events.append(event)
            while len(self._recent_events) > self._max_recent:
                self._recent_events.popleft()

            while len(self._request_order) > self._max_requests:
                old = self._request_order.popleft()
                self._events_by_request.pop(old, None)

    def get_trace(self, *, request_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            events = self._events_by_request.get(request_id, [])
            return [e.to_dict() for e in events]

    def list_recent(
        self,
        *,
        limit: int = 50,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        event: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        safe_limit = max(min(int(limit), self._max_recent), 1)
        with self._lock:
            items = list(self._recent_events)[-safe_limit:]

        out: List[Dict[str, Any]] = []
        for e in reversed(items):
            if user_id and e.user_id != user_id:
                continue
            if session_id and e.session_id != session_id:
                continue
            if task_id and e.task_id != task_id:
                continue
            if event and e.event != event:
                continue
            out.append(e.to_dict())
            if len(out) >= safe_limit:
                break
        return out


_trace_store: Optional[GenAITraceStoreService] = None


def get_genai_trace_store_service() -> GenAITraceStoreService:
    global _trace_store
    if _trace_store is None:
        _trace_store = GenAITraceStoreService()
    return _trace_store


def reset_genai_trace_store_service() -> None:
    global _trace_store
    _trace_store = None
