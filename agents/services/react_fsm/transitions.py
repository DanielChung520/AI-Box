# 代碼功能說明: ReAct FSM 狀態轉移邏輯
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""ReAct FSM 狀態轉移邏輯

實現 ReAct 循環的狀態轉移，支持 Retry、Extend Plan 等操作。
"""

import logging
from typing import Optional

from agents.services.state_store.models import DecisionAction, ReactState, ReactStateType

logger = logging.getLogger(__name__)


class StateTransitions:
    """狀態轉移類"""

    @staticmethod
    def get_next_state(current_state: ReactState) -> Optional[ReactStateType]:
        """
        獲取下一個狀態

        Args:
            current_state: 當前狀態

        Returns:
            下一個狀態，如果沒有則返回 None
        """
        if current_state.decision is None:
            # 沒有決策，無法確定下一個狀態
            return None

        decision = current_state.decision

        # 根據決策動作確定下一個狀態
        if decision.action == DecisionAction.COMPLETE:
            return ReactStateType.COMPLETE  # 完成，結束循環

        elif decision.action == DecisionAction.RETRY:
            return ReactStateType.DELEGATION  # 重試，回到 DELEGATION

        elif decision.action == DecisionAction.EXTEND_PLAN:
            return ReactStateType.PLANNING  # 擴展計劃，回到 PLANNING

        elif decision.action == DecisionAction.ESCALATE:
            return ReactStateType.COMPLETE  # 升級，結束循環

        else:
            logger.warning(f"Unknown decision action: {decision.action}")
            return None

    @staticmethod
    def should_continue(current_state: ReactState) -> bool:
        """
        判斷是否應該繼續循環

        Args:
            current_state: 當前狀態

        Returns:
            是否應該繼續
        """
        if current_state.decision is None:
            return True  # 沒有決策，繼續循環

        decision = current_state.decision

        # 只有 COMPLETE 和 ESCALATE 會結束循環
        if decision.action in [DecisionAction.COMPLETE, DecisionAction.ESCALATE]:
            return False

        # RETRY 和 EXTEND_PLAN 會繼續循環
        return True

    @staticmethod
    def increment_iteration(current_state: ReactState) -> int:
        """
        獲取下一個迭代次數

        Args:
            current_state: 當前狀態

        Returns:
            下一個迭代次數
        """
        if current_state.decision is None:
            return current_state.iteration + 1

        decision = current_state.decision

        # RETRY 和 EXTEND_PLAN 會增加迭代次數
        if decision.action in [DecisionAction.RETRY, DecisionAction.EXTEND_PLAN]:
            return current_state.iteration + 1

        # COMPLETE 和 ESCALATE 不會增加迭代次數（循環結束）
        return current_state.iteration
