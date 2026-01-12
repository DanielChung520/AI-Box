# 代碼功能說明: 執行測試並保存結果
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""執行測試並保存結果到文件"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加項目根目錄到 Python 路徑
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from test_file_editing_agent_routing import TEST_SCENARIOS

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.models import TaskAnalysisRequest


async def run_test_scenario(scenario: dict) -> dict:
    """執行單個測試場景"""
    scenario_id = scenario["scenario_id"]
    user_input = scenario["user_input"]
    expected_task_type = scenario.get("expected_task_type")
    expected_agent = scenario.get("expected_agent")

    print(f"執行測試: {scenario_id} - {user_input[:50]}...")

    try:
        # 確保 builtin agents 已註冊
        try:
            from agents.builtin import register_builtin_agents

            register_builtin_agents()
        except Exception:
            pass

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

        return {
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
    except Exception as e:
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


async def run_tests_batch(scenarios: list, batch_size: int = 10) -> list:
    """批量執行測試"""
    results = []
    total = len(scenarios)

    for i in range(0, total, batch_size):
        batch = scenarios[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"\n{'='*80}")
        print(f"批次 {batch_num}/{total_batches} (場景 {i+1}-{min(i+batch_size, total)})")
        print(f"{'='*80}\n")

        batch_results = await asyncio.gather(*[run_test_scenario(scenario) for scenario in batch])
        results.extend(batch_results)

        # 顯示批次統計
        batch_passed = sum(1 for r in batch_results if r["all_passed"])
        print(
            f"\n批次 {batch_num} 完成: {batch_passed}/{len(batch)} 通過 ({batch_passed/len(batch)*100:.1f}%)"
        )

        # 保存中間結果
        save_results(results, f"intermediate_results_batch_{batch_num}.json")

    return results


def save_results(results: list, filename: str = None):
    """保存結果到文件"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"

    output_dir = Path(__file__).parent / "test_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / filename

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n結果已保存至: {output_file}")
    return output_file


async def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="執行文件編輯 Agent 語義路由測試")
    parser.add_argument("--limit", type=int, default=None, help="限制場景數量")
    parser.add_argument("--batch-size", type=int, default=10, help="批次大小")
    args = parser.parse_args()

    scenarios = TEST_SCENARIOS[: args.limit] if args.limit else TEST_SCENARIOS

    print(f"\n{'='*80}")
    print("開始執行文件編輯 Agent 語義路由測試")
    print(f"總場景數: {len(scenarios)}")
    print(f"批次大小: {args.batch_size}")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    results = await run_tests_batch(scenarios, batch_size=args.batch_size)

    # 保存最終結果
    final_file = save_results(results)

    # 生成統計
    total = len(results)
    passed = sum(1 for r in results if r["all_passed"])
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"\n{'='*80}")
    print("測試完成")
    print(f"{'='*80}")
    print(f"總場景數: {total}")
    print(f"通過: {passed}")
    print(f"失敗: {failed}")
    print(f"通過率: {pass_rate:.2f}%")
    print(f"結果文件: {final_file}")
    print(f"{'='*80}\n")

    return results


if __name__ == "__main__":
    asyncio.run(main())
