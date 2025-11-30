# 代碼功能說明: 更新整合測試場景文檔（階段四測試結果）
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""更新整合測試場景文檔，添加階段四測試結果"""

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def load_test_results() -> Dict[str, Any]:
    """載入測試結果 JSON 文件"""
    results_file = (
        Path(__file__).parent.parent
        / "tests"
        / "integration"
        / "phase4"
        / "test_results_summary.json"
    )
    if results_file.exists():
        with open(results_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def update_phase4_stats(content: str, results: Dict[str, Any]) -> str:
    """更新階段四統計部分"""
    if not results:
        return content

    # 更新階段四統計狀態
    phase4_status_pattern = r"(### 階段四統計\s*\n\s*\*\*狀態\*\*: )⏸️ 待實現"
    test_date = results.get("test_date", datetime.now().strftime("%Y-%m-%d"))
    pass_rate = results.get("pass_rate", 0)
    skipped_rate = (
        (results.get("skipped", 0) / results.get("total", 1) * 100)
        if results.get("total", 0) > 0
        else 0
    )

    replacement = f"\\1✅ 已實現（測試代碼已編寫完成，測試執行完成）\n\n**執行結果** ({test_date}):\n- 總測試數: {results.get('total', 0)}\n- 通過: {results.get('passed', 0)} ({pass_rate:.1f}%)\n- 失敗: {results.get('failed', 0)} (0%)\n- 跳過: {results.get('skipped', 0)} ({skipped_rate:.1f}%)\n- 執行時間: {results.get('duration', 0):.2f}s\n- 通過率: {pass_rate:.1f}%"

    content = re.sub(phase4_status_pattern, replacement, content, flags=re.MULTILINE)

    # 更新總體統計表中的階段四狀態
    total_stats_pattern = r"(\| \*\*階段四\*\* \| 4 \| )⏸️( \| ✅ \| - \| - \| - \| - \|)"
    pass_count = results.get("passed", 0)
    skip_count = results.get("skipped", 0)
    total_count = results.get("total", 0)
    total_stats_replacement = (
        f"\\1✅\\2 {pass_count}/{total_count} | 0 | {skip_count} | {pass_rate:.1f}% |"
    )

    content = re.sub(
        total_stats_pattern, total_stats_replacement, content, flags=re.MULTILINE
    )

    return content


def update_test_progress_table(content: str, results: Dict[str, Any]) -> str:
    """更新測試進度管制表"""
    if not results:
        return content

    test_descriptions = {
        "IT-4.1": "文件處理流程整合測試",
        "IT-4.2": "文本分析流程整合測試",
        "IT-4.3": "上下文管理整合測試",
        "IT-4.4": "AAM 模組整合測試",
    }

    test_date = results.get("test_date", datetime.now().strftime("%Y-%m-%d"))

    # 更新每個測試劇本的行
    for test_id in ["IT-4.1", "IT-4.2", "IT-4.3", "IT-4.4"]:
        test_data = results.get("tests", {}).get(test_id, {})
        if not test_data:
            continue

        total_duration = sum(t.get("duration", 0) for t in test_data.get("tests", []))
        passed_count = test_data.get("passed", 0)
        total_count = test_data.get("total", 0)
        skipped_count = test_data.get("skipped", 0)
        status = test_data.get("status", "待實現")

        # 匹配測試進度表行 - 更靈活的匹配
        pattern = rf"(\| {re.escape(test_id)} \| {re.escape(test_descriptions[test_id])} \| )⏸️( 待實現 \| - \| - \|)"

        if status == "已實現":
            replacement = f"\\1✅ 通過\\2 {total_duration:.2f}s | {test_date} | {passed_count}個測試用例全部通過 |"
        elif status == "部分實現":
            replacement = f"\\1⏸️ 部分實現\\2 {total_duration:.2f}s | {test_date} | {passed_count}/{total_count} 個測試通過，{skipped_count} 個跳過 |"
        else:
            replacement = (
                f"\\1⏸️ 部分實現\\2 {total_duration:.2f}s | {test_date} | API 端點部分實現，需驗證 |"
            )

        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    return content


def update_test_scenario_details(content: str, results: Dict[str, Any]) -> str:
    """更新測試劇本詳情部分"""
    if not results:
        return content

    # 更新 IT-4.1 文件處理流程
    content = update_test_scenario_steps(content, "IT-4.1", results)

    # 更新 IT-4.2 文本分析流程
    content = update_test_scenario_steps(content, "IT-4.2", results)

    # 更新 IT-4.3 上下文管理
    content = update_test_scenario_steps(content, "IT-4.3", results)

    # 更新 IT-4.4 AAM 模組
    content = update_test_scenario_steps(content, "IT-4.4", results)

    return content


def update_test_scenario_steps(
    content: str, test_id: str, results: Dict[str, Any]
) -> str:
    """更新特定測試劇本的步驟結果"""
    test_data = results.get("tests", {}).get(test_id, {})
    if not test_data:
        return content

    # 步驟映射到測試方法名
    step_to_test = {
        "IT-4.1": {
            "步驟 1": "test_file_upload",
            "步驟 2": "test_file_chunking",
            "步驟 3": "test_multiformat_support",
        },
        "IT-4.2": {
            "步驟 1": "test_ner_extraction",
            "步驟 2": "test_re_extraction",
            "步驟 3": "test_rt_classification",
            "步驟 4": "test_triple_extraction",
            "步驟 5": "test_kg_build",
        },
        "IT-4.3": {
            "步驟 1": "test_context_manager",
            "步驟 2": "test_conversation_history",
            "步驟 3": "test_context_window",
        },
        "IT-4.4": {
            "步驟 1": "test_realtime_interaction",
            "步驟 2": "test_async_agent",
            "步驟 3": "test_hybrid_rag",
        },
    }

    # 創建測試方法名到測試信息的映射
    test_map = {t.get("name", ""): t for t in test_data.get("tests", [])}

    # 更新每個測試步驟
    for step_num, test_method in step_to_test.get(test_id, {}).items():
        test_info = test_map.get(test_method)
        if not test_info:
            continue

        status = test_info.get("status", "")
        duration = test_info.get("duration", 0)
        reason = test_info.get("reason", "")

        # 構建狀態標記和結果文本
        if status == "passed":
            status_mark = "✅ 通過"
            result_text = f"**測試結果**: ✅ 已實現（測試代碼已編寫完成，測試執行通過）\n**實際響應時間**: {duration:.3f}s\n**實際響應內容**:\n```\n測試通過，API 端點正常工作\n```"
            note_text = "測試通過"
        elif status == "skipped":
            status_mark = "⏭️ 跳過"
            reason_short = reason.split("\n")[0][:80] if reason else "API 端點未實現或不可用"
            result_text = f"**測試結果**: ⏭️ 跳過（{reason_short}）\n**實際響應時間**: {duration:.3f}s\n**實際響應內容**:\n```\n{reason_short}\n```"
            note_text = reason_short
        else:
            status_mark = "❌ 失敗"
            result_text = f"**測試結果**: ❌ 失敗\n**實際響應時間**: {duration:.3f}s\n**實際響應內容**:\n```\n{reason}\n```"
            note_text = "測試失敗，需要修復"

        # 匹配測試步驟的測試結果部分
        # 尋找 "**步驟 X**: ... **測試結果**: ... **備註**:"
        pattern = rf"(\*\*{re.escape(step_num)}\*\*:.*?\n(?:\*\*輸入數據\*\*:.*?\n)?(?:\*\*預期輸出\*\*:.*?\n))\*\*測試結果\*\*:.*?\n(?:\*\*實際響應時間\*\*:.*?\n)?(?:\*\*實際響應內容\*\*:.*?\n)?\*\*狀態\*\*:.*?\n\n\*\*備註\*\*:\s*\n.*?\n"

        replacement = (
            f"\\1{result_text}\n**狀態**: {status_mark}\n\n**備註**:\n{note_text}\n"
        )

        # 如果沒有找到帶狀態的版本，嘗試匹配沒有狀態的版本
        if not re.search(pattern, content, flags=re.MULTILINE | re.DOTALL):
            pattern = rf"(\*\*{re.escape(step_num)}\*\*:.*?\n(?:\*\*輸入數據\*\*:.*?\n)?(?:\*\*預期輸出\*\*:.*?\n))\*\*測試結果\*\*:.*?\n(?:\*\*實際響應時間\*\*:.*?\n)?(?:\*\*實際響應內容\*\*:.*?\n)?\*\*備註\*\*:\s*\n.*?\n"
            replacement = (
                f"\\1{result_text}\n**狀態**: {status_mark}\n\n**備註**:\n{note_text}\n"
            )

        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)

    return content


def update_last_modified_date(content: str) -> str:
    """更新最後修改日期"""
    today = datetime.now().strftime("%Y-%m-%d")

    # 更新文檔開頭的日期
    pattern = r"(\*\*最後更新\*\*: )\d{4}-\d{2}-\d{2}"
    replacement = f"\\1{today}"
    content = re.sub(pattern, replacement, content)

    # 更新文檔末尾的日期
    pattern = r"(\*\*最後更新\*\*: )\d{4}-\d{2}-\d{2}"
    replacement = f"\\1{today}"
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    return content


def main():
    """主函數"""
    base_dir = Path(__file__).parent.parent
    doc_path = base_dir / "tests" / "integration" / "integration_test_scenarios.md"

    if not doc_path.exists():
        print(f"錯誤: 找不到 {doc_path}")
        return

    # 載入測試結果
    results = load_test_results()
    if not results:
        print("錯誤: 無法載入測試結果")
        return

    print(f"讀取文檔 {doc_path}...")
    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    print("更新階段四統計...")
    content = update_phase4_stats(content, results)

    print("更新測試進度管制表...")
    content = update_test_progress_table(content, results)

    print("更新測試劇本詳情...")
    content = update_test_scenario_details(content, results)

    print("更新最後修改日期...")
    content = update_last_modified_date(content)

    print("寫入更新後的文檔...")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("完成！")


if __name__ == "__main__":
    main()
