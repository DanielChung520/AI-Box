# 代碼功能說明: 解析測試結果並更新測試劇本文件
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""解析 pytest 測試結果並更新測試劇本文件"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict


def parse_pytest_output(output_file: str) -> Dict[str, any]:
    """解析 pytest 輸出文件"""

    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 解析測試場景
    scenario_pattern = r"測試場景: (\w+-\d+)"
    re.findall(scenario_pattern, content)

    # 解析驗證結果

    # 解析測試總結

    # 解析 PASSED/FAILED
    passed_pattern = r"(\w+-\d+).*?PASSED"
    failed_pattern = r"(\w+-\d+).*?FAILED"

    passed_scenarios = re.findall(passed_pattern, content)
    failed_scenarios = re.findall(failed_pattern, content)

    return {
        "passed": passed_scenarios,
        "failed": failed_scenarios,
        "total": len(passed_scenarios) + len(failed_scenarios),
    }


def update_test_script_file(results: Dict, test_script_path: str):
    """更新測試劇本文件"""
    script_path = Path(test_script_path)

    if not script_path.exists():
        print(f"測試劇本文件不存在: {test_script_path}")
        return

    content = script_path.read_text(encoding="utf-8")

    # 更新測試執行摘要表
    today = datetime.now().strftime("%Y-%m-%d")
    total = results.get("total", 100)
    passed = len(results.get("passed", []))
    failed = len(results.get("failed", []))
    pass_rate = f"{(passed/total*100):.1f}%" if total > 0 else "0%"

    # 更新第1輪測試記錄
    summary_pattern = r"\| 第 1 輪  \| -        \| -      \| -        \| v3\.2     \| 100      \| -    \| -    \| 100    \| -      \| 待執行 \|"
    replacement = f"| 第 1 輪  | {today} | Daniel Chung | 本地開發環境 | v3.2     | {total}      | {passed}    | {failed}    | {total - passed - failed}    | {pass_rate}      | 已完成 |"

    content = re.sub(summary_pattern, replacement, content)

    # 更新各類別的統計
    # 這裡需要根據實際結果更新每個場景的狀態
    # 由於解析複雜，先更新摘要表

    script_path.write_text(content, encoding="utf-8")
    print(f"已更新測試劇本文件: {test_script_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python parse_test_results.py <pytest_output_file> [test_script_path]")
        sys.exit(1)

    output_file = sys.argv[1]
    test_script_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "docs/系统设计文档/核心组件/Agent平台/archive/testing/文件編輯Agent語義路由測試劇本-v2.md"
    )

    results = parse_pytest_output(output_file)
    print(f"解析結果: 通過 {len(results['passed'])}, 失敗 {len(results['failed'])}, 總計 {results['total']}")

    update_test_script_file(results, test_script_path)
