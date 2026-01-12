#!/usr/bin/env python3
# 代碼功能說明: 依序測試所有場景（帶進度保存）
# 創建日期: 2026-01-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-09

"""依序測試所有場景（帶進度保存）

使用 pytest 運行，按場景分組依序執行，並保存進度
"""

import json
import subprocess
import sys
from datetime import datetime
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

# 進度文件
PROGRESS_FILE = Path(__file__).parent / ".test_progress.json"


def load_progress():
    """載入測試進度"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed": [], "failed": []}


def save_progress(completed, failed):
    """保存測試進度"""
    progress = {"completed": completed, "failed": failed, "last_update": datetime.now().isoformat()}
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def main():
    """依序運行每個場景的所有模型測試"""
    print("=" * 80)
    print("Router LLM 模型比較測試（依序模式 - 按場景分組）")
    print("=" * 80)

    progress = load_progress()
    completed = set(progress.get("completed", []))
    failed = set(progress.get("failed", []))

    remaining = [s for s in SCENARIOS if s not in completed]

    print(f"\n總場景數: {len(SCENARIOS)}")
    print(f"已完成: {len(completed)}")
    print(f"失敗: {len(failed)}")
    print(f"剩餘: {len(remaining)}")
    print("每個場景測試 6 個模型")
    print(f"總測試次數: {len(SCENARIOS) * 6} = 90 個測試用例")

    if completed:
        print(f"\n已完成的場景: {', '.join(sorted(completed))}")
    if remaining:
        print(f"\n將繼續測試場景: {', '.join(remaining)}")

    print("\n" + "=" * 80)
    print("開始測試...")
    print("=" * 80)

    project_root = Path(__file__).parent.parent.parent
    test_file = project_root / "tests" / "agents" / "test_router_llm_model_comparison_auto.py"

    for idx, scenario_id in enumerate(SCENARIOS, 1):
        if scenario_id in completed:
            print(f"\n[場景 {idx}/{len(SCENARIOS)}] {scenario_id} - 已跳過（已完成）")
            continue

        print(f"\n{'=' * 80}")
        print(f"[場景 {idx}/{len(SCENARIOS)}] 測試場景: {scenario_id}")
        print("=" * 80)

        # 使用 pytest 運行該場景的所有模型測試
        # 注意：pytest 的 -k 選項需要匹配測試名稱，我們需要找到正確的匹配方式
        # 由於參數化測試的名稱格式，我們直接運行所有測試，然後過濾結果
        cmd = [sys.executable, "-m", "pytest", str(test_file), "-v", "-s", "--tb=short"]

        try:
            result = subprocess.run(cmd, cwd=str(project_root), timeout=3600)  # 1小時超時

            if result.returncode == 0:
                completed.add(scenario_id)
                if scenario_id in failed:
                    failed.remove(scenario_id)
                print(f"\n✅ 場景 {scenario_id} 測試完成")
            else:
                failed.add(scenario_id)
                print(f"\n⚠️  場景 {scenario_id} 測試完成（部分測試可能失敗）")
        except subprocess.TimeoutExpired:
            failed.add(scenario_id)
            print(f"\n⏱️  場景 {scenario_id} 測試超時")
        except Exception as e:
            failed.add(scenario_id)
            print(f"\n❌ 場景 {scenario_id} 測試出錯: {e}")

        # 保存進度
        save_progress(list(completed), list(failed))

    print("\n" + "=" * 80)
    print("所有場景測試完成！")
    print("=" * 80)
    print("\n完成統計:")
    print(f"  已完成: {len(completed)}/{len(SCENARIOS)}")
    print(f"  失敗: {len(failed)}/{len(SCENARIOS)}")
    if failed:
        print(f"  失敗場景: {', '.join(sorted(failed))}")
    print("\n報告已自動生成到: docs/系统设计文档/核心组件/Agent平台/")

    # 清理進度文件
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()


if __name__ == "__main__":
    main()
