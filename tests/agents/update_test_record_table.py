# 代碼功能說明: 更新測試場景執行記錄表
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""根據測試結果更新測試劇本文件中的測試場景執行記錄表"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_test_results(results_file: Path) -> Dict[str, Any]:
    """加載測試結果 JSON 文件"""
    with open(results_file, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_markdown_table(lines: List[str], start_line: int, end_line: int) -> List[Dict[str, str]]:
    """解析 Markdown 表格

    Args:
        lines: 文件行列表
        start_line: 表格開始行（從1開始，包含表頭）
        end_line: 表格結束行（從1開始）

    Returns:
        包含每行數據的字典列表
    """
    table_data = []

    # 跳過表頭和分隔線（通常前兩行）
    for i in range(start_line, min(end_line + 1, len(lines) + 1)):
        line = lines[i - 1].strip()  # 轉換為0-based索引

        # 跳過空行和分隔線
        if not line or line.startswith("|---"):
            continue

        # 解析表格行
        if line.startswith("|") and line.endswith("|"):
            # 移除首尾的 |
            parts = [p.strip() for p in line[1:-1].split("|")]
            if len(parts) >= 9:  # 確保有足夠的列
                table_data.append(
                    {
                        "scenario_id": parts[0],
                        "user_input": parts[1],
                        "execution_date": parts[2],
                        "executor": parts[3],
                        "task_type_identification": parts[4],
                        "intent_extraction": parts[5],
                        "agent_call": parts[6],
                        "status": parts[7],
                        "notes": parts[8] if len(parts) > 8 else "",
                        "line_number": i,
                        "raw_line": line,
                    }
                )

    return table_data


def find_table_boundaries(content: str, category_title: str) -> Tuple[Optional[int], Optional[int]]:
    """查找類別表格的邊界

    Args:
        content: 文件內容
        category_title: 類別標題（如 "類別 1：md-editor（Markdown 編輯器）- 20 個場景"）

    Returns:
        (start_line, end_line) 從1開始的行號
    """
    lines = content.split("\n")

    # 首先查找"測試場景執行記錄表"部分
    table_section_start = None
    for i, line in enumerate(lines, 1):
        if "測試場景執行記錄表" in line and line.startswith("##"):
            table_section_start = i
            break

    if table_section_start is None:
        return None, None

    # 在"測試場景執行記錄表"部分查找類別標題（如 "### 類別 1：md-editor（Markdown 編輯器）- 20 個場景"）
    start_line = None
    for i in range(table_section_start, len(lines)):
        line = lines[i]
        if category_title in line and line.startswith("###"):
            # 找到表頭行（跳過標題和空行）
            for j in range(i + 1, min(i + 5, len(lines) + 1)):
                if lines[j - 1].startswith("| 場景 ID"):
                    start_line = j
                    break
            break

    if start_line is None:
        return None, None

    # 查找表格結束（通常是 "**類別統計**"）
    end_line = None
    for i in range(start_line, len(lines)):
        if lines[i].startswith("**類別統計**"):
            end_line = i - 1  # 統計行的上一行
            break

    if end_line is None:
        end_line = len(lines)

    return start_line, end_line


def update_table_row(
    row_data: Dict[str, str], test_result: Dict[str, Any], execution_date: str, executor: str
) -> str:
    """更新表格行

    Args:
        row_data: 原始表格行數據
        test_result: 測試結果
        execution_date: 執行日期
        executor: 執行人

    Returns:
        更新後的表格行字符串
    """
    scenario_id = row_data["scenario_id"]

    # 獲取測試結果
    test_result.get("actual_task_type", "")
    test_result.get("actual_agents", [])
    task_type_match = test_result.get("task_type_match", False)
    agent_match = test_result.get("agent_match", False)
    all_passed = test_result.get("all_passed", False)
    error = test_result.get("error")

    # 格式化字段
    task_type_status = "✅" if task_type_match else "❌"
    # 意圖提取：如果任務類型匹配且Agent匹配，則為✅
    intent_extraction_status = "✅" if (task_type_match and agent_match) else "❌"
    agent_call_status = "✅" if agent_match else "❌"
    status = "✅ 通過" if all_passed else "❌ 失敗"
    notes = error if error else ""

    # 構建新的表格行
    user_input = row_data["user_input"]
    new_line = f"| {scenario_id}  | {user_input} | {execution_date} | {executor} | {task_type_status} | {intent_extraction_status} | {agent_call_status} | {status} | {notes} |"

    return new_line


def update_category_statistics(
    content: str, category_title: str, category_name: str, results: List[Dict[str, Any]]
) -> str:
    """更新類別統計

    Args:
        content: 文件內容
        category_title: 類別標題（如 "類別 1：md-editor（Markdown 編輯器）- 20 個場景"）
        category_name: 類別名稱（如 "md-editor"）
        results: 所有測試結果列表

    Returns:
        更新後的內容
    """
    lines = content.split("\n")

    # 查找類別統計行（在該類別表格之後）
    category_results = [r for r in results if r.get("category") == category_name]
    total = len(category_results)
    passed = sum(1 for r in category_results if r.get("all_passed", False))
    failed = total - passed
    not_executed = 0
    pass_rate = f"{(passed/total*100):.1f}%" if total > 0 else "0%"

    # 查找類別標題，然後查找其後的統計行
    start_search = None
    for i, line in enumerate(lines, 1):
        if category_title in line and line.startswith("###"):
            start_search = i
            break

    if start_search:
        # 在類別標題之後查找統計行
        for i in range(start_search, min(start_search + 30, len(lines))):
            if lines[i].startswith("**類別統計**"):
                new_statistics = (
                    f"**類別統計**：通過 {passed} / 失敗 {failed} / 未執行 {not_executed} / 通過率 {pass_rate}"
                )
                lines[i] = new_statistics
                break

    return "\n".join(lines)


def update_test_execution_summary(
    content: str, results: List[Dict[str, Any]], execution_date: str, executor: str
) -> str:
    """更新測試執行摘要表

    Args:
        content: 文件內容
        results: 所有測試結果
        execution_date: 執行日期
        executor: 執行人

    Returns:
        更新後的內容
    """
    lines = content.split("\n")

    total = len(results)
    passed = sum(1 for r in results if r.get("all_passed", False))
    failed = total - passed
    not_executed = 0
    pass_rate = f"{(passed/total*100):.1f}%" if total > 0 else "0%"

    # 查找並替換摘要表行（第51行）
    summary_pattern = re.compile(
        r"\| 第 1 輪  \| .* \| .* \| .* \| v3\.2     \| 100      \| .* \| .* \| .* \| .* \| .* \|"
    )

    for i, line in enumerate(lines):
        if summary_pattern.search(line) and i >= 49 and i <= 51:  # 大約在第51行
            new_summary = f"| 第 1 輪  | {execution_date} | {executor} | 本地開發環境 | v3.2     | {total}      | {passed}    | {failed}    | {not_executed}    | {pass_rate}      | 測試完成 |"
            lines[i] = new_summary
            break

    return "\n".join(lines)


def update_test_record_table(
    test_script_path: Path,
    results_file: Path,
    output_path: Optional[Path] = None,
) -> Path:
    """更新測試場景執行記錄表

    Args:
        test_script_path: 測試劇本文件路徑
        results_file: 測試結果 JSON 文件路徑
        output_path: 輸出文件路徑（如果為None，則覆蓋原文件）

    Returns:
        更新後的文件路徑
    """
    # 加載測試結果
    test_results = load_test_results(results_file)
    results = test_results.get("results", [])
    execution_date = test_results.get("execution_date", datetime.now().strftime("%Y-%m-%d"))
    executor = test_results.get("executor", "Daniel Chung")

    # 讀取測試劇本文件
    with open(test_script_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")

    # 創建場景ID到測試結果的映射
    results_map = {r["scenario_id"]: r for r in results}

    # 定義類別映射
    category_map = {
        "md-editor": ("類別 1：md-editor（Markdown 編輯器）- 20 個場景", "md-editor"),
        "xls-editor": ("類別 2：xls-editor（Excel 編輯器）- 20 個場景", "xls-editor"),
        "md-to-pdf": ("類別 3：md-to-pdf（Markdown 轉 PDF）- 20 個場景", "md-to-pdf"),
        "xls-to-pdf": ("類別 4：xls-to-pdf（Excel 轉 PDF）- 20 個場景", "xls-to-pdf"),
        "pdf-to-md": ("類別 5：pdf-to-md（PDF 轉 Markdown）- 20 個場景", "pdf-to-md"),
    }

    # 更新每個類別的表格
    for category_key, (category_title, category_name) in category_map.items():
        # 查找表格邊界
        start_line, end_line = find_table_boundaries(content, category_title)

        if start_line is None or end_line is None:
            print(f"警告：找不到類別 {category_title} 的表格邊界")
            continue

        # 解析表格
        table_data = parse_markdown_table(lines, start_line, end_line)

        # 更新每個場景的行
        for row_data in table_data:
            scenario_id = row_data["scenario_id"]
            test_result = results_map.get(scenario_id)

            if test_result:
                # 更新表格行
                new_line = update_table_row(row_data, test_result, execution_date, executor)
                line_number = row_data["line_number"]
                lines[line_number - 1] = new_line  # 轉換為0-based索引

        # 更新類別統計
        content = "\n".join(lines)
        content = update_category_statistics(content, category_title, category_name, results)
        lines = content.split("\n")

    # 更新測試執行摘要表
    content = "\n".join(lines)
    content = update_test_execution_summary(content, results, execution_date, executor)

    # 寫回文件
    output_path = output_path or test_script_path
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"測試記錄表已更新: {output_path}")
    return output_path


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="更新測試場景執行記錄表")
    parser.add_argument(
        "--results",
        type=str,
        required=True,
        help="測試結果 JSON 文件路徑",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="輸出文件路徑（如果未指定，則覆蓋原文件）",
    )
    parser.add_argument(
        "--script",
        type=str,
        default="docs/系统设计文档/核心组件/Agent平台/archive/testing/文件編輯Agent語義路由測試劇本-v2.md",
        help="測試劇本文件路徑",
    )

    args = parser.parse_args()

    test_script_path = Path(args.script)
    results_file = Path(args.results)
    output_path = Path(args.output) if args.output else None

    if not test_script_path.exists():
        print(f"錯誤：測試劇本文件不存在: {test_script_path}")
        return 1

    if not results_file.exists():
        print(f"錯誤：測試結果文件不存在: {results_file}")
        return 1

    try:
        update_test_record_table(test_script_path, results_file, output_path)
        print("更新完成")
        return 0
    except Exception as e:
        print(f"錯誤：更新失敗: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
