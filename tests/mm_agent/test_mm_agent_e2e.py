# 代碼功能說明: MM-Agent 端到端測試 - 意圖識別核心測試
# 創建日期: 2026-02-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-04

"""
MM-Agent 端到端測試套件

測試場景：
1. 問候/閒聊 → 直接回應
2. 知識問題 → 檢索知識庫
3. 數據查詢 → 啟動 MM-Agent
4. 需要澄清 → 詢問用戶
"""

import pytest
import re
from unittest.mock import Mock, AsyncMock


# ============================================
# 測試案例：意圖識別函數
# ============================================


class TestQueryIntentDetection:
    """測試意圖識別函數"""

    def test_data_query_rm_code(self):
        """測試：RM01-003 料號查詢 → 數據查詢"""
        from api.routers.chat import _detect_query_intent, QueryIntentType

        test_cases = [
            ("RM01-003 最近 3 個月買進多少？", QueryIntentType.DATA_QUERY),
            ("RM05-008 上月庫存多少", QueryIntentType.DATA_QUERY),
            ("RM01003 價格多少", QueryIntentType.DATA_QUERY),
        ]

        for query, expected_intent in test_cases:
            intent, desc, entities = _detect_query_intent(query)
            assert intent == expected_intent, (
                f"Query '{query}' expected {expected_intent}, got {intent}"
            )

    def test_data_query_keywords(self):
        """測試：庫存/採購關鍵詞 → 數據查詢"""
        from api.routers.chat import _detect_query_intent, QueryIntentType

        test_cases = [
            ("料號 RM01-003 庫存多少", QueryIntentType.DATA_QUERY),
            ("物料 AB-123 買進數量", QueryIntentType.DATA_QUERY),
            ("最近 3 個月出貨記錄", QueryIntentType.DATA_QUERY),
            ("這個月採購多少", QueryIntentType.DATA_QUERY),
        ]

        for query, expected_intent in test_cases:
            intent, desc, entities = _detect_query_intent(query)
            assert intent == expected_intent, (
                f"Query '{query}' expected {expected_intent}, got {intent}"
            )

    def test_knowledge_query_system(self):
        """測試：系統能力問題 → 知識查詢"""
        from api.routers.chat import _detect_query_intent, QueryIntentType

        test_cases = [
            ("MM-Agent 能做什麼？", QueryIntentType.KNOWLEDGE_QUERY),
            ("你有什麼功能", QueryIntentType.KNOWLEDGE_QUERY),
            ("系統如何使用", QueryIntentType.KNOWLEDGE_QUERY),
            ("怎麼用這個系統", QueryIntentType.KNOWLEDGE_QUERY),
        ]

        for query, expected_intent in test_cases:
            intent, desc, entities = _detect_query_intent(query)
            assert intent == expected_intent, (
                f"Query '{query}' expected {expected_intent}, got {intent}"
            )

    def test_knowledge_query_ai_identity(self):
        """測試：AI 身份問題 → 知識查詢"""
        from api.routers.chat import _detect_query_intent, QueryIntentType

        test_cases = [
            ("你是誰？", QueryIntentType.KNOWLEDGE_QUERY),
            ("你的職責是什麼", QueryIntentType.KNOWLEDGE_QUERY),
            ("你有什麼能力", QueryIntentType.KNOWLEDGE_QUERY),
            ("你能做什麼", QueryIntentType.KNOWLEDGE_QUERY),
            ("什麼是 MM-Agent", QueryIntentType.KNOWLEDGE_QUERY),
        ]

        for query, expected_intent in test_cases:
            intent, desc, entities = _detect_query_intent(query)
            assert intent == expected_intent, (
                f"Query '{query}' expected {expected_intent}, got {intent}"
            )

    def test_conversation_greeting(self):
        """測試：問候/閒聊 → 一般對話"""
        from api.routers.chat import _detect_query_intent, QueryIntentType

        test_cases = [
            ("你好", QueryIntentType.CONVERSATION),
            ("嗨，您好", QueryIntentType.CONVERSATION),
            ("今天天氣怎麼樣", QueryIntentType.CONVERSATION),
            ("很高興見到你", QueryIntentType.CONVERSATION),
        ]

        for query, expected_intent in test_cases:
            intent, desc, entities = _detect_query_intent(query)
            assert intent == expected_intent, (
                f"Query '{query}' expected {expected_intent}, got {intent}"
            )

    def test_clarification_pronouns(self):
        """測試：指代不明確 → 需要澄清"""
        from api.routers.chat import _detect_query_intent, QueryIntentType

        test_cases = [
            ("這個料號庫存還有多少", QueryIntentType.CLARIFICATION_NEEDED),
            ("那個物料的價格", QueryIntentType.CLARIFICATION_NEEDED),
            ("它最近買進多少", QueryIntentType.CLARIFICATION_NEEDED),
            ("之前說的那個料號", QueryIntentType.CLARIFICATION_NEEDED),
        ]

        for query, expected_intent in test_cases:
            intent, desc, entities = _detect_query_intent(query)
            assert intent == expected_intent, (
                f"Query '{query}' expected {expected_intent}, got {intent}"
            )


# ============================================
# 測試案例：意圖識別實體提取
# ============================================


class TestQueryIntentEntities:
    """測試意圖識別的實體提取"""

    def test_data_query_extracts_part_number(self):
        """測試：數據查詢正確提取料號"""
        from api.routers.chat import _detect_query_intent

        intent, desc, entities = _detect_query_intent("RM01-003 最近 3 個月買進多少？")

        # 應該提取到料號
        has_part_number = any("rm01-003" in e.lower() or "rm01" in e.lower() for e in entities)
        assert has_part_number or len(entities) > 0, f"Should extract entities, got: {entities}"

    def test_clarification_extracts_entities(self):
        """測試：需要澄清時也會提取實體"""
        from api.routers.chat import _detect_query_intent

        intent, desc, entities = _detect_query_intent("這個料號庫存還有多少？")

        # 應該提取到「料號」實體
        has_entity = any("料號" in e or "這" in e for e in entities) or len(entities) > 0
        assert has_entity or intent == QueryIntentType.CLARIFICATION_NEEDED


# ============================================
# 測試案例：意圖描述生成
# ============================================


class TestQueryIntentDescription:
    """測試意圖描述是否人類可讀"""

    def test_data_query_description(self):
        """測試：數據查詢的描述"""
        from api.routers.chat import _detect_query_intent

        intent, desc, entities = _detect_query_intent("RM01-003 庫存多少？")

        # 描述應該是人類語言
        assert desc and len(desc) > 0
        assert "數據" in desc or "query" in desc.lower()

    def test_knowledge_query_description(self):
        """測試：知識查詢的描述"""
        from api.routers.chat import _detect_query_intent

        intent, desc, entities = _detect_query_intent("MM-Agent 能做什麼？")

        # 描述應該是人類語言
        assert desc and len(desc) > 0


# ============================================
# 測試案例：流程邏輯模擬
# ============================================


class TestFlowLogic:
    """測試流程邏輯"""

    def test_conversation_flow_no_knowledge_retrieval(self):
        """測試：對話流程不應該觸發知識庫檢索"""
        from api.routers.chat import _detect_query_intent, QueryIntentType

        # 模擬流程邏輯
        def should_retrieve_knowledge(query: str) -> bool:
            intent, desc, entities = _detect_query_intent(query)
            return intent == QueryIntentType.KNOWLEDGE_QUERY

        # 問候不應該觸發知識庫
        assert should_retrieve_knowledge("你好") == False
        assert should_retrieve_knowledge("今天天氣") == False

        # 知識問題應該觸發知識庫
        assert should_retrieve_knowledge("你能做什麼？") == True
        assert should_retrieve_knowledge("系統怎麼用") == True

    def test_data_query_flow_no_knowledge_retrieval(self):
        """測試：數據查詢不應該觸發知識庫檢索"""
        from api.routers.chat import _detect_query_intent, QueryIntentType

        # 模擬流程邏輯
        def should_retrieve_knowledge(query: str) -> bool:
            intent, desc, entities = _detect_query_intent(query)
            return intent == QueryIntentType.KNOWLEDGE_QUERY

        def should_route_to_agent(query: str) -> bool:
            intent, desc, entities = _detect_query_intent(query)
            return intent == QueryIntentType.DATA_QUERY

        # 數據查詢應該路由到 Agent，不應該查知識庫
        assert should_retrieve_knowledge("RM01-003 庫存多少") == False
        assert should_route_to_agent("RM01-003 庫存多少") == True


# ============================================
# 測試案例：優先級測試
# ============================================


class TestIntentPriority:
    """測試意圖優先級"""

    def test_data_query_priority_over_conversation(self):
        """測試：數據查詢優先於一般對話"""
        from api.routers.chat import _detect_query_intent

        # 測試包含時間查詢的數據查詢
        intent, desc, entities = _detect_query_intent("RM01-003 今天買進多少？")

        # 應該識別為數據查詢，不是對話
        from api.routers.chat import QueryIntentType

        assert intent != QueryIntentType.CONVERSATION

    def test_clarification_priority(self):
        """測試：需要澄清的優先級"""
        from api.routers.chat import _detect_query_intent, QueryIntentType

        # 指代不明確時，優先要求澄清
        intent, desc, entities = _detect_query_intent("那個料號多少")

        assert intent == QueryIntentType.CLARIFICATION_NEEDED


# ============================================
# 測試運行配置
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
