# 代碼功能說明: LLM 路由策略基類定義
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""定義路由策略基類和策略註冊機制。"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from agents.task_analyzer.models import LLMProvider, TaskClassificationResult

logger = logging.getLogger(__name__)


class RoutingResult:
    """路由策略選擇結果。"""

    def __init__(
        self,
        provider: LLMProvider,
        confidence: float,
        reasoning: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.provider = provider
        self.confidence = confidence
        self.reasoning = reasoning
        self.metadata = metadata or {}


class BaseRoutingStrategy(ABC):
    """路由策略抽象基類。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化路由策略。

        Args:
            config: 策略配置字典
        """
        self.config = config or {}
        self._metrics: Dict[str, Any] = {}

    @abstractmethod
    def select_provider(
        self,
        task_classification: TaskClassificationResult,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingResult:
        """
        選擇 LLM 提供商。

        Args:
            task_classification: 任務分類結果
            task: 任務描述
            context: 上下文信息

        Returns:
            路由選擇結果
        """
        raise NotImplementedError

    @abstractmethod
    def evaluate(
        self,
        provider: LLMProvider,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        評估提供商對任務的適合度。

        Args:
            provider: LLM 提供商
            task_type: 任務類型
            context: 上下文信息

        Returns:
            適合度分數（0.0-1.0）
        """
        raise NotImplementedError

    def update_metrics(
        self,
        provider: LLMProvider,
        success: bool,
        latency: Optional[float] = None,
        cost: Optional[float] = None,
    ) -> None:
        """
        更新路由指標。

        Args:
            provider: LLM 提供商
            success: 是否成功
            latency: 延遲時間（秒）
            cost: 成本
        """
        if provider.value not in self._metrics:
            self._metrics[provider.value] = {
                "total_requests": 0,
                "successful_requests": 0,
                "total_latency": 0.0,
                "total_cost": 0.0,
            }

        metrics = self._metrics[provider.value]
        metrics["total_requests"] += 1
        if success:
            metrics["successful_requests"] += 1
        if latency is not None:
            metrics["total_latency"] += latency
        if cost is not None:
            metrics["total_cost"] += cost

    def get_metrics(self, provider: Optional[LLMProvider] = None) -> Dict[str, Any]:
        """
        獲取路由指標。

        Args:
            provider: 提供商（可選，不提供則返回所有指標）

        Returns:
            指標字典
        """
        if provider is None:
            return self._metrics.copy()
        return self._metrics.get(provider.value, {}).copy()

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """返回策略名稱。"""
        raise NotImplementedError


class RoutingStrategyRegistry:
    """路由策略註冊表。"""

    _strategies: Dict[str, type[BaseRoutingStrategy]] = {}

    @classmethod
    def register(cls, name: str, strategy_class: type[BaseRoutingStrategy]) -> None:
        """
        註冊路由策略。

        Args:
            name: 策略名稱
            strategy_class: 策略類
        """
        if name in cls._strategies:
            logger.warning(f"策略 {name} 已存在，將被覆蓋")
        cls._strategies[name] = strategy_class
        logger.info(f"已註冊路由策略: {name}")

    @classmethod
    def get(
        cls, name: str, config: Optional[Dict[str, Any]] = None
    ) -> BaseRoutingStrategy:
        """
        獲取路由策略實例。

        Args:
            name: 策略名稱
            config: 策略配置

        Returns:
            策略實例

        Raises:
            ValueError: 如果策略不存在
        """
        if name not in cls._strategies:
            raise ValueError(f"未找到路由策略: {name}")
        return cls._strategies[name](config)

    @classmethod
    def list_strategies(cls) -> List[str]:
        """
        列出所有已註冊的策略。

        Returns:
            策略名稱列表
        """
        return list(cls._strategies.keys())

    @classmethod
    def has(cls, name: str) -> bool:
        """
        檢查策略是否已註冊。

        Args:
            name: 策略名稱

        Returns:
            如果已註冊返回 True
        """
        return name in cls._strategies
