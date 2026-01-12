# 代碼功能說明: Observation Collector Observation Summary 生成
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Observation Collector Observation Summary 生成

生成符合 GRO 規範的 Observation Summary。
"""

import logging
from typing import Any, Dict, List

from agents.services.observation_collector.fan_in import FanIn
from agents.services.observation_collector.models import FanInMode, ObservationSummary
from agents.services.orchestrator.models import TaskResult

logger = logging.getLogger(__name__)


class ObservationSummaryGenerator:
    """Observation Summary 生成器"""

    @staticmethod
    def generate_summary(
        observations: List[TaskResult | Dict[str, Any]],
        mode: FanInMode = FanInMode.ALL,
        threshold: float = 0.7,
    ) -> ObservationSummary:
        """
        生成 Observation Summary

        Args:
            observations: 觀察結果列表
            mode: Fan-in 模式
            threshold: 閾值（僅 quorum 模式使用）

        Returns:
            ObservationSummary 對象
        """
        return FanIn.fan_in(observations, mode, threshold)

    @staticmethod
    def extract_key_metrics(summary: ObservationSummary) -> Dict[str, Any]:
        """
        提取關鍵指標

        Args:
            summary: ObservationSummary 對象

        Returns:
            關鍵指標字典
        """
        return {
            "success_rate": summary.success_rate,
            "blocking_issues": summary.blocking_issues,
            "lowest_confidence": summary.lowest_confidence,
            "total_count": summary.total_count,
            "success_count": summary.success_count,
            "failure_count": summary.failure_count,
            "partial_count": summary.partial_count,
            "issue_count": len(summary.issues),
        }
