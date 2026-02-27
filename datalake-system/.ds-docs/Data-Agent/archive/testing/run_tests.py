#!/usr/bin/env python3
"""
Data-Agent 100 場景測試腳本
"""

import asyncio
import json
import time
import httpx
from datetime import datetime

TEST_CASES = {
    "A": [
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
    ],
    "B": [
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
    ],
    "C": [
        ("C01", "查詢 2024 年有多少筆採購進貨"),
        ("C02", "查詢所有採購進貨交易"),
        ("C03", "查詢 W04 倉庫的進貨記錄"),
        ("C04", "查詢 2024 年 1 月的交易記錄"),
        ("C07", "查詢所有銷貨記錄"),
        ("C08", "2024 年銷售出庫筆數"),
        ("C09", "查詢完工入庫記錄"),
        ("C10", "查詢生產領料記錄"),
        ("C12", "按交易類型統計數量"),
        ("C13", "查詢料號 10-0001 的所有交易"),
    ],
    "D": [
        ("D01", "查詢所有供應商"),
        ("D02", "某供應商的聯絡人"),
        ("D03", "查詢供應商 VND003 的詳細資訊"),
        ("D04", "統計供應商數量"),
        ("D05", "查詢所有供應商名稱"),
    ],
    "E": [
        ("E01", "查詢所有採購單"),
        ("E02", "按供應商統計採購單數量"),
        ("E03", "2024 年有多少筆採購單"),
        ("E04", "查詢某供應商的採購單"),
        ("E05", "按月份統計採購單數量"),
        ("E06", "查詢採購單 PO-2024010001 的明細"),
        ("E07", "查詢某料號的採購數量"),
        ("E12", "查詢最近 10 筆採購單"),
        ("E14", "計算採購單總數量"),
    ],
    "F": [
        ("F01", "查詢所有客戶"),
        ("F02", "某客戶的聯絡人"),
        ("F03", "查詢客戶 D010 的詳細資訊"),
        ("F04", "統計客戶數量"),
        ("F05", "查詢所有客戶名稱"),
    ],
    "G": [
        ("G01", "查詢所有訂單"),
        ("G02", "統計每個客户的訂單數量"),
        ("G03", "查詢最近 10 筆訂單"),
        ("G07", "2024 年有多少筆訂單"),
        ("G09", "查詢訂單 SO-2024010001 的明細"),
        ("G11", "查詢料號 10-0001 的訂購數量"),
    ],
    "H": [
        ("H01", "查詢料號 10-0001 的單價"),
        ("H02", "料號 10-0001 的最新報價"),
        ("H04", "查詢已批准的訂價"),
        ("H07", "計算料號的平均價格"),
    ],
    "I": [
        ("I01", "查詢 W01 倉庫的所有儲位"),
        ("I03", "查詢所有倉庫代號"),
        ("I05", "查詢某倉庫名稱"),
    ],
}


async def test_query(client: httpx.AsyncClient, test_id: str, query: str) -> dict:
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

        return {
            "test_id": test_id,
            "query": query,
            "sql": actual_result.get("sql_query", ""),
            "row_count": actual_result.get("row_count"),
            "elapsed_ms": round(elapsed, 2),
            "success": actual_result.get("row_count", 0) is not None,
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
        for category, cases in TEST_CASES.items():
            print(f"\n{'=' * 60}")
            print(f"測試類別: {category}")
            print(f"{'=' * 60}")

            for test_id, query in cases:
                result = await test_query(client, test_id, query)
                results.append(result)

                status = "✅" if result["success"] else "❌"
                print(f"{status} {test_id}: {result['row_count']} rows ({result['elapsed_ms']}ms)")

    return results


def generate_report(results: list) -> str:
    """生成測試報告"""
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed

    report = f"""# Data-Agent 100 場景測試報告

**測試日期**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**通過率**: {passed}/{total} ({passed / total * 100:.1f}%)

## 測試摘要

| 指標 | 數值 |
|------|------|
| 總測試數 | {total} |
| 通過 | {passed} |
| 失敗 | {failed} |
| 通過率 | {passed / total * 100:.1f}% |

## 詳細結果

| 測試ID | 查詢 | SQL | 筆數 | 耗時(ms) | 狀態 |
|--------|------|-----|------|----------|------|
"""

    for r in results:
        status = "✅ 通過" if r["success"] else "❌ 失敗"
        sql_display = r["sql"][:80] + "..." if r["sql"] and len(r["sql"]) > 80 else r["sql"]
        report += f"| {r['test_id']} | {r['query'][:30]}... | {sql_display} | {r['row_count']} | {r['elapsed_ms']} | {status} |\n"

    return report


if __name__ == "__main__":
    results = asyncio.run(run_all_tests())
    report = generate_report(results)
    print(f"\n{'=' * 60}")
    print(f"測試完成: {len(results)} 個測試")
    print(f"通過: {sum(1 for r in results if r['success'])}")
    print(f"失敗: {sum(1 for r in results if not r['success'])}")
    print(f"{'=' * 60}")
    print(report)
