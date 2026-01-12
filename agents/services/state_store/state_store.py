# 代碼功能說明: State Store 核心類
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""State Store 核心類

負責 ReAct 狀態的持久化、Decision Log 存儲和狀態回放。
符合 GRO 規範。
"""

import logging
from typing import List, Optional

from agents.services.state_store.models import DecisionLog, ReactState
from agents.services.state_store.state_persistence import StatePersistence
from agents.services.state_store.state_replay import StateReplay
from database.arangodb import ArangoDBClient

logger = logging.getLogger(__name__)


class StateStore:
    """State Store 核心類

    負責 ReAct 狀態的持久化、Decision Log 存儲和狀態回放。
    符合 GRO 規範。
    """

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 State Store

        Args:
            client: ArangoDB 客戶端（可選，如果不提供則使用默認客戶端）
        """
        self.persistence = StatePersistence(client)
        self.replay = StateReplay(self.persistence)

    def save_state(self, state: ReactState) -> None:
        """
        保存 ReAct 狀態

        Args:
            state: ReAct 狀態對象
        """
        self.persistence.save_state(state)

    def get_state(self, react_id: str, iteration: int) -> Optional[ReactState]:
        """
        獲取 ReAct 狀態

        Args:
            react_id: ReAct session ID
            iteration: 迭代次數

        Returns:
            ReAct 狀態對象，如果不存在則返回 None
        """
        return self.persistence.get_state(react_id, iteration)

    def get_states_by_react_id(self, react_id: str) -> List[ReactState]:
        """
        獲取指定 react_id 的所有狀態

        Args:
            react_id: ReAct session ID

        Returns:
            狀態列表（按 iteration 排序）
        """
        return self.persistence.get_states_by_react_id(react_id)

    def save_decision_log(self, log: DecisionLog) -> None:
        """
        保存 Decision Log

        Args:
            log: Decision Log 對象
        """
        self.persistence.save_decision_log(log)

    def get_decision_logs_by_react_id(self, react_id: str) -> List[DecisionLog]:
        """
        獲取指定 react_id 的所有 Decision Log

        Args:
            react_id: ReAct session ID

        Returns:
            Decision Log 列表（按 iteration 排序）
        """
        return self.persistence.get_decision_logs_by_react_id(react_id)

    def replay_states(self, react_id: str) -> List[ReactState]:
        """
        回放指定 react_id 的所有狀態

        Args:
            react_id: ReAct session ID

        Returns:
            狀態列表（按 iteration 排序）
        """
        return self.replay.replay(react_id)

    def replay_decision_logs(self, react_id: str) -> List[DecisionLog]:
        """
        回放指定 react_id 的所有 Decision Log

        Args:
            react_id: ReAct session ID

        Returns:
            Decision Log 列表（按 iteration 排序）
        """
        return self.replay.replay_decision_logs(react_id)

    def get_state_history(self, react_id: str) -> dict:
        """
        獲取完整的狀態歷史（包括狀態和決策日誌）

        Args:
            react_id: ReAct session ID

        Returns:
            包含 states 和 decision_logs 的字典
        """
        return self.replay.get_state_history(react_id)
