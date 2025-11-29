# 代碼功能說明: 多 LLM 負載均衡器實現
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""多 LLM 負載均衡器，擴展現有 LLMNodeRouter，支持多 LLM 提供商負載均衡。"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

from agents.task_analyzer.models import LLMProvider


logger = logging.getLogger(__name__)


@dataclass
class LLMProviderNode:
    """LLM 提供商節點（用於負載均衡）。"""

    provider: LLMProvider
    weight: int = 1
    healthy: bool = True
    active_connections: int = 0
    next_retry_ts: float = field(default=0.0)
    last_used: float = field(default_factory=time.time)
    average_latency: float = field(default=0.0)
    last_latency: float = field(default=0.0)
    response_times: Deque[float] = field(default_factory=lambda: deque(maxlen=100))

    def available(self, now: float) -> bool:
        """檢查節點是否可用。"""
        return self.healthy or now >= self.next_retry_ts


class MultiLLMLoadBalancer:
    """多 LLM 負載均衡器，支持多個 LLM 提供商的負載均衡。"""

    def __init__(
        self,
        providers: List[LLMProvider],
        strategy: str = "round_robin",
        weights: Optional[Dict[LLMProvider, int]] = None,
        cooldown_seconds: int = 30,
        health_check_callback: Optional[Callable[[LLMProvider], bool]] = None,
    ):
        """
        初始化多 LLM 負載均衡器。

        Args:
            providers: LLM 提供商列表
            strategy: 負載均衡策略（round_robin, weighted, least_connections）
            weights: 提供商權重字典（可選）
            cooldown_seconds: 故障冷卻時間（秒）
        """
        if not providers:
            raise ValueError("MultiLLMLoadBalancer requires at least one provider")

        self.strategy = strategy
        self.cooldown_seconds = max(cooldown_seconds, 5)

        # 驗證策略名稱
        valid_strategies = [
            "round_robin",
            "weighted",
            "least_connections",
            "latency_based",
            "response_time_based",
        ]
        if strategy not in valid_strategies:
            logger.warning(
                f"Unknown strategy '{strategy}', falling back to 'round_robin'"
            )
            self.strategy = "round_robin"

        # 創建提供商節點
        self._provider_nodes: Dict[LLMProvider, LLMProviderNode] = {}
        for provider in providers:
            weight = weights.get(provider, 1) if weights else 1
            self._provider_nodes[provider] = LLMProviderNode(
                provider=provider,
                weight=max(weight, 1),
            )

        self._lock = threading.Lock()
        self._rr_index = 0
        self._health_check_callback = health_check_callback

        # 統計信息
        self._total_requests: int = 0
        self._success_count: Dict[LLMProvider, int] = {}
        self._failure_count: Dict[LLMProvider, int] = {}
        self._total_latency: Dict[LLMProvider, float] = {}
        self._request_count: Dict[LLMProvider, int] = {}

    def _eligible_providers(self) -> List[LLMProviderNode]:
        """獲取可用的提供商節點。"""
        now = time.time()
        healthy = [
            node
            for node in self._provider_nodes.values()
            if node.available(now)
            and (
                self._health_check_callback is None
                or self._health_check_callback(node.provider)
            )
        ]
        return healthy or list(self._provider_nodes.values())

    def select_provider(self) -> LLMProvider:
        """
        根據策略選擇 LLM 提供商。

        Returns:
            選中的 LLM 提供商
        """
        with self._lock:
            candidates = self._eligible_providers()

            if not candidates:
                # 如果沒有可用提供商，返回第一個
                return list(self._provider_nodes.keys())[0]

            if self.strategy == "weighted":
                # 加權輪詢
                pool: List[LLMProviderNode] = []
                for node in candidates:
                    pool.extend([node] * node.weight)
                selected_node = pool[self._rr_index % len(pool)]
                self._rr_index = (self._rr_index + 1) % len(pool)
            elif self.strategy == "least_connections":
                # 最少連接
                selected_node = min(
                    candidates,
                    key=lambda n: n.active_connections,
                )
            elif self.strategy == "latency_based":
                # 基於延遲：選擇平均延遲最低的節點
                selected_node = min(
                    candidates,
                    key=lambda n: (
                        n.average_latency if n.average_latency > 0 else float("inf")
                    ),
                )
            elif self.strategy == "response_time_based":
                # 基於響應時間：選擇最近響應時間最短的節點
                selected_node = min(
                    candidates,
                    key=lambda n: (
                        n.last_latency
                        if n.last_latency > 0
                        else (
                            n.average_latency if n.average_latency > 0 else float("inf")
                        )
                    ),
                )
            else:
                # 輪詢（默認）
                selected_node = candidates[self._rr_index % len(candidates)]
                self._rr_index = (self._rr_index + 1) % len(candidates)

            # 更新使用時間和連接數
            selected_node.last_used = time.time()
            selected_node.active_connections += 1

            # 更新統計信息
            self._total_requests += 1
            self._request_count[selected_node.provider] = (
                self._request_count.get(selected_node.provider, 0) + 1
            )

            return selected_node.provider

    def mark_success(
        self, provider: LLMProvider, latency: Optional[float] = None
    ) -> None:
        """
        標記提供商成功。

        Args:
            provider: LLM 提供商
            latency: 請求延遲時間（秒，可選）
        """
        with self._lock:
            if provider in self._provider_nodes:
                node = self._provider_nodes[provider]
                node.healthy = True
                node.next_retry_ts = 0.0
                node.active_connections = max(0, node.active_connections - 1)

                # 更新統計信息
                self._success_count[provider] = self._success_count.get(provider, 0) + 1
                if latency is not None:
                    self._total_latency[provider] = (
                        self._total_latency.get(provider, 0.0) + latency
                    )
                    # 更新節點的延遲信息
                    node.last_latency = latency
                    node.response_times.append(latency)
                    # 計算平均延遲
                    if node.response_times:
                        node.average_latency = sum(node.response_times) / len(
                            node.response_times
                        )

    def mark_failure(self, provider: LLMProvider) -> None:
        """
        標記提供商失敗並啟動冷卻。

        Args:
            provider: LLM 提供商
        """
        with self._lock:
            if provider in self._provider_nodes:
                node = self._provider_nodes[provider]
                node.healthy = False
                node.next_retry_ts = time.time() + self.cooldown_seconds
                node.active_connections = max(0, node.active_connections - 1)

                # 更新統計信息
                self._failure_count[provider] = self._failure_count.get(provider, 0) + 1

                logger.warning(
                    f"Marked {provider.value} as failed, will retry after {self.cooldown_seconds}s"
                )

    def get_provider_stats(self) -> Dict[LLMProvider, Dict[str, Any]]:
        """
        獲取提供商統計信息。

        Returns:
            提供商統計字典
        """
        with self._lock:
            stats: Dict[LLMProvider, Dict[str, Any]] = {}
            now = time.time()
            for provider, node in self._provider_nodes.items():
                request_count = self._request_count.get(provider, 0)
                success_count = self._success_count.get(provider, 0)
                failure_count = self._failure_count.get(provider, 0)
                total_latency = self._total_latency.get(provider, 0.0)

                stats[provider] = {
                    "healthy": node.healthy,
                    "available": node.available(now),
                    "weight": node.weight,
                    "active_connections": node.active_connections,
                    "last_used": node.last_used,
                    "next_retry_ts": node.next_retry_ts,
                    "request_count": request_count,
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "success_rate": (
                        success_count / request_count if request_count > 0 else 0.0
                    ),
                    "average_latency": (
                        total_latency / success_count if success_count > 0 else 0.0
                    ),
                }
            return stats

    def get_overall_stats(self) -> Dict[str, Any]:
        """
        獲取整體統計信息。

        Returns:
            整體統計字典
        """
        with self._lock:
            total_success = sum(self._success_count.values())
            total_failure = sum(self._failure_count.values())
            total_requests = self._total_requests

            return {
                "total_requests": total_requests,
                "total_success": total_success,
                "total_failure": total_failure,
                "success_rate": (
                    total_success / total_requests if total_requests > 0 else 0.0
                ),
                "strategy": self.strategy,
                "provider_count": len(self._provider_nodes),
            }

    def update_weight(self, provider: LLMProvider, weight: int) -> None:
        """
        更新提供商權重。

        Args:
            provider: LLM 提供商
            weight: 新權重
        """
        with self._lock:
            if provider in self._provider_nodes:
                self._provider_nodes[provider].weight = max(1, weight)
                logger.info(f"Updated {provider.value} weight to {weight}")

    def add_provider(
        self,
        provider: LLMProvider,
        weight: int = 1,
    ) -> None:
        """
        添加提供商。

        Args:
            provider: LLM 提供商
            weight: 權重
        """
        with self._lock:
            if provider not in self._provider_nodes:
                self._provider_nodes[provider] = LLMProviderNode(
                    provider=provider,
                    weight=max(weight, 1),
                )
                logger.info(f"Added provider {provider.value} with weight {weight}")
            else:
                logger.warning(f"Provider {provider.value} already exists")

    def remove_provider(self, provider: LLMProvider) -> None:
        """
        移除提供商。

        Args:
            provider: LLM 提供商
        """
        with self._lock:
            if provider in self._provider_nodes:
                del self._provider_nodes[provider]
                logger.info(f"Removed provider {provider.value}")
            else:
                logger.warning(f"Provider {provider.value} not found")
