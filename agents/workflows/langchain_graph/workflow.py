# 代碼功能說明: LangChain/Graph Workflow 執行核心
# 創建日期: 2025-11-26 20:07 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 20:07 (UTC+8)

"""LangChain/Graph 工作流編排實作。"""

from __future__ import annotations

import textwrap
from typing import Any, Dict, List, Literal

from langchain_core.runnables import RunnableConfig, RunnableLambda
from langgraph.graph import END, StateGraph

from agents.workflows.base import WorkflowExecutionResult, WorkflowRequestContext
from genai.workflows.langchain.checkpoint import build_checkpointer
from genai.workflows.langchain.context_recorder import build_context_recorder
from genai.workflows.langchain.state import LangGraphState, build_initial_state
from genai.workflows.langchain.telemetry import WorkflowTelemetryCollector
from agents.workflows.settings import LangChainGraphSettings

try:  # pragma: no cover - API 層未載入時允許繼續
    from services.api.telemetry import publish_workflow_metrics
except Exception:  # pylint: disable=broad-except
    publish_workflow_metrics = None  # type: ignore[assignment]


class LangChainGraphWorkflow:
    """負責將請求映射到 LangGraph 的工作流執行器。"""

    def __init__(
        self,
        *,
        settings: LangChainGraphSettings,
        request_ctx: WorkflowRequestContext,
        telemetry: WorkflowTelemetryCollector,
    ) -> None:
        self._settings = settings
        self._ctx = request_ctx
        self._telemetry = telemetry
        self._checkpointer = build_checkpointer(settings)
        self._context_recorder = build_context_recorder(settings)
        self._graph = self._compile_graph()
        self._step_executor = RunnableLambda(self._synthesize_step_output)

    def _compile_graph(self):
        graph = StateGraph(LangGraphState)

        graph.add_node("ingest", self._node_ingest)
        graph.add_node("planner", self._node_planner)
        graph.add_node("executor", self._node_executor)
        graph.add_node("router", self._node_router)
        graph.add_node("research", self._node_research)
        graph.add_node("reviewer", self._node_reviewer)

        graph.add_edge("ingest", "planner")
        graph.add_edge("planner", "router")
        graph.add_conditional_edges(
            "router",
            self._route_next_node,
            {
                "standard": "executor",
                "deep_dive": "research",
            },
        )
        graph.add_edge("research", "executor")
        graph.add_edge("executor", "reviewer")
        graph.add_edge("reviewer", END)
        graph.set_entry_point("ingest")

        return graph.compile(checkpointer=self._checkpointer)

    async def run(self) -> WorkflowExecutionResult:
        """執行整個工作流。"""

        initial_state = build_initial_state(
            self._ctx.task,
            self._ctx.context or {},
        )

        config = RunnableConfig(
            configurable={
                "thread_id": self._ctx.task_id,
                "checkpoint_id": self._ctx.task_id,
                "task_id": self._ctx.task_id,
                "max_iterations": self._settings.max_iterations,
            }
        )

        self._telemetry.emit(
            "workflow.start",
            task_id=self._ctx.task_id,
            workflow="langchain_graph",
        )

        final_state = await self._graph.ainvoke(initial_state, config=config)

        # 將最終狀態寫入 Context Recorder 以供後續查詢/恢復
        try:
            self._context_recorder.save(self._ctx.task_id, dict(final_state))
        except Exception as exc:  # pragma: no cover
            self._telemetry.emit("context_recorder.error", error=str(exc))

        status = final_state.get("status", "completed")
        error = final_state.get("error")
        if error:
            status = "failed"
            self._telemetry.emit(
                "workflow.failed",
                task_id=self._ctx.task_id,
                error=error,
            )
        else:
            self._telemetry.emit(
                "workflow.completed",
                task_id=self._ctx.task_id,
                steps=len(final_state.get("plan") or []),
            )

        result = WorkflowExecutionResult(
            status=status,
            output={
                "plan": final_state.get("plan", []),
                "outputs": final_state.get("outputs", []),
            },
            reasoning="LangChain/Graph workflow execution finished",
            telemetry=self._telemetry.export(),
            state_snapshot=dict(final_state),
        )

        if publish_workflow_metrics is not None:
            try:
                publish_workflow_metrics(
                    workflow="langchain_graph",
                    status=status,
                    steps=len(final_state.get("plan") or []),
                    route=final_state.get("route", "standard"),
                    events=result.telemetry,
                )
            except Exception as exc:  # pragma: no cover
                self._telemetry.emit("metrics.publish_failed", error=str(exc))

        return result

    async def _node_ingest(
        self, state: LangGraphState, config: RunnableConfig
    ) -> LangGraphState:
        self._telemetry.emit(
            "ingest",
            task_id=self._ctx.task_id,
            user_id=self._ctx.user_id,
        )
        return LangGraphState(
            status="planning",
            current_step=0,
        )

    async def _node_planner(
        self, state: LangGraphState, config: RunnableConfig
    ) -> LangGraphState:
        plan = state.get("plan") or self._build_plan(
            state["task"], state.get("context") or {}
        )
        self._telemetry.emit(
            "planner",
            plan_size=len(plan),
            task_id=self._ctx.task_id,
        )
        return LangGraphState(
            plan=plan,
            status="executing",
        )

    async def _node_router(
        self, state: LangGraphState, config: RunnableConfig
    ) -> LangGraphState:
        route = self._decide_route(state)
        self._telemetry.emit(
            "router",
            route=route,
            plan_size=len(state.get("plan") or []),
        )
        return LangGraphState(route=route)

    def _route_next_node(self, state: LangGraphState) -> str:
        return state.get("route") or "standard"

    def _decide_route(self, state: LangGraphState) -> Literal["standard", "deep_dive"]:
        workflow_config = self._ctx.workflow_config or {}
        complexity_score = workflow_config.get("complexity_score", 0)
        plan_size = len(state.get("plan") or [])

        high_complexity = complexity_score >= 60 or plan_size > 3
        keywords = ["深入", "多渠道", "long", "complex", "監控"]
        keyword_hit = any(keyword in self._ctx.task for keyword in keywords)

        return "deep_dive" if high_complexity or keyword_hit else "standard"

    async def _node_research(
        self, state: LangGraphState, config: RunnableConfig
    ) -> LangGraphState:
        plan = state.get("plan") or []
        research_notes = (
            f"為 {self._ctx.task} 執行深入研究，參考 {len(plan)} 個原子步驟。"
        )
        self._telemetry.emit(
            "research",
            note=research_notes,
        )
        return LangGraphState(
            outputs=[f"[Research] {research_notes}"],
            status="executing",
        )

    async def _node_executor(
        self, state: LangGraphState, config: RunnableConfig
    ) -> LangGraphState:
        plan = state.get("plan") or []
        if not plan:
            self._telemetry.emit("executor.skip", reason="empty_plan")
            return LangGraphState(status="review")

        outputs: List[str] = []
        max_iterations = min(len(plan), self._settings.max_iterations)
        for idx in range(max_iterations):
            step = plan[idx]
            payload = {
                "task": self._ctx.task,
                "step": step,
                "step_index": idx,
                "context": self._ctx.context or {},
                "config": self._ctx.workflow_config or {},
            }
            output = await self._step_executor.ainvoke(payload, config=config)
            outputs.append(output)
            self._telemetry.emit(
                "executor.step",
                step_index=idx,
                text=step,
            )

        return LangGraphState(
            outputs=outputs,
            current_step=max_iterations,
            status="review",
        )

    async def _node_reviewer(
        self, state: LangGraphState, config: RunnableConfig
    ) -> LangGraphState:
        outputs = state.get("outputs") or []
        summary = self._build_summary(outputs)
        self._telemetry.emit(
            "review",
            outputs=len(outputs),
        )
        return LangGraphState(
            outputs=outputs + [summary],
            status="completed",
        )

    def _build_plan(self, task: str, context: Dict[str, Any]) -> List[str]:
        """非常簡化的規劃器，後續可替換為 LangChain Agent。"""

        if context and "workflow_plan" in context:
            plan = context["workflow_plan"]
            if isinstance(plan, list):
                return plan

        task_lower = task.lower()
        plan_steps: List[str] = []

        if "analy" in task_lower:
            plan_steps.append("收集相關資料並整理關鍵指標")
            plan_steps.append("執行資料/趨勢分析並萃取見解")
            plan_steps.append("撰寫分析結論與建議")
        else:
            plan_steps.append("理解任務目標與成功條件")
            plan_steps.append("蒐集或生成解決任務所需的資訊")
            plan_steps.append("整理輸出並確認滿足需求")

        return plan_steps

    def _build_summary(self, outputs: List[str]) -> str:
        if not outputs:
            return "未產生可供摘要的步驟輸出。"
        numbered = "\n".join(f"{idx + 1}. {text}" for idx, text in enumerate(outputs))
        summary = textwrap.dedent(
            f"""
            步驟輸出整理：
            {numbered}
            """
        ).strip()
        return summary

    def _synthesize_step_output(self, payload: Dict[str, Any]) -> str:
        """預設的步驟輸出生成器，可被 LangChain Runnable 取代。"""

        step = payload["step"]
        step_index = payload["step_index"]
        context = payload.get("context") or {}
        hints = context.get("hints")
        hint_text = f"（提示: {hints}）" if hints else ""
        return f"[步驟 {step_index + 1}] {step}{hint_text}"
