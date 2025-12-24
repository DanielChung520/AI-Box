# 代碼功能說明: 工作流決策引擎
# 創建日期: 2025-11-26 22:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 22:30 (UTC+8)

"""實現工作流模式選擇決策邏輯。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Literal, Optional

from agents.task_analyzer.models import (
    TaskClassificationResult,
    TaskType,
    WorkflowStrategy,
    WorkflowType,
)

logger = logging.getLogger(__name__)


class DecisionEngine:
    """工作流決策引擎。"""

    def __init__(self):
        """初始化決策引擎。"""
        # 複雜度閾值
        self.complexity_threshold_hybrid = 70
        self.step_count_threshold_hybrid = 10

        # 成本門檻（避免頻繁切換）
        self.cost_threshold_switch = 100.0  # 美元

        # 冷卻時間（秒）
        self.cooldown_seconds = 60

    def decide_strategy(
        self,
        classification: TaskClassificationResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowStrategy:
        """
        決策工作流策略。

        Args:
            classification: 任務分類結果
            context: 上下文信息

        Returns:
            工作流策略
        """
        context = context or {}
        task_type = classification.task_type
        complexity_score = context.get("complexity_score", 0)
        step_count = context.get("step_count", 0)
        failure_history = context.get("failure_history", [])
        requires_observability = context.get("requires_observability", False)
        requires_long_horizon = context.get("requires_long_horizon", False)

        # 決策邏輯
        mode: Literal["single", "hybrid"] = "single"
        primary = WorkflowType.LANGCHAIN
        fallback: list[WorkflowType] = []
        reasoning_parts = []

        # 規則 1: 複雜度 ≥70 分 → 混合模式
        if complexity_score >= self.complexity_threshold_hybrid:
            mode = "hybrid"
            primary = WorkflowType.AUTOGEN
            fallback = [WorkflowType.LANGCHAIN]
            reasoning_parts.append(
                f"複雜度分數 {complexity_score} ≥ {self.complexity_threshold_hybrid}，使用混合模式"
            )

        # 規則 2: 步驟數 >10 → 混合模式
        elif step_count > self.step_count_threshold_hybrid:
            mode = "hybrid"
            primary = WorkflowType.AUTOGEN
            fallback = [WorkflowType.LANGCHAIN]
            reasoning_parts.append(f"步驟數 {step_count} > {self.step_count_threshold_hybrid}，使用混合模式")

        # 規則 3: 需要可觀測性 → LangGraph 作為主要模式
        elif requires_observability:
            if mode == "hybrid":
                primary = WorkflowType.LANGCHAIN
                fallback = [WorkflowType.AUTOGEN]
            else:
                primary = WorkflowType.LANGCHAIN
            reasoning_parts.append("需要狀態可觀測性，優先使用 LangGraph")

        # 規則 4: 需要長程規劃 → AutoGen 作為主要模式
        elif requires_long_horizon:
            if mode == "hybrid":
                primary = WorkflowType.AUTOGEN
                fallback = [WorkflowType.LANGCHAIN]
            else:
                primary = WorkflowType.AUTOGEN
            reasoning_parts.append("需要長程規劃能力，優先使用 AutoGen")

        # 規則 5: 失敗歷史 → 觸發 fallback
        if failure_history:
            if not fallback:
                # 根據任務類型選擇 fallback
                if task_type == TaskType.PLANNING:
                    fallback = [WorkflowType.LANGCHAIN]
                else:
                    fallback = [WorkflowType.AUTOGEN]
            reasoning_parts.append(f"檢測到 {len(failure_history)} 次失敗歷史，啟用備用模式")

        # 根據任務類型調整策略
        if mode == "single":
            primary, fallback = self._adjust_for_task_type(task_type)
            reasoning_parts.append(f"根據任務類型 {task_type.value} 選擇 {primary.value} 工作流")

        # 構建切換條件
        switch_conditions = {
            "error_rate_threshold": 0.3,
            "cost_threshold": self.cost_threshold_switch,
            "cooldown_seconds": self.cooldown_seconds,
            "max_switches": 5,
        }

        # 合併推理
        reasoning = "；".join(reasoning_parts) if reasoning_parts else "使用默認策略"

        strategy = WorkflowStrategy(
            mode=mode,
            primary=primary,
            fallback=fallback,
            switch_conditions=switch_conditions,
            reasoning=reasoning,
        )

        logger.info(
            f"Decided strategy: mode={mode}, primary={primary.value}, "
            f"fallback={[f.value for f in fallback]}"
        )

        return strategy

    def _adjust_for_task_type(self, task_type: TaskType) -> tuple[WorkflowType, list[WorkflowType]]:
        """
        根據任務類型調整工作流選擇。

        Args:
            task_type: 任務類型

        Returns:
            (主要工作流, 備用工作流列表)
        """
        mapping = {
            TaskType.QUERY: (WorkflowType.LANGCHAIN, [WorkflowType.CREWAI]),
            TaskType.EXECUTION: (
                WorkflowType.LANGCHAIN,
                [WorkflowType.AUTOGEN, WorkflowType.CREWAI],
            ),
            TaskType.REVIEW: (WorkflowType.LANGCHAIN, [WorkflowType.CREWAI]),
            TaskType.PLANNING: (
                WorkflowType.AUTOGEN,
                [WorkflowType.CREWAI, WorkflowType.LANGCHAIN],
            ),
            TaskType.COMPLEX: (
                WorkflowType.AUTOGEN,
                [WorkflowType.LANGCHAIN, WorkflowType.CREWAI],
            ),
        }

        return mapping.get(task_type, (WorkflowType.LANGCHAIN, []))

    def check_cost_threshold(self, current_cost: float) -> bool:
        """
        檢查成本是否超過閾值。

        Args:
            current_cost: 當前成本

        Returns:
            是否超過閾值
        """
        return current_cost > self.cost_threshold_switch

    def is_cooldown_active(self, last_switch_time: Optional[float], current_time: float) -> bool:
        """
        檢查是否在冷卻時間內。

        Args:
            last_switch_time: 上次切換時間戳
            current_time: 當前時間戳

        Returns:
            是否在冷卻時間內
        """
        if last_switch_time is None:
            return False
        return (current_time - last_switch_time) < self.cooldown_seconds
