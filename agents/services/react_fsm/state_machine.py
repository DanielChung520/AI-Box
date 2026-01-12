# 代碼功能說明: ReAct FSM 狀態機核心類
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""ReAct FSM 狀態機核心類

實現 GRO 規範的 ReAct 循環，支持狀態轉移、持久化和回放。
"""

import logging
import uuid
from typing import Any, Dict, Optional

from agents.services.observation_collector import ObservationCollector
from agents.services.policy_engine import PolicyEngine
from agents.services.react_fsm.models import ReactResult
from agents.services.react_fsm.states import (
    AwarenessState,
    DecisionState,
    DelegationState,
    ObservationState,
    PlanningState,
)
from agents.services.react_fsm.transitions import StateTransitions
from agents.services.state_store import StateStore
from agents.services.state_store.models import ReactStateType

logger = logging.getLogger(__name__)


class ReactStateMachine:
    """ReAct FSM 狀態機核心類

    實現 GRO 規範的 ReAct 循環，支持狀態轉移、持久化和回放。
    """

    def __init__(
        self,
        state_store: Optional[StateStore] = None,
        policy_engine: Optional[PolicyEngine] = None,
        observation_collector: Optional[ObservationCollector] = None,
        message_bus=None,
    ):
        """
        初始化 ReAct FSM

        Args:
            state_store: State Store 實例（可選）
            policy_engine: Policy Engine 實例（可選）
            observation_collector: Observation Collector 實例（可選）
            message_bus: Message Bus 實例（可選）
        """
        self.state_store = state_store or StateStore()
        self.policy_engine = policy_engine or PolicyEngine()
        self.observation_collector = observation_collector or ObservationCollector()
        self.message_bus = message_bus

    async def execute(
        self,
        command: str,
        context: Optional[Dict[str, Any]] = None,
        react_id: Optional[str] = None,
    ) -> ReactResult:
        """
        執行 ReAct 循環

        Args:
            command: 用戶命令
            context: 上下文信息
            react_id: ReAct session ID（可選，如果不提供則自動生成）

        Returns:
            ReactResult 對象
        """
        react_id = react_id or str(uuid.uuid4())
        iteration = 0
        states = []

        logger.info(f"Starting ReAct FSM execution: react_id={react_id}")

        try:
            # AWARENESS 階段
            awareness_state = await AwarenessState.process(react_id, iteration, command, context)
            states.append(awareness_state)
            self.state_store.save_state(awareness_state)

            # PLANNING 階段
            iteration += 1
            planning_state = await PlanningState.process(
                react_id, iteration, awareness_state, context
            )
            states.append(planning_state)
            self.state_store.save_state(planning_state)

            # DELEGATION 階段
            iteration += 1
            delegation_state = await DelegationState.process(
                react_id, iteration, planning_state, context
            )
            states.append(delegation_state)
            self.state_store.save_state(delegation_state)

            # OBSERVATION 階段
            iteration += 1
            # 收集任務 ID
            task_ids = [
                d.get("task_id") for d in (delegation_state.delegations or []) if d.get("task_id")
            ]
            observation_state = await ObservationState.process(
                react_id, iteration, delegation_state, None, context, task_ids, self.message_bus
            )
            states.append(observation_state)
            self.state_store.save_state(observation_state)

            # DECISION 階段
            iteration += 1
            decision_state = await DecisionState.process(
                react_id, iteration, observation_state, None, context, self.policy_engine
            )
            states.append(decision_state)
            self.state_store.save_state(decision_state)

            # 保存 Decision Log
            if decision_state.decision:
                from agents.services.state_store.models import DecisionLog, DecisionOutcome

                # 簡化實現：根據決策動作確定 outcome
                outcome_mapping = {
                    "complete": DecisionOutcome.SUCCESS,
                    "retry": DecisionOutcome.PARTIAL,
                    "extend_plan": DecisionOutcome.PARTIAL,
                    "escalate": DecisionOutcome.FAILURE,
                }

                outcome = outcome_mapping.get(
                    decision_state.decision.action.value, DecisionOutcome.PARTIAL
                )

                decision_log = DecisionLog(
                    react_id=react_id,
                    iteration=iteration,
                    state=ReactStateType.DECISION,
                    input_signature=decision_state.input_signature,
                    observations=decision_state.observations,
                    decision=decision_state.decision,
                    outcome=outcome,
                )
                self.state_store.save_decision_log(decision_log)

            # 判斷是否繼續循環
            while StateTransitions.should_continue(decision_state):
                next_iteration = StateTransitions.increment_iteration(decision_state)
                next_state_type = StateTransitions.get_next_state(decision_state)

                if next_state_type is None:
                    logger.warning("Cannot determine next state, breaking loop")
                    break

                if next_state_type == ReactStateType.COMPLETE:
                    break

                # 根據下一個狀態類型處理
                if next_state_type == ReactStateType.PLANNING:
                    planning_state = await PlanningState.process(
                        react_id, next_iteration, decision_state, context
                    )
                    states.append(planning_state)
                    self.state_store.save_state(planning_state)
                    decision_state = planning_state

                elif next_state_type == ReactStateType.DELEGATION:
                    delegation_state = await DelegationState.process(
                        react_id, next_iteration, decision_state, context
                    )
                    states.append(delegation_state)
                    self.state_store.save_state(delegation_state)

                    observation_state = await ObservationState.process(
                        react_id, next_iteration + 1, delegation_state, None, context
                    )
                    states.append(observation_state)
                    self.state_store.save_state(observation_state)

                    decision_state = await DecisionState.process(
                        react_id,
                        next_iteration + 2,
                        observation_state,
                        None,
                        context,
                        self.policy_engine,
                    )
                    states.append(decision_state)
                    self.state_store.save_state(decision_state)

                iteration = next_iteration

            # 構建結果
            success = (
                decision_state.decision is not None
                and decision_state.decision.action.value == "complete"
            )

            final_state = (
                ReactStateType.COMPLETE
                if decision_state.decision and decision_state.decision.action.value == "complete"
                else ReactStateType.DECISION
            )

            result = ReactResult(
                react_id=react_id,
                success=success,
                final_state=final_state,
                result=decision_state.observations,
                error=None,
                total_iterations=iteration + 1,
                states=states,
            )

            logger.info(
                f"ReAct FSM execution completed: react_id={react_id}, success={success}, iterations={iteration + 1}"
            )

            return result

        except Exception as e:
            logger.error(f"ReAct FSM execution failed: {e}", exc_info=True)
            return ReactResult(
                react_id=react_id,
                success=False,
                final_state=ReactStateType.DECISION,
                result=None,
                error=str(e),
                total_iterations=iteration + 1,
                states=states,
            )

    async def replay(self, react_id: str) -> ReactResult:
        """
        回放 ReAct 循環

        Args:
            react_id: ReAct session ID

        Returns:
            ReactResult 對象
        """
        states = self.state_store.replay_states(react_id)

        if not states:
            raise ValueError(f"No states found for react_id: {react_id}")

        # 獲取最後一個狀態
        final_state = states[-1]

        success = (
            final_state.decision is not None and final_state.decision.action.value == "complete"
        )

        return ReactResult(
            react_id=react_id,
            success=success,
            final_state=final_state.state,
            result=final_state.observations,
            error=None,
            total_iterations=len(states),
            states=states,
        )
