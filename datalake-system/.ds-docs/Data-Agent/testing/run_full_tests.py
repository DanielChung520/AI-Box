#!/usr/bin/env python3
"""
Data-Agent 100 場景完整測試腳本
會持續優化直到全部通過

若在非 TTY 環境出現「stty: 標準輸入: 不希望的裝置輸出入控制 (ioctl)」可忽略；
  欲抑制可改為：python3 run_full_tests.py < /dev/null

分類執行（建議，避免單次逾時）：
  --list-categories           列出類別與場景數
  --category A                僅執行 A（料件主檔，10 場景）
  --category A,B               僅執行 A 與 B
  --category B                僅執行 B（庫存，15 場景）
  ... 依此類推，最後可合併各類別報告。
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import httpx

# 100 場景測試清單
TEST_CASES = []

# A. 料件主檔查詢 (A01-A10)
TEST_CASES.extend(
    [
        ("A01", "查詢料號 10-0001 的品名和規格"),
        ("A02", "列出所有料件"),
        ("A03", "有多少種料件"),
        ("A04", "查詢所有料件的品名"),
        ("A05", "料號 10-0001 是什麼"),
        ("A06", "查詢料號開頭為 10- 的成品"),
        ("A07", "查詢所有原料"),
        ("A08", "查詢庫存單位為 PCS 的料號"),
        ("A09", "查詢料號 RM01-001 的資訊"),
        ("A10", "按來源碼統計料件數量"),
    ]
)

# B. 庫存查詢 (B01-B15)
TEST_CASES.extend(
    [
        ("B01", "查詢 W01 倉庫的庫存"),
        ("B02", "計算各倉庫的總庫存量"),
        ("B03", "查詢料號 10-0001 的庫存信息"),
        ("B04", "列出所有負庫存的物料"),
        ("B05", "列出前 10 個庫存量最多的物料"),
        ("B06", "統計 W03 成品倉的總庫存量"),
        ("B07", "計算各倉庫的平均庫存量"),
        ("B08", "查詢庫存為 0 的料號"),
        ("B09", "原料倉存貨總額"),
        ("B10", "成品倉各料號庫存"),
        ("B11", "W02 倉有多少庫存"),
        ("B12", "各倉庫庫存數量統計"),
        ("B13", "查詢料號 RM01-003 的庫存"),
        ("B14", "庫存量最高的 5 個物料"),
        ("B15", "找出庫存最少的 10 個料號"),
    ]
)

# C. 交易記錄查詢 (C01-C15)
TEST_CASES.extend(
    [
        ("C01", "查詢 2024 年有多少筆採購進貨"),
        ("C02", "查詢所有採購進貨交易"),
        ("C03", "查詢 W04 倉庫的進貨記錄"),
        ("C04", "查詢 2024 年 1 月的交易記錄"),
        ("C05", "最近 30 天的進貨"),
        ("C06", "計算 2024 年採購總數量"),
        ("C07", "查詢所有銷貨記錄"),
        ("C08", "2024 年銷售出庫筆數"),
        ("C09", "查詢完工入庫記錄"),
        ("C10", "查詢生產領料記錄"),
        ("C11", "查詢庫存報廢記錄"),
        ("C12", "按交易類型統計數量"),
        ("C13", "查詢料號 10-0001 的所有交易"),
        ("C14", "查詢某來源單號的交易"),
        ("C15", "查詢某倉庫的交易趨勢"),
    ]
)

# D. 供應商查詢 (D01-D08)
TEST_CASES.extend(
    [
        ("D01", "查詢所有供應商"),
        ("D02", "供應商 VND001 的聯絡人是誰"),
        ("D03", "查詢供應商 VND003 的詳細資訊"),
        ("D04", "統計供應商數量"),
        ("D05", "查詢所有供應商名稱"),
        ("D06", "查詢電話為 02-xxxx 的供應商"),
        ("D07", "查詢聯絡人為 張先生的供應商"),
        ("D08", "按供應商類型統計"),
    ]
)

# E. 採購單查詢 (E01-E15)
TEST_CASES.extend(
    [
        ("E01", "查詢所有採購單"),
        ("E02", "按供應商統計採購單數量"),
        ("E03", "2024 年有多少筆採購單"),
        ("E04", "查詢供應商 VND001 的採購單"),
        ("E05", "按月份統計採購單數量"),
        ("E06", "查詢採購單 PO-2024010001 的明細"),
        ("E07", "查詢料號 10-0001 的採購數量"),
        ("E08", "查詢已交貨數量"),
        ("E09", "查詢所有收料記錄"),
        ("E10", "查詢採購單 PO-2024010001 的收料記錄"),
        ("E11", "查詢料號 10-0001 的收料數量"),
        ("E12", "查詢最近 10 筆採購單"),
        ("E13", "查詢採購人員的採購單"),
        ("E14", "計算採購單總數量"),
        ("E15", "查詢預計到貨日為 2024-01-15 的採購單"),
    ]
)

# F. 客戶查詢 (F01-F08)
TEST_CASES.extend(
    [
        ("F01", "查詢所有客戶"),
        ("F02", "客戶 D003 的聯絡人是誰"),
        ("F03", "查詢客戶 D010 的詳細資訊"),
        ("F04", "統計客戶數量"),
        ("F05", "查詢所有客戶名稱"),
        ("F06", "查詢電話為 0x-xxxx 的客戶"),
        ("F07", "查詢聯絡人為 李小姐的客戶"),
        ("F08", "查詢客戶名稱包含 企業 的客戶"),
    ]
)

# G. 訂單查詢 (G01-G15)
TEST_CASES.extend(
    [
        ("G01", "查詢所有訂單"),
        ("G02", "統計每個客户的訂單數量"),
        ("G03", "查詢最近 10 筆訂單"),
        ("G04", "客戶 D003 的訂單"),
        ("G05", "統計未出貨訂單數量"),
        ("G06", "查詢已出貨訂單"),
        ("G07", "2024 年有多少筆訂單"),
        ("G08", "按月份統計訂單數量"),
        ("G09", "查詢訂單 SO-2024010001 的明細"),
        ("G10", "查詢訂單 SO-2024010001 的總金額"),
        ("G11", "查詢料號 10-0001 的訂購數量"),
        ("G12", "查詢已出貨數量"),
        ("G13", "按客户統計訂單金額"),
        ("G14", "查詢部分出貨的訂單"),
        ("G15", "查詢業務人員的訂單"),
    ]
)

# H. 價格查詢 (H01-H08)
TEST_CASES.extend(
    [
        ("H01", "查詢料號 10-0001 的單價"),
        ("H02", "料號 10-0001 的最新報價"),
        ("H03", "所有料件的價格列表"),
        ("H04", "查詢已批准的訂價"),
        ("H05", "查詢待批准的訂價"),
        ("H06", "查詢料號 10-0001 的歷史價格"),
        ("H07", "計算料號的平均價格"),
        ("H08", "查詢有效期內的價格"),
    ]
)

# I. 倉庫儲位查詢 (I01-I05)
TEST_CASES.extend(
    [
        ("I01", "查詢 W01 倉庫的所有儲位"),
        ("I02", "儲位 L01-W01-01 的庫存"),
        ("I03", "查詢所有倉庫代號"),
        ("I04", "W03 成品倉的儲位列表"),
        ("I05", "查詢原料倉的代號"),
    ]
)

# J. 異常處理 (J01-J10) — 對齊 Data-Agent-100場景測試計劃.md
TEST_CASES.extend(
    [
        ("J01", "查詢不存在的料號 XYZ-999"),
        ("J02", "查詢不存在的倉庫 W99"),
        ("J03", "查詢不存在的訂單 XYZ-999"),
        ("J04", "從料件表刪除所有資料"),
        ("J05", ""),  # 缺少必要參數：空查詢
        ("J06", "刪除所有料件"),
        ("J07", "查詢料號 10-0001' OR '1'='1"),
        ("J08", "查詢 2030 年的採購進貨"),
        ("J09", "查詢料號 @#$%^&*"),
        ("J10", "列出所有料件前 999999 筆"),
    ]
)

# 類別代碼與名稱（對齊 Data-Agent-100場景測試計劃.md 0.2）
CATEGORY_NAMES = {
    "A": "料件主檔查詢",
    "B": "庫存查詢",
    "C": "交易記錄查詢",
    "D": "供應商查詢",
    "E": "採購單查詢",
    "F": "客戶查詢",
    "G": "訂單查詢",
    "H": "價格查詢",
    "I": "倉庫儲位查詢",
    "J": "異常處理",
}


def _is_exception_test(test_id: str) -> bool:
    """J04-J07 預期 API 返回錯誤為通過；J01-J03/J08-J10 為邊界/正常查詢。"""
    return test_id in ("J04", "J05", "J06", "J07")


async def run_test(client: httpx.AsyncClient, test_id: str, query: str, expected_rows: str = None):
    """執行單個測試"""
    start_time = time.time()
    try:
        payload = {
            "task_id": f"test_{test_id}",
            "task_type": "data_query",
            "task_data": {
                "action": "execute_structured_query",
                "natural_language_query": query,
            },
        }
        # J05 空查詢：不傳 natural_language_query 或傳空
        if test_id == "J05":
            payload["task_data"] = {"action": "execute_structured_query"}

        response = await client.post(
            "http://localhost:8004/execute",
            json=payload,
            timeout=120.0,
        )
        elapsed = (time.time() - start_time) * 1000
        result = response.json()
        status = result.get("status", "")
        inner_result = result.get("result") or {}
        if isinstance(inner_result, dict):
            actual_result = inner_result.get("result") or {}
            error_msg = inner_result.get("error", "")
        else:
            actual_result = {}
            error_msg = str(inner_result) if inner_result else ""

        sql = (actual_result or {}).get("sql_query", "")
        row_count = (actual_result or {}).get("row_count")

        # 異常場景 J04-J07：預期返回錯誤為通過
        if _is_exception_test(test_id):
            success = status in ("failed", "error") or bool(error_msg)
        else:
            # 一般場景：有 SQL 且 row_count 有值（可為 0）
            success = bool(sql and sql.strip()) and row_count is not None

        return {
            "test_id": test_id,
            "query": query or "(空查詢)",
            "sql": sql,
            "row_count": row_count,
            "elapsed_ms": round(elapsed, 2),
            "success": success,
            "error": error_msg or None,
        }
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        return {
            "test_id": test_id,
            "query": query or "(空查詢)",
            "sql": "",
            "row_count": None,
            "elapsed_ms": round(elapsed, 2),
            "success": False,
            "error": str(e),
        }


async def run_all_tests(limit: int = 0, categories: list[str] | None = None):
    """執行測試。limit>0 僅執行前 N 個；categories 為類別代碼列表（如 ['A','B']）時僅執行該類別。"""
    cases = TEST_CASES
    if categories:
        cases = [(tid, q) for tid, q in cases if tid and tid[0] in categories]
    if limit > 0:
        cases = cases[:limit]
    results = []
    async with httpx.AsyncClient() as client:
        current_category = ""
        for test_id, query in cases:
            category = test_id[0]
            if category != current_category:
                current_category = category
                print(f"\n{'=' * 70}")
                print(f"類別 {category}")
                print(f"{'=' * 70}")

            result = await run_test(client, test_id, query)
            results.append(result)

            status = "✅" if result["success"] else "❌"
            print(f"{status} {test_id}: rows={result['row_count']} ({result['elapsed_ms']:.0f}ms)")

    return results


def analyze_results(results):
    """分析測試結果"""
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    pct = (passed / total * 100) if total else 0

    print(f"\n{'=' * 70}")
    print(f"測試摘要: {passed}/{total} 通過 ({pct:.1f}%)")
    print(f"{'=' * 70}")

    # 按類別統計
    categories = {}
    for r in results:
        cat = r["test_id"][0]
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "failed": []}
        categories[cat]["total"] += 1
        if r["success"]:
            categories[cat]["passed"] += 1
        else:
            categories[cat]["failed"].append(r["test_id"])

    print("\n按類別:")
    for cat in sorted(categories.keys()):
        c = categories[cat]
        rate = (c["passed"] / c["total"] * 100) if c["total"] else 0
        print(f"  {cat}: {c['passed']}/{c['total']} ({rate:.0f}%)", end="")
        if c["failed"]:
            print(f" ❌ {', '.join(c['failed'])}")
        else:
            print()

    return categories


def generate_report(results, iteration=1, subtitle=""):
    """生成測試報告（含摘要、100 場景明細、失敗分析、改進建議）。"""
    total = len(results)
    passed = sum(1 for r in results if r["success"])

    report = f"""# Data-Agent 100 場景測試報告{subtitle}

**測試日期**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**適用**: 新結構（schema_registry 載入、無硬編碼表名/路徑）
**通過率**: {passed}/{total} ({passed / total * 100:.1f}%)

---

## 1. 測試摘要

| 類別 | 總數 | 通過 | 失敗 | 通過率 |
|------|------|------|------|--------|
"""

    categories = {}
    for r in results:
        cat = r["test_id"][0]
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "failed": []}
        categories[cat]["total"] += 1
        if r["success"]:
            categories[cat]["passed"] += 1
        else:
            categories[cat]["failed"].append(r["test_id"])

    for cat in sorted(categories.keys()):
        c = categories[cat]
        rate = c["passed"] / c["total"] * 100
        report += f"| {cat}. | {c['total']} | {c['passed']} | {len(c['failed'])} | {rate:.0f}% |\n"

    report += f"| **合計** | **{total}** | **{passed}** | **{total - passed}** | **{passed / total * 100:.1f}%** |\n\n"

    # 2. 100 場景詳細列表
    report += "## 2. 場景詳細列表\n\n"
    report += "| 場景ID | 自然語言 | 生成SQL | 返回筆數 | 耗時(ms) | 狀態 | 失敗原因 |\n"
    report += "|--------|----------|---------|----------|----------|------|----------|\n"
    for r in results:
        q_short = (r["query"] or "")[:36] + ("..." if len(r["query"] or "") > 36 else "")
        sql_short = (r["sql"] or "")[:50] + ("..." if len(r["sql"] or "") > 50 else "")
        rows = r["row_count"] if r["row_count"] is not None else "-"
        status_str = "通過" if r["success"] else "失敗"
        err = (r["error"] or "")[:30] + ("..." if len(r["error"] or "") > 30 else "") if r["error"] else ""
        report += f"| {r['test_id']} | {q_short} | {sql_short} | {rows} | {r['elapsed_ms']} | {status_str} | {err} |\n"

    # 3. 失敗場景分析
    failed_tests = [r for r in results if not r["success"]]
    if failed_tests:
        report += "\n## 3. 失敗場景分析\n\n"
        report += "| 場景ID | 自然語言 | 錯誤/原因 |\n"
        report += "|--------|----------|------------|\n"
        for r in failed_tests:
            err = (r["error"] or "無錯誤訊息")[:60]
            report += f"| {r['test_id']} | {(r['query'] or '')[:40]}... | {err} |\n"
    else:
        report += "\n## 3. 失敗場景分析\n\n無失敗場景。\n"

    # 4. 改進建議
    report += "\n## 4. 改進建議\n\n"
    if failed_tests:
        report += "- 針對上表失敗場景檢查：SQL 語義、schema_registry 表/欄位對應、LLM prompt。\n"
        report += "- 異常類 J04-J07 預期返回錯誤；若返回成功需加強危險語句與參數校驗。\n"
    else:
        report += "- 全部通過，可考慮增加邊界與效能回歸測試。\n"

    return report


# 統一報告用：合併結果的 JSON 預設路徑
DEFAULT_RESULTS_JSON = (
    "/home/daniel/ai-box/datalake-system/.ds-docs/Data-Agent/testing/"
    "Data-Agent-100場景-合併結果.json"
)


def load_merged_results(path: str) -> list:
    """從 JSON 載入已合併的結果列表。"""
    if not path or not Path(path).exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def save_merged_results(path: str, results: list) -> None:
    """將結果列表寫入 JSON（依 test_id 排序）。"""
    by_id = {r["test_id"]: r for r in results}
    ordered = [by_id[tid] for tid, _ in TEST_CASES if tid in by_id]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Data-Agent 100 場景測試（可依類別分次執行，結果可合併為統一報告）",
        epilog="範例: --category A --output-json 結果.json | 最後 --from-json 結果.json --report-only",
    )
    parser.add_argument("--limit", type=int, default=0, help="僅執行前 N 個場景（0=不限制）")
    parser.add_argument(
        "--category",
        type=str,
        default="",
        help="僅執行指定類別，可多個逗號分隔，如 A 或 A,B,C",
    )
    parser.add_argument("--list-categories", action="store_true", help="列出類別代碼與場景數後結束")
    parser.add_argument(
        "--output-json",
        type=str,
        default="",
        help="將本次結果合併寫入此 JSON；與 --category 搭配可分批跑完後做統一報告",
    )
    parser.add_argument(
        "--from-json",
        type=str,
        default="",
        help="從 JSON 載入結果（與 --report-only 同用可只產統一報告）",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="僅從 --from-json 載入結果並產出報告，不執行測試",
    )
    args = parser.parse_args()

    if args.list_categories:
        print("類別代碼與場景數（對齊測試計劃 0.2）:\n")
        for code, name in CATEGORY_NAMES.items():
            n = sum(1 for tid, _ in TEST_CASES if tid and tid[0] == code)
            print(f"  {code}: {name} ({n} 場景)")
        print(f"\n合計: {len(TEST_CASES)} 場景")
        raise SystemExit(0)

    # 僅產報告：從 JSON 載入 → 產出統一報告
    if args.report_only and args.from_json:
        json_path = args.from_json
        results = load_merged_results(json_path)
        if not results:
            print(f"無結果可載入: {json_path}")
            raise SystemExit(1)
        # 依 TEST_CASES 順序排列
        by_id = {r["test_id"]: r for r in results}
        ordered = [by_id[tid] for tid, _ in TEST_CASES if tid in by_id]
        report = generate_report(ordered, 1, "（新結構・統一報告）")
        date_str = datetime.now().strftime("%Y%m%d")
        report_path = (
            "/home/daniel/ai-box/datalake-system/.ds-docs/Data-Agent/testing/"
            f"Data-Agent-100場景測試報告-新結構-統一-{date_str}.md"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"統一報告已保存: {report_path}（共 {len(ordered)} 場景）")
        raise SystemExit(0)

    categories_list = [c.strip().upper() for c in args.category.split(",") if c.strip()] or None

    print("=" * 70)
    print("Data-Agent 100 場景測試（新結構）")
    print("=" * 70)
    if categories_list:
        names = [f"{c}({CATEGORY_NAMES.get(c, '?')})" for c in categories_list]
        print(f"僅執行類別: {', '.join(names)}\n")
    if args.limit > 0:
        print(f"僅執行前 {args.limit} 個場景\n")

    results = asyncio.run(run_all_tests(limit=args.limit, categories=categories_list))
    analyze_results(results)

    # 合併寫入 JSON（與既有結果依 test_id 合併）
    if args.output_json:
        existing = load_merged_results(args.output_json)
        current_ids = {r["test_id"] for r in results}
        merged = [r for r in existing if r["test_id"] not in current_ids] + results
        save_merged_results(args.output_json, merged)
        print(f"\n結果已合併寫入: {args.output_json}（目前共 {len(merged)} 筆）")

    subtitle = "（新結構）"
    if categories_list:
        subtitle += f" 類別{''.join(categories_list)}"
    report = generate_report(results, 1, subtitle)
    print(report)

    date_str = datetime.now().strftime("%Y%m%d")
    slug = "".join(categories_list) if categories_list else "全部"
    report_path = (
        f"/home/daniel/ai-box/datalake-system/.ds-docs/Data-Agent/testing/"
        f"Data-Agent-100場景測試報告-新結構-{slug}-{date_str}.md"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n報告已保存: {report_path}")
