#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data-Agent-JP 測試執行器 (簡化版)

功能：
- 執行測試場景並即時顯示進度
- 處理超時和錯誤
- 即時保存部分結果

建立日期: 2026-02-10
建立人: Daniel Chung
"""

import json
import time
import uuid
import httpx
import statistics
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List
from pathlib import Path

DATA_AGENT_ENDPOINT = "http://localhost:8004/jp/execute"
TEST_FILE = Path(__file__).parent / "test_jp_100_scenarios.json"
OUTPUT_FILE = Path(__file__).parent / "reports" / "test_results_partial.json"


def load_scenarios() -> List[Dict]:
    """載入測試場景"""
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("scenarios", []), data.get("summary", {})


def run_single_test(scenario: Dict) -> Dict:
    """執行單一測試"""
    test_id = scenario.get("id", "UNKNOWN")
    nlq = scenario.get("natural_language", "")

    payload = {
        "task_id": str(uuid.uuid4()),
        "task_type": "schema_driven_query",
        "task_data": {"nlq": nlq},
    }

    start_time = time.time()

    try:
        with httpx.Client(timeout=180.0) as client:
            response = client.post(DATA_AGENT_ENDPOINT, json=payload)
            response.raise_for_status()
            result = response.json()

        elapsed = int((time.time() - start_time) * 1000)

        return {
            "test_id": test_id,
            "category": scenario.get("category", ""),
            "complexity": scenario.get("complexity", ""),
            "description": scenario.get("description", ""),
            "natural_language": nlq,
            "status": result.get("status", "unknown"),
            "row_count": result.get("result", {}).get("row_count", 0)
            if result.get("result")
            else 0,
            "sql": result.get("result", {}).get("sql", "") if result.get("result") else "",
            "execution_time_ms": elapsed,
            "token_usage": result.get("result", {}).get("token_usage", {})
            if result.get("result")
            else {},
            "error": result.get("message", "") if result.get("status") == "error" else "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        elapsed = int((time.time() - start_time) * 1000)
        return {
            "test_id": test_id,
            "category": scenario.get("category", ""),
            "complexity": scenario.get("complexity", ""),
            "description": scenario.get("description", ""),
            "natural_language": nlq,
            "status": "error",
            "row_count": 0,
            "execution_time_ms": elapsed,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def main():
    """主函數"""
    scenarios, summary_info = load_scenarios()
    total = len(scenarios)

    print(f"🚀 Data-Agent-JP 測試執行器")
    print(f"📁 測試檔案: {TEST_FILE}")
    print(f"📊 總測試數: {total}")
    print("")

    results = []
    passed = 0
    failed = 0
    errors = 0
    total_tokens = 0
    total_rows = 0

    start_time = time.time()

    for idx, scenario in enumerate(scenarios, 1):
        test_id = scenario.get("id", f"TEST_{idx}")
        category = scenario.get("category", "")

        result = run_single_test(scenario)
        results.append(result)

        # 更新計數
        if result["status"] == "success":
            passed += 1
            status_icon = "✅"
        elif result["status"] == "error":
            errors += 1
            status_icon = "❌"
        else:
            failed += 1
            status_icon = "⚠️"

        tokens = result.get("token_usage", {}).get("total_tokens", 0)
        total_tokens += tokens
        total_rows += result.get("row_count", 0)

        # 即時顯示
        elapsed = result.get("execution_time_ms", 0)
        print(
            f"[{idx:03d}/{total}] {test_id} | {status_icon} | rows={result.get('row_count', 0):>6} | {elapsed:>4}ms | tokens={tokens:>5}"
        )

        # 每 10 個保存一次
        if idx % 10 == 0:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "progress": idx,
                        "total": total,
                        "passed": passed,
                        "failed": failed,
                        "errors": errors,
                        "results": results,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            print(f"   📁 [進度 {idx}/{total}] 已保存")
            sys.stdout.flush()

    elapsed_total = time.time() - start_time

    # 最終報告
    print("\n" + "=" * 70)
    print("📊 測試摘要")
    print("=" * 70)
    print(f"總測試數:      {total}")
    print(f"✅ 通過:       {passed}")
    print(f"❌ 錯誤:       {errors}")
    print(f"⚠️  失敗:       {failed}")
    print(f"通過率:        {passed / total * 100:.1f}%")
    print(f"總耗時:        {elapsed_total:.1f} 秒")
    print(f"平均耗時:      {elapsed_total / total * 1000:.0f} ms")
    print(f"總消耗 Token:  {total_tokens:,}")
    print(f"總返回行數:    {total_rows:,}")
    print("=" * 70)

    # 保存完整結果
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": {
                    "total_tests": total,
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "pass_rate": f"{passed / total * 100:.1f}%",
                    "total_duration_seconds": elapsed_total,
                    "avg_duration_ms": elapsed_total / total * 1000,
                    "total_tokens": total_tokens,
                    "total_rows": total_rows,
                },
                "scenarios_summary": summary_info,
                "results": results,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n📄 完整報告: {OUTPUT_FILE}")

    return 0 if errors == 0 and failed == 0 else 1


if __name__ == "__main__":
    exit(main())
