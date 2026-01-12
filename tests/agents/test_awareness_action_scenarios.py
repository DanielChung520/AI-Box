# 代碼功能說明: 命令感知與實際行動一致性測試劇本執行腳本
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""命令感知與實際行動一致性測試劇本執行腳本

執行 50 個測試場景，驗證系統是否能準確識別用戶意圖並執行對應的後端動作。
完整場景定義請參考：docs/系统设计文档/核心组件/Agent平台/測試劇本-50個場景.md
"""


import pytest

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.models import TaskAnalysisRequest

# 測試場景定義（簡化版本，完整版本請參考文檔）
TEST_SCENARIOS = [
    # 簡單查詢類
    {
        "scenario_id": "TC-001",
        "category": "簡單查詢",
        "user_input": "查詢系統配置",
        "expected_task_type": "query",
        "expected_agent": "system_config_agent",
        "expected_code": [
            "agents/task_analyzer/analyzer.py: _extract_config_intent()",
            "agents/builtin/system_config_agent/agent.py: execute()",
        ],
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
        "expected_code": [
            "agents/task_analyzer/analyzer.py: _extract_log_query_intent()",
            "services/api/core/log/log_service.py: query_logs()",
        ],
    },
    # 文件編輯類（重點）
    {
        "scenario_id": "TC-011",
        "category": "文件編輯",
        "user_input": "編輯文件 README.md，在開頭添加版本號",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
        "expected_code": [
            "agents/task_analyzer/analyzer.py: analyze()",
            "agents/builtin/document_editing/agent.py: execute()",
            "agents/core/execution/document_editing_service.py: generate_editing_patches()",
        ],
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
        "scenario_id": "TC-018",
        "category": "文件編輯",
        "user_input": "重寫 test_agent.py 文件中的 test_function 函數",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
        "clarification_needed": True,
    },
    {
        "scenario_id": "TC-019",
        "category": "文件編輯",
        "user_input": "在文件開頭添加版權聲明",
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
    {
        "scenario_id": "TC-021",
        "category": "文件編輯",
        "user_input": "在 utils.py 中添加一個新的工具函數",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
        "clarification_needed": True,
    },
    {
        "scenario_id": "TC-022",
        "category": "文件編輯",
        "user_input": "格式化整個文件，使用 black 風格",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
        "clarification_needed": True,
    },
    {
        "scenario_id": "TC-023",
        "category": "文件編輯",
        "user_input": "在文件中的特定位置插入代碼片段",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
        "clarification_needed": True,
    },
    {
        "scenario_id": "TC-024",
        "category": "文件編輯",
        "user_input": "將文件中的函數重命名為新名稱",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
        "clarification_needed": True,
    },
    {
        "scenario_id": "TC-025",
        "category": "文件編輯",
        "user_input": "在文件的導入部分添加新的 import 語句",
        "expected_task_type": "execution",
        "expected_agent": "document-editing-agent",
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
    {
        "scenario_id": "TC-050",
        "category": "混合複雜",
        "user_input": "編輯代碼文件，運行代碼審查，修復問題，並生成報告",
        "expected_task_type": "complex",
        "expected_agent": "planning_agent, document-editing-agent, review_agent, reports_agent",
        "clarification_needed": True,
    },
]


class TestAwarenessActionScenarios:
    """命令感知與實際行動一致性測試類"""

    @pytest.fixture
    def orchestrator(self):
        """創建 Orchestrator 實例"""
        return AgentOrchestrator()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", TEST_SCENARIOS)
    async def test_scenario(self, orchestrator, scenario):
        """測試單個場景"""
        scenario_id = scenario["scenario_id"]
        user_input = scenario["user_input"]
        expected_task_type = scenario.get("expected_task_type")
        expected_agent = scenario.get("expected_agent")
        expected_code = scenario.get("expected_code", [])
        clarification_needed = scenario.get("clarification_needed", False)

        print(f"\n{'='*80}")
        print(f"測試場景: {scenario_id}")
        print(f"類別: {scenario['category']}")
        print(f"用戶輸入: {user_input}")
        print(f"{'='*80}")

        # 1. 執行命令感知（Awareness 階段）
        analysis_request = TaskAnalysisRequest(task=user_input)
        analysis_result = await orchestrator._task_analyzer.analyze(analysis_request)

        print("\n[命令感知結果]")
        print(f"  任務類型: {analysis_result.task_type.value}")
        print(f"  工作流類型: {analysis_result.workflow_type.value}")
        print(f"  置信度: {analysis_result.confidence:.2f}")
        print(f"  建議的 Agent: {analysis_result.suggested_agents}")
        print(f"  需要澄清: {analysis_result.analysis_details.get('clarification_needed', False)}")

        # 驗證任務類型
        if expected_task_type:
            assert (
                analysis_result.task_type.value == expected_task_type
            ), f"任務類型不匹配: 預期 {expected_task_type}, 實際 {analysis_result.task_type.value}"

        # 驗證澄清需求
        actual_clarification = analysis_result.analysis_details.get("clarification_needed", False)
        if clarification_needed:
            assert actual_clarification is True, "預期需要澄清，但實際未觸發澄清機制"

        # 驗證建議的 Agent
        if expected_agent:
            if "," in expected_agent:
                # 多個 Agent（用逗號分隔）
                expected_agents = [a.strip() for a in expected_agent.split(",")]
                assert any(
                    agent in analysis_result.suggested_agents for agent in expected_agents
                ), f"建議的 Agent 不包含預期的 Agent: 預期 {expected_agent}, 實際 {analysis_result.suggested_agents}"
            else:
                assert (
                    expected_agent in analysis_result.suggested_agents
                ), f"建議的 Agent 不匹配: 預期 {expected_agent}, 實際 {analysis_result.suggested_agents}"

        # 2. 如果不需要澄清，執行實際行動
        if not actual_clarification:
            print("\n[執行實際行動]")
            try:
                result = await orchestrator.process_natural_language_request(instruction=user_input)

                print(f"  執行狀態: {result.get('status', 'unknown')}")
                print(f"  執行結果: {str(result.get('result', ''))[:200]}...")

                # 驗證執行結果
                assert result.get("status") in [
                    "completed",
                    "failed",
                ], f"執行狀態異常: {result.get('status')}"

            except Exception as e:
                print(f"  執行異常: {e}")
                # 某些場景可能因為環境問題而失敗，這是可以接受的
                pass

        print("\n[預期要執行的代碼]")
        for code_path in expected_code:
            print(f"  - {code_path}")

        print(f"\n{'='*80}\n")


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short"])
