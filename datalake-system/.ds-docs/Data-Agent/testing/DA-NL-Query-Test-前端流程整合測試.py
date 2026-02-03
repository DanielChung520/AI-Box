#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端流程整合測試 - Data-Agent 自然語言查詢

模擬 Dashboard 前端的完整 5 步流程：
1. 步驟 1：分析查詢意圖 → 生成意圖分析字典
2. 步驟 2：確認查詢類型 → 判定為 text_to_sql (pass-to-llm)
3. 步驟 3：LLM 生成 SQL → 傳遞意圖分析給後端，獲取 SQL
4. 步驟 4：執行 SQL 查詢 → 執行生成的 SQL
5. 步驟 5：顯示查詢結果 → 驗證返回數據

測試日期：2026-01-31
"""

import sys
import os
import json
import time

# 添加路徑
sys.path.insert(0, "/home/daniel/ai-box/datalake-system")
sys.path.insert(0, "/home/daniel/ai-box/datalake-system/dashboard")

from services.data_agent_client import call_data_agent_sync

# 載入 Schema
SCHEMA_PATH = "/home/daniel/ai-box/datalake-system/metadata/schema_registry.json"
with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    SCHEMA_INFO = json.load(f)

# 測試案例
TEST_CASES = [
    {
        "name": "W01 各料號的庫存",
        "natural_language": "W01 各料號的庫存",
        "expected_intent": {
            "intent_type": "query_inventory",
            "table": "img_file",
            "aggregation": "SUM",
            "group_by": "img01",
            "filters": "img02 = 'W01'",
        },
    },
    {
        "name": "查詢 W01 原料倉有多少庫存",
        "natural_language": "查詢 W01 原料倉有多少庫存",
        "expected_intent": {
            "intent_type": "query_inventory",
            "table": "img_file",
            "aggregation": "SUM",
            "group_by": None,
            "filters": "img02 = 'W01'",
        },
    },
    {
        "name": "計算 10-0001 的總庫存量",
        "natural_language": "計算 10-0001 的總庫存量",
        "expected_intent": {
            "intent_type": "calculate_total",
            "table": "img_file",
            "aggregation": "SUM",
            "group_by": None,
            "filters": "img01 = '10-0001'",
        },
    },
]


def run_full_flow_test(test_case: dict) -> dict:
    """
    模擬前端完整流程測試

    Returns:
        dict: 測試結果，包含每步驟的產出
    """
    print(f"\n{'=' * 60}")
    print(f"測試案例：{test_case['name']}")
    print(f"自然語言：{test_case['natural_language']}")
    print(f"{'=' * 60}")

    result = {
        "test_name": test_case["name"],
        "natural_language": test_case["natural_language"],
        "steps": {},
        "success": True,
        "errors": [],
    }

    # ===== 步驟 1：分析查詢意圖 =====
    print("\n📊 步驟 1：分析查詢意圖")
    print("-" * 40)

    # 模擬 IntentAnalyzer 的功能
    nl = test_case["natural_language"]
    intent = {
        "intent_type": "query_inventory",
        "description": f"查詢{nl}",
        "table": "img_file",
        "aggregation": "SUM",
        "group_by": "img01",
        "filters": "img02 = 'W01'",
    }

    # 檢測料號
    import re

    item_match = re.search(r"(\d{2}-\d{4})", nl)
    if item_match:
        item_code = item_match.group(1)
        intent["filters"] = f"img01 = '{item_code}'"
        intent["group_by"] = None

    # 檢測倉庫
    warehouse_match = re.search(r"(W0[1-5])", nl)
    if warehouse_match:
        warehouse = warehouse_match.group(1)
        intent["filters"] = f"img02 = '{warehouse}'"

    # 檢測計算意圖
    if "計算" in nl or "總" in nl:
        intent["aggregation"] = "SUM"
    elif "平均" in nl:
        intent["aggregation"] = "AVG"
    elif "數量" in nl or "筆" in nl:
        intent["aggregation"] = "COUNT"

    # 檢測分組
    if "各" in nl or "每個" in nl or "每" in nl:
        intent["group_by"] = "img01"

    result["steps"]["step1_intent_analysis"] = {
        "status": "completed",
        "intent": intent,
        "prompt": f"""用戶查詢：「{nl}」

意圖分析：
- 意圖類型：{intent["intent_type"]}
- 描述：{intent["description"]}
- 資料表：{intent["table"]}
- 聚合方式：{intent["aggregation"]}（計算總和）
- 分組欄位：{intent["group_by"] or "無"}（按料號分組）
- 篩選條件：{intent["filters"]}（限定 W01 倉庫）

輸出要求：請根據以上意圖生成對應的 PostgreSQL SQL 語句。""",
    }

    print(f"  ✅ 意圖類型：{intent['intent_type']}")
    print(f"  ✅ 資料表：{intent['table']}")
    print(f"  ✅ 聚合：{intent['aggregation']}")
    print(f"  ✅ 分組：{intent['group_by']}")
    print(f"  ✅ 篩選：{intent['filters']}")
    print(f"  ✅ Prompt 長度：{len(result['steps']['step1_intent_analysis']['prompt'])} 字元")

    # ===== 步驟 2：確認查詢類型 =====
    print("\n📊 步驟 2：確認查詢類型")
    print("-" * 40)

    # 判定類型
    if intent["aggregation"] in ["SUM", "AVG", "COUNT"] or intent["group_by"]:
        decision_type = "pass-to-llm"
        decision_reason = "需要 LLM 根據意圖生成 SQL 語句"
    elif "多少" in nl or "統計" in nl:
        decision_type = "pass-to-llm"
        decision_reason = "需要計算，交付 LLM 生成 SQL"
    else:
        decision_type = "pass-to-llm"
        decision_reason = "需要 LLM 解析意圖生成 SQL"

    result["steps"]["step2_query_type"] = {
        "status": "completed",
        "decision_type": decision_type,
        "decision_reason": decision_reason,
        "action": "text_to_sql",
    }

    print(f"  ✅ 判定類型：{decision_type}")
    print(f"  ✅ 判定理由：{decision_reason}")
    print(f"  ✅ 執行動作：{result['steps']['step2_query_type']['action']}")

    # ===== 步驟 3：LLM 生成 SQL =====
    print("\n📊 步驟 3：LLM 生成 SQL")
    print("-" * 40)

    start_time = time.time()

    # 準備請求參數（包含意圖分析）
    request_params = {
        "action": "text_to_sql",
        "schema_info": {},  # 使用預設 schema
        "intent_analysis": intent,
    }

    # 調用後端
    try:
        llm_result = call_data_agent_sync(
            test_case["natural_language"],
            action="text_to_sql",
            schema_info=SCHEMA_INFO,  # 傳遞正確的 Schema
            intent_analysis=intent,
        )

        llm_duration = time.time() - start_time

        # 解析結果
        outer_result = llm_result.get("result", {})
        inner_result = outer_result.get("result", {}) if isinstance(outer_result, dict) else {}

        sql_query = inner_result.get("sql_query", "")
        confidence = inner_result.get("confidence", 0)

        # 提取 conversion_log
        conversion_log = inner_result.get("conversion_log", {})
        llm_ms = 0
        if conversion_log.get("steps"):
            for step in conversion_log["steps"]:
                if step.get("step") == "llm_generate":
                    llm_ms = step.get("duration_ms", 0)
                    break

        result["steps"]["step3_llm_sql"] = {
            "status": "completed" if sql_query else "failed",
            "sql_query": sql_query,
            "confidence": confidence,
            "duration_sec": llm_ms / 1000,
            "llm_result": llm_result,
        }

        print(f"  ✅ SQL：{sql_query[:100]}...")
        print(f"  ✅ 置信度：{confidence:.2%}")
        print(f"  ✅ 耗時：{llm_ms / 1000:.2f} 秒")

        if not sql_query:
            result["success"] = False
            result["errors"].append("步驟 3：SQL 生成失敗")

    except Exception as e:
        result["steps"]["step3_llm_sql"] = {
            "status": "error",
            "error": str(e),
        }
        result["success"] = False
        result["errors"].append(f"步驟 3：{str(e)}")
        print(f"  ❌ 錯誤：{e}")

    # ===== 步驟 4：執行 SQL 查詢 =====
    print("\n📊 步驟 4：執行 SQL 查詢")
    print("-" * 40)

    if result["steps"]["step3_llm_sql"].get("status") == "completed":
        sql = result["steps"]["step3_llm_sql"]["sql_query"]

        try:
            exec_start = time.time()
            exec_result = call_data_agent_sync(
                "",
                action="execute_sql_on_datalake",
                sql_query_datalake=sql,
            )
            exec_duration = time.time() - exec_start

            # 解析執行結果
            exec_outer = exec_result.get("result", {})
            exec_inner = exec_outer.get("result", {}) if isinstance(exec_outer, dict) else {}

            rows = exec_inner.get("rows", []) if isinstance(exec_inner, dict) else []
            row_count = exec_inner.get("row_count", 0) if isinstance(exec_inner, dict) else 0

            result["steps"]["step4_execute_sql"] = {
                "status": "completed",
                "row_count": row_count,
                "duration_sec": exec_duration,
                "exec_result": exec_result,
            }

            print(f"  ✅ 返回筆數：{row_count}")
            print(f"  ✅ 執行耗時：{exec_duration:.2f} 秒")

            if rows:
                print(f"  ✅ 數據樣本：{rows[0] if rows else 'N/A'}")

        except Exception as e:
            result["steps"]["step4_execute_sql"] = {
                "status": "error",
                "error": str(e),
            }
            result["success"] = False
            result["errors"].append(f"步驟 4：{str(e)}")
            print(f"  ❌ 錯誤：{e}")
    else:
        result["steps"]["step4_execute_sql"] = {
            "status": "skipped",
            "reason": "步驟 3 失敗",
        }
        print(f"  ⚠️ 跳過：步驟 3 失敗")

    # ===== 步驟 5：顯示查詢結果 =====
    print("\n📊 步驟 5：顯示查詢結果")
    print("-" * 40)

    step4 = result["steps"].get("step4_execute_sql", {})
    if step4.get("status") == "completed":
        rows = step4.get("exec_result", {}).get("result", {}).get("result", {}).get("rows", [])
        row_count = step4.get("row_count", 0)

        result["steps"]["step5_show_results"] = {
            "status": "completed",
            "row_count": row_count,
            "has_data": len(rows) > 0,
        }

        print(f"  ✅ 狀態：{'有數據' if rows else '無數據'}")
        print(f"  ✅ 總筆數：{row_count}")

        if rows:
            # 嘗試計算統計
            import pandas as pd

            df = pd.DataFrame(rows[:50])
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

            if numeric_cols:
                for col in numeric_cols[:2]:  # 只顯示前2個數值欄位
                    total = df[col].sum()
                    avg = df[col].mean()
                    print(f"  ✅ {col} 統計：總和={total:,.0f}, 平均={avg:,.1f}")
    else:
        result["steps"]["step5_show_results"] = {
            "status": "skipped",
            "reason": "步驟 4 失敗",
        }
        print(f"  ⚠️ 跳過：步驟 4 失敗")

    return result


def main():
    """主測試函數"""
    print("\n" + "=" * 60)
    print("Data-Agent 前端流程整合測試")
    print("測試日期：2026-01-31")
    print("=" * 60)

    all_results = []
    passed = 0
    failed = 0

    for test_case in TEST_CASES:
        try:
            result = run_full_flow_test(test_case)
            all_results.append(result)

            if result["success"]:
                passed += 1
                print(f"\n✅ 測試通過：{test_case['name']}")
            else:
                failed += 1
                print(f"\n❌ 測試失敗：{test_case['name']}")
                for error in result["errors"]:
                    print(f"   - {error}")

        except Exception as e:
            failed += 1
            print(f"\n❌ 測試異常：{test_case['name']}")
            print(f"   錯誤：{e}")
            import traceback

            traceback.print_exc()

    # 總結
    print("\n" + "=" * 60)
    print("測試總結")
    print("=" * 60)
    print(f"總測試數：{len(TEST_CASES)}")
    print(f"通過：{passed}")
    print(f"失敗：{failed}")
    print(f"通過率：{passed / len(TEST_CASES) * 100:.1f}%")

    # 保存結果
    output_file = "/home/daniel/ai-box/datalake-system/.ds-docs/Data-Agent/testing/integration_test_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n結果已保存至：{output_file}")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
