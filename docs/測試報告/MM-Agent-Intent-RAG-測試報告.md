# MM-Agent Intent RAG 測試報告

**測試時間**: 2026-02-23 01:54:00
**測試數量**: 38
**正確數量**: 28
**準確率**: 73.7%
**總耗時**: 237.9s
**平均耗時**: 6261ms

---

## 測試環境

| 項目 | 說明 |
|------|------|
| 測試組件 | SemanticTranslatorAgent |
| Intent RAG | 啟用 (use_intent_rag=True) |
| 規則引擎 | 啟用 (use_rules_engine=True) |
| 模型 | gpt-oss:120b (Ollama) |
| Qdrant Collection | mm_agent_intents |

---

## 按類別統計

| 類別 | 總數 | 正確 | 準確率 |
|------|------|------|--------|
| SIMPLE_QUERY | 17 | 16 | 94.1% |
| CLARIFICATION | 7 | 3 | 42.9% |
| COMPLEX_TASK | 7 | 2 | 28.6% |
| KNOWLEDGE_QUERY | 7 | 7 | 100.0% |

---

## 失敗項目

| ID | 輸入 | 預期 | 實際 | 耗時 |
|---|------|------|------|------|
| 12 | 那個料號的品名 | CLARIFICATION | SIMPLE_QUERY | 5821ms |
| 13 | 最近採購的 | CLARIFICATION | SIMPLE_QUERY | 13016ms |
| 15 | 比較近三個月採購金額 | COMPLEX_TASK | CLARIFICATION | 7489ms |
| 16 | 如何建立採購單 | COMPLEX_TASK | KNOWLEDGE_QUERY | 4561ms |
| 18 | 料號 10-0001 的採購與庫存總覽 | COMPLEX_TASK | SIMPLE_QUERY | 0ms |
| 19 | 本月採購單未交貨明細 | COMPLEX_TASK | CLARIFICATION | 8189ms |
| 20 | 成品倉與原料倉庫存對比 | COMPLEX_TASK | CLARIFICATION | 10348ms |
| 32 | 查詢某來源單號的交易 | CLARIFICATION | SIMPLE_QUERY | 11899ms |
| 35 | 客戶 D003 的訂單 | SIMPLE_QUERY | QUERY_CUSTOMER | 10025ms |
| 48 | W03 | CLARIFICATION | SIMPLE_QUERY | 8730ms |

---

## 詳細結果

| ID | 輸入 | 預期 | 實際 | ✅ | 耗時 |
|---|------|------|------|---|------|
| 01 | 查詢 W03 倉庫的庫存 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 1ms |
| 02 | 料號 10-0001 的品名和規格 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 14078ms |
| 03 | W01 倉有多少庫存 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 1ms |
| 04 | 查詢供應商 VND001 的採購單 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 8329ms |
| 05 | 2024 年有多少筆採購進貨 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 7055ms |
| 06 | 料號 10-0001 的庫存信息 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 0ms |
| 07 | 查詢所有料件的品名 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 5702ms |
| 08 | 查詢訂單 SO-2024010001 的明細 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 8048ms |
| 09 | 查詢料號 10-0001 的單價 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 0ms |
| 10 | 各倉庫的總庫存量 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 5632ms |
| 11 | 查一下庫存 | CLARIFICATION | CLARIFICATION | ✅ | 8659ms |
| 12 | 那個料號的品名 | CLARIFICATION | SIMPLE_QUERY | ❌ | 5821ms |
| 13 | 最近採購的 | CLARIFICATION | SIMPLE_QUERY | ❌ | 13016ms |
| 14 | ABC 庫存分類分析 | COMPLEX_TASK | COMPLEX_TASK | ✅ | 8044ms |
| 15 | 比較近三個月採購金額 | COMPLEX_TASK | CLARIFICATION | ❌ | 7489ms |
| 16 | 如何建立採購單 | COMPLEX_TASK | KNOWLEDGE_QUERY | ❌ | 4561ms |
| 17 | 各倉庫庫存金額排行 | COMPLEX_TASK | COMPLEX_TASK | ✅ | 7545ms |
| 18 | 料號 10-0001 的採購與庫存總覽 | COMPLEX_TASK | SIMPLE_QUERY | ❌ | 0ms |
| 19 | 本月採購單未交貨明細 | COMPLEX_TASK | CLARIFICATION | ❌ | 8189ms |
| 20 | 成品倉與原料倉庫存對比 | COMPLEX_TASK | CLARIFICATION | ❌ | 10348ms |
| 21 | 如何做好 ABC 庫存管理 | KNOWLEDGE_QUERY | KNOWLEDGE_QUERY | ✅ | 5628ms |
| 22 | ERP 收料操作步驟 | KNOWLEDGE_QUERY | KNOWLEDGE_QUERY | ✅ | 6056ms |
| 23 | 採購單審核流程是什麼 | KNOWLEDGE_QUERY | KNOWLEDGE_QUERY | ✅ | 5235ms |
| 24 | 安全庫存怎麼設定 | KNOWLEDGE_QUERY | KNOWLEDGE_QUERY | ✅ | 4935ms |
| 25 | 什麼是 MRP | KNOWLEDGE_QUERY | KNOWLEDGE_QUERY | ✅ | 3977ms |
| 26 | 公司規定採購單超過多少要副總簽核 | KNOWLEDGE_QUERY | KNOWLEDGE_QUERY | ✅ | 5572ms |
| 27 | 庫存周轉率怎麼算 | KNOWLEDGE_QUERY | KNOWLEDGE_QUERY | ✅ | 5220ms |
| 28 | 查詢 W03 倉庫的庫存，並匯出 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 0ms |
| 29 | 10-0001 品名是什麼 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 5488ms |
| 30 | 有沒有料號 10-0001 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 5745ms |
| 31 | 列出所有成品 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 6729ms |
| 32 | 查詢某來源單號的交易 | CLARIFICATION | SIMPLE_QUERY | ❌ | 11899ms |
| 33 | 最近 10 筆採購單 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 6755ms |
| 34 | 各供應商採購筆數 | SIMPLE_QUERY | SIMPLE_QUERY | ✅ | 9251ms |
| 35 | 客戶 D003 的訂單 | SIMPLE_QUERY | QUERY_CUSTOMER | ❌ | 10025ms |
| 48 | W03 | CLARIFICATION | SIMPLE_QUERY | ❌ | 8730ms |
| 49 | 查詢 | CLARIFICATION | CLARIFICATION | ✅ | 7717ms |
| 50 | 幫我 | CLARIFICATION | CLARIFICATION | ✅ | 6428ms |

---

## 問題分析

### 1. COMPLEX_TASK 誤判率高 (28.6%)

**問題**: 包含比較、總覽等關鍵詞的輸入被誤判為 CLARIFICATION 或 SIMPLE_QUERY

**原因**:
- RAG 回傳的 few-shot examples 不夠精確
- LLM 判斷時優先匹配到簡單查詢規則

**案例**:
- "比較近三個月採購金額" → CLARIFICATION (應為 COMPLEX_TASK)
- "本月採購單未交貨明細" → CLARIFICATION (應為 COMPLEX_TASK)
- "成品倉與原料倉庫存對比" → CLARIFICATION (應為 COMPLEX_TASK)

### 2. CLARIFICATION 觸發不足 (42.9%)

**問題**: 代詞指代、不完整輸入未被識別為需要澄清

**案例**:
- "那個料號的品名" → SIMPLE_QUERY (應為 CLARIFICATION)
- "最近採購的" → SIMPLE_QUERY (應為 CLARIFICATION)
- "W03" → SIMPLE_QUERY (應為 CLARIFICATION)

### 3. 規則引擎優先順序問題

**問題**: `use_rules_engine=True` 時，正則匹配優先於 RAG 判斷

**建議**:
- 調整規則優先順序
- 增加 CLARIFICATION 規則
- 增加 COMPLEX_TASK 關鍵詞規則

---

## 改進建議

1. **增加 Intent RAG 訓練數據**
   - 添加更多 COMPLEX_TASK 案例到 `mm_agent_intents.json`
   - 添加更多 CLARIFICATION 案例

2. **調整規則引擎**
   - 增加 CLARIFICATION 關鍵詞規則
   - 增加 COMPLEX_TASK 關鍵詞規則

3. **修復 JSON 解析問題**
   - LLM 返回 `knowledge_source_type: "unknow..."` 被截斷
   - 需要修復 fallback 邏輯

---

*報告生成時間: 2026-02-23*
