# 代碼功能說明: md-editor 場景測試執行腳本
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""md-editor 場景測試執行腳本

只測試 md-editor 場景（20 個場景），用於調試 Agent 調用問題
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加項目根目錄到 Python 路徑
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.models import TaskAnalysisRequest

# 導入測試場景
from tests.agents.test_file_editing_agent_routing import TEST_SCENARIOS

# 只選擇 md-editor 場景
MD_EDITOR_SCENARIOS = [s for s in TEST_SCENARIOS if s["category"] == "md-editor"]

MD_EDITOR_AGENT_ID = "md-editor"


async def run_single_test(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """執行單個測試場景"""
    scenario_id = scenario["scenario_id"]
    user_input = scenario["user_input"]
    expected_task_type = scenario.get("expected_task_type")
    expected_agent = scenario.get("expected_agent")

    print(f"\n[測試場景 {scenario_id}] {user_input}")
    print(f"  預期任務類型: {expected_task_type}")
    print(f"  預期 Agent: {expected_agent}")

    try:
        # 確保 builtin agents 已註冊
        try:
            from agents.builtin import register_builtin_agents

            register_builtin_agents()
        except Exception as e:
            print(f"  [警告] Agent 註冊失敗: {e}")

        orchestrator = AgentOrchestrator()
        analysis_request = TaskAnalysisRequest(
            task=user_input,
            context={"user_id": "test_user", "task": user_input, "query": user_input},
        )
        task_analyzer = orchestrator.task_analyzer
        analysis_result = await task_analyzer.analyze(analysis_request)

        # 提取結果
        actual_task_type = analysis_result.task_type.value if analysis_result.task_type else None
        actual_intent_type = (
            analysis_result.router_decision.intent_type.value
            if analysis_result.router_decision
            else None
        )
        actual_agents = (
            [agent.agent_id for agent in analysis_result.selected_agents]
            if analysis_result.selected_agents
            else []
        )

        # 驗證結果
        task_type_match = actual_task_type == expected_task_type
        agent_match = expected_agent in actual_agents if actual_agents else False
        all_passed = task_type_match and agent_match

        print(f"  實際任務類型: {actual_task_type} {'✅' if task_type_match else '❌'}")
        print(f"  實際意圖類型: {actual_intent_type}")
        print(f"  實際 Agent: {actual_agents} {'✅' if agent_match else '❌'}")
        print(f"  通過: {'✅' if all_passed else '❌'}")

        result = {
            "scenario_id": scenario_id,
            "category": scenario["category"],
            "complexity": scenario.get("complexity", "未知"),
            "user_input": user_input,
            "expected_task_type": expected_task_type,
            "expected_agent": expected_agent,
            "actual_task_type": actual_task_type,
            "actual_intent_type": actual_intent_type,
            "actual_agents": actual_agents,
            "task_type_match": task_type_match,
            "agent_match": agent_match,
            "all_passed": all_passed,
            "status": "✅ 通過" if all_passed else "❌ 失敗",
            "error": None,
        }

        return result

    except Exception as e:
        print(f"  ❌ 測試執行失敗: {e}")
        import traceback

        traceback.print_exc()
        return {
            "scenario_id": scenario_id,
            "category": scenario["category"],
            "complexity": scenario.get("complexity", "未知"),
            "user_input": user_input,
            "expected_task_type": expected_task_type,
            "expected_agent": expected_agent,
            "actual_task_type": None,
            "actual_agents": [],
            "task_type_match": False,
            "agent_match": False,
            "all_passed": False,
            "status": "❌ 錯誤",
            "error": str(e),
        }


async def run_all_tests(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """執行所有 md-editor 場景測試

    Args:
        limit: 限制執行的場景數量（用於快速測試），None 表示執行所有場景
    """
    scenarios = MD_EDITOR_SCENARIOS[:limit] if limit else MD_EDITOR_SCENARIOS
    results = []
    total = len(scenarios)

    print(f"\n{'='*80}")
    print("開始執行 md-editor 場景測試")
    print(f"總場景數: {total}" + (f" (限制: {limit})" if limit else ""))
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n進度: [{i}/{total}]")
        result = await run_single_test(scenario)
        results.append(result)

        # 每5個場景顯示一次統計
        if i % 5 == 0:
            passed = sum(1 for r in results if r["all_passed"])
            print(f"\n[進度統計] 已完成 {i}/{total}, 通過 {passed}/{i} ({passed/i*100:.1f}%)")

    return results


def generate_report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """生成測試報告"""
    total = len(results)
    passed = sum(1 for r in results if r["all_passed"])
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    report = {
        "test_type": "md-editor_only",
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
        "results": results,
    }

    return report


def print_report(report: Dict[str, Any]):
    """打印測試報告"""
    print(f"\n{'='*80}")
    print("md-editor 場景測試報告")
    print(f"{'='*80}")
    print(f"執行日期: {report['execution_date']}")
    print(f"執行時間: {report['execution_time']}")
    print(f"執行人: {report['executor']}")
    print(f"測試環境: {report['test_environment']}")
    print(f"系統版本: {report['system_version']}")
    print("\n[測試摘要]")
    summary = report["summary"]
    total = summary["total_scenarios"]
    print(f"  總場景數: {total}")
    print(f"  通過: {summary['passed']}")
    print(f"  失敗: {summary['failed']}")
    print(f"  通過率: {summary['pass_rate']}")

    # Agent 調用統計
    results = report.get("results", [])
    agents_with_agents = sum(1 for r in results if r.get("actual_agents", []))
    print("\n[Agent 調用統計]")
    print(f"  有 Agent 的場景: {agents_with_agents} / {total} ({agents_with_agents/total*100:.1f}%)")
    print(
        f"  無 Agent 的場景: {total - agents_with_agents} / {total} ({(total-agents_with_agents)/total*100:.1f}%)"
    )

    # 任務類型統計
    task_type_correct = sum(
        1 for r in results if r.get("actual_task_type") == r.get("expected_task_type")
    )
    print("\n[任務類型識別]")
    print(f"  正確: {task_type_correct} / {total} ({task_type_correct/total*100:.1f}%)")

    print("\n[失敗場景]")
    failed_results = [r for r in results if not r["all_passed"]]
    if failed_results:
        for result in failed_results:
            print(f"  ❌ {result['scenario_id']}: {result['user_input']}")
            print(f"     預期 Agent: {result['expected_agent']}")
            print(f"     實際 Agent: {result['actual_agents']}")
            if result["error"]:
                print(f"     錯誤: {result['error']}")
    else:
        print("  無失敗場景")

    print(f"\n{'='*80}\n")


def save_report(report: Dict[str, Any], output_dir: Path):
    """保存測試報告"""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"md_editor_test_{timestamp}.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"測試報告已保存至: {report_file}")
    return report_file


async def main(limit: Optional[int] = None):
    """主函數

    Args:
        limit: 限制執行的場景數量（用於快速測試），None 表示執行所有場景
    """
    # 執行測試
    results = await run_all_tests(limit=limit)

    # 生成報告
    report = generate_report(results)

    # 打印報告（需要修正，使用 report 中的 results）
    total = len(results)
    agents_with_agents = sum(1 for r in results if r.get("actual_agents", []))
    task_type_correct = sum(
        1 for r in results if r.get("actual_task_type") == r.get("expected_task_type")
    )

    print(f"\n{'='*80}")
    print("md-editor 場景測試報告")
    print(f"{'='*80}")
    print(f"執行日期: {report['execution_date']}")
    print(f"執行時間: {report['execution_time']}")
    print("\n[測試摘要]")
    summary = report["summary"]
    print(f"  總場景數: {summary['total_scenarios']}")
    print(f"  通過: {summary['passed']}")
    print(f"  失敗: {summary['failed']}")
    print(f"  通過率: {summary['pass_rate']}")

    print("\n[Agent 調用統計]")
    print(f"  有 Agent 的場景: {agents_with_agents} / {total} ({agents_with_agents/total*100:.1f}%)")
    print(
        f"  無 Agent 的場景: {total - agents_with_agents} / {total} ({(total-agents_with_agents)/total*100:.1f}%)"
    )

    print("\n[任務類型識別]")
    print(f"  正確: {task_type_correct} / {total} ({task_type_correct/total*100:.1f}%)")

    print("\n[失敗場景]")
    failed_results = [r for r in results if not r["all_passed"]]
    if failed_results:
        for result in failed_results[:10]:  # 只顯示前10個
            print(f"  ❌ {result['scenario_id']}: {result['user_input'][:50]}...")
            print(f"     預期 Agent: {result['expected_agent']}")
            print(f"     實際 Agent: {result['actual_agents']}")
    else:
        print("  無失敗場景")

    print(f"\n{'='*80}\n")

    # 保存報告
    output_dir = Path(__file__).parent / "test_reports"
    save_report(report, output_dir)

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="執行 md-editor 場景測試")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制執行的場景數量（用於快速測試）",
    )
    args = parser.parse_args()

    asyncio.run(main(limit=args.limit))
