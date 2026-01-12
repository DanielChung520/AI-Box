#!/usr/bin/env python3
# 代碼功能說明: 簡化版測試 DateTimeTool 意圖識別流程（不需要數據庫連接）
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""簡化版測試：測試 Task Analyzer 的核心邏輯（不依賴數據庫）

這個測試腳本可以直接測試：
1. _is_direct_answer_candidate 方法
2. _is_simple_query 方法
3. Router LLM 的決策邏輯（如果可用）
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_is_simple_query():
    """測試 _is_simple_query 方法"""
    print("=" * 80)
    print("測試 1: _is_simple_query 方法")
    print("=" * 80)

    # 導入 TaskAnalyzer
    from agents.task_analyzer.analyzer import TaskAnalyzer

    analyzer = TaskAnalyzer()

    test_cases = [
        ("告訴我此刻時間", False, "包含時間關鍵詞，應該返回 False"),
        ("你好", True, "簡單問候語，應該返回 True"),
        ("hello", True, "簡單問候語，應該返回 True"),
        ("什麼是 AI？", False, "知識性問題，長度 > 10，應該返回 False"),
        ("幫我看股價", False, "包含工具關鍵詞，應該返回 False"),
    ]

    print("\n測試用例:")
    all_passed = True
    for query, expected, description in test_cases:
        result = analyzer._is_simple_query(query)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        print(f"  {status} '{query}' -> {result} (期望: {expected}) - {description}")

    return all_passed


def test_is_direct_answer_candidate():
    """測試 _is_direct_answer_candidate 方法"""
    print("\n" + "=" * 80)
    print("測試 2: _is_direct_answer_candidate 方法")
    print("=" * 80)

    from agents.task_analyzer.analyzer import TaskAnalyzer

    analyzer = TaskAnalyzer()

    test_cases = [
        ("告訴我此刻時間", False, "包含時間關鍵詞，需要工具，應該返回 False"),
        ("你好", True, "簡單問候語，可以直接回答，應該返回 True"),
        ("什麼是 DevSecOps？", True, "知識性問題，可以直接回答，應該返回 True"),
        ("幫我看看台積電今天的股價", False, "包含股價關鍵詞，需要工具，應該返回 False"),
        ("今天天氣如何？", False, "包含天氣關鍵詞，需要工具，應該返回 False"),
    ]

    print("\n測試用例:")
    all_passed = True
    for query, expected, description in test_cases:
        result = analyzer._is_direct_answer_candidate(query)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        print(f"  {status} '{query}' -> {result} (期望: {expected}) - {description}")

    return all_passed


def test_tool_indicators():
    """測試工具指示詞匹配"""
    print("\n" + "=" * 80)
    print("測試 3: 工具指示詞匹配")
    print("=" * 80)

    from agents.task_analyzer.analyzer import TaskAnalyzer

    TaskAnalyzer()

    # 獲取工具指示詞列表（從代碼中）
    tool_indicators = [
        "股價",
        "股票",
        "天氣",
        "匯率",
        "時間",
        "時刻",
        "位置",
        "stock price",
        "weather",
        "exchange rate",
        "location",
    ]

    test_cases = [
        ("告訴我此刻時間", ["時間", "時刻"], True),
        ("現在幾點了？", ["時間", "時刻"], True),
        ("幫我看台積電的股價", ["股價", "股票"], True),
        ("今天天氣如何？", ["天氣"], True),
        ("你好", [], False),
        ("什麼是 AI？", [], False),
    ]

    print("\n測試用例:")
    all_passed = True
    for query, expected_keywords, should_match in test_cases:
        query_lower = query.lower().strip()
        matched_keywords = [kw for kw in tool_indicators if kw in query_lower]
        matches = len(matched_keywords) > 0
        status = "✅" if matches == should_match else "❌"
        if matches != should_match:
            all_passed = False
        print(f"  {status} '{query}'")
        print(f"      匹配關鍵詞: {matched_keywords} (期望: {expected_keywords})")
        print(f"      是否匹配: {matches} (期望: {should_match})")

    return all_passed


def test_query_length():
    """測試查詢長度判斷"""
    print("\n" + "=" * 80)
    print("測試 4: 查詢長度判斷")
    print("=" * 80)

    test_cases = [
        ("告訴我此刻時間", 7, "< 10"),
        ("你好", 2, "< 10"),
        ("什麼是 DevSecOps？", 9, "< 10"),
        ("什麼是人工智慧？", 7, "< 10"),
        ("請幫我分析一下這個問題", 11, ">= 10"),
    ]

    print("\n測試用例:")
    for query, length, comparison in test_cases:
        print(f"  '{query}' -> 長度: {length} ({comparison})")


def main():
    """主測試函數"""
    print("\n🚀 開始測試 Task Analyzer 核心邏輯\n")

    results = []

    # 測試 1: _is_simple_query
    results.append(("_is_simple_query", test_is_simple_query()))

    # 測試 2: _is_direct_answer_candidate
    results.append(("_is_direct_answer_candidate", test_is_direct_answer_candidate()))

    # 測試 3: 工具指示詞匹配
    results.append(("工具指示詞匹配", test_tool_indicators()))

    # 測試 4: 查詢長度判斷
    test_query_length()

    # 總結
    print("\n" + "=" * 80)
    print("📊 測試總結")
    print("=" * 80)
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✅ 所有核心邏輯測試通過！")
        print("\n💡 提示：")
        print("   - _is_simple_query 和 _is_direct_answer_candidate 都正確識別了時間查詢")
        print("   - '告訴我此刻時間' 應該進入 Layer 2/3 進行工具選擇")
        print("   - 如果實際運行中仍然有問題，可能是以下原因：")
        print("     1. Router LLM 的 prompt 不夠明確")
        print("     2. Decision Engine 的工具匹配邏輯有問題")
        print("     3. 聊天 API 沒有正確執行選擇的工具")
    else:
        print("\n❌ 部分測試失敗，請檢查輸出")

    print("=" * 80 + "\n")
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
