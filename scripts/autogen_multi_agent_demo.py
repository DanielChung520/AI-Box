# 代碼功能說明: AutoGen 多 Agent 協作示例
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""演示 AutoGen 多 Agent 協作的基本用法。"""

import sys
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def demo_agent_roles():
    """演示 Agent 角色定義。"""
    print("=" * 60)
    print("AutoGen Agent 角色定義演示")
    print("=" * 60)

    from agents.autogen.agent_roles import get_default_agent_roles

    roles = get_default_agent_roles()

    for role_name, role in roles.items():
        print(f"\n{role_name.upper()}:")
        print(f"  名稱: {role.name}")
        print(f"  描述: {role.description}")
        print(f"  能力: {', '.join(role.capabilities)}")
        print(f"  最大自動回復: {role.max_consecutive_auto_reply}")


def demo_conversation_manager():
    """演示會話管理。"""
    print("\n" + "=" * 60)
    print("會話管理演示")
    print("=" * 60)

    from agents.autogen.conversation import ConversationManager

    manager = ConversationManager(session_id="demo-session-001")

    # 記錄一些消息
    manager.record_message(
        agent_name="planner",
        role="assistant",
        content="我已經分析了任務，制定了執行計劃。",
    )
    manager.record_message(
        agent_name="executor",
        role="assistant",
        content="正在執行步驟 1：準備數據。",
    )
    manager.record_message(
        agent_name="evaluator",
        role="assistant",
        content="步驟 1 執行成功，結果符合預期。",
    )

    # 獲取歷史
    history = manager.get_conversation_history()
    print(f"\n會話歷史記錄數: {len(history)}")
    for msg in history:
        print(f"  [{msg['agent_name']}] {msg['content'][:50]}...")

    # 導出摘要
    summary = manager.export_summary()
    print("\n會話摘要:")
    print(f"  消息數: {summary['message_count']}")
    print(f"  參與 Agent: {', '.join(summary['agents'])}")


def demo_tool_adapter():
    """演示工具適配器。"""
    print("\n" + "=" * 60)
    print("工具適配器演示")
    print("=" * 60)

    from agents.autogen.tool_adapter import AutoGenToolAdapter

    # 創建工具適配器
    adapter = AutoGenToolAdapter()

    # 獲取工具描述
    descriptions = adapter.get_tool_descriptions()
    print(f"\n可用工具數: {len(descriptions)}")
    for desc in descriptions[:5]:  # 只顯示前 5 個
        print(f"  - {desc['name']}: {desc['description'][:50]}...")


def demo_coordinator():
    """演示協調器。"""
    print("\n" + "=" * 60)
    print("Agent 協調器演示")
    print("=" * 60)

    from agents.autogen.coordinator import AgentCoordinator, MessageType

    coordinator = AgentCoordinator()

    # 註冊一些虛擬 Agent
    coordinator.register_agent("planner", {"type": "planning"})
    coordinator.register_agent("executor", {"type": "execution"})
    coordinator.register_agent("evaluator", {"type": "evaluation"})

    # 發送消息
    coordinator.send_message(
        message_type=MessageType.TASK_REQUEST,
        from_agent="planner",
        to_agent="executor",
        content="請執行步驟 1",
    )
    coordinator.send_message(
        message_type=MessageType.EXECUTION_RESULT,
        from_agent="executor",
        to_agent="evaluator",
        content="步驟 1 執行完成",
    )

    # 分配任務
    coordinator.assign_task("task-001", "executor")

    # 獲取摘要
    summary = coordinator.get_coordination_summary()
    print("\n協調摘要:")
    print(f"  註冊 Agent: {', '.join(summary['registered_agents'])}")
    print(f"  消息數: {summary['message_count']}")
    print(f"  任務分配數: {summary['task_assignments']}")


def main():
    """主函數。"""
    try:
        demo_agent_roles()
        demo_conversation_manager()
        demo_tool_adapter()
        demo_coordinator()
        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)
        return 0
    except Exception as exc:
        print(f"\n錯誤: {exc}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
