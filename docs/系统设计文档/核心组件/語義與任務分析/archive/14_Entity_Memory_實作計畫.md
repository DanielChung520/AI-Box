# Entity Memory 實作計畫

**文件編號**: AI-Box-PLAN-014  
**版本**: 1.0  
**創建日期**: 2026-02-04  
**狀態**: 草稿

---

## 1. 階段規劃總覽

### 1.1 實作階段

| 階段 | 名稱 | 預估天數 | 依賴 | 主要產出 |
|------|------|---------|------|---------|
| Phase 1 | 存儲層 | 1-2 天 | 無 | `entity_storage.py` |
| Phase 2 | 提取層 | 1-2 天 | Phase 1 | `entity_extractor.py` |
| Phase 3 | 檢索策略 | 1 天 | Phase 1 | `retrieval_strategy.py` |
| Phase 4 | 服務整合 | 1-2 天 | Phase 1, 2, 3 | `entity_memory_service.py` |

**總預估時間**: 4-7 天

### 1.2 里程碑

| 里程碑 | 預估完成時間 | 驗收標準 |
|--------|-------------|---------|
| M1: 存儲層完成 | Day 2 | Qdrant/ArangoDB 存儲正常 |
| M2: 提取層完成 | Day 4 | 實體提取正確 |
| M3: 檢索策略完成 | Day 5 | 多策略檢索正常 |
| M4: 服務整合完成 | Day 7 | 整合到 Chat API 正常 |

---

## 2. Phase 1: 存儲層

### 2.1 目錄結構

```
agents/services/entity_memory/
├── __init__.py
├── models.py
├── entity_storage.py
└── test_entity_storage.py
```

### 2.2 實作任務

**Task 1.1**: 創建數據模型 (`models.py`)
- EntityMemory, EntityRelation, SessionContext

**Task 1.2**: 創建存儲類 (`entity_storage.py`)
- store_entity(), get_entity(), search_entities()
- store_relation(), get_related_entities()
- store_session_context(), get_session_context()

**Task 1.3**: 創建種子數據腳本 (`scripts/seed_entity_memory.py`)

### 2.3 驗收標準

| 測試場景 | 預期結果 |
|---------|---------|
| 存儲實體 | 實體成功存入 Qdrant |
| 獲取實體 | 根據 ID 返回正確實體 |
| 搜索實體 | 返回相關實體列表 |
| 精確匹配 | 根據名稱找到實體 |

---

## 3. Phase 2: 提取層

### 3.1 目錄結構

```
agents/services/entity_memory/
├── entity_extractor.py
└── test_entity_extractor.py
```

### 3.2 實作任務

**Task 2.1**: 實體提取器 (`entity_extractor.py`)
- extract_from_text() - 從文本中提取實體
- detect_remember_intent() - 檢測「幫我記住」指示
- is_new_entity() - 判斷是否為新實體

**提取方法**:
1. 規則基礎提取 - 名詞短語識別
2. LLM 提取 - 使用 LLM 識別實體
3. 用戶指示提取 - 檢測「幫我記住」模式

### 3.3 驗收標準

| 測試場景 | 預期結果 |
|---------|---------|
| 提取系統實體 | 正確提取 AI-Box、mm-agent 等 |
| 提取新實體 | 正確識別未見過的名詞 |
| 識別「幫我記住」 | 正確提取用戶指定的實體 |

---

## 4. Phase 3: 檢索策略

### 4.1 目錄結構

```
agents/services/entity_memory/
├── retrieval_strategy.py
└── test_retrieval_strategy.py
```

### 4.2 實作任務

**Task 3.1**: 檢索策略類 (`retrieval_strategy.py`)
- search() - 統一檢索接口
- search_by_coreference() - 根據指代詞查找實體

**融合公式**:
```
final_score = 0.4 * vector_score + 0.4 * exact_score + 0.2 * freshness_score
```

### 4.3 驗收標準

| 測試場景 | 預期結果 |
|---------|---------|
| 精確匹配 | 根據名稱找到正確實體 |
| 向量搜索 | 返回語義相似的實體 |
| 混合融合 | 多策略結果正確融合排序 |

---

## 5. Phase 4: 服務整合

### 5.1 目錄結構

```
agents/services/entity_memory/
├── entity_memory_service.py
└── test_entity_memory_service.py
```

### 5.2 實作任務

**Task 4.1**: 統一服務類 (`entity_memory_service.py`)
- resolve_coreference() - 指代消解主接口
- extract_and_store() - 提取並存儲實體
- remember_entity() - 手動記住實體

**Task 4.2**: 整合到 Chat API (`api/routers/chat.py`)
- 導入 EntityMemoryService
- 在消息處理流程中添加指代消解
- 在消息處理流程中添加實體提取與學習

### 5.3 驗收標準

| 測試場景 | 預期結果 |
|---------|---------|
| 指代消解正常 | 「它」正確消解為實體 |
| 實體學習正常 | 新實體存入長期記憶 |
| 長期記憶持久化 | 重啟後實體仍在 |

---

## 6. 測試計畫

### 6.1 測試類型

| 測試類型 | 覆蓋範圍 | 工具 |
|---------|---------|------|
| 單元測試 | 各模組獨立功能 | pytest |
| 集成測試 | 模組間協作 | pytest + fixtures |
| E2E 測試 | 完整流程 | pytest + API calls |

### 6.2 風險識別

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| Qdrant 連接失敗 | 高 | 使用內存回退 |
| 實體提取不準確 | 中 | 使用 LLM 二次確認 |
| 指代消解錯誤 | 中 | 置信度閾值過濾 |

---

## 7. 代碼結構

```
agents/services/entity_memory/
├── __init__.py
├── models.py                    # 數據模型
├── entity_storage.py            # 存儲層 (Phase 1)
├── entity_extractor.py          # 提取層 (Phase 2)
├── retrieval_strategy.py        # 檢索策略 (Phase 3)
└── entity_memory_service.py     # 統一服務 (Phase 4)

scripts/
└── seed_entity_memory.py        # 種子數據腳本

tests/
├── unit/
├── integration/
└── e2e/
```

---

## 8. 參考文檔

- [Entity Memory 規格書](14_Entity_Memory_規格書.md)
- [CoreferenceResolver 現有實現](../../../../datalake-system/mm_agent/coreference_resolver.py)
- [AAM 系統設計](../AAM系统.md)

---

**文件結束**
