# 技術債文檔

## 概述

本文檔記錄 AI-Box 專案中的技術債，作為後續優化的參考依據。

---

## Data-Agent Schema-Driven Query 技術債

### 1. DA_IntentRAG 異步調用問題

**日期**: 2026-02-24

**狀態**: 🔴 待處理（短期方案已上線）

**問題描述**:

DA_IntentRAG 使用完全異步設計（async/await），但調用層（Parser.parse()）是同步設計，導致在 FastAPI 環境中無法直接調用。

**根本原因**:

```python
# parser.py - 同步方法
def parse(cls, nlq: str) -> Optional[ParsedIntent]:
    # 嘗試調用異步方法
    rag_result = await rag.match_intent(nlq)  # ❌ SyntaxError
```

**短期方案 (Solution A)**:

在 `da_intent_rag.py` 添加同步包裝方法 `match_intent_sync()`，使用 ThreadPoolExecutor 處理異步調用。

```python
def match_intent_sync(self, query: str) -> Optional[IntentMatchResult]:
    """同步版本的意圖匹配（短期方案）"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(loop.run_until_complete, self.match_intent(query))
            return future.result()
    else:
        return loop.run_until_complete(self.match_intent(query))
```

**長期方案 (Solution B)**:

將調用鏈全部改為 async：

```
FastAPI Router (async) 
    → Resolver.resolve() [async]
        → Parser.parse() [async]
            → DA_IntentRAG.match_intent() [async]
```

**影響範圍**:

| 檔案 | 修改內容 |
|------|---------|
| `parser.py` | `parse()` → `async parse()` |
| `resolver.py` | `_parse_nlq()`, `resolve()` → async |
| `tests/` | 測試需改為 async |

**優先級**: 中（功能已上線，可後續優化）

---

### 2. SQL 欄位名稱衝突

**日期**: 2026-02-24

**狀態**: ✅ 已修復

**問題描述**:

當查詢涉及多個 Mart 表時，SQL 生成會產生欄位名稱衝突。

**修復方案**:

在 `resolver.py` 中添加條件性表格前綴邏輯：

```python
needs_table_prefix = len(tables) > 1

# SELECT 子句
table_prefix = f"{binding.table}." if (needs_table_prefix and binding.table) else ""
expr = f"{table_prefix}{binding.column}"
```

**狀態**: ✅ 已完成，無需後續

---

### 3. MasterRAG 實體提取尚未完全整合

**日期**: 2026-02-24

**狀態**: 🔴 待處理

**問題描述**:

根據產品化要求，實體提取應使用 MasterRAG 語義搜索，而非正則表達式。但目前 Parser 中的參數提取（如料號、工單號）仍使用正則表達式。

**預期改動**:

將 `parser.py` 中的 PARAM_PATTERNS 替換為 MasterRAG 調用。

**優先級**: 低（當前正則表達式可正常工作）

---

## 備註

- 本文檔由 Sisyphus AI Agent 維護
- 更新頻率：發現新技術債時
- 審閱週期：每週
