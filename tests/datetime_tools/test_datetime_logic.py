#!/usr/bin/env python3
# 代碼功能說明: 測試 DateTimeTool 意圖識別邏輯（不依賴數據庫）
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""測試 DateTimeTool 意圖識別邏輯

直接測試核心邏輯，不依賴數據庫連接。
"""


def test_is_simple_query_logic():
    """測試 _is_simple_query 的邏輯"""
    print("=" * 80)
    print("測試 1: _is_simple_query 邏輯")
    print("=" * 80)

    # 從 analyzer.py 複製的邏輯
    simple_keywords = ["你好", "hello", "hi", "謝謝", "thanks"]
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

    def _is_simple_query(task: str) -> bool:
        task_lower = task.lower().strip()

        # 檢查是否是簡單關鍵詞（完全匹配）
        if task_lower in simple_keywords:
            return True

        # 檢查長度（但必須排除需要工具的查詢）
        if len(task_lower) < 10 and not any(
            keyword in task_lower for keyword in tool_indicators
        ):
            return True

        return False

    test_cases = [
        ("告訴我此刻時間", False, "包含時間關鍵詞，應該返回 False（需要工具）"),
        ("你好", True, "簡單問候語，應該返回 True"),
        ("hello", True, "簡單問候語，應該返回 True"),
        ("什麼是 AI？", True, "長度 < 10，應該返回 True（簡單查詢）"),
        ("幫我看股價", False, "包含工具關鍵詞，應該返回 False"),
    ]

    print("\n測試用例:")
    all_passed = True
    for query, expected, description in test_cases:
        result = _is_simple_query(query)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        print(f"  {status} '{query}' -> {result} (期望: {expected})")
        print(f"      {description}")

    return all_passed


def test_is_direct_answer_candidate_logic():
    """測試 _is_direct_answer_candidate 的邏輯"""
    print("\n" + "=" * 80)
    print("測試 2: _is_direct_answer_candidate 邏輯")
    print("=" * 80)

    # 從 analyzer.py 複製的邏輯
    import re

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

    action_keywords = ["幫我", "幫", "執行", "運行", "執行", "查詢", "獲取"]

    def _is_direct_answer_candidate(task: str) -> bool:
        task_lower = task.lower().strip()

        # 1. 長度檢查
        if len(task_lower) < 10:
            # 但排除工具指示詞
            if any(keyword in task_lower for keyword in tool_indicators):
                return False
            return True

        # 2. 簡單關鍵詞
        simple_keywords = ["你好", "hello", "hi", "謝謝", "thanks"]
        if task_lower in simple_keywords:
            return True

        # 3. Factoid / Definition 模式
        factoid_patterns = [
            r"什麼是\s*\w+",  # "什麼是 DevSecOps?"
            r"什麼叫\s*\w+",
            r"^[\w\s]+是哪家公司",  # "HCI 是哪家公司？"
            r"^[\w\s]+是什麼",
        ]
        if any(re.match(pattern, task_lower) for pattern in factoid_patterns):
            return True

        # 4. 檢查是否有副作用關鍵詞（需要系統行動）
        if any(keyword in task_lower for keyword in action_keywords):
            return False  # 需要系統行動 → Layer 2

        # 5. 檢查是否涉及內部狀態/工具
        if any(keyword in task_lower for keyword in tool_indicators):
            return False  # 需要工具 → Layer 2

        return True  # 默認：嘗試直接回答 → Layer 1

    test_cases = [
        ("告訴我此刻時間", False, "包含時間關鍵詞，需要工具，應該返回 False"),
        ("你好", True, "簡單問候語，可以直接回答，應該返回 True"),
        ("什麼是 DevSecOps？", True, "知識性問題，可以直接回答，應該返回 True"),
        ("幫我看看台積電今天的股價", False, "包含股價關鍵詞，需要工具，應該返回 False"),
        ("今天天氣如何？", False, "包含天氣關鍵詞，需要工具，應該返回 False"),
        ("HCI 是哪家公司？", True, "Factoid 模式，可以直接回答，應該返回 True"),
    ]

    print("\n測試用例:")
    all_passed = True
    for query, expected, description in test_cases:
        result = _is_direct_answer_candidate(query)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        print(f"  {status} '{query}' -> {result} (期望: {expected})")
        print(f"      {description}")

    return all_passed


def test_tool_indicator_matching():
    """測試工具指示詞匹配"""
    print("\n" + "=" * 80)
    print("測試 3: 工具指示詞匹配")
    print("=" * 80)

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
        ("告訴我此刻時間", ["時間"], True),  # 實際只匹配"時間"
        ("現在幾點了？", [], False),  # "幾點"不在工具指示詞列表中
        ("幫我看台積電的股價", ["股價"], True),  # 實際只匹配"股價"
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
        print(f"      匹配關鍵詞: {matched_keywords} (期望包含: {expected_keywords})")
        print(f"      是否匹配: {matches} (期望: {should_match})")

    return all_passed


def main():
    """主測試函數"""
    print("\n🚀 開始測試 DateTimeTool 意圖識別邏輯\n")

    results = []

    # 測試 1: _is_simple_query 邏輯
    results.append(("_is_simple_query 邏輯", test_is_simple_query_logic()))

    # 測試 2: _is_direct_answer_candidate 邏輯
    results.append(
        ("_is_direct_answer_candidate 邏輯", test_is_direct_answer_candidate_logic())
    )

    # 測試 3: 工具指示詞匹配
    results.append(("工具指示詞匹配", test_tool_indicator_matching()))

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
        print("\n✅ 所有邏輯測試通過！")
        print("\n💡 關鍵發現：")
        print("   1. ✅ '_is_simple_query' 正確識別了時間查詢（返回 False）")
        print("   2. ✅ '_is_direct_answer_candidate' 正確識別了時間查詢（返回 False）")
        print("   3. ✅ '告訴我此刻時間' 會被正確識別為需要工具的查詢")
        print("\n📋 預期執行流程：")
        print("   '告訴我此刻時間' -> Layer 0 (False) -> Layer 1 (False) -> Layer 2/3")
        print("   -> Router LLM (needs_tools=True) -> Decision Engine (選擇 datetime 工具)")
        print("\n🔍 如果實際運行中仍然有問題，請檢查：")
        print("   1. Router LLM 的 prompt 是否正確引導 AI 識別工具需求")
        print("   2. Decision Engine 是否正確選擇了 datetime 工具")
        print("   3. 聊天 API 是否正確執行了選擇的工具")
    else:
        print("\n❌ 部分測試失敗，請檢查輸出")

    print("=" * 80 + "\n")
    return all_passed


if __name__ == "__main__":
    import sys

    success = main()
    sys.exit(0 if success else 1)
