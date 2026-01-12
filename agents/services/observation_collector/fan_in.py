# 代碼功能說明: Observation Collector Fan-in 匯整邏輯
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Observation Collector Fan-in 匯整邏輯

實現 all/any/quorum 三種模式的 fan-in 匯整。
"""

import logging
from typing import Any, Dict, List

from agents.services.observation_collector.models import FanInMode, ObservationSummary
from agents.services.orchestrator.models import TaskResult, TaskStatus

logger = logging.getLogger(__name__)


class FanIn:
    """Fan-in 匯整類"""

    @staticmethod
    def fan_in(
        observations: List[TaskResult | Dict[str, Any]],
        mode: FanInMode = FanInMode.ALL,
        threshold: float = 0.7,
    ) -> ObservationSummary:
        """
        執行 fan-in 匯整

        Args:
            observations: 觀察結果列表（TaskResult 對象或字典）
            mode: Fan-in 模式（all/any/quorum）
            threshold: 閾值（僅 quorum 模式使用）

        Returns:
            ObservationSummary 對象
        """
        # 轉換為統一格式
        obs_list = []
        for obs in observations:
            if isinstance(obs, dict):
                obs_list.append(obs)
            elif isinstance(obs, TaskResult):
                obs_list.append(FanIn._task_result_to_dict(obs))
            else:
                logger.warning(f"Unsupported observation type: {type(obs)}")
                continue

        if not obs_list:
            # 空觀察列表
            return ObservationSummary(
                success_rate=0.0,
                blocking_issues=True,
                lowest_confidence=0.0,
                observations=[],
                total_count=0,
                success_count=0,
                failure_count=0,
                partial_count=0,
                issues=[],
            )

        # 計算統計信息
        total_count = len(obs_list)
        success_count = sum(1 for obs in obs_list if obs.get("status") == "success")
        failure_count = sum(1 for obs in obs_list if obs.get("status") == "failed")
        partial_count = sum(1 for obs in obs_list if obs.get("status") == "partial")

        # 計算成功率
        success_rate = success_count / total_count if total_count > 0 else 0.0

        # 計算最低置信度
        confidences = [obs.get("confidence", 0.0) for obs in obs_list if "confidence" in obs]
        lowest_confidence = min(confidences) if confidences else 0.0

        # 收集問題
        issues = []
        for obs in obs_list:
            if "issues" in obs and obs["issues"]:
                issues.extend(obs["issues"])

        # 判斷是否有阻塞問題
        blocking_issues = FanIn._has_blocking_issues(obs_list, mode, threshold, success_rate)

        return ObservationSummary(
            success_rate=success_rate,
            blocking_issues=blocking_issues,
            lowest_confidence=lowest_confidence,
            observations=obs_list,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
            partial_count=partial_count,
            issues=issues,
        )

    @staticmethod
    def _has_blocking_issues(
        observations: List[Dict[str, Any]],
        mode: FanInMode,
        threshold: float,
        success_rate: float,
    ) -> bool:
        """
        判斷是否有阻塞問題

        Args:
            observations: 觀察結果列表
            mode: Fan-in 模式
            threshold: 閾值
            success_rate: 成功率

        Returns:
            是否有阻塞問題
        """
        if mode == FanInMode.ALL:
            # all 模式：所有觀察都必須成功
            return success_rate < 1.0

        elif mode == FanInMode.ANY:
            # any 模式：至少一個觀察成功即可
            return success_rate == 0.0

        elif mode == FanInMode.QUORUM:
            # quorum 模式：成功率必須達到閾值
            return success_rate < threshold

        else:
            logger.warning(f"Unknown fan-in mode: {mode}")
            return True

    @staticmethod
    def _task_result_to_dict(task_result: TaskResult) -> Dict[str, Any]:
        """
        將 TaskResult 轉換為字典

        Args:
            task_result: TaskResult 對象

        Returns:
            字典
        """
        # 根據 TaskStatus 映射到 GRO 規範的 status
        status_mapping = {
            TaskStatus.COMPLETED: "success",
            TaskStatus.FAILED: "failed",
            TaskStatus.CANCELLED: "failed",
            TaskStatus.PENDING: "partial",
            TaskStatus.RUNNING: "partial",
            TaskStatus.ASSIGNED: "partial",
        }

        status = status_mapping.get(task_result.status, "failed")

        result = {
            "task_id": task_result.task_id,
            "status": status,
            "result": task_result.result,
            "error": task_result.error,
            "agent_id": task_result.agent_id,
        }

        # 添加置信度（如果 metadata 中有）
        if "confidence" in task_result.metadata:
            result["confidence"] = task_result.metadata["confidence"]

        # 添加問題（如果 metadata 中有）
        if "issues" in task_result.metadata:
            result["issues"] = task_result.metadata["issues"]

        return result
