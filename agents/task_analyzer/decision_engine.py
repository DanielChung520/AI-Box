# 代碼功能說明: 工作流決策引擎
# 創建日期: 2025-11-26 22:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 22:30 (UTC+8)

"""實現工作流模式選擇決策邏輯。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Literal, Optional

from agents.task_analyzer.models import (
    CapabilityMatch,
    DecisionResult,
    RouterDecision,
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

    def decide(
        self,
        router_decision: RouterDecision,
        agent_candidates: list[CapabilityMatch],
        tool_candidates: list[CapabilityMatch],
        model_candidates: list[CapabilityMatch],
        context: Optional[Dict[str, Any]] = None,
    ) -> DecisionResult:
        """
        綜合決策：選擇 Agent、Tool、Model

        Args:
            router_decision: Router 決策
            agent_candidates: Agent 候選列表
            tool_candidates: Tool 候選列表
            model_candidates: Model 候選列表
            context: 上下文信息

        Returns:
            決策結果
        """
        context = context or {}
        reasoning_parts = []

        # 1. Rule Filter（硬性規則過濾）
        # 風險等級過濾
        max_risk_level = router_decision.risk_level
        agent_candidates = [
            a for a in agent_candidates if self._check_risk_level(a, max_risk_level)
        ]
        tool_candidates = [t for t in tool_candidates if self._check_risk_level(t, max_risk_level)]
        model_candidates = [
            m for m in model_candidates if self._check_risk_level(m, max_risk_level)
        ]

        # 成本限制
        max_cost = context.get("max_cost", "medium")
        agent_candidates = [a for a in agent_candidates if self._check_cost_constraint(a, max_cost)]
        tool_candidates = [t for t in tool_candidates if self._check_cost_constraint(t, max_cost)]
        model_candidates = [m for m in model_candidates if self._check_cost_constraint(m, max_cost)]

        # 2. 選擇 Agent
        chosen_agent = None
        if router_decision.needs_agent and agent_candidates:
            # 選擇評分最高的 Agent
            best_agent = max(agent_candidates, key=lambda x: x.total_score)
            if best_agent.total_score >= 0.5:  # 最低可接受評分
                chosen_agent = best_agent.candidate_id
                reasoning_parts.append(
                    f"選擇 Agent: {chosen_agent} (評分: {best_agent.total_score:.2f})"
                )
            else:
                reasoning_parts.append(f"Agent 評分過低 ({best_agent.total_score:.2f})，不使用 Agent")

        # 3. 選擇 Tool
        chosen_tools = []
        if router_decision.needs_tools and tool_candidates:
            # 選擇評分最高的工具（可以選擇多個）
            sorted_tools = sorted(tool_candidates, key=lambda x: x.total_score, reverse=True)
            for tool in sorted_tools[:3]:  # 最多選擇 3 個工具
                if tool.total_score >= 0.5:  # 最低可接受評分
                    chosen_tools.append(tool.candidate_id)
                    reasoning_parts.append(
                        f"選擇 Tool: {tool.candidate_id} (評分: {tool.total_score:.2f})"
                    )

        # 4. 選擇 Model
        chosen_model = None
        if model_candidates:
            best_model = max(model_candidates, key=lambda x: x.total_score)
            chosen_model = best_model.candidate_id
            reasoning_parts.append(f"選擇 Model: {chosen_model} (評分: {best_model.total_score:.2f})")

        # 5. 計算總評分
        scores = []
        if chosen_agent:
            agent_match = next(
                (a for a in agent_candidates if a.candidate_id == chosen_agent), None
            )
            if agent_match:
                scores.append(agent_match.total_score)
        if chosen_tools:
            tool_scores = [
                next((t for t in tool_candidates if t.candidate_id == tool_id), None).total_score
                for tool_id in chosen_tools
                if next((t for t in tool_candidates if t.candidate_id == tool_id), None)
            ]
            if tool_scores:
                scores.append(sum(tool_scores) / len(tool_scores))
        if chosen_model:
            model_match = next(
                (m for m in model_candidates if m.candidate_id == chosen_model), None
            )
            if model_match:
                scores.append(model_match.total_score)

        overall_score = sum(scores) / len(scores) if scores else 0.5

        # 6. Fallback 檢查
        fallback_used = False
        if overall_score < 0.5:  # 最低可接受評分
            fallback_used = True
            reasoning_parts.append("評分過低，使用 Fallback 模式")
            # Fallback: 不使用 Agent，只使用基礎模型
            chosen_agent = None
            chosen_tools = []

        # 7. 構建決策結果
        reasoning = "；".join(reasoning_parts) if reasoning_parts else "使用默認決策"

        result = DecisionResult(
            router_result=router_decision,
            chosen_agent=chosen_agent,
            chosen_tools=chosen_tools,
            chosen_model=chosen_model,
            score=overall_score,
            fallback_used=fallback_used,
            reasoning=reasoning,
        )

        logger.info(
            f"Decision made: agent={chosen_agent}, tools={chosen_tools}, "
            f"model={chosen_model}, score={overall_score:.2f}"
        )

        return result

    def _check_risk_level(self, candidate: CapabilityMatch, max_risk_level: str) -> bool:
        """
        檢查候選的風險等級

        Args:
            candidate: 候選匹配結果
            max_risk_level: 最大允許風險等級

        Returns:
            是否符合風險要求
        """
        # 簡化實現：從 metadata 中獲取風險等級（如果有的話）
        candidate_risk = candidate.metadata.get("risk_level", "low")

        risk_levels = {"low": 0, "mid": 1, "high": 2}
        return risk_levels.get(candidate_risk, 0) <= risk_levels.get(max_risk_level, 2)

    def _check_cost_constraint(self, candidate: CapabilityMatch, max_cost: str) -> bool:
        """
        檢查候選的成本約束

        Args:
            candidate: 候選匹配結果
            max_cost: 最大允許成本（low/medium/high）

        Returns:
            是否符合成本要求
        """
        # 簡化實現：根據 cost_score 判斷
        if max_cost == "low":
            return candidate.cost_score >= 0.7
        elif max_cost == "medium":
            return candidate.cost_score >= 0.5
        else:  # high
            return True  # 不限制
