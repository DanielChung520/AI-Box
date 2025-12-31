# 代碼功能說明: 工具調用統計和監控
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""工具調用統計和監控模組"""

import logging
import time
from collections import defaultdict
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ToolMetrics:
    """工具指標收集器"""

    def __init__(self):
        """初始化工具指標收集器"""
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "total_calls": 0,
                "success_calls": 0,
                "failure_calls": 0,
                "total_latency_ms": 0.0,
                "min_latency_ms": float("inf"),
                "max_latency_ms": 0.0,
                "error_types": defaultdict(int),
                "last_call_time": None,
                "last_success_time": None,
                "last_failure_time": None,
            }
        )

    def record_call(
        self,
        tool_name: str,
        success: bool,
        latency_ms: float,
        error_type: Optional[str] = None,
    ) -> None:
        """
        記錄工具調用

        Args:
            tool_name: 工具名稱
            success: 是否成功
            latency_ms: 延遲時間（毫秒）
            error_type: 錯誤類型（如果失敗）
        """
        metrics = self.metrics[tool_name]
        metrics["total_calls"] += 1
        metrics["total_latency_ms"] += latency_ms
        metrics["last_call_time"] = time.time()

        if success:
            metrics["success_calls"] += 1
            metrics["last_success_time"] = time.time()
        else:
            metrics["failure_calls"] += 1
            metrics["last_failure_time"] = time.time()
            if error_type:
                metrics["error_types"][error_type] += 1

        # 更新延遲統計
        if latency_ms < metrics["min_latency_ms"]:
            metrics["min_latency_ms"] = latency_ms
        if latency_ms > metrics["max_latency_ms"]:
            metrics["max_latency_ms"] = latency_ms

    def get_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        獲取工具統計信息

        Args:
            tool_name: 工具名稱，如果為 None 則返回所有工具的統計

        Returns:
            Dict[str, Any]: 統計信息
        """
        if tool_name:
            if tool_name not in self.metrics:
                return {}

            metrics = self.metrics[tool_name]
            total = metrics["total_calls"]
            if total == 0:
                return {}

            return {
                "tool_name": tool_name,
                "total_calls": total,
                "success_calls": metrics["success_calls"],
                "failure_calls": metrics["failure_calls"],
                "success_rate": metrics["success_calls"] / total if total > 0 else 0.0,
                "average_latency_ms": metrics["total_latency_ms"] / total if total > 0 else 0.0,
                "min_latency_ms": (
                    metrics["min_latency_ms"] if metrics["min_latency_ms"] != float("inf") else 0.0
                ),
                "max_latency_ms": metrics["max_latency_ms"],
                "error_types": dict(metrics["error_types"]),
                "last_call_time": metrics["last_call_time"],
                "last_success_time": metrics["last_success_time"],
                "last_failure_time": metrics["last_failure_time"],
            }
        else:
            # 返回所有工具的統計
            return {name: self.get_stats(name) for name in self.metrics.keys()}

    def get_summary(self) -> Dict[str, Any]:
        """
        獲取統計摘要

        Returns:
            Dict[str, Any]: 統計摘要
        """
        total_tools = len(self.metrics)
        total_calls = sum(m["total_calls"] for m in self.metrics.values())
        total_success = sum(m["success_calls"] for m in self.metrics.values())
        total_failure = sum(m["failure_calls"] for m in self.metrics.values())

        return {
            "total_tools": total_tools,
            "total_calls": total_calls,
            "total_success": total_success,
            "total_failure": total_failure,
            "overall_success_rate": total_success / total_calls if total_calls > 0 else 0.0,
            "tools": list(self.metrics.keys()),
        }

    def reset(self, tool_name: Optional[str] = None) -> None:
        """
        重置統計信息

        Args:
            tool_name: 工具名稱，如果為 None 則重置所有工具的統計
        """
        if tool_name:
            if tool_name in self.metrics:
                del self.metrics[tool_name]
        else:
            self.metrics.clear()


# 全局工具指標實例
_tool_metrics: Optional[ToolMetrics] = None


def get_tool_metrics() -> ToolMetrics:
    """
    獲取全局工具指標實例

    Returns:
        ToolMetrics: 工具指標實例
    """
    global _tool_metrics
    if _tool_metrics is None:
        _tool_metrics = ToolMetrics()
    return _tool_metrics
