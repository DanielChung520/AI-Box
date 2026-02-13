# Schema RAG 模組
# 代碼功能說明: Schema RAG 初始化模組
# 創建日期: 2026-02-13
# 創建人: Daniel Chung

"""Schema RAG 模組

職責：
- 意圖識別（Intent Recognition）
- 概念匹配（Concept Matching）
- 綁定解析（Binding Resolution）
- Schema 同步（Qdrant + ArangoDB）
- Master Data 同步

使用示例：
    from data_agent.RAG.schema_rag_jp import SchemaRAGJP

    rag = SchemaRAGJP()
    intents = rag.retrieve_intents("查詢料號庫存")
"""

from .schema_rag_jp import SchemaRAGJP, ConceptRetrievalResult, IntentRetrievalResult

__all__ = ["SchemaRAGJP", "ConceptRetrievalResult", "IntentRetrievalResult"]
