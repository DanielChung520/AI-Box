# -*- coding: utf-8 -*-
"""
Data-Agent-JP Token 監控模組

提供 Token 使用量監控和 Metrics 統計

建立日期: 2026-02-10
建立人: Daniel Chung
最後修改日期: 2026-02-10
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class TokenStats:
    """Token 統計資料"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    query_count: int = 0
    start_time: str = ""
    last_updated: str = ""

    def add(self, prompt: int, completion: int):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        self.query_count += 1
        self.last_updated = self._now()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "query_count": self.query_count,
            "avg_tokens_per_query": self.total_tokens / self.query_count
            if self.query_count > 0
            else 0,
            "start_time": self.start_time,
            "last_updated": self.last_updated,
        }


@dataclass
class HourlyTokenStats:
    """每小時 Token 統計"""

    hourly_data: Dict[str, TokenStats] = field(default_factory=dict)

    def add(self, hour_key: str, prompt: int, completion: int):
        if hour_key not in self.hourly_data:
            self.hourly_data[hour_key] = TokenStats()
        self.hourly_data[hour_key].add(prompt, completion)

    def get_today_stats(self) -> Dict[str, TokenStats]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return {k: v for k, v in self.hourly_data.items() if k.startswith(today)}


class TokenMonitor:
    """
    Token 使用量監控器

    功能：
    - 追蹤 Token 使用量
    - 提供 Prometheus Metrics 格式輸出
    - 計算每日/每小時統計
    - 預估成本
    """

    # Token 單價 (USD) - 可根據實際使用情況調整
    PROMPT_TOKEN_COST_PER_1M = 0.01  # $0.01 per 1M prompt tokens
    COMPLETION_TOKEN_COST_PER_1M = 0.03  # $0.03 per 1M completion tokens

    def __init__(self):
        self._lock = Lock()
        self._total_stats = TokenStats()
        self._today_stats = TokenStats()
        self._hourly_stats = HourlyTokenStats()
        self._query_stats: Dict[str, TokenStats] = defaultdict(TokenStats)
        self._initialized = False

    def initialize(self):
        """初始化監控器"""
        with self._lock:
            if not self._initialized:
                now = datetime.now(timezone.utc).isoformat()
                self._total_stats.start_time = now
                self._today_stats.start_time = now
                self._initialized = True
                logger.info("Token Monitor initialized")

    def record(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        query_type: str = "unknown",
        intent: str = "",
    ):
        """
        記錄 Token 使用量

        Args:
            prompt_tokens: Prompt Token 數量
            completion_tokens: Completion Token 數量
            query_type: 查詢類型
            intent: 意圖名稱
        """
        if not self._initialized:
            self.initialize()

        total = prompt_tokens + completion_tokens
        now = datetime.now(timezone.utc)
        hour_key = now.strftime("%Y-%m-%d %H:00")
        today_key = now.strftime("%Y-%m-%d")

        with self._lock:
            self._total_stats.add(prompt_tokens, completion_tokens)
            self._hourly_stats.add(hour_key, prompt_tokens, completion_tokens)

            today_key_exists = today_key in self._today_stats.to_dict().get("start_time", "")
            if not today_key_exists or self._today_stats.query_count == 0:
                self._today_stats.start_time = now.isoformat()

            self._today_stats.add(prompt_tokens, completion_tokens)

            query_key = f"{query_type}:{intent}" if intent else query_type
            self._query_stats[query_key].add(prompt_tokens, completion_tokens)

        logger.debug(
            f"Token recorded: prompt={prompt_tokens}, completion={completion_tokens}, "
            f"total={total}, query_type={query_type}"
        )

    def get_total_stats(self) -> Dict[str, Any]:
        """取得總統計"""
        with self._lock:
            stats = self._total_stats.to_dict()
            stats["estimated_cost_usd"] = self._calculate_cost(
                stats["prompt_tokens"], stats["completion_tokens"]
            )
            return stats

    def get_today_stats(self) -> Dict[str, Any]:
        """取得今日統計"""
        with self._lock:
            stats = self._today_stats.to_dict()
            stats["estimated_cost_usd"] = self._calculate_cost(
                stats["prompt_tokens"], stats["completion_tokens"]
            )
            return stats

    def get_hourly_stats(self) -> Dict[str, Dict[str, Any]]:
        """取得每小時統計"""
        with self._lock:
            return {hour: stats.to_dict() for hour, stats in self._hourly_stats.hourly_data.items()}

    def get_query_stats(self) -> Dict[str, Dict[str, Any]]:
        """取得查詢類型統計"""
        with self._lock:
            return {query: stats.to_dict() for query, stats in self._query_stats.items()}

    def get_prometheus_metrics(self) -> str:
        """
        取得 Prometheus Metrics 格式輸出

        Returns:
            str: Metrics 格式字串
        """
        total = self._total_stats.to_dict()
        today = self._today_stats.to_dict()

        metrics = [
            "# HELP data_agent_token_prompt_total Total prompt tokens processed",
            "# TYPE data_agent_token_prompt_total counter",
            f"data_agent_token_prompt_total {total['prompt_tokens']}",
            "",
            "# HELP data_agent_token_completion_total Total completion tokens generated",
            "# TYPE data_agent_token_completion_total counter",
            f"data_agent_token_completion_total {total['completion_tokens']}",
            "",
            "# HELP data_agent_token_total Total tokens (prompt + completion)",
            "# TYPE data_agent_token_total counter",
            f"data_agent_token_total {total['total_tokens']}",
            "",
            "# HELP data_agent_token_cost_estimated_usd Estimated cost in USD",
            "# TYPE data_agent_token_cost_estimated_usd gauge",
            f"data_agent_token_cost_estimated_usd {self._calculate_cost(total['prompt_tokens'], total['completion_tokens'])}",
            "",
            "# HELP data_agent_query_total Total number of queries",
            "# TYPE data_agent_query_total counter",
            f"data_agent_query_total {total['query_count']}",
            "",
            "# HELP data_agent_token_prompt_daily Daily prompt tokens",
            "# TYPE data_agent_token_prompt_daily counter",
            f"data_agent_token_prompt_daily {today['prompt_tokens']}",
            "",
            "# HELP data_agent_token_completion_daily Daily completion tokens",
            "# TYPE data_agent_token_completion_daily counter",
            f"data_agent_token_completion_daily {today['completion_tokens']}",
            "",
            "# HELP data_agent_token_total_daily Daily total tokens",
            "# TYPE data_agent_token_total_daily counter",
            f"data_agent_token_total_daily {today['total_tokens']}",
            "",
            "# HELP data_agent_token_avg_per_query Average tokens per query",
            "# TYPE data_agent_token_avg_per_query gauge",
            f"data_agent_token_avg_per_query {today.get('avg_tokens_per_query', 0)}",
        ]

        return "\n".join(metrics)

    def reset_today_stats(self):
        """重置今日統計"""
        with self._lock:
            self._today_stats = TokenStats()
            self._today_stats.start_time = datetime.now(timezone.utc).isoformat()
            logger.info("Today's token stats reset")

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        計算預估成本

        Args:
            prompt_tokens: Prompt Token 數量
            completion_tokens: Completion Token 數量

        Returns:
            float: 預估成本 (USD)
        """
        return (prompt_tokens / 1_000_000) * self.PROMPT_TOKEN_COST_PER_1M + (
            completion_tokens / 1_000_000
        ) * self.COMPLETION_TOKEN_COST_PER_1M

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        取得 Dashboard 摘要

        Returns:
            Dict: Dashboard 顯示用的摘要資料
        """
        total = self.get_total_stats()
        today = self.get_today_stats()
        hourly = self.get_hourly_stats()

        sorted_hourly = dict(
            sorted(
                hourly.items(),
                key=lambda x: x[0],
                reverse=True,
            )
        )

        return {
            "total": total,
            "today": today,
            "hourly_distribution": sorted_hourly,
            "cost_per_1m_prompt": self.PROMPT_TOKEN_COST_PER_1M,
            "cost_per_1m_completion": self.COMPLETION_TOKEN_COST_PER_1M,
        }


# Singleton instance
_token_monitor: Optional[TokenMonitor] = None


def get_token_monitor() -> TokenMonitor:
    """取得 Token Monitor Singleton"""
    global _token_monitor
    if _token_monitor is None:
        _token_monitor = TokenMonitor()
        _token_monitor.initialize()
    return _token_monitor


def record_token_usage(
    prompt_tokens: int,
    completion_tokens: int,
    query_type: str = "schema_driven_query",
    intent: str = "",
):
    """
    便利函式：記錄 Token 使用量

    Args:
        prompt_tokens: Prompt Token 數量
        completion_tokens: Completion Token 數量
        query_type: 查詢類型
        intent: 意圖名稱
    """
    monitor = get_token_monitor()
    monitor.record(prompt_tokens, completion_tokens, query_type, intent)


class TokenMetricsMiddleware:
    """中間件：用於自動記錄 Parser 的 Token 使用量"""

    def __init__(self, monitor: Optional[TokenMonitor] = None):
        self.monitor = monitor or get_token_monitor()

    def record_parse_result(
        self,
        prompt: str,
        result: Dict[str, Any],
        query_type: str = "schema_driven_query",
    ):
        """
        記錄解析結果的 Token 使用量

        Args:
            prompt: 輸入的 Prompt
            result: LLM 回傳結果
            query_type: 查詢類型
        """
        prompt_tokens = result.get("prompt_eval_count", len(prompt) // 4)
        completion_tokens = result.get("eval_count", 0)
        intent = result.get("parsed", {}).get("intent", "")

        self.monitor.record(prompt_tokens, completion_tokens, query_type, intent)
