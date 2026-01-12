# 代碼功能說明: State Store 狀態回放機制
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""State Store 狀態回放機制

支持 ReAct 狀態的回放和重放，用於審計、調試和訓練。
"""

import logging
from typing import List, Optional

from agents.services.state_store.models import DecisionLog, ReactState
from agents.services.state_store.state_persistence import StatePersistence

logger = logging.getLogger(__name__)


class StateReplay:
    """狀態回放類"""

    def __init__(self, persistence: Optional[StatePersistence] = None):
        """
        初始化狀態回放

        Args:
            persistence: 狀態持久化實例（可選）
        """
        self.persistence = persistence or StatePersistence()

    def replay(self, react_id: str) -> List[ReactState]:
        """
        回放指定 react_id 的所有狀態

        Args:
            react_id: ReAct session ID

        Returns:
            狀態列表（按 iteration 排序）
        """
        states = self.persistence.get_states_by_react_id(react_id)
        logger.info(f"Replaying {len(states)} states for react_id={react_id}")
        return states

    def replay_decision_logs(self, react_id: str) -> List[DecisionLog]:
        """
        回放指定 react_id 的所有 Decision Log

        Args:
            react_id: ReAct session ID

        Returns:
            Decision Log 列表（按 iteration 排序）
        """
        logs = self.persistence.get_decision_logs_by_react_id(react_id)
        logger.info(f"Replaying {len(logs)} decision logs for react_id={react_id}")
        return logs

    def get_state_history(self, react_id: str) -> dict:
        """
        獲取完整的狀態歷史（包括狀態和決策日誌）

        Args:
            react_id: ReAct session ID

        Returns:
            包含 states 和 decision_logs 的字典
        """
        states = self.replay(react_id)
        decision_logs = self.replay_decision_logs(react_id)

        return {
            "react_id": react_id,
            "states": [state.to_dict() for state in states],
            "decision_logs": [log.to_dict() for log in decision_logs],
            "total_iterations": len(states),
        }
