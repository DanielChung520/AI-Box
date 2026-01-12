# 代碼功能說明: Message Bus 單元測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Message Bus 單元測試

測試 Message Bus 的核心功能：消息發布、訂閱和 fan-in。
"""

import pytest

from agents.services.message_bus import MessageBus
from agents.services.message_bus.models import MessageType, TaskDispatch, TaskResult


class TestMessageBus:
    """Message Bus 測試類"""

    def test_message_bus_init(self):
        """測試 Message Bus 初始化"""
        bus = MessageBus()
        assert bus is not None

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self):
        """測試消息發布和訂閱"""
        bus = MessageBus()
        received_messages = []

        async def callback(message):
            received_messages.append(message)

        bus.subscribe(MessageType.TASK_DISPATCH, callback)

        dispatch = TaskDispatch(
            react_id="test-react-001",
            task_id="task-001",
            delegate_to="execution_agent",
            objective="測試任務",
        )

        await bus.publish(dispatch)

        assert len(received_messages) == 1
        assert received_messages[0].task_id == "task-001"

    @pytest.mark.asyncio
    async def test_wait_for_results(self):
        """測試等待任務結果（fan-in）"""
        bus = MessageBus()

        # 發布多個任務結果
        result1 = TaskResult(
            react_id="test-react-002",
            task_id="task-001",
            agent_id="agent-1",
            status="success",
        )
        result2 = TaskResult(
            react_id="test-react-002",
            task_id="task-002",
            agent_id="agent-2",
            status="success",
        )

        await bus.publish_task_result(result1)
        await bus.publish_task_result(result2)

        # 等待結果
        results = await bus.wait_for_results("test-react-002", ["task-001", "task-002"], timeout=1)

        assert len(results) == 2
        assert results[0].task_id == "task-001"
        assert results[1].task_id == "task-002"

    def test_get_task_result(self):
        """測試獲取任務結果"""
        bus = MessageBus()

        result = TaskResult(
            react_id="test-react-003",
            task_id="task-001",
            agent_id="agent-1",
            status="success",
        )

        # 手動設置結果（用於測試）
        bus._task_results["task-001"] = result

        retrieved = bus.get_task_result("task-001")
        assert retrieved is not None
        assert retrieved.task_id == "task-001"
        assert retrieved.status == "success"
