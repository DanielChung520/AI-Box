# 代碼功能說明: ReAct FSM 單元測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""ReAct FSM 單元測試

測試 ReAct FSM 的核心功能：狀態轉移、狀態機執行和狀態回放。
"""

import pytest

from agents.services.react_fsm import ReactStateMachine
from agents.services.state_store.models import ReactStateType


class TestReactFSM:
    """ReAct FSM 測試類"""

    def test_react_fsm_init(self):
        """測試 ReAct FSM 初始化"""
        fsm = ReactStateMachine()
        assert fsm is not None
        assert fsm.state_store is not None

    @pytest.mark.asyncio
    async def test_execute_basic_flow(self):
        """測試基本執行流程"""
        fsm = ReactStateMachine()

        result = await fsm.execute("測試命令")

        assert result is not None
        assert result.react_id is not None
        assert result.total_iterations > 0
        assert len(result.states) > 0

    @pytest.mark.asyncio
    async def test_state_transitions(self):
        """測試狀態轉移"""
        from agents.services.react_fsm.transitions import StateTransitions
        from agents.services.state_store.models import Decision, DecisionAction, ReactState

        # 創建一個帶有決策的狀態
        state = ReactState(
            react_id="test-react-001",
            iteration=0,
            state=ReactStateType.DECISION,
            decision=Decision(
                action=DecisionAction.COMPLETE,
                reason="Test",
                next_state=ReactStateType.COMPLETE,
            ),
        )

        # 測試狀態轉移
        next_state = StateTransitions.get_next_state(state)
        assert next_state == ReactStateType.COMPLETE

        # 測試是否應該繼續
        should_continue = StateTransitions.should_continue(state)
        assert should_continue is False

    @pytest.mark.asyncio
    async def test_replay(self):
        """測試狀態回放"""
        fsm = ReactStateMachine()

        # 先執行一次
        result = await fsm.execute("測試命令")
        react_id = result.react_id

        # 回放
        replayed_result = await fsm.replay(react_id)
        assert replayed_result is not None
        assert replayed_result.react_id == react_id
        assert len(replayed_result.states) > 0
