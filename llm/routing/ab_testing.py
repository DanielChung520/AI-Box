# 代碼功能說明: LLM 路由 A/B 測試框架
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""實現 A/B 測試框架，支持流量分配、結果收集和統計分析。"""

from __future__ import annotations

import hashlib
import logging
import statistics
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from agents.task_analyzer.models import LLMProvider

logger = logging.getLogger(__name__)


class TrafficAllocationMethod(str, Enum):
    """流量分配方法。"""

    USER_ID = "user_id"  # 按用戶 ID
    SESSION_ID = "session_id"  # 按會話 ID
    TASK_TYPE = "task_type"  # 按任務類型
    RANDOM = "random"  # 隨機分配
    HASH = "hash"  # 哈希分配


@dataclass
class ABTestGroup:
    """A/B 測試組。"""

    name: str
    strategy: str
    traffic_percentage: float
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ABTestResult:
    """A/B 測試結果。"""

    provider: LLMProvider
    success: bool
    latency: Optional[float] = None
    cost: Optional[float] = None
    quality_score: Optional[float] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ABTestMetrics:
    """A/B 測試指標。"""

    group_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency: float = 0.0
    total_cost: float = 0.0
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
        """計算平均質量。"""
        if not self.quality_scores:
            return 0.0
        return statistics.mean(self.quality_scores)


class ABTestManager:
    """A/B 測試管理器。"""

    def __init__(
        self,
        test_name: str,
        groups: List[ABTestGroup],
        allocation_method: TrafficAllocationMethod = TrafficAllocationMethod.RANDOM,
    ):
        """
        初始化 A/B 測試管理器。

        Args:
            test_name: 測試名稱
            groups: 測試組列表
            allocation_method: 流量分配方法
        """
        self.test_name = test_name
        self.groups = groups
        self.allocation_method = allocation_method
        self.active = True
        self.created_at = time.time()

        # 驗證流量分配總和
        total_percentage = sum(g.traffic_percentage for g in groups)
        if abs(total_percentage - 1.0) > 0.01:
            raise ValueError(f"流量分配總和必須為 1.0，當前為 {total_percentage}")

        # 初始化指標
        self.group_metrics: Dict[str, ABTestMetrics] = {
            group.name: ABTestMetrics(group_name=group.name) for group in groups
        }

        # 分配記錄（用於一致性分配）
        self.allocations: Dict[str, str] = {}

    def assign_group(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> ABTestGroup:
        """
        分配測試組。

        Args:
            user_id: 用戶 ID
            session_id: 會話 ID
            task_type: 任務類型

        Returns:
            分配的測試組
        """
        if not self.active:
            # 如果測試已停止，返回第一個組
            return self.groups[0]

        allocation_key: Optional[str] = None

        if self.allocation_method == TrafficAllocationMethod.USER_ID:
            allocation_key = user_id
        elif self.allocation_method == TrafficAllocationMethod.SESSION_ID:
            allocation_key = session_id
        elif self.allocation_method == TrafficAllocationMethod.TASK_TYPE:
            allocation_key = task_type
        elif self.allocation_method == TrafficAllocationMethod.HASH:
            # 使用多個字段的哈希
            key_str = f"{user_id}:{session_id}:{task_type}"
            allocation_key = hashlib.md5(key_str.encode()).hexdigest()

        # 檢查是否已分配
        if allocation_key and allocation_key in self.allocations:
            group_name = self.allocations[allocation_key]
            for group in self.groups:
                if group.name == group_name:
                    return group

        # 根據流量百分比分配
        import random

        rand = (
            random.random()
            if allocation_key is None
            else (int(hashlib.md5(allocation_key.encode()).hexdigest(), 16) / (16**32))
        )

        cumulative = 0.0
        for group in self.groups:
            cumulative += group.traffic_percentage
            if rand <= cumulative:
                # 記錄分配
                if allocation_key:
                    self.allocations[allocation_key] = group.name
                return group

        # 默認返回最後一個組
        return self.groups[-1]

    def record_result(
        self,
        group_name: str,
        provider: LLMProvider,
        success: bool,
        latency: Optional[float] = None,
        cost: Optional[float] = None,
        quality_score: Optional[float] = None,
    ) -> None:
        """
        記錄測試結果。

        Args:
            group_name: 測試組名稱
            provider: LLM 提供商
            success: 是否成功
            latency: 延遲時間（秒）
            cost: 成本
            quality_score: 質量評分（0.0-1.0）
        """
        if group_name not in self.group_metrics:
            logger.warning(f"未知的測試組: {group_name}")
            return

        metrics = self.group_metrics[group_name]
        metrics.total_requests += 1

        if success:
            metrics.successful_requests += 1
            if latency is not None:
                metrics.total_latency += latency
            if cost is not None:
                metrics.total_cost += cost
            if quality_score is not None:
                metrics.quality_scores.append(quality_score)
        else:
            metrics.failed_requests += 1

    def get_metrics(self, group_name: Optional[str] = None) -> Dict[str, Any]:
        """
        獲取測試指標。

        Args:
            group_name: 組名稱（可選，不提供則返回所有組）

        Returns:
            指標字典
        """
        if group_name:
            metrics = self.group_metrics.get(group_name)
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

        return {
            name: {
                "success_rate": m.success_rate,
                "average_latency": m.average_latency,
                "average_cost": m.average_cost,
                "average_quality": m.average_quality,
                "total_requests": m.total_requests,
            }
            for name, m in self.group_metrics.items()
        }

    def calculate_statistical_significance(
        self, group1_name: str, group2_name: str, metric: str = "success_rate"
    ) -> Dict[str, Any]:
        """
        計算統計顯著性。

        Args:
            group1_name: 第一組名稱
            group2_name: 第二組名稱
            metric: 指標名稱（success_rate, average_latency, average_cost, average_quality）

        Returns:
            統計分析結果
        """
        metrics1 = self.group_metrics.get(group1_name)
        metrics2 = self.group_metrics.get(group2_name)

        if metrics1 is None or metrics2 is None:
            return {"error": "組不存在"}

        # 獲取指標值
        if metric == "success_rate":
            value1 = metrics1.success_rate
            value2 = metrics2.success_rate
            n1 = metrics1.total_requests
            n2 = metrics2.total_requests
        elif metric == "average_latency":
            value1 = metrics1.average_latency
            value2 = metrics2.average_latency
            n1 = metrics1.successful_requests
            n2 = metrics2.successful_requests
        elif metric == "average_cost":
            value1 = metrics1.average_cost
            value2 = metrics2.average_cost
            n1 = metrics1.successful_requests
            n2 = metrics2.successful_requests
        elif metric == "average_quality":
            value1 = metrics1.average_quality
            value2 = metrics2.average_quality
            n1 = len(metrics1.quality_scores)
            n2 = len(metrics2.quality_scores)
        else:
            return {"error": f"不支持的指標: {metric}"}

        if n1 == 0 or n2 == 0:
            return {"error": "樣本數量不足"}

        # 簡化的統計顯著性計算（t-test）
        # 這裡使用簡化版本，實際應用中可以使用 scipy.stats
        diff = abs(value1 - value2)
        pooled_std = (
            (value1 * (1 - value1) / n1 + value2 * (1 - value2) / n2) ** 0.5
            if metric == "success_rate"
            else 0.1  # 簡化假設
        )

        if pooled_std == 0:
            z_score = 0.0
        else:
            z_score = diff / pooled_std

        # 簡化的 p-value 計算（使用 z-score）
        # 實際應用中應該使用正確的統計測試
        p_value = 2 * (1 - 0.5 * (1 + z_score / (1 + z_score**2) ** 0.5))

        significant = p_value < 0.05

        return {
            "group1_value": value1,
            "group2_value": value2,
            "difference": diff,
            "z_score": z_score,
            "p_value": p_value,
            "significant": significant,
            "n1": n1,
            "n2": n2,
        }

    def generate_report(self) -> Dict[str, Any]:
        """
        生成測試報告。

        Returns:
            測試報告字典
        """
        report: Dict[str, Any] = {
            "test_name": self.test_name,
            "active": self.active,
            "created_at": self.created_at,
            "allocation_method": self.allocation_method.value,
            "groups": [],
            "comparisons": [],
        }

        # 添加各組指標
        for group in self.groups:
            metrics = self.group_metrics[group.name]
            report["groups"].append(
                {
                    "name": group.name,
                    "strategy": group.strategy,
                    "traffic_percentage": group.traffic_percentage,
                    "metrics": {
                        "success_rate": metrics.success_rate,
                        "average_latency": metrics.average_latency,
                        "average_cost": metrics.average_cost,
                        "average_quality": metrics.average_quality,
                        "total_requests": metrics.total_requests,
                    },
                }
            )

        # 添加組間比較
        if len(self.groups) >= 2:
            for i in range(len(self.groups) - 1):
                for j in range(i + 1, len(self.groups)):
                    group1 = self.groups[i]
                    group2 = self.groups[j]

                    comparison: Dict[str, Any] = {
                        "group1": group1.name,
                        "group2": group2.name,
                        "metrics": {},
                    }

                    for metric in [
                        "success_rate",
                        "average_latency",
                        "average_cost",
                        "average_quality",
                    ]:
                        sig_result = self.calculate_statistical_significance(
                            group1.name, group2.name, metric
                        )
                        metrics_dict: Dict[str, Any] = comparison["metrics"]
                        metrics_dict[metric] = sig_result

                    report["comparisons"].append(comparison)

        return report

    def stop(self) -> None:
        """停止測試。"""
        self.active = False
        logger.info(f"A/B 測試已停止: {self.test_name}")

    def resume(self) -> None:
        """恢復測試。"""
        self.active = True
        logger.info(f"A/B 測試已恢復: {self.test_name}")
