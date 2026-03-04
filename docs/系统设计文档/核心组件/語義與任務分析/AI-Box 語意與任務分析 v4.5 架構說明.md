# AI-Box 語意與任務分析 v4.5 架構說明

**代碼功能說明**: AI-Box 語意與任務分析系統架構說明（v4.5 - Intent RAG 完整版）
**創建日期**: 2026-02-23
**創建人**: Daniel Chung
**最後修改日期**: 2026-02-23
**版本**: v4.5

---

## 📋 文檔概述

本文檔整合所有語意與任務分析的設計與實現，詳細記錄 Intent RAG 架構，避免日後維護時遺忘關鍵細節。

### 版本歷史

| 版本 | 日期 | 說明 |
|------|------|------|
| v4.0 | 2025-xx-xx | 初始版本 |
| v4.1 | 2025-xx-xx | 重構版本 |
| v4.2 | 2026-01-xx | 新增 Task Analyzer |
| v4.3 | 2026-02-09 | 兩層意圖分類架構 |
| v4.4 | 2026-02-20 | 澄清端點解析，整合實現狀態 |
| v4.5 | 2026-02-23 | 新增 Intent RAG 完整架構與維護流程 |

---

## 🏗️ 系統架構

### 整體流程圖

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           用戶輸入 (AI-Box Frontend)                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    第一層：AI-Box API Router (chat.py)                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ GAI Intent Classification (classify_gai_intent)                    │   │
│  │  - GREETING, THANKS, COMPLAIN, CANCEL, CONTINUE, MODIFY             │   │
│  │  - HISTORY, EXPORT, CONFIRM, FEEDBACK, CLARIFICATION, BUSINESS     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                     │
│              ┌───────────────────────┼───────────────────────┐             │
│              ▼                       ▼                       ▼             │
│       GREETING/etc.          CLARIFICATION            BUSINESS             │
│       (直接回覆)              (請求澄清)              (轉發 BPA)          │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼ (當 GAIIntent = BUSINESS)
┌─────────────────────────────────────────────────────────────────────────────┐
│                    第二層：MM-Agent (BPA) - Port 8003                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ BPA Intent Classification (intent_endpoint.py + Intent RAG)         │   │
│  │  - KNOWLEDGE_QUERY → KA-Agent (8000)                                │   │
│  │  - SIMPLE_QUERY → Data-Agent (8004)                                 │   │
│  │  - COMPLEX_TASK → ReAct Planner + RQ Worker                         │   │
│  │  - CLARIFICATION → 返回澄清                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                ┌───────────────────────┼───────────────────────┐
                ▼                       ▼                       ▼
          KA-Agent              Data-Agent              RQ Worker
          (8000)                (8004)                  (異步)
```

---

## 🔄 兩層意圖分類架構

### 第一層：AI-Box GAI 前端意圖

**職責**：在 AI-Box API 層直接處理對話管理相關意圖

**代碼位置**：`api/routers/chat.py:33-291`

```python
class GAIIntentType(str, Enum):
    GREETING = "GREETING"        # 問候/打招呼
    CLARIFICATION = "CLARIFICATION"  # 需要澄清
    CANCEL = "CANCEL"            # 取消任務
    CONTINUE = "CONTINUE"        # 繼續執行
    MODIFY = "MODIFY"            # 重新處理
    HISTORY = "HISTORY"          # 顯示歷史
    EXPORT = "EXPORT"            # 導出結果
    CONFIRM = "CONFIRM"          # 確認回覆
    THANKS = "THANKS"            # 感謝回覆
    COMPLAIN = "COMPLAIN"        # 道歉處理
    FEEDBACK = "FEEDBACK"        # 記錄反饋
    BUSINESS = "BUSINESS"         # 業務請求（轉發 BPA）
```

**實現狀態**：✅ 完整實現

| 意圖 | 狀態 | 說明 |
|------|------|------|
| GREETING | ✅ 已實現 | 問候回覆 |
| THANKS | ✅ 已實現 | 感謝回覆 |
| COMPLAIN | ✅ 已實現 | 道歉處理 |
| CANCEL | ✅ 已實現 | 終止任務 |
| CONTINUE | ✅ 已實現 | 繼續執行 |
| MODIFY | ✅ 已實現 | 重新處理 |
| HISTORY | ✅ 已實現 | 顯示歷史 |
| EXPORT | ✅ 已實現 | 導出結果 |
| CONFIRM | ✅ 已實現 | 請求確認 |
| FEEDBACK | ✅ 已實現 | 記錄反饋 |
| CLARIFICATION | ✅ 已實現 | 請求澄清 |
| BUSINESS | ✅ 已實現 | 轉發 BPA |

### 第二層：MM-Agent (BPA) 業務意圖

**職責**：在 MM-Agent 服務中進行業務意圖分類

**代碼位置**：`datalake-system/mm_agent/intent_endpoint.py`

```python
class BPAIntentType(str, Enum):
    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"      # 業務知識問題
    SIMPLE_QUERY = "SIMPLE_QUERY"            # 簡單數據查詢
    COMPLEX_TASK = "COMPLEX_TASK"            # 複雜任務/操作指引
    CLARIFICATION = "CLARIFICATION"          # 需要澄清
    CONTINUE_WORKFLOW = "CONTINUE_WORKFLOW"  # 繼續執行工作流
```

**實現狀態**：✅ 完整實現

| 意圖 | 下游處理 | 說明 |
|------|----------|------|
| KNOWLEDGE_QUERY | KA-Agent (8000) | 知識庫查詢 |
| SIMPLE_QUERY | Data-Agent (8004) | SQL 查詢 |
| COMPLEX_TASK | ReAct Planner | 複雜任務 |
| CLARIFICATION | 返回澄清 | 需要更多資訊 |
| CONTINUE_WORKFLOW | 執行下一步 | 繼續工作流 |

---

## 🔌 Intent RAG 架構（⚠️ 重要）

### 架構概述

Intent RAG 是用於**意圖分類增強**的向量檢索系統，幫助 LLM 正確識別用戶意圖。

```
用戶查詢 → Intent RAG (Qdrant) → Few-shot Examples → LLM → Intent Classification
```

### 為什麼需要 Intent RAG？

1. **意圖分類困難**：同一句話可能有多種理解方式，LLM 需要參考範例來正確判斷
2. **規則引擎局限**：正則表達式無法處理語義變化
3. **統一管理**：所有意圖分類邏輯集中管理於 JSON + 向量庫
4. **可持續優化**：通過增加訓練案例持續提升準確率

### 數據流向

```
┌─────────────────────────┐
│  mm_agent_intents.json  │  ← 意圖場景庫（源頭）
└───────────┬─────────────┘
            │ sync_intent.py
            ▼ (生成向量)
┌─────────────────────────┐
│   Qdrant Collection    │  ← 向量存儲
│   mm_agent_intents     │  ← 177 個場景
└───────────┬─────────────┘
            │
            ▼ (查詢)
┌─────────────────────────┐
│ IntentRAGClient        │  ← 檢索客戶端
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ SemanticTranslator     │  ← 增強 LLM 判斷
└─────────────────────────┘
```

### 關鍵文件位置

| 功能 | 文件位置 | 說明 |
|------|----------|------|
| **意圖場景庫（源頭）** | `data/intents/mm_agent_intents.json` | 177 個場景 |
| **同步腳本** | `data/intents/sync_intent.py` | 同步到 Qdrant |
| **檢索客戶端** | `datalake-system/mm_agent/intent_rag_client.py` | 查詢接口 |
| **使用方** | `datalake-system/mm_agent/semantic_translator.py` | Line 38-40 |
| **Qdrant Collection** | `mm_agent_intents` | 向量存儲 |

### Intent RAG 配置位置: `datalake-system/mm_agent/semantic_translator.py`

```python
# Intent RAG 配置
INTENT_RAG_ENABLED = True  # 是否啟用 Intent RAG
INTENT_RAG_TOP_K = 3        # 檢索的範例數量
INTENT_RAG_MIN_SCORE = 0.3 # 最小相似度閾值
```

### 使用方式

```python
from mm_agent.intent_rag_client import get_intent_rag_client

client = get_client()
# 獲取 few-shot examples
examples = client.get_few_shot_examples(
    query="請你檢查你的知識庫有那些！",
    top_k=3
)
# examples 返回格式:
# [{'user_input': '...', 'intent': 'KNOWLEDGE_QUERY', 'description': '...'}]
```

---

## ⚠️ Intent RAG 維護流程（必讀）

### 添加新意圖場景的完整流程

當需要新增意圖場景時，**必須**執行以下步驟：

#### Step 1: 修改源頭 JSON

**文件**: `data/intents/mm_agent_intents.json`

```bash
# 1. 打開文件添加新場景
code data/intents/mm_agent_intents.json

# 2. 在適當位置添加新場景（遵循現有格式）
{
  "id": "K21",
  "category": "知識查詢",
  "layer": 2,
  "intent": "KNOWLEDGE_QUERY",
  "sub_type": "knowledge_base",
  "user_input": "你的新查詢表達",
  "intent_description": "場景描述"
}

# 3. 更新統計數據
"statistics": {
  "total_scenarios": 177,  # 更新總數
  "by_intent": {
    "KNOWLEDGE_QUERY": 30,  # 更新計數
    ...
  }
}
```

#### Step 2: 同步到 Qdrant（關鍵步驟）

```bash
cd /home/daniel/ai-box

# 方式一：強制重建（推薦，生產環境慎用）
source venv/bin/activate
python3 data/intents/sync_intent.py --rebuild

# 方式二：增量更新
python3 data/intents/sync_intent.py
```

**⚠️ 警告**：修改 `mm_agent_intents.json` 後**必須**執行 sync，否則：
- Qdrant 不會自動更新
- Intent RAG 檢索結果仍是舊數據
- 會浪費大量時間排查「為什麼改了沒生效」

#### Step 3: 重啟 MM-Agent

```bash
cd /home/daniel/ai-box/datalake-system
./scripts/mm_agent/stop.sh
./scripts/mm_agent/start.sh
```

### 驗證流程

添加新場景後，**必須**驗證：

```bash
# 1. 驗證 Qdrant 數據更新
cd /home/daniel/ai-box
source venv/bin/activate

python3 -c "
from database.qdrant.client import get_qdrant_client
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
query = '你的新查詢表達'
embedding = model.encode(query).tolist()

client = get_qdrant_client()
result = client.query_points(
    collection_name='mm_agent_intents',
    query=embedding,
    limit=3,
)

print('Query:', query)
for p in result.points:
    print(f'  {p.payload.get(\"user_input\")} -> {p.payload.get(\"intent\")}')
"

# 2. 驗證 SemanticTranslator
cd /home/daniel/ai-box/datalake-system
source venv/bin/activate

python3 -c "
import asyncio
from mm_agent.semantic_translator import SemanticTranslatorAgent

async def test():
    agent = SemanticTranslatorAgent(use_rules_engine=True)
    result = await agent.translate('你的新查詢表達')
    print('Intent:', result.intent)

asyncio.run(test())
"
```

---

## 🧪 測試結果與優化歷程

### 測試版本演進

| 版本 | 訓練案例數 | 正確率 | 說明 |
|------|-----------|--------|------|
| v1 | 106 | ~55% | 初始版本 |
| v2 | 177 | 60% | 增加訓練案例 |
| **v3** | **177** | **100%** | **修復代碼問題後** |

### v3 修復內容

#### 問題根因分析

測試中發現 Layer 1 的 GAI 意圖（GREETING, THANKS, CANCEL, EXPORT, HISTORY, CONFIRM）大量誤判為 CLARIFICATION。

**根本原因**：`semantic_translator.py` 中的 `INTENT_ENUM` 缺少 Layer 1 的 GAI 意圖。

- RAG 檢索正確（如 "你好" 檢索到 GREETING，score=1.0）
- 但 LLM 無法輸出這些意圖因為不在允許列表中
- LLM 只能從允許列表中選擇，最終輸出 CLARIFICATION

#### 修復方案

1. **新增 INTENT_ENUM** (`semantic_translator.py:46-60`)

```python
INTENT_ENUM = [
    # Layer 1: GAI 意圖（對話管理）
    "GREETING",  # 問候
    "THANKS",  # 感謝
    "CANCEL",  # 取消
    "HISTORY",  # 歷史記錄
    "EXPORT",  # 導出
    "CONFIRM",  # 確認
    # Layer 2: BPA 意圖（業務處理）
    "KNOWLEDGE_QUERY",  # 知識庫查詢
    "SIMPLE_QUERY",  # 簡單數據查詢
    "COMPLEX_TASK",  # 複雜任務
    "CLARIFICATION",  # 需要澄清
    "CONTINUE_WORKFLOW",  # 繼續工作流
]
```

2. **增強 Prompt** (`semantic_translator.py:340-351`)

```python
few_shot_section = f"""
【參考範例】（這些範例幫助你理解如何正確分類意圖）
{examples_text}
【關鍵規則】當參考範例與用戶輸入語義高度相似時，必須採用相同的意圖分類！
特別是：
 「你好」「嗨」「早安」→ GREETING
 「謝謝」「感謝」「多謝」→ THANKS
 「取消」「算了」「停止」→ CANCEL
 「匯出」「下載」「導出」→ EXPORT
 「歷史」「記錄」→ HISTORY
 「確認」「對嗎」→ CONFIRM
"""
```

### v3 測試結果（100% 正確率）

| # | 輸入 | 預期意圖 | 實際意圖 | 耗時(ms) | 結果 |
|---|------|----------|----------|----------|------|
| 1 | 公司的採購流程是什麼？ | KNOWLEDGE_QUERY | KNOWLEDGE_QUERY | 19,994 | ✅ |
| 2 | 查詢某個料號的庫存 | SIMPLE_QUERY | SIMPLE_QUERY | 6,572 | ✅ |
| 3 | 比較不同時間段的採購金額 | COMPLEX_TASK | COMPLEX_TASK | 6,141 | ✅ |
| 4 | 查詢庫存 | CLARIFICATION | CLARIFICATION | 9,764 | ✅ |
| 5 | 你好 | GREETING | GREETING | 11,580 | ✅ |
| 6 | 謝謝 | THANKS | THANKS | 9,496 | ✅ |
| 7 | 取消 | CANCEL | CANCEL | 8,776 | ✅ |
| 8 | 匯出 | EXPORT | EXPORT | 9,965 | ✅ |
| 9 | 歷史記錄 | HISTORY | HISTORY | 9,289 | ✅ |
| 10 | 確認 | CONFIRM | CONFIRM | 9,791 | ✅ |

---

## 📊 訓練案例統計

### 按意圖類型分布

| 意圖類型 | 數量 | 佔比 |
|---------|------|------|
| KNOWLEDGE_QUERY | ~30 | 17% |
| SIMPLE_QUERY | ~50 | 28% |
| COMPLEX_TASK | ~20 | 11% |
| CLARIFICATION | ~20 | 11% |
| GREETING | ~10 | 6% |
| THANKS | ~10 | 6% |
| CANCEL | ~10 | 6% |
| EXPORT | ~10 | 6% |
| HISTORY | ~10 | 6% |
| CONFIRM | ~7 | 4% |
| **總計** | **177** | **100%** |

### 設計原則（⚠️ 必讀）

1. **去數據化**：不包含具體料號、倉庫代碼、供應商代碼
   - ✅ 使用「某個料號」、「某個倉庫」
   - ❌ 禁止使用「10-0001」、「W01」、「VND001」

2. **語義優先**：聚焦「查詢」、「統計」、「比較」等意圖表達
   - ✅ 「查詢某個料號的庫存」
   - ❌ 「查詢料號 10-0001 的庫存」

3. **唯一性**：每個場景表達必須與其他場景有明顯區別

4. **可擴展**：預留空間給未來新增場景

---

## 📁 關鍵代碼位置

| 功能 | 文件位置 | 行號 |
|------|----------|------|
| GAIIntentType 定義 | `api/routers/chat.py` | 33-52 |
| classify_gai_intent() | `api/routers/chat.py` | 67-291 |
| should_forward_to_bpa() | `api/routers/chat.py` | 369-393 |
| Agent 解析邏輯 | `api/routers/chat.py` | 2243-2315 |
| MM-Agent 轉發 | `api/routers/chat.py` | 2371-2470 |
| BPAIntentType 定義 | `datalake-system/mm_agent/intent_endpoint.py` | - |
| Intent 分類端點 | `datalake-system/mm_agent/main.py` | - |
| **Intent RAG 配置** | `datalake-system/mm_agent/semantic_translator.py` | 38-40 |
| **INTENT_ENUM 定義** | `datalake-system/mm_agent/semantic_translator.py` | 46-60 |
| **Prompt 構建** | `datalake-system/mm_agent/semantic_translator.py` | 320-388 |
| **Intent RAG 客戶端** | `datalake-system/mm_agent/intent_rag_client.py` | - |
| **同步腳本** | `data/intents/sync_intent.py` | - |

---

## 🔌 Agent 端點解析

### Agent ID 映射

| 前端顯示名稱 | agent_id | _key (ArangoDB) | endpoint |
|-------------|----------|-----------------|----------|
| 經寶物料管理代理 | mm-agent | -h0tjyh | http://localhost:8003/api/v1/chat/auto-execute |

### 端點列表

| 服務 | 端點 | 用途 |
|------|------|------|
| MM-Agent | `/api/v1/chat/auto-execute` | 聊天執行 |
| MM-Agent | `/health` | 健康檢查 |
| MM-Agent | `/execute` | 任務執行 |
| KA-Agent | `/api/v1/knowledge/query` | 知識庫查詢 |
| KA-Agent | `/api/v1/ka/list` | 知識庫列表 |
| KA-Agent | `/api/v1/ka/stats` | 知識庫統計 |
| Data-Agent | `/execute` | 數據查詢 |

---

## 📊 問題排查清單

當遇到意圖分類問題時，按以下順序排查：

1. **檢查 Intent RAG**
   ```bash
   # 驗證 Qdrant 數據
   python3 data/intents/sync_intent.py --test "你的查詢"
   ```

2. **檢查 SemanticTranslator INTENT_ENUM**
   ```python
   # 確認 INTENT_ENUM 包含所有預期意圖
   from mm_agent.semantic_translator import SemanticTranslatorAgent
   print(SemanticTranslatorAgent.INTENT_ENUM)
   # 必須包含: GREETING, THANKS, CANCEL, HISTORY, EXPORT, CONFIRM
   ```

3. **檢查 SemanticTranslator**
   ```python
   # 直接測試翻譯器
   agent = SemanticTranslatorAgent(use_rules_engine=True)
   result = await agent.translate("你的查詢")
   print(result.intent)
   ```

4. **檢查 classify_intent**
   ```python
   # 測試端點
   result = await classify_intent("你的查詢")
   print(result.intent, result.is_list_files_query)
   ```

5. **檢查 MM-Agent 日誌**
   ```bash
   ./scripts/mm_agent/view_logs.sh
   ```

6. **檢查網絡連接**
   ```bash
   curl http://localhost:8003/health
   curl http://localhost:8000/health
   curl http://localhost:8004/health
   ```

---

## 📝 更新記錄

| 日期 | 版本 | 更新內容 | 更新人 |
|------|------|----------|--------|
| 2026-02-23 | v4.5 | 新增 Intent RAG 完整架構與維護流程、測試結果與優化歷程 | Daniel Chung |
| 2026-02-20 | v4.4 | 創建整合文檔，澄清端點解析，歸檔舊文檔 | Daniel Chung |
| 2026-02-09 | v4.3 | 兩層意圖分類架構 | Daniel Chung |

---

## ⚠️ 重要提醒（開發者必讀）

1. **修改 `mm_agent_intents.json` 後必須執行 sync**
   ```bash
   python3 data/intents/sync_intent.py --rebuild
   ```

2. **sync 後必須重啟 MM-Agent**
   ```bash
   cd datalake-system
   ./scripts/mm_agent/stop.sh && ./scripts/mm_agent/start.sh
   ```

3. **新增場景後必須驗證**
   - 使用測試腳本驗證 RAG 檢索正確
   - 使用 SemanticTranslator 驗證最終輸出正確

4. **不要直接修改 Qdrant，必須通過 JSON + sync 管理**
   - Qdrant 是向量存儲，應視為緩存
   - 源頭是 `mm_agent_intents.json`

5. **INTENT_ENUM 必須與訓練案例一致**
   - 如果 JSON 中有某個意圖類型，但 INTENT_ENUM 沒有，LLM 將無法輸出該意圖
   - 這是 v3 版本修復的核心問題

6. **Prompt 中的【關鍵規則】是增強手段**
   - 當 RAG 檢索結果與【關鍵規則】衝突時，【關鍵規則】優先
   - 這解決了短語輸入（如「你好」）被誤判的問題

---

**文檔版本**: v4.5
**最後更新**: 2026-02-23
**維護人**: Daniel Chung
