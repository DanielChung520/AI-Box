# Agent 能力 RAG 初始化說明

**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-11

---

## 📋 概述

本文檔說明如何初始化 Agent 能力 RAG 向量庫，將 Agent 相關文檔存儲到 RAG 向量數據庫（ChromaDB/AAM），以便在 Agent 選擇時進行語義檢索。

---

## ✅ Agent 註冊確認

### 已確認註冊的 Agent

根據代碼分析，以下 Agent 已經正確註冊為 System Agent：

1. **md-editor** (Markdown Editor Agent v2.0)
   - Agent ID: `md-editor`
   - 註冊位置: `agents/builtin/__init__.py` (line 482-584)
   - System Agent Registry: ✅ 已註冊（`is_system_agent: True`）

2. **xls-editor** (Excel Editor Agent v2.0)
   - Agent ID: `xls-editor`
   - 註冊位置: `agents/builtin/__init__.py` (line 587-605)

3. **md-to-pdf** (Markdown to PDF Agent v2.0)
   - Agent ID: `md-to-pdf`
   - 註冊位置: `agents/builtin/__init__.py` (line 607-624)

4. **xls-to-pdf** (Excel to PDF Agent v2.0)
   - Agent ID: `xls-to-pdf`
   - 註冊位置: `agents/builtin/__init__.py` (line 626-643)

5. **pdf-to-md** (PDF to Markdown Agent v2.0)
   - Agent ID: `pdf-to-md`
   - 註冊位置: `agents/builtin/__init__.py` (line 645-662)

**詳細確認報告**: 請參閱 `Agent註冊確認報告.md`

---

## 📚 RAG 初始化腳本

### 腳本位置

`scripts/init_agent_capabilities_rag.py`

### 功能說明

該腳本會將以下內容存儲到 RAG 向量數據庫：

1. **Agent 能力描述**（從 Agent Registry 獲取）
   - 所有在線 Agent 的能力描述
   - Agent ID、名稱、類型、能力列表
   - 適用場景說明

2. **設計文檔**
   - `文件編輯-Agent-模組設計-v2.md`
   - `文件編輯-Agent-系統規格書-v2.0.md`
   - `Agent-Platform.md`（內部版本 v4.0）

### 使用方法

```bash
# 從項目根目錄執行
cd /Users/daniel/GitHub/AI-Box
python3 scripts/init_agent_capabilities_rag.py
```

### 存儲位置

- **命名空間**: `agent_capabilities`
- **存儲方式**: AAMManager → ChromaDB（向量存儲）
- **文檔分割**: 自動將長文檔分割為 2000 字符的塊

### 文檔結構

每個文檔塊包含以下元數據：

```python
{
    "doc_id": "file_editing_agent_module_design_v2",
    "doc_type": "design_document",  # 或 "specification", "architecture", "agent_capability"
    "title": "文件編輯 Agent 模組設計 v2.0",
    "category": "module_design",
    "version": "2.0",
    "chunk_index": 0,
    "total_chunks": 5,
    "namespace": "agent_capabilities"
}
```

---

## 🔍 RAG 檢索使用

### 在 AgentCapabilityRetriever 中使用

`AgentCapabilityRetriever.retrieve_matching_agents()` 會自動從 `agent_capabilities` 命名空間檢索：

```python
from agents.task_analyzer.agent_capability_retriever import AgentCapabilityRetriever

retriever = AgentCapabilityRetriever()
matching_agents = await retriever.retrieve_matching_agents(
    user_input="編輯文件 README.md",
    intent_type="execution",
    top_k=5,
)
```

### 檢索結果格式

```python
[
    {
        "agent_id": "md-editor",
        "score": 0.85,
        "metadata": {
            "doc_id": "agent_md-editor",
            "doc_type": "agent_capability",
            "agent_type": "document_editing",
            ...
        },
        "content": "Agent ID: md-editor\n..."
    },
    ...
]
```

---

## 📝 相關文件

- RAG 初始化腳本: `scripts/init_agent_capabilities_rag.py`
- Agent 能力檢索服務: `agents/task_analyzer/agent_capability_retriever.py`
- Agent 註冊確認報告: `Agent註冊確認報告.md`
- AAMManager: `agents/infra/memory/aam/aam_core.py`
- HybridRAGService: `genai/workflows/rag/hybrid_rag.py`

---

## ⚠️ 注意事項

1. **首次運行**: 需要確保 AAMManager 和 ChromaDB 已正確初始化
2. **文檔更新**: 如果文檔有更新，需要重新運行初始化腳本
3. **命名空間**: 所有 Agent 能力相關文檔都存儲在 `agent_capabilities` 命名空間
4. **向量化**: 文檔會自動進行向量化並存儲到 ChromaDB

---

## 🔄 更新流程

當需要更新 RAG 向量庫時：

1. 更新相關文檔
2. 運行初始化腳本：`python3 scripts/init_agent_capabilities_rag.py`
3. 驗證存儲結果（檢查日誌輸出）

---

**最後更新日期**: 2026-01-11
