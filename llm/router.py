# 代碼功能說明: LLM 節點負載均衡器（輪詢/加權/健康檢查）
# 創建日期: 2025-11-25 23:57 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 23:57 (UTC+8)

"""支援本地 LLM 節點的負載均衡策略。"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class LLMNodeConfig:
    """節點設定（通常來自 config.json）。"""

    name: str
    host: str
    port: int
    weight: int = 1


@dataclass
class LLMNode:
    """節點執行時狀態。"""

    name: str
    host: str
    port: int
    weight: int = 1
    healthy: bool = True
    next_retry_ts: float = field(default=0.0)

    def available(self, now: float) -> bool:
        return self.healthy or now >= self.next_retry_ts

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class LLMNodeRouter:
    """提供輪詢、加權輪詢與健康檢查時間控制的節點選擇器。"""

    def __init__(
        self,
        nodes: List[LLMNodeConfig],
        strategy: str = "round_robin",
        cooldown_seconds: int = 30,
    ):
        if not nodes:
            raise ValueError("LLMNodeRouter requires at least one node")

        self.strategy = strategy
        self.cooldown_seconds = max(cooldown_seconds, 5)
        self._nodes: List[LLMNode] = [
            LLMNode(
                name=node.name,
                host=node.host,
                port=node.port,
                weight=max(node.weight, 1),
            )
            for node in nodes
        ]
        self._lock = threading.Lock()
        self._rr_index = 0

    def _eligible_nodes(self) -> List[LLMNode]:
        now = time.time()
        healthy = [node for node in self._nodes if node.available(now)]
        return healthy or self._nodes

    def select_node(self) -> LLMNode:
        """依策略挑選下一個節點。"""
        with self._lock:
            candidates = self._eligible_nodes()
            if self.strategy == "weighted":
                pool: List[LLMNode] = []
                for node in candidates:
                    pool.extend([node] * node.weight)
                node = pool[self._rr_index % len(pool)]
            else:
                node = candidates[self._rr_index % len(candidates)]
            self._rr_index = (self._rr_index + 1) % len(candidates)
            return node

    def mark_failure(self, node_name: str) -> None:
        """標記節點失敗並啟動冷卻。"""
        with self._lock:
            for node in self._nodes:
                if node.name == node_name:
                    node.healthy = False
                    node.next_retry_ts = time.time() + self.cooldown_seconds
                    break

    def mark_success(self, node_name: str) -> None:
        """成功後恢復節點狀態。"""
        with self._lock:
            for node in self._nodes:
                if node.name == node_name:
                    node.healthy = True
                    node.next_retry_ts = 0.0
                    break

    def get_nodes(self) -> List[LLMNode]:
        """取得節點快照（thread-safe 副本）。"""
        with self._lock:
            return [LLMNode(**vars(node)) for node in self._nodes]
