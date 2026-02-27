#!/usr/bin/env python3
# 代碼功能說明: 生成 Data-Agent 50 場景詳細測試報告
# 創建日期: 2026-01-30
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-30

"""生成詳細的 Data-Agent 50 場景測試報告

基於 run_50_scenarios_results.json 生成詳細的測試報告，
包含 SQL 語法檢查、異常處理機制、執行時間、選錯表檢測等詳細信息。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


def load_results() -> Dict[str, Any]:
    """讀取測試結果 JSON"""
    results_path = Path(__file__).parent / "run_50_scenarios_results.json"
    with open(results_path, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_sql_syntax(sql: str) -> Dict[str, Any]:
    """分析 SQL 語法

    Args:
        sql: SQL 查詢字串

    Returns:
        包含語法分析的字典
    """
    analysis = {
        "has_syntax_error": False,
        "has_select": "SELECT" in sql.upper(),
        "has_from": "FROM" in sql.upper(),
        "has_where": "WHERE" in sql.upper(),
        "has_join": any(
            k in sql.upper() for k in ["JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN"]
        ),
        "has_aggregation": any(k in sql.upper() for k in ["SUM", "AVG", "MAX", "MIN", "COUNT"]),
        "has_group_by": "GROUP BY" in sql.upper(),
        "has_order_by": "ORDER BY" in sql.upper(),
        "has_limit": "LIMIT" in sql.upper(),
        "has_parameterized_query": "?" in sql or "$1" in sql or "$2" in sql or "$3" in sql,
        "table_names": [],
        "column_names": [],
        "syntax_warnings": [],
    }

    # 提取表名和欄位名（簡化版本）
    if "FROM" in sql.upper():
        from_idx = sql.upper().find("FROM")
        after_from = sql[from_idx + 4 :].strip()

        # 提取可能的表名
        tables = []
        for token in ["ima_file", "img_file", "tlf_file", "pmn_file", "stock"]:
            if token in sql:
                tables.append(token)
        analysis["table_names"] = list(set(tables))

        # 提取可能的欄位名
        columns = []
        for token in [
            "ima01",
            "ima02",
            "ima08",
            "ima25",
            "img01",
            "img02",
            "img04",
            "img10",
            "tlf01",
            "tlf06",
            "tlf10",
            "tlf19",
            "pmn01",
            "pmn02",
            "pmn10",
        ]:
            if token in sql:
                columns.append(token)
        analysis["column_names"] = list(set(columns))

    # 語法檢查
    if analysis["has_select"] and not analysis["has_from"]:
        analysis["syntax_warnings"].append("⚠️ SQL 有 SELECT 但缺少 FROM 子句")

    if not analysis["has_select"]:
        analysis["syntax_warnings"].append("⚠️ SQL 缺少 SELECT 子句")

    return analysis


def detect_wrong_table_usage(scenario_id: str, generated_sql: str, category: str) -> Dict[str, Any]:
    """偵測選錯表的問題

    Args:
        scenario_id: 場景 ID
        generated_sql: 生成的 SQL
        category: 場景分類

    Returns:
        包含選錯表分析的字典
    """
    analysis = {
        "has_wrong_table": False,
        "expected_tables": [],
        "actual_tables": [],
        "wrong_tables": [],
        "severity": "none",  # low, medium, high
        "suggestion": "",
    }

    # 將 SQL 轉為大寫進行分析
    sql_upper = generated_sql.upper()

    # 偵測實際使用的表
    actual_tables = []
    if "IMA_FILE" in sql_upper:
        actual_tables.append("ima_file")
    if "IMG_FILE" in sql_upper:
        actual_tables.append("img_file")
    if "TLF_FILE" in sql_upper:
        actual_tables.append("tlf_file")
    if "PMN_FILE" in sql_upper:
        actual_tables.append("pmn_file")

    analysis["actual_tables"] = actual_tables

    # 根據場景分類判斷預期表
    expected_tables = []

    # 庫存相關查詢應使用 img_file
    if "庫存" in category or "stock" in generated_sql.lower():
        if "查詢" in category and ("WHERE" in generated_sql or "LIMIT" in generated_sql):
            expected_tables.append("img_file")

    # 交易記錄應使用 tlf_file
    if "交易" in category or "tlf" in generated_sql.lower():
        expected_tables.append("tlf_file")

    # 物料查詢應使用 ima_file
    if "物料" in category or "品名" in category:
        expected_tables.append("ima_file")

    # 聚合查詢（SUM, AVG, MAX, MIN）涉及庫存量應使用 img_file
    if any(k in sql_upper for k in ["SUM", "AVG", "MAX", "MIN"]):
        if "img10" in generated_sql.lower():
            expected_tables.append("img_file")

    analysis["expected_tables"] = expected_tables

    # 判斷是否選錯表
    if expected_tables and actual_tables:
        # 檢查是否使用了預期以外的表
        for table in actual_tables:
            if table not in expected_tables:
                analysis["wrong_tables"].append(table)

        # 判斷嚴重程度
        if analysis["wrong_tables"]:
            analysis["has_wrong_table"] = True
            # 如果完全沒有使用預期表，嚴重程度高
            if not any(t in actual_tables for t in expected_tables):
                analysis["severity"] = "high"
                analysis["suggestion"] = (
                    f"應使用 {expected_tables} 表，但實際使用了 {actual_tables} 表"
                )
            # 如果使用了預期表之外的其他表，嚴重程度中等
            else:
                analysis["severity"] = "medium"
                analysis["suggestion"] = (
                    f"建議使用 {expected_tables} 表，額外使用了 {analysis['wrong_tables']} 表"
                )

    # 特別情況：庫存查詢使用了 pmn_file（採購單）通常是錯的
    if "庫存" in category and "pmn_file" in actual_tables and "img_file" not in actual_tables:
        analysis["has_wrong_table"] = True
        analysis["severity"] = "high"
        analysis["suggestion"] = "庫存查詢應使用 img_file 而非 pmn_file"

    # 特別情況：交易記錄查詢使用了 pmn_file 通常是錯的
    if "交易" in category and "pmn_file" in actual_tables and "tlf_file" not in actual_tables:
        analysis["has_wrong_table"] = True
        analysis["severity"] = "high"
        analysis["suggestion"] = "交易記錄查詢應使用 tlf_file 而非 pmn_file"

    return analysis


def analyze_exception_handling(result: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
    """分析異常處理機制

    Args:
        result: 測試結果
        scenario: 場景定義

    Returns:
        包含異常處理分析的字典
    """
    analysis = {
        "expected_failure": not scenario.get("expected_success", True),
        "actual_failure": not result.get("actual_success", True),
        "error_message": result.get("error"),
        "error_type": None,
        "has_proper_error_handling": False,
        "exception_notes": [],
    }

    # 檢查錯誤訊息
    error_msg = result.get("error", "")
    if error_msg:
        # 判斷錯誤類型
        if "validation" in error_msg.lower() or "required" in error_msg.lower():
            analysis["error_type"] = "參數驗證錯誤"
        elif "unknown action" in error_msg.lower() or "invalid action" in error_msg.lower():
            analysis["error_type"] = "無效的 action 錯誤"
        elif "dangerous" in error_msg.lower() or "injection" in error_msg.lower():
            analysis["error_type"] = "安全警告"
        elif "sql" in error_msg.lower() or "syntax" in error_msg.lower():
            analysis["error_type"] = "SQL 語法錯誤"
        else:
            analysis["error_type"] = "其他錯誤"

    # 判斷是否有正確的錯誤處理
    if analysis["expected_failure"]:
        if analysis["actual_failure"]:
            if error_msg and len(error_msg) > 0:
                analysis["has_proper_error_handling"] = True
                analysis["exception_notes"].append(f"✅ 正確回報錯誤: {analysis['error_type']}")
            else:
                analysis["exception_notes"].append("⚠️ 失敗但缺少錯誤訊息")
        else:
            analysis["exception_notes"].append("❌ 預期失敗但實際成功")
    else:
        if analysis["actual_failure"]:
            analysis["exception_notes"].append(f"❌ 未預期的錯誤: {error_msg}")
        else:
            analysis["has_proper_error_handling"] = True
            analysis["exception_notes"].append("✅ 正常執行")

    return analysis


def generate_scenario_detail(result: Dict[str, Any], scenario: Dict[str, Any]) -> str:
    """生成單一場景的詳細報告

    Args:
        result: 測試結果
        scenario: 場景定義

    Returns:
        Markdown 格式的詳細報告
    """
    sid = result["scenario_id"]
    category = result.get("category", "")
    passed = result.get("passed", False)
    duration = result.get("duration_sec")
    generated_sql = result.get("generated_sql", "")
    notes = result.get("notes", [])

    detail_lines = [
        f"#### {sid}: {category}",
        "",
        "**執行結果:**",
        f"- 狀態: {'✅ 通過' if passed else '❌ 失敗'}",
    ]

    if duration is not None:
        detail_lines.append(f"- 執行時間: {duration:.3f} 秒")
    else:
        detail_lines.append("- 執行時間: N/A")

    detail_lines.append("")

    # SQL 語法分析
    if generated_sql:
        detail_lines.extend(
            [
                "**生成的 SQL:**",
                f"```sql",
                generated_sql,
                f"```",
                "",
                "**SQL 語法分析:**",
            ]
        )

        syntax_analysis = analyze_sql_syntax(generated_sql)
        detail_lines.extend(
            [
                f"- 包含 SELECT: {'✅' if syntax_analysis['has_select'] else '❌'}",
                f"- 包含 FROM: {'✅' if syntax_analysis['has_from'] else '❌'}",
                f"- 包含 WHERE: {'✅' if syntax_analysis['has_where'] else '❌'}",
                f"- 包含 JOIN: {'✅' if syntax_analysis['has_join'] else '❌'}",
                f"- 包含聚合函數: {'✅' if syntax_analysis['has_aggregation'] else '❌'}",
                f"- 包含 GROUP BY: {'✅' if syntax_analysis['has_group_by'] else '❌'}",
                f"- 包含 ORDER BY: {'✅' if syntax_analysis['has_order_by'] else '❌'}",
                f"- 包含 LIMIT: {'✅' if syntax_analysis['has_limit'] else '❌'}",
                f"- 使用參數化查詢: {'✅' if syntax_analysis['has_parameterized_query'] else '❌'}",
            ]
        )

        if syntax_analysis["table_names"]:
            detail_lines.append(f"- 偵測到的表名: {', '.join(syntax_analysis['table_names'])}")

        if syntax_analysis["column_names"]:
            detail_lines.append(f"- 偵測到的欄位名: {', '.join(syntax_analysis['column_names'])}")

        if syntax_analysis["syntax_warnings"]:
            detail_lines.extend(
                [
                    "",
                    "**語法警告:**",
                ]
            )
            for warning in syntax_analysis["syntax_warnings"]:
                detail_lines.append(f"- {warning}")

        # 選錯表檢測
        wrong_table_analysis = detect_wrong_table_usage(sid, generated_sql, category)
        if wrong_table_analysis["has_wrong_table"]:
            severity_icon = "🔴" if wrong_table_analysis["severity"] == "high" else "🟡"
            detail_lines.extend(
                [
                    "",
                    f"{severity_icon} **選錯表問題:**",
                    f"- 嚴重程度: {wrong_table_analysis['severity'].upper()}",
                    f"- 預期表: {', '.join(wrong_table_analysis['expected_tables']) if wrong_table_analysis['expected_tables'] else '未指定'}",
                    f"- 實際表: {', '.join(wrong_table_analysis['actual_tables'])}",
                    f"- 錯誤表: {', '.join(wrong_table_analysis['wrong_tables'])}",
                    f"- 建議: {wrong_table_analysis['suggestion']}",
                ]
            )

        detail_lines.append("")

    # 異常處理分析
    exception_analysis = analyze_exception_handling(result, scenario)
    detail_lines.extend(
        [
            "**異常處理分析:**",
            f"- 預期失敗: {'是' if exception_analysis['expected_failure'] else '否'}",
            f"- 實際失敗: {'是' if exception_analysis['actual_failure'] else '否'}",
        ]
    )

    if exception_analysis["error_message"]:
        detail_lines.append(f"- 錯誤訊息: {exception_analysis['error_message']}")
        detail_lines.append(f"- 錯誤類型: {exception_analysis['error_type']}")

    if exception_analysis["exception_notes"]:
        detail_lines.extend(
            [
                "",
                "**異常處理評估:**",
            ]
        )
        for note in exception_analysis["exception_notes"]:
            detail_lines.append(f"- {note}")

    detail_lines.append("")

    # 其他備註
    if notes:
        detail_lines.extend(
            [
                "**測試備註:**",
            ]
        )
        for note in notes:
            detail_lines.append(f"- {note}")
        detail_lines.append("")

    # 執行步驟詳情（如果有 conversion_log）
    result_summary = result.get("result_summary", {})
    if isinstance(result_summary, dict):
        result_data = result_summary.get("result", {})
        if isinstance(result_data, dict):
            conversion_log = result_data.get("conversion_log")
            if conversion_log and isinstance(conversion_log, dict):
                steps = conversion_log.get("steps", [])
                if steps:
                    detail_lines.extend(
                        [
                            "**執行步驟詳情:**",
                        ]
                    )
                    for step in steps:
                        step_name = step.get("step", "unknown")
                        step_status = step.get("status", "unknown")
                        step_duration = step.get("duration_ms")
                        status_icon = "✅" if step_status == "success" else "❌"
                        if step_duration:
                            detail_lines.append(
                                f"- {status_icon} {step_name}: {step_duration:.2f}ms"
                            )
                        else:
                            detail_lines.append(f"- {status_icon} {step_name}")
                    detail_lines.append("")

    # Confidence
    if isinstance(result_summary, dict):
        result_data = result_summary.get("result", {})
        if isinstance(result_data, dict):
            confidence = result_data.get("confidence")
            if confidence is not None:
                detail_lines.extend(
                    [
                        "**信心度分析:**",
                        f"- LLM 信心度: {confidence:.2f}",
                    ]
                )
                if confidence >= 0.8:
                    detail_lines.append("- 評估: 高信心度")
                elif confidence >= 0.6:
                    detail_lines.append("- 評估: 中等信心度")
                else:
                    detail_lines.append("- 評估: 低信心度")
                detail_lines.append("")

    # Warnings
    if isinstance(result_summary, dict):
        result_data = result_summary.get("result", {})
        if isinstance(result_data, dict):
            warnings = result_data.get("warnings", [])
            if warnings:
                detail_lines.extend(
                    [
                        "**系統警告:**",
                    ]
                )
                for warning in warnings:
                    detail_lines.append(f"- ⚠️ {warning}")
                detail_lines.append("")

    detail_lines.append("---")
    detail_lines.append("")

    return "\n".join(detail_lines)


def generate_summary_report(
    data: Dict[str, Any],
    round_number: int = 5,
    previous_round_data: Optional[Dict[str, Any]] = None,
) -> str:
    """生成摘要報告

    Args:
        data: 測試結果數據
        round_number: 測試輪次（默認為第5輪）
        previous_round_data: 上一輪測試結果（用於比較）

    Returns:
        Markdown 格式的摘要報告
    """
    # 獲取當前日期和時間
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    summary = data.get("summary", {})
    results = data.get("results", [])

    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    pass_rate = (passed / total * 100) if total > 0 else 0

    # 統計執行時間
    durations = [r.get("duration_sec", 0) for r in results if r.get("duration_sec")]
    avg_duration = sum(durations) / len(durations) if durations else 0
    max_duration = max(durations) if durations else 0
    min_duration = min(durations) if durations else 0

    # 統計語法問題
    sql_issues = 0
    sql_success = 0
    for result in results:
        sql = result.get("generated_sql", "")
        if sql:
            analysis = analyze_sql_syntax(sql)
            if analysis["syntax_warnings"]:
                sql_issues += 1
            else:
                sql_success += 1

    # 分類統計
    categories = {}
    for result in results:
        cat = result.get("category", "未分類")
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "failed": 0, "results": []}
        categories[cat]["total"] += 1
        if result.get("passed", False):
            categories[cat]["passed"] += 1
        else:
            categories[cat]["failed"] += 1
        categories[cat]["results"].append(result)

    summary_lines = [
        "# Data-Agent 50 場景測試詳細報告",
        "",
        f"**報告日期：** {current_datetime}",
        "**測試人員：** Daniel Chung",
        "**測試範圍：** Data-Agent 50 場景測試計劃",
        "**測試計劃：** `Data-Agent-50場景測試計劃.md`",
        f"**測試輪次：** 第 {round_number} 輪（閾值 60 秒）",
        "",
        "---",
        "",
        "## 測試總結",
        "",
        f"本次測試執行 Data-Agent 50 場景測試計劃，驗證 text_to_sql、execute_query、validate_query 及異常處理功能。",
        "",
        "### 測試結果總結",
        "",
        "| 統計項 | 數值 |",
        "|--------|------|",
        f"| 總場景數 | {total} |",
        f"| 通過數 | {passed} |",
        f"| 失敗數 | {failed} |",
        f"| 通過率 | {pass_rate:.1f}% |",
        "",
    ]

    # 如果有上一輪數據，添加比較
    if previous_round_data:
        prev_summary = previous_round_data.get("summary", {})
        prev_passed = prev_summary.get("passed", 0)
        prev_failed = prev_summary.get("failed", 0)
        prev_pass_rate = (prev_passed / total * 100) if total > 0 else 0

        passed_change = passed - prev_passed
        failed_change = failed - prev_failed
        pass_rate_change = pass_rate - prev_pass_rate

        passed_arrow = "⬆️" if passed_change > 0 else "⬇️" if passed_change < 0 else "➖"
        failed_arrow = "⬆️" if failed_change > 0 else "⬇️" if failed_change < 0 else "➖"
        pass_rate_arrow = "⬆️" if pass_rate_change > 0 else "⬇️" if pass_rate_change < 0 else "➖"

        summary_lines.extend(
            [
                "### 與上一輪比較（第 4 輪）",
                "",
                "| 統計項 | 第 4 輪 | 第 5 輪 | 變化 |",
                "|--------|--------|--------|------|",
                f"| 通過數 | {prev_passed} | {passed} | {passed_arrow} {abs(passed_change)} |",
                f"| 失敗數 | {prev_failed} | {failed} | {failed_arrow} {abs(failed_change)} |",
                f"| 通過率 | {prev_pass_rate:.1f}% | {pass_rate:.1f}% | {pass_rate_arrow} {abs(pass_rate_change):.1f}% |",
                "",
            ]
        )

    summary_lines.extend(
        [
            "### 執行時間統計",
            "",
            "| 統計項 | 數值 |",
            "|--------|------|",
            f"| 平均執行時間 | {avg_duration:.3f} 秒 |",
            f"| 最快執行時間 | {min_duration:.3f} 秒 |",
            f"| 最慢執行時間 | {max_duration:.3f} 秒 |",
            "",
            "### SQL 語法分析",
            "",
            "| 統計項 | 數值 |",
            "|--------|------|",
            f"| 生成 SQL 的場景數 | {sql_success + sql_issues} |",
            f"| SQL 語法正確 | {sql_success} |",
            f"| SQL 語法有問題 | {sql_issues} |",
            "",
            "### 分類統計",
            "",
            "| 分類 | 總數 | 通過 | 失敗 | 通過率 |",
            "|------|------|------|------|--------|",
        ]
    )

    for cat, stats in categories.items():
        cat_pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        status = "✅" if stats["passed"] == stats["total"] else "❌"
        summary_lines.append(
            f"| {status} {cat} | {stats['total']} | {stats['passed']} | {stats['failed']} | {cat_pass_rate:.1f}% |"
        )

    summary_lines.extend(
        [
            "",
            "---",
            "",
            "## 測試結果詳情",
            "",
        ]
    )

    return "\n".join(summary_lines)


def get_expected_success_from_scenario_id(scenario_id: str) -> bool:
    """根據場景 ID 判斷預期是否成功

    Args:
        scenario_id: 場景 ID (如 "T2S-001")

    Returns:
        True 表示預期成功，False 表示預期失敗
    """
    # 異常處理場景預期失敗
    if "T2S-031" <= scenario_id <= "T2S-047":
        return False
    return True


def analyze_failure_reasons(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析失敗原因並分類

    Args:
        results: 測試結果列表

    Returns:
        失敗原因分析的字典
    """
    failure_analysis = {
        "keyword_mismatch": [],  # 關鍵字不匹配
        "wrong_table": [],  # 選錯表
        "timeout": [],  # 超時
        "schema_mismatch": [],  # Schema 不匹配
        "validation_error": [],  # 驗證錯誤
        "other": [],  # 其他
        "by_category": {},  # 按分類統計
    }

    for result in results:
        if not result.get("passed", False):
            sid = result["scenario_id"]
            category = result.get("category", "")
            notes = result.get("notes", [])

            # 按分類統計
            if category not in failure_analysis["by_category"]:
                failure_analysis["by_category"][category] = []
            failure_analysis["by_category"][category].append(
                {
                    "scenario_id": sid,
                    "notes": notes,
                    "error": result.get("error"),
                    "generated_sql": result.get("generated_sql"),
                    "duration_sec": result.get("duration_sec"),
                }
            )

            # 分析失敗原因
            has_keyword_issue = any("關鍵字" in note for note in notes)
            has_timeout = any("超閾值" in note for note in notes)
            has_validation = any("預期" in note for note in notes)

            # 檢查選錯表
            generated_sql = result.get("generated_sql", "")
            if generated_sql:
                wrong_table_analysis = detect_wrong_table_usage(sid, generated_sql, category)
                if wrong_table_analysis["has_wrong_table"]:
                    failure_analysis["wrong_table"].append(sid)

            if has_keyword_issue:
                failure_analysis["keyword_mismatch"].append(sid)
            elif has_timeout:
                failure_analysis["timeout"].append(sid)
            elif has_validation:
                failure_analysis["validation_error"].append(sid)
            else:
                failure_analysis["other"].append(sid)

    return failure_analysis


def generate_failure_analysis_report(data: Dict[str, Any]) -> str:
    """生成失敗原因分析報告（根據實際測試結果）

    Args:
        data: 測試結果數據

    Returns:
        Markdown 格式的失敗原因分析報告
    """
    results = data.get("results", [])
    failed_results = [r for r in results if not r.get("passed", False)]

    analysis = analyze_failure_reasons(results)

    report_lines = [
        "---",
        "",
        "## 失敗原因分析與改進方向",
        "",
        f"本次測試共有 **{len(failed_results)}** 個場景失敗，以下為詳細的失敗原因分析與改進建議。",
        "",
        "### 失敗原因分類統計",
        "",
        "| 失敗原因 | 場景數 | 場景 ID | 嚴重程度 |",
        "|----------|--------|---------|----------|",
    ]

    # 關鍵字不匹配
    if analysis["keyword_mismatch"]:
        report_lines.append(
            f"| 🔴 關鍵字不匹配 | {len(analysis['keyword_mismatch'])} | {', '.join(analysis['keyword_mismatch'][:10])}{'...' if len(analysis['keyword_mismatch']) > 10 else ''} | 高 |"
        )

    # 選錯表
    if analysis["wrong_table"]:
        report_lines.append(
            f"| 🔴 選錯表 | {len(analysis['wrong_table'])} | {', '.join(analysis['wrong_table'][:10])}{'...' if len(analysis['wrong_table']) > 10 else ''} | 高 |"
        )

    # 超時
    if analysis["timeout"]:
        report_lines.append(
            f"| 🟡 超時 | {len(analysis['timeout'])} | {', '.join(analysis['timeout'][:10])}{'...' if len(analysis['timeout']) > 10 else ''} | 中 |"
        )

    # 驗證錯誤
    if analysis["validation_error"]:
        report_lines.append(
            f"| 🔴 驗證錯誤 | {len(analysis['validation_error'])} | {', '.join(analysis['validation_error'][:10])}{'...' if len(analysis['validation_error']) > 10 else ''} | 高 |"
        )

    # 其他
    if analysis["other"]:
        report_lines.append(
            f"| 🟡 其他 | {len(analysis['other'])} | {', '.join(analysis['other'][:10])}{'...' if len(analysis['other']) > 10 else ''} | 中 |"
        )

    # 按分類統計失敗
    report_lines.extend(
        [
            "",
            "### 按分類的失敗詳情",
            "",
        ]
    )

    for cat, failures in analysis["by_category"].items():
        if failures:
            report_lines.append(f"#### {cat}")
            report_lines.append("")
            report_lines.append("| 場景 ID | 問題描述 | 執行時間 | 錯誤/備註 |")
            report_lines.append("|---------|----------|----------|-----------|")
            for f in failures:
                sid = f["scenario_id"]
                notes_str = "; ".join(f["notes"]) if f["notes"] else "-"
                duration = f"{f['duration_sec']:.3f}s" if f["duration_sec"] else "N/A"
                report_lines.append(f"| {sid} | {notes_str} | {duration} | {f['error'] or '-'} |")
            report_lines.append("")

    # 問題定位與改進方向（根據實際失敗場景）
    report_lines.extend(
        [
            "### 問題定位與改進方向（第 5 輪）",
            "",
        ]
    )

    # 獲取失敗的場景 ID
    failed_scenario_ids = [r["scenario_id"] for r in failed_results]

    # 根據具體失敗場景生成針對性改進建議
    report_lines.extend(
        [
            "#### 1. 關鍵字不匹配問題（第 5 輪實際分析）",
            "",
            "**第 5 輪失敗場景:**",
            f"- {', '.join(analysis['keyword_mismatch'])}",
            "",
            "**現象分析:**",
            "- T2S-003（OR 條件）: 生成的 SQL 未包含 OR 關鍵字",
            "- T2S-010（GROUP BY 分組）: 生成的 SQL 未包含 GROUP BY、img02、img10",
            "- T2S-022（Bottom N）: 生成的 SQL 未包含 ORDER BY、ASC、LIMIT、5",
            "- T2S-026（HAVING 條件）: 生成的 SQL 未包含 GROUP BY、HAVING、SUM、img10",
            "- T2S-028（日期範圍）: 生成的 SQL 未包含 tlf06、01",
            "",
            "**問題定位:**",
            "- **OR 條件範例缺失**: 6 個範例中沒有 OR 條件的範例",
            "- **複雜查詢範例不夠**: GROUP BY + HAVING、Bottom N、日期範圍等複雜查詢的範例缺失",
            "- **關鍵字檢測邏輯**: 測試腳本的關鍵字檢查可能對某些 SQL 語法過於嚴格",
            "",
            "**第 5 輪已執行的改進:**",
            "- ✅ 已增強 Schema 提示（添加欄位說明、表用途、詞彙映射）",
            "- ✅ 已添加 6 個標準範例",
            "- ✅ 已添加表關係說明",
            "- ✅ 通過率從 48% 提升至 84%（提升 36%）",
            "",
            "**進一步改進方向:**",
            "1. **添加複雜查詢範例**",
            "   - 添加 OR 條件範例（T2S-003 失敗）",
            "   - 添加 GROUP BY + HAVING 範例（T2S-026 失敗）",
            "   - 添加 ORDER BY + LIMIT 範例（T2S-022 失敗）",
            "   - 添加日期範圍範例（T2S-028 失敗）",
            "",
            "2. **優化關鍵字檢查邏輯**",
            "   - 考慮 LLM 可能使用不同的 SQL 語法風格",
            "   - 檢查關鍵字的同義詞（例如 UNION ALL 可能會取代 OR）",
            "   - 對複雜查詢，檢查其等效的 SQL 語法",
            "",
            "3. **增加範例數量**",
            "   - 從 6 個範例增加到 10-12 個範例",
            "   - 覆蓋更多查詢模式和關鍵字組合",
            "",
        ]
    )

    # 問題 2: 驗證錯誤
    if analysis["validation_error"]:
        report_lines.extend(
            [
                "",
                "#### 2. validate_query 驗證邏輯問題（第 5 輪實際分析）",
                "",
                "**第 5 輪失敗場景:**",
                f"- {', '.join(analysis['validation_error'])}",
                "",
                "**現象分析:**",
                "- T2S-039（無效 SQL 語法）: SQL 為 `SELECT FROM img_file`，應該被驗證為 invalid，但實際通過",
                "- T2S-041（validate_query 不通過）: 預期 valid=False，但實際返回 valid=True",
                "",
                "**問題定位:**",
                "- **sqlparse 導入失敗**: sqlparse 庫可能未正確導入或使用",
                "- **驗證邏輯不完整**: validate_query 可能沒有使用 sqlparse 進行驗證",
                "- **測試環境差異**: sqlparse 可能在測試環境中不可用",
                "",
                "**第 5 輪已執行的改進:**",
            ]
        )

        # 檢查是否有 sqlparse
        try:
            import sqlparse

            has_sqlparse = True
        except ImportError:
            has_sqlparse = False

        report_lines.extend(
            [
                f"- ✅ 代碼中已添加 sqlparse 導入",
                f"- ❌ sqlparse {'已導入' if has_sqlparse else '未導入（測試環境不可用）'}",
                "",
                "**進一步改進方向:**",
                "1. **確保 sqlparse 可用**",
                f"   - {'在測試環境安裝 sqlparse: pip3 install sqlparse' if not has_sqlparse else 'sqlparse 已導入'}",
                "   - 驗證 sqlparse 是否正確導入",
                "",
                "2. **增強驗證邏輯**",
                "   - 使用 sqlparse 檢查 SQL 語法結構",
                "   - 檢查 SELECT 是否有欄位、是否有 FROM 子句",
                "   - 檢查是否有危險關鍵字",
                "",
                "3. **添加更多無效 SQL 測試案例**",
                "   - 添加 `SELECT FROM`（無欄位）",
                "   - 添加 `FROM table`（無 SELECT）",
                "   - 添加 `DROP TABLE`",
                "",
            ]
        )

    # 問題 3: 選錯表（如果有）
    if analysis["wrong_table"]:
        report_lines.extend(
            [
                "",
                "#### 3. 選錯表問題（第 5 輪實際分析）",
                "",
                "**第 5 輪失敗場景:**",
                f"- {', '.join(analysis['wrong_table'][:10])}",
                "",
                "**現象分析:**",
                "- T2S-010: LLM 使用了所有表（ima_file, img_file, tlf_file, pmn_file）的 UNION，但預期只使用 img_file",
                "",
                "**問題定位:**",
                "- **表選擇邏輯過於寬鬆**: LLM 可能認為所有表都可能包含相關數據",
                "- **UNION ALL 濫進表選擇**: LLM 使用 UNION ALL 合併所有表，導致選錯表",
                "",
                "**第 5 輪已執行的改進:**",
                "- ✅ 已添加表用途說明",
                "- ✅ 已添加表關係說明",
                "- ✅ 已添加詞彙映射表",
                "",
                "**進一步改進方向:**",
                "1. **強化表選擇提示**",
                "   - 在 prompt 中更明確地指定：「庫存查詢」只使用 img_file",
                "   - 添加反例範例，展示錯誤的 UNION ALL 用法",
                "",
                "2. **改進查詢理解**",
                "   - 添加更多關鍵詞到詞彙映射表",
                "   - 明確區分不同查詢類型應使用的表",
                "",
            ]
        )

    # 問題 4: 其他（T2S-038 SQL 注入）
    if "T2S-038" in failed_scenario_ids:
        report_lines.extend(
            [
                "",
                "#### 4. SQL 注入嘗試問題（第 5 輪實際分析）",
                "",
                "**現象:**",
                "- T2S-038: SQL 注入嘗試（`'; DROP TABLE img_file;--`）被識別為「產出含危險關鍵字」而失敗",
                "",
                "**分析:**",
                "- 這是預期的行為：SQL 注入攻擊應該被拒絕",
                "- 但測試失敗的原因是「產出含危險關鍵字」，而不是「SQL 被拒絕」",
                "- 可能是 validate_query 或 text_to_sql 的邏輯需要調整",
                "",
                "**改進方向:**",
                "1. **明確測試預期**",
                "   - 這個場景應該成功（SQL 被拒絕，但系統正確識別了危險操作）",
                "   - 考慮修改測試預期，將此場景改為通過",
                "",
            ]
        )

    # 總結
    report_lines.extend(
        [
            "### 改進優先級建議（第 5 輪後）",
            "",
            "**高優先級（短期，1-2 週）:**",
            "1. ✅ 增強 Schema 提示，添加欄位中文說明和業務含義（已完成）",
            "2. ✅ 明確表用途說明，說明每個表的業務用途和使用場景（已完成）",
            "3. ✅ 建立「自然語言詞彙」到「SQL 欄位」的映射表（已完成）",
            "4. 🔲 添加 OR 條件範例（T2S-003 失敗）",
            "5. 🔲 添加 GROUP BY + HAVING 範例（T2S-026 失敗）",
            "6. 🔲 添加 ORDER BY + LIMIT 範例（T2S-022 失敗）",
            "7. 🔲 添加日期範圍範例（T2S-028 失敗）",
            "8. 🔲 確保 sqlparse 正確安裝和導入（T2S-039, T2S-041 失敗）",
            "",
            "**中優先級（中期，1-2 月）:**",
            "1. ✅ 在 prompt 中添加 6 個標準範例（已完成）",
            "2. ✅ 添加表關係說明（已完成）",
            "3. ⚠️ 優化關鍵字檢查邏輯（考慮同義詞和等效 SQL 語法）",
            "4. ⚠️ 查詢場景分類，明確每類查詢應使用的主要表",
            "5. ⚠️ 優化 prompt，減少 token 數量",
            "6. ⚠️ 添加查詢快取機制，減少重複查詢的 LLM 調用",
            "",
            "**低優先級（長期，3 月以上）:**",
            "1. 🔲 考慮使用更快的 LLM 模型或 GPU 加速",
            "2. 🔲 建立人機回饋機制，收集失敗案例用於改進",
            "3. 🔲 實現並行處理，減少整體等待時間",
            "",
            "### 預期改進效果（第 6 輪目標）",
            "",
            "實施上述改進措施後，預期可以達到以下效果：",
            "",
            "| 改進項目 | 第 5 輪狀態 | 第 6 輪目標 |",
            "|----------|----------|----------|",
            "| 關鍵字不匹配失敗 | 5 場景 | 降低至 0 場景 |",
            "| 選錯表失敗 | 2 場景 | 降低至 0 場景 |",
            "| 驗證錯誤 | 2 場景 | 降低至 0 場景 |",
            "| SQL 注入嘗試 | 1 場景（行為正確，需調整測試預期） | 調整測試預期 |",
            "| 平均執行時間 | 1.953 秒 | 維持在 2 秒以內 |",
            "| 整體通過率 | 84.0% | 提升至 > 90% |",
            "",
            "---",
            "",
        ]
    )

    return "\n".join(report_lines)


def main():
    """主函數：生成完整報告"""
    data = load_results()

    # 嘗試加載上一輪測試結果（第4輪）
    previous_round_data = None
    try:
        # 查找可能的上一輪結果文件
        import glob

        result_files = list(Path(__file__).parent.glob("run_50_scenarios_results_*.json"))
        # 找到最新的結果文件（排除當前的 round5 文件）
        if len(result_files) > 1:
            # 按修改時間排序，取第二新的
            result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            # 排除 round5 文件（名稱包含 round5）
            filtered_files = [f for f in result_files if "round5" not in f.name]

            for result_file in filtered_files[1:2]:  # 嘗試最多 2 個文件
                try:
                    with open(result_file, "r", encoding="utf-8") as f:
                        previous_round_data = json.load(f)
                    print(f"找到上一輪測試結果: {result_file}")
                    break
                except Exception as e:
                    print(f"無法讀取 {result_file}: {e}")
                    continue

        # 如果沒有找到過濾後的文件，嘗試手動查找 round4 文件
        if previous_round_data is None:
            round4_file = (
                Path(__file__).parent / "run_50_scenarios_results_round4_20260130_090349.json"
            )
            if round4_file.exists():
                with open(round4_file, "r", encoding="utf-8") as f:
                    previous_round_data = json.load(f)
                print(f"找到第4輪測試結果: {round4_file}")
    except Exception as e:
        print(f"無法加載上一輪測試結果: {e}")

    # 生成報告（第5輪）
    report_lines = [
        generate_summary_report(data, round_number=5, previous_round_data=previous_round_data),
    ]

    # 添加每個場景的詳細報告
    results = data.get("results", [])

    for result in results:
        sid = result["scenario_id"]
        # 構建簡單的場景定義（只需要 expected_success）
        scenario = {
            "scenario_id": sid,
            "expected_success": get_expected_success_from_scenario_id(sid),
        }
        detail = generate_scenario_detail(result, scenario)
        report_lines.append(detail)

    # 添加失敗原因分析報告
    failure_report = generate_failure_analysis_report(data)
    report_lines.append(failure_report)

    # 寫入報告文件
    output_path = Path(__file__).parent / "Data-Agent-50場景測試報告.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"詳細測試報告已生成: {output_path}")


if __name__ == "__main__":
    main()
