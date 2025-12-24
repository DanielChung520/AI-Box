# 代碼功能說明: 系統監控指標收集器
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""系統監控指標收集器模組"""

import logging
from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Any, Dict

logger = logging.getLogger(__name__)


class Metrics:
    """系統指標收集器"""

    def __init__(self):
        """初始化指標收集器"""
        self.request_count = 0
        self.error_count = 0
        self.total_latency = 0.0
        self.method_counts = defaultdict(int)
        self.method_errors = defaultdict(int)
        self.method_latencies = defaultdict(list)
        self.lock = Lock()
        self.start_time = datetime.now()

    def record_request(self, method: str, latency: float, is_error: bool = False) -> None:
        """
        記錄請求指標

        Args:
            method: 請求方法名稱
            latency: 請求延遲（秒）
            is_error: 是否為錯誤請求
        """
        with self.lock:
            self.request_count += 1
            self.total_latency += latency
            self.method_counts[method] += 1
            self.method_latencies[method].append(latency)

            if is_error:
                self.error_count += 1
                self.method_errors[method] += 1

            # 保持每個方法的延遲記錄不超過 1000 條
            if len(self.method_latencies[method]) > 1000:
                self.method_latencies[method] = self.method_latencies[method][-1000:]

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計信息

        Returns:
            Dict[str, Any]: 統計信息字典
        """
        with self.lock:
            uptime = (datetime.now() - self.start_time).total_seconds()
            avg_latency = self.total_latency / self.request_count if self.request_count > 0 else 0.0
            error_rate = self.error_count / self.request_count if self.request_count > 0 else 0.0

            method_stats = {}
            for method in self.method_counts:
                method_latencies = self.method_latencies[method]
                method_stats[method] = {
                    "count": self.method_counts[method],
                    "errors": self.method_errors[method],
                    "error_rate": (
                        self.method_errors[method] / self.method_counts[method]
                        if self.method_counts[method] > 0
                        else 0.0
                    ),
                    "avg_latency": (
                        sum(method_latencies) / len(method_latencies) if method_latencies else 0.0
                    ),
                    "min_latency": min(method_latencies) if method_latencies else 0.0,
                    "max_latency": max(method_latencies) if method_latencies else 0.0,
                }

            return {
                "uptime_seconds": uptime,
                "total_requests": self.request_count,
                "total_errors": self.error_count,
                "error_rate": error_rate,
                "avg_latency_seconds": avg_latency,
                "methods": method_stats,
            }

    def reset(self) -> None:
        """重置指標"""
        with self.lock:
            self.request_count = 0
            self.error_count = 0
            self.total_latency = 0.0
            self.method_counts.clear()
            self.method_errors.clear()
            self.method_latencies.clear()
            self.start_time = datetime.now()


# 全局指標實例
_metrics = Metrics()


def get_metrics() -> Metrics:
    """
    獲取全局指標實例

    Returns:
        Metrics: 指標實例
    """
    return _metrics
