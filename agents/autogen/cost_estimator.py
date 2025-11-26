# 代碼功能說明: AutoGen 成本估算器
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""實現 Token 使用量預估、成本計算和預算控制。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from agents.autogen.planner import ExecutionPlan, PlanStep

logger = logging.getLogger(__name__)


@dataclass
class CostEstimate:
    """成本估算結果。"""

    total_tokens: int
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    currency: str = "USD"
    model_name: str = ""
    breakdown: Dict[str, Any] = None

    def __post_init__(self):
        """初始化後處理。"""
        if self.breakdown is None:
            self.breakdown = {}


# 默認的模型定價（每 1K tokens，單位：USD）
# 這些是示例值，實際應該從配置或 API 獲取
DEFAULT_MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-oss:20b": {
        "input": 0.0,  # 本地模型，假設免費
        "output": 0.0,
    },
    "qwen3-coder:30b": {
        "input": 0.0,
        "output": 0.0,
    },
    "llama3.1:8b": {
        "input": 0.0,
        "output": 0.0,
    },
    "mistral-nemo:12b": {
        "input": 0.0,
        "output": 0.0,
    },
}


class CostEstimator:
    """成本估算器。"""

    def __init__(
        self,
        model_pricing: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        """
        初始化成本估算器。

        Args:
            model_pricing: 模型定價字典（可選）
        """
        self.model_pricing = model_pricing or DEFAULT_MODEL_PRICING

    def estimate_plan_cost(
        self,
        plan: ExecutionPlan,
        model_name: str = "gpt-oss:20b",
    ) -> CostEstimate:
        """
        估算計劃成本。

        Args:
            plan: 執行計劃
            model_name: 模型名稱

        Returns:
            成本估算結果
        """
        total_input_tokens = 0
        total_output_tokens = 0

        # 估算每個步驟的 token 使用量
        for step in plan.steps:
            # 假設輸入和輸出各佔一半（實際應該更精確）
            step_tokens = step.estimated_tokens
            step_input = step_tokens // 2
            step_output = step_tokens - step_input

            total_input_tokens += step_input
            total_output_tokens += step_output

        # 獲取模型定價
        pricing = self.model_pricing.get(
            model_name,
            self.model_pricing.get("gpt-oss:20b", {"input": 0.0, "output": 0.0}),
        )

        # 計算成本
        input_cost = (total_input_tokens / 1000.0) * pricing.get("input", 0.0)
        output_cost = (total_output_tokens / 1000.0) * pricing.get("output", 0.0)
        total_cost = input_cost + output_cost

        # 構建詳細分解
        breakdown = {
            "steps": [
                {
                    "step_id": step.step_id,
                    "estimated_tokens": step.estimated_tokens,
                    "estimated_cost": (step.estimated_tokens / 1000.0)
                    * (pricing.get("input", 0.0) + pricing.get("output", 0.0))
                    / 2,
                }
                for step in plan.steps
            ],
            "model": model_name,
            "pricing": pricing,
        }

        estimate = CostEstimate(
            total_tokens=total_input_tokens + total_output_tokens,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            estimated_cost=total_cost,
            model_name=model_name,
            breakdown=breakdown,
        )

        logger.info(
            f"Cost estimate for plan {plan.plan_id}: "
            f"{estimate.total_tokens} tokens, ${estimate.estimated_cost:.4f}"
        )

        return estimate

    def check_budget(
        self,
        estimate: CostEstimate,
        budget_tokens: int,
    ) -> tuple[bool, str]:
        """
        檢查預算限制。

        Args:
            estimate: 成本估算結果
            budget_tokens: Token 預算上限

        Returns:
            (是否在預算內, 消息)
        """
        if estimate.total_tokens <= budget_tokens:
            return True, f"預算充足（使用 {estimate.total_tokens}/{budget_tokens} tokens）"
        else:
            excess = estimate.total_tokens - budget_tokens
            return (
                False,
                f"超出預算 {excess} tokens（{estimate.total_tokens}/{budget_tokens}）",
            )

    def estimate_step_cost(
        self,
        step: PlanStep,
        model_name: str = "gpt-oss:20b",
    ) -> float:
        """
        估算單個步驟的成本。

        Args:
            step: 計劃步驟
            model_name: 模型名稱

        Returns:
            估算成本（USD）
        """
        pricing = self.model_pricing.get(
            model_name,
            self.model_pricing.get("gpt-oss:20b", {"input": 0.0, "output": 0.0}),
        )
        avg_price = (pricing.get("input", 0.0) + pricing.get("output", 0.0)) / 2.0
        return (step.estimated_tokens / 1000.0) * avg_price
