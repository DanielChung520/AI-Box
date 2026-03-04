# MM-Agent Intent RAG 測試報告 (v2)

**測試日期**: 2026-02-23
**訓練案例數**: 177 個
**Intent RAG**: Qdrant Collection `mm_agent_intents`

---

## 測試結果摘要

| 項目 | 數值 |
|------|------|
| 測試案例數 | 10 |
| 正確數 | 6 |
| **正確率** | **60.0%** |
| 平均耗時 | 10,137 ms |

---

## 詳細測試結果

| # | 輸入 | 預期意圖 | 實際意圖 | 耗時(ms) | 結果 |
|---|------|----------|----------|----------|------|
| 1 | 公司的採購流程是什麼？ | KNOWLEDGE_QUERY | KNOWLEDGE_QUERY | 19,994 | ✅ |
| 2 | 查詢某個料號的庫存 | SIMPLE_QUERY | SIMPLE_QUERY | 6,572 | ✅ |
| 3 | 比較不同時間段的採購金額 | COMPLEX_TASK | COMPLEX_TASK | 6,141 | ✅ |
| 4 | 查詢庫存 | CLARIFICATION | CLARIFICATION | 9,764 | ✅ |
| 5 | 你好 | GREETING | CLARIFICATION | 11,580 | ❌ |
| 6 | 謝謝 | THANKS | THANKS | 9,496 | ✅ |
| 7 | 取消 | CANCEL | CANCEL | 8,776 | ✅ |
| 8 | 匯出 | EXPORT | CLARIFICATION | 9,965 | ❌ |
| 9 | 歷史記錄 | HISTORY | SIMPLE_QUERY | 9,289 | ❌ |
| 10 | 確認 | CONFIRM | CLARIFICATION | 9,791 | ❌ |

---

## 錯誤分析

### 1. GREETING 誤判為 CLARIFICATION
- **輸入**: "你好"
- **預期**: GREETING
- **實際**: CLARIFICATION
- **原因**: "你好" 可能是輸入開頭，RAG 匹配到了澄清需求

### 2. EXPORT 誤判為 CLARIFICATION
- **輸入**: "匯出"
- **預期**: EXPORT
- **實際**: CLARIFICATION
- **原因**: 單字輸入可能被識別為不完整語句

### 3. HISTORY 誤判為 SIMPLE_QUERY
- **輸入**: "歷史記錄"
- **預期**: HISTORY
- **實際**: SIMPLE_QUERY
- **原因**: 訓練案例中 HISTORY 數量相對較少

### 4. CONFIRM 誤判為 CLARIFICATION
- **輸入**: "確認"
- **預期**: CONFIRM
- **實際**: CLARIFICATION
- **原因**: 單字輸入可能被識別為不完整語句

---

## 改進建議

### 1. 增加 Layer 1 (GAI) 訓練案例
- GREETING, THANKS, CANCEL, EXPORT, HISTORY, CONFIRM 需要更多訓練案例
- 特別是短語/單字的表達方式

### 2. 調整 RAG 檢索策略
- 考慮為 Layer 1 意圖設置更高的權重
- 針對短語輸入優化匹配邏輯

### 3. 後處理規則
- 針對明確的單字意圖（如"你好"、"謝謝"、"取消"）添加規則優先級

---

## 對比之前測試

| 版本 | 訓練案例數 | 正確率 |
|------|-----------|--------|
| v1 | 106 | ~55% |
| v2 | 177 | 60% |

**改善**: +5%

---

## 結論

Intent RAG 訓練案例已從 106 增加到 177，正確率從 ~55% 提升到 60%。主要錯誤集中在 Layer 1 的 GAI 意圖（短語輸入），建議後續優化這部分案例。
