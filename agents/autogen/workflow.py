# 代碼功能說明: AutoGen Workflow 執行核心
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""AutoGen Workflow 執行器實現。"""

from __future__ import annotations

import logging
from typing import Any, Dict

from agents.workflows.base import (
    WorkflowExecutionResult,
    WorkflowRequestContext,
    WorkflowTelemetryEvent,
)
from agents.autogen.config import AutoGenSettings
from agents.autogen.conversation import ConversationManager
from agents.autogen.coordinator import AgentCoordinator
from agents.autogen.cost_estimator import CostEstimator
from agents.autogen.long_horizon import LongHorizonTaskManager
from agents.autogen.llm_adapter import AutoGenLLMAdapter
from agents.autogen.planner import ExecutionPlanner, PlanStatus
from agents.autogen.tool_adapter import AutoGenToolAdapter
from agents.autogen.agent_roles import get_default_agent_roles

try:
    from services.api.telemetry import publish_workflow_metrics
except Exception:
    publish_workflow_metrics = None

logger = logging.getLogger(__name__)


class AutoGenWorkflow:
    """AutoGen Workflow 執行器。"""

    def __init__(
        self,
        settings: AutoGenSettings,
        request_ctx: WorkflowRequestContext,
    ):
        """
        初始化 AutoGen Workflow。

        Args:
            settings: AutoGen 設定
            request_ctx: 請求上下文
        """
        self._settings = settings
        self._ctx = request_ctx

        # 初始化組件
        self._conversation_manager = ConversationManager(session_id=request_ctx.task_id)
        self._coordinator = AgentCoordinator()
        self._tool_adapter = AutoGenToolAdapter()
        self._cost_estimator = CostEstimator()
        self._long_horizon_manager = LongHorizonTaskManager(
            checkpoint_dir=settings.checkpoint_dir
        )
        self._planner = ExecutionPlanner(
            context_recorder=self._conversation_manager.context_recorder
        )

        # 初始化 LLM 適配器
        self._llm_adapter = AutoGenLLMAdapter(
            model_name=settings.default_llm,
            temperature=0.7,
        )

        # 初始化 Agent 角色
        self._agent_roles = get_default_agent_roles()

        # 初始化 Telemetry
        self._telemetry_events: list[WorkflowTelemetryEvent] = []

    async def run(self) -> WorkflowExecutionResult:
        """
        執行工作流。

        Returns:
            工作流執行結果
        """
        try:
            self._emit_telemetry("workflow.start", task_id=self._ctx.task_id)

            # 步驟 1: 生成執行計劃
            plan = await self._planner.generate_plan(
                task=self._ctx.task,
                llm_adapter=self._llm_adapter,
                max_steps=self._settings.max_steps,
                context=self._ctx.context,
            )

            # 步驟 2: 成本估算和預算檢查
            cost_estimate = self._cost_estimator.estimate_plan_cost(
                plan, model_name=self._settings.default_llm
            )
            within_budget, budget_msg = self._cost_estimator.check_budget(
                cost_estimate, self._settings.budget_tokens
            )

            if not within_budget:
                logger.warning(f"Budget exceeded: {budget_msg}")
                return WorkflowExecutionResult(
                    status="failed",
                    output={"error": f"預算超支: {budget_msg}"},
                    reasoning=budget_msg,
                    telemetry=self._telemetry_events,
                )

            # 步驟 3: 資源限制檢查
            (
                within_limits,
                limits_msg,
            ) = self._long_horizon_manager.check_resource_limits(
                plan,
                budget_tokens=self._settings.budget_tokens,
                max_rounds=self._settings.max_rounds,
            )

            if not within_limits:
                logger.warning(f"Resource limits exceeded: {limits_msg}")
                return WorkflowExecutionResult(
                    status="failed",
                    output={"error": f"資源限制超標: {limits_msg}"},
                    reasoning=limits_msg,
                    telemetry=self._telemetry_events,
                )

            # 步驟 4: 保存初始檢查點
            if self._settings.checkpoint_enabled:
                self._long_horizon_manager.save_checkpoint(plan)

            # 步驟 5: 執行計劃（這裡簡化處理，實際應該使用 AutoGen 的 Agent 協作）
            execution_result = await self._execute_plan(plan)

            # 步驟 6: 保存最終狀態
            if self._settings.checkpoint_enabled:
                self._long_horizon_manager.save_checkpoint(plan, {"completed": True})

            # 步驟 7: 記錄成本到 Telemetry
            self._emit_telemetry(
                "workflow.cost",
                task_id=self._ctx.task_id,
                total_tokens=cost_estimate.total_tokens,
                estimated_cost=cost_estimate.estimated_cost,
            )

            # 構建執行結果
            result = WorkflowExecutionResult(
                status="completed" if execution_result["success"] else "failed",
                output=execution_result.get("output", {}),
                reasoning=execution_result.get("reasoning"),
                telemetry=self._telemetry_events,
                state_snapshot={
                    "plan_id": plan.plan_id,
                    "status": plan.status.value,
                    "steps": [
                        {
                            "step_id": step.step_id,
                            "status": step.status,
                        }
                        for step in plan.steps
                    ],
                },
            )

            self._emit_telemetry("workflow.complete", task_id=self._ctx.task_id)
            return result

        except Exception as exc:
            logger.error(f"Workflow execution failed: {exc}", exc_info=True)
            self._emit_telemetry(
                "workflow.error",
                task_id=self._ctx.task_id,
                error=str(exc),
            )
            return WorkflowExecutionResult(
                status="failed",
                output={"error": str(exc)},
                telemetry=self._telemetry_events,
            )

    async def _execute_plan(self, plan: Any) -> Dict[str, Any]:
        """
        執行計劃（簡化實現）。

        Args:
            plan: 執行計劃

        Returns:
            執行結果
        """
        # 這裡是簡化實現，實際應該：
        # 1. 使用 AutoGen 的 AssistantAgent 和 GroupChat
        # 2. 按照計劃步驟執行
        # 3. 處理失敗和重試

        logger.info(f"Executing plan {plan.plan_id} with {len(plan.steps)} steps")

        completed_steps = 0
        failed_steps = 0

        for step in plan.steps:
            try:
                # 記錄步驟開始
                self._conversation_manager.record_message(
                    agent_name="executor",
                    role="assistant",
                    content=f"開始執行步驟: {step.description}",
                )

                # 這裡應該實際執行步驟（調用工具、LLM 等）
                # 為了演示，我們標記為完成
                step.status = "completed"
                step.result = {"status": "success"}
                completed_steps += 1

                # 記錄步驟完成
                self._conversation_manager.record_message(
                    agent_name="executor",
                    role="assistant",
                    content=f"步驟完成: {step.description}",
                )

                # 保存中間檢查點
                if self._settings.checkpoint_enabled:
                    self._long_horizon_manager.save_checkpoint(plan)

            except Exception as exc:
                logger.error(f"Step {step.step_id} failed: {exc}")
                step.status = "failed"
                step.error = str(exc)
                failed_steps += 1

                # 處理失敗
                should_retry = self._long_horizon_manager.handle_failure(
                    plan, step.step_id, str(exc), max_retries=3
                )

                if should_retry:
                    # 重試邏輯（這裡簡化處理）
                    logger.info(f"Retrying step {step.step_id}")

        # 更新計劃狀態
        if failed_steps == 0:
            plan.status = PlanStatus.COMPLETED
        elif completed_steps > 0:
            plan.status = PlanStatus.EXECUTING
        else:
            plan.status = PlanStatus.FAILED

        return {
            "success": failed_steps == 0,
            "output": {
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "total_steps": len(plan.steps),
            },
            "reasoning": f"執行完成: {completed_steps} 成功, {failed_steps} 失敗",
        }

    def _emit_telemetry(self, name: str, **payload: Any) -> None:
        """發送 Telemetry 事件。"""
        event = WorkflowTelemetryEvent(name=name, payload=payload)
        self._telemetry_events.append(event)

        # 如果可用，發送到 Prometheus
        if publish_workflow_metrics:
            try:
                publish_workflow_metrics(
                    workflow_type="autogen",
                    event_name=name,
                    **payload,
                )
            except Exception as exc:
                logger.warning(f"Failed to publish metrics: {exc}")
