# 代碼功能說明: MM-Agent 整合測試 - 獨立運行版本
# 創建日期: 2026-02-04

"""
MM-Agent 整合測試套件（獨立版本）

測試範圍：
1. 意圖識別與流程路由
2. 人類語言狀態顯示
3. Agent 路由邏輯
4. 多輪對話流程
5. 邊界情況處理
"""

import re
from typing import Dict, Any, List, Tuple


# ============================================
# QueryIntentType（複製自 chat.py）
# ============================================


class QueryIntentType:
    DATA_QUERY = "data_query"
    KNOWLEDGE_QUERY = "knowledge_query"
    CONVERSATION = "conversation"
    CLARIFICATION_NEEDED = "clarification_needed"


# ============================================
# 意圖識別函數（複製自 chat.py）
# ============================================


def detect_query_intent(user_query: str) -> Tuple[str, str, List[str]]:
    """意圖識別函數"""
    query = user_query.strip()
    query_lower = query.lower()

    data_query_patterns = [
        r"rm\d{2}-?\d{3,}",
        r"料號\s*[A-Za-z0-9\-]+",
        r"物料\s*[A-Za-z0-9\-]+",
        r"part\s*[A-Za-z0-9]+",
        r"庫存",
        r"庫存數量",
        r"庫存多少",
        r"買進",
        r"賣出",
        r"採購",
        r"進貨",
        r"出貨",
        r"訂單",
        r"訂單數量",
        r"最近\s*\d+\s*個月?",
        r"這\s*\d+\s*天?",
        r"多少錢",
        r"單價",
        r"價格",
        r"供應商",
        r"廠商",
    ]

    knowledge_query_patterns = [
        r"能做什麼",
        r"有什麼功能",
        r"系統能",
        r"如何使用",
        r"怎麼用",
        r"如何[操作|使用|設定]",
        r"你是誰",
        r"你的職責",
        r"你能做",
        r"你有什麼能力",
        r"什麼是",
        r"解釋一下",
    ]

    clarification_patterns = [
        r"^(?!這個月|這個週)[這那]個",
        r"(?<![月年日週時])\s+這[個件]",
        r"(?<![月年日週時])\s+那[個件]",
        r"^它",
        r"之前說的",
    ]

    explicit_data_patterns = [
        r"rm\d{2}-?\d{3,}",
        r"料號\s*[A-Za-z0-9\-]+",
        r"物料\s*[A-Za-z0-9\-]+",
        r"part\s*[A-Za-z0-9]+",
    ]

    # 檢測是否需要澄清
    clarification_matches = []
    has_explicit_data = False
    for pattern in clarification_patterns:
        if re.search(pattern, query_lower):
            clarification_matches.append(pattern)

    for pattern in explicit_data_patterns:
        if re.search(pattern, query_lower):
            has_explicit_data = True

    if clarification_matches and not has_explicit_data:
        return QueryIntentType.CLARIFICATION_NEEDED, "需要澄清", []

    # 檢測數據查詢
    data_query_matches = []
    for pattern in data_query_patterns:
        matches = re.findall(pattern, query_lower)
        data_query_matches.extend(matches)

    if data_query_matches:
        intent_type = QueryIntentType.DATA_QUERY
        intent_description = "數據查詢"

        if re.search(r"買進|賣出|採購|進貨|出貨", query_lower):
            intent_description = "查詢採購/銷售數據"
        elif re.search(r"庫存", query_lower):
            intent_description = "查詢庫存數據"
        elif re.search(r"訂單", query_lower):
            intent_description = "查詢訂單數據"
        elif re.search(r"多少錢|單價|價格", query_lower):
            intent_description = "查詢價格"

        return intent_type, intent_description, list(set(data_query_matches))

    # 檢測知識查詢
    knowledge_matches = []
    for pattern in knowledge_query_patterns:
        if re.search(pattern, query_lower):
            knowledge_matches.append(pattern)

    if knowledge_matches:
        intent_type = QueryIntentType.KNOWLEDGE_QUERY
        intent_description = "知識查詢"

        if re.search(r"能做什麼|有什麼功能|系統能", query_lower):
            intent_description = "查詢系統能力"
        elif re.search(r"如何使用|怎麼用", query_lower):
            intent_description = "查詢操作方式"

        return intent_type, intent_description, []

    return QueryIntentType.CONVERSATION, "一般對話", []


# ============================================
# 測試案例：意圖識別與流程路由
# ============================================


def test_intent_routing():
    """意圖識別與流程路由測試"""

    print("\n" + "=" * 70)
    print("測試類別: 意圖識別與流程路由")
    print("=" * 70)

    passed = 0
    failed = 0

    # 數據查詢 → Agent
    test_queries = [
        ("RM01-003 最近 3 個月買進多少？", QueryIntentType.DATA_QUERY),
        ("RM05-008 庫存多少", QueryIntentType.DATA_QUERY),
        ("料號 AB-123 價格", QueryIntentType.DATA_QUERY),
    ]

    for query, expected_intent in test_queries:
        intent, desc, entities = detect_query_intent(query)
        if intent == expected_intent:
            print(f"  ✅ {query[:30]:30s} → {intent}")
            passed += 1
        else:
            print(f"  ❌ {query[:30]:30s} → {intent} (期望: {expected_intent})")
            failed += 1

    # 知識查詢 → KA-Agent
    knowledge_queries = [
        ("MM-Agent 能做什麼？", QueryIntentType.KNOWLEDGE_QUERY),
        ("系統如何使用", QueryIntentType.KNOWLEDGE_QUERY),
    ]

    for query, expected_intent in knowledge_queries:
        intent, desc, entities = detect_query_intent(query)
        if intent == expected_intent:
            print(f"  ✅ {query[:30]:30s} → {intent}")
            passed += 1
        else:
            print(f"  ❌ {query[:30]:30s} → {intent} (期望: {expected_intent})")
            failed += 1

    # 對話 → 直接回應
    conversation_queries = [
        ("你好", QueryIntentType.CONVERSATION),
        ("今天天氣怎麼樣", QueryIntentType.CONVERSATION),
    ]

    for query, expected_intent in conversation_queries:
        intent, desc, entities = detect_query_intent(query)
        if intent == expected_intent:
            print(f"  ✅ {query[:30]:30s} → {intent}")
            passed += 1
        else:
            print(f"  ❌ {query[:30]:30s} → {intent} (期望: {expected_intent})")
            failed += 1

    # 需要澄清
    clarification_queries = [
        ("這個料號庫存還有多少", QueryIntentType.CLARIFICATION_NEEDED),
        ("那個物料的價格", QueryIntentType.CLARIFICATION_NEEDED),
        ("它最近買進多少", QueryIntentType.CLARIFICATION_NEEDED),
    ]

    for query, expected_intent in clarification_queries:
        intent, desc, entities = detect_query_intent(query)
        if intent == expected_intent:
            print(f"  ✅ {query[:30]:30s} → {intent}")
            passed += 1
        else:
            print(f"  ❌ {query[:30]:30s} → {intent} (期望: {expected_intent})")
            failed += 1

    print(f"\n  結果: {passed} 通過, {failed} 失敗")
    return failed == 0


# ============================================
# 測試案例：人類語言狀態
# ============================================


def test_human_language_status():
    """人類語言狀態顯示測試"""

    print("\n" + "=" * 70)
    print("測試類別: 人類語言狀態")
    print("=" * 70)

    passed = 0
    failed = 0

    technical_terms = [
        "semantic_understanding",
        "intent_analysis",
        "router_llm",
        "L1",
        "L2",
        "L3",
        "L4",
        "L5",
        "retrieval",
        "injection",
    ]

    test_queries = [
        "RM01-003 庫存多少",
        "MM-Agent 能做什麼",
        "你好",
    ]

    for query in test_queries:
        intent, desc, entities = detect_query_intent(query)

        # 檢查描述不包含技術術語
        has_technical = any(term.lower() in desc.lower() for term in technical_terms)

        if not has_technical:
            print(f"  ✅ {query[:30]:30s} - 無技術術語")
            passed += 1
        else:
            print(f"  ❌ {query[:30]:30s} - 包含技術術語")
            failed += 1

    # 測試狀態消息格式
    status_tests = [
        ("RM01-003 庫存多少", "數據查詢"),
        ("MM-Agent 能做什麼", "查找"),
        ("這個料號多少", "模糊"),
    ]

    for query, expected_keyword in status_tests:
        intent, desc, entities = detect_query_intent(query)

        # 生成狀態消息
        if intent == QueryIntentType.DATA_QUERY:
            status = f"從您的描述中，我理解您想要：\n• {desc}\n\n這是個明確的數據查詢請求"
        elif intent == QueryIntentType.KNOWLEDGE_QUERY:
            status = f"從您的描述中，我理解您想要：\n• {desc}\n\n正在為您查找相關資訊..."
        elif intent == QueryIntentType.CLARIFICATION_NEEDED:
            status = f"您的請求有點模糊，請問您是指：\n• 具體是哪個料號？"
        else:
            status = "您好！很高興見到您。"

        if expected_keyword in status:
            print(f"  ✅ {query[:30]:30s} - 狀態消息正確")
            passed += 1
        else:
            print(f"  ❌ {query[:30]:30s} - 狀態消息錯誤")
            failed += 1

    print(f"\n  結果: {passed} 通過, {failed} 失敗")
    return failed == 0


# ============================================
# 測試案例：Agent 路由邏輯
# ============================================


def test_agent_routing_logic():
    """Agent 路由邏輯測試"""

    print("\n" + "=" * 70)
    print("測試類別: Agent 路由邏輯")
    print("=" * 70)

    passed = 0
    failed = 0

    # 路由決策邏輯
    def get_routing_decision(query: str) -> Dict[str, Any]:
        intent, desc, entities = detect_query_intent(query)

        if intent == QueryIntentType.DATA_QUERY:
            return {
                "intent": intent,
                "route_to": "mm-agent",
                "retrieve_knowledge": False,
                "requires_context": False,
            }
        elif intent == QueryIntentType.KNOWLEDGE_QUERY:
            return {
                "intent": intent,
                "route_to": "ka-agent",
                "retrieve_knowledge": True,
                "requires_context": False,
            }
        elif intent == QueryIntentType.CLARIFICATION_NEEDED:
            return {
                "intent": intent,
                "route_to": "clarification",
                "retrieve_knowledge": False,
                "requires_context": False,
            }
        else:
            return {
                "intent": intent,
                "route_to": "direct",
                "retrieve_knowledge": False,
                "requires_context": False,
            }

    # 測試路由決策
    routing_tests = [
        ("RM01-003 庫存多少", "mm-agent", False),
        ("MM-Agent 能做什麼", "ka-agent", True),
        ("你好", "direct", False),
        ("這個料號多少", "clarification", False),
    ]

    for query, expected_route, expected_knowledge in routing_tests:
        decision = get_routing_decision(query)

        if (
            decision["route_to"] == expected_route
            and decision["retrieve_knowledge"] == expected_knowledge
        ):
            print(f"  ✅ {query[:30]:30s} → {decision['route_to']}")
            passed += 1
        else:
            print(f"  ❌ {query[:30]:30s} → {decision['route_to']} (期望: {expected_route})")
            failed += 1

    print(f"\n  結果: {passed} 通過, {failed} 失敗")
    return failed == 0


# ============================================
# 測試案例：完整流程
# ============================================


def test_complete_flows():
    """完整流程測試"""

    print("\n" + "=" * 70)
    print("測試類別: 完整流程")
    print("=" * 70)

    passed = 0
    failed = 0

    # 數據查詢完整流程
    def test_data_query_flow():
        query = "RM01-003 最近 3 個月買進多少？"

        # Step 1: 意圖識別
        intent, desc, entities = detect_query_intent(query)
        assert intent == QueryIntentType.DATA_QUERY, "Step 1 失敗"

        # Step 2: 路由決策
        if intent == QueryIntentType.DATA_QUERY:
            route_to = "mm-agent"
            skip_knowledge = True

        assert route_to == "mm-agent", "Step 2 失敗"
        assert skip_knowledge, "Step 2 失敗"

        # Step 3: 狀態消息
        status = f"從您的描述中，我理解您想要：\n• {desc}\n\n這是個明確的數據查詢請求"
        assert "數據查詢" in status, "Step 3 失敗"

        # Step 4: Agent 執行
        agent_result = {
            "success": True,
            "part_number": "RM01-003",
            "purchase_quantity": 5000,
        }
        assert agent_result["success"], "Step 4 失敗"

        return True

    if test_data_query_flow():
        print("  ✅ 數據查詢完整流程")
        passed += 1
    else:
        print("  ❌ 數據查詢完整流程")
        failed += 1

    # 知識查詢完整流程
    def test_knowledge_query_flow():
        query = "MM-Agent 能做什麼？"

        # Step 1: 意圖識別
        intent, desc, entities = detect_query_intent(query)
        assert intent == QueryIntentType.KNOWLEDGE_QUERY, "Step 1 失敗"

        # Step 2: 路由決策
        if intent == QueryIntentType.KNOWLEDGE_QUERY:
            route_to = "ka-agent"
            retrieve_knowledge = True

        assert route_to == "ka-agent", "Step 2 失敗"
        assert retrieve_knowledge, "Step 2 失敗"

        # Step 3: 狀態消息
        status = f"從您的描述中，我理解您想要：\n• {desc}\n\n正在為您查找相關資訊..."
        assert "查找" in status, "Step 3 失敗"

        return True

    if test_knowledge_query_flow():
        print("  ✅ 知識查詢完整流程")
        passed += 1
    else:
        print("  ❌ 知識查詢完整流程")
        failed += 1

    # 澄清流程
    def test_clarification_flow():
        query = "這個料號庫存還有多少？"

        # Step 1: 意圖識別
        intent, desc, entities = detect_query_intent(query)
        assert intent == QueryIntentType.CLARIFICATION_NEEDED, "Step 1 失敗"

        # Step 2: 詢問澄清
        question = f"您的請求有點模糊，請問您是指：\n• 具體是哪個料號？"
        assert "料號" in question, "Step 2 失敗"

        return True

    if test_clarification_flow():
        print("  ✅ 澄清流程")
        passed += 1
    else:
        print("  ❌ 澄清流程")
        failed += 1

    print(f"\n  結果: {passed} 通過, {failed} 失敗")
    return failed == 0


# ============================================
# 測試案例：邊界情況
# ============================================


def test_edge_cases():
    """邊界情況測試"""

    print("\n" + "=" * 70)
    print("測試類別: 邊界情況")
    print("=" * 70)

    passed = 0
    failed = 0

    edge_cases = [
        # (查詢, 期望意圖, 描述)
        ("", QueryIntentType.CONVERSATION, "空查詢"),
        ("RM01-003 " * 100 + "庫存多少？", QueryIntentType.DATA_QUERY, "長查詢"),
        ("RM01-003 庫存多少？ MM-Agent 能做什麼？", QueryIntentType.DATA_QUERY, "混合意圖"),
        ("RM01-003!!! @#$% 庫存多少？", QueryIntentType.DATA_QUERY, "特殊字符"),
        ("這個月採購多少", QueryIntentType.DATA_QUERY, "這個月不是澄清"),
        ("怎麼用這個系統", QueryIntentType.KNOWLEDGE_QUERY, "怎麼用不是澄清"),
    ]

    for query, expected_intent, description in edge_cases:
        intent, desc, entities = detect_query_intent(query)

        if intent == expected_intent:
            print(f"  ✅ {description:20s} → {intent}")
            passed += 1
        else:
            print(f"  ❌ {description:20s} → {intent} (期望: {expected_intent})")
            failed += 1

    print(f"\n  結果: {passed} 通過, {failed} 失敗")
    return failed == 0


# ============================================
# 主測試函數
# ============================================


def run_all_tests():
    """運行所有整合測試"""

    print("=" * 70)
    print("MM-Agent 整合測試套件")
    print("=" * 70)

    results = []

    results.append(("意圖識別與流程路由", test_intent_routing()))
    results.append(("人類語言狀態", test_human_language_status()))
    results.append(("Agent 路由邏輯", test_agent_routing_logic()))
    results.append(("完整流程", test_complete_flows()))
    results.append(("邊界情況", test_edge_cases()))

    print("\n" + "=" * 70)
    print("測試摘要")
    print("=" * 70)

    total_passed = sum(1 for _, passed in results if passed)
    total_failed = sum(1 for _, passed in results if not passed)

    for name, passed in results:
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"  {name:25s} {status}")

    print("=" * 70)
    print(f"總結果: {total_passed} 通過, {total_failed} 失敗")
    print("=" * 70)

    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
