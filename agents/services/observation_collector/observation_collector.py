# 代碼功能說明: Observation Collector 核心類
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Observation Collector 核心類

實現 fan-in 匯整機制，生成 Observation Summary。
"""

import asyncio
import logging
from typing import Any, Dict, List

from agents.services.observation_collector.fan_in import FanIn
from agents.services.observation_collector.models import FanInMode, ObservationSummary
from agents.services.observation_collector.observation_summary import ObservationSummaryGenerator
from agents.services.orchestrator.models import TaskResult

logger = logging.getLogger(__name__)


class ObservationCollector:
    """Observation Collector 核心類

    實現 fan-in 匯整機制，生成 Observation Summary。
    """

    def __init__(self):
        """初始化 Observation Collector"""
        self._pending_observations: Dict[str, List[TaskResult | Dict[str, Any]]] = {}

    async def collect(
        self,
        react_id: str,
        task_ids: List[str],
        timeout: int = 300,
        mode: FanInMode = FanInMode.ALL,
        threshold: float = 0.7,
        message_bus=None,
    ) -> ObservationSummary:
        """
        收集觀察結果（等待所有任務完成或超時）

        Args:
            react_id: ReAct session ID
            task_ids: 任務 ID 列表
            timeout: 超時時間（秒）
            mode: Fan-in 模式
            threshold: 閾值（僅 quorum 模式使用）
            message_bus: Message Bus 實例（可選）

        Returns:
            ObservationSummary 對象
        """
        # 初始化待收集列表
        self._pending_observations[react_id] = []

        logger.info(f"Collecting observations for react_id={react_id}, task_ids={task_ids}")

        # 如果提供了 Message Bus，從 Message Bus 等待結果
        if message_bus:
            try:
                from agents.services.message_bus.models import MessageType

                # 訂閱 TASK_RESULT 消息
                async def on_task_result(message):
                    if message.task_id in task_ids:
                        self.add_observation(react_id, message)

                message_bus.subscribe(MessageType.TASK_RESULT, on_task_result)

                # 等待結果
                results = await message_bus.wait_for_results(react_id, task_ids, timeout)

                # 轉換為觀察列表
                observations = []
                for result in results:
                    observations.append(
                        {
                            "task_id": result.task_id,
                            "status": result.status,
                            "result": result.result,
                            "error": result.result.get("error") if result.result else None,
                            "confidence": result.confidence,
                            "issues": result.issues,
                        }
                    )

                # 取消訂閱
                message_bus.unsubscribe(MessageType.TASK_RESULT, on_task_result)

                return self.fan_in(observations, mode, threshold)
            except Exception as e:
                logger.error(f"Failed to collect from Message Bus: {e}", exc_info=True)

        # Fallback：從待收集列表獲取
        await asyncio.sleep(0.1)  # 佔位符
        observations = self._pending_observations.get(react_id, [])

        # 如果觀察數量不足，返回部分摘要
        if len(observations) < len(task_ids):
            logger.warning(f"Not all observations received: {len(observations)}/{len(task_ids)}")

        return self.fan_in(observations, mode, threshold)

    def fan_in(
        self,
        observations: List[TaskResult | Dict[str, Any]],
        mode: FanInMode = FanInMode.ALL,
        threshold: float = 0.7,
    ) -> ObservationSummary:
        """
        執行 fan-in 匯整

        Args:
            observations: 觀察結果列表
            mode: Fan-in 模式
            threshold: 閾值（僅 quorum 模式使用）

        Returns:
            ObservationSummary 對象
        """
        return FanIn.fan_in(observations, mode, threshold)

    def add_observation(self, react_id: str, observation: TaskResult | Dict[str, Any]) -> None:
        """
        添加觀察結果（用於 Message Bus 訂閱）

        Args:
            react_id: ReAct session ID
            observation: 觀察結果
        """
        if react_id not in self._pending_observations:
            self._pending_observations[react_id] = []

        self._pending_observations[react_id].append(observation)
        logger.debug(f"Added observation for react_id={react_id}")

    def clear_observations(self, react_id: str) -> None:
        """
        清除觀察結果

        Args:
            react_id: ReAct session ID
        """
        if react_id in self._pending_observations:
            del self._pending_observations[react_id]
            logger.debug(f"Cleared observations for react_id={react_id}")

    def generate_summary(
        self,
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
        return ObservationSummaryGenerator.generate_summary(observations, mode, threshold)
