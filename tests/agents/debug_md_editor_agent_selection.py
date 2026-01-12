# 代碼功能說明: md-editor Agent 選擇問題診斷腳本
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""診斷 md-editor Agent 選擇問題

檢查：
1. md-editor 是否已註冊到 Registry
2. CapabilityMatcher 是否找到了 md-editor
3. DecisionEngine 是否選擇了 md-editor
"""

import asyncio
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from agents.builtin import register_builtin_agents
from agents.services.registry.registry import get_agent_registry


async def check_agent_registration():
    """檢查 Agent 註冊狀態"""
    print("=" * 80)
    print("步驟 1: 檢查 Agent 註冊狀態")
    print("=" * 80)

    # 註冊內建 Agent
    try:
        registered = register_builtin_agents()
        print(f"✅ 內建 Agent 註冊完成: {registered}")
    except Exception as e:
        print(f"❌ Agent 註冊失敗: {e}")
        return False

    # 檢查 Registry
    registry = get_agent_registry()

    # 檢查 md-editor
    md_editor = registry.get_agent_info("md-editor")
    if md_editor:
        print("\n✅ md-editor 已註冊:")
        print(f"   agent_id: {md_editor.agent_id}")
        print(f"   agent_type: {md_editor.agent_type}")
        print(f"   status: {md_editor.status}")
        print(f"   is_system_agent: {md_editor.is_system_agent}")
        print(f"   capabilities: {md_editor.capabilities}")
    else:
        print("\n❌ md-editor 未找到！")
        return False

    # 檢查 document_editing 類型的 Agent
    from agents.services.registry.models import AgentStatus

    editing_agents = registry.list_agents(
        agent_type="document_editing",
        status=AgentStatus.ONLINE,
        include_system_agents=True,
    )
    print(f"\n✅ document_editing 類型的 Agent ({len(editing_agents)} 個):")
    for agent in editing_agents:
        print(f"   - {agent.agent_id} (type: {agent.agent_type}, status: {agent.status})")

    return True


async def check_capability_matcher():
    """檢查 CapabilityMatcher 是否找到了 md-editor"""
    print("\n" + "=" * 80)
    print("步驟 2: 檢查 CapabilityMatcher")
    print("=" * 80)

    from agents.task_analyzer.capability_matcher import CapabilityMatcher
    from agents.task_analyzer.models import Complexity, IntentType, RiskLevel, RouterDecision

    # 創建模擬的 RouterDecision
    router_decision = RouterDecision(
        intent_type=IntentType.EXECUTION,
        complexity=Complexity.LOW,
        needs_agent=True,
        needs_tools=True,
        risk_level=RiskLevel.LOW,
        confidence=0.95,
    )

    # 創建模擬的 context（包含文件編輯任務）
    context = {
        "task": "編輯文件 README.md",
        "query": "編輯文件 README.md",
        "user_id": "test_user",
    }

    # 執行匹配
    matcher = CapabilityMatcher()
    agent_candidates = await matcher.match_agents(router_decision, context)

    print(f"\n✅ CapabilityMatcher 找到 {len(agent_candidates)} 個 Agent 候選:")
    for candidate in agent_candidates:
        print(f"   - {candidate.candidate_id} (score: {candidate.total_score:.2f})")

    # 檢查是否包含 md-editor
    md_editor_candidate = next((c for c in agent_candidates if c.candidate_id == "md-editor"), None)
    if md_editor_candidate:
        print(f"\n✅ md-editor 在候選列表中 (score: {md_editor_candidate.total_score:.2f})")
        return agent_candidates
    else:
        print("\n❌ md-editor 不在候選列表中！")
        print(f"   候選列表: {[c.candidate_id for c in agent_candidates]}")
        return agent_candidates


async def check_decision_engine(agent_candidates):
    """檢查 DecisionEngine 是否選擇了 md-editor"""
    print("\n" + "=" * 80)
    print("步驟 3: 檢查 DecisionEngine")
    print("=" * 80)

    from agents.task_analyzer.decision_engine import DecisionEngine
    from agents.task_analyzer.models import Complexity, IntentType, RiskLevel, RouterDecision

    # 創建模擬的 RouterDecision
    router_decision = RouterDecision(
        intent_type=IntentType.EXECUTION,
        complexity=Complexity.LOW,
        needs_agent=True,
        needs_tools=True,
        risk_level=RiskLevel.LOW,
        confidence=0.95,
    )

    # 創建模擬的 context
    context = {
        "task": "編輯文件 README.md",
        "query": "編輯文件 README.md",
    }

    # 執行決策
    engine = DecisionEngine()
    decision_result = engine.decide(
        router_decision,
        agent_candidates,
        [],
        [],
        context,
    )

    print("\n✅ DecisionEngine 選擇結果:")
    print(f"   chosen_agent: {decision_result.chosen_agent}")
    print(f"   chosen_tools: {decision_result.chosen_tools}")
    print(f"   score: {decision_result.score:.2f}")
    print(f"   reasoning: {decision_result.reasoning}")

    if decision_result.chosen_agent == "md-editor":
        print("\n✅ DecisionEngine 正確選擇了 md-editor！")
    else:
        print("\n❌ DecisionEngine 沒有選擇 md-editor")
        print(f"   實際選擇: {decision_result.chosen_agent}")
        print(f"   候選列表: {[c.candidate_id for c in agent_candidates]}")


async def main():
    """主函數"""
    print("\n" + "=" * 80)
    print("md-editor Agent 選擇問題診斷")
    print("=" * 80 + "\n")

    # 步驟 1: 檢查 Agent 註冊
    if not await check_agent_registration():
        print("\n❌ Agent 註冊檢查失敗，停止診斷")
        return

    # 步驟 2: 檢查 CapabilityMatcher
    agent_candidates = await check_capability_matcher()

    # 步驟 3: 檢查 DecisionEngine
    if agent_candidates:
        await check_decision_engine(agent_candidates)

    print("\n" + "=" * 80)
    print("診斷完成")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
