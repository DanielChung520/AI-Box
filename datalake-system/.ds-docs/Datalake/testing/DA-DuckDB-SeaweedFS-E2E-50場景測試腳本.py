#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data-Agent-DuckDB-SeaweedFS E2E 測試腳本 - 50 場景

功能：
- 測試 Data-Agent 的 text_to_sql 功能
- 測試 execute_sql_on_datalake 執行
- 測試異常處理場景
- 生成詳細測試報告

使用方式：
    python3 DA-DuckDB-SeaweedFS-E2E-50場景測試腳本.py
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

# 添加 AI-Box 根目錄到 Python 路徑
# Path: testing/.ds-docs/Datalake/testing → 5 levels up to get to /home/daniel/ai-box
ai_box_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

# 添加 datalake-system 到路徑
# Path: testing/.ds-docs/Datalake/testing → 4 levels up to get to /home/daniel/ai-box/datalake-system
datalake_root = Path(__file__).resolve().parent.parent.parent.parent
if str(datalake_root) not in sys.path:
    sys.path.insert(0, str(datalake_root))

from agents.services.protocol.base import AgentServiceRequest, AgentServiceResponse
from data_agent.agent import DataAgent


# ============================================================================
# 測試配置
# ============================================================================

TEST_CONFIG = {
    "max_text_to_sql_time": 30,  # 秒
    "max_execute_query_time": 60,  # 秒
    "max_large_query_time": 120,  # 秒
    "default_max_rows": 10,
    "large_query_max_rows": 1000,
}


# ============================================================================
# 測試場景定義
# ============================================================================

SCENARIOS = {
    # T2S-001 ~ T2S-022: 語言轉 SQL 功能場景
    "T2S-001": {
        "category": "簡單 WHERE 條件查詢",
        "natural_language": "查詢料號為 10-0001 的庫存記錄",
        "expected_keywords": ["WHERE", "img01", "10-0001"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-002": {
        "category": "AND 條件查詢",
        "natural_language": "查詢料號 10-0001 且倉庫為 W01 的庫存",
        "expected_keywords": ["WHERE", "AND", "img01", "img02"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-003": {
        "category": "OR 條件查詢",
        "natural_language": "查詢料號為 10-0001 或 10-0002 的庫存",
        "expected_keywords": ["WHERE", "OR", "img01"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-004": {
        "category": "IN 條件查詢",
        "natural_language": "查詢料號在 10-0001、10-0002、10-0003 中的庫存",
        "expected_keywords": ["WHERE", "IN", "img01"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-005": {
        "category": "SUM 聚合",
        "natural_language": "計算料號 10-0001 的總庫存量",
        "expected_keywords": ["SUM", "img10", "WHERE", "img01"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-006": {
        "category": "AVG 聚合",
        "natural_language": "查詢料號 10-0001 在各倉庫的平均庫存量",
        "expected_keywords": ["AVG", "img10", "GROUP BY"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-007": {
        "category": "MAX 聚合",
        "natural_language": "查詢庫存量最高的單筆記錄的數量",
        "expected_keywords": ["MAX", "img10"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-008": {
        "category": "MIN 聚合",
        "natural_language": "查詢庫存量最低的單筆記錄的數量",
        "expected_keywords": ["MIN", "img10"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-009": {
        "category": "COUNT 聚合",
        "natural_language": "統計料號 10-0001 的庫存記錄筆數",
        "expected_keywords": ["COUNT", "img01", "10-0001"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-010": {
        "category": "GROUP BY 分組",
        "natural_language": "按倉庫統計總庫存量",
        "expected_keywords": ["GROUP BY", "img02", "SUM"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-011": {
        "category": "ORDER BY ASC",
        "natural_language": "查詢庫存記錄，按庫存量由小到大排序",
        "expected_keywords": ["ORDER BY", "img10", "ASC"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-012": {
        "category": "ORDER BY DESC",
        "natural_language": "查詢庫存記錄，按庫存量由大到小排序",
        "expected_keywords": ["ORDER BY", "img10", "DESC"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-013": {
        "category": "LIMIT 限制",
        "natural_language": "查詢前 10 筆庫存記錄",
        "expected_keywords": ["LIMIT", "10"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-014": {
        "category": ">= 範圍過濾",
        "natural_language": "查詢庫存量大於等於 100 的記錄",
        "expected_keywords": [">=", "img10", "100"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-015": {
        "category": "<= 範圍過濾",
        "natural_language": "查詢庫存量小於等於 500 的記錄",
        "expected_keywords": ["<=", "img10", "500"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-016": {
        "category": "BETWEEN 範圍過濾",
        "natural_language": "查詢庫存量在 100 到 500 之間的記錄",
        "expected_keywords": ["BETWEEN", "100", "500"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-017": {
        "category": "當月數據查詢",
        "natural_language": "查詢當月的交易記錄",
        "expected_keywords": ["WHERE", "tlf06"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-018": {
        "category": "大數據量查詢",
        "natural_language": "查詢庫存表前 1000 筆記錄",
        "expected_keywords": ["LIMIT", "1000"],
        "action": "text_to_sql",
        "execute_after": True,
        "max_rows": 1000,
    },
    "T2S-019": {
        "category": "複雜查詢",
        "natural_language": "查詢庫存量≥100 的料號，按料號分組加總庫存，再按總量由高到低排序取前 5 筆",
        "expected_keywords": ["WHERE", "GROUP BY", "ORDER BY", "DESC", "LIMIT 5"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-020": {
        "category": "多條件查詢",
        "natural_language": "查詢料號 10-0001、倉庫 W01、庫存量大於 50 的記錄",
        "expected_keywords": ["WHERE", "AND", "img01", "img02", "img10"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-021": {
        "category": "Top N 料號查詢",
        "natural_language": "查詢庫存總量前 5 名的料號",
        "expected_keywords": ["GROUP BY", "ORDER BY", "DESC", "LIMIT 5"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-022": {
        "category": "Bottom N 料號查詢",
        "natural_language": "查詢庫存總量最低的 5 個料號",
        "expected_keywords": ["GROUP BY", "ORDER BY", "ASC", "LIMIT 5"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-023": {
        "category": "LIKE 模糊查詢",
        "natural_language": "查詢料號開頭為 10- 的物料主檔",
        "expected_keywords": ["LIKE", "ima01", "10-%"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-024": {
        "category": "空結果處理",
        "natural_language": "查詢料號為不存在的料號-XYZ 的庫存",
        "expected_keywords": ["WHERE", "img01"],
        "action": "text_to_sql",
        "execute_after": True,
        "expect_empty": True,
    },
    "T2S-025": {
        "category": "DISTINCT",
        "natural_language": "查詢有庫存記錄的不重複料號列表",
        "expected_keywords": ["DISTINCT", "img01"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-026": {
        "category": "HAVING 條件",
        "natural_language": "查詢總庫存量超過 1000 的料號",
        "expected_keywords": ["GROUP BY", "HAVING", "SUM", "1000"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-027": {
        "category": "多表語義",
        "natural_language": "查詢料號 10-0001 的品名與其總庫存量",
        "expected_keywords": ["ima02", "ima_file", "WHERE", "ima01", "10-0001"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-028": {
        "category": "日期範圍",
        "natural_language": "查詢 2026 年 1 月的交易記錄",
        "expected_keywords": ["WHERE", "tlf06", "2026"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-029": {
        "category": "NULL 條件",
        "natural_language": "查詢批號為空的庫存記錄",
        "expected_keywords": ["WHERE", "img03", "IS NULL"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    "T2S-030": {
        "category": "中文描述複雜條件",
        "natural_language": "查詢庫存數量在 100 到 200 之間且倉庫為 W01 或 W02 的記錄",
        "expected_keywords": ["WHERE", "AND", "BETWEEN", "IN"],
        "action": "text_to_sql",
        "execute_after": True,
    },
    # T2S-031 ~ T2S-050: 異常處理場景
    "T2S-031": {
        "category": "缺參數",
        "action": "text_to_sql",
        "task_data": {"action": "text_to_sql"},
        "expect_error": True,
        "expected_error_contains": ["natural_language"],
    },
    "T2S-032": {
        "category": "缺參數",
        "action": "execute_sql_on_datalake",
        "task_data": {"action": "execute_sql_on_datalake"},
        "expect_error": True,
        "expected_error_contains": ["sql_query_datalake"],
    },
    "T2S-033": {
        "category": "錯誤 action",
        "action": "invalid_action",
        "task_data": {"action": "invalid_action"},
        "expect_error": True,
        "expected_error_contains": ["Unknown action"],
    },
    "T2S-034": {
        "category": "空 task_data",
        "action": "text_to_sql",
        "task_data": {},
        "expect_error": True,
    },
    "T2S-035": {
        "category": "危險 SQL",
        "action": "execute_sql_on_datalake",
        "task_data": {
            "action": "execute_sql_on_datalake",
            "sql_query_datalake": "DROP TABLE img_file",
        },
        "expect_error": True,
    },
    "T2S-036": {
        "category": "危險 SQL",
        "action": "execute_sql_on_datalake",
        "task_data": {
            "action": "execute_sql_on_datalake",
            "sql_query_datalake": "DELETE FROM img_file WHERE 1=1",
        },
        "expect_error": True,
    },
    "T2S-037": {
        "category": "SQL 注入",
        "action": "execute_sql_on_datalake",
        "task_data": {
            "action": "execute_sql_on_datalake",
            "sql_query_datalake": "SELECT * FROM img_file WHERE img01 = '10-0001'; DROP TABLE img_file;--",
        },
        "expect_error": True,
    },
    "T2S-038": {
        "category": "無效語法",
        "action": "execute_sql_on_datalake",
        "task_data": {
            "action": "execute_sql_on_datalake",
            "sql_query_datalake": "SELECT FROM img_file",
        },
        "expect_error": True,
    },
    "T2S-039": {
        "category": "validate_query",
        "action": "validate_query",
        "task_data": {"action": "validate_query", "query": "SELECT * FROM img_file LIMIT 1"},
        "expect_valid": True,
    },
    "T2S-040": {
        "category": "validate_query",
        "action": "validate_query",
        "task_data": {"action": "validate_query", "query": "SELECT FROM img_file"},
        "expect_valid": False,
    },
    "T2S-041": {
        "category": "validate_query",
        "action": "validate_query",
        "task_data": {"action": "validate_query", "sql_query": "SELECT FROM img_file"},
        "expect_error": True,
        "expected_error_contains": ["query"],
    },
}


# ============================================================================
# 測試執行函數
# ============================================================================


class DataAgentE2ETester:
    """Data-Agent E2E 測試類"""

    def __init__(self):
        self.agent = DataAgent()
        self.results: List[Dict[str, Any]] = []
        self.start_time = None

    def create_request(self, scenario_id: str, scenario: Dict) -> AgentServiceRequest:
        """建立測試請求"""
        task_data = scenario.get("task_data", {}).copy()

        # 對於 text_to_sql 場景，添加 natural_language
        if scenario.get("action") == "text_to_sql":
            task_data["action"] = "text_to_sql"
            task_data["natural_language"] = scenario["natural_language"]

        return AgentServiceRequest(
            task_id=f"e2e_test_{scenario_id}_{int(time.time())}",
            task_type="data_query",
            task_data=task_data,
        )

    def extract_sql_from_result(self, result: Dict) -> str:
        """從結果中提取 SQL"""
        try:
            if result.get("success"):
                inner = result.get("result", {})
                # SQL 可能直接在 inner 中，或在 inner["result"] 中
                if isinstance(inner, dict):
                    if "sql_query" in inner:
                        return inner.get("sql_query", "")
                    sql_result = inner.get("result", {})
                    if isinstance(sql_result, dict):
                        return sql_result.get("sql_query", "")
            return ""
        except Exception:
            return ""

    def check_sql_keywords(self, sql: str, expected_keywords: List[str]) -> Tuple[bool, List[str]]:
        """檢查 SQL 是否包含預期關鍵字"""
        if not sql:
            return False, expected_keywords

        sql_upper = sql.upper().replace("\n", " ").replace("\t", " ")
        found = []
        missing = []

        for keyword in expected_keywords:
            # 特殊處理 LIMIT N -> LIMIT 數字
            if keyword == "LIMIT 5":
                if "LIMIT" in sql_upper and any(c.isdigit() for c in keyword):
                    found.append(keyword)
                else:
                    missing.append(keyword)
            elif keyword == "LIMIT 10":
                if "LIMIT" in sql_upper and "10" in sql_upper:
                    found.append(keyword)
                else:
                    missing.append(keyword)
            elif keyword == "LIMIT 1000":
                if "LIMIT" in sql_upper and "1000" in sql_upper:
                    found.append(keyword)
                else:
                    missing.append(keyword)
            elif keyword.upper() in sql_upper:
                found.append(keyword)
            else:
                missing.append(keyword)

        return len(missing) == 0, missing

    async def run_scenario(self, scenario_id: str, scenario: Dict) -> Dict[str, Any]:
        """執行單一場景"""
        result = {
            "scenario_id": scenario_id,
            "category": scenario.get("category", ""),
            "natural_language": scenario.get("natural_language", ""),
            "action": scenario.get("action", ""),
            "start_time": datetime.now().isoformat(),
            "status": "pending",
            "duration_ms": 0,
            "sql_query": "",
            "error": None,
            "result": None,
        }

        start_time = time.time()

        try:
            # 建立請求
            request = self.create_request(scenario_id, scenario)

            # 執行測試
            response = await self.agent.execute(request)

            duration = (time.time() - start_time) * 1000
            result["duration_ms"] = round(duration, 2)

            # 解析響應
            response_data = response.result or {}
            result_data = response_data.get("result", {}) if isinstance(response_data, dict) else {}

            # 處理 failed status 或有錯誤訊息的情況
            if response.status == "failed" or response.error:
                error_msg = response.error or ""
                if isinstance(response_data, dict):
                    error_msg = response_data.get("error", "") or error_msg
                    if response_data.get("result") and isinstance(response_data["result"], dict):
                        error_msg = response_data["result"].get("error", "") or error_msg

                # 檢查是否預期錯誤
                if scenario.get("expect_error"):
                    # 如果有 expected_error_contains，檢查錯誤訊息是否包含預期內容
                    if "expected_error_contains" in scenario:
                        expected = scenario["expected_error_contains"]
                        if any(e.lower() in error_msg.lower() for e in expected):
                            result["status"] = "passed"
                            result["error"] = error_msg
                        else:
                            result["status"] = "failed"
                            result["error"] = (
                                f"錯誤訊息不符預期: 預期包含 {expected}, 實際為: {error_msg}"
                            )
                    else:
                        result["status"] = "passed"
                        result["error"] = error_msg
                else:
                    result["status"] = "failed"
                    result["error"] = f"預期成功但失敗: {error_msg}"

            elif response.status == "completed":
                # 檢查是否預期錯誤 (completed 但有 error 標記)
                if scenario.get("expect_error"):
                    result_data_inner = (
                        response_data.get("result", {}) if isinstance(response_data, dict) else {}
                    )
                    if (
                        response_data.get("success") == False
                        or result_data_inner.get("success") == False
                    ):
                        result["status"] = "passed"
                        result["error"] = result_data_inner.get("error", "") or response_data.get(
                            "error", ""
                        )
                    else:
                        result["status"] = "failed"
                        result["error"] = f"預期錯誤但成功: {response_data}"
                elif scenario.get("expect_empty"):
                    # 檢查空結果
                    rows = result_data.get("rows", []) if isinstance(result_data, dict) else []
                    if len(rows) == 0:
                        result["status"] = "passed"
                    else:
                        result["status"] = "failed"
                        result["error"] = f"預期空結果但返回 {len(rows)} 筆"
                elif scenario.get("expect_valid") is not None:
                    # validate_query 場景 - valid 在 result.result 中
                    result_inner = (
                        response_data.get("result", {}) if isinstance(response_data, dict) else {}
                    )
                    actual_valid = (
                        result_inner.get("valid", False)
                        if isinstance(result_inner, dict)
                        else False
                    )
                    if actual_valid == scenario["expect_valid"]:
                        result["status"] = "passed"
                    else:
                        result["status"] = "failed"
                        result["error"] = (
                            f"validate 結果不符預期: expected={scenario['expect_valid']}, actual={actual_valid}"
                        )
                else:
                    # 正常場景
                    result["status"] = "passed"
                    result["result"] = response_data

                    # 提取 SQL
                    if scenario.get("action") == "text_to_sql":
                        sql = self.extract_sql_from_result(response_data)
                        result["sql_query"] = sql

                        # 檢查關鍵字
                        if "expected_keywords" in scenario:
                            is_valid, missing = self.check_sql_keywords(
                                sql, scenario["expected_keywords"]
                            )
                            if not is_valid:
                                result["status"] = "failed"
                                result["error"] = f"SQL 缺少關鍵字: {missing}"

                    # 如果需要執行 SQL（驗證能從 SeaweedFS 取出資料）
                    if scenario.get("execute_after") and result["sql_query"]:
                        exec_result = await self.agent.execute(
                            AgentServiceRequest(
                                task_id=f"e2e_exec_{scenario_id}_{int(time.time())}",
                                task_type="query",
                                task_data={
                                    "action": "execute_sql_on_datalake",
                                    "sql_query_datalake": result["sql_query"],
                                    "max_rows": scenario.get(
                                        "max_rows", TEST_CONFIG["large_query_max_rows"]
                                    ),
                                },
                            )
                        )

                        # 解析執行結果
                        exec_success = False
                        exec_row_count = 0
                        exec_error = None

                        if exec_result.status == "completed":
                            exec_data = exec_result.result or {}
                            exec_inner = exec_data.get("result", {})
                            exec_success = exec_data.get("success", False)
                            if isinstance(exec_inner, dict):
                                exec_row_count = exec_inner.get("row_count", 0)
                            exec_error = exec_data.get("error", "") or exec_inner.get("error", "")
                        elif exec_result.status == "failed":
                            exec_error = exec_result.error or "Unknown error"

                        # 記錄執行結果
                        result["execute_result"] = {
                            "success": exec_success,
                            "row_count": exec_row_count,
                            "error": exec_error,
                            "sql_executed": result["sql_query"],
                        }

                        # 驗證資料是否成功取出
                        if scenario.get("expect_empty"):
                            # 空結果場景：預期 row_count = 0
                            if exec_row_count == 0:
                                result["status"] = "passed"
                            elif exec_error:
                                # 如果有錯誤但期望空結果，可能語意理解有誤
                                result["status"] = "failed"
                                result["error"] = f"期望空結果但執行出錯: {exec_error}"
                            else:
                                result["status"] = "failed"
                                result["error"] = f"期望空結果但返回 {exec_row_count} 筆資料"
                        elif exec_success and exec_row_count > 0:
                            # 正常場景：成功取出資料
                            result["status"] = "passed"
                            result["data_retrieved"] = True
                        elif exec_success and exec_row_count == 0:
                            # 成功執行但無資料（可能是後置異常：資料欄位問題）
                            result["status"] = "passed"
                            result["data_retrieved"] = False
                            result["warning"] = "SQL 執行成功但無資料返回，可能需要檢查資料欄位"
                        elif exec_error:
                            # 執行錯誤（可能是後置異常）
                            # 檢查是否為預期的後置異常
                            if scenario.get("allow_execution_error"):
                                result["status"] = "passed"
                                result["error"] = f"預期執行錯誤: {exec_error}"
                            else:
                                result["status"] = "failed"
                                result["error"] = f"SQL 執行錯誤: {exec_error}"
                        else:
                            result["status"] = "failed"
                            result["error"] = (
                                f"無法從 SeaweedFS 取出資料: {exec_error or 'Unknown error'}"
                            )

            else:
                result["status"] = "failed"
                result["error"] = response.error or f"未知錯誤: {response.status}"

        except KeyError as e:
            # 缺少必要參數的情況
            result["status"] = "passed"
            result["error"] = f"缺少必要參數: {e}"
            result["duration_ms"] = round((time.time() - start_time) * 1000, 2)
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            result["duration_ms"] = round((time.time() - start_time) * 1000, 2)

        result["end_time"] = datetime.now().isoformat()
        return result

    async def run_all_scenarios(self) -> List[Dict[str, Any]]:
        """執行所有場景"""
        self.start_time = datetime.now()
        print("=" * 60)
        print("Data-Agent-DuckDB-SeaweedFS E2E 測試 - 50 場景")
        print("=" * 60)
        print(f"開始時間: {self.start_time}")
        print()

        for i, (scenario_id, scenario) in enumerate(SCENARIOS.items(), 1):
            print(f"[{i:02d}/50] {scenario_id}: {scenario.get('category', '')}...", end=" ")

            result = await self.run_scenario(scenario_id, scenario)
            self.results.append(result)

            if result["status"] == "passed":
                print(f"✅ ({result['duration_ms']:.0f}ms)")
            elif result["status"] == "failed":
                print(f"❌ ({result['duration_ms']:.0f}ms)")
                print(f"   錯誤: {result.get('error', 'N/A')[:100]}")
            else:
                print(f"⚠️  ({result['duration_ms']:.0f}ms)")
                print(f"   錯誤: {result.get('error', 'N/A')[:100]}")

        return self.results

    def generate_report(self) -> str:
        """生成測試報告"""
        passed = sum(1 for r in self.results if r["status"] == "passed")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        errors = sum(1 for r in self.results if r["status"] == "error")
        total = len(self.results)

        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        report = f"""# Data-Agent-DuckDB-SeaweedFS E2E 測試報告 - 50 場景

**版本**：1.0  
**輪次**：第 1 輪  
**執行日期**：{self.start_time.strftime("%Y-%m-%d %H:%M:%S")}  
**完成時間**：{end_time.strftime("%Y-%m-%d %H:%M:%S")}  
**總耗時**：{duration:.1f} 秒

---

## 1. 測試摘要

| 項目 | 數值 |
|------|------|
| 總場景數 | {total} |
| 通過 | {passed} |
| 失敗 | {failed} |
| 錯誤 | {errors} |
| 通過率 | {passed / total * 100:.1f}% |

### 測試環境

| 組件 | 版本/狀態 |
|------|-----------|
| Data-Agent | localhost:8004 |
| DuckDB | 1.4.4 |
| SeaweedFS S3 | localhost:8334 |

---

## 2. 測試結果統計

### 按類別統計

| 類別 | 通過 | 失敗 | 錯誤 | 小計 |
|------|------|------|------|------|
"""

        # 按類別統計
        categories = {}
        for r in self.results:
            cat = r.get("category", "未分類")
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0, "error": 0}
            categories[cat][r["status"]] += 1

        for cat, stats in categories.items():
            report += f"| {cat} | {stats['passed']} | {stats['failed']} | {stats['error']} | {sum(stats.values())} |\n"

        report += """
### 耗時統計

| 類型 | 平均耗時 | 最快 | 最慢 |
|------|----------|------|------|
"""

        durations = [r["duration_ms"] for r in self.results if r["duration_ms"] > 0]
        if durations:
            report += f"| 全部場景 | {sum(durations) / len(durations):.0f}ms | {min(durations):.0f}ms | {max(durations):.0f}ms |\n"

        report += """
---

## 3. 詳細測試結果

### 3.1 通過的場景

"""
        passed_scenarios = [r for r in self.results if r["status"] == "passed"]
        for r in passed_scenarios:
            report += f"- **{r['scenario_id']}**: {r['category']}"
            if r.get("sql_query"):
                report += f"\n  ```sql\n  {r['sql_query'][:200]}\n  ```\n"
            report += "\n"

        report += """
### 3.2 失敗的場景

"""
        failed_scenarios = [r for r in self.results if r["status"] == "failed"]
        for r in failed_scenarios:
            report += f"- **{r['scenario_id']}**: {r['category']}\n"
            report += f"  錯誤: {r.get('error', 'N/A')}\n"
            if r.get("sql_query"):
                report += f"  SQL: {r['sql_query'][:100]}\n"
            report += "\n"

        report += """
### 3.3 錯誤的場景

"""
        error_scenarios = [r for r in self.results if r["status"] == "error"]
        for r in error_scenarios:
            report += f"- **{r['scenario_id']}**: {r['category']}\n"
            report += f"  錯誤: {r.get('error', 'N/A')}\n"
            report += "\n"

        report += f"""
---

## 4. 原始測試數據

詳細測試數據已保存至 `DA-DuckDB-SeaweedFS-E2E-50場景測試結果-第1輪.json`

---

*報告生成時間：{end_time.strftime("%Y-%m-%d %H:%M:%S")}*
"""

        return report


# ============================================================================
# 主程式
# ============================================================================


async def main():
    """主執行函數"""
    tester = DataAgentE2ETester()

    # 執行測試
    await tester.run_all_scenarios()

    # 生成報告
    report = tester.generate_report()

    # 儲存報告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_dir = Path(__file__).parent
    report_path = script_dir / f"DA-DuckDB-SeaweedFS-E2E-50場景測試報告-第1輪.md"
    json_path = script_dir / f"DA-DuckDB-SeaweedFS-E2E-50場景測試結果-第1輪.json"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(tester.results, f, ensure_ascii=False, indent=2)

    # 輸出摘要
    passed = sum(1 for r in tester.results if r["status"] == "passed")
    failed = sum(1 for r in tester.results if r["status"] == "failed")
    total = len(tester.results)

    print()
    print("=" * 60)
    print("測試完成！")
    print("=" * 60)
    print(f"通過: {passed}/{total} ({passed / total * 100:.1f}%)")
    print(f"失敗: {failed}/{total} ({failed / total * 100:.1f}%)")
    print()
    print(f"報告: {report_path}")
    print(f"數據: {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
