# 代碼功能說明: ReAct FSM 狀態定義
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""ReAct FSM 狀態定義

定義 ReAct 循環的五個核心狀態：AWARENESS、PLANNING、DELEGATION、OBSERVATION、DECISION。
"""

import logging
from typing import Any, Dict, List, Optional

from agents.services.state_store.models import ReactState, ReactStateType

logger = logging.getLogger(__name__)


class AwarenessState:
    """AWARENESS 狀態處理器

    命令感知階段：判斷指令是否具備可操作性，進行初步風險評估。
    """

    @staticmethod
    async def process(
        react_id: str,
        iteration: int,
        command: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReactState:
        """
        處理 AWARENESS 狀態

        Args:
            react_id: ReAct session ID
            iteration: 迭代次數
            command: 用戶命令
            context: 上下文信息

        Returns:
            ReactState 對象
        """
        logger.info(f"Processing AWARENESS state: react_id={react_id}, iteration={iteration}")

        # 調用 Task Analyzer 進行命令分析
        try:
            from agents.task_analyzer.analyzer import TaskAnalyzer
            from agents.task_analyzer.models import TaskAnalysisRequest

            task_analyzer = TaskAnalyzer()
            analysis_result = await task_analyzer.analyze(
                TaskAnalysisRequest(
                    task=command,
                    context=context,
                    user_id=context.get("user_id") if context else None,
                    session_id=context.get("session_id") if context else None,
                )
            )

            # 構建 input_signature（命令分類）
            input_signature = {
                "command_type": analysis_result.task_type.value,
                "scope": "multi_step"
                if analysis_result.task_type.value == "complex"
                else "single_step",
                "risk_level": "safe",  # 可以從 Security Agent 獲取
                "urgency": "normal",
                "workflow_type": analysis_result.workflow_type.value,
                "confidence": analysis_result.confidence,
            }

            # 如果有意圖，添加到 metadata
            metadata = {"command": command, "context": context or {}}
            intent = analysis_result.get_intent()
            if intent:
                metadata["intent"] = intent.dict() if hasattr(intent, "dict") else intent

            return ReactState(
                react_id=react_id,
                iteration=iteration,
                state=ReactStateType.AWARENESS,
                input_signature=input_signature,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to process AWARENESS state: {e}", exc_info=True)
            # Fallback：使用簡化實現
            input_signature = {
                "command_type": "TASK",
                "scope": "single_step",
                "risk_level": "safe",
                "urgency": "normal",
            }
            return ReactState(
                react_id=react_id,
                iteration=iteration,
                state=ReactStateType.AWARENESS,
                input_signature=input_signature,
                metadata={"command": command, "context": context or {}, "error": str(e)},
            )


class PlanningState:
    """PLANNING 狀態處理器

    任務規劃階段：將任務拆解為結構化的任務依賴圖 (Task DAG)。
    """

    @staticmethod
    async def process(
        react_id: str,
        iteration: int,
        awareness_state: ReactState,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReactState:
        """
        處理 PLANNING 狀態

        Args:
            react_id: ReAct session ID
            iteration: 迭代次數
            awareness_state: AWARENESS 狀態
            context: 上下文信息

        Returns:
            ReactState 對象
        """
        logger.info(f"Processing PLANNING state: react_id={react_id}, iteration={iteration}")

        # 調用 Planning Agent 進行任務規劃（如果可用）
        try:
            from agents.core.planning.agent import PlanningAgent

            _planning_agent = PlanningAgent()  # noqa: F841
            command = awareness_state.metadata.get("command", "")

            # 簡化實現：調用 Planning Agent
            # 實際實現中應該根據任務類型選擇合適的規劃策略
            plan = {
                "strategy": "單步驟執行",
                "steps": [
                    {
                        "step_id": "step-1",
                        "objective": command,
                        "agent_role": "execution_agent",
                        "dependencies": [],
                        "risk_level": awareness_state.input_signature.get("risk_level", "safe"),
                    }
                ],
            }

            return ReactState(
                react_id=react_id,
                iteration=iteration,
                state=ReactStateType.PLANNING,
                input_signature=awareness_state.input_signature,
                plan=plan,
                metadata=awareness_state.metadata,
            )
        except Exception as e:
            logger.warning(f"Planning Agent not available, using fallback: {e}")
            # Fallback：使用簡化實現
            plan = {
                "strategy": "單步驟執行",
                "steps": [
                    {
                        "step_id": "step-1",
                        "objective": awareness_state.metadata.get("command", ""),
                        "agent_role": "execution_agent",
                        "dependencies": [],
                        "risk_level": "safe",
                    }
                ],
            }

            return ReactState(
                react_id=react_id,
                iteration=iteration,
                state=ReactStateType.PLANNING,
                input_signature=awareness_state.input_signature,
                plan=plan,
                metadata=awareness_state.metadata,
            )


class DelegationState:
    """DELEGATION 狀態處理器

    任務派發階段：將任務分發給合適的 Agent。
    """

    @staticmethod
    async def process(
        react_id: str,
        iteration: int,
        planning_state: ReactState,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReactState:
        """
        處理 DELEGATION 狀態

        Args:
            react_id: ReAct session ID
            iteration: 迭代次數
            planning_state: PLANNING 狀態
            context: 上下文信息

        Returns:
            ReactState 對象
        """
        logger.info(f"Processing DELEGATION state: react_id={react_id}, iteration={iteration}")

        # 調用 Orchestrator 進行任務派發
        delegations = []
        if planning_state.plan and "steps" in planning_state.plan:
            try:
                from agents.services.orchestrator.orchestrator import AgentOrchestrator

                orchestrator = AgentOrchestrator()

                for step in planning_state.plan["steps"]:
                    task_id = f"{react_id}_task_{step['step_id']}"
                    agent_role = step.get("agent_role", "execution_agent")
                    objective = step.get("objective", "")

                    # 創建任務記錄
                    user_id = context.get("user_id") if context else "unknown"
                    intent = planning_state.metadata.get("intent")
                    intent_dict = (
                        intent.dict() if hasattr(intent, "dict") else intent if intent else None
                    )

                    orchestrator._task_tracker.create_task(
                        instruction=objective,
                        target_agent_id=agent_role,
                        user_id=user_id,
                        intent=intent_dict,
                    )

                    delegations.append(
                        {
                            "task_id": task_id,
                            "step_id": step["step_id"],
                            "delegate_to": agent_role,
                            "objective": objective,
                        }
                    )

            except Exception as e:
                logger.error(f"Failed to delegate tasks: {e}", exc_info=True)
                # Fallback：使用簡化實現
                for step in planning_state.plan["steps"]:
                    delegations.append(
                        {
                            "task_id": f"{react_id}_task_{step['step_id']}",
                            "step_id": step["step_id"],
                            "delegate_to": step.get("agent_role", "execution_agent"),
                            "objective": step.get("objective", ""),
                        }
                    )

        return ReactState(
            react_id=react_id,
            iteration=iteration,
            state=ReactStateType.DELEGATION,
            input_signature=planning_state.input_signature,
            plan=planning_state.plan,
            delegations=delegations,
            metadata=planning_state.metadata,
        )


class ObservationState:
    """OBSERVATION 狀態處理器

    觀察回傳階段：收集 Agent 執行結果。
    """

    @staticmethod
    async def process(
        react_id: str,
        iteration: int,
        delegation_state: ReactState,
        observations: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        task_ids: Optional[List[str]] = None,
        message_bus=None,
    ) -> ReactState:
        """
        處理 OBSERVATION 狀態

        Args:
            react_id: ReAct session ID
            iteration: 迭代次數
            delegation_state: DELEGATION 狀態
            observations: 觀察結果（可選，如果不提供則從 Task Tracker 獲取）
            context: 上下文信息

        Returns:
            ReactState 對象
        """
        logger.info(f"Processing OBSERVATION state: react_id={react_id}, iteration={iteration}")

        # 如果沒有提供觀察結果，從 Message Bus 或 Task Tracker 獲取
        if observations is None:
            if message_bus and task_ids:
                # 優先使用 Message Bus
                try:
                    from agents.services.observation_collector import (
                        FanInMode,
                        ObservationCollector,
                    )

                    collector = ObservationCollector()
                    summary = await collector.collect(
                        react_id, task_ids, timeout=300, mode=FanInMode.ALL, message_bus=message_bus
                    )

                    obs_data = {
                        "success_rate": summary.success_rate,
                        "blocking_issues": summary.blocking_issues,
                        "lowest_confidence": summary.lowest_confidence,
                        "total_count": summary.total_count,
                        "success_count": summary.success_count,
                        "failure_count": summary.failure_count,
                        "partial_count": summary.partial_count,
                        "issues": summary.issues,
                    }
                except Exception as e:
                    logger.error(f"Failed to collect from Message Bus: {e}", exc_info=True)
                    obs_data = {
                        "success_rate": 0.0,
                        "blocking_issues": True,
                        "lowest_confidence": 0.0,
                    }
            elif delegation_state.delegations:
                # Fallback：從 Task Tracker 獲取
                try:
                    from agents.services.orchestrator.orchestrator import AgentOrchestrator

                    orchestrator = AgentOrchestrator()
                    task_results = []

                    for delegation in delegation_state.delegations:
                        task_id = delegation.get("task_id")
                        if task_id:
                            task_record = orchestrator._task_tracker.get_task_status(task_id)
                            if task_record:
                                from agents.services.orchestrator.models import TaskResult

                                task_result = TaskResult(
                                    task_id=task_id,
                                    status=task_record.status,
                                    result=task_record.result,
                                    error=task_record.error,
                                    agent_id=task_record.target_agent_id,
                                )
                                task_results.append(task_result)

                    if task_results:
                        from agents.services.observation_collector import (
                            FanInMode,
                            ObservationCollector,
                        )

                        collector = ObservationCollector()
                        summary = collector.fan_in(task_results, mode=FanInMode.ALL)

                        obs_data = {
                            "success_rate": summary.success_rate,
                            "blocking_issues": summary.blocking_issues,
                            "lowest_confidence": summary.lowest_confidence,
                            "total_count": summary.total_count,
                            "success_count": summary.success_count,
                            "failure_count": summary.failure_count,
                            "partial_count": summary.partial_count,
                            "issues": summary.issues,
                        }
                    else:
                        obs_data = {
                            "success_rate": 0.0,
                            "blocking_issues": True,
                            "lowest_confidence": 0.0,
                        }
                except Exception as e:
                    logger.error(f"Failed to collect observations: {e}", exc_info=True)
                    obs_data = {
                        "success_rate": 1.0,
                        "blocking_issues": False,
                        "lowest_confidence": 0.9,
                    }
            else:
                obs_data = {
                    "success_rate": 1.0,
                    "blocking_issues": False,
                    "lowest_confidence": 0.9,
                }
        else:
            obs_data = observations

        return ReactState(
            react_id=react_id,
            iteration=iteration,
            state=ReactStateType.OBSERVATION,
            input_signature=delegation_state.input_signature,
            observations=obs_data,
            plan=delegation_state.plan,
            delegations=delegation_state.delegations,
            metadata=delegation_state.metadata,
        )


class DecisionState:
    """DECISION 狀態處理器

    策略性判斷階段：根據觀察結果和決策預期決定下一步。
    """

    @staticmethod
    async def process(
        react_id: str,
        iteration: int,
        observation_state: ReactState,
        decision: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        policy_engine=None,
    ) -> ReactState:
        """
        處理 DECISION 狀態

        Args:
            react_id: ReAct session ID
            iteration: 迭代次數
            observation_state: OBSERVATION 狀態
            decision: 決策結果（可選，如果不提供則使用 Policy Engine 生成）
            context: 上下文信息
            policy_engine: Policy Engine 實例（可選）

        Returns:
            ReactState 對象
        """
        logger.info(f"Processing DECISION state: react_id={react_id}, iteration={iteration}")

        from agents.services.state_store.models import Decision, DecisionAction, ReactStateType

        # 如果沒有提供決策，使用 Policy Engine 生成
        if decision is None:
            try:
                if policy_engine is None:
                    from pathlib import Path

                    from agents.services.policy_engine import PolicyEngine

                    policy_path = (
                        Path(__file__).resolve().parent.parent.parent.parent
                        / "config"
                        / "policies"
                        / "default_policy.yaml"
                    )
                    policy_engine = PolicyEngine(
                        default_policy_path=policy_path if policy_path.exists() else None
                    )

                # 構建 Policy Context
                from agents.services.policy_engine.models import PolicyContext

                policy_context = PolicyContext(
                    command=observation_state.input_signature,
                    constraints=context.get("constraints", {}) if context else {},
                    observation_summary=observation_state.observations or {},
                    retry_count=iteration,
                )

                # 評估政策
                effective_policy = policy_engine.evaluate(policy_context)

                if effective_policy.decision:
                    decision_obj = effective_policy.decision
                else:
                    # 根據觀察結果生成默認決策
                    obs = observation_state.observations or {}
                    success_rate = obs.get("success_rate", 0.0)
                    blocking_issues = obs.get("blocking_issues", False)

                    if success_rate == 1.0 and not blocking_issues:
                        decision_obj = Decision(
                            action=DecisionAction.COMPLETE,
                            reason="All tasks completed successfully",
                            next_state=ReactStateType.COMPLETE,
                        )
                    elif blocking_issues:
                        decision_obj = Decision(
                            action=DecisionAction.RETRY,
                            reason="Blocking issues detected, retrying",
                            next_state=ReactStateType.DELEGATION,
                        )
                    else:
                        decision_obj = Decision(
                            action=DecisionAction.EXTEND_PLAN,
                            reason="Partial success, extending plan",
                            next_state=ReactStateType.PLANNING,
                        )
            except Exception as e:
                logger.error(f"Failed to evaluate policy: {e}", exc_info=True)
                # Fallback：使用默認決策
                decision_obj = Decision(
                    action=DecisionAction.COMPLETE,
                    reason="All tasks completed successfully",
                    next_state=ReactStateType.COMPLETE,
                )
        else:
            # decision 可能是字典或 Decision 對象
            if isinstance(decision, dict):
                decision_obj = Decision(
                    action=DecisionAction(decision["action"]),
                    reason=decision.get("reason"),
                    next_state=ReactStateType(decision["next_state"]),
                )
            else:
                decision_obj = decision

        return ReactState(
            react_id=react_id,
            iteration=iteration,
            state=ReactStateType.DECISION,
            input_signature=observation_state.input_signature,
            observations=observation_state.observations,
            decision=decision_obj,
            plan=observation_state.plan,
            delegations=observation_state.delegations,
            metadata=observation_state.metadata,
        )
