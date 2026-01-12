# 代碼功能說明: Router LLM 模型比較自動化測試腳本
# 創建日期: 2026-01-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-09

"""Router LLM 模型比較自動化測試腳本

支持自動化測試，可以：
1. 使用 pytest 運行（推薦）
2. 直接運行腳本（獨立模式）
3. 生成比較報告

運行方式：
    # 使用 pytest 運行（推薦，支持並行和報告）
    pytest tests/agents/test_router_llm_model_comparison_auto.py -v -s

    # 只測試特定模型
    pytest tests/agents/test_router_llm_model_comparison_auto.py -v -s -k "qwen3-next"

    # 只測試特定場景
    pytest tests/agents/test_router_llm_model_comparison_auto.py -v -s -k "FE-011"

    # 直接運行腳本（獨立模式）
    python3 tests/agents/test_router_llm_model_comparison_auto.py
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加項目根目錄到 Python 路徑
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest

from agents.task_analyzer.models import RouterInput
from agents.task_analyzer.router_llm import RouterLLM

# 測試模型列表
# 注意：quentinz/bge-large-zh-v1.5:latest 已排除（測試結果顯示不適合意圖判斷，所有任務都被識別為 conversation）
TEST_MODELS = [
    # "quentinz/bge-large-zh-v1.5:latest",  # 已排除：不適合意圖判斷
    "qwen3-next:latest",
    "gpt-oss:120b-cloud",
    "mistral-nemo:12b",
    "gpt-oss:20b",
    "qwen3-coder:30b",
]

# 類別 2：產生/創建文件（10個場景）
CATEGORY_2_SCENARIOS = [
    {
        "scenario_id": "FE-011",
        "user_input": "幫我產生一個 README.md 文件",
        "expected_task_type": "execution",
    },
    {
        "scenario_id": "FE-012",
        "user_input": "創建一個新的配置文件 config.json",
        "expected_task_type": "execution",
    },
    {
        "scenario_id": "FE-013",
        "user_input": "幫我寫一個 Python 腳本",
        "expected_task_type": "execution",
    },
    {
        "scenario_id": "FE-014",
        "user_input": "生成一份報告文件",
        "expected_task_type": "execution",
    },
    {
        "scenario_id": "FE-015",
        "user_input": "幫我建立一個新的文件",
        "expected_task_type": "execution",
    },
    {
        "scenario_id": "FE-016",
        "user_input": "製作一個 Markdown 文檔",
        "expected_task_type": "execution",
    },
    {
        "scenario_id": "FE-017",
        "user_input": "幫我產生一份測試報告",
        "expected_task_type": "execution",
    },
    {
        "scenario_id": "FE-018",
        "user_input": "建立一個新的程式檔案",
        "expected_task_type": "execution",
    },
    {
        "scenario_id": "FE-019",
        "user_input": "幫我寫一份文件",
        "expected_task_type": "execution",
    },
    {
        "scenario_id": "FE-020",
        "user_input": "生成一個新的檔案",
        "expected_task_type": "execution",
    },
]

# 類別 3：隱含編輯意圖（5個場景）
CATEGORY_3_SCENARIOS = [
    {
        "scenario_id": "FE-021",
        "user_input": "幫我在 README.md 中加入安裝說明",
        "expected_task_type": "execution",
    },
    {
        "scenario_id": "FE-022",
        "user_input": "在文件裡添加註釋",
        "expected_task_type": "execution",
    },
    {
        "scenario_id": "FE-023",
        "user_input": "把這個函數改成新的實現",
        "expected_task_type": "execution",
    },
    {
        "scenario_id": "FE-024",
        "user_input": "幫我整理一下這個文件",
        "expected_task_type": "execution",
    },
    {
        "scenario_id": "FE-025",
        "user_input": "優化這個代碼文件",
        "expected_task_type": "execution",
    },
]

# 合併測試場景（類別2 + 類別3）
ALL_TEST_SCENARIOS = CATEGORY_2_SCENARIOS + CATEGORY_3_SCENARIOS

# 全局結果存儲（用於生成比較報告）
_test_results: List[Dict[str, Any]] = []

# 超時設置（秒）
TEST_TIMEOUT = 30


async def test_model_on_scenario(
    model_name: str, scenario: Dict[str, Any], timeout: float = TEST_TIMEOUT
) -> Dict[str, Any]:
    """
    測試單個模型在單個場景上的表現

    Args:
        model_name: 模型名稱
        scenario: 測試場景
        timeout: 超時時間（秒）

    Returns:
        測試結果字典
    """
    original_model = os.environ.get("ROUTER_LLM_MODEL")
    os.environ["ROUTER_LLM_MODEL"] = model_name

    try:
        router_llm = RouterLLM(preferred_provider="ollama")
        router_input = RouterInput(
            user_query=scenario["user_input"],
            session_context={},
        )

        start_time = time.time()
        try:
            # 使用超時控制
            decision = await asyncio.wait_for(router_llm.route(router_input), timeout=timeout)
            elapsed_time = time.time() - start_time

            task_type_correct = decision.intent_type == scenario["expected_task_type"]
            needs_agent_correct = decision.needs_agent  # 文件編輯任務應該需要 Agent

            return {
                "model": model_name,
                "scenario_id": scenario["scenario_id"],
                "user_input": scenario["user_input"],
                "expected_task_type": scenario["expected_task_type"],
                "actual_task_type": decision.intent_type,
                "task_type_correct": task_type_correct,
                "needs_agent": decision.needs_agent,
                "needs_agent_correct": needs_agent_correct,
                "confidence": decision.confidence,
                "elapsed_time": elapsed_time,
                "success": task_type_correct and needs_agent_correct,
                "error": None,
            }
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            return {
                "model": model_name,
                "scenario_id": scenario["scenario_id"],
                "user_input": scenario["user_input"],
                "expected_task_type": scenario["expected_task_type"],
                "actual_task_type": None,
                "task_type_correct": False,
                "needs_agent": False,
                "needs_agent_correct": False,
                "confidence": 0.0,
                "elapsed_time": elapsed_time,
                "success": False,
                "error": f"Timeout after {timeout}s",
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            return {
                "model": model_name,
                "scenario_id": scenario["scenario_id"],
                "user_input": scenario["user_input"],
                "expected_task_type": scenario["expected_task_type"],
                "actual_task_type": None,
                "task_type_correct": False,
                "needs_agent": False,
                "needs_agent_correct": False,
                "confidence": 0.0,
                "elapsed_time": elapsed_time,
                "success": False,
                "error": str(e),
            }
    finally:
        # 恢復原始環境變量
        if original_model is not None:
            os.environ["ROUTER_LLM_MODEL"] = original_model
        elif "ROUTER_LLM_MODEL" in os.environ:
            del os.environ["ROUTER_LLM_MODEL"]


def _generate_comparison_report(results: List[Dict[str, Any]], output_file: Optional[str] = None):
    """生成模型比較報告"""
    print("\n" + "=" * 80)
    print("模型比較分析表（自動生成）")
    print("=" * 80)

    # 按模型分組統計
    model_stats: Dict[str, Dict[str, Any]] = {}
    for model in TEST_MODELS:
        model_results = [r for r in results if r["model"] == model]
        if not model_results:
            continue

        correct_count = sum(1 for r in model_results if r["task_type_correct"])
        needs_agent_correct_count = sum(1 for r in model_results if r["needs_agent_correct"])
        success_count = sum(1 for r in model_results if r["success"])
        total_time = sum(r["elapsed_time"] for r in model_results)
        avg_time = total_time / len(model_results)
        avg_confidence = sum(r["confidence"] for r in model_results) / len(model_results)

        model_stats[model] = {
            "task_type_accuracy": correct_count / len(model_results) * 100,
            "needs_agent_accuracy": needs_agent_correct_count / len(model_results) * 100,
            "overall_success_rate": success_count / len(model_results) * 100,
            "avg_time": avg_time,
            "total_time": total_time,
            "avg_confidence": avg_confidence,
        }

    # 打印整體比較表
    print("\n| 模型 | 任務類型識別正確率 | needs_agent 正確率 | 整體成功率 | 平均耗時 | 總耗時 | 平均置信度 |")
    print(
        "|------|-------------------|-------------------|-----------|---------|--------|-----------|"
    )
    for model in TEST_MODELS:
        if model not in model_stats:
            continue
        stats = model_stats[model]
        print(
            f"| {model[:30]:30} | {stats['task_type_accuracy']:17.1f}% | {stats['needs_agent_accuracy']:17.1f}% | "
            f"{stats['overall_success_rate']:9.1f}% | {stats['avg_time']:7.2f}s | {stats['total_time']:6.2f}s | "
            f"{stats['avg_confidence']:11.2f} |"
        )

    # 按類別統計
    print("\n" + "=" * 80)
    print("按類別統計（類別2：產生/創建文件）")
    print("=" * 80)
    category_2_results = [r for r in results if r["scenario_id"].startswith("FE-01")]
    print("\n| 模型 | 任務類型識別正確率 | needs_agent 正確率 | 整體成功率 | 平均耗時 |")
    print("|------|-------------------|-------------------|-----------|---------|")
    for model in TEST_MODELS:
        model_cat2_results = [r for r in category_2_results if r["model"] == model]
        if model_cat2_results:
            correct_count = sum(1 for r in model_cat2_results if r["task_type_correct"])
            needs_agent_correct_count = sum(
                1 for r in model_cat2_results if r["needs_agent_correct"]
            )
            success_count = sum(1 for r in model_cat2_results if r["success"])
            avg_time = sum(r["elapsed_time"] for r in model_cat2_results) / len(model_cat2_results)
            print(
                f"| {model[:30]:30} | {correct_count/len(model_cat2_results)*100:17.1f}% | "
                f"{needs_agent_correct_count/len(model_cat2_results)*100:17.1f}% | "
                f"{success_count/len(model_cat2_results)*100:9.1f}% | {avg_time:7.2f}s |"
            )

    print("\n" + "=" * 80)
    print("按類別統計（類別3：隱含編輯意圖）")
    print("=" * 80)
    category_3_results = [r for r in results if r["scenario_id"].startswith("FE-02")]
    print("\n| 模型 | 任務類型識別正確率 | needs_agent 正確率 | 整體成功率 | 平均耗時 |")
    print("|------|-------------------|-------------------|-----------|---------|")
    for model in TEST_MODELS:
        model_cat3_results = [r for r in category_3_results if r["model"] == model]
        if model_cat3_results:
            correct_count = sum(1 for r in model_cat3_results if r["task_type_correct"])
            needs_agent_correct_count = sum(
                1 for r in model_cat3_results if r["needs_agent_correct"]
            )
            success_count = sum(1 for r in model_cat3_results if r["success"])
            avg_time = sum(r["elapsed_time"] for r in model_cat3_results) / len(model_cat3_results)
            print(
                f"| {model[:30]:30} | {correct_count/len(model_cat3_results)*100:17.1f}% | "
                f"{needs_agent_correct_count/len(model_cat3_results)*100:17.1f}% | "
                f"{success_count/len(model_cat3_results)*100:9.1f}% | {avg_time:7.2f}s |"
            )

    # 保存 JSON 報告
    if output_file:
        report_data = {
            "test_time": datetime.now().isoformat(),
            "models": TEST_MODELS,
            "scenarios": ALL_TEST_SCENARIOS,
            "results": results,
            "statistics": model_stats,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        print(f"\n報告已保存到: {output_file}")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """設置測試環境"""
    global _test_results
    _test_results.clear()
    yield
    # 測試結束後生成比較報告
    if _test_results:
        # 生成報告文件
        report_file = (
            Path(__file__).parent.parent.parent
            / "docs"
            / "系统设计文档"
            / "核心组件"
            / "Agent平台"
            / f"router_llm_model_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        _generate_comparison_report(_test_results, str(report_file))


class TestRouterLLMModelComparison:
    """Router LLM 模型比較測試類（pytest 自動化測試）"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("model_name", TEST_MODELS)
    @pytest.mark.parametrize("scenario", ALL_TEST_SCENARIOS)
    async def test_model_on_scenario(self, model_name: str, scenario: Dict[str, Any]):
        """
        測試單個模型在單個場景上的表現

        Args:
            model_name: 模型名稱
            scenario: 測試場景
        """
        result = await test_model_on_scenario(model_name, scenario)

        # 存儲結果到全局列表
        global _test_results
        _test_results.append(result)

        # 輸出測試結果摘要
        status = "✅" if result["success"] else "❌"
        print(
            f"{status} [{model_name[:20]:20}] {scenario['scenario_id']}: "
            f"任務類型={result['actual_task_type']} (預期={scenario['expected_task_type']}), "
            f"needs_agent={result['needs_agent']}, 耗時={result['elapsed_time']:.2f}s"
        )

        # 不強制斷言失敗（這是比較測試，記錄結果即可）
        # 如果需要嚴格測試，可以取消註釋以下斷言
        # assert result["task_type_correct"], (
        #     f"模型 {model_name} 在場景 {scenario['scenario_id']} 上任務類型識別錯誤"
        # )
        # assert result["needs_agent_correct"], (
        #     f"模型 {model_name} 在場景 {scenario['scenario_id']} 上 needs_agent 錯誤"
        # )


# 獨立運行模式（不使用 pytest）
async def run_standalone():
    """獨立運行所有模型測試（按模型分組）"""
    print("=" * 80)
    print("Router LLM 模型比較測試（獨立運行模式 - 按模型分組）")
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print(f"\n測試模型數量: {len(TEST_MODELS)}")
    print(f"測試場景數量: {len(ALL_TEST_SCENARIOS)}")
    print(f"總測試次數: {len(TEST_MODELS) * len(ALL_TEST_SCENARIOS)}")
    print("\n測試模型列表:")
    for i, model in enumerate(TEST_MODELS, 1):
        print(f"  {i}. {model}")

    print("\n" + "=" * 80)
    print("開始測試...")
    print("=" * 80)

    all_results: List[Dict[str, Any]] = []

    for model_idx, model_name in enumerate(TEST_MODELS, 1):
        print(f"\n[{model_idx}/{len(TEST_MODELS)}] 測試模型: {model_name}")
        print("-" * 80)

        model_results = []
        for scenario_idx, scenario in enumerate(ALL_TEST_SCENARIOS, 1):
            print(
                f"  測試場景 [{scenario_idx}/{len(ALL_TEST_SCENARIOS)}]: {scenario['scenario_id']} - {scenario['user_input'][:50]}..."
            )
            result = await test_model_on_scenario(model_name, scenario)
            model_results.append(result)
            all_results.append(result)

            status = "✅" if result["success"] else "❌"
            print(
                f"    {status} 任務類型: {result['actual_task_type']} (預期: {result['expected_task_type']}), "
                f"needs_agent: {result['needs_agent']}, "
                f"耗時: {result['elapsed_time']:.2f}s"
            )
            if result["error"]:
                print(f"    錯誤: {result['error']}")

        # 計算模型統計
        correct_count = sum(1 for r in model_results if r["task_type_correct"])
        needs_agent_correct_count = sum(1 for r in model_results if r["needs_agent_correct"])
        success_count = sum(1 for r in model_results if r["success"])
        avg_time = sum(r["elapsed_time"] for r in model_results) / len(model_results)
        avg_confidence = sum(r["confidence"] for r in model_results) / len(model_results)

        print(f"\n  模型統計 ({model_name}):")
        print(
            f"    任務類型識別正確率: {correct_count}/{len(model_results)} ({correct_count/len(model_results)*100:.1f}%)"
        )
        print(
            f"    needs_agent 正確率: {needs_agent_correct_count}/{len(model_results)} ({needs_agent_correct_count/len(model_results)*100:.1f}%)"
        )
        print(
            f"    整體成功率: {success_count}/{len(model_results)} ({success_count/len(model_results)*100:.1f}%)"
        )
        print(f"    平均耗時: {avg_time:.2f}s")
        print(f"    平均置信度: {avg_confidence:.2f}")

    # 生成比較分析表
    report_file = (
        Path(__file__).parent.parent.parent
        / "docs"
        / "系统设计文档"
        / "核心组件"
        / "Agent平台"
        / f"router_llm_model_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    _generate_comparison_report(all_results, str(report_file))

    print("\n" + "=" * 80)
    print("測試完成")
    print("=" * 80)

    return all_results


async def run_sequential_by_scenario():
    """按場景分組依序測試所有模型"""
    print("=" * 80)
    print("Router LLM 模型比較測試（依序模式 - 按場景分組）")
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print(f"\n測試模型數量: {len(TEST_MODELS)}")
    print(f"測試場景數量: {len(ALL_TEST_SCENARIOS)}")
    print(f"總測試次數: {len(TEST_MODELS) * len(ALL_TEST_SCENARIOS)}")
    print("\n測試模型列表:")
    for i, model in enumerate(TEST_MODELS, 1):
        print(f"  {i}. {model}")

    print("\n" + "=" * 80)
    print("開始測試（按場景分組依序運行）...")
    print("=" * 80)

    all_results: List[Dict[str, Any]] = []

    # 遍歷所有場景
    for scenario_idx, scenario in enumerate(ALL_TEST_SCENARIOS, 1):
        print(f"\n{'=' * 80}")
        print(
            f"[場景 {scenario_idx}/{len(ALL_TEST_SCENARIOS)}] {scenario['scenario_id']}: {scenario['user_input']}"
        )
        print("-" * 80)

        scenario_results = []

        # 依序測試所有模型
        for model_idx, model_name in enumerate(TEST_MODELS, 1):
            print(f"  [{model_idx}/{len(TEST_MODELS)}] 測試模型: {model_name[:50]}...")
            result = await test_model_on_scenario(model_name, scenario)
            scenario_results.append(result)
            all_results.append(result)

            status = "✅" if result["success"] else "❌"
            task_type_status = "✓" if result["task_type_correct"] else "✗"
            needs_agent_status = "✓" if result["needs_agent_correct"] else "✗"

            print(
                f"    {status} 任務類型={task_type_status} {result['actual_task_type']} "
                f"(預期={scenario['expected_task_type']}), "
                f"needs_agent={needs_agent_status} {result['needs_agent']}, "
                f"耗時={result['elapsed_time']:.2f}s"
            )
            if result["error"]:
                print(f"    錯誤: {result['error']}")

        # 計算場景統計摘要
        task_type_correct_count = sum(1 for r in scenario_results if r["task_type_correct"])
        needs_agent_correct_count = sum(1 for r in scenario_results if r["needs_agent_correct"])
        success_count = sum(1 for r in scenario_results if r["success"])
        avg_time = sum(r["elapsed_time"] for r in scenario_results) / len(scenario_results)
        total_time = sum(r["elapsed_time"] for r in scenario_results)
        avg_confidence = sum(r["confidence"] for r in scenario_results) / len(scenario_results)

        print(f"\n  場景統計 ({scenario['scenario_id']}):")
        print(
            f"    任務類型識別正確: {task_type_correct_count}/{len(scenario_results)} ({task_type_correct_count/len(scenario_results)*100:.1f}%)"
        )
        print(
            f"    needs_agent 正確: {needs_agent_correct_count}/{len(scenario_results)} ({needs_agent_correct_count/len(scenario_results)*100:.1f}%)"
        )
        print(
            f"    整體成功: {success_count}/{len(scenario_results)} ({success_count/len(scenario_results)*100:.1f}%)"
        )
        print(f"    平均耗時: {avg_time:.2f}s")
        print(f"    總耗時: {total_time:.2f}s")
        print(f"    平均置信度: {avg_confidence:.2f}")

    # 生成比較分析表
    report_file = (
        Path(__file__).parent.parent.parent
        / "docs"
        / "系统设计文档"
        / "核心组件"
        / "Agent平台"
        / f"router_llm_model_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    _generate_comparison_report(all_results, str(report_file))

    print("\n" + "=" * 80)
    print("測試完成")
    print("=" * 80)

    return all_results


if __name__ == "__main__":
    import sys

    # 檢查命令行參數
    if len(sys.argv) > 1 and sys.argv[1] == "--sequential":
        # 依序模式：按場景分組
        asyncio.run(run_sequential_by_scenario())
    else:
        # 默認模式：按模型分組
        asyncio.run(run_standalone())
