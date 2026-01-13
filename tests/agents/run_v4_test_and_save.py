# 代碼功能說明: 運行 v4 測試並保存結果的包裝腳本
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""運行 v4 測試並保存結果的包裝腳本"""

import subprocess
import sys
from pathlib import Path

# 添加項目根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.agents.test_file_editing_agent_routing_v4 import _test_results, save_test_results


def main():
    """運行測試並保存結果"""
    print("開始運行 v4 測試（50 個 md-editor 場景）...")
    print("=" * 80)

    # 清空結果列表
    _test_results.clear()

    # 運行 pytest
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/agents/test_file_editing_agent_routing_v4.py::TestFileEditingAgentRoutingV4::test_md_editor_routing_v4",
            "-v",
            "--tb=short",
        ],
        cwd=Path(__file__).parent.parent.parent,
    )

    # 保存結果
    if _test_results:
        output_file = save_test_results()
        print(f"\n{'='*80}")
        print("測試摘要")
        print(f"{'='*80}")
        total = len(_test_results)
        passed = sum(1 for r in _test_results if r.get("all_passed", False))
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0

        l1_passed = sum(1 for r in _test_results if r.get("l1_passed", False))
        l2_passed = sum(1 for r in _test_results if r.get("l2_passed", False))
        l3_passed = sum(1 for r in _test_results if r.get("l3_passed", False))
        l4_passed = sum(1 for r in _test_results if r.get("l4_passed", False))
        l5_passed = sum(1 for r in _test_results if r.get("l5_passed", False))

        latencies = [r.get("latency_ms", 0) for r in _test_results if r.get("latency_ms")]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

        print(f"總場景數: {total}")
        print(f"通過: {passed}")
        print(f"失敗: {failed}")
        print(f"通過率: {pass_rate:.2f}%")
        print(f"\nL1-L5 層級通過率:")
        print(f"  L1 語義理解: {(l1_passed / total * 100) if total > 0 else 0:.2f}% ({l1_passed}/{total})")
        print(f"  L2 Intent DSL: {(l2_passed / total * 100) if total > 0 else 0:.2f}% ({l2_passed}/{total})")
        print(f"  L3 Capability: {(l3_passed / total * 100) if total > 0 else 0:.2f}% ({l3_passed}/{total})")
        print(f"  L4 Policy: {(l4_passed / total * 100) if total > 0 else 0:.2f}% ({l4_passed}/{total})")
        print(f"  L5 執行記錄: {(l5_passed / total * 100) if total > 0 else 0:.2f}% ({l5_passed}/{total})")
        print(f"\n性能指標:")
        print(f"  平均響應時間: {avg_latency:.2f}ms")
        print(f"  P95 響應時間: {p95_latency:.2f}ms")
        print(f"\n✅ 測試結果已保存至: {output_file}")
        print(f"{'='*80}\n")
    else:
        print("\n⚠️  未找到測試結果，測試可能未正常執行")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
