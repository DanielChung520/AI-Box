# 代碼功能說明: xls-editor 場景測試腳本
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""xls-editor 場景測試腳本

測試 xls-editor Agent 的語義路由能力（10 個場景：XLS-001 ~ XLS-010）
注意：所有場景都必須包含明確的 Excel 關鍵字（.xlsx, .xls, Excel 等）
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

# 添加項目根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.models import TaskAnalysisRequest

# Agent ID 定義
XLS_EDITOR_AGENT_ID = "xls-editor"

# xls-editor 測試場景定義（10 個場景，所有場景都包含明確的 Excel 關鍵字）
XLS_EDITOR_SCENARIOS = [
    {
        "scenario_id": "XLS-001",
        "category": "xls-editor",
        "user_input": "編輯文件 data.xlsx",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "excel_keyword": ".xlsx",
    },
    {
        "scenario_id": "XLS-002",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中 A1 單元格輸入數據",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "excel_keyword": ".xlsx",
    },
    {
        "scenario_id": "XLS-003",
        "category": "xls-editor",
        "user_input": "將 data.xlsx 中 A1 單元格設置為粗體和紅色",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
        "excel_keyword": ".xlsx",
    },
    {
        "scenario_id": "XLS-004",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中 B 列前插入一列",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
        "excel_keyword": ".xlsx",
    },
    {
        "scenario_id": "XLS-005",
        "category": "xls-editor",
        "user_input": "更新 data.xlsx 中 B10 單元格的公式為 =SUM(A1:A9)",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
        "excel_keyword": ".xlsx",
    },
    {
        "scenario_id": "XLS-006",
        "category": "xls-editor",
        "user_input": "刪除 data.xlsx 中 Sheet1 的第 5 行",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "excel_keyword": ".xlsx",
    },
    {
        "scenario_id": "XLS-007",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中添加一行數據",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
        "excel_keyword": ".xlsx",
    },
    {
        "scenario_id": "XLS-008",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中填充 A1 到 A10 的序號",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
        "excel_keyword": ".xlsx",
    },
    {
        "scenario_id": "XLS-009",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 中創建一個新的工作表 '統計'",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "excel_keyword": ".xlsx",
    },
    {
        "scenario_id": "XLS-010",
        "category": "xls-editor",
        "user_input": "將 data.xlsx 中的 Sheet1 重命名為 '數據'",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "excel_keyword": ".xlsx",
    },
]

# 測試結果收集器
_test_results: List[Dict[str, Any]] = []


class TestXLSEditorRouting:
    """xls-editor 場景測試類"""

    @pytest.fixture
    def orchestrator(self):
        """創建 Orchestrator 實例"""
        return AgentOrchestrator()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", XLS_EDITOR_SCENARIOS)
    async def test_xls_editor_routing(self, orchestrator, scenario):
        """測試 xls-editor Agent 語義路由"""
        global _test_results

        scenario_id = scenario["scenario_id"]
        user_input = scenario["user_input"]
        expected_task_type = scenario.get("expected_task_type")
        expected_agent = scenario.get("expected_agent")
        complexity = scenario.get("complexity", "未知")
        excel_keyword = scenario.get("excel_keyword", "")

        print(f"\n{'='*80}")
        print(f"測試場景: {scenario_id}")
        print(f"類別: {scenario['category']}")
        print(f"複雜度: {complexity}")
        print(f"Excel 關鍵字: {excel_keyword}")
        print(f"用戶輸入: {user_input}")
        print(f"預期 Agent: {expected_agent}")
        print(f"{'='*80}")

        # 驗證場景包含 Excel 關鍵字
        has_excel_keyword = any(
            keyword in user_input.lower()
            for keyword in [".xlsx", ".xls", "excel", "spreadsheet", "工作表", "單元格"]
        )
        if not has_excel_keyword:
            print(f"  ⚠️  警告: 場景 {scenario_id} 未包含明確的 Excel 關鍵字")

        # 執行意圖解析
        try:
            # 確保 builtin agents 已註冊到 Registry
            try:
                from agents.builtin import register_builtin_agents

                registered_agents = register_builtin_agents()
                if registered_agents:
                    print(
                        f"\n[Agent 註冊] 已註冊 {len(registered_agents)} 個內建 Agent: {list(registered_agents.keys())}"
                    )
            except Exception as e:
                print(f"\n[Agent 註冊警告] 註冊內建 Agent 時發生錯誤: {e}")

            analysis_request = TaskAnalysisRequest(task=user_input)
            task_analyzer = orchestrator._get_task_analyzer()
            analysis_result = await task_analyzer.analyze(analysis_request)

            print("\n[意圖解析結果]")
            print(f"  任務類型: {analysis_result.task_type.value}")
            intent_type = None
            if analysis_result.router_decision:
                intent_type = analysis_result.router_decision.intent_type
                print(f"  意圖類型: {intent_type}")
                print(f"  複雜度: {analysis_result.router_decision.complexity}")
                print(f"  需要 Agent: {analysis_result.router_decision.needs_agent}")
            print(f"  工作流類型: {analysis_result.workflow_type.value}")
            print(f"  置信度: {analysis_result.confidence:.2f}")
            print(f"  建議的 Agent: {analysis_result.suggested_agents}")

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
                agent_match = expected_agent in analysis_result.suggested_agents
                status_icon = "✅" if agent_match else "❌"
                print(
                    f"  {status_icon} Agent 調用: 預期 {expected_agent}, 實際 {analysis_result.suggested_agents}"
                )

            # 檢查是否調用了 document-editing-agent（不應該調用）
            called_document_editing_agent = (
                "document-editing-agent" in analysis_result.suggested_agents
            )
            if called_document_editing_agent:
                print("  ⚠️  警告: 調用了已停用的 document-editing-agent")

            # 檢查是否錯誤調用了 md-editor（不應該調用）
            called_md_editor = "md-editor" in analysis_result.suggested_agents
            if called_md_editor and expected_agent == XLS_EDITOR_AGENT_ID:
                print("  ⚠️  警告: 錯誤調用了 md-editor（應該調用 xls-editor）")

            # 總結
            all_passed = (
                task_type_match
                and agent_match
                and not called_document_editing_agent
                and not (called_md_editor and expected_agent == XLS_EDITOR_AGENT_ID)
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
                if called_document_editing_agent:
                    print("    - 調用了已停用的 document-editing-agent")
                if called_md_editor and expected_agent == XLS_EDITOR_AGENT_ID:
                    print("    - 錯誤調用了 md-editor")

            # 構建結果
            result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "excel_keyword": excel_keyword,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": analysis_result.task_type.value,
                "actual_intent_type": (
                    analysis_result.router_decision.intent_type
                    if analysis_result.router_decision
                    else None
                ),
                "actual_agents": analysis_result.suggested_agents,
                "task_type_match": task_type_match,
                "agent_match": agent_match,
                "called_document_editing_agent": called_document_editing_agent,
                "called_md_editor": called_md_editor
                if expected_agent == XLS_EDITOR_AGENT_ID
                else False,
                "all_passed": all_passed,
                "confidence": analysis_result.confidence,
                "router_confidence": (
                    analysis_result.router_decision.confidence
                    if analysis_result.router_decision
                    else None
                ),
                "status": "✅ 通過" if all_passed else "❌ 失敗",
                "error": None,
            }

            _test_results.append(result)
            return result

        except Exception as e:
            print("\n[錯誤]")
            print(f"  ❌ 測試執行失敗: {e}")
            import traceback

            traceback.print_exc()

            error_result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "excel_keyword": excel_keyword,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": None,
                "actual_intent_type": None,
                "actual_agents": [],
                "task_type_match": False,
                "agent_match": False,
                "called_document_editing_agent": False,
                "called_md_editor": False,
                "all_passed": False,
                "confidence": 0.0,
                "router_confidence": None,
                "status": "❌ 錯誤",
                "error": str(e),
            }

            _test_results.append(error_result)
            raise


def save_test_results() -> Path:
    """保存測試結果到 JSON 文件"""
    global _test_results

    output_dir = Path(__file__).parent / "test_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"xls_editor_test_results_{timestamp}.json"

    total = len(_test_results)
    passed = sum(1 for r in _test_results if r.get("all_passed", False))
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    report = {
        "execution_date": datetime.now().strftime("%Y-%m-%d"),
        "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "executor": "Daniel Chung",
        "test_environment": "本地開發環境",
        "system_version": "v3.2",
        "summary": {
            "total_scenarios": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{pass_rate:.2f}%",
        },
        "results": _test_results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return output_file


if __name__ == "__main__":
    # 清空結果列表
    _test_results.clear()

    # 運行測試
    exit_code = pytest.main([__file__, "-v", "--tb=short", "-s"])

    # 保存結果
    if _test_results:
        output_file = save_test_results()
        print(f"\n測試結果已保存至: {output_file}")

        # 打印摘要
        total = len(_test_results)
        passed = sum(1 for r in _test_results if r.get("all_passed", False))
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"\n{'='*80}")
        print("測試摘要")
        print(f"{'='*80}")
        print(f"總場景數: {total}")
        print(f"通過: {passed}")
        print(f"失敗: {failed}")
        print(f"通過率: {pass_rate:.2f}%")
        print(f"{'='*80}\n")

    sys.exit(exit_code)
