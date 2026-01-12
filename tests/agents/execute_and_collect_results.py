# 代碼功能說明: 執行測試並收集結果
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""執行文件編輯 Agent 語義路由測試並收集結果

使用 pytest 執行測試，測試腳本會自動保存結果到 JSON 文件
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def run_pytest_tests(limit: Optional[int] = None) -> int:
    """使用 pytest 執行測試"""
    test_file = Path(__file__).parent / "test_file_editing_agent_routing.py"
    project_root = Path(__file__).resolve().parent.parent.parent

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(test_file),
        "-v",
        "-s",
        "--tb=short",
    ]

    if limit:
        # 如果有限制，只執行前N個場景
        scenario_filters = [f"scenario{i}" for i in range(limit)]
        cmd.extend(["-k", " or ".join(scenario_filters)])

    print(f"\n{'='*80}")
    print("開始執行文件編輯 Agent 語義路由測試")
    print(f"測試文件: {test_file}")
    if limit:
        print(f"限制場景數: {limit}")
    else:
        print("總場景數: 100")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    result = subprocess.run(
        cmd,
        cwd=project_root,
    )

    print(f"\n{'='*80}")
    print("測試執行完成")
    print(f"退出代碼: {result.returncode}")
    print(f"{'='*80}\n")

    return result.returncode


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="執行文件編輯 Agent 語義路由測試")
    parser.add_argument("--limit", type=int, default=None, help="限制場景數量（用於測試）")
    args = parser.parse_args()

    exit_code = run_pytest_tests(limit=args.limit)

    print("\n注意：測試腳本會自動保存結果到 test_reports/ 目錄")
    print("使用 update_test_record_table.py 腳本來更新測試記錄表")

    return exit_code


if __name__ == "__main__":
    exit(main())
