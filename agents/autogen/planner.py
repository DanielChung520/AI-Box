# 代碼功能說明: AutoGen Execution Planning 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""實現多步驟計畫生成、計畫驗證、重規劃機制。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from agent_process.context.recorder import ContextRecorder

logger = logging.getLogger(__name__)


class PlanStatus(str, Enum):
    """計劃狀態。"""

    DRAFT = "draft"
    VALIDATED = "validated"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVISED = "revised"


@dataclass
class PlanStep:
    """計劃步驟。"""

    step_id: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    estimated_tokens: int = 0
    estimated_duration: int = 0  # 秒
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """執行計劃。"""

    plan_id: str
    task: str
    steps: List[PlanStep]
    status: PlanStatus = PlanStatus.DRAFT
    total_estimated_tokens: int = 0
    total_estimated_duration: int = 0
    feasibility_score: float = 0.0
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典。"""
        return {
            "plan_id": self.plan_id,
            "task": self.task,
            "steps": [
                {
                    "step_id": step.step_id,
                    "description": step.description,
                    "dependencies": step.dependencies,
                    "estimated_tokens": step.estimated_tokens,
                    "estimated_duration": step.estimated_duration,
                    "status": step.status,
                    "retry_count": step.retry_count,
                }
                for step in self.steps
            ],
            "status": self.status.value,
            "total_estimated_tokens": self.total_estimated_tokens,
            "total_estimated_duration": self.total_estimated_duration,
            "feasibility_score": self.feasibility_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


class ExecutionPlanner:
    """執行計劃生成器。"""

    def __init__(
        self,
        context_recorder: Optional[ContextRecorder] = None,
    ):
        """
        初始化計劃生成器。

        Args:
            context_recorder: Context Recorder 實例（可選）
        """
        self.context_recorder = context_recorder or ContextRecorder()

    async def generate_plan(
        self,
        task: str,
        llm_adapter: Any,
        max_steps: int = 20,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """
        生成執行計劃。

        Args:
            task: 任務描述
            llm_adapter: LLM 適配器實例
            max_steps: 最大步驟數
            context: 上下文信息

        Returns:
            執行計劃
        """
        import uuid
        from datetime import datetime

        plan_id = str(uuid.uuid4())
        logger.info(f"Generating plan for task: {task[:100]}...")

        # 構建計劃生成提示
        prompt = self._build_planning_prompt(task, max_steps, context)

        # 調用 LLM 生成計劃
        messages = [{"role": "user", "content": prompt}]
        response = await llm_adapter.generate(messages)

        # 解析計劃
        plan = self._parse_plan_response(
            plan_id=plan_id,
            task=task,
            response=response,
        )

        # 驗證計劃
        plan.feasibility_score = self._validate_plan(plan)
        plan.status = (
            PlanStatus.VALIDATED if plan.feasibility_score >= 0.7 else PlanStatus.DRAFT
        )
        plan.created_at = datetime.now().isoformat()
        plan.updated_at = plan.created_at

        # 記錄計劃到 Context Recorder
        self._record_plan(plan)

        logger.info(
            f"Plan generated: plan_id={plan_id}, "
            f"steps={len(plan.steps)}, "
            f"feasibility={plan.feasibility_score:.2f}"
        )

        return plan

    def _build_planning_prompt(
        self,
        task: str,
        max_steps: int,
        context: Optional[Dict[str, Any]],
    ) -> str:
        """構建計劃生成提示。"""
        prompt = f"""請為以下任務生成詳細的執行計劃：

任務：{task}

要求：
1. 將任務分解為不超過 {max_steps} 個清晰的步驟
2. 每個步驟應該：
   - 有明確的描述
   - 標註依賴關係（如果有）
   - 估算所需的 token 數量和執行時間
3. 步驟之間應該有邏輯順序
4. 考慮可能的失敗情況和重試策略

請以 JSON 格式返回計劃，格式如下：
{{
  "steps": [
    {{
      "step_id": "step_1",
      "description": "步驟描述",
      "dependencies": [],
      "estimated_tokens": 1000,
      "estimated_duration": 60
    }}
  ]
}}
"""

        if context:
            prompt += f"\n上下文信息：\n{json.dumps(context, ensure_ascii=False, indent=2)}"

        return prompt

    def _parse_plan_response(
        self,
        plan_id: str,
        task: str,
        response: str,
    ) -> ExecutionPlan:
        """解析 LLM 響應為執行計劃。"""
        try:
            # 嘗試提取 JSON
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
            else:
                # 如果沒有找到 JSON，創建默認計劃
                logger.warning(
                    "Failed to parse JSON from response, creating default plan"
                )
                data = {"steps": []}

            # 構建計劃步驟
            steps = []
            for idx, step_data in enumerate(data.get("steps", []), 1):
                step = PlanStep(
                    step_id=step_data.get("step_id", f"step_{idx}"),
                    description=step_data.get("description", ""),
                    dependencies=step_data.get("dependencies", []),
                    estimated_tokens=step_data.get("estimated_tokens", 0),
                    estimated_duration=step_data.get("estimated_duration", 0),
                )
                steps.append(step)

            # 計算總計
            total_tokens = sum(step.estimated_tokens for step in steps)
            total_duration = sum(step.estimated_duration for step in steps)

            plan = ExecutionPlan(
                plan_id=plan_id,
                task=task,
                steps=steps,
                total_estimated_tokens=total_tokens,
                total_estimated_duration=total_duration,
            )

            return plan
        except Exception as exc:
            logger.error(f"Failed to parse plan response: {exc}")
            # 返回空計劃
            return ExecutionPlan(
                plan_id=plan_id,
                task=task,
                steps=[],
            )

    def _validate_plan(self, plan: ExecutionPlan) -> float:
        """
        驗證計劃可行性。

        Args:
            plan: 執行計劃

        Returns:
            可行性分數 (0.0-1.0)
        """
        if not plan.steps:
            return 0.0

        score = 1.0

        # 檢查步驟完整性
        if len(plan.steps) == 0:
            score -= 0.5

        # 檢查依賴關係
        step_ids = {step.step_id for step in plan.steps}
        for step in plan.steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    score -= 0.1
                    logger.warning(f"Step {step.step_id} has invalid dependency: {dep}")

        # 檢查資源估算
        if plan.total_estimated_tokens == 0:
            score -= 0.2

        return max(0.0, min(1.0, score))

    def revise_plan(
        self,
        plan: ExecutionPlan,
        feedback: Dict[str, Any],
        llm_adapter: Any,
    ) -> ExecutionPlan:
        """
        基於執行反饋修訂計劃。

        Args:
            plan: 原始計劃
            feedback: 執行反饋
            llm_adapter: LLM 適配器實例

        Returns:
            修訂後的計劃
        """
        from datetime import datetime

        logger.info(f"Revising plan {plan.plan_id} based on feedback")

        # 識別失敗的步驟
        failed_steps = [step for step in plan.steps if step.status == "failed"]

        if not failed_steps:
            logger.info("No failed steps to revise")
            return plan

        # 構建重規劃提示
        failed_steps_data = [
            {
                "step_id": step.step_id,
                "description": step.description,
                "error": step.error,
                "retry_count": step.retry_count,
            }
            for step in failed_steps
        ]

        prompt = f"""原始計劃執行過程中遇到以下問題：

{json.dumps(feedback, ensure_ascii=False, indent=2)}

失敗的步驟：
{json.dumps(failed_steps_data, ensure_ascii=False, indent=2)}

請提供修訂建議，包括：
1. 需要重試的步驟
2. 需要調整的步驟順序
3. 需要新增的步驟
4. 需要移除的步驟

請以 JSON 格式返回修訂建議。
"""

        # 調用 LLM 獲取修訂建議（這裡簡化處理，實際應該異步調用）
        # 為了演示，我們直接修改失敗的步驟
        for step in failed_steps:
            if step.retry_count < 3:  # 最多重試 3 次
                step.status = "pending"
                step.retry_count += 1
                step.error = None
            else:
                step.status = "skipped"
                logger.warning(f"Step {step.step_id} exceeded max retries")

        plan.status = PlanStatus.REVISED
        plan.updated_at = datetime.now().isoformat()

        # 記錄修訂後的計劃
        self._record_plan(plan)

        return plan

    def _record_plan(self, plan: ExecutionPlan) -> None:
        """記錄計劃到 Context Recorder。"""
        try:
            plan_dict = plan.to_dict()
            self.context_recorder.record(
                session_id=plan.plan_id,
                role="system",
                content=f"Execution Plan: {json.dumps(plan_dict, ensure_ascii=False)}",
                metadata={
                    "type": "execution_plan",
                    "plan_id": plan.plan_id,
                    "status": plan.status.value,
                },
            )
        except Exception as exc:
            logger.error(f"Failed to record plan: {exc}")
