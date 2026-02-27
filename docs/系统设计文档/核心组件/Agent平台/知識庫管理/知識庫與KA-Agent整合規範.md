# 知識庫與 KA-Agent 整合規範

> **文件狀態**: 工程開發規範  
> **文檔版本**: v3.0.0  
> **最後更新**: 2026-02-21  
> **維護人**: Daniel Chung  
> **對齊系統**: AI-Box v3.0

---

## 1. 概述

本文檔定義 AI-Box 知識庫管理與 KA-Agent 的整合規範，確保：
- 知識作為平台級資產的統一治理
- 業務代理（MM-Agent）透過 KA-Agent 進行知識檢索
- 授權與安全的端到端保障

### 1.1 設計原則

1. **Knowledge is not memory**：知識是平台級資產，不屬於任何單一 Agent
2. **Assets over documents**：以 Knowledge Base 為治理單位，而非原始文件
3. **Governance before retrieval**：所有檢索操作必須先通過安全審計
4. **Unified Retrieval**：所有 Agent 統一通過 KA-Agent 進行知識檢索
5. **Authorization by agent_key**：根據呼叫者的 `agent_key` 進行動態授權

---

## 2. 核心概念

### 2.1 角色定義

| 角色 | 說明 | 示例 |
|------|------|------|
| **業務代理 (Business Agent)** | 處理特定領域業務邏輯的代理 | MM-Agent (經寶物料管理代理) |
| **知識服務代理 (KA-Agent)** | 統一提供知識檢索服務 | Knowledge Architect Agent |
| **HybridRAG** | 向量 + 圖譜混合檢索引擎 | Qdrant + ArangoDB |

### 2.2 數據關係

```
agent_display_configs._key (如 "-h0tjyh")
    ↓
agent_config.knowledge_bases = [kb_roots._key]
    ↓
file_metadata.knowledge_base_id = kb_roots._key
```

| Collection | Key 欄位 | 關聯欄位 |
|------------|---------|---------|
| `agent_display_configs` | `_key` (arangodb_key) | `knowledge_bases` |
| `kb_roots` | `_key` | - |
| `file_metadata` | `file_id` | `knowledge_base_id` → `kb_roots._key` |

---

## 3. 完整流程

### 3.1 端到端流程

```
用戶在 AI-Box 輸入查詢
    │
    ▼
AI-Box 意圖分類
    │
    ▼ [選擇業務代理]
查詢 agent_key → endpoint_url
    │
    ▼
轉發給業務代理 (如 MM-Agent)
    │
    ▼ [需要知識庫時]
業務代理調用 KA-Agent
    │
    ├── 傳遞 caller_agent_key = "-h0tjyh"
    │         (業務代理的 arangodb_key)
    │
    ▼
KA-Agent 授權檢索
    │
    ├── 根據 caller_agent_key 查詢 knowledge_bases
    ├── 比對 file_metadata.knowledge_base_id
    │
    ▼
HybridRAG 檢索與組織
    │
    ├── 向量檢索 (Qdrant)
    ├── 圖譜檢索 (ArangoDB)
    ├── 重排序與組裝
    │
    ▼
返回組織好的知識回覆
    │
    ▼
業務代理使用知識組裝回覆
    │
    ▼
AI-Box 返回最終回覆
```

### 3.2 API 調用示例

**Step 1: AI-Box 轉發給業務代理**

```python
# chat.py
agent_config = store.get_agent_config(agent_key="-h0tjyh")
mm_endpoint = agent_config.endpoint_url  # http://localhost:8003

# 轉發任務
response = httpx.post(mm_endpoint + "/chat/auto-execute", json={
    "instruction": "查詢料號庫存",
    "session_id": "..."
})
```

**Step 2: 業務代理調用 KA-Agent**

```python
# MM-Agent 內部
ka_request = {
    "query": "料號庫存查詢方式",
    "agent_id": "ka-agent",
    "user_id": "user_123",
    "metadata": {
        "caller_agent_key": "-h0tjyh",
        "caller_agent_id": "mm-agent"
    },
    "options": {
        "top_k": 5,
        "include_graph": True
    }
}

# KA-Agent 回覆
ka_response = {
    "success": True,
    "results": [
        {
            "content": "組織好的知識內容...",
            "source": "物料管理員專業知識.md",
            "score": 0.95
        }
    ],
    "total": 5,
    "query_time_ms": 120
}
```

---

## 4. KA-Agent 規範

### 4.1 核心職責

| 職責 | 說明 | 狀態 |
|------|------|------|
| **Knowledge Retrieval** | 統一知識檢索入口 | ✅ |
| **Authorization** | 根據 caller_agent_key 授權檢索 | ✅ |
| **HybridRAG** | 向量 + 圖譜混合檢索 | ✅ |
| **Security & Audit** | 安全審計、權限驗證 | ✅ |
| **Provenance** | 來源追溯、可信度提示 | ✅ |

### 4.2 接口規範

**接口**: `/api/v1/ka-agent/knowledge.query`

**請求格式**:
```python
class KnowledgeQueryRequest(BaseModel):
    request_id: str
    query: str
    agent_id: str  # KA-Agent 的 ID (固定為 "ka-agent")
    user_id: str
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # 可包含 caller_agent_key
    options: Optional[Dict[str, Any]] = None
```

**關鍵字段**:
| 字段 | 必填 | 說明 |
|------|------|------|
| `metadata.caller_agent_key` | 建議 | 呼叫者的 arangodb_key (如 "-h0tjyh") |
| `metadata.caller_agent_id` | 可選 | 呼叫者的 agent_id (如 "mm-agent") |
| `options.top_k` | 可選 | 返回結果數量 (預設 10) |
| `options.include_graph` | 可選 | 是否包含圖譜檢索 (預設 True) |

### 4.3 授權機制

KA-Agent 根據 `caller_agent_key` 進行動態授權：

```python
def authorize(caller_agent_key: str) -> List[str]:
    """
    根據 caller_agent_key 獲取授權的 KB IDs
    
    優先級:
    1. agent_display_configs.knowledge_bases
    2. kb_auth_service (fallback)
    """
    # 查詢邏輯...
    return authorized_kb_ids
```

---

## 5. 授權服務

### 5.1 服務位置

| 服務 | 位置 | 功能 |
|------|------|------|
| `kb_auth_service.py` | `services/api/services/` | 即時 AQL 查詢 |
| `kb_agent_authorization` | ArangoDB Collection | 預計算 Materialized Cache |
| `agent_ka_view` | ArangoDB View | 全文檢索/備份核對 |

### 5.2 使用範例

```python
from services.api.services.kb_auth_service import get_kb_auth_service

svc = get_kb_auth_service()

# 根據 agent_key 查詢授權的 KB
kb_ids = svc.get_knowledge_bases(agent_key="-h0tjyh")

# 根據 agent_key 查詢授權的檔案
files = svc.get_authorized_files(agent_key="-h0tjyh")

# 檢查檔案訪問權限
has_access = svc.check_file_access(agent_key="-h0tjyh", file_id="xxx")
```

---

## 6. 權限檢查點

| 檢查點 | 位置 | 說明 |
|--------|------|------|
| 1 | AI-Box Chat API | 驗證 user 權限，選擇合適的代理 |
| 2 | 業務代理 | 處理業務邏輯，判斷是否需要知識 |
| 3 | KA-Agent | 根據 caller_agent_key 驗證知識庫權限 |
| 4 | HybridRAG | 只檢索授權的檔案 |

---

## 7. 異常處理

### 7.1 知識庫不可用

當知識庫服務不可用時：
1. 記錄錯誤日誌
2. 返回友好提示：“目前無法訪問知識庫，請稍後再試”
3. 不 fallback 到網絡搜索（除非明確需要）

### 7.2 知識庫為空

當用戶詢問知識庫內容但知識庫為空時：
1. 返回引導提示：如 “知識庫中尚未有任何文件，請先上傳文件”
2. 不返回錯誤

### 7.3 未授權訪問

當 caller_agent_key 沒有知識庫權限時：
1. 返回空結果（安全考量，不暴露知識庫存在）
2. 記錄審計日誌

---

## 8. 實現狀態

| 功能 | 位置 | 狀態 |
|------|------|------|
| Agent list 使用 arangodb_key | `useAgentDisplayConfig.ts` | ✅ |
| 後端 get_agent_config 修復 | `agent_display_config_store_service.py` | ✅ |
| Chat API 調用修正 | `chat.py` | ✅ |
| KB Auth Service | `kb_auth_service.py` | ✅ |
| KA-Agent 整合 | `ka_agent_mcp.py` | ✅ |
| ArangoDB Collection | `kb_agent_authorization` | ✅ |
| ArangoDB View | `agent_ka_view` | ✅ |

---

## 9. 測試場景

### 9.1 MM-Agent 知識庫查詢

**場景**: 用戶選擇「經寶物料管理代理」，詢問物料管理相關問題

**預期結果**:
- 只返回 5 份授權的知識文件
- 根據 `knowledge_base_id = root_Material_Management_1770989092` 過濾

**授權文件**:
1. 物料管理員職能與標準作業規範手冊.md
2. 19.原物料管理作業程序_v.1.0_PDF.pdf
3. 物料管理員專業知識.md
4. 鼎捷TIPTOP ERP全套操作参考手册-赫非域.pdf
5. MM-Agent-skills.md

---

## 10. 附錄

### 10.1 相關文件

- `api/routers/chat.py` - Chat API
- `api/routers/ka_agent_mcp.py` - KA-Agent MCP 接口
- `services/api/services/kb_auth_service.py` - 授權服務
- `services/api/services/agent_display_config_store_service.py` - Agent 配置服務
- `agents/builtin/ka_agent/agent.py` - KA-Agent 實現

### 10.2 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `ARANGODB_HOST` | ArangoDB 地址 | localhost:8529 |
| `QDRANT_HOST` | Qdrant 地址 | localhost:6333 |
| `SEAWEEDFS_HOST` | SeaweedFS 地址 | localhost:8333 |

---

*本文檔為 AI-Box v3.0 知識庫與 KA-Agent 整合的核心規範*
