# 代碼功能說明: 收集階段五和階段一 IT-1.5 測試結果
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""收集階段五和階段一 IT-1.5 測試結果並生成 JSON 報告"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def parse_pytest_output(output: str) -> Dict[str, Any]:
    """解析 pytest 輸出並提取測試結果"""
    results: Dict[str, Any] = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "duration": 0.0,
        "test_details": [],
    }

    # 解析總結行
    summary_match = re.search(r"(\d+)\s+passed.*?(\d+)\s+skipped.*?(\d+\.\d+)s", output)
    if summary_match:
        results["passed"] = int(summary_match.group(1))
        results["skipped"] = int(summary_match.group(2))
        results["duration"] = float(summary_match.group(3))

    failed_match = re.search(r"(\d+)\s+failed", output)
    if failed_match:
        results["failed"] = int(failed_match.group(1))

    error_match = re.search(r"(\d+)\s+error", output)
    if error_match:
        results["errors"] = int(error_match.group(1))

    results["total"] = (
        results["passed"] + results["failed"] + results["skipped"] + results["errors"]
    )

    # 解析測試詳情
    test_pattern = (
        r"tests/integration/(phase\d+)/(test_\w+\.py)::(\w+)::(\w+)\s+(PASSED|FAILED|SKIPPED|ERROR)"
    )
    for match in re.finditer(test_pattern, output):
        phase = match.group(1)
        test_file = match.group(2)
        test_class = match.group(3)
        test_name = match.group(4)
        status = match.group(5).lower()

        results["test_details"].append(
            {
                "phase": phase,
                "test_file": test_file,
                "test_class": test_class,
                "test_name": test_name,
                "status": status,
            }
        )

    return results


def organize_results(phase1_output: str, phase5_output: str) -> Dict[str, Any]:
    """組織測試結果"""
    phase1_parsed = parse_pytest_output(phase1_output)
    phase5_parsed = parse_pytest_output(phase5_output)

    # 測試 ID 到步驟映射
    test_mapping = {
        "IT-1.5": {
            "test_ollama_connection": "步驟 1",
            "test_model_list": "步驟 2",
            "test_llm_chat": "步驟 3",
            "test_embeddings": "步驟 4",
        },
        "IT-5.1": {
            "test_llm_routing_decision": "步驟 1",
            "test_llm_routing_with_different_tasks": "步驟 2",
            "test_llm_routing_performance": "步驟 3",
        },
        "IT-5.2": {
            "test_llm_health_check": "步驟 1",
            "test_llm_provider_status": "步驟 2",
            "test_multi_llm_switching": "步驟 3",
            "test_llm_models_availability": "步驟 4",
        },
        "IT-5.3": {
            "test_load_balancer_stats": "步驟 1",
            "test_load_balancer_health_check": "步驟 2",
            "test_load_balancer_performance": "步驟 3",
            "test_load_balancer_strategy": "步驟 4",
        },
        "IT-5.4": {
            "test_health_check_status": "步驟 1",
            "test_failover_mechanism": "步驟 2",
            "test_failover_retry_mechanism": "步驟 3",
            "test_provider_health_status": "步驟 4",
            "test_failover_with_different_providers": "步驟 5",
        },
    }

    # 合併結果
    total_results = {
        "total": phase1_parsed["total"] + phase5_parsed["total"],
        "passed": phase1_parsed["passed"] + phase5_parsed["passed"],
        "failed": phase1_parsed["failed"] + phase5_parsed["failed"],
        "skipped": phase1_parsed["skipped"] + phase5_parsed["skipped"],
        "errors": phase1_parsed["errors"] + phase5_parsed["errors"],
        "duration": phase1_parsed["duration"] + phase5_parsed["duration"],
        "test_date": datetime.now().strftime("%Y-%m-%d"),
    }

    if total_results["total"] > 0:
        total_results["pass_rate"] = (total_results["passed"] / total_results["total"]) * 100
    else:
        total_results["pass_rate"] = 0.0

    # 組織測試詳情
    all_details = phase1_parsed["test_details"] + phase5_parsed["test_details"]
    organized_tests: Dict[str, Dict[str, Any]] = {}

    # 按測試 ID 分組
    for detail in all_details:
        test_name = detail["test_name"]
        test_file = detail["test_file"]

        # 確定測試 ID
        test_id = None
        if (
            "test_ollama" in test_file
            or "test_model" in test_file
            or "test_llm_chat" in test_name
            or "test_embeddings" in test_name
        ):
            test_id = "IT-1.5"
        elif "test_llm_router" in test_file:
            test_id = "IT-5.1"
        elif "test_multi_llm" in test_file:
            test_id = "IT-5.2"
        elif "test_load_balancer" in test_file:
            test_id = "IT-5.3"
        elif "test_failover" in test_file:
            test_id = "IT-5.4"

        if test_id:
            if test_id not in organized_tests:
                organized_tests[test_id] = {
                    "status": "已實現",
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "errors": 0,
                    "total": 0,
                    "tests": [],
                }

            step = test_mapping.get(test_id, {}).get(test_name, "")
            organized_tests[test_id]["tests"].append(
                {
                    "name": test_name,
                    "step": step,
                    "status": detail["status"],
                    "duration": 0.0,
                    "reason": "",
                }
            )

            organized_tests[test_id]["total"] += 1
            if detail["status"] == "passed":
                organized_tests[test_id]["passed"] += 1
            elif detail["status"] == "skipped":
                organized_tests[test_id]["skipped"] += 1
            elif detail["status"] == "failed":
                organized_tests[test_id]["failed"] += 1
            elif detail["status"] == "error":
                organized_tests[test_id]["errors"] += 1

    # 更新狀態
    for test_id, test_data in organized_tests.items():
        if test_data["passed"] > 0 and test_data["skipped"] == 0:
            test_data["status"] = "已實現"
        elif test_data["passed"] > 0:
            test_data["status"] = "部分實現"
        else:
            test_data["status"] = "待實現"

    total_results["tests"] = organized_tests

    return total_results


def main():
    """主函數"""
    base_dir = Path(__file__).parent.parent

    # 讀取已運行的測試輸出
    print("讀取測試輸出...")
    with open("/tmp/pytest_output.txt", "r", encoding="utf-8") as f:
        full_output = f.read()

    # 分離階段一和階段五的輸出
    phase1_lines = []
    phase5_lines = []
    current_phase = None

    for line in full_output.split("\n"):
        if "test_ollama_integration.py" in line:
            current_phase = "phase1"
        elif "phase5" in line or any(
            f"test_{x}" in line for x in ["llm_router", "multi_llm", "load_balancer", "failover"]
        ):
            current_phase = "phase5"

        if current_phase == "phase1":
            phase1_lines.append(line)
        elif current_phase == "phase5":
            phase5_lines.append(line)

    phase1_output = "\n".join(phase1_lines)
    phase5_output = "\n".join(phase5_lines)

    # 如果無法分離，使用完整輸出
    if not phase1_output or not phase5_output:
        phase1_output = full_output
        phase5_output = full_output

    # 組織結果
    results = organize_results(phase1_output, phase5_output)

    # 保存結果
    phase5_dir = base_dir / "tests" / "integration" / "phase5"
    phase5_dir.mkdir(parents=True, exist_ok=True)

    output_file = phase5_dir / "test_results_summary.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"測試結果已保存到: {output_file}")
    print(f"總測試數: {results['total']}")
    print(f"通過: {results['passed']}")
    print(f"失敗: {results['failed']}")
    print(f"跳過: {results['skipped']}")
    print(f"通過率: {results['pass_rate']:.1f}%")


if __name__ == "__main__":
    main()
