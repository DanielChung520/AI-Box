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
from typing import Any, Dict, List, Optional

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

    def _eligible_providers(self) -> List[LLMProviderNode]:
        """獲取可用的提供商節點。"""
        now = time.time()
        healthy = [
            node for node in self._provider_nodes.values() if node.available(now)
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
            else:
                # 輪詢（默認）
                selected_node = candidates[self._rr_index % len(candidates)]
                self._rr_index = (self._rr_index + 1) % len(candidates)

            # 更新使用時間和連接數
            selected_node.last_used = time.time()
            selected_node.active_connections += 1

            return selected_node.provider

    def mark_success(self, provider: LLMProvider) -> None:
        """
        標記提供商成功。

        Args:
            provider: LLM 提供商
        """
        with self._lock:
            if provider in self._provider_nodes:
                node = self._provider_nodes[provider]
                node.healthy = True
                node.next_retry_ts = 0.0
                node.active_connections = max(0, node.active_connections - 1)

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
                stats[provider] = {
                    "healthy": node.healthy,
                    "available": node.available(now),
                    "weight": node.weight,
                    "active_connections": node.active_connections,
                    "last_used": node.last_used,
                    "next_retry_ts": node.next_retry_ts,
                }
            return stats

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
