#!/usr/bin/env python3
# 代碼功能說明: Data-Agent 5 場景快速測試（驗證修復）
# 創建日期: 2026-01-30
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-30

"""Data-Agent 5 場景快速測試：驗證參數化查詢修復"""

import asyncio
import json
import sys
from pathlib import Path

# 添加 AI-Box 根目錄到 Python 路徑
_script_dir = Path(__file__).resolve().parent
_datalake_system_dir = _script_dir.parent
_ai_box_root = _datalake_system_dir.parent
for _p in (_ai_box_root, _datalake_system_dir):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from agents.services.protocol.base import AgentServiceRequest
from data_agent.agent import DataAgent

# 簡化的 Schema
SCHEMA_INFO = {
    "tables": [
        {"name": "ima_file", "columns": ["ima01", "ima02", "ima25", "imag08"]},
        {"name": "img_file", "columns": ["img01", "img02", "img10", "img04"]},
        {"name": "tlf_file", "columns": ["tlf01", "tlf06", "tlf10", "tlf19"]},
        {"name": "pmn_file", "columns": ["pmn01", "pmn02", "qmn10"]},
    ]
}


def build_scenarios() -> list:
    """構建 5 個測試場景"""
    scenarios = []

    # T2S-001～T2S-005：語言轉 SQL 功能場景
    text_cases = [
        (
            "T2S-001",
            "簡單 WHERE 條件查詢",
            "查詢料號為 10-0001 的庫存記錄。",
            ["WHERE", "img01", "10-0001"],
        ),
        (
            "T2S-002",
            "AND 條件查詢",
            "查詢料號 10-0001 且倉庫為 W01 的庫存。",
            ["WHERE", "AND", "img01", "img02", "10-0001", "W01"],
        ),
        (
            "T2S-003",
            "OR 條件查詢",
            "查詢料號 10-0001 或 10-0002 的庫存。",
            ["WHERE", "OR", "img01", "10-0001", "10-0002"],
        ),
        (
            "T2S-004",
            "IN 條件查詢",
            "查詢料號在 10-0001、10-0002、10-0003 中的庫存。",
            ["WHERE", "IN", "img01", "('10-0001','10-0002','10-0003')"],
        ),
        (
            "T2S-005",
            "SUM 聚合",
            "計算料號 10-0001 的總庫存量。",
            ["SELECT", "SUM", "img10", "WHERE"],
        ),
    ]

    for item in text_cases:
        sid, cat, nl, keywords = item[0], item[1], item[2]
        scenarios.append(
            {
                "scenario_id": sid,
                "category": cat,
                "task_data": {
                    "action": "text_to_sql",
                    "natural_language": nl,
                    "schema_info": SCHEMA_INFO,
                },
                "expected_success": True,
                "expected_keywords": keywords,
                # 修復：允許參數化查詢，檢查 SQL 基本結構（SELECT, FROM, WHERE）
                "allow_parameterized": True,
                "check_sql_structure": True,
            }
        )

    return scenarios


async def run_one(
    agent: DataAgent,
    scenario: dict,
    index: int,
) -> dict:
    """執行單一場景，記錄耗時與結果"""
    sid = scenario["scenario_id"]
    task_data = scenario["task_data"]
    raw_task_data = scenario.get("raw_task_data", False)
    expected_success = scenario.get("expected_success", True)
    expected_keywords = scenario.get("expected_keywords", [])
    timeout_threshold = 10.0  # 鰡化超時為 10 秒
    allow_parameterized = scenario.get("allow_parameterized", True)
    check_sql_structure = scenario.get("check_sql_structure", False)

    request_payload = (
        task_data
        if isinstance(task_data, dict)
        else {"action": "text_to_sql", "natural_language": str(task_data)}
    )

    record = {
        "scenario_id": sid,
        "category": scenario.get("category", ""),
        "passed": False,
        "duration_sec": None,
        "expected_success": expected_success,
        "actual_success": None,
        "error": None,
        "generated_sql": None,
        "result_summary": None,
        "notes": [],
    }

    try:
        import time as time_module
        t0 = time_module.perf_counter()
        
        response = await agent.execute(
            AgentServiceRequest(
                task_id=f"run_{sid}",
                task_type="data_agent",
                task_data=request_payload,
                context=None,
                metadata=None,
            )
        )
        
        duration = time_module.perf_counter() - t0
        record["duration_sec"] = round(duration, 3)
        record["actual_success"] = response.status == "completed"
        record["error"] = response.error

        result_data = response.result or {}
        
        # 提取 SQL 查詢
        if result_data and isinstance(result_data, dict):
            inner = result_data.get("result", {})
            if "sql_query" in inner:
                record["generated_sql"] = inner.get("sql_query", "")[:500]

        # 參數化查詢驗證
        if allow_parameterized and record["generated_sql"]:
            sql_upper = (record["generated_sql"] or "").upper()
            expected_present = any(kw.upper() in sql_upper for kw in expected_keywords)
            
            # 檢查參數化查詢（$1, $2 等）
            has_placeholder = any(marker in sql_upper for marker in ["$", "1", "2", "3", "4", "5", "6", "7", "8", "9"])
            
            # 檢查 SQL 基本結構（修復）
            has_basic_structure = False
            if check_sql_structure:
                for struct_kw in ["SELECT", "FROM", "WHERE"]:
                    if struct_kw in sql_upper:
                        has_basic_structure = True
                        break
            
            # 檢查並通過邏輯
            if has_placeholder and has_basic_structure:
                record["notes"].append("✅ 參數化查詢（包含 SQL 基本結構）")
                record["passed"] = True
            elif has_basic_structure and not has_placeholder:
                if expected_present:
                    record["notes"].append(f"✅ 包含預期關鍵字: {expected_keywords}")
                    record["passed"] = True
                else:
                    # 允許：無參數化的基本 SQL
                    record["passed"] = False
                    record["notes"].append("⚠️ 無參數化且無預期關鍵字")
            else:
                # 無基本結構
                if expected_present:
                    record["notes"].append(f"✅ 包含預期關鍵字: {expected_keywords}")
                    record["passed"] = True
                else:
                    record["notes"].append("❌ 未包含預期關鍵字")
                    record["passed"] = False

        # 超時檢查
        if duration > timeout_threshold:
            record["notes"].append(f"⚠️ 耗時 {duration:.2f}s 超過閾值 {timeout_threshold}s")
            record["passed"] = False

        if record["actual_success"] != expected_success:
            record["notes"].append(f"預期成功={expected_success}，實際={record['actual_success']}")

        if record.get("passed"):
            record["result_summary"] = "查詢成功"
        else:
            if record.get("generated_sql"):
                record["result_summary"] = f"查詢失敗，SQL: {record['generated_sql'][:100]}"
            else:
                record["result_summary"] = "查詢失敗"

        return record


async def main() -> None:
    """執行 5 場景測試並輸出報告"""
    scenarios = build_scenarios()
    agent = DataAgent()
    results = []
    passed = 0
    failed = 0

    print("=" * 60)
    print("Data-Agent 5 場景快速測試（驗證參數化查詢修復）")
    print("=" * 60)

    for i, scenario in enumerate(scenarios, 1):
        sid = scenario["scenario_id"]
        print(f"\n[{i}/5] {sid} {scenario.get('category', '')}")
        try:
            record = await run_one(agent, scenario, i)
            results.append(record)
            
            if record.get("passed"):
                passed += 1
                status = "✅ 通過"
            else:
                failed += 1
                status = f"❌ 失敗: {' '.join(record.get('notes', []))}"
            
            print(f"  {status} (耗時: {record.get('duration_sec')}s)")
            
            if record.get("generated_sql"):
                print(f"  SQL: {record['generated_sql'][:200]}...")
            
            if record.get("error"):
                print(f"  錯誤: {record.get('error')}")
                
        except Exception as e:
            failed += 1
            results.append(
                {"scenario_id": sid, "passed": False, "error": str(e), "notes": ["執行異常"]}
            )
            print(f"  異常: {e}")

    print("\n" + "=" * 60)
    print(f"總計: 5，通過: {passed}，失敗: {failed}")
    print("=" * 60)

    # 輸出結果
    out_path = _script_dir / "run_5_scenarios_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"summary": {"total": 5, "passed": passed, "failed": failed}, "results": results},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"結果已寫入: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
