#!/usr/bin/env python3
# 代碼功能說明: 依序測試所有場景的包裝腳本
# 創建日期: 2026-01-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-09

"""依序測試所有場景的包裝腳本

使用 pytest 運行，但按場景分組依序執行
"""

import subprocess
import sys
from pathlib import Path

# 測試場景列表
SCENARIOS = [
    "FE-011",
    "FE-012",
    "FE-013",
    "FE-014",
    "FE-015",
    "FE-016",
    "FE-017",
    "FE-018",
    "FE-019",
    "FE-020",
    "FE-021",
    "FE-022",
    "FE-023",
    "FE-024",
    "FE-025",
]


def main():
    """依序運行每個場景的所有模型測試"""
    print("=" * 80)
    print("Router LLM 模型比較測試（依序模式 - 按場景分組）")
    print("=" * 80)
    print(f"\n總場景數: {len(SCENARIOS)}")
    print("每個場景測試 6 個模型")
    print(f"總測試次數: {len(SCENARIOS) * 6} = 90 個測試用例")
    print("\n" + "=" * 80)
    print("開始測試...")
    print("=" * 80)

    project_root = Path(__file__).parent.parent.parent
    test_file = project_root / "tests" / "agents" / "test_router_llm_model_comparison_auto.py"

    for idx, scenario_id in enumerate(SCENARIOS, 1):
        print(f"\n{'=' * 80}")
        print(f"[場景 {idx}/{len(SCENARIOS)}] 測試場景: {scenario_id}")
        print("=" * 80)

        # 使用 pytest 運行該場景的所有模型測試
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "-v",
            "-s",
            "-k",
            scenario_id,
            "--tb=short",
        ]

        result = subprocess.run(cmd, cwd=str(project_root))

        if result.returncode != 0:
            print(f"\n⚠️  場景 {scenario_id} 測試完成（部分測試可能失敗）")
        else:
            print(f"\n✅ 場景 {scenario_id} 測試完成")

    print("\n" + "=" * 80)
    print("所有場景測試完成！")
    print("=" * 80)
    print("\n報告已自動生成到: docs/系统设计文档/核心组件/Agent平台/")


if __name__ == "__main__":
    main()
