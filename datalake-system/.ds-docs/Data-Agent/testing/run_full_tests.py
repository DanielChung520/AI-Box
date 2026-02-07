#!/usr/bin/env python3
"""
Data-Agent 100 場景完整測試腳本
會持續優化直到全部通過
"""

import asyncio
import httpx
import time
import json
from datetime import datetime

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

# J. 異常處理 (J01-J10)
TEST_CASES.extend(
    [
        ("J01", "查詢不存在的料號 XYZ-999"),
        ("J02", "查詢不存在的倉庫 W99"),
        ("J03", "查詢不存在的訂單 XYZ-999"),
    ]
)


async def run_test(client: httpx.AsyncClient, test_id: str, query: str, expected_rows: str = None):
    """執行單個測試"""
    start_time = time.time()
    try:
        response = await client.post(
            "http://localhost:8004/execute",
            json={
                "task_id": f"test_{test_id}",
                "task_type": "data_query",
                "task_data": {
                    "action": "execute_structured_query",
                    "natural_language_query": query,
                },
            },
            timeout=120.0,
        )
        elapsed = (time.time() - start_time) * 1000

        result = response.json()
        inner_result = result.get("result", {})
        actual_result = inner_result.get("result", {})

        sql = actual_result.get("sql_query", "")
        row_count = actual_result.get("row_count")

        # 基本成功標準：有 SQL 且有結果
        success = sql and sql.strip() and row_count is not None

        return {
            "test_id": test_id,
            "query": query,
            "sql": sql,
            "row_count": row_count,
            "elapsed_ms": round(elapsed, 2),
            "success": success,
            "error": None,
        }
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        return {
            "test_id": test_id,
            "query": query,
            "sql": "",
            "row_count": None,
            "elapsed_ms": round(elapsed, 2),
            "success": False,
            "error": str(e),
        }


async def run_all_tests():
    """執行所有測試"""
    results = []
    async with httpx.AsyncClient() as client:
        current_category = ""
        for test_id, query in TEST_CASES:
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

    print(f"\n{'=' * 70}")
    print(f"測試摘要: {passed}/{total} 通過 ({passed / total * 100:.1f}%)")
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
        rate = c["passed"] / c["total"] * 100
        print(f"  {cat}: {c['passed']}/{c['total']} ({rate:.0f}%)", end="")
        if c["failed"]:
            print(f" ❌ {', '.join(c['failed'])}")
        else:
            print()

    return categories


def generate_report(results, iteration=1):
    """生成測試報告"""
    total = len(results)
    passed = sum(1 for r in results if r["success"])

    report = f"""# Data-Agent 100 場景測試報告 (第 {iteration} 輪)

**測試日期**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**通過率**: {passed}/{total} ({passed / total * 100:.1f}%)

---

## 測試摘要

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

    # 失敗清單
    failed_tests = [r for r in results if not r["success"]]
    if failed_tests:
        report += "## 失敗場景\n\n"
        report += "| 測試ID | 查詢 | 錯誤 |\n"
        report += "|--------|------|------|\n"
        for r in failed_tests:
            report += f"| {r['test_id']} | {r['query'][:40]}... | SQL 生成失敗 |\n"

    return report


if __name__ == "__main__":
    print("=" * 70)
    print("Data-Agent 100 場景測試")
    print("=" * 70)

    results = asyncio.run(run_all_tests())
    categories = analyze_results(results)

    report = generate_report(results, 1)
    print(report)

    # 保存報告
    with open(
        "/home/daniel/ai-box/datalake-system/.ds-docs/Data-Agent/testing/test_report_latest.md", "w"
    ) as f:
        f.write(report)

    # 如果有失敗，繼續優化
    passed = sum(1 for r in results if r["success"])
    if passed < len(results):
        print(f"\n需要優化，已保存報告到 test_report_latest.md")
