# 代碼功能說明: 文件編輯意圖識別測試腳本
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""文件編輯意圖識別測試腳本

專門測試文件編輯相關的意圖識別，包括：
1. 明確的編輯指令
2. 產生/創建文件意圖
3. 隱含的編輯意圖
4. 一般聊天（不應調用編輯Agent）

驗證系統是否能正確識別並調用 document-editing-agent。
完整場景定義請參考：docs/系统设计文档/核心组件/Agent平台/文件編輯意圖識別測試劇本.md
"""


import pytest

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.models import TaskAnalysisRequest

# 文件編輯 Agent ID
DOCUMENT_EDITING_AGENT_ID = "document-editing-agent"

# 測試場景定義
TEST_SCENARIOS = [
    # 類別 1：明確文件編輯指令
    {
        "scenario_id": "FE-001",
        "category": "明確編輯指令",
        "user_input": "編輯文件 README.md",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
    },
    {
        "scenario_id": "FE-002",
        "category": "明確編輯指令",
        "user_input": "修改 config.json 文件",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
    },
    {
        "scenario_id": "FE-003",
        "category": "明確編輯指令",
        "user_input": "幫我編輯 main.py",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-004",
        "category": "明確編輯指令",
        "user_input": "更新 README.md 文件",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-005",
        "category": "明確編輯指令",
        "user_input": "刪除文件中的第 10 行",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-006",
        "category": "明確編輯指令",
        "user_input": "在文件開頭添加版本號",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-007",
        "category": "明確編輯指令",
        "user_input": "替換文件中的 'old' 為 'new'",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-008",
        "category": "明確編輯指令",
        "user_input": "重寫 test.py 中的函數",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-009",
        "category": "明確編輯指令",
        "user_input": "在 utils.py 中添加新函數",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-010",
        "category": "明確編輯指令",
        "user_input": "格式化整個文件",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    # 類別 2：產生/創建文件意圖
    {
        "scenario_id": "FE-011",
        "category": "產生/創建文件",
        "user_input": "幫我產生一個 README.md 文件",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-012",
        "category": "產生/創建文件",
        "user_input": "創建一個新的配置文件 config.json",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-013",
        "category": "產生/創建文件",
        "user_input": "幫我寫一個 Python 腳本",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-014",
        "category": "產生/創建文件",
        "user_input": "生成一份報告文件",
        "expected_task_type": "execution",
        "expected_agent": f"{DOCUMENT_EDITING_AGENT_ID} 或 reports_agent",
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-015",
        "category": "產生/創建文件",
        "user_input": "幫我建立一個新的文件",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-016",
        "category": "產生/創建文件",
        "user_input": "製作一個 Markdown 文檔",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-017",
        "category": "產生/創建文件",
        "user_input": "幫我產生一份測試報告",
        "expected_task_type": "execution",
        "expected_agent": f"{DOCUMENT_EDITING_AGENT_ID} 或 reports_agent",
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-018",
        "category": "產生/創建文件",
        "user_input": "建立一個新的程式檔案",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-019",
        "category": "產生/創建文件",
        "user_input": "幫我寫一份文件",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-020",
        "category": "產生/創建文件",
        "user_input": "生成一個新的檔案",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    # 類別 3：隱含編輯意圖
    {
        "scenario_id": "FE-021",
        "category": "隱含編輯意圖",
        "user_input": "幫我在 README.md 中加入安裝說明",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
    },
    {
        "scenario_id": "FE-022",
        "category": "隱含編輯意圖",
        "user_input": "在文件裡添加註釋",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-023",
        "category": "隱含編輯意圖",
        "user_input": "把這個函數改成新的實現",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-024",
        "category": "隱含編輯意圖",
        "user_input": "幫我整理一下這個文件",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    {
        "scenario_id": "FE-025",
        "category": "隱含編輯意圖",
        "user_input": "優化這個代碼文件",
        "expected_task_type": "execution",
        "expected_agent": DOCUMENT_EDITING_AGENT_ID,
        "should_call_editing_agent": True,
        "clarification_needed": True,
    },
    # 類別 4：一般聊天（不應調用編輯Agent）
    {
        "scenario_id": "FE-026",
        "category": "一般聊天",
        "user_input": "你好，今天天氣怎麼樣？",
        "expected_task_type": "query",
        "expected_agent": None,
        "should_call_editing_agent": False,
    },
    {
        "scenario_id": "FE-027",
        "category": "一般聊天",
        "user_input": "告訴我系統的當前狀態",
        "expected_task_type": "query",
        "expected_agent": "system_config_agent 或 status_agent",
        "should_call_editing_agent": False,
    },
    {
        "scenario_id": "FE-028",
        "category": "一般聊天",
        "user_input": "查詢一下配置信息",
        "expected_task_type": "query",
        "expected_agent": "system_config_agent",
        "should_call_editing_agent": False,
    },
    {
        "scenario_id": "FE-029",
        "category": "一般聊天",
        "user_input": "幫我解釋一下這個功能",
        "expected_task_type": "query",
        "expected_agent": None,
        "should_call_editing_agent": False,
    },
    {
        "scenario_id": "FE-030",
        "category": "一般聊天",
        "user_input": "列出所有可用的 Agent",
        "expected_task_type": "query",
        "expected_agent": "registry_manager",
        "should_call_editing_agent": False,
    },
]


class TestFileEditingIntent:
    """文件編輯意圖識別測試類"""

    @pytest.fixture
    def orchestrator(self):
        """創建 Orchestrator 實例"""
        return AgentOrchestrator()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", TEST_SCENARIOS)
    async def test_file_editing_intent(self, orchestrator, scenario):
        """測試文件編輯意圖識別"""
        scenario_id = scenario["scenario_id"]
        user_input = scenario["user_input"]
        expected_task_type = scenario.get("expected_task_type")
        expected_agent = scenario.get("expected_agent")
        should_call_editing_agent = scenario.get("should_call_editing_agent", False)
        clarification_needed = scenario.get("clarification_needed", False)

        print(f"\n{'='*80}")
        print(f"測試場景: {scenario_id}")
        print(f"類別: {scenario['category']}")
        print(f"用戶輸入: {user_input}")
        print(f"預期調用編輯Agent: {should_call_editing_agent}")
        print(f"{'='*80}")

        # 執行意圖解析
        try:
            # 確保 builtin agents 已註冊到 Registry（特別是多個 document-editing-agent）
            try:
                from agents.builtin import register_builtin_agents
                from agents.services.registry.registry import get_agent_registry
                from services.api.services.system_agent_registry_store_service import (
                    get_system_agent_registry_store_service,
                )

                # 註冊 builtin agents（包括 System Agent Registry）
                registered_agents = register_builtin_agents()
                print(
                    f"\n[Agent 註冊] 已註冊 {len(registered_agents)} 個內建 Agent: {list(registered_agents.keys())}"
                )

                # 檢查 document-editing-agent 是否在 Agent Registry 中
                registry = get_agent_registry()
                agent_info = registry.get_agent_info(DOCUMENT_EDITING_AGENT_ID)
                if agent_info:
                    print("\n[Agent Registry 檢查] ✅ document-editing-agent 在 Agent Registry 中")
                    print(f"  - Agent ID: {agent_info.agent_id}")
                    print(f"  - Agent 類型: {agent_info.agent_type}")
                    print(f"  - 狀態: {agent_info.status.value}")
                    print(f"  - 是否 System Agent: {agent_info.is_system_agent}")
                    print(f"  - 能力: {agent_info.capabilities}")
                else:
                    print("\n[Agent Registry 檢查] ❌ document-editing-agent 不在 Agent Registry 中")

                # 檢查 document-editing-agent 是否在 System Agent Registry 中
                system_agent_store = get_system_agent_registry_store_service()
                system_agent = system_agent_store.get_system_agent(DOCUMENT_EDITING_AGENT_ID)
                if system_agent:
                    print(
                        "\n[System Agent Registry 檢查] ✅ document-editing-agent 在 System Agent Registry 中"
                    )
                    print(f"  - Agent ID: {system_agent.agent_id}")
                    print(f"  - Agent 類型: {system_agent.agent_type}")
                    print(f"  - 狀態: {system_agent.status}")
                    print(f"  - 是否啟用: {system_agent.is_active}")
                    print(f"  - 能力: {system_agent.capabilities}")
                else:
                    print(
                        "\n[System Agent Registry 檢查] ❌ document-editing-agent 不在 System Agent Registry 中"
                    )

                # 列出所有可用的 Agent（包括 System Agents，用於診斷）
                all_agents = registry.list_agents(include_system_agents=True)
                print(f"\n[Agent 列表] 總共 {len(all_agents)} 個 Agent（包括 System Agents）")
                for agent in all_agents:
                    if "document" in agent.agent_id.lower() or "editing" in agent.agent_id.lower():
                        print(
                            f"  - {agent.agent_id} (類型: {agent.agent_type}, System: {agent.is_system_agent}, 狀態: {agent.status.value})"
                        )

                # 列出所有 System Agents（用於診斷）
                system_agents = system_agent_store.list_system_agents(is_active=True)
                print(f"\n[System Agent 列表] 總共 {len(system_agents)} 個 System Agent（啟用）")
                for agent in system_agents:
                    print(f"  - {agent.agent_id} (類型: {agent.agent_type}, 狀態: {agent.status})")

            except Exception as e:
                print(f"\n[Agent 註冊警告] 註冊內建 Agent 時發生錯誤: {e}")
                import traceback

                traceback.print_exc()

            analysis_request = TaskAnalysisRequest(task=user_input)
            task_analyzer = orchestrator._get_task_analyzer()
            analysis_result = await task_analyzer.analyze(analysis_request)

            print("\n[意圖解析結果]")
            print(f"  任務類型: {analysis_result.task_type.value}")
            print(f"  工作流類型: {analysis_result.workflow_type.value}")
            print(f"  置信度: {analysis_result.confidence:.2f}")
            print(f"  需要 Agent: {analysis_result.requires_agent}")
            print(f"  建議的 Agent: {analysis_result.suggested_agents}")

            # 檢查是否調用了 document-editing-agent
            actual_calls_editing_agent = (
                DOCUMENT_EDITING_AGENT_ID in analysis_result.suggested_agents
            )

            print("\n[Agent 調用檢查]")
            print(f"  是否調用編輯Agent: {actual_calls_editing_agent}")
            print(f"  預期調用編輯Agent: {should_call_editing_agent}")

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
                if "," in expected_agent or "或" in expected_agent:
                    # 多個 Agent（用逗號或"或"分隔）
                    expected_agents = [
                        a.strip() for a in expected_agent.replace("或", ",").split(",")
                    ]
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

            # 驗證是否正確調用/不調用編輯Agent
            editing_agent_match = actual_calls_editing_agent == should_call_editing_agent
            status_icon = "✅" if editing_agent_match else "❌"
            print(
                f"  {status_icon} 編輯Agent調用: 預期 {'調用' if should_call_editing_agent else '不調用'}, 實際 {'調用' if actual_calls_editing_agent else '不調用'}"
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
                and editing_agent_match
                and (clarification_match if clarification_needed else True)
            )
            print("\n[測試總結]")
            if all_passed:
                print("  ✅ 所有驗證點通過")
            else:
                print("  ❌ 部分驗證點未通過")
                if not task_type_match:
                    print("    - 任務類型不匹配")
                if not editing_agent_match:
                    print("    - 編輯Agent調用不匹配（這是關鍵驗證點）")
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
    print("文件編輯意圖識別測試摘要")
    print(f"{'='*80}")
    print(f"總場景數: {len(TEST_SCENARIOS)}")
    print("測試類別:")
    categories = {}
    for scenario in TEST_SCENARIOS:
        cat = scenario["category"]
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in categories.items():
        print(f"  - {cat}: {count} 個場景")

    should_call_count = sum(1 for s in TEST_SCENARIOS if s.get("should_call_editing_agent", False))
    should_not_call_count = len(TEST_SCENARIOS) - should_call_count
    print(f"\n預期調用編輯Agent: {should_call_count} 個場景")
    print(f"預期不調用編輯Agent: {should_not_call_count} 個場景")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    generate_test_summary()
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short", "-s"])
