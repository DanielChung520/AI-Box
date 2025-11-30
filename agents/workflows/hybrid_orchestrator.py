# 代碼功能說明: AutoGen + LangGraph 混合模式編排器
# 創建日期: 2025-11-26 22:00 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 22:00 (UTC+8)

"""實現 AutoGen 與 LangGraph 混合模式的核心編排邏輯。"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict

from agents.autogen.planner import ExecutionPlan, PlanStatus
from agents.workflows.base import (
    WorkflowExecutionResult,
    WorkflowRequestContext,
    WorkflowTelemetryEvent,
)
from genai.workflows.langchain.state import LangGraphState

logger = logging.getLogger(__name__)


class SwitchRecord(TypedDict, total=False):
    """切換記錄。"""

    timestamp: str
    from_mode: str
    to_mode: str
    reason: str
    state_hash: str
    success: bool
    error: Optional[str]


class HybridState(TypedDict, total=False):
    """混合模式統一狀態格式。"""

    task_id: str
    task: str
    context: Dict[str, Any]
    current_mode: Literal["autogen", "langgraph", "crewai"]
    autogen_plan: Dict[str, Any]  # ExecutionPlan 序列化格式
    langgraph_state: LangGraphState  # LangGraph 狀態
    switch_history: List[SwitchRecord]
    sync_checkpoint: Dict[str, Any]
    created_at: str
    updated_at: str


def serialize_hybrid_state(state: HybridState) -> str:
    """
    序列化 HybridState 為 JSON 字串。

    Args:
        state: 混合狀態

    Returns:
        JSON 字串
    """
    # 深拷貝以避免修改原始狀態
    serialized = dict(state)

    # 確保所有字段都是可序列化的
    if "autogen_plan" in serialized and isinstance(serialized["autogen_plan"], dict):
        # 已經是字典格式，直接使用
        pass
    elif "autogen_plan" in serialized:
        # 如果是 ExecutionPlan 對象，轉換為字典
        plan_obj = serialized["autogen_plan"]
        if hasattr(plan_obj, "to_dict"):
            serialized["autogen_plan"] = plan_obj.to_dict()
        elif hasattr(plan_obj, "__dict__"):
            # 檢查是否為 dataclass 實例
            from dataclasses import is_dataclass

            if is_dataclass(plan_obj) and not isinstance(plan_obj, type):
                # 確保是實例而不是類
                serialized["autogen_plan"] = asdict(plan_obj)  # type: ignore[arg-type]
            else:
                serialized["autogen_plan"] = (
                    plan_obj.__dict__ if hasattr(plan_obj, "__dict__") else {}
                )

    # LangGraphState 已經是 TypedDict，可以直接序列化
    if "langgraph_state" in serialized:
        # 確保 telemetry 是可序列化的
        langgraph_state = serialized["langgraph_state"]
        if isinstance(langgraph_state, dict) and "telemetry" in langgraph_state:
            telemetry = langgraph_state["telemetry"]
            if isinstance(telemetry, list):
                from dataclasses import is_dataclass

                langgraph_state["telemetry"] = [
                    (
                        asdict(event)
                        if is_dataclass(event) and hasattr(event, "__dict__")
                        else event
                    )
                    for event in telemetry
                ]

    return json.dumps(serialized, ensure_ascii=False, default=str)


def deserialize_hybrid_state(json_str: str) -> HybridState:
    """
    反序列化 JSON 字串為 HybridState。

    Args:
        json_str: JSON 字串

    Returns:
        混合狀態
    """
    data = json.loads(json_str)
    return HybridState(**data)


def compute_state_hash(state: HybridState) -> str:
    """
    計算狀態的哈希值，用於驗證一致性。

    Args:
        state: 混合狀態

    Returns:
        狀態哈希值
    """
    # 創建狀態的簡化版本用於哈希計算
    hash_data = {
        "task_id": state.get("task_id"),
        "current_mode": state.get("current_mode"),
        "autogen_plan_id": state.get("autogen_plan", {}).get("plan_id"),
        "langgraph_status": state.get("langgraph_state", {}).get("status"),
        "switch_count": len(state.get("switch_history", [])),
    }
    hash_str = json.dumps(hash_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(hash_str.encode("utf-8")).hexdigest()[:16]


class PlanningSync:
    """AutoGen 計畫與 LangGraph 狀態同步器。"""

    def autogen_to_langgraph(self, plan: ExecutionPlan) -> LangGraphState:
        """
        將 AutoGen 計畫節點映射為 LangGraph 狀態。

        Args:
            plan: AutoGen 執行計畫

        Returns:
            LangGraph 狀態
        """
        # 將 PlanStep 轉換為 plan: List[str]
        plan_steps: List[str] = []
        for step in plan.steps:
            plan_steps.append(step.description)

        # 提取依賴關係並設置 current_step
        # 找到第一個未完成的步驟
        current_step = 0
        for idx, step in enumerate(plan.steps):
            if step.status in ["pending", "executing"]:
                current_step = idx
                break
            elif step.status == "completed":
                current_step = idx + 1

        # 提取執行結果作為 outputs
        outputs: List[str] = []
        for step in plan.steps:
            if step.status == "completed" and step.result:
                if isinstance(step.result, str):
                    outputs.append(step.result)
                elif isinstance(step.result, dict):
                    outputs.append(json.dumps(step.result, ensure_ascii=False))
                else:
                    outputs.append(str(step.result))

        # 保留元數據到 context
        context: Dict[str, Any] = {
            "plan_id": plan.plan_id,
            "feasibility_score": plan.feasibility_score,
            "total_estimated_tokens": plan.total_estimated_tokens,
            "total_estimated_duration": plan.total_estimated_duration,
            "plan_metadata": plan.metadata,
        }

        # 根據計畫狀態映射到 LangGraph 狀態
        status_mapping = {
            PlanStatus.DRAFT: "planning",
            PlanStatus.VALIDATED: "planning",
            PlanStatus.EXECUTING: "executing",
            PlanStatus.COMPLETED: "completed",
            PlanStatus.FAILED: "failed",
            PlanStatus.REVISED: "planning",
        }
        langgraph_status_raw = status_mapping.get(plan.status, "planning")
        # 確保 status 是 Literal 類型
        valid_statuses = (
            "initialized",
            "planning",
            "executing",
            "review",
            "completed",
            "failed",
        )
        if langgraph_status_raw in valid_statuses:
            langgraph_status: Literal[
                "initialized", "planning", "executing", "review", "completed", "failed"
            ] = langgraph_status_raw  # type: ignore[assignment]
        else:
            langgraph_status = "planning"

        return LangGraphState(
            task=plan.task,
            context=context,
            plan=plan_steps,
            current_step=current_step,
            outputs=outputs,
            route="standard",
            status=langgraph_status,
            error=None,
            telemetry=[],
        )

    def validate_sync(
        self, autogen_plan: ExecutionPlan, langgraph_state: LangGraphState
    ) -> bool:
        """
        驗證同步一致性。

        Args:
            autogen_plan: AutoGen 計畫
            langgraph_state: LangGraph 狀態

        Returns:
            是否一致
        """
        # 檢查任務描述是否一致
        if autogen_plan.task != langgraph_state.get("task"):
            logger.warning("Task mismatch between plan and state")
            return False

        # 檢查步驟數量是否一致
        plan_steps = langgraph_state.get("plan", [])
        if len(plan_steps) != len(autogen_plan.steps):
            logger.warning(
                f"Step count mismatch: plan={len(autogen_plan.steps)}, "
                f"state={len(plan_steps)}"
            )
            return False

        # 檢查步驟描述是否一致
        for idx, (step, plan_step) in enumerate(zip(autogen_plan.steps, plan_steps)):
            if step.description != plan_step:
                logger.warning(
                    f"Step {idx} description mismatch: "
                    f"plan={step.description}, state={plan_step}"
                )
                return False

        return True


class StateSync:
    """LangGraph 狀態與 AutoGen 計畫同步器。"""

    def langgraph_to_autogen(self, state: LangGraphState) -> Dict[str, Any]:
        """
        將 LangGraph 狀態輸出為 AutoGen 計畫上下文。

        Args:
            state: LangGraph 狀態

        Returns:
            AutoGen 計畫上下文字典
        """
        context = state.get("context", {})
        plan_steps = state.get("plan", [])
        outputs = state.get("outputs", [])
        current_step = state.get("current_step", 0)

        # 提取 outputs 作為執行結果
        execution_results = []
        for idx, output in enumerate(outputs):
            execution_results.append(
                {
                    "step_index": idx,
                    "output": output,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # 將 plan 轉換為 PlanStep 格式的上下文
        plan_context = []
        for idx, step_desc in enumerate(plan_steps):
            plan_context.append(
                {
                    "step_index": idx,
                    "description": step_desc,
                    "status": "completed" if idx < current_step else "pending",
                    "result": outputs[idx] if idx < len(outputs) else None,
                }
            )

        return {
            "execution_results": execution_results,
            "plan_context": plan_context,
            "current_step": current_step,
            "status": state.get("status", "unknown"),
            "context": context,
        }

    def update_plan_from_state(
        self, plan: ExecutionPlan, state: LangGraphState
    ) -> ExecutionPlan:
        """
        更新計畫從 LangGraph 狀態。

        Args:
            plan: AutoGen 執行計畫
            state: LangGraph 狀態

        Returns:
            更新後的計畫
        """
        outputs = state.get("outputs", [])
        current_step = state.get("current_step", 0)
        status = state.get("status", "unknown")

        # 更新計畫步驟狀態
        for idx, step in enumerate(plan.steps):
            if idx < current_step:
                step.status = "completed"
                if idx < len(outputs):
                    step.result = outputs[idx]
            elif idx == current_step:
                step.status = "executing"
            else:
                step.status = "pending"

        # 更新計畫狀態
        status_mapping = {
            "planning": PlanStatus.VALIDATED,
            "executing": PlanStatus.EXECUTING,
            "completed": PlanStatus.COMPLETED,
            "failed": PlanStatus.FAILED,
            "review": PlanStatus.EXECUTING,
        }
        plan.status = status_mapping.get(status, PlanStatus.EXECUTING)

        # 更新時間戳
        plan.updated_at = datetime.now().isoformat()

        return plan


class SwitchController:
    """模式切換控制器。"""

    def __init__(self, cooldown_seconds: int = 60, max_switches: int = 5):
        """
        初始化切換控制器。

        Args:
            cooldown_seconds: 切換冷卻時間（秒）
            max_switches: 最大切換次數
        """
        self.cooldown_seconds = cooldown_seconds
        self.max_switches = max_switches
        self._last_switch_time: Dict[str, float] = {}
        self._switch_count: Dict[str, int] = {}
        self._locked_modes: Dict[str, bool] = {}

    def should_switch(
        self,
        current_mode: str,
        state: HybridState,
        metrics: Dict[str, Any],
    ) -> Optional[str]:
        """
        判斷是否切換模式。

        Args:
            current_mode: 當前模式
            state: 混合狀態
            metrics: 執行指標（錯誤率、延遲、成本等）

        Returns:
            目標模式，如果不應切換則返回 None
        """
        task_id = state.get("task_id", "unknown")

        # 檢查模式是否被鎖定
        if self._locked_modes.get(task_id, False):
            logger.debug(f"Mode locked for task {task_id}")
            return None

        # 檢查切換次數限制
        switch_count = self._switch_count.get(task_id, 0)
        if switch_count >= self.max_switches:
            logger.warning(f"Max switches reached for task {task_id}: {switch_count}")
            self._lock_mode(task_id)
            return None

        # 檢查冷卻時間
        last_switch = self._last_switch_time.get(task_id, 0)
        current_time = datetime.now().timestamp()
        if current_time - last_switch < self.cooldown_seconds:
            logger.debug(
                f"Switch cooldown active for task {task_id}: "
                f"{self.cooldown_seconds - (current_time - last_switch):.1f}s remaining"
            )
            return None

        # 檢查切換條件
        error_rate = metrics.get("error_rate", 0.0)
        cost = metrics.get("cost", 0.0)
        cost_threshold = metrics.get("cost_threshold", float("inf"))

        # 錯誤率 > 30% 時切換
        if error_rate > 0.3:
            target_mode = self._get_fallback_mode(current_mode, state)
            if target_mode:
                logger.info(
                    f"High error rate ({error_rate:.2%}) detected, "
                    f"switching from {current_mode} to {target_mode}"
                )
                return target_mode

        # 成本超標時切換
        if cost > cost_threshold:
            target_mode = self._get_fallback_mode(current_mode, state)
            if target_mode:
                logger.info(
                    f"Cost threshold exceeded ({cost} > {cost_threshold}), "
                    f"switching from {current_mode} to {target_mode}"
                )
                return target_mode

        # 手動觸發（通過 context）
        context = state.get("context", {})
        if context.get("force_switch_to"):
            target_mode = context.get("force_switch_to")
            logger.info(f"Manual switch requested from {current_mode} to {target_mode}")
            return target_mode

        return None

    def _get_fallback_mode(
        self, current_mode: str, state: HybridState
    ) -> Optional[str]:
        """獲取備用模式。"""
        context = state.get("context", {})
        fallback_modes = context.get("fallback_modes", [])

        # 優先使用配置的備用模式
        if fallback_modes:
            for mode in fallback_modes:
                if mode != current_mode:
                    return mode

        # 默認備用邏輯
        if current_mode == "autogen":
            return "langgraph"
        elif current_mode == "langgraph":
            return "autogen"

        return None

    def pause_workflow(self, workflow: Any, mode: str) -> Dict[str, Any]:
        """
        暫停工作流並保存狀態。

        Args:
            workflow: 工作流實例
            mode: 工作流模式

        Returns:
            保存的狀態
        """
        try:
            # 嘗試獲取當前狀態
            if hasattr(workflow, "get_state"):
                state = workflow.get_state()
            elif hasattr(workflow, "_state"):
                state = workflow._state
            else:
                state = {}

            return {
                "mode": mode,
                "state": state,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as exc:
            logger.error(f"Failed to pause workflow ({mode}): {exc}")
            return {
                "mode": mode,
                "state": {},
                "error": str(exc),
                "timestamp": datetime.now().isoformat(),
            }

    def resume_workflow(
        self, workflow: Any, mode: str, saved_state: Dict[str, Any]
    ) -> None:
        """
        恢復工作流。

        Args:
            workflow: 工作流實例
            mode: 工作流模式
            saved_state: 保存的狀態
        """
        try:
            if hasattr(workflow, "set_state"):
                workflow.set_state(saved_state.get("state", {}))
            elif hasattr(workflow, "_state"):
                workflow._state = saved_state.get("state", {})
            else:
                logger.warning(f"Workflow ({mode}) does not support state restoration")
        except Exception as exc:
            logger.error(f"Failed to resume workflow ({mode}): {exc}")

    def dump_state(self, workflow: Any, mode: str) -> Dict[str, Any]:
        """
        導出狀態快照。

        Args:
            workflow: 工作流實例
            mode: 工作流模式

        Returns:
            狀態快照
        """
        try:
            if hasattr(workflow, "get_state"):
                state = workflow.get_state()
            elif hasattr(workflow, "_state"):
                state = workflow._state
            else:
                state = {}

            return {
                "mode": mode,
                "state": state,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as exc:
            logger.error(f"Failed to dump state ({mode}): {exc}")
            return {
                "mode": mode,
                "state": {},
                "error": str(exc),
                "timestamp": datetime.now().isoformat(),
            }

    def _lock_mode(self, task_id: str) -> None:
        """鎖定模式（避免頻繁切換）。"""
        self._locked_modes[task_id] = True
        logger.info(f"Mode locked for task {task_id}")

    def unlock_mode(self, task_id: str) -> None:
        """解鎖模式。"""
        self._locked_modes.pop(task_id, None)
        logger.info(f"Mode unlocked for task {task_id}")

    def record_switch(
        self, task_id: str, from_mode: str, to_mode: str, success: bool
    ) -> None:
        """記錄切換事件。"""
        self._last_switch_time[task_id] = datetime.now().timestamp()
        if success:
            self._switch_count[task_id] = self._switch_count.get(task_id, 0) + 1


class HybridOrchestrator:
    """混合模式編排器主類，整合所有組件。"""

    def __init__(
        self,
        request_ctx: WorkflowRequestContext,
        primary_mode: Literal["autogen", "langgraph", "crewai"] = "autogen",
        fallback_modes: Optional[
            List[Literal["autogen", "langgraph", "crewai"]]
        ] = None,
    ):
        """
        初始化混合編排器。

        Args:
            request_ctx: 請求上下文
            primary_mode: 主要模式
            fallback_modes: 備用模式列表
        """
        self._ctx = request_ctx
        self._primary_mode = primary_mode
        self._fallback_modes = fallback_modes or ["langgraph"]
        self._planning_sync = PlanningSync()
        self._state_sync = StateSync()
        self._switch_controller = SwitchController()

        # 初始化混合狀態
        self._hybrid_state: HybridState = {
            "task_id": request_ctx.task_id,
            "task": request_ctx.task,
            "context": (request_ctx.context or {}).copy(),
            "current_mode": primary_mode,
            "autogen_plan": {},
            "langgraph_state": {},
            "switch_history": [],
            "sync_checkpoint": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        # 設置備用模式到 context
        self._hybrid_state["context"]["fallback_modes"] = self._fallback_modes

        # 工作流實例（延遲初始化）
        self._current_workflow: Optional[Any] = None
        self._workflow_factories: Dict[str, Any] = {}

        # Telemetry 事件
        self._telemetry_events: List[WorkflowTelemetryEvent] = []

    async def run(self) -> WorkflowExecutionResult:
        """
        執行混合模式工作流。

        Returns:
            工作流執行結果
        """
        try:
            self._emit_telemetry(
                "hybrid.workflow.start",
                task_id=self._ctx.task_id,
                primary_mode=self._primary_mode,
            )

            # 初始化主要工作流
            await self._initialize_primary_workflow()

            # 執行主循環
            result = await self._execute_with_monitoring()

            # 記錄最終狀態
            self._hybrid_state["updated_at"] = datetime.now().isoformat()
            self._emit_telemetry(
                "hybrid.workflow.completed",
                task_id=self._ctx.task_id,
                status=result.status,
            )

            return result

        except Exception as exc:
            logger.error(f"Hybrid workflow execution failed: {exc}", exc_info=True)
            self._emit_telemetry(
                "hybrid.workflow.error",
                task_id=self._ctx.task_id,
                error=str(exc),
            )
            return WorkflowExecutionResult(
                status="failed",
                output={"error": str(exc)},
                telemetry=self._telemetry_events,
                state_snapshot=dict(self._hybrid_state),
            )

    async def _initialize_primary_workflow(self) -> None:
        """初始化主要工作流。"""
        from agents.workflows.factory_router import get_workflow_factory_router
        from agents.task_analyzer.models import WorkflowType

        router = get_workflow_factory_router()

        # 根據模式獲取對應的工廠
        mode_to_workflow = {
            "autogen": WorkflowType.AUTOGEN,
            "langgraph": WorkflowType.LANGCHAIN,
            "crewai": WorkflowType.CREWAI,
        }

        workflow_type = mode_to_workflow.get(self._primary_mode)
        if not workflow_type:
            raise ValueError(f"Unknown primary mode: {self._primary_mode}")

        factory = router.get_factory(workflow_type)
        if not factory:
            raise ValueError(f"No factory found for {workflow_type}")

        self._current_workflow = factory.build_workflow(self._ctx)
        self._workflow_factories[self._primary_mode] = factory

        logger.info(
            f"Initialized primary workflow: {self._primary_mode} "
            f"for task {self._ctx.task_id}"
        )

    async def _execute_with_monitoring(self) -> WorkflowExecutionResult:
        """執行工作流並監控切換條件。"""
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # 執行當前工作流
            if not self._current_workflow:
                raise RuntimeError("No workflow initialized")

            result = await self._current_workflow.run()

            # 更新混合狀態
            await self._update_hybrid_state_from_result(result)

            # 檢查是否需要切換
            metrics = self._collect_metrics(result)
            target_mode = self._switch_controller.should_switch(
                self._hybrid_state["current_mode"],
                self._hybrid_state,
                metrics,
            )

            if target_mode and target_mode != self._hybrid_state["current_mode"]:
                # 執行切換
                current_mode = self._hybrid_state["current_mode"]
                if target_mode in (
                    "autogen",
                    "langgraph",
                    "crewai",
                ) and current_mode in (
                    "autogen",
                    "langgraph",
                    "crewai",
                ):
                    switch_success = await self._execute_switch(
                        current_mode, target_mode  # type: ignore[arg-type]
                    )
                else:
                    logger.warning(
                        f"Invalid mode for switch: {current_mode} -> {target_mode}"
                    )
                    switch_success = False

                if switch_success:
                    # 繼續執行新工作流
                    continue
                else:
                    # 切換失敗，返回當前結果
                    logger.warning("Switch failed, returning current result")
                    break
            else:
                # 不需要切換，執行完成
                break

        return result

    async def _update_hybrid_state_from_result(
        self, result: WorkflowExecutionResult
    ) -> None:
        """從工作流結果更新混合狀態。"""
        current_mode = self._hybrid_state["current_mode"]

        if current_mode == "autogen" and result.state_snapshot:
            # 更新 AutoGen 計畫
            plan_data = result.state_snapshot.get("plan_id")
            if plan_data:
                self._hybrid_state["autogen_plan"] = result.state_snapshot

        elif current_mode == "langgraph" and result.state_snapshot:
            # 更新 LangGraph 狀態
            if isinstance(result.state_snapshot, dict):
                # 確保是 LangGraphState 類型
                # 使用類型忽略，因為 TypedDict 的 ** 展開在 mypy 中有限制
                self._hybrid_state["langgraph_state"] = LangGraphState(
                    **result.state_snapshot  # type: ignore[typeddict-item]
                )
            else:
                self._hybrid_state["langgraph_state"] = result.state_snapshot  # type: ignore[assignment]

        self._hybrid_state["updated_at"] = datetime.now().isoformat()

    def _collect_metrics(self, result: WorkflowExecutionResult) -> Dict[str, Any]:
        """收集執行指標。"""
        metrics = {
            "error_rate": 0.0,
            "latency": 0.0,
            "cost": 0.0,
            "cost_threshold": float("inf"),
        }

        # 從 telemetry 提取指標
        for event in result.telemetry:
            if event.name == "workflow.cost":
                metrics["cost"] = event.payload.get("estimated_cost", 0.0)
            elif event.name == "workflow.error":
                metrics["error_rate"] = 1.0  # 有錯誤

        # 從 context 獲取成本閾值
        context = self._hybrid_state.get("context", {})
        metrics["cost_threshold"] = context.get("cost_threshold", float("inf"))

        return metrics

    async def _execute_switch(
        self,
        from_mode: Literal["autogen", "langgraph", "crewai"],
        to_mode: Literal["autogen", "langgraph", "crewai"],
    ) -> bool:
        """
        執行模式切換。

        Args:
            from_mode: 源模式
            to_mode: 目標模式

        Returns:
            是否成功
        """
        try:
            self._emit_telemetry(
                "hybrid.switch.initiated",
                task_id=self._ctx.task_id,
                from_mode=from_mode,
                to_mode=to_mode,
                reason="monitoring_triggered",
            )

            start_time = datetime.now()

            # 暫停當前工作流並保存狀態
            self._switch_controller.pause_workflow(self._current_workflow, from_mode)

            # 執行狀態遷移
            migrated_state = await self._migrate_state(from_mode, to_mode)

            # 初始化目標工作流
            await self._initialize_target_workflow(to_mode, migrated_state)

            # 記錄切換
            duration = (datetime.now() - start_time).total_seconds()
            state_hash = compute_state_hash(self._hybrid_state)

            switch_record: SwitchRecord = {
                "timestamp": datetime.now().isoformat(),
                "from_mode": from_mode,
                "to_mode": to_mode,
                "reason": "monitoring_triggered",
                "state_hash": state_hash,
                "success": True,
                "error": None,
            }
            self._hybrid_state["switch_history"].append(switch_record)

            self._switch_controller.record_switch(
                self._ctx.task_id, from_mode, to_mode, True
            )

            self._emit_telemetry(
                "hybrid.switch.completed",
                task_id=self._ctx.task_id,
                from_mode=from_mode,
                to_mode=to_mode,
                duration=duration,
                state_hash=state_hash,
            )

            return True

        except Exception as exc:
            logger.error(f"Switch failed: {exc}", exc_info=True)

            # 處理切換失敗
            await self._handle_switch_failure(from_mode, to_mode, str(exc))

            return False

    async def _migrate_state(
        self,
        from_mode: Literal["autogen", "langgraph", "crewai"],
        to_mode: Literal["autogen", "langgraph", "crewai"],
    ) -> HybridState:
        """
        執行狀態遷移。

        Args:
            from_mode: 源模式
            to_mode: 目標模式

        Returns:
            遷移後的混合狀態
        """
        if from_mode == "autogen" and to_mode == "langgraph":
            # AutoGen → LangGraph
            autogen_plan_dict = self._hybrid_state.get("autogen_plan", {})
            if autogen_plan_dict:
                # 重建 ExecutionPlan 對象
                plan = self._reconstruct_plan(autogen_plan_dict)
                langgraph_state = self._planning_sync.autogen_to_langgraph(plan)
                self._hybrid_state["langgraph_state"] = langgraph_state

        elif from_mode == "langgraph" and to_mode == "autogen":
            # LangGraph → AutoGen
            langgraph_state = self._hybrid_state.get("langgraph_state", {})
            if langgraph_state:
                # 轉換狀態（autogen_context 目前未使用，保留轉換邏輯以備將來使用）
                self._state_sync.langgraph_to_autogen(langgraph_state)
                # 更新 autogen_plan
                autogen_plan = self._hybrid_state.get("autogen_plan", {})
                if autogen_plan:
                    plan = self._reconstruct_plan(autogen_plan)
                    updated_plan = self._state_sync.update_plan_from_state(
                        plan, langgraph_state
                    )
                    self._hybrid_state["autogen_plan"] = updated_plan.to_dict()

        # 更新當前模式
        self._hybrid_state["current_mode"] = to_mode
        self._hybrid_state["updated_at"] = datetime.now().isoformat()

        return self._hybrid_state

    def _reconstruct_plan(self, plan_dict: Dict[str, Any]) -> ExecutionPlan:
        """從字典重建 ExecutionPlan 對象。"""
        from agents.autogen.planner import PlanStep

        steps = []
        for step_data in plan_dict.get("steps", []):
            step = PlanStep(
                step_id=step_data.get("step_id", ""),
                description=step_data.get("description", ""),
                dependencies=step_data.get("dependencies", []),
                estimated_tokens=step_data.get("estimated_tokens", 0),
                estimated_duration=step_data.get("estimated_duration", 0),
                status=step_data.get("status", "pending"),
                result=step_data.get("result"),
                error=step_data.get("error"),
                retry_count=step_data.get("retry_count", 0),
                metadata=step_data.get("metadata", {}),
            )
            steps.append(step)

        plan = ExecutionPlan(
            plan_id=plan_dict.get("plan_id", ""),
            task=plan_dict.get("task", ""),
            steps=steps,
            status=PlanStatus(plan_dict.get("status", "draft")),
            total_estimated_tokens=plan_dict.get("total_estimated_tokens", 0),
            total_estimated_duration=plan_dict.get("total_estimated_duration", 0),
            feasibility_score=plan_dict.get("feasibility_score", 0.0),
            created_at=plan_dict.get("created_at", ""),
            updated_at=plan_dict.get("updated_at", ""),
            metadata=plan_dict.get("metadata", {}),
        )

        return plan

    async def _initialize_target_workflow(
        self, target_mode: str, migrated_state: HybridState
    ) -> None:
        """初始化目標工作流。"""
        from agents.workflows.factory_router import get_workflow_factory_router
        from agents.task_analyzer.models import WorkflowType

        router = get_workflow_factory_router()

        mode_to_workflow = {
            "autogen": WorkflowType.AUTOGEN,
            "langgraph": WorkflowType.LANGCHAIN,
            "crewai": WorkflowType.CREWAI,
        }

        workflow_type = mode_to_workflow.get(target_mode)
        if not workflow_type:
            raise ValueError(f"Unknown target mode: {target_mode}")

        factory = router.get_factory(workflow_type)
        if not factory:
            raise ValueError(f"No factory found for {workflow_type}")

        # 更新請求上下文以包含遷移的狀態
        updated_ctx = WorkflowRequestContext(
            task_id=self._ctx.task_id,
            task=self._ctx.task,
            user_id=self._ctx.user_id,
            context=migrated_state.get("context", {}),
            workflow_config=self._ctx.workflow_config,
        )

        self._current_workflow = factory.build_workflow(updated_ctx)
        self._workflow_factories[target_mode] = factory

        logger.info(
            f"Initialized target workflow: {target_mode} "
            f"for task {self._ctx.task_id}"
        )

    async def _handle_switch_failure(
        self,
        from_mode: Literal["autogen", "langgraph", "crewai"],
        to_mode: Literal["autogen", "langgraph", "crewai"],
        error: str,
    ) -> None:
        """處理切換失敗。"""
        logger.error(f"Switch from {from_mode} to {to_mode} failed: {error}")

        # 記錄失敗
        switch_record: SwitchRecord = {
            "timestamp": datetime.now().isoformat(),
            "from_mode": from_mode,
            "to_mode": to_mode,
            "reason": "switch_failed",
            "state_hash": compute_state_hash(self._hybrid_state),
            "success": False,
            "error": error,
        }
        self._hybrid_state["switch_history"].append(switch_record)

        # 回退到原始模式
        self._hybrid_state["current_mode"] = from_mode

        # 鎖定模式避免頻繁切換
        self._switch_controller._lock_mode(self._ctx.task_id)

        self._emit_telemetry(
            "hybrid.switch.failed",
            task_id=self._ctx.task_id,
            from_mode=from_mode,
            to_mode=to_mode,
            error=error,
            fallback_mode=from_mode,
        )

    def _emit_telemetry(self, name: str, **payload: Any) -> None:
        """發送 Telemetry 事件。"""
        event = WorkflowTelemetryEvent(name=name, payload=payload)
        self._telemetry_events.append(event)
        logger.debug(f"Telemetry event: {name} with payload: {payload}")
