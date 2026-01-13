# 代碼功能說明: 生成整合測試報告
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""生成整合測試報告"""

import json
import sys
from pathlib import Path

# 獲取測試結果文件
test_dir = Path(__file__).parent
result_file = test_dir / "integration_test_results.json"

if not result_file.exists():
    print(f"❌ 測試結果文件不存在: {result_file}")
    print("   請先運行測試: python3 test_integration_scenarios.py")
    sys.exit(1)

# 讀取測試結果
with open(result_file, "r", encoding="utf-8") as f:
    data = json.load(f)

summary = data.get("summary", {})
results = data.get("results", [])

# 生成Markdown報告
report_file = test_dir / "INTEGRATION_TEST_REPORT.md"

with open(report_file, "w", encoding="utf-8") as f:
    f.write("# 庫管員Agent整合測試報告\n\n")
    f.write("**測試日期**：2026-01-13\n")
    f.write("**測試版本**：1.0.0\n\n")
    f.write("---\n\n")

    # 執行摘要
    f.write("## 執行摘要\n\n")
    f.write(f"- **總測試數**：{summary.get('total', 0)}\n")
    f.write(f"- **通過數**：{summary.get('passed', 0)} ✅\n")
    f.write(f"- **失敗數**：{summary.get('failed', 0)} ❌\n")
    f.write(f"- **通過率**：{summary.get('pass_rate', 0):.1f}%\n\n")
    f.write("---\n\n")

    # 詳細結果
    f.write("## 詳細測試結果\n\n")
    for i, result in enumerate(results, 1):
        test_name = result.get("test_name", f"測試 {i}")
        status = result.get("status", "未知")
        instruction = result.get("instruction", "")
        error = result.get("error")

        f.write(f"### {i}. {test_name}\n\n")
        f.write(f"**指令**：`{instruction}`\n\n")
        f.write(f"**狀態**：{status}\n\n")

        if error:
            f.write(f"**錯誤**：{error}\n\n")

        f.write("---\n\n")

    # 失敗測試摘要
    failed_tests = [r for r in results if "❌" in r.get("status", "")]
    if failed_tests:
        f.write("## 失敗測試摘要\n\n")
        for result in failed_tests:
            test_name = result.get("test_name", "Unknown")
            error = result.get("error", "No error message")
            f.write(f"- **{test_name}**：{error}\n\n")

print(f"✅ 測試報告已生成: {report_file}")
