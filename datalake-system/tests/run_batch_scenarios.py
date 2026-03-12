# 代碼功能說明: 從 500 場景中選取 N 個分散場景，批次測試 DT-Agent 並收集結果（含 QueryGuard 攔截統計）
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

"""
用法:
  cd datalake-system
  PYTHONPATH=. python tests/run_batch_scenarios.py           # 預設 100 場景
  PYTHONPATH=. python tests/run_batch_scenarios.py --count 50
  PYTHONPATH=. python tests/run_batch_scenarios.py --count 200
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

import httpx

DT_AGENT_URL = "http://localhost:8005/api/v1/dt-agent/execute"
SCENARIO_FILE = Path(__file__).parent / "500場景_JP適用版.json"
TIMEOUT = 120.0  # 單筆最大等待秒數


def select_n(scenarios: list[dict], n: int = 100) -> list[dict]:
    """從各 category 中均勻抽樣，共 n 個。"""
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for s in scenarios:
        by_cat[s["category"]].append(s)

    per_cat = n // len(by_cat)
    remainder = n - per_cat * len(by_cat)

    selected: list[dict] = []
    cat_order = sorted(by_cat.keys())
    for i, cat in enumerate(cat_order):
        items = by_cat[cat]
        take = per_cat + (1 if i < remainder else 0)
        # 均勻間隔取樣
        step = max(1, len(items) // take) if take > 0 else 1
        picked = [items[j * step] for j in range(take) if j * step < len(items)]
        # 補足
        while len(picked) < take and len(picked) < len(items):
            for item in items:
                if item not in picked:
                    picked.append(item)
                    break
        selected.extend(picked)

    return selected[:n]


def run_test(client: httpx.Client, scenario: dict, idx: int, total: int) -> dict:
    """執行單筆測試，回傳結果摘要。"""
    sid = scenario["id"]
    cat = scenario["category"]
    question = scenario["question"]

    # 聚合類用 summary mode，其他用 list
    return_mode = "summary" if cat in ("AGG", "GROUP") else "list"

    payload = {
        "task_id": f"batch-{sid}",
        "task_type": "simple_query",
        "task_data": {
            "nlq": question,
            "module": "tiptop_jp",
            "return_mode": return_mode,
        },
    }

    t0 = time.perf_counter()
    try:
        resp = client.post(DT_AGENT_URL, json=payload, timeout=TIMEOUT)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        resp.raise_for_status()
        data = resp.json()

        meta = data.get("metadata", {})
        error_code = data.get("error_code")
        guard_type = meta.get("guard_type")

        return {
            "idx": idx,
            "id": sid,
            "category": cat,
            "question": question,
            "success": data.get("success", False),
            "intent": meta.get("matched_intent", "N/A"),
            "confidence": round(meta.get("intent_confidence") or 0, 4),
            "sql": data.get("sql", ""),
            "sqlglot_valid": meta.get("sqlglot_valid", False),
            "row_count": data.get("row_count") or 0,
            "model": meta.get("model_used", "N/A"),
            "retries": meta.get("retries", 0),
            "escalated": meta.get("escalated", False),
            "total_time_ms": round(meta.get("total_time_ms") or elapsed_ms, 1),
            "error_code": error_code,
            "guard_type": guard_type,
            "clarification_needed": data.get("clarification_needed"),
            "suggestion": data.get("suggestion"),
            "error": data.get("message") or None,
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return {
            "idx": idx,
            "id": sid,
            "category": cat,
            "question": question,
            "success": False,
            "intent": "ERROR",
            "confidence": 0,
            "sql": "",
            "sqlglot_valid": False,
            "row_count": 0,
            "model": "N/A",
            "retries": 0,
            "escalated": False,
            "total_time_ms": round(elapsed_ms, 1),
            "error_code": "HTTP_ERROR",
            "guard_type": None,
            "clarification_needed": None,
            "suggestion": None,
            "error": str(e),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="DT-Agent 批次場景測試")
    parser.add_argument("--count", "-n", type=int, default=100, help="測試場景數量（預設 100）")
    args = parser.parse_args()
    n = args.count

    with SCENARIO_FILE.open("r", encoding="utf-8") as f:
        all_scenarios = json.load(f)

    selected = select_n(all_scenarios, n=n)
    actual_n = len(selected)
    print(f"=== DT-Agent 批次測試：{actual_n} 場景 ===\n")

    # 按 category 統計選取數量
    cat_counts = Counter(s["category"] for s in selected)
    for cat in sorted(cat_counts):
        print(f"  {cat}: {cat_counts[cat]}")
    print()

    results: list[dict] = []
    client = httpx.Client(timeout=TIMEOUT)

    try:
        for i, scenario in enumerate(selected, 1):
            print(
                f"[{i:3d}/{actual_n}] {scenario['id']} | {scenario['question'][:40]}...",
                end=" ",
                flush=True,
            )
            result = run_test(client, scenario, i, actual_n)
            results.append(result)

            # 判斷顯示狀態
            if result.get("guard_type"):
                status = "🛡️"  # 被 QueryGuard 攔截
                extra = f"guard={result['guard_type']}"
            elif result["success"] and result["sqlglot_valid"]:
                status = "✅"
                extra = f"rows={result['row_count']:>5}"
            elif result["success"] and not result["sqlglot_valid"]:
                status = "⚠️"
                extra = f"rows={result['row_count']:>5}"
            else:
                status = "❌"
                extra = f"err={result.get('error_code', 'UNKNOWN')}"

            print(f"{status} {result['total_time_ms']:>8.0f}ms | {extra} | {result['intent']}")
    finally:
        client.close()

    # === 統計報告 ===
    print("\n" + "=" * 110)
    print("統計報告")
    print("=" * 110)

    total = len(results)
    success_count = sum(1 for r in results if r["success"])
    guard_count = sum(1 for r in results if r.get("guard_type"))
    valid_sql_count = sum(1 for r in results if r["sqlglot_valid"])
    has_rows = sum(1 for r in results if r["row_count"] > 0)
    escalated_count = sum(1 for r in results if r["escalated"])
    retried_count = sum(1 for r in results if r["retries"] > 0)
    exec_fail_count = sum(1 for r in results if not r["success"] and not r.get("guard_type"))

    times = [r["total_time_ms"] for r in results]
    avg_time = sum(times) / len(times) if times else 0
    min_time = min(times) if times else 0
    max_time = max(times) if times else 0
    sorted_times = sorted(times)
    p50 = sorted_times[len(sorted_times) // 2] if sorted_times else 0
    p95 = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0

    # 只看「實際執行 SQL」的場景（排除被 guard 攔截的）
    executed_results = [r for r in results if not r.get("guard_type")]
    exec_total = len(executed_results)
    exec_success = sum(1 for r in executed_results if r["success"])
    exec_times = [r["total_time_ms"] for r in executed_results]
    exec_avg = sum(exec_times) / len(exec_times) if exec_times else 0

    print(f"\n📊 總覽：")
    print(f"  總場景數:           {total}")
    print(
        f"  成功（含 guard）:   {success_count + guard_count}/{total} ({(success_count + guard_count) / total * 100:.1f}%)"
    )
    print(f"  SQL 成功:           {success_count}/{total} ({success_count / total * 100:.1f}%)")
    print(f"  🛡️ Guard 攔截:      {guard_count}/{total} ({guard_count / total * 100:.1f}%)")
    print(f"  ❌ 執行失敗:        {exec_fail_count}/{total} ({exec_fail_count / total * 100:.1f}%)")
    print(f"  SQL 有效:           {valid_sql_count}/{exec_total} (of executed)")
    print(f"  有資料回傳:         {has_rows}/{exec_total} (of executed)")
    print(f"  需 escalate:        {escalated_count}/{total}")
    print(f"  需 retry:           {retried_count}/{total}")

    # Guard 類型分布
    guard_types = Counter(r.get("guard_type") for r in results if r.get("guard_type"))
    if guard_types:
        print(f"\n🛡️ Guard 攔截類型分布：")
        for gt, cnt in guard_types.most_common():
            print(f"  {gt}: {cnt}")

    print(f"\n⏱️ 耗時統計（全部，含 guard，ms）：")
    print(f"  平均:  {avg_time:>10.1f}")
    print(f"  最小:  {min_time:>10.1f}")
    print(f"  最大:  {max_time:>10.1f}")
    print(f"  P50:   {p50:>10.1f}")
    print(f"  P95:   {p95:>10.1f}")

    if exec_times:
        exec_sorted = sorted(exec_times)
        exec_p50 = exec_sorted[len(exec_sorted) // 2]
        exec_p95 = exec_sorted[int(len(exec_sorted) * 0.95)]
        print(f"\n⏱️ 耗時統計（僅 SQL 執行場景，ms）：")
        print(f"  平均:  {exec_avg:>10.1f}")
        print(f"  P50:   {exec_p50:>10.1f}")
        print(f"  P95:   {exec_p95:>10.1f}")

    # 按 category 分組統計
    print(f"\n📂 按 Category 統計：")
    print(
        f"  {'Category':<10} {'Count':>5} {'Success':>8} {'Guard':>6} {'Fail':>5} {'ValidSQL':>9} {'HasRows':>8} {'AvgMs':>10}"
    )
    for cat in sorted(cat_counts):
        cat_results = [r for r in results if r["category"] == cat]
        c_total = len(cat_results)
        c_success = sum(1 for r in cat_results if r["success"])
        c_guard = sum(1 for r in cat_results if r.get("guard_type"))
        c_fail = sum(1 for r in cat_results if not r["success"] and not r.get("guard_type"))
        c_valid = sum(1 for r in cat_results if r["sqlglot_valid"])
        c_rows = sum(1 for r in cat_results if r["row_count"] > 0)
        c_avg = sum(r["total_time_ms"] for r in cat_results) / c_total if c_total else 0
        print(
            f"  {cat:<10} {c_total:>5} {c_success:>8} {c_guard:>6} {c_fail:>5} {c_valid:>9} {c_rows:>8} {c_avg:>10.1f}"
        )

    # Guard 攔截場景列表
    guarded = [r for r in results if r.get("guard_type")]
    if guarded:
        print(f"\n🛡️ Guard 攔截場景（{len(guarded)} 個）：")
        for r in guarded:
            print(f"  {r['id']} | {r['question'][:50]}")
            print(f"    intent={r['intent']} guard={r['guard_type']}")
            if r.get("suggestion"):
                print(f"    suggestion: {r['suggestion'][:100]}")

    # 執行失敗場景列表
    failures = [r for r in results if not r["success"] and not r.get("guard_type")]
    if failures:
        print(f"\n❌ 執行失敗場景（{len(failures)} 個）：")
        for r in failures:
            print(f"  {r['id']} | {r['question'][:50]}")
            print(f"    intent={r['intent']} conf={r['confidence']} sql_valid={r['sqlglot_valid']}")
            if r["error"]:
                print(f"    error: {r['error'][:120]}")
            if r["sql"]:
                print(f"    SQL: {r['sql'][:120]}")

    # 0 rows 場景
    zero_rows = [r for r in results if r["success"] and r["sqlglot_valid"] and r["row_count"] == 0]
    if zero_rows:
        print(f"\n⚠️ 成功但 0 rows（{len(zero_rows)} 個）：")
        for r in zero_rows:
            print(f"  {r['id']} | {r['question'][:50]}")
            print(f"    intent={r['intent']} SQL: {r['sql'][:120]}")

    # 輸出完整 JSON 結果
    output_path = Path(__file__).parent / f"batch_{actual_n}_results.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📄 完整結果已寫入: {output_path}")


if __name__ == "__main__":
    main()
