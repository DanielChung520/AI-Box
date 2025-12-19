# 代碼功能說明: LLM 動態路由切換器
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""實現動態路由切換、路由狀態管理和路由規則熱重載。"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseRoutingStrategy, RoutingStrategyRegistry

logger = logging.getLogger(__name__)


@dataclass
class RoutingState:
    """路由狀態。"""

    strategy_name: str
    config: Dict[str, Any]
    active: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0


@dataclass
class RoutingSwitchEvent:
    """路由切換事件。"""

    timestamp: float
    from_strategy: Optional[str]
    to_strategy: str
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class DynamicRouter:
    """動態路由切換器。"""

    def __init__(self, default_strategy: str = "hybrid"):
        """
        初始化動態路由器。

        Args:
            default_strategy: 默認路由策略名稱
        """
        self.default_strategy = default_strategy
        self.current_strategy_name: str = default_strategy
        self._lock = threading.Lock()
        self._strategy_instances: Dict[str, BaseRoutingStrategy] = {}
        self._routing_states: Dict[str, RoutingState] = {}
        self._switch_history: List[RoutingSwitchEvent] = []
        self._max_history_size = 1000

    def get_strategy(self, strategy_name: Optional[str] = None) -> BaseRoutingStrategy:
        """
        獲取路由策略實例。

        Args:
            strategy_name: 策略名稱（可選，使用當前策略）

        Returns:
            路由策略實例

        Raises:
            ValueError: 如果策略不存在
        """
        name = strategy_name or self.current_strategy_name

        with self._lock:
            if name not in self._strategy_instances:
                # 從註冊表創建策略實例
                if not RoutingStrategyRegistry.has(name):
                    raise ValueError(f"路由策略不存在: {name}")

                # 獲取策略配置（如果有的話）
                config = self._routing_states.get(name, RoutingState(name, {})).config
                strategy = RoutingStrategyRegistry.get(name, config)
                self._strategy_instances[name] = strategy

                # 創建或更新狀態
                if name not in self._routing_states:
                    self._routing_states[name] = RoutingState(strategy_name=name, config=config)

            return self._strategy_instances[name]

    def switch_strategy(
        self,
        strategy_name: str,
        reason: str = "manual_switch",
        config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        切換路由策略。

        Args:
            strategy_name: 目標策略名稱
            reason: 切換原因
            config: 策略配置（可選）
            metadata: 其他元數據
        """
        if not RoutingStrategyRegistry.has(strategy_name):
            raise ValueError(f"路由策略不存在: {strategy_name}")

        with self._lock:
            old_strategy = self.current_strategy_name
            self.current_strategy_name = strategy_name

            # 更新或創建狀態
            if strategy_name not in self._routing_states:
                self._routing_states[strategy_name] = RoutingState(
                    strategy_name=strategy_name, config=config or {}
                )
            else:
                state = self._routing_states[strategy_name]
                state.updated_at = time.time()
                if config:
                    state.config.update(config)

            # 如果配置改變，重新創建策略實例
            if config and strategy_name in self._strategy_instances:
                del self._strategy_instances[strategy_name]

            # 記錄切換事件
            event = RoutingSwitchEvent(
                timestamp=time.time(),
                from_strategy=old_strategy,
                to_strategy=strategy_name,
                reason=reason,
                metadata=metadata or {},
            )
            self._switch_history.append(event)

            # 限制歷史記錄大小
            if len(self._switch_history) > self._max_history_size:
                self._switch_history = self._switch_history[-self._max_history_size :]

            logger.info(f"路由策略已切換: {old_strategy} -> {strategy_name} (原因: {reason})")

    def reload_strategy_config(self, strategy_name: str, config: Dict[str, Any]) -> None:
        """
        重新加載策略配置（熱重載）。

        Args:
            strategy_name: 策略名稱
            config: 新配置
        """
        with self._lock:
            if strategy_name not in self._routing_states:
                self._routing_states[strategy_name] = RoutingState(
                    strategy_name=strategy_name, config=config
                )
            else:
                state = self._routing_states[strategy_name]
                state.config = config
                state.updated_at = time.time()

            # 清除策略實例以強制重新創建
            if strategy_name in self._strategy_instances:
                del self._strategy_instances[strategy_name]

            logger.info(f"策略配置已重新加載: {strategy_name}")

    def record_request(self, strategy_name: str, success: bool) -> None:
        """
        記錄請求結果。

        Args:
            strategy_name: 策略名稱
            success: 是否成功
        """
        with self._lock:
            if strategy_name not in self._routing_states:
                return

            state = self._routing_states[strategy_name]
            state.request_count += 1
            if success:
                state.success_count += 1
            else:
                state.failure_count += 1
            state.updated_at = time.time()

    def get_state(self, strategy_name: Optional[str] = None) -> Optional[RoutingState]:
        """
        獲取路由狀態。

        Args:
            strategy_name: 策略名稱（可選，使用當前策略）

        Returns:
            路由狀態
        """
        name = strategy_name or self.current_strategy_name
        with self._lock:
            return self._routing_states.get(name)

    def get_all_states(self) -> Dict[str, RoutingState]:
        """
        獲取所有路由狀態。

        Returns:
            狀態字典
        """
        with self._lock:
            return self._routing_states.copy()

    def get_switch_history(self, limit: Optional[int] = None) -> List[RoutingSwitchEvent]:
        """
        獲取切換歷史。

        Args:
            limit: 限制返回數量（可選）

        Returns:
            切換事件列表
        """
        with self._lock:
            history = self._switch_history.copy()
            if limit:
                return history[-limit:]
            return history

    def rollback(self) -> bool:
        """
        回滾到上一個策略。

        Returns:
            如果成功回滾返回 True
        """
        with self._lock:
            if len(self._switch_history) < 2:
                logger.warning("沒有足夠的歷史記錄進行回滾")
                return False

            # 獲取上一個策略
            last_event = self._switch_history[-1]
            previous_strategy = last_event.from_strategy

            if previous_strategy is None:
                previous_strategy = self.default_strategy

            # 切換回上一個策略
            self.current_strategy_name = previous_strategy

            # 記錄回滾事件
            event = RoutingSwitchEvent(
                timestamp=time.time(),
                from_strategy=last_event.to_strategy,
                to_strategy=previous_strategy,
                reason="rollback",
                metadata={"original_reason": last_event.reason},
            )
            self._switch_history.append(event)

            logger.info(f"已回滾到策略: {previous_strategy}")
            return True

    def reset_to_default(self) -> None:
        """重置到默認策略。"""
        self.switch_strategy(self.default_strategy, reason="reset_to_default")
