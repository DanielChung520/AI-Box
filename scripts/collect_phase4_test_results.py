# 代碼功能說明: 收集階段四整合測試結果
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""解析 pytest junit.xml 報告並生成結構化的測試結果 JSON"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# 測試文件到測試劇本的映射
TEST_MAPPING = {
    "test_file_processing": "IT-4.1",
    "test_text_analysis": "IT-4.2",
    "test_kg_builder": "IT-4.3",  # 注意：文件名是 test_kg_builder.py 但實際測試上下文管理
    "test_aam_module": "IT-4.4",
}

# 測試方法到測試步驟的映射
STEP_MAPPING = {
    "IT-4.1": {
        "test_file_upload": "步驟 1",
        "test_file_chunking": "步驟 2",
        "test_multiformat_support": "步驟 3",
    },
    "IT-4.2": {
        "test_ner_extraction": "步驟 1",
        "test_re_extraction": "步驟 2",
        "test_rt_classification": "步驟 3",
        "test_triple_extraction": "步驟 4",
        "test_kg_build": "步驟 5",
    },
    "IT-4.3": {
        "test_context_manager": "步驟 1",
        "test_conversation_history": "步驟 2",
        "test_context_window": "步驟 3",
    },
    "IT-4.4": {
        "test_realtime_interaction": "步驟 1",
        "test_async_agent": "步驟 2",
        "test_hybrid_rag": "步驟 3",
    },
}


def parse_junit_xml(xml_path: Path) -> Dict[str, Any]:
    """解析 junit.xml 文件"""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    testsuite = root.find("testsuite")
    if testsuite is None:
        raise ValueError("無法找到 testsuite 元素")

    total = int(testsuite.get("tests", 0))
    errors = int(testsuite.get("errors", 0))
    failures = int(testsuite.get("failures", 0))
    skipped = int(testsuite.get("skipped", 0))
    time = float(testsuite.get("time", 0))

    passed = total - errors - failures - skipped
    pass_rate = (passed / total * 100) if total > 0 else 0

    # 按測試劇本分組
    test_results: Dict[str, Dict[str, Any]] = {}

    for testcase in testsuite.findall("testcase"):
        classname = testcase.get("classname", "")
        name = testcase.get("name", "")
        time_taken = float(testcase.get("time", 0))

        # 確定測試劇本 ID
        test_id = None
        for key, value in TEST_MAPPING.items():
            if key in classname.lower():
                test_id = value
                break

        if test_id is None:
            continue

        # 確定狀態
        if testcase.find("skipped") is not None:
            status = "skipped"
            skip_elem = testcase.find("skipped")
            reason = skip_elem.get("message", "") if skip_elem is not None else ""
        elif testcase.find("failure") is not None:
            status = "failed"
            failure_elem = testcase.find("failure")
            reason = failure_elem.get("message", "") if failure_elem is not None else ""
        elif testcase.find("error") is not None:
            status = "error"
            error_elem = testcase.find("error")
            reason = error_elem.get("message", "") if error_elem is not None else ""
        else:
            status = "passed"
            reason = ""

        # 獲取步驟編號
        step = STEP_MAPPING.get(test_id, {}).get(name, "")

        if test_id not in test_results:
            test_results[test_id] = {
                "status": "部分實現",
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0,
                "total": 0,
                "tests": [],
            }

        test_results[test_id]["total"] += 1
        if status == "passed":
            test_results[test_id]["passed"] += 1
        elif status == "failed":
            test_results[test_id]["failed"] += 1
        elif status == "skipped":
            test_results[test_id]["skipped"] += 1
        elif status == "error":
            test_results[test_id]["errors"] += 1

        # 更新狀態
        if test_results[test_id]["passed"] == test_results[test_id]["total"]:
            test_results[test_id]["status"] = "已實現"
        elif test_results[test_id]["passed"] > 0:
            test_results[test_id]["status"] = "部分實現"
        else:
            test_results[test_id]["status"] = "待實現"

        test_results[test_id]["tests"].append(
            {
                "name": name,
                "step": step,
                "status": status,
                "duration": time_taken,
                "reason": reason,
            }
        )

    return {
        "total": total,
        "passed": passed,
        "failed": failures,
        "skipped": skipped,
        "errors": errors,
        "duration": time,
        "pass_rate": round(pass_rate, 1),
        "test_date": datetime.now().strftime("%Y-%m-%d"),
        "tests": test_results,
    }


def main():
    """主函數"""
    base_dir = Path(__file__).parent.parent
    xml_path = base_dir / "tests" / "integration" / "phase4" / "junit.xml"
    output_path = base_dir / "tests" / "integration" / "phase4" / "test_results_summary.json"

    if not xml_path.exists():
        print(f"錯誤: 找不到 {xml_path}")
        return

    print(f"解析 {xml_path}...")
    results = parse_junit_xml(xml_path)

    print(f"寫入結果到 {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n測試結果摘要:")
    print(f"  總測試數: {results['total']}")
    print(f"  通過: {results['passed']}")
    print(f"  失敗: {results['failed']}")
    print(f"  跳過: {results['skipped']}")
    print(f"  錯誤: {results['errors']}")
    print(f"  通過率: {results['pass_rate']}%")
    print(f"  執行時間: {results['duration']:.2f}s")

    print("\n各測試劇本結果:")
    for test_id, test_data in results["tests"].items():
        print(f"  {test_id}: {test_data['status']} ({test_data['passed']}/{test_data['total']} 通過)")


if __name__ == "__main__":
    main()
