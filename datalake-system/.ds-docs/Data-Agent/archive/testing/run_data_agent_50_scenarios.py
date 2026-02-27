#!/usr/bin/env python3
# 代碼功能說明: Data-Agent 50 場景測試腳本（對應 Data-Agent-50場景測試計劃.md）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""Data-Agent 50 場景測試腳本

對應規格：DAta-Agent/testing/Data-Agent-50場景測試計劃.md
- T2S-001～T2S-022：語言轉 SQL 功能場景
- T2S-023～T2S-030：其他語義與邊界場景
- T2S-031～T2S-050：異常處理場景

驗證維度：正確性、耗時、異常處置恰當。
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from pydantic import ValidationError

# 添加 AI-Box 根目錄到 Python 路徑
_script_dir = Path(__file__).resolve().parent
_datalake_system_dir = _script_dir.parent
_ai_box_root = _datalake_system_dir.parent
for _p in (_ai_box_root, _datalake_system_dir):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from agents.services.protocol.base import AgentServiceRequest
from data_agent.agent import DataAgent  # type: ignore[import-not-found]

# 耗時閾值（秒）
THRESHOLD_TEXT_TO_SQL = 60.0
THRESHOLD_QUERY = 60.0
THRESHOLD_LARGE_QUERY = 60.0

# 用於 text_to_sql 的 Schema 簡述（可選）
SCHEMA_INFO = {
    "tables": [
        {
            "name": "ima_file",
            "description": "物料主檔（儲存物料基本信息、品名、規格等）",
            "usage": "用於查詢物料基本信息、品名、規格、庫存類型等",
            "columns": [
                {"name": "ima01", "description": "料號（主鍵）", "type": "string"},
                {"name": "ima02", "description": "品名", "type": "string"},
                {"name": "ima08", "description": "倉庫", "type": "string"},
                {"name": "ima25", "description": "庫存類型", "type": "string"},
            ],
        },
        {
            "name": "img_file",
            "description": "庫存明細檔（儲存庫存數量和倉庫信息）",
            "usage": "用於查詢庫存數量、倉庫庫存、庫存交易等（主要用於庫存查詢）",
            "columns": [
                {
                    "name": "img01",
                    "description": "料號（關聯欄位，對應 ima_file.ima01）",
                    "type": "string",
                },
                {"name": "img02", "description": "倉庫", "type": "string"},
                {"name": "img10", "description": "庫存量（數量）", "type": "number"},
                {"name": "img04", "description": "批號（可為空）", "type": "string"},
            ],
        },
        {
            "name": "tlf_file",
            "description": "交易明細檔（儲存交易記錄）",
            "usage": "用於查詢交易歷史、交易數量、交易日期等",
            "columns": [
                {
                    "name": "tlf01",
                    "description": "料號（關聯欄位，對應 ima_file.ima01）",
                    "type": "string",
                },
                {"name": "tlf06", "description": "交易日期", "type": "date"},
                {"name": "tlf10", "description": "交易數量", "type": "number"},
                {"name": "tlf19", "description": "交易類別", "type": "string"},
            ],
        },
        {
            "name": "pmn_file",
            "description": "採購單檔（儲存採購訂單信息）",
            "usage": "用於查詢採購單信息、供應商、採購數量等",
            "columns": [
                {"name": "pmn01", "description": "採購單號（主鍵）", "type": "string"},
                {"name": "pmn02", "description": "供應商", "type": "string"},
                {"name": "pmn10", "description": "採購數量", "type": "number"},
            ],
        },
    ],
    # 詞彙映射表：自然語言詞彙 -> SQL 欄位
    "vocabulary_mapping": {
        "料號": ["ima01", "img01", "tlf01"],
        "品名": ["ima02"],
        "庫存量": ["img10"],
        "庫存": ["img10"],
        "數量": ["img10", "tlf10", "pmn10"],
        "倉庫": ["ima08", "img02"],
        "批號": ["img04"],
        "交易日期": ["tlf06"],
        "交易數量": ["tlf10"],
        "採購單號": ["pmn01"],
        "供應商": ["pmn02"],
        "採購數量": ["pmn10"],
    },
    # 表關係說明
    "table_relationships": [
        "ima_file.ima01 = img_file.img01",
        "ima_file.ima01 = tlf_file.tlf01",
    ],
}


def build_scenarios() -> List[Dict[str, Any]]:
    """依 Data-Agent-50場景測試計劃 建構 50 套劇本。"""
    scenarios: List[Dict[str, Any]] = []

    # T2S-001～T2S-022：語言轉 SQL 功能場景
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
            ["WHERE", "AND", "img01", "img02"],
        ),
        (
            "T2S-003",
            "OR 條件查詢",
            "查詢料號為 10-0001 或 10-0002 的庫存。",
            ["WHERE", "OR", "img01"],
        ),
        (
            "T2S-004",
            "IN 條件查詢",
            "查詢料號在 10-0001、10-0002、10-0003 中的庫存。",
            ["WHERE", "IN", "img01"],
        ),
        ("T2S-005", "SUM 聚合", "計算料號 10-0001 的總庫存量。", ["SUM", "img10", "WHERE"]),
        ("T2S-006", "AVG 聚合", "查詢料號 10-0001 在各倉庫的平均庫存量。", ["AVG", "img10"]),
        ("T2S-007", "MAX 聚合", "查詢庫存量最高的單筆記錄的數量。", ["MAX", "img10"]),
        ("T2S-008", "MIN 聚合", "查詢庫存量最低的單筆記錄的數量。", ["MIN", "img10"]),
        ("T2S-009", "COUNT 聚合", "統計料號 10-0001 的庫存記錄筆數。", ["COUNT", "WHERE", "img01"]),
        ("T2S-010", "GROUP BY 分組", "按倉庫統計總庫存量。", ["GROUP BY", "img02", "SUM", "img10"]),
        (
            "T2S-011",
            "ORDER BY ASC 排序",
            "查詢庫存記錄，按庫存量由小到大排序。",
            ["ORDER BY", "img10", "ASC"],
        ),
        (
            "T2S-012",
            "ORDER BY DESC 排序",
            "查詢庫存記錄，按庫存量由大到小排序。",
            ["ORDER BY", "img10", "DESC"],
        ),
        ("T2S-013", "LIMIT 限制", "查詢前 10 筆庫存記錄。", ["LIMIT", "10"]),
        (
            "T2S-014",
            ">= 範圍過濾",
            "查詢庫存量大於等於 100 的記錄。",
            ["WHERE", "img10", ">=", "100"],
        ),
        (
            "T2S-015",
            "<= 範圍過濾",
            "查詢庫存量小於等於 500 的記錄。",
            ["WHERE", "img10", "<=", "500"],
        ),
        (
            "T2S-016",
            "BETWEEN 範圍過濾",
            "查詢庫存量在 100 到 500 之間的記錄。",
            ["WHERE", "BETWEEN", "100", "500"],
        ),
        ("T2S-017", "當月數據查詢", "查詢當月的交易記錄。", ["tlf06", "tlf_file", "WHERE"]),
        (
            "T2S-018",
            "大數據量查詢（1000 筆）",
            "查詢庫存表前 1000 筆記錄。",
            ["LIMIT", "1000"],
            THRESHOLD_LARGE_QUERY,
        ),
        (
            "T2S-019",
            "複雜查詢（WHERE + GROUP BY + ORDER BY）",
            "查詢庫存量≥100 的料號，按料號分組加總庫存，再按總量由高到低排序取前 5 筆。",
            ["WHERE", "GROUP BY", "ORDER BY", "LIMIT"],
        ),
        (
            "T2S-020",
            "多條件查詢",
            "查詢料號 10-0001、倉庫 W01、庫存量大於 50 的記錄。",
            ["WHERE", "AND", "img01", "img02", "img10"],
        ),
        (
            "T2S-021",
            "Top N 料號查詢",
            "查詢庫存總量前 5 名的料號。",
            ["GROUP BY", "img01", "ORDER BY", "DESC", "LIMIT", "5"],
        ),
        (
            "T2S-022",
            "Bottom N 料號查詢",
            "查詢庫存總量最低的 5 個料號。",
            ["GROUP BY", "img01", "ORDER BY", "ASC", "LIMIT", "5"],
        ),
    ]
    for item in text_cases:
        sid, cat, nl, keywords = item[0], item[1], item[2], item[3]
        timeout_threshold = item[4] if len(item) > 4 else THRESHOLD_TEXT_TO_SQL
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
                "timeout_threshold": timeout_threshold,
                "check_sql_keywords": True,
            }
        )

    # T2S-023～T2S-030：其他語義與邊界
    more_text = [
        ("T2S-023", "LIKE 模糊查詢", "查詢料號開頭為 10- 的物料主檔。", ["LIKE", "ima01", "10-"]),
        ("T2S-024", "空結果處理", "查詢料號為「不存在的料號-XYZ」的庫存。", ["WHERE", "img01"]),
        ("T2S-025", "DISTINCT", "查詢有庫存記錄的不重複料號列表。", ["DISTINCT", "img01"]),
        (
            "T2S-026",
            "HAVING 條件",
            "查詢總庫存量超過 1000 的料號。",
            ["GROUP BY", "HAVING", "SUM", "img10"],
        ),
        (
            "T2S-027",
            "多表語義（若支援）",
            "查詢料號 10-0001 的品名與其總庫存量。",
            ["ima_file", "img_file", "ima02", "SUM"],
        ),
        ("T2S-028", "日期範圍", "查詢 2026 年 1 月的交易記錄。", ["tlf06", "2026", "1", "WHERE"]),
        ("T2S-029", "NULL 條件", "查詢批號為空的庫存記錄。", ["img04", "IS NULL"]),
        (
            "T2S-030",
            "中文描述複雜條件",
            "查詢庫存數量在 100 到 200 之間且倉庫為 W01 或 W02 的記錄。",
            ["BETWEEN", "100", "200", "W01", "W02"],
        ),
    ]
    for sid, cat, nl, keywords in more_text:
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
                "timeout_threshold": THRESHOLD_TEXT_TO_SQL,
                "check_sql_keywords": True,
            }
        )

    # T2S-031～T2S-050：異常處理場景
    # T2S-031 缺 natural_language
    scenarios.append(
        {
            "scenario_id": "T2S-031",
            "category": "缺參數：無 natural_language",
            "task_data": {"action": "text_to_sql"},
            "expected_success": False,
            "expected_error_contains": ["natural_language", "required"],
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-032 缺 sql_query
    scenarios.append(
        {
            "scenario_id": "T2S-032",
            "category": "缺參數：無 sql_query",
            "task_data": {"action": "execute_query"},
            "expected_success": False,
            "expected_error_contains": ["sql_query", "required"],
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-033 錯誤 action
    scenarios.append(
        {
            "scenario_id": "T2S-033",
            "category": "錯誤 action",
            "task_data": {"action": "invalid_action"},
            "expected_success": False,
            "expected_error_contains": ["Unknown action", "invalid_action"],
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-034 task_data 空（缺 action 會觸發 Pydantic 驗證）
    scenarios.append(
        {
            "scenario_id": "T2S-034",
            "category": "task_data 為空",
            "task_data": {},
            "expected_success": False,
            "expected_error_contains": None,  # 可能為 ValidationError 訊息
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-035 task_data 型別錯誤（傳入後由 execute 解析會失敗）
    scenarios.append(
        {
            "scenario_id": "T2S-035",
            "category": "task_data 型別錯誤",
            "task_data": "not_a_dict",
            "expected_success": False,
            "expected_error_contains": None,
            "timeout_threshold": THRESHOLD_QUERY,
            "raw_task_data": True,
        }
    )
    # T2S-036 危險 SQL DROP（validate_query 或 execute_query）
    scenarios.append(
        {
            "scenario_id": "T2S-036",
            "category": "危險 SQL：DROP",
            "task_data": {"action": "validate_query", "query": "DROP TABLE img_file;"},
            "expected_success": False,
            "expected_error_contains": None,
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-037 危險 SQL DELETE
    scenarios.append(
        {
            "scenario_id": "T2S-037",
            "category": "危險 SQL：DELETE",
            "task_data": {
                "action": "validate_query",
                "query": "DELETE FROM img_file WHERE img01='x';",
            },
            "expected_success": False,
            "expected_error_contains": None,
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-038 SQL 注入嘗試（text_to_sql 輸入）
    scenarios.append(
        {
            "scenario_id": "T2S-038",
            "category": "SQL 注入嘗試",
            "task_data": {"action": "text_to_sql", "natural_language": "'; DROP TABLE img_file;--"},
            "expected_success": False,  # 惡意輸入應該被檢測並拒絕
            "expected_error_contains": ["未被授權做資料查詢以外的變更操作"],
            "timeout_threshold": THRESHOLD_TEXT_TO_SQL,
            "check_sql_keywords": False,
        }
    )
    # T2S-039 無效 SQL 語法
    scenarios.append(
        {
            "scenario_id": "T2S-039",
            "category": "無效 SQL 語法",
            "task_data": {"action": "validate_query", "query": "SELECT FROM img_file"},
            "expected_success": False,
            "expected_error_contains": None,
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-040 validate_query 通過
    scenarios.append(
        {
            "scenario_id": "T2S-040",
            "category": "validate_query 通過",
            "task_data": {"action": "validate_query", "query": "SELECT * FROM img_file LIMIT 1"},
            "expected_success": True,
            "expected_valid": True,
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-041 validate_query 不通過
    scenarios.append(
        {
            "scenario_id": "T2S-041",
            "category": "validate_query 不通過",
            "task_data": {"action": "validate_query", "query": "INVALID SQL ???"},
            "expected_success": True,  # 響應成功但 result.valid=False
            "expected_valid": False,
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-042 query_datalake 缺 bucket
    scenarios.append(
        {
            "scenario_id": "T2S-042",
            "category": "query_datalake 缺 bucket",
            "task_data": {"action": "query_datalake", "key": "some/key"},
            "expected_success": False,
            "expected_error_contains": ["bucket", "key"],
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-043 query_datalake 不存在的 key（需有 bucket）
    scenarios.append(
        {
            "scenario_id": "T2S-043",
            "category": "query_datalake 不存在的 key",
            "task_data": {
                "action": "query_datalake",
                "bucket": "tiptop-raw",
                "key": "nonexistent/key/xyz.parquet",
                "query_type": "exact",
            },
            "expected_success": False,
            "expected_error_contains": None,
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-044 超時（若已實作，此處僅呼叫大範圍查詢；實際超時由服務端控制）
    scenarios.append(
        {
            "scenario_id": "T2S-044",
            "category": "超時（若已實作）",
            "task_data": {
                "action": "text_to_sql",
                "natural_language": "查詢庫存表所有記錄不限制筆數",
            },
            "expected_success": True,
            "timeout_threshold": THRESHOLD_LARGE_QUERY,
        }
    )
    # T2S-045 過大 LIMIT
    scenarios.append(
        {
            "scenario_id": "T2S-045",
            "category": "過大 LIMIT（若有限制）",
            "task_data": {"action": "text_to_sql", "natural_language": "查詢庫存表 100 萬筆記錄"},
            "expected_success": True,
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-046 get_schema 缺 schema_id
    scenarios.append(
        {
            "scenario_id": "T2S-046",
            "category": "get_schema 缺 schema_id",
            "task_data": {"action": "get_schema"},
            "expected_success": False,
            "expected_error_contains": ["schema_id"],
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-047 create_dictionary 缺必要欄位
    scenarios.append(
        {
            "scenario_id": "T2S-047",
            "category": "create_dictionary 缺必要欄位",
            "task_data": {"action": "create_dictionary"},
            "expected_success": False,
            "expected_error_contains": ["dictionary_id", "dictionary_data"],
            "timeout_threshold": THRESHOLD_QUERY,
        }
    )
    # T2S-048 重複呼叫 text_to_sql
    scenarios.append(
        {
            "scenario_id": "T2S-048",
            "category": "重複呼叫 text_to_sql",
            "task_data": {
                "action": "text_to_sql",
                "natural_language": "查詢料號 10-0001 的庫存記錄。",
                "schema_info": SCHEMA_INFO,
            },
            "expected_success": True,
            "expected_keywords": ["WHERE", "img01"],
            "timeout_threshold": THRESHOLD_TEXT_TO_SQL,
            "check_sql_keywords": True,
            "run_twice": True,
        }
    )
    # T2S-049 混合：text_to_sql → validate_query（腳本內兩步）
    scenarios.append(
        {
            "scenario_id": "T2S-049",
            "category": "混合流程：text_to_sql → validate_query",
            "task_data": {
                "action": "text_to_sql",
                "natural_language": "查詢前 1 筆庫存記錄",
                "schema_info": SCHEMA_INFO,
            },
            "expected_success": True,
            "timeout_threshold": THRESHOLD_TEXT_TO_SQL,
            "then_validate": True,
        }
    )
    # T2S-050 混合：text_to_sql → execute_query（若環境支援）
    scenarios.append(
        {
            "scenario_id": "T2S-050",
            "category": "混合流程：text_to_sql → execute_query",
            "task_data": {
                "action": "text_to_sql",
                "natural_language": "查詢前 1 筆庫存記錄",
                "schema_info": SCHEMA_INFO,
            },
            "expected_success": True,
            "timeout_threshold": THRESHOLD_TEXT_TO_SQL,
            "then_execute": True,
        }
    )

    return scenarios


async def run_one(
    agent: DataAgent,
    scenario: Dict[str, Any],
    index: int,
) -> Dict[str, Any]:
    """執行單一場景，記錄耗時與結果。"""
    sid = scenario["scenario_id"]
    task_data = scenario.get("task_data")
    raw_task_data = scenario.get("raw_task_data", False)
    expected_success = scenario.get("expected_success", True)
    expected_keywords = scenario.get("expected_keywords", [])
    expected_error_contains = scenario.get("expected_error_contains")
    timeout_threshold = scenario.get("timeout_threshold", THRESHOLD_QUERY)
    check_sql = scenario.get("check_sql_keywords", False)
    check_no_dangerous = scenario.get("check_no_dangerous_sql", False)
    run_twice = scenario.get("run_twice", False)
    then_validate = scenario.get("then_validate", False)
    then_execute = scenario.get("then_execute", False)

    request_payload = (
        task_data
        if isinstance(task_data, dict)
        else {"action": "text_to_sql", "natural_language": str(task_data)}
    )
    if raw_task_data:
        request_payload = task_data  # type: ignore[assignment]  # T2S-035 等：可能為非 dict

    record: Dict[str, Any] = {
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
        # T2S-035：task_data 非 dict 時 Pydantic 會在建構 Request 時拋 ValidationError
        if sid == "T2S-035" and not isinstance(task_data, dict):
            try:
                AgentServiceRequest(
                    task_id=f"run_{sid}",
                    task_type="data_agent",
                    task_data=task_data,  # type: ignore[arg-type]
                    context=None,
                    metadata=None,
                )
            except ValidationError as e:
                record["passed"] = True
                record["actual_success"] = False
                record["error"] = str(e)
                record["notes"].append("Pydantic 驗證拒絕非 dict task_data")
                return record
            # 若未拋錯則繼續（理論上不應發生）

        if not isinstance(request_payload, dict) or "action" not in request_payload:
            # T2S-034 等：task_data 為空或缺 action，直接傳入由 execute 內驗證
            req = AgentServiceRequest(
                task_id=f"run_{sid}",
                task_type="data_agent",
                task_data=request_payload if isinstance(request_payload, dict) else {},
                context=None,
                metadata=None,
            )
        else:
            req = AgentServiceRequest(
                task_id=f"run_{sid}",
                task_type="data_agent",
                task_data=request_payload,
                context=None,
                metadata=None,
            )

        t0 = time.perf_counter()
        response = await agent.execute(req)
        duration = time.perf_counter() - t0
        record["duration_sec"] = round(duration, 3)
        record["actual_success"] = response.status == "completed"
        record["error"] = response.error
        result_data = response.result or {}
        record["result_summary"] = (
            result_data if isinstance(result_data, dict) else str(result_data)[:500]
        )

        if result_data and isinstance(result_data, dict):
            inner = result_data.get("result")
            if isinstance(inner, dict) and "sql_query" in inner:
                record["generated_sql"] = inner.get("sql_query", "")[:500]
            elif isinstance(inner, str):
                record["generated_sql"] = inner[:500]

        # 正確性：預期成功與否
        if record["actual_success"] != expected_success:
            # 特殊處理 1：validate_query 場景（T2S-036/037/039）
            # 如果 action 是 validate_query 且 result.valid=False，視為預期失敗的通過情況
            if (
                expected_success is False
                and request_payload.get("action") == "validate_query"
                and result_data
                and isinstance(result_data, dict)
            ):
                # 檢查 valid 欄位
                valid_val = result_data.get("valid")
                if valid_val is None and isinstance(result_data.get("result"), dict):
                    valid_val = result_data["result"].get("valid")
                if valid_val is False:
                    # valid=False，視為通過（成功檢測到問題）
                    record["passed"] = True
                else:
                    record["notes"].append(
                        f"預期成功={expected_success}，實際={record['actual_success']}"
                    )
            # 特殊處理 2：text_to_sql 授權檢查
            elif (
                expected_success is False
                and request_payload.get("action") == "text_to_sql"
                and record["error"]
                and "未被授權做資料查詢以外的變更操作" in record["error"]
            ):
                # 授權檢測成功，視為通過
                record["passed"] = True
            # 特殊處理 3：text_to_sql 語義檢查
            elif (
                expected_success is False
                and request_payload.get("action") == "text_to_sql"
                and record["error"]
                and "語義理解不清楚" in record["error"]
            ):
                # 語義檢測成功，視為通過
                record["passed"] = True
            else:
                record["notes"].append(
                    f"預期成功={expected_success}，實際={record['actual_success']}"
                )
        else:
            record["passed"] = True

        # 異常場景：預期錯誤訊息包含
        if expected_error_contains and record["error"]:
            for kw in expected_error_contains:
                if kw.lower() not in (record["error"] or "").lower():
                    record["notes"].append(f"預期錯誤含「{kw}」")
                    record["passed"] = False
        if expected_error_contains and expected_success is False and not record["error"]:
            record["notes"].append("預期有錯誤訊息但為空")
            record["passed"] = False

        # SQL 關鍵字檢查（text_to_sql）
        if check_sql and record.get("generated_sql") and expected_keywords:
            sql_lower = (record["generated_sql"] or "").upper()

            # 檢查是否使用了參數化查詢
            is_parameterized = "?" in sql_lower or "$" in sql_lower

            for kw in expected_keywords:
                # 特殊處理 1：接受 IN 作為 OR 的等效語法（T2S-003）
                if kw.upper() == "OR" and sid == "T2S-003":
                    if "IN " in sql_lower:
                        # 如果使用 IN，視為通過
                        continue
                # 特殊處理 2：參數化查詢使用 ? 或 $1 等時不檢查字面值
                if is_parameterized and kw.startswith(("'", '"', "“", "”")):
                    # 如果使用參數化查詢，跳過字符串字面值關鍵字檢查
                    continue
                # 特殊處理 3：料號欄位可以是 img01 或 ima01（等效）
                if kw == "img01" and ("IMG01" in sql_lower or "IMA01" in sql_lower):
                    # 如果使用了任一料號欄位，視為通過
                    continue
                # 特殊處理 4：倉庫欄位可以是 img02 或 ima08（等效）
                if kw == "img02" and ("IMG02" in sql_lower or "IMA08" in sql_lower):
                    # 如果使用了任一倉庫欄位，視為通過
                    continue
                if kw.upper() not in sql_lower:
                    record["notes"].append(f"SQL 未含預期關鍵字: {kw}")
                    record["passed"] = False

        # 危險 SQL 檢查
        if check_no_dangerous and record.get("generated_sql"):
            d = (record["generated_sql"] or "").upper()
            if "DROP" in d or "DELETE" in d or "TRUNCATE" in d:
                record["notes"].append("產出含危險關鍵字")
                record["passed"] = False

        # validate 結果檢查
        if scenario.get("expected_valid") is not None:
            valid_val = None
            if result_data and isinstance(result_data, dict):
                valid_val = result_data.get("valid")
                if valid_val is None and isinstance(result_data.get("result"), dict):
                    valid_val = result_data["result"].get("valid")
            if valid_val != scenario["expected_valid"]:
                record["notes"].append(f"預期 valid={scenario['expected_valid']}，實際={valid_val}")
                record["passed"] = False
            # valid 符合預期時不改寫 passed（由其他檢查決定）

        # 耗時
        if duration > timeout_threshold:
            record["notes"].append(f"耗時 {duration:.2f}s 超過閾值 {timeout_threshold}s")
            record["passed"] = False

        if run_twice and record["passed"]:
            req2 = AgentServiceRequest(
                task_id=f"run_{sid}_2",
                task_type="data_agent",
                task_data=request_payload,
                context=None,
                metadata=None,
            )
            t1 = time.perf_counter()
            resp2 = await agent.execute(req2)
            d2 = time.perf_counter() - t1
            r2 = resp2.result or {}
            sql2 = None
            if isinstance(r2, dict) and isinstance(r2.get("result"), dict):
                sql2 = (r2["result"].get("sql_query") or "")[:300]
            if (
                record.get("generated_sql")
                and sql2
                and (record["generated_sql"] or "").strip() != (sql2 or "").strip()
            ):
                record["notes"].append("重複呼叫 SQL 不一致（可接受小幅差異）")
            record["duration_sec"] = (record["duration_sec"] or 0) + round(d2, 3)

        if then_validate and record["actual_success"] and record.get("generated_sql"):
            req_v = AgentServiceRequest(
                task_id=f"run_{sid}_validate",
                task_type="data_agent",
                task_data={"action": "validate_query", "query": record["generated_sql"]},
                context=None,
                metadata=None,
            )
            resp_v = await agent.execute(req_v)
            rv = resp_v.result or {}
            valid_v = rv.get("valid") if isinstance(rv, dict) else None
            if isinstance(rv, dict) and isinstance(rv.get("result"), dict):
                valid_v = rv["result"].get("valid")
            if not valid_v:
                record["notes"].append("混合流程 validate_query 未通過")
                record["passed"] = False

        if then_execute and record["actual_success"] and record.get("generated_sql"):
            req_e = AgentServiceRequest(
                task_id=f"run_{sid}_execute",
                task_type="data_agent",
                task_data={
                    "action": "execute_query",
                    "sql_query": record["generated_sql"],
                    "max_rows": 10,
                },
                context=None,
                metadata=None,
            )
            resp_e = await agent.execute(req_e)
            if resp_e.status != "completed":
                record["notes"].append(f"混合流程 execute_query 失敗: {resp_e.error}")
                record["passed"] = False

    except Exception as e:
        record["error"] = str(e)
        record["actual_success"] = False
        if expected_success:
            record["notes"].append(f"未預期異常: {e}")
        else:
            record["passed"] = True  # 預期失敗且確實拋錯
    return record


def fix_t2s049_t2s050(record: Dict[str, Any], scenario: Dict[str, Any]) -> None:
    """T2S-049/050 的 expected_valid 與 passed 邏輯已在 run_one 內處理。"""
    pass


async def main() -> None:
    """執行 50 場景並輸出摘要。"""
    scenarios = build_scenarios()
    agent = DataAgent()
    results: List[Dict[str, Any]] = []
    passed = 0
    failed = 0

    print("Data-Agent 50 場景測試（對應 Data-Agent-50場景測試計劃.md）")
    print("=" * 60)

    for i, scenario in enumerate(scenarios, 1):
        sid = scenario["scenario_id"]
        print(f"\n[{i}/50] {sid} {scenario.get('category', '')}")
        try:
            record = await run_one(agent, scenario, i)
            # T2S-034：空 task_data 導致失敗即符合預期
            if sid == "T2S-034" and (record.get("actual_success") is False or record.get("error")):
                record["passed"] = True
            # T2S-035 已在 run_one 內以 ValidationError 判定通過
            results.append(record)
            if record.get("passed"):
                passed += 1
                print(f"  通過 (耗時: {record.get('duration_sec')}s)")
            else:
                failed += 1
                print(f"  失敗 {record.get('notes')} {record.get('error') or ''}")
        except Exception as e:
            failed += 1
            results.append(
                {"scenario_id": sid, "passed": False, "error": str(e), "notes": ["執行異常"]}
            )
            print(f"  異常: {e}")

    print("\n" + "=" * 60)
    print(f"總計: 50，通過: {passed}，失敗: {failed}")

    # 使用時間戳生成結果文件名
    import datetime as dt

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = _script_dir / f"run_50_scenarios_results_round5_{timestamp}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"summary": {"total": 50, "passed": passed, "failed": failed}, "results": results},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"結果已寫入: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
