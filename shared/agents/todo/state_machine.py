# 代碼功能說明: Agent Todo 狀態機
# 創建日期: 2026-02-07
# 創建人: OpenCode AI
# 最後修改日期: 2026-02-07

"""Agent Todo 狀態機引擎"""

import logging
from typing import Dict, Set, Optional, Tuple, List, Any
from datetime import datetime

from .schema import TodoState

logger = logging.getLogger(__name__)


VALID_TRANSITIONS: Dict[TodoState, Set[TodoState]] = {
    TodoState.PENDING: {TodoState.DISPATCHED},
    TodoState.DISPATCHED: {TodoState.EXECUTING, TodoState.FAILED},
    TodoState.EXECUTING: {TodoState.COMPLETED, TodoState.FAILED},
    TodoState.FAILED: {TodoState.DISPATCHED, TodoState.COMPLETED},
}


TRANSITION_EVENTS: Dict[Tuple[TodoState, TodoState], str] = {
    (TodoState.PENDING, TodoState.DISPATCHED): "dispatched",
    (TodoState.DISPATCHED, TodoState.EXECUTING): "agent_ack",
    (TodoState.EXECUTING, TodoState.COMPLETED): "done",
    (TodoState.EXECUTING, TodoState.FAILED): "fail",
    (TodoState.FAILED, TodoState.DISPATCHED): "retry",
    (TodoState.FAILED, TodoState.COMPLETED): "skip",
}


class TodoStateMachine:
    """Todo 狀態機"""

    @staticmethod
    def can_transition(current: TodoState, next_state: TodoState) -> bool:
        """檢查是否允許狀態轉移"""
        return next_state in VALID_TRANSITIONS.get(current, set())

    @staticmethod
    def validate_transition(current: TodoState, next_state: TodoState) -> Tuple[bool, str]:
        """驗證狀態轉移，返回 (是否允許, 事件名稱)"""
        if TodoStateMachine.can_transition(current, next_state):
            event = TRANSITION_EVENTS.get((current, next_state), "unknown")
            return True, event
        return False, ""

    @staticmethod
    def get_next_states(current: TodoState) -> Set[TodoState]:
        """取得所有可能的下一狀態"""
        return VALID_TRANSITIONS.get(current, set()).copy()

    @staticmethod
    def is_terminal_state(state: TodoState) -> bool:
        """檢查是否為終端狀態"""
        return state in {TodoState.COMPLETED}

    @staticmethod
    def is_retryable(state: TodoState) -> bool:
        """檢查是否可重試"""
        return state == TodoState.FAILED

    @staticmethod
    def transition(
        current: TodoState, next_state: TodoState, timestamp: Optional[datetime] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """執行狀態轉移，返回 (是否成功, 事件名稱, 歷史記錄)"""
        valid, event = TodoStateMachine.validate_transition(current, next_state)

        if not valid:
            logger.warning(f"Invalid transition: {current} -> {next_state}")
            return False, "", {}

        history_entry = {
            "from_state": current,
            "to_state": next_state,
            "event": event,
            "timestamp": (timestamp or datetime.utcnow()).isoformat(),
        }

        logger.info(f"State transition: {current} -> {next_state} (event: {event})")
        return True, event, history_entry


class TodoStateManager:
    """Todo 狀態管理器 - 管理狀態轉移歷史"""

    def __init__(self):
        self._history: List[Dict[str, Any]] = []

    def transition(self, current: TodoState, next_state: TodoState) -> Tuple[bool, str]:
        """執行狀態轉移"""
        success, event, history = TodoStateMachine.transition(current, next_state)

        if success:
            self._history.append(history)

        return success, event

    def get_history(self) -> List[Dict[str, Any]]:
        """取得轉移歷史"""
        return self._history.copy()

    def clear(self):
        """清除歷史"""
        self._history = []
