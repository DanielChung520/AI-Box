# 代碼功能說明: Planning Agent 核心實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Planning Agent - 實現計劃生成和驗證"""

import uuid
import logging
from typing import Dict, Any, Optional, List

from agents.core.planning.models import (
    PlanRequest,
    PlanResult,
    PlanStep,
    PlanStepStatus,
)
from genai.prompt import PromptManager
from agents.infra.memory import MemoryManager

logger = logging.getLogger(__name__)


class PlanningAgent:
    """Planning Agent - 規劃代理"""

    def __init__(
        self,
        prompt_manager: Optional[PromptManager] = None,
        memory_manager: Optional[MemoryManager] = None,
    ):
        """
        初始化 Planning Agent

        Args:
            prompt_manager: 提示管理器
            memory_manager: 記憶管理器
        """
        self.prompt_manager = prompt_manager or PromptManager()
        self.memory_manager = memory_manager

    def generate_plan(self, request: PlanRequest) -> PlanResult:
        """
        生成任務計劃

        Args:
            request: 計劃請求

        Returns:
            計劃結果
        """
        logger.info(f"Generating plan for task: {request.task[:100]}...")

        plan_id = str(uuid.uuid4())

        # 步驟1: 分析任務
        task_analysis = self._analyze_task(request)

        # 步驟2: 生成計劃步驟
        steps = self._generate_steps(request, task_analysis)

        # 步驟3: 驗證計劃可行性
        feasibility_score = self._validate_plan(steps, request)

        # 步驟4: 估算執行時間
        estimated_duration = self._estimate_duration(steps)

        # 構建計劃結果
        plan_result = PlanResult(
            plan_id=plan_id,
            task=request.task,
            steps=steps,
            estimated_duration=estimated_duration,
            feasibility_score=feasibility_score,
            metadata=request.metadata,
        )

        # 存儲計劃到記憶（如果可用）
        if self.memory_manager:
            self.memory_manager.store_short_term(
                key=f"plan:{plan_id}",
                value=plan_result.model_dump(),
                ttl=3600,  # 1小時
            )

        logger.info(
            f"Plan generated: plan_id={plan_id}, "
            f"steps={len(steps)}, "
            f"feasibility={feasibility_score:.2f}"
        )

        return plan_result

    def _analyze_task(self, request: PlanRequest) -> Dict[str, Any]:
        """
        分析任務

        Args:
            request: 計劃請求

        Returns:
            任務分析結果
        """
        # 簡單的任務分析邏輯
        # 實際實現應該使用 LLM 進行更深入的分析

        analysis = {
            "complexity": "medium",
            "estimated_steps": 3,
            "key_actions": [],
        }

        # 根據任務描述提取關鍵動作
        task_lower = request.task.lower()
        key_actions: List[str] = analysis["key_actions"]  # type: ignore[assignment]
        if "查詢" in task_lower or "查詢" in task_lower:
            key_actions.append("query")
        if "執行" in task_lower or "執行" in task_lower:
            key_actions.append("execute")
        if "創建" in task_lower or "create" in task_lower:
            key_actions.append("create")
        if "更新" in task_lower or "update" in task_lower:
            key_actions.append("update")
        if "刪除" in task_lower or "delete" in task_lower:
            key_actions.append("delete")

        return analysis

    def _generate_steps(
        self,
        request: PlanRequest,
        task_analysis: Dict[str, Any],
    ) -> List[PlanStep]:
        """
        生成計劃步驟

        Args:
            request: 計劃請求
            task_analysis: 任務分析結果

        Returns:
            計劃步驟列表
        """
        steps = []

        # 根據任務分析生成步驟
        key_actions = task_analysis.get("key_actions", [])

        if not key_actions:
            # 默認步驟
            steps.append(
                PlanStep(
                    step_id=str(uuid.uuid4()),
                    step_number=1,
                    description="分析任務需求",
                    action="analyze",
                    dependencies=[],
                    result=None,
                )
            )
            steps.append(
                PlanStep(
                    step_id=str(uuid.uuid4()),
                    step_number=2,
                    description="執行任務",
                    action="execute",
                    dependencies=[steps[0].step_id],
                    result=None,
                )
            )
            steps.append(
                PlanStep(
                    step_id=str(uuid.uuid4()),
                    step_number=3,
                    description="驗證結果",
                    action="validate",
                    result=None,
                    dependencies=[steps[1].step_id],
                )
            )
        else:
            # 根據關鍵動作生成步驟
            for idx, action in enumerate(key_actions, start=1):
                step_id = str(uuid.uuid4())
                dependencies = []

                if idx > 1:
                    # 依賴前一個步驟
                    dependencies.append(steps[-1].step_id)

                steps.append(
                    PlanStep(
                        step_id=step_id,
                        step_number=idx,
                        description=f"執行 {action} 操作",
                        action=action,
                        dependencies=dependencies,
                        result=None,
                    )
                )

        return steps

    def _validate_plan(
        self,
        steps: List[PlanStep],
        request: PlanRequest,
    ) -> float:
        """
        驗證計劃可行性

        Args:
            steps: 計劃步驟列表
            request: 計劃請求

        Returns:
            可行性評分（0.0-1.0）
        """
        if not steps:
            return 0.0

        # 檢查步驟依賴關係
        step_ids = {step.step_id for step in steps}
        valid_dependencies = True

        for step in steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    valid_dependencies = False
                    break

        if not valid_dependencies:
            return 0.3

        # 檢查是否有循環依賴
        has_cycle = self._check_cyclic_dependencies(steps)
        if has_cycle:
            return 0.2

        # 基本可行性評分
        base_score = 0.8

        # 根據步驟數量調整
        if len(steps) > 10:
            base_score -= 0.1
        elif len(steps) < 3:
            base_score += 0.1

        # 根據約束條件調整
        if request.constraints:
            base_score -= len(request.constraints) * 0.05

        return max(0.0, min(1.0, base_score))

    def _check_cyclic_dependencies(self, steps: List[PlanStep]) -> bool:
        """
        檢查是否有循環依賴

        Args:
            steps: 計劃步驟列表

        Returns:
            是否有循環依賴
        """
        # 簡單的循環檢測（DFS）
        step_map = {step.step_id: step for step in steps}
        visited = set()
        rec_stack = set()

        def has_cycle(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)

            step = step_map.get(step_id)
            if step:
                for dep_id in step.dependencies:
                    if dep_id not in visited:
                        if has_cycle(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(step_id)
            return False

        for step in steps:
            if step.step_id not in visited:
                if has_cycle(step.step_id):
                    return True

        return False

    def _estimate_duration(self, steps: List[PlanStep]) -> int:
        """
        估算執行時間

        Args:
            steps: 計劃步驟列表

        Returns:
            預估執行時間（秒）
        """
        # 簡單估算：每個步驟平均30秒
        base_time_per_step = 30
        return len(steps) * base_time_per_step

    def update_step_status(
        self,
        plan_id: str,
        step_id: str,
        status: PlanStepStatus,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        更新步驟狀態

        Args:
            plan_id: 計劃ID
            step_id: 步驟ID
            status: 新狀態
            result: 步驟結果

        Returns:
            是否成功更新
        """
        # 從記憶中獲取計劃
        if self.memory_manager:
            plan_data = self.memory_manager.retrieve_short_term(f"plan:{plan_id}")
            if plan_data:
                # 更新步驟狀態
                for step in plan_data.get("steps", []):
                    if step["step_id"] == step_id:
                        step["status"] = status.value
                        if result:
                            step["result"] = result

                # 保存回記憶
                self.memory_manager.store_short_term(
                    key=f"plan:{plan_id}",
                    value=plan_data,
                    ttl=3600,
                )
                return True

        return False
