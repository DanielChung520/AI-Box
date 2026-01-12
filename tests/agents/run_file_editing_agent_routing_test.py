# 代碼功能說明: 文件編輯 Agent 語義路由測試執行腳本
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""文件編輯 Agent 語義路由測試執行腳本

批量執行測試並生成測試報告
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

from test_file_editing_agent_routing import TEST_SCENARIOS

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.models import TaskAnalysisRequest


async def run_single_test(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """執行單個測試場景"""
    scenario_id = scenario["scenario_id"]
    user_input = scenario["user_input"]
    expected_task_type = scenario.get("expected_task_type")
    expected_agent = scenario.get("expected_agent")

    print(f"\n[測試場景 {scenario_id}] {user_input}")

    try:
        # 確保 builtin agents 已註冊
        try:
            from agents.builtin import register_builtin_agents

            register_builtin_agents()
        except Exception as e:
            print(f"  [警告] Agent 註冊失敗: {e}")

        orchestrator = AgentOrchestrator()
        analysis_request = TaskAnalysisRequest(task=user_input)
        task_analyzer = orchestrator._get_task_analyzer()
        analysis_result = await task_analyzer.analyze(analysis_request)

        # 驗證結果
        task_type_match = (
            analysis_result.task_type.value == expected_task_type if expected_task_type else False
        )
        agent_match = (
            expected_agent in analysis_result.suggested_agents if expected_agent else False
        )
        all_passed = task_type_match and agent_match

        result = {
            "scenario_id": scenario_id,
            "category": scenario["category"],
            "complexity": scenario.get("complexity", "未知"),
            "user_input": user_input,
            "expected_task_type": expected_task_type,
            "expected_agent": expected_agent,
            "actual_task_type": analysis_result.task_type.value,
            "actual_agents": analysis_result.suggested_agents,
            "task_type_match": task_type_match,
            "agent_match": agent_match,
            "all_passed": all_passed,
            "confidence": analysis_result.confidence,
            "status": "✅ 通過" if all_passed else "❌ 失敗",
            "error": None,
        }

        status_icon = "✅" if all_passed else "❌"
        print(f"  {status_icon} 任務類型: {task_type_match}, Agent: {agent_match}")

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
            "confidence": 0.0,
            "status": "❌ 錯誤",
            "error": str(e),
        }


async def run_all_tests(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """執行所有測試場景

    Args:
        limit: 限制執行的場景數量（用於測試），None 表示執行所有場景
    """
    scenarios = TEST_SCENARIOS[:limit] if limit else TEST_SCENARIOS
    results = []
    total = len(scenarios)

    print(f"\n{'='*80}")
    print("開始執行文件編輯 Agent 語義路由測試")
    print(f"總場景數: {total}" + (f" (限制: {limit})" if limit else ""))
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n進度: [{i}/{total}]")
        result = await run_single_test(scenario)
        results.append(result)

        # 每10個場景顯示一次統計
        if i % 10 == 0:
            passed = sum(1 for r in results if r["all_passed"])
            print(f"\n[進度統計] 已完成 {i}/{total}, 通過 {passed}/{i} ({passed/i*100:.1f}%)")

    return results


def generate_report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """生成測試報告"""
    total = len(results)
    passed = sum(1 for r in results if r["all_passed"])
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    # 按類別統計
    category_stats = {}
    for result in results:
        cat = result["category"]
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0, "failed": 0}
        category_stats[cat]["total"] += 1
        if result["all_passed"]:
            category_stats[cat]["passed"] += 1
        else:
            category_stats[cat]["failed"] += 1

    # 按複雜度統計
    complexity_stats = {}
    for result in results:
        comp = result["complexity"]
        if comp not in complexity_stats:
            complexity_stats[comp] = {"total": 0, "passed": 0, "failed": 0}
        complexity_stats[comp]["total"] += 1
        if result["all_passed"]:
            complexity_stats[comp]["passed"] += 1
        else:
            complexity_stats[comp]["failed"] += 1

    report = {
        "test_round": 1,
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
        "category_stats": {
            cat: {
                "total": stats["total"],
                "passed": stats["passed"],
                "failed": stats["failed"],
                "pass_rate": f"{stats['passed']/stats['total']*100:.2f}%"
                if stats["total"] > 0
                else "0%",
            }
            for cat, stats in category_stats.items()
        },
        "complexity_stats": {
            comp: {
                "total": stats["total"],
                "passed": stats["passed"],
                "failed": stats["failed"],
                "pass_rate": f"{stats['passed']/stats['total']*100:.2f}%"
                if stats["total"] > 0
                else "0%",
            }
            for comp, stats in complexity_stats.items()
        },
        "results": results,
    }

    return report


def print_report(report: Dict[str, Any]):
    """打印測試報告"""
    print(f"\n{'='*80}")
    print("文件編輯 Agent 語義路由測試報告")
    print(f"{'='*80}")
    print(f"執行日期: {report['execution_date']}")
    print(f"執行時間: {report['execution_time']}")
    print(f"執行人: {report['executor']}")
    print(f"測試環境: {report['test_environment']}")
    print(f"系統版本: {report['system_version']}")
    print("\n[測試摘要]")
    summary = report["summary"]
    print(f"  總場景數: {summary['total_scenarios']}")
    print(f"  通過: {summary['passed']}")
    print(f"  失敗: {summary['failed']}")
    print(f"  通過率: {summary['pass_rate']}")

    print("\n[按類別統計]")
    for cat, stats in report["category_stats"].items():
        print(f"  {cat}: {stats['passed']}/{stats['total']} 通過 ({stats['pass_rate']})")

    print("\n[按複雜度統計]")
    for comp, stats in report["complexity_stats"].items():
        print(f"  {comp}: {stats['passed']}/{stats['total']} 通過 ({stats['pass_rate']})")

    print("\n[失敗場景]")
    failed_results = [r for r in report["results"] if not r["all_passed"]]
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
    report_file = output_dir / f"file_editing_agent_routing_test_report_{timestamp}.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"測試報告已保存至: {report_file}")
    return report_file


async def main(limit: Optional[int] = None):
    """主函數

    Args:
        limit: 限制執行的場景數量（用於測試），None 表示執行所有場景
    """
    # 執行測試
    results = await run_all_tests(limit=limit)

    # 生成報告
    report = generate_report(results)

    # 打印報告
    print_report(report)

    # 保存報告
    output_dir = Path(__file__).parent / "test_reports"
    save_report(report, output_dir)

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="執行文件編輯 Agent 語義路由測試")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制執行的場景數量（用於測試）",
    )
    args = parser.parse_args()

    asyncio.run(main(limit=args.limit))
