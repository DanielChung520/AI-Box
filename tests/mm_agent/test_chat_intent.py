#!/usr/bin/env python3
# 代碼功能說明: 測試 chat.py 的意圖識別邏輯
# 創建日期: 2026-02-04

"""測試 chat.py 的意圖識別邏輯"""

import sys

sys.path.insert(0, "/home/daniel/ai-box")

# 直接複製意圖識別函數來測試
import re
from typing import Tuple, List


class QueryIntentType:
    DATA_QUERY = "data_query"
    KNOWLEDGE_QUERY = "knowledge_query"
    CONVERSATION = "conversation"
    CLARIFICATION_NEEDED = "clarification_needed"


def detect_query_intent(user_query: str) -> Tuple[str, str, List[str]]:
    """從 chat.py 複製的意圖識別函數"""
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
        r"^(?!這個月|這個週)[這那]個",  # 以「這個/那個」開頭，但不是「這個月/這個週」
        r"(?<![月年日週時])\s+這[個件]",  # 「這個/這件」前面不是時間單位
        r"(?<![月年日週時])\s+那[個件]",  # 「那個/那件」前面不是時間單位
        r"^它",  # 「它」開頭（指代不明確）
        r"之前說的",  # 「之前說的」指代
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


def test_all_cases():
    """測試所有場景"""
    test_cases = [
        # (查詢, 期望意圖)
        # 數據查詢
        ("RM01-003 最近 3 個月買進多少？", QueryIntentType.DATA_QUERY),
        ("RM05-008 上月庫存多少", QueryIntentType.DATA_QUERY),
        ("料號 RM01-003 庫存多少", QueryIntentType.DATA_QUERY),
        ("物料 AB-123 買進數量", QueryIntentType.DATA_QUERY),
        ("最近 3 個月出貨記錄", QueryIntentType.DATA_QUERY),
        ("這個月採購多少", QueryIntentType.DATA_QUERY),
        # 知識查詢
        ("MM-Agent 能做什麼？", QueryIntentType.KNOWLEDGE_QUERY),
        ("你有什麼功能", QueryIntentType.KNOWLEDGE_QUERY),
        ("系統如何使用", QueryIntentType.KNOWLEDGE_QUERY),
        ("怎麼用這個系統", QueryIntentType.KNOWLEDGE_QUERY),
        ("你是誰？", QueryIntentType.KNOWLEDGE_QUERY),
        ("你的職責是什麼", QueryIntentType.KNOWLEDGE_QUERY),
        # 問候/閒聊
        ("你好", QueryIntentType.CONVERSATION),
        ("嗨，您好", QueryIntentType.CONVERSATION),
        ("今天天氣怎麼樣", QueryIntentType.CONVERSATION),
        # 需要澄清
        ("這個料號庫存還有多少", QueryIntentType.CLARIFICATION_NEEDED),
        ("那個物料的價格", QueryIntentType.CLARIFICATION_NEEDED),
        ("它最近買進多少", QueryIntentType.CLARIFICATION_NEEDED),
        ("之前說的那個料號", QueryIntentType.CLARIFICATION_NEEDED),
    ]

    passed = 0
    failed = 0

    print("=" * 70)
    print("意圖識別測試")
    print("=" * 70)

    for query, expected_intent in test_cases:
        intent, desc, entities = detect_query_intent(query)

        if intent == expected_intent:
            print(f"  ✅ {query[:30]:30s} → {intent:20s} ({desc})")
            passed += 1
        else:
            print(f"  ❌ {query[:30]:30s} → {intent:20s} (期望: {expected_intent})")
            failed += 1

    print("=" * 70)
    print(f"結果: {passed} 通過, {failed} 失敗")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = test_all_cases()
    exit(0 if success else 1)
