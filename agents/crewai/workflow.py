# 代碼功能說明: CrewAI Workflow 執行核心
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""CrewAI 工作流編排實作。"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from agents.workflows.base import WorkflowExecutionResult, WorkflowRequestContext
from agents.crewai.settings import CrewAISettings
from agents.crewai.llm_adapter import OllamaLLMAdapter
from agents.crewai.process_engine import ProcessEngine
from agents.crewai.token_budget import TokenBudgetGuard
from agents.crewai.manager import CrewManager
from agents.crewai.models import CrewConfig
from agents.crewai.task_registry import TaskRegistry
from agents.crewai.task_models import CrewTask, TaskStatus, TaskResult
from agent_process.context.recorder import ContextRecorder

logger = logging.getLogger(__name__)

try:  # pragma: no cover - API 層未載入時允許繼續
    from services.api.telemetry import publish_workflow_metrics
except Exception:  # pylint: disable=broad-except
    publish_workflow_metrics = None  # type: ignore[assignment]


class CrewAIWorkflow:
    """負責將請求映射到 CrewAI 的工作流執行器。"""

    def __init__(
        self,
        *,
        settings: CrewAISettings,
        request_ctx: WorkflowRequestContext,
    ) -> None:
        """
        初始化 CrewAI Workflow。

        Args:
            settings: CrewAI 設定
            request_ctx: 請求上下文
        """
        self._settings = settings
        self._ctx = request_ctx
        self._llm_adapter = OllamaLLMAdapter(
            model_name=settings.default_llm,
            temperature=0.7,
        )
        self._process_engine = ProcessEngine(self._llm_adapter)
        self._crew_manager = CrewManager()
        self._task_registry = TaskRegistry()
        self._context_recorder = ContextRecorder()
        self._token_guard = TokenBudgetGuard(settings.token_budget)
        self._telemetry_events: List[Dict[str, Any]] = []

    async def run(self) -> WorkflowExecutionResult:
        """執行整個工作流。"""
        start_time = time.time()

        # 記錄開始事件
        self._emit_telemetry("workflow.start", {"task_id": self._ctx.task_id})

        try:
            # 獲取或創建 Crew 配置
            crew_config = self._get_or_create_crew_config()

            # 創建 Agent 和 Task（這裡需要從 agent_templates 和 task_registry 獲取）
            # 暫時使用簡化版本，後續會在 T3.2.4 和 T3.2.5 中完善
            agents = self._create_agents(crew_config)
            tasks = self._create_tasks(crew_config)

            # 創建 Crew
            crew = self._process_engine.create_crew_from_config(
                crew_config,
                agents,
                tasks,
                self._token_guard,
            )

            # 註冊任務到 Task Registry
            crew_task = CrewTask(
                task_id=self._ctx.task_id,
                crew_id=crew_config.crew_id,
                description=self._ctx.task,
                status=TaskStatus.IN_PROGRESS,
            )
            self._task_registry.register_task(crew_task)
            self._task_registry.update_task_status(
                self._ctx.task_id,
                TaskStatus.IN_PROGRESS,
                message="Task execution started",
            )

            # 記錄任務開始
            self._record_context("task_start", {"task": self._ctx.task})

            # 執行 Crew
            self._emit_telemetry("crew.execute.start", {"crew_id": crew_config.crew_id})
            result = crew.kickoff(inputs={"task": self._ctx.task})
            self._emit_telemetry(
                "crew.execute.complete", {"crew_id": crew_config.crew_id}
            )

            # 記錄任務完成
            execution_time = time.time() - start_time
            self._record_context(
                "task_complete", {"result": str(result), "time": execution_time}
            )

            # 更新任務狀態
            self._task_registry.update_task_status(
                self._ctx.task_id,
                TaskStatus.COMPLETED,
                message="Task execution completed",
            )

            # 保存任務結果
            task_result = TaskResult(
                task_id=self._ctx.task_id,
                status=TaskStatus.COMPLETED,
                output=str(result),
                execution_time=execution_time,
                token_usage=self._token_guard.usage.total_tokens,
            )
            self._task_registry.save_task_result(task_result)

            # 更新觀測指標
            self._update_metrics(crew_config.crew_id, execution_time)

            # 構建執行結果
            status = "completed"
            if self._token_guard.is_exceeded():
                status = "token_budget_exceeded"
                logger.warning("Token budget exceeded during execution")

            workflow_result = WorkflowExecutionResult(
                status=status,
                output={"result": str(result)},
                reasoning="CrewAI workflow execution finished",
                telemetry=self._telemetry_events,
                state_snapshot={
                    "crew_id": crew_config.crew_id,
                    "execution_time": execution_time,
                    "token_usage": self._token_guard.usage.total_tokens,
                },
            )

            # 發布指標
            if publish_workflow_metrics is not None:
                try:
                    publish_workflow_metrics(
                        workflow="crewai",
                        status=status,
                        steps=len(tasks),
                        crew_id=crew_config.crew_id,
                        events=self._telemetry_events,
                    )
                except Exception as exc:  # pragma: no cover
                    logger.warning(f"Failed to publish metrics: {exc}")

            return workflow_result

        except Exception as exc:
            execution_time = time.time() - start_time
            logger.error(f"CrewAI workflow execution failed: {exc}", exc_info=True)
            self._emit_telemetry("workflow.failed", {"error": str(exc)})
            self._record_context(
                "task_failed", {"error": str(exc), "time": execution_time}
            )

            # 更新任務狀態為失敗
            self._task_registry.update_task_status(
                self._ctx.task_id,
                TaskStatus.FAILED,
                message=f"Task execution failed: {exc}",
            )

            # 保存任務結果
            task_result = TaskResult(
                task_id=self._ctx.task_id,
                status=TaskStatus.FAILED,
                error=str(exc),
                execution_time=execution_time,
                token_usage=self._token_guard.usage.total_tokens,
            )
            self._task_registry.save_task_result(task_result)

            return WorkflowExecutionResult(
                status="failed",
                output={"error": str(exc)},
                reasoning=f"CrewAI workflow execution failed: {exc}",
                telemetry=self._telemetry_events,
                state_snapshot={"execution_time": execution_time},
            )

    def _get_or_create_crew_config(self) -> CrewConfig:
        """獲取或創建 Crew 配置。"""
        # 從 workflow_config 中獲取 crew_id，如果沒有則創建新的
        workflow_config = self._ctx.workflow_config or {}
        crew_id = workflow_config.get("crew_id")

        if crew_id:
            config = self._crew_manager.get_crew(crew_id)
            if config:
                return config

        # 創建新的 Crew
        collaboration_mode = workflow_config.get(
            "collaboration_mode", self._settings.collaboration_mode
        )
        from agents.crewai.models import CollaborationMode

        mode = (
            CollaborationMode(collaboration_mode)
            if isinstance(collaboration_mode, str)
            else collaboration_mode
        )

        config = self._crew_manager.create_crew(
            name=f"Crew-{self._ctx.task_id[:8]}",
            description=f"Crew for task: {self._ctx.task[:100]}",
            collaboration_mode=mode,
            resource_quota=self._settings.token_budget,
        )

        return config

    def _create_agents(self, crew_config: CrewConfig) -> List[Any]:
        """創建 Agent 列表。"""
        # 這裡暫時返回空列表，後續會在 T3.2.4 中實現
        # 需要從 agent_templates 創建 Agent
        from crewai import Agent

        agents = []
        for agent_role in crew_config.agents:
            agent = Agent(
                role=agent_role.role,
                goal=agent_role.goal,
                backstory=agent_role.backstory,
                verbose=agent_role.verbose,
                allow_delegation=agent_role.allow_delegation,
                llm=self._llm_adapter,
            )
            agents.append(agent)

        return agents

    def _create_tasks(self, crew_config: CrewConfig) -> List[Any]:
        """創建 Task 列表。"""
        # 這裡暫時返回簡化版本，後續會在 T3.2.5 中實現
        from crewai import Task

        tasks = [
            Task(
                description=self._ctx.task,
                agent=crew_config.agents[0] if crew_config.agents else None,
            )
        ]

        return tasks

    def _record_context(self, event_type: str, data: Dict[str, Any]) -> None:
        """記錄上下文。"""
        if not self._settings.enable_memory:
            return

        try:
            content = f"{event_type}: {data}"
            self._context_recorder.record(
                session_id=self._ctx.task_id,
                role="system",
                content=content,
                metadata=data,
            )
        except Exception as exc:
            logger.warning(f"Failed to record context: {exc}")

    def _emit_telemetry(self, event_name: str, payload: Dict[str, Any]) -> None:
        """發送觀測事件。"""
        event = {"name": event_name, "payload": payload}
        self._telemetry_events.append(event)
        logger.debug(f"Telemetry event: {event_name}")

    def _update_metrics(
        self,
        crew_id: str,
        execution_time: float,
    ) -> None:
        """更新觀測指標。"""
        try:
            self._crew_manager.update_metrics(
                crew_id=crew_id,
                token_usage=self._token_guard.usage.total_tokens,
                execution_time=execution_time,
                task_count=1,
                success_rate=1.0,
            )
        except Exception as exc:
            logger.warning(f"Failed to update metrics: {exc}")
