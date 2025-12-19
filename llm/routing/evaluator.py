# 代碼功能說明: LLM 路由評估器
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""實現路由性能評估、優化和 A/B 測試數據收集。"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agents.task_analyzer.models import LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class RoutingMetrics:
    """路由指標數據類。"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency: float = 0.0
    total_cost: float = 0.0
    total_tokens: int = 0
    quality_scores: List[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """計算成功率。"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def average_latency(self) -> float:
        """計算平均延遲。"""
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency / self.successful_requests

    @property
    def average_cost(self) -> float:
        """計算平均成本。"""
        if self.successful_requests == 0:
            return 0.0
        return self.total_cost / self.successful_requests

    @property
    def average_quality(self) -> float:
        """計算平均質量評分。"""
        if not self.quality_scores:
            return 0.0
        return sum(self.quality_scores) / len(self.quality_scores)


@dataclass
class RoutingDecision:
    """路由決策記錄。"""

    timestamp: float
    provider: LLMProvider
    strategy: str
    task_type: str
    success: bool
    latency: Optional[float] = None
    cost: Optional[float] = None
    quality_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RoutingEvaluator:
    """路由性能評估器。"""

    def __init__(self, max_history_size: int = 10000):
        """
        初始化評估器。

        Args:
            max_history_size: 最大歷史記錄數量
        """
        self.max_history_size = max_history_size
        self.decision_history: List[RoutingDecision] = []
        self.provider_metrics: Dict[LLMProvider, RoutingMetrics] = defaultdict(RoutingMetrics)
        self.strategy_metrics: Dict[str, RoutingMetrics] = defaultdict(RoutingMetrics)

    def record_decision(
        self,
        provider: LLMProvider,
        strategy: str,
        task_type: str,
        success: bool,
        latency: Optional[float] = None,
        cost: Optional[float] = None,
        quality_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        記錄路由決策。

        Args:
            provider: LLM 提供商
            strategy: 使用的路由策略
            task_type: 任務類型
            success: 是否成功
            latency: 延遲時間（秒）
            cost: 成本
            quality_score: 質量評分（0.0-1.0）
            metadata: 其他元數據
        """
        decision = RoutingDecision(
            timestamp=time.time(),
            provider=provider,
            strategy=strategy,
            task_type=task_type,
            success=success,
            latency=latency,
            cost=cost,
            quality_score=quality_score,
            metadata=metadata or {},
        )

        self.decision_history.append(decision)

        # 限制歷史記錄大小
        if len(self.decision_history) > self.max_history_size:
            self.decision_history = self.decision_history[-self.max_history_size :]

        # 更新提供商指標
        provider_metric = self.provider_metrics[provider]
        provider_metric.total_requests += 1
        if success:
            provider_metric.successful_requests += 1
            if latency is not None:
                provider_metric.total_latency += latency
            if cost is not None:
                provider_metric.total_cost += cost
            if quality_score is not None:
                provider_metric.quality_scores.append(quality_score)
        else:
            provider_metric.failed_requests += 1

        # 更新策略指標
        strategy_metric = self.strategy_metrics[strategy]
        strategy_metric.total_requests += 1
        if success:
            strategy_metric.successful_requests += 1
            if latency is not None:
                strategy_metric.total_latency += latency
            if cost is not None:
                strategy_metric.total_cost += cost
            if quality_score is not None:
                strategy_metric.quality_scores.append(quality_score)
        else:
            strategy_metric.failed_requests += 1

    def get_provider_metrics(self, provider: Optional[LLMProvider] = None) -> Dict[str, Any]:
        """
        獲取提供商指標。

        Args:
            provider: 提供商（可選，不提供則返回所有指標）

        Returns:
            指標字典
        """
        if provider is None:
            return {
                p.value: {
                    "success_rate": m.success_rate,
                    "average_latency": m.average_latency,
                    "average_cost": m.average_cost,
                    "average_quality": m.average_quality,
                    "total_requests": m.total_requests,
                }
                for p, m in self.provider_metrics.items()
            }

        metrics = self.provider_metrics.get(provider)
        if metrics is None:
            return {}

        return {
            "success_rate": metrics.success_rate,
            "average_latency": metrics.average_latency,
            "average_cost": metrics.average_cost,
            "average_quality": metrics.average_quality,
            "total_requests": metrics.total_requests,
            "successful_requests": metrics.successful_requests,
            "failed_requests": metrics.failed_requests,
        }

    def get_strategy_metrics(self, strategy: Optional[str] = None) -> Dict[str, Any]:
        """
        獲取策略指標。

        Args:
            strategy: 策略名稱（可選，不提供則返回所有指標）

        Returns:
            指標字典
        """
        if strategy is None:
            return {
                s: {
                    "success_rate": m.success_rate,
                    "average_latency": m.average_latency,
                    "average_cost": m.average_cost,
                    "average_quality": m.average_quality,
                    "total_requests": m.total_requests,
                }
                for s, m in self.strategy_metrics.items()
            }

        metrics = self.strategy_metrics.get(strategy)
        if metrics is None:
            return {}

        return {
            "success_rate": metrics.success_rate,
            "average_latency": metrics.average_latency,
            "average_cost": metrics.average_cost,
            "average_quality": metrics.average_quality,
            "total_requests": metrics.total_requests,
            "successful_requests": metrics.successful_requests,
            "failed_requests": metrics.failed_requests,
        }

    def calculate_quality_score(
        self,
        provider: LLMProvider,
        success_rate_weight: float = 0.4,
        latency_weight: float = 0.2,
        cost_weight: float = 0.2,
        quality_weight: float = 0.2,
    ) -> float:
        """
        計算提供商質量評分。

        Args:
            provider: LLM 提供商
            success_rate_weight: 成功率權重
            latency_weight: 延遲權重
            cost_weight: 成本權重
            quality_weight: 質量權重

        Returns:
            質量評分（0.0-1.0）
        """
        metrics = self.provider_metrics.get(provider)
        if metrics is None or metrics.total_requests == 0:
            return 0.0

        # 標準化各項指標
        success_score = metrics.success_rate

        # 延遲評分（延遲越低越好，假設最大延遲為 10 秒）
        max_latency = 10.0
        latency_score = (
            max(0.0, 1.0 - (metrics.average_latency / max_latency))
            if metrics.average_latency > 0
            else 1.0
        )

        # 成本評分（成本越低越好，假設最大成本為 1.0）
        max_cost = 1.0
        cost_score = (
            max(0.0, 1.0 - (metrics.average_cost / max_cost)) if metrics.average_cost > 0 else 1.0
        )

        # 質量評分
        quality_score = metrics.average_quality if metrics.average_quality > 0 else 0.5

        # 加權計算總分
        total_score = (
            success_score * success_rate_weight
            + latency_score * latency_weight
            + cost_score * cost_weight
            + quality_score * quality_weight
        )

        return min(1.0, max(0.0, total_score))

    def get_recommendations(self, task_type: Optional[str] = None) -> Dict[str, Any]:
        """
        獲取路由優化建議。

        Args:
            task_type: 任務類型（可選）

        Returns:
            優化建議字典
        """
        recommendations: Dict[str, Any] = {
            "best_provider": None,
            "best_strategy": None,
            "provider_rankings": [],
            "strategy_rankings": [],
        }

        # 過濾歷史記錄（如果指定了任務類型）
        if task_type:
            filtered_decisions = [d for d in self.decision_history if d.task_type == task_type]
        else:
            filtered_decisions = self.decision_history

        if not filtered_decisions:
            return recommendations

        # 計算各提供商的平均表現
        provider_scores: Dict[LLMProvider, float] = {}
        for provider in LLMProvider:
            score = self.calculate_quality_score(provider)
            if score > 0:
                provider_scores[provider] = score

        if provider_scores:
            # 排序並選擇最佳提供商
            sorted_providers = sorted(provider_scores.items(), key=lambda x: x[1], reverse=True)
            recommendations["best_provider"] = sorted_providers[0][0].value
            recommendations["provider_rankings"] = [
                {"provider": p.value, "score": s} for p, s in sorted_providers
            ]

        # 計算各策略的平均表現
        strategy_scores: Dict[str, float] = {}
        for strategy, metrics in self.strategy_metrics.items():
            if metrics.total_requests > 0:
                score = (
                    metrics.success_rate * 0.4
                    + (1.0 - min(1.0, metrics.average_latency / 10.0)) * 0.3
                    + (1.0 - min(1.0, metrics.average_cost / 1.0)) * 0.2
                    + metrics.average_quality * 0.1
                )
                strategy_scores[strategy] = score

        if strategy_scores:
            # 排序並選擇最佳策略
            sorted_strategies = sorted(strategy_scores.items(), key=lambda x: x[1], reverse=True)
            recommendations["best_strategy"] = sorted_strategies[0][0]
            recommendations["strategy_rankings"] = [
                {"strategy": s, "score": score} for s, score in sorted_strategies
            ]

        return recommendations

    def clear_history(self) -> None:
        """清空歷史記錄。"""
        self.decision_history.clear()
        self.provider_metrics.clear()
        self.strategy_metrics.clear()
        logger.info("已清空路由評估歷史記錄")
