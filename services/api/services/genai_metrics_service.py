"""
代碼功能說明: GenAI Metrics（G5）- 產品級 Chat 指標彙總（memory 優先，避免高基數）
創建日期: 2025-12-13 20:15:11 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 21:00:38 (UTC+8)
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, Optional

from services.api.services.genai_trace_store_service import GenAITraceEvent


@dataclass
class _LatencyStats:
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0

    def record(self, value_ms: Optional[float]) -> None:
        if value_ms is None:
            return
        v = float(value_ms)
        if v < 0:
            return
        if self.count == 0:
            self.min_ms = v
            self.max_ms = v
        else:
            self.min_ms = min(self.min_ms, v)
            self.max_ms = max(self.max_ms, v)
        self.count += 1
        self.total_ms += v

    def to_dict(self) -> Dict[str, Any]:
        avg = (self.total_ms / self.count) if self.count else 0.0
        return {
            "count": self.count,
            "avg_ms": avg,
            "min_ms": self.min_ms if self.count else 0.0,
            "max_ms": self.max_ms if self.count else 0.0,
        }


class GenAIMetricsService:
    """MVP：以 in-memory 統計為主，提供 stats endpoint（prod_ready 但非 Prometheus）。"""

    def __init__(self, *, max_dim_keys: int = 100) -> None:
        self._lock = Lock()
        self._max_dim_keys = max(max_dim_keys, 1)

        self.chat_total = 0
        self.chat_error_total = 0
        self.memory_hit_total = 0
        self.memory_miss_total = 0
        self.failover_total = 0

        self.total_latency = _LatencyStats()
        self.llm_latency = _LatencyStats()
        self.retrieval_latency = _LatencyStats()

        self.by_provider: Dict[str, Dict[str, Any]] = {}
        self.by_strategy: Dict[str, Dict[str, Any]] = {}

    def _bump_dim(self, store: Dict[str, Dict[str, Any]], key: str, event: GenAITraceEvent) -> None:
        if not key:
            return
        if key not in store and len(store) >= self._max_dim_keys:
            return
        bucket = store.setdefault(
            key,
            {
                "chat_total": 0,
                "chat_error_total": 0,
                "failover_total": 0,
                "total_latency": _LatencyStats(),
                "llm_latency": _LatencyStats(),
                "retrieval_latency": _LatencyStats(),
            },
        )
        bucket["chat_total"] += 1
        if event.status != "ok":
            bucket["chat_error_total"] += 1
        if event.failover_used:
            bucket["failover_total"] += 1
        bucket["total_latency"].record(event.total_latency_ms)
        bucket["llm_latency"].record(event.llm_latency_ms)
        bucket["retrieval_latency"].record(event.retrieval_latency_ms)

    def record_final_event(self, event: GenAITraceEvent) -> None:
        """只建議餵 final event：chat.response_sent 或 chat.failed。"""
        with self._lock:
            self.chat_total += 1
            if event.status != "ok":
                self.chat_error_total += 1

            if event.failover_used:
                self.failover_total += 1

            hit = int(event.memory_hit_count or 0)
            if hit > 0:
                self.memory_hit_total += 1
            else:
                self.memory_miss_total += 1

            self.total_latency.record(event.total_latency_ms)
            self.llm_latency.record(event.llm_latency_ms)
            self.retrieval_latency.record(event.retrieval_latency_ms)

            if event.provider:
                self._bump_dim(self.by_provider, event.provider, event)
            if event.strategy:
                self._bump_dim(self.by_strategy, event.strategy, event)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            by_provider = {
                k: {
                    "chat_total": v["chat_total"],
                    "chat_error_total": v["chat_error_total"],
                    "failover_total": v["failover_total"],
                    "total_latency": v["total_latency"].to_dict(),
                    "llm_latency": v["llm_latency"].to_dict(),
                    "retrieval_latency": v["retrieval_latency"].to_dict(),
                }
                for k, v in self.by_provider.items()
            }
            by_strategy = {
                k: {
                    "chat_total": v["chat_total"],
                    "chat_error_total": v["chat_error_total"],
                    "failover_total": v["failover_total"],
                    "total_latency": v["total_latency"].to_dict(),
                    "llm_latency": v["llm_latency"].to_dict(),
                    "retrieval_latency": v["retrieval_latency"].to_dict(),
                }
                for k, v in self.by_strategy.items()
            }

            error_rate = (self.chat_error_total / self.chat_total) if self.chat_total else 0.0
            return {
                "chat_total": self.chat_total,
                "chat_error_total": self.chat_error_total,
                "error_rate": error_rate,
                "memory_hit_total": self.memory_hit_total,
                "memory_miss_total": self.memory_miss_total,
                "failover_total": self.failover_total,
                "total_latency": self.total_latency.to_dict(),
                "llm_latency": self.llm_latency.to_dict(),
                "retrieval_latency": self.retrieval_latency.to_dict(),
                "by_provider": by_provider,
                "by_strategy": by_strategy,
            }


_metrics_service: Optional[GenAIMetricsService] = None


def get_genai_metrics_service() -> GenAIMetricsService:
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = GenAIMetricsService()
    return _metrics_service


def reset_genai_metrics_service() -> None:
    global _metrics_service
    _metrics_service = None
