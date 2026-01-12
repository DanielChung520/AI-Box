# 代碼功能說明: State Store 單元測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""State Store 單元測試

測試 State Store 的核心功能：狀態持久化、Decision Log 存儲和狀態回放。
"""


from agents.services.state_store import StateStore
from agents.services.state_store.models import (
    Decision,
    DecisionAction,
    DecisionLog,
    DecisionOutcome,
    ReactState,
    ReactStateType,
)


class TestStateStore:
    """State Store 測試類"""

    def test_state_store_init(self):
        """測試 State Store 初始化"""
        store = StateStore()
        assert store is not None
        assert store.persistence is not None
        assert store.replay is not None

    def test_save_and_get_state(self):
        """測試保存和獲取狀態"""
        store = StateStore()
        react_id = "test-react-001"
        iteration = 0

        state = ReactState(
            react_id=react_id,
            iteration=iteration,
            state=ReactStateType.AWARENESS,
            input_signature={"command_type": "TASK", "risk_level": "safe"},
        )

        # 保存狀態
        store.save_state(state)

        # 獲取狀態
        retrieved_state = store.get_state(react_id, iteration)
        assert retrieved_state is not None
        assert retrieved_state.react_id == react_id
        assert retrieved_state.iteration == iteration
        assert retrieved_state.state == ReactStateType.AWARENESS

    def test_get_states_by_react_id(self):
        """測試獲取指定 react_id 的所有狀態"""
        store = StateStore()
        react_id = "test-react-002"

        # 創建多個狀態
        for i in range(3):
            state = ReactState(
                react_id=react_id,
                iteration=i,
                state=ReactStateType.AWARENESS,
                input_signature={"iteration": i},
            )
            store.save_state(state)

        # 獲取所有狀態
        states = store.get_states_by_react_id(react_id)
        assert len(states) == 3
        assert all(s.react_id == react_id for s in states)
        assert states[0].iteration == 0
        assert states[1].iteration == 1
        assert states[2].iteration == 2

    def test_save_and_get_decision_log(self):
        """測試保存和獲取 Decision Log"""
        store = StateStore()
        react_id = "test-react-003"
        iteration = 0

        decision_log = DecisionLog(
            react_id=react_id,
            iteration=iteration,
            state=ReactStateType.DECISION,
            input_signature={"command_type": "TASK"},
            decision=Decision(
                action=DecisionAction.COMPLETE,
                reason="All tasks completed",
                next_state=ReactStateType.COMPLETE,
            ),
            outcome=DecisionOutcome.SUCCESS,
        )

        # 保存 Decision Log
        store.save_decision_log(decision_log)

        # 獲取 Decision Logs
        logs = store.get_decision_logs_by_react_id(react_id)
        assert len(logs) == 1
        assert logs[0].react_id == react_id
        assert logs[0].decision.action == DecisionAction.COMPLETE
        assert logs[0].outcome == DecisionOutcome.SUCCESS

    def test_replay_states(self):
        """測試狀態回放"""
        store = StateStore()
        react_id = "test-react-004"

        # 創建多個狀態
        for i in range(3):
            state = ReactState(
                react_id=react_id,
                iteration=i,
                state=ReactStateType.AWARENESS,
                input_signature={"iteration": i},
            )
            store.save_state(state)

        # 回放狀態
        replayed_states = store.replay_states(react_id)
        assert len(replayed_states) == 3
        assert all(s.react_id == react_id for s in replayed_states)

    def test_get_state_history(self):
        """測試獲取完整狀態歷史"""
        store = StateStore()
        react_id = "test-react-005"

        # 創建狀態和 Decision Log
        state = ReactState(
            react_id=react_id,
            iteration=0,
            state=ReactStateType.AWARENESS,
            input_signature={"command_type": "TASK"},
        )
        store.save_state(state)

        decision_log = DecisionLog(
            react_id=react_id,
            iteration=0,
            state=ReactStateType.DECISION,
            input_signature={"command_type": "TASK"},
            decision=Decision(
                action=DecisionAction.COMPLETE,
                reason="Test",
                next_state=ReactStateType.COMPLETE,
            ),
            outcome=DecisionOutcome.SUCCESS,
        )
        store.save_decision_log(decision_log)

        # 獲取狀態歷史
        history = store.get_state_history(react_id)
        assert history["react_id"] == react_id
        assert len(history["states"]) == 1
        assert len(history["decision_logs"]) == 1
        assert history["total_iterations"] == 1
