# ChromaDB 到 Qdrant 遷移問題報告

**創建日期**：2026-01-30
**發現日期**：2026-01-30
**狀態**：⚠️ 遷移未完成
**優先級**：高

---

## 1. 問題概述

在嘗試啟動 Data-Agent 服務時，發現 ChromaDB 尚未完全遷移到 Qdrant。雖然 `database/qdrant/` 目錄已存在，但部分組件仍然直接依賴 ChromaDB。

---

## 2. 影響範圍

### 2.1 受影響的組件

| 組件 | 文件路徑 | 依賴狀態 |
|------|---------|---------|
| Memory Manager | `/home/daniel/ai-box/agents/infra/memory/manager.py` | 直接導入 ChromaDBClient |
| Task Analyzer RAG Service | `/home/daniel/ai-box/agents/task_analyzer/rag_service.py` | 已改用 QdrantClient ✅ |
| System Agent Registry | `/home/daniel/ai-box/services/api/services/system_agent_registry_store_service.py` | 使用 ArangoDB ✅ |

### 2.2 遷移進度

| 組件 | 目標資料庫 | 狀態 |
|------|----------|------|
| Agent Memory（長期記憶） | ChromaDB → Qdrant | ⚠️ 部分遷移 |
| System Agent Registry | ArangoDB | ✅ 已完成 |
| Knowledge Graph | ArangoDB | ✅ 已完成 |

---

## 3. 具體問題分析

### 3.1 Memory Manager 硬性依賴 ChromaDB

**問題位置**：`agents/infra/memory/manager.py:22`

```python
# 硬性導入（失敗時會導致整個模組無法載入）
from database.chromadb.client import ChromaDBClient
```

**問題影響**：
- 當 `chromadb` 模組未安裝時，整個 `agents.infra.memory` 模組導入失敗
- Data-Agent 啟動時需要導入 `agents.task_analyzer`，而它會間接導入 `agents.infra.memory`
- 即使 MemoryManager 不需要 ChromaDB 功能，模組導入仍然會失敗

**目前臨時解決方案**：
將 ChromaDB 導入改為可選導入：

```python
CHROMADB_AVAILABLE = False

try:
    from database.chromadb.client import ChromaDBClient
    CHROMADB_AVAILABLE = True
except ImportError:
    ChromaDBClient = None
    logging.warning("ChromaDB not available, long-term memory will be disabled")
```

### 3.2 ChromaDB 模組檔案仍存在

| 檔案路徑 | 狀態 |
|---------|------|
| `/home/daniel/ai-box/database/chromadb/__init__.py` | 存在 |
| `/home/daniel/ai-box/database/chromadb/client.py` | 存在 |

這些檔案仍然包含實作代碼，但 ChromaDB 客戶端套件可能未安裝。

### 3.3 依賴清單未更新

`requirements.txt` 中仍然包含 `chromadb>=0.4.0`，但 Qdrant 對應的依賴為：

```bash
qdrant-client>=1.0.0
```

---

## 4. 遷移建議

### 4.1 Memory Manager 遷移步驟

1. **添加 Qdrant 支援**：
   - 在 `MemoryManager` 中添加 `qdrant_client` 參數
   - 將長期記憶功能從 ChromaDB 遷移到 Qdrant
   - 保留 ChromaDB 接口作為過渡期相容

2. **更新方法簽名**：
   ```python
   def __init__(
       self,
       redis_client: Optional[Any] = None,
       qdrant_client: Optional[Any] = None,
       chromadb_client: Optional[Any] = None,  # 保留過渡期支援
       short_term_ttl: int = 3600,
   ):
   ```

3. **實作 Qdrant 版本的長期記憶方法**：
   - `_store_long_term_qdrant()`
   - `_retrieve_long_term_qdrant()`

### 4.2 清理 ChromaDB 相關代碼

1. **保留選項**：
   - 將 ChromaDB 代碼移到 `database/chromadb/deprecated/`
   - 添加棄用警告

2. **完全移除**（建議）：
   - 刪除 `database/chromadb/` 目錄
   - 更新所有引用 ChromaDB 的代碼

### 4.3 更新依賴清單

1. 從 `requirements.txt` 中移除 `chromadb>=0.4.0`
2. 添加 `qdrant-client>=1.0.0`

---

## 5. 測試驗證

### 5.1 驗證點

- [ ] Data-Agent 可以正常啟動（不依賴 ChromaDB）
- [ ] MemoryManager 可以使用 Qdrant 存儲長期記憶
- [ ] 現有的 ChromaDB 數據可以遷移到 Qdrant（如有）
- [ ] 所有 Agent 的長期記憶功能正常運作

### 5.2 遷移檢查清單

- [ ] MemoryManager 支援 Qdrant
- [ ] 更新所有使用 ChromaDB 的組件
- [ ] 刪除或棄用 ChromaDB 相關代碼
- [ ] 更新 requirements.txt
- [ ] 更新文檔
- [ ] 完成測試

---

## 6. 臨時解決方案

目前為了讓 Data-Agent 能夠啟動，已經將 `agents/infra/memory/manager.py` 中的 ChromaDB 導入改為可選導入。這使得：

- 即使沒有 ChromaDB 模組，MemoryManager 仍然可以初始化
- 長期記憶功能會被禁用，但短期記憶（Redis 或記憶體）仍然可以運作
- Data-Agent 可以正常啟動，不受 ChromaDB 影響

**注意**：這只是臨時解決方案，完整的遷移仍需按照 §4 的步驟進行。

---

## 7. 相關文檔

- [存儲架構說明](./存儲架構.md)
- [SeaweedFS雙服務架構說明](./SeaweedFS双服务架构说明.md)
- [Qdrant 客戶端實作](/home/daniel/ai-box/database/qdrant/client.py)

---

## 8. 更新日誌

| 日期 | 更新內容 |
|------|---------|
| 2026-01-30 | 初始報告，記錄 ChromaDB 遷移未完成的問題 |
