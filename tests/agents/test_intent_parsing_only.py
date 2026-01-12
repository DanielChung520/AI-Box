# 代碼功能說明: 意圖解析測試腳本（僅測試意圖解析和調用識別，不實際執行）
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""意圖解析測試腳本

僅測試意圖解析和 Agent 調用識別，不實際執行任務。
用於驗證系統是否能準確理解用戶意圖並識別需要調用的 Agent。
"""


import pytest

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.models import TaskAnalysisRequest

# 從完整測試場景中選取代表性場景進行測試
TEST_SCENARIOS = [
    # 簡單查詢類
    {
        "scenario_id": "TC-001",
        "category": "簡單查詢",
        "user_input": "查詢系統配置",
        "expected_task_type": "query",
        "expected_agent": "system_config_agent",
    },
    {
        "scenario_id": "TC-002",
        "category": "簡單查詢",
        "user_input": "查看當前系統狀態",
        "expected_task_type": "query",
        "expected_agent": "system_config_agent",
    },
    {
        "scenario_id": "TC-004",
        "category": "簡單查詢",
        "user_input": "查詢最近 1 小時的錯誤日誌",
        "expected_task_type": "log_query",
        "expected_agent": None,
    },
    {
        "scenario_id": "TC-008",
        "category": "簡單查詢",
        "user_input": "查詢知識圖譜中的實體",
        "expected_task_type": "query",
        "expected_agent": "knowledge_ontology_agent",
    },
    {
        "scenario_id": "TC-010",
        "category": "簡單查詢",
        "user_input": "查詢數據庫中的用戶表",
        "expected_task_type": "query",
        "expected_agent": "data_agent",
    },
    # 文件編輯類（重點）
    {
        "scenario_id": "TC-011",
        "category": "文件編輯",
        "user_input": "編輯文件 README.md，在開頭添加版本號",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
    },
    {
        "scenario_id": "TC-012",
        "category": "文件編輯",
        "user_input": "修改 config.json 文件，將 timeout 設置為 60",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
    },
    {
        "scenario_id": "TC-013",
        "category": "文件編輯",
        "user_input": "幫我在文件末尾添加一行註釋",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
        "clarification_needed": True,
    },
    {
        "scenario_id": "TC-014",
        "category": "文件編輯",
        "user_input": "刪除文件中的第 10 行",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
        "clarification_needed": True,
    },
    {
        "scenario_id": "TC-015",
        "category": "文件編輯",
        "user_input": "在 main.py 的第 50 行插入新的函數定義",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
        "clarification_needed": True,
    },
    {
        "scenario_id": "TC-016",
        "category": "文件編輯",
        "user_input": "替換文件中的所有 'old_text' 為 'new_text'",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
        "clarification_needed": True,
    },
    {
        "scenario_id": "TC-017",
        "category": "文件編輯",
        "user_input": "更新 README.md，在安裝說明部分添加新的依賴項",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
        "clarification_needed": True,
    },
    {
        "scenario_id": "TC-020",
        "category": "文件編輯",
        "user_input": "修改配置文件，將 debug 模式設為 false",
        "expected_task_type": "execution",
        "expected_agent": "system_config_agent 或 document-editing-agent",
        "clarification_needed": True,
    },
    # 配置操作類
    {
        "scenario_id": "TC-026",
        "category": "配置操作",
        "user_input": "設置 LLM 提供商為 OpenAI",
        "expected_task_type": "execution",
        "expected_agent": "system_config_agent",
    },
    {
        "scenario_id": "TC-027",
        "category": "配置操作",
        "user_input": "創建新的租戶配置，允許使用 GPT-4",
        "expected_task_type": "execution",
        "expected_agent": "system_config_agent",
        "clarification_needed": True,
    },
    # 複雜執行類
    {
        "scenario_id": "TC-034",
        "category": "複雜執行",
        "user_input": "生成上週的數據分析報告",
        "expected_task_type": "execution",
        "expected_agent": "planning_agent, execution_agent, reports_agent",
        "clarification_needed": True,
    },
    {
        "scenario_id": "TC-036",
        "category": "複雜執行",
        "user_input": "分析上個月的用戶行為，生成報告並發送給管理層",
        "expected_task_type": "complex",
        "expected_agent": "planning_agent, data_agent, reports_agent, execution_agent",
    },
    # 混合複雜任務
    {
        "scenario_id": "TC-045",
        "category": "混合複雜",
        "user_input": "編輯配置文件並重啟服務",
        "expected_task_type": "execution",
        "expected_agent": "planning_agent, document-editing-agent, execution_agent",
        "clarification_needed": True,
    },
    {
        "scenario_id": "TC-047",
        "category": "混合複雜",
        "user_input": "更新代碼文件，運行測試，生成測試報告",
        "expected_task_type": "complex",
        "expected_agent": "planning_agent, document-editing-agent, execution_agent, reports_agent",
        "clarification_needed": True,
    },
]


class TestIntentParsingOnly:
    """意圖解析測試類（僅測試意圖解析，不實際執行）"""

    @pytest.fixture
    def orchestrator(self):
        """創建 Orchestrator 實例"""
        return AgentOrchestrator()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", TEST_SCENARIOS)
    async def test_intent_parsing(self, orchestrator, scenario):
        """測試意圖解析和 Agent 調用識別"""
        scenario_id = scenario["scenario_id"]
        user_input = scenario["user_input"]
        expected_task_type = scenario.get("expected_task_type")
        expected_agent = scenario.get("expected_agent")
        clarification_needed = scenario.get("clarification_needed", False)

        print(f"\n{'='*80}")
        print(f"測試場景: {scenario_id}")
        print(f"類別: {scenario['category']}")
        print(f"用戶輸入: {user_input}")
        print(f"{'='*80}")

        # 執行意圖解析（僅測試 Awareness 階段）
        try:
            analysis_request = TaskAnalysisRequest(task=user_input)
            task_analyzer = orchestrator._get_task_analyzer()
            analysis_result = await task_analyzer.analyze(analysis_request)

            print("\n[意圖解析結果]")
            print(f"  任務類型: {analysis_result.task_type.value}")
            print(f"  工作流類型: {analysis_result.workflow_type.value}")
            print(f"  置信度: {analysis_result.confidence:.2f}")
            print(f"  需要 Agent: {analysis_result.requires_agent}")
            print(f"  建議的 Agent: {analysis_result.suggested_agents}")
            print(f"  建議的工具: {analysis_result.suggested_tools}")

            # 顯示意圖詳情
            if analysis_result.analysis_details:
                print("\n[意圖詳情]")
                intent = analysis_result.get_intent()
                if intent:
                    print(f"  意圖對象: {type(intent).__name__}")
                    if hasattr(intent, "action"):
                        print(f"  操作類型: {intent.action}")
                    if hasattr(intent, "scope"):
                        print(f"  配置範圍: {intent.scope}")
                    if hasattr(intent, "log_type"):
                        print(f"  日誌類型: {intent.log_type}")

                clarification_needed_actual = analysis_result.analysis_details.get(
                    "clarification_needed", False
                )
                if clarification_needed_actual:
                    clarification_question = analysis_result.analysis_details.get(
                        "clarification_question"
                    )
                    print("  需要澄清: 是")
                    if clarification_question:
                        print(f"  澄清問題: {clarification_question}")
                else:
                    print("  需要澄清: 否")

            # 顯示決策結果（如果有）
            if analysis_result.decision_result:
                print("\n[決策結果]")
                decision = analysis_result.decision_result
                if hasattr(decision, "decision_type"):
                    print(f"  決策類型: {decision.decision_type}")
                if hasattr(decision, "reasoning"):
                    print(f"  決策理由: {decision.reasoning}")
                # 打印所有可用屬性
                print(f"  決策對象: {type(decision).__name__}")
                if hasattr(decision, "__dict__"):
                    print(f"  決策詳情: {decision.__dict__}")

            # 驗證任務類型
            task_type_match = False
            if expected_task_type:
                task_type_match = analysis_result.task_type.value == expected_task_type
                status_icon = "✅" if task_type_match else "❌"
                print("\n[驗證結果]")
                print(
                    f"  {status_icon} 任務類型: 預期 {expected_task_type}, 實際 {analysis_result.task_type.value}"
                )

            # 驗證 Agent 調用
            agent_match = False
            if expected_agent:
                if "," in expected_agent:
                    # 多個 Agent（用逗號分隔）
                    expected_agents = [a.strip() for a in expected_agent.split(",")]
                    agent_match = any(
                        agent in analysis_result.suggested_agents for agent in expected_agents
                    )
                    status_icon = "✅" if agent_match else "❌"
                    print(
                        f"  {status_icon} Agent 調用: 預期 {expected_agent}, 實際 {analysis_result.suggested_agents}"
                    )
                else:
                    agent_match = expected_agent in analysis_result.suggested_agents
                    status_icon = "✅" if agent_match else "❌"
                    print(
                        f"  {status_icon} Agent 調用: 預期 {expected_agent}, 實際 {analysis_result.suggested_agents}"
                    )

            # 驗證澄清需求
            clarification_match = False
            actual_clarification = analysis_result.analysis_details.get(
                "clarification_needed", False
            )
            if clarification_needed:
                clarification_match = actual_clarification is True
                status_icon = "✅" if clarification_match else "❌"
                print(f"  {status_icon} 澄清機制: 預期需要澄清, 實際 {'需要' if actual_clarification else '不需要'}")

            # 總結
            all_passed = (
                task_type_match
                and agent_match
                and (clarification_match if clarification_needed else True)
            )
            print("\n[測試總結]")
            if all_passed:
                print("  ✅ 所有驗證點通過")
            else:
                print("  ❌ 部分驗證點未通過")
                if not task_type_match:
                    print("    - 任務類型不匹配")
                if not agent_match:
                    print("    - Agent 調用不匹配")
                if clarification_needed and not clarification_match:
                    print("    - 澄清機制未正確觸發")

        except Exception as e:
            print("\n[錯誤]")
            print(f"  ❌ 測試執行失敗: {e}")
            import traceback

            traceback.print_exc()
            raise

        print(f"\n{'='*80}\n")


def generate_test_summary():
    """生成測試摘要報告"""
    print(f"\n{'='*80}")
    print("測試摘要")
    print(f"{'='*80}")
    print(f"總場景數: {len(TEST_SCENARIOS)}")
    print("測試類別:")
    categories = {}
    for scenario in TEST_SCENARIOS:
        cat = scenario["category"]
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in categories.items():
        print(f"  - {cat}: {count} 個場景")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    generate_test_summary()
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short", "-s"])
