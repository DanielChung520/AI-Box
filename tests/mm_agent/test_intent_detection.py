# 代碼功能說明: MM-Agent 意圖識別邏輯測試（獨立運行版本）
# 創建日期: 2026-02-04
# 創建人: Daniel Chung

"""
意圖識別邏輯測試

測試場景：
1. 問候/閒聊 → 直接回應
2. 知識問題 → 檢索知識庫
3. 數據查詢 → 啟動 MM-Agent
4. 需要澄清 → 詢問用戶
"""

import re
from typing import Dict, Any, List, Tuple


# ============================================
# 意圖識別邏輯（從 chat.py 複製）
# ============================================


class QueryIntentType:
    """查詢意圖類型枚舉"""

    DATA_QUERY = "data_query"  # 數據查詢（業務數據）
    KNOWLEDGE_QUERY = "knowledge_query"  # 知識查詢（系統能力、操作方式）
    CONVERSATION = "conversation"  # 一般對話
    CLARIFICATION_NEEDED = "clarification_needed"  # 需要澄清


def detect_query_intent(user_query: str) -> Tuple[str, str, List[str]]:
    """
    識別用戶查詢的意圖類型

    這是知識庫使用的核心邏輯：
    - 知識庫存的是「如何做」的知識，不是業務數據
    - 業務數據應該向後端系統查詢，不是從知識庫檢索

    Args:
        user_query: 用戶的查詢內容

    Returns:
        tuple: (意圖類型, 意圖描述, 關鍵實體列表)
    """
    query = user_query.strip()
    query_lower = query.lower()

    # 數據查詢的關鍵詞模式（必須有明確的數據標識）
    data_query_patterns = [
        # 料號/物料相關 - 必須有 RM 代碼或具體料號
        r"rm\d{2}-?\d{3,}",  # RM01-003, RM01003
        r"料號\s*[A-Za-z0-9\-]+",  # 料號 AB-123
        r"物料\s*[A-Za-z0-9\-]+",  # 物料 AB-123
        r"part\s*[A-Za-z0-9]+",  # part AB123
        # 時間範圍相關（也是數據查詢）
        r"最近\s*\d+\s*個月?",
        r"這\s*\d+\s*天?",
        r"上月",
        r"本月",
        r"上週",
        r"本週",
        r"這個月",
        r"那個月",
    ]

    # 檢查是否包含「沒有明確標識」的數據關鍵詞
    ambiguous_data_keywords = [
        r"庫存",
        r"買進",
        r"賣出",
        r"採購",
        r"進貨",
        r"出貨",
        r"訂單",
        r"多少錢",
        r"單價",
        r"價格",
        r"供應商",
        r"廠商",
    ]

    # 檢查是否包含「沒有明確標識」的數據關鍵詞
    ambiguous_data_keywords = [
        r"庫存",
        r"買進",
        r"賣出",
        r"採購",
        r"進貨",
        r"出貨",
        r"訂單",
        r"多少錢",
        r"單價",
        r"價格",
        r"供應商",
        r"廠商",
    ]

    # 檢查是否包含「沒有明確標識」的數據關鍵詞
    ambiguous_data_keywords = [
        r"庫存",
        r"買進",
        r"賣出",
        r"採購",
        r"進貨",
        r"出貨",
        r"訂單",
        r"多少錢",
        r"單價",
        r"價格",
        r"供應商",
        r"廠商",
    ]

    # 知識查詢的關鍵詞模式
    knowledge_query_patterns = [
        # 系統能力相關
        r"能做什麼",
        r"有什麼功能",
        r"系統能",
        r"如何使用",
        r"怎麼用",
        r"如何[操作|使用|設定]",
        # AI 知識相關
        r"你是誰",
        r"你的職責",
        r"你能做",
        r"你有什麼能力",
        r"什麼是",
        r"解釋一下",
    ]

    # 需要澄清的模糊模式
    clarification_patterns = [
        r"那個",
        r"這個",
        r"它",
        r"之前.*",
        r"相關.*",
    ]

    # 檢測數據查詢意圖
    data_query_matches = []
    has_explicit_data = False
    has_ambiguous_keyword = False

    for pattern in data_query_patterns:
        matches = re.findall(pattern, query_lower)
        if matches:
            data_query_matches.extend(matches)
            has_explicit_data = True

    # 檢查是否有模糊的數據關鍵詞（沒有明確標識時）
    for pattern in ambiguous_data_keywords:
        if re.search(pattern, query_lower):
            has_ambiguous_keyword = True
            break

    # 如果有明確數據標識 + 模糊關鍵詞 = 數據查詢
    # 如果只有模糊關鍵詞，沒有明確標識 = 需要澄清
    if has_explicit_data and has_ambiguous_keyword:
        intent_type = QueryIntentType.DATA_QUERY
        intent_description = "查詢業務數據"
        entities = list(set(data_query_matches))
        return intent_type, intent_description, entities

    if has_explicit_data:
        # 有明確數據標識，視為數據查詢
        intent_type = QueryIntentType.DATA_QUERY
        intent_description = "查詢業務數據"
        entities = list(set(data_query_matches))
        return intent_type, intent_description, entities

    if has_ambiguous_keyword:
        # 只有模糊關鍵詞，沒有明確標識 = 需要澄清
        intent_type = QueryIntentType.CLARIFICATION_NEEDED
        intent_description = "需要澄清的模糊查詢"
        entities = ["無法識別的具體數據"]
        return intent_type, intent_description, entities

    # 檢測知識查詢意圖
    knowledge_query_matches = []
    for pattern in knowledge_query_patterns:
        if re.search(pattern, query_lower):
            knowledge_query_matches.append(pattern)
            break

    if knowledge_query_matches:
        # 這是一個知識查詢
        intent_type = QueryIntentType.KNOWLEDGE_QUERY
        intent_description = "查詢系統知識"

        return intent_type, intent_description, []

    # 檢測是否需要澄清
    clarification_matches = []
    for pattern in clarification_patterns:
        if re.search(pattern, query_lower):
            # 檢查是否有明確的數據標識（如 RM 代碼等）
            # 只匹配 RM 格式的料號，不匹配純文字「料號」
            has_explicit_data = re.search(r"rm\d{2}-?\d{3,}", query_lower)

            # 如果沒有明確的 RM 代碼，才是澄清需求
            if not has_explicit_data:
                clarification_matches.append(pattern)
                break

    if clarification_matches:
        # 這是一個需要澄清的查詢
        intent_type = QueryIntentType.CLARIFICATION_NEEDED
        intent_description = "需要澄清的模糊查詢"
        entities = ["無法識別的指代詞"]

        return intent_type, intent_description, entities

    # 默認為一般對話
    return QueryIntentType.CONVERSATION, "一般對話", []


# ============================================
# 流程邏輯測試
# ============================================


def should_retrieve_knowledge(query: str) -> bool:
    """判斷是否應該檢索知識庫"""
    intent, desc, entities = detect_query_intent(query)
    return intent == QueryIntentType.KNOWLEDGE_QUERY


def should_route_to_agent(query: str) -> bool:
    """判斷是否應該路由到 Agent"""
    intent, desc, entities = detect_query_intent(query)
    return intent == QueryIntentType.DATA_QUERY


def should_ask_clarification(query: str) -> bool:
    """判斷是否需要澄清"""
    intent, desc, entities = detect_query_intent(query)
    return intent == QueryIntentType.CLARIFICATION_NEEDED


def should_direct_respond(query: str) -> bool:
    """判斷是否應該直接回應"""
    intent, desc, entities = detect_query_intent(query)
    return intent == QueryIntentType.CONVERSATION


# ============================================
# 測試案例
# ============================================


def test_data_query_rm_code():
    """測試：RM01-003 料號查詢 → 數據查詢"""
    test_cases = [
        "RM01-003 最近 3 個月買進多少？",
        "RM05-008 上月庫存多少",
        "RM01003 價格多少",
    ]

    print("\n=== 測試：RM 代碼數據查詢 ===")
    for query in test_cases:
        intent, desc, entities = detect_query_intent(query)
        assert intent == QueryIntentType.DATA_QUERY, (
            f"Query '{query}' expected DATA_QUERY, got {intent}"
        )
        print(f"  ✅ '{query}' → {intent} ({desc})")


def test_data_query_keywords():
    """測試：庫存/採購關鍵詞 → 數據查詢"""
    test_cases = [
        ("料號 RM01-003 庫存多少", QueryIntentType.DATA_QUERY),
        ("物料 AB-123 買進數量", QueryIntentType.DATA_QUERY),
        ("最近 3 個月出貨記錄", QueryIntentType.DATA_QUERY),
        ("這個月採購多少", QueryIntentType.DATA_QUERY),
    ]

    print("\n=== 測試：數據查詢關鍵詞 ===")
    for query, expected_intent in test_cases:
        intent, desc, entities = detect_query_intent(query)
        assert intent == expected_intent, (
            f"Query '{query}' expected {expected_intent}, got {intent}"
        )
        print(f"  ✅ '{query}' → {intent} ({desc})")


def test_knowledge_query_system():
    """測試：系統能力問題 → 知識查詢"""
    test_cases = [
        "MM-Agent 能做什麼？",
        "你有什麼功能",
        "系統如何使用",
        "怎麼用這個系統",
    ]

    print("\n=== 測試：系統能力知識查詢 ===")
    for query in test_cases:
        intent, desc, entities = detect_query_intent(query)
        assert intent == QueryIntentType.KNOWLEDGE_QUERY, (
            f"Query '{query}' expected KNOWLEDGE_QUERY, got {intent}"
        )
        print(f"  ✅ '{query}' → {intent} ({desc})")


def test_knowledge_query_ai_identity():
    """測試：AI 身份問題 → 知識查詢"""
    test_cases = [
        "你是誰？",
        "你的職責是什麼",
        "你有什麼能力",
        "你能做什麼",
        "什麼是 MM-Agent",
    ]

    print("\n=== 測試：AI 身份知識查詢 ===")
    for query in test_cases:
        intent, desc, entities = detect_query_intent(query)
        assert intent == QueryIntentType.KNOWLEDGE_QUERY, (
            f"Query '{query}' expected KNOWLEDGE_QUERY, got {intent}"
        )
        print(f"  ✅ '{query}' → {intent} ({desc})")


def test_conversation_greeting():
    """測試：問候/閒聊 → 一般對話"""
    test_cases = [
        "你好",
        "嗨，您好",
        "今天天氣怎麼樣",
        "很高興見到你",
    ]

    print("\n=== 測試：問候/閒聊 ===")
    for query in test_cases:
        intent, desc, entities = detect_query_intent(query)
        assert intent == QueryIntentType.CONVERSATION, (
            f"Query '{query}' expected CONVERSATION, got {intent}"
        )
        print(f"  ✅ '{query}' → {intent} ({desc})")


def test_clarification_pronouns():
    """測試：指代不明確 → 需要澄清"""
    test_cases = [
        "這個料號庫存還有多少",
        "那個物料的價格",
        "它最近買進多少",
        "之前說的那個料號",
    ]

    print("\n=== 測試：指代需要澄清 ===")
    for query in test_cases:
        intent, desc, entities = detect_query_intent(query)
        assert intent == QueryIntentType.CLARIFICATION_NEEDED, (
            f"Query '{query}' expected CLARIFICATION_NEEDED, got {intent}"
        )
        print(f"  ✅ '{query}' → {intent} ({desc})")


def test_flow_logic():
    """測試：流程邏輯"""
    print("\n=== 測試：流程邏輯 ===")

    # 問候不應該觸發知識庫
    assert should_retrieve_knowledge("你好") == False
    print("  ✅ 問候不會觸發知識庫")

    # 知識問題應該觸發知識庫
    assert should_retrieve_knowledge("你能做什麼？") == True
    print("  ✅ 知識問題會觸發知識庫")

    # 數據查詢應該路由到 Agent
    assert should_route_to_agent("RM01-003 庫存多少") == True
    print("  ✅ 數據查詢會路由到 Agent")

    # 數據查詢不應該觸發知識庫
    assert should_retrieve_knowledge("RM01-003 庫存多少") == False
    print("  ✅ 數據查詢不會觸發知識庫")

    # 指代不明確需要澄清
    assert should_ask_clarification("這個料號多少") == True
    print("  ✅ 指代需要澄清")


def test_entity_extraction():
    """測試：實體提取"""
    print("\n=== 測試：實體提取 ===")

    intent, desc, entities = detect_query_intent("RM01-003 最近 3 個月買進多少？")
    print(f"  Query: 'RM01-003 最近 3 個月買進多少？'")
    print(f"  Entities: {entities}")
    assert len(entities) > 0, "Should extract part number entities"


# ============================================
# 主測試函數
# ============================================


def run_all_tests():
    """運行所有測試"""
    print("=" * 70)
    print("MM-Agent 意圖識別測試")
    print("=" * 70)

    try:
        test_data_query_rm_code()
        test_data_query_keywords()
        test_knowledge_query_system()
        test_knowledge_query_ai_identity()
        test_conversation_greeting()
        test_clarification_pronouns()
        test_flow_logic()
        test_entity_extraction()

        print("\n" + "=" * 70)
        print("✅ 所有測試通過！")
        print("=" * 70)
        return True

    except AssertionError as e:
        print(f"\n❌ 測試失敗: {e}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
