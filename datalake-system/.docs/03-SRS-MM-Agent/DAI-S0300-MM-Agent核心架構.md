# DAI-S0300 MM-Agent 核心架構規格書

**文件編號**: DAI-S0300  
**版本**: 3.1  
**日期**: 2026-02-06  
**依據代碼**: `datalake-system/mm_agent/`

---

## 一、架構總覽

### 1.1 核心理念

```
職責清晰、層次分明、AI 發力、企業級精準
```

**設計原則**：
- 每一層只做一件事
- Schema 統一管理（解決零散問題）
- AI 專注理解，規則專注轉換
- 企業級精準：有歧義 → 回問用戶
- 模組化設計：可移植到 AI-Box 其他 Agent

---

### 1.2 架構圖

```
用戶輸入 (NLP)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  GenAI (Router)                                            │
│  職責：                                                    │
│  ├─ 意圖過濾（打錯字 / 打招呼 / 非相關）                    │
│  ├─ 任務路由（轉發到對應 BPA）                              │
│  └─ 簡單指代消解（this/that）                              │
│  技術：LLM（分類 + 指代）                                   │
└─────────────────────────────────────────────────────────────┘
              │
              │ 清洗後意圖
              ▼
┌─────────────────────────────────────────────────────────────┐
│  BPA (MM-Agent)                                           │
│  職責：                                                    │
│  ├─ 業務意圖分類（簡單查詢 / 複雜任務）                     │
│  ├─ 語義分析（what/when/how/where）                       │
│  ├─ 指代消解（「那個料號」→ RM05-008）                     │
│  ├─ 澄清處理（缺失字段 / 歧義表達）                        │
│  ├─ 簡單查詢 → 結構化需求 → Data-Agent                     │
│  └─ 複雜任務 → Todo 規劃 + 逐步執行                       │
│  技術：LLM（理解） + 規則（任務分類）                       │
└─────────────────────────────────────────────────────────────┘
              │
              │ QuerySpec
              ▼
┌─────────────────────────────────────────────────────────────┐
│  Data-Agent                                               │
│  職責：                                                    │
│  ├─ Schema Registry（真值來源，統一管理）                  │
│  ├─ Text-to-SQL（混合模式）                                │
│  │   ├─ 規則引擎：常見模式（料號查詢、庫存查詢）          │
│  │   └─ LLM：複雜查詢（自然語句、模糊需求）               │
│  ├─ DuckDB 查詢（SeaweedFS）                              │
│  └─ 結果驗證（欄位類型、數據範圍）                         │
│  技術：規則引擎 + LLM + DuckDB                             │
└─────────────────────────────────────────────────────────────┘
              │
              │ SQL 結果
              ▼
┌─────────────────────────────────────────────────────────────┐
│  GenAI (補全) - PoC 階段                                   │
│  職責：                                                    │
│  ├─ 結果格式化（表格、列表）                                │
│  └─ 簡單自然語言說明                                       │
│  技術：Prompt Template                                     │
└─────────────────────────────────────────────────────────────┘
```

---

### 1.3 職責對照表

| 層次 | 組件 | 輸入 | 輸出 | 技術 |
|------|------|------|------|------|
| L1 | GenAI (Router) | 用戶原始輸入 | 清洗後意圖 / 拒絕回覆 | LLM |
| L2 | BPA (MM-Agent) | 清洗後意圖 | 結構化需求 / Todo 列表 | LLM + 規則 |
| L3 | Data-Agent | 結構化需求 | SQL 執行結果 | 規則 + LLM |
| L4 | GenAI (補全) | SQL 結果 | 自然語言回覆 | Prompt |

---

## 二、組件詳細設計

### 2.1 GenAI (Router)

**職責**：
1. 意圖過濾（排除無關請求）
2. 簡單指代消解
3. 任務路由

**意圖類型**：

```python
class TaskType(Enum):
    GREETING = "greeting"        # 打招呼
    ERROR_INPUT = "error_input"  # 錯誤輸入
    QUERY = "query"             # 簡單查詢
    COMPLEX = "complex"          # 複雜任務
    OUT_OF_SCOPE = "out_of_scope"  # 非任務範圍
```

**處理邏輯**：

| 輸入類型 | 處理方式 |
|----------|----------|
| 打招呼 | 直接回覆問候語 |
| 錯誤輸入 | 要求重新輸入 |
| 非相關問題 |礼貌拒绝 |
| 簡單查詢 | 轉發 BPA |
| 複雜任務 | 轉發 BPA |

**Router Prompt**：

```
你是智能助手路由系統。

任務：分析用戶輸入，分類並過濾。

【分類規則】
1. 打招呼：「你好」「早安」「嗨」等
2. 錯誤輸入：乱码、无意义字符、过短
3. 非任務範圍：與庫存/採購/銷售無關的問題
4. 簡單查詢：單一數據需求（如「RM05-008 上月買進多少」）
5. 複雜任務：多步驟、多條件、分析需求

【輸出格式】
{
  "task_type": "query",
  "cleaned_input": "RM05-008 上月買進多少",
  "simple_reference": null,  // this/that 的指代
  "response": null,          // 直接回覆（如打招呼）
  "confidence": 0.95
}
```

---

### 2.2 BPA (MM-Agent)

**職責**：
1. 業務意圖分類
2. 語義分析
3. 指代消解（業務相關）
4. 澄清處理（缺失字段 / 歧義表達）
5. 簡單查詢 → 結構化需求
6. 複雜任務 → Todo 規劃

**意圖類型**：

```python
class QueryIntent(Enum):
    QUERY_STOCK = "QUERY_STOCK"           # 庫存查詢
    QUERY_PURCHASE = "QUERY_PURCHASE"     # 採購交易查詢
    QUERY_SALES = "QUERY_SALES"           # 銷售交易查詢
    ANALYZE_SHORTAGE = "ANALYZE_SHORTAGE"  # 缺料分析
    GENERATE_ORDER = "GENERATE_ORDER"     # 生成訂單
```

**QuerySpec 結構**：

```python
class QuerySpec(BaseModel):
    """結構化查詢需求"""

    # 意圖
    intent: QueryIntent

    # 參數
    material_id: Optional[str] = None        # 料號
    warehouse: Optional[str] = None           # 倉庫
    time_type: Optional[TimeType] = None      # 時間類型
    time_value: Optional[str] = None          # 時間值
    transaction_type: Optional[str] = None   # 交易類型
    material_category: Optional[str] = None   # 物料類別
    aggregation: Optional[str] = None         # 聚合函數
    order_by: Optional[str] = None            # 排序
    limit: int = 100

    # 置信度
    confidence: float = 1.0
    missing_fields: List[str] = []

    # 指代消解標記
    has_coreference: bool = False
    coreference_resolved: bool = False

    # 澄清處理
    clarification: Optional[Dict] = None
```

**Clarification 處理**：

```python
class ClarificationIssue(BaseModel):
    """澄清問題"""
    field: str                    # 字段名稱
    issue_type: str               # missing / ambiguous / invalid
    message: str                  # 問題描述
    suggestion: Optional[str] = None  # 建議


class ClarificationResult(BaseModel):
    """澄清結果"""
    need_clarification: bool = False
    question: Optional[str] = None
    issues: List[ClarificationIssue] = []
```

**歧義詞處理**：

| 歧義詞 | 處理方式 |
|--------|----------|
| 「這個」/「那個」 | 請提供具體料號 |
| 「上次」 | 請提供具體時間或料號 |
| 「最近」 | 請明確時間範圍（如最近7天） |
| 「一些」/「大概」 | 請提供準確信息 |

**必填字段檢查**：

| 意圖類型 | 必填字段 |
|----------|----------|
| QUERY_STOCK | material_id |
| QUERY_PURCHASE | material_id |
| QUERY_SALES | material_id |
| ANALYZE_SHORTAGE | material_category |
| GENERATE_ORDER | material_id |

**簡單 vs 複雜判斷**：

| 判斷維度 | 簡單查詢 | 複雜任務 |
|----------|----------|----------|
| 條件數量 | 1 個 | 2 個以上 |
| 實體數量 | 1 個 | 2 個以上 |
| 關鍵詞 | 無 | 「分析」「比較」「排名」「ABC」 |
| 輸出 | 單一結果 | 複合結果 |

**指代消解整合**：

```
┌─────────────────────────────────────────────────────────┐
│  Extractor                                               │
│  ├─ 指代消解器 (CoreferenceResolver)                    │
│  │   ├─ 規則基礎消解（快速）                            │
│  │   ├─ LLM 消解（高精度）                             │
│  │   └─ AAM 長期記憶（可選）                           │
│  ├─ 參數提取                                            │
│  │   ├─ 規則引擎（料號、時間）                          │
│  │   └─ LLM（意圖理解）                                │
│  └─ 澄清處理                                            │
│      ├─ 缺失字段檢查                                    │
│      └─ 歧義表達檢查                                    │
└─────────────────────────────────────────────────────────┘
```

**BPA Prompt**：

```
你是庫存管理 BPA。

任務：分析用戶需求，生成結構化查詢或任務規劃。

【意圖分類】
- QUERY_STOCK：查詢庫存
- QUERY_PURCHASE：查詢採購交易
- QUERY_SALES：查詢銷售交易
- ANALYZE_SHORTAGE：缺料分析
- GENERATE_ORDER：生成訂單

【複雜任務判斷】
- 多個料號
- 多個條件（時間+倉庫+類別）
- 包含「分析」「比較」「排名」「ABC」

【指代消解】
- 「那個料號」→ 從上下文獲取
- 「上次」→ 從上下文獲取

【澄清處理】
- 缺失必填字段 → 生成澄清問題
- 歧義表達 → 生成澄清問題

【輸出格式】
{
  "intent": "QUERY_PURCHASE",
  "is_complex": false,
  "query_spec": {
    "material_id": "RM05-008",
    "time_type": "last_month",
    "transaction_type": "101"
  },
  "clarification": {
    "need_clarification": false
  },
  "confidence": 0.95
}
```

---

### 2.3 Data-Agent

**職責**：
1. Schema Registry 管理
2. Text-to-SQL（混合模式）
3. DuckDB 查詢
4. 結果驗證

**架構**：

```
Data-Agent
├── Schema Registry（真值來源）
│   ├── tables/          # 表結構
│   ├── concepts/        # 概念映射
│   └── intent_templates/ # 意圖模板
│
├── Text-to-SQL Engine
│   ├── Rule Engine      # 常見模式
│   └── LLM Generator    # 複雜查詢
│
├── DuckDB Executor
│   └── Query Runner
│
└── Result Validator
    └── Type/Range Check
```

**Schema Registry 結構**：

```json
{
  "tables": {
    "ima_file": {
      "columns": [
        {"id": "ima01", "name": "料號", "type": "VARCHAR"},
        {"id": "ima02", "name": "品名", "type": "VARCHAR"},
        {"id": "ima08", "name": "物料類別", "type": "VARCHAR"}
      ]
    },
    "img_file": {
      "columns": [
        {"id": "img01", "name": "料號", "type": "VARCHAR"},
        {"id": "img02", "name": "倉庫", "type": "VARCHAR"},
        {"id": "img10", "name": "庫存數量", "type": "DECIMAL"}
      ]
    },
    "tlf_file": {
      "columns": [
        {"id": "tlf01", "name": "料號", "type": "VARCHAR"},
        {"id": "tlf06", "name": "交易日期", "type": "DATE"},
        {"id": "tlf10", "name": "數量", "type": "DECIMAL"},
        {"id": "tlf19", "name": "交易類型", "type": "VARCHAR"}
      ]
    }
  },
  "concepts": {
    "MATERIAL_CATEGORY": {
      "plastic": {"keywords": ["塑料件", "塑膠件"], "target_field": "ima02"},
      "metal": {"keywords": ["金屬件"], "target_field": "ima02"}
    },
    "TRANSACTION_TYPE": {
      "101": {"keywords": ["採購", "買進", "進貨"], "target_field": "tlf19"},
      "202": {"keywords": ["銷售", "賣出", "出貨"], "target_field": "tlf19"}
    },
    "WAREHOUSE": {
      "W01": {"keywords": ["原料倉", "原料"], "target_field": "img02"},
      "W02": {"keywords": ["成品倉", "成品"], "target_field": "img02"}
    }
  },
  "intent_templates": {
    "QUERY_PURCHASE": {
      "primary_table": "tlf_file",
      "joins": [{"table": "ima_file", "on": "tlf01 = ima01"}],
      "output_fields": ["tlf01", "ima02", "SUM(tlf10)"],
      "group_by": ["tlf01", "ima02"]
    }
  }
}
```

**Text-to-SQL 流程**：

```
QuerySpec
    │
    ▼
┌─────────────────┐
│ 意圖解析        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ 規則引擎匹配    │────▶│ 模板生成 SQL   │
 │ (常見模式)      │     │ (確定性)        │
└─────────────────┘     └─────────────────┘
         │
         ▼ (未匹配)
┌─────────────────┐     ┌─────────────────┐
 │ LLM 生成        │────▶│ Schema Hints   │
 │ (複雜查詢)      │     │ (約束)          │
└─────────────────┘     └─────────────────┘
```

---

### 2.4 GenAI (補全)

**PoC 階段職責**：
1. 結果格式化（表格）
2. 簡單自然語言說明

**不包含**：
- 深度數據分析
- 建議生成
- 複雜推論

**補全 Prompt** ：

```
你是一個數據助手。

任務：將查詢結果格式化為用戶易讀的形式。

【輸出要求】
1. 表格形式（markdown）
2. 標題說明
3. 簡單統計

【示例】
查詢結果：
料號       | 品名           | 數量
RM05-008  | 塑料原料 A     | 1,000
RM05-009  | 塑料原料 B     | 2,500

總計：3,500
```

---

## 三、數據流

### 3.1 簡單查詢流程

```
用戶：「RM05-008 上月買進多少」
    │
    ▼
Router → TaskType.QUERY
    │
    ▼
Extactor → QuerySpec {
  intent: QUERY_PURCHASE,
  material_id: RM05-008,
  time_type: last_month,
  transaction_type: 101
}
    │
    ▼
Clarification Check → 通過
    │
    ▼
Data-Agent → SQL {
  SELECT tlf01, ima02, SUM(tlf10)
  FROM tlf_file LEFT JOIN ima_file ON tlf01 = ima01
  WHERE tlf01 = 'RM05-008' 
    AND tlf19 = '101'
    AND tlf06 >= last_month
  GROUP BY tlf01, ima02
}
    │
    ▼
GenAI 補全 → 表格 + 說明
```

### 3.2 需要澄清的流程

```
用戶：「上月買進多少」
    │
    ▼
Router → TaskType.QUERY
    │
    ▼
Extractor → QuerySpec {
  intent: QUERY_PURCHASE,
  material_id: null,  // 缺失
  time_type: last_month
}
    │
    ▼
Clarification Check → ❌ 缺少必填字段
    │
    ▼
返回澄清問題：
{
  "need_clarification": true,
  "question": "請提供料號",
  "suggestions": ["RM05-008", "RM06-010"]
}
```

### 3.3 複雜任務流程

```
用戶：「分析 RM05 系列的庫存 ABC 分類」
    │
    ▼
Router → TaskType.COMPLEX
    │
    ▼
BPA → TodoPlan {
  title: "RM05 系列庫存 ABC 分類分析",
  steps: [
    {step: 1, description: "查詢 RM05 系列庫存", query_spec: {...}},
    {step: 2, description: "ABC 分類計算", requires_knowledge: true},
    {step: 3, description: "生成報告"}
  ]
}
    │
    ▼
執行 Step 1 → Data-Agent → 庫存數據
    │
    ▼
執行 Step 2 → 知識庫 → ABC 分類算法
    │
    ▼
執行 Step 3 → 整合結果 → 最終報告
```

---

## 四、Schema 統一管理

### 4.1 問題診斷（舊架構）

| 問題 | 原因 | 影響 |
|------|------|------|
| Schema 零散 | 多個文件、多個位置 | 維護困難 |
| 映射不一致 | 同一概念多處定義 | 錯誤來源 |
| 缺乏約束 | 沒有統一真值 | AI 臆測 |

### 4.2 解決方案

**單一 Schema Registry**：

```
metadata/
└── schema_registry.json   # 唯一真值來源

mm_agent/
└── services/
    └── schema_registry.py  # 訪問接口
```

**使用原則**：
1. 所有概念映射必須在 `schema_registry.json` 中定義
2. 所有代碼通過 `SchemaRegistry` 類訪問
3. 禁止硬編碼映射關係

---

## 五、與現有系統整合

### 5.1 現有組件

| 組件 | 路徑 | 狀態 |
|------|------|------|
| NLP 前端 | `frontend/src/pages/NLP.tsx` | 需整合 |
| MM-Agent | `mm_agent/main.py` | 已改造 |
| Data-Agent | `data_agent/` | 需改造 |

### 5.2 整合方式

```
┌─────────────────────────────────────────────────────────┐
│  前端 (NLP.tsx)                                        │
│  ├─ 調用 MM-Agent API                                 │
│  └─ 顯示結果（表格 + 說明）                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  MM-Agent (main.py)                                    │
│  ├─ Router → Extractor → Clarification                │
│  ├─ BPA → Todo Planning                               │
│  └─ 調用 Data-Agent API                               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Data-Agent (data_agent/)                              │
│  ├─ Schema Registry                                    │
│  ├─ Text-to-SQL Engine                                │
│  └─ DuckDB 查詢                                        │
└─────────────────────────────────────────────────────────┘
```

---

## 六、文件結構

```
datalake-system/
├── metadata/
│   └── schema_registry.json       # Schema 真值來源
│
├── mm_agent/
│   ├── router.py                  # GenAI (Router)
│   ├── extractor.py               # Extractor + Clarification
│   ├── coreference_resolver.py   # 指代消解器
│   ├── sql_generator.py           # SQL 生成器
│   │
│   ├── bpa/                       # BPA 模組
│   │   ├── __init__.py
│   │   ├── intent_classifier.py   # 意圖分類
│   │   ├── semantic_analyzer.py   # 語義分析
│   │   ├── todo_planner.py        # Todo 規劃
│   │   └── models.py              # BPA 模型
│   │
│   ├── services/
│   │   ├── schema_registry.py     # Schema 訪問
│   │   └── text_to_sql.py         # Text-to-SQL
│   │
│   └── main.py                    # 入口整合
│
├── data_agent/
│   ├── agent.py                   # Data-Agent 主體
│   ├── schema_service.py          # Schema 服務
│   └── text_to_sql.py             # Text-to-SQL
│
└── frontend/
    └── src/
        └── pages/
            └── NLP.tsx           # 前端整合
```

---

## 七、實現計劃

### Phase 1：基礎設施 ✅ 已完成

- [x] 統一 Schema Registry（整合現有 schema）
- [x] 實現 Router（GenAI 第一層）
- [x] 實現 Extractor（語義分析 + 指代消解）

### Phase 2：核心功能 ✅ 已完成

- [x] 實現 Data-Agent Text-to-SQL（混合模式）
- [x] 實現 SQL Generator
- [x] 整合 MM-Agent → Data-Agent
- [x] 新增 Clarification 機制

### Phase 3：完善功能 ⏳ 待執行

- [ ] 實現 Todo 規劃（複雜任務）
- [ ] 實現 GenAI 補全（表格格式化）
- [ ] 前端整合

### Phase 4：測試優化 ⏳ 待執行

- [ ] 單元測試
- [ ] 整合測試
- [ ] 效能優化

---

## 八、優勢

### 8.1 職責清晰

| 舊架構 | 新架構 |
|--------|--------|
| 多層語義分析 | 三層分明 |
| Schema 零散 | 統一 Registry |
| 混合模式 | 規則 + AI 分工 |
| 無澄清機制 | Clarification 保障精準 |

### 8.2 可維護性

- **修改意圖邏輯** → 只改 BPA
- **修改 Schema** → 只改 Registry
- **修改 SQL 生成** → 只改 Text-to-SQL
- **修改澄清邏輯** → 只改 Extractor

### 8.3 可擴展性

- **增加新意圖** → 只加 BPA 分類
- **增加新 Schema** → 只加 Registry
- **增加新數據源** → 只改 Data-Agent
- **增加新 Agent** → 複用 Router/Extractor

### 8.4 企業級精準

- **指代消解** → 解決「這個」「那個」
- **Clarification** → 處理缺失/歧義
- **驗證機制** → 確保數據正確

---

## 九、注意事項

### 9.1 AI 的角色

- **Router**：LLM 做分類，不做轉換
- **BPA/Extractor**：LLM 做理解，規則做分流
- **指代消解**：規則優先，LLM 補充
- **Clarification**：規則檢查，確保精準
- **Data-Agent**：規則做轉換，LLM 做複雜補充

### 9.2 Schema 的使用

- **不是實時查表**，而是注入到 Prompt
- LLM 知道 Schema 後，直接輸出結構化參數
- SQL Generator 根據參數查表生成 SQL

### 9.3 Clarification 原則

1. **精準優先** → 有歧義就回問
2. **一次性澄清** → 避免多輪回覆
3. **提供建議** → 幫助用戶回答

### 9.4 PoC 階段優先級

1. ✅ Router 過濾
2. ✅ BPA 意圖分類
3. ✅ Extractor + Clarification
4. ✅ Data-Agent Text-to-SQL
5. ⏳ Todo 規劃
6. ⏳ GenAI 補全

---

## 九、多語言支持

### 9.1 設計原則

```
規則優先 → 覆蓋 80% 場景
Clarification 兜底 → 確保精準
LLM 擴充 → 產品化階段
```

### 9.2 當前覆蓋狀態

| 語言 | 時間表達 | 指代消解 | 交易類型 | 狀態 |
|------|---------|---------|---------|------|
| 簡體中文 | ✅ | ✅ | ✅ | 完整 |
| 繁體中文 | ⚠️ 部分 | ✅ | ⚠️ 部分 | 需擴充 |
| 英文 | ❌ 未覆蓋 | ❌ 未覆蓋 | ❌ 未覆蓋 | 待開發 |

### 9.3 時間表達規則（PoC）

```python
# extractor.py - 多語言時間表達規則

TIME_EXPRESSIONS = {
    # 簡體中文
    "last_month": ["上月", "上个月"],
    "this_month": ["本月", "这个月"],
    "last_year": ["去年"],
    "this_year": ["今年"],
    "last_week": ["最近7天", "上週", "上周", "最近一週"],
    "last_2_months": ["上上月", "上上个月"],
    "last_2_weeks": ["上上週", "上上周", "前第二周"],

    # 繁體中文（待擴充）
    "last_month_tw": ["上個月"],
    "this_month_tw": ["本月", "這個月"],

    # 英文（待開發）
    "last_month_en": ["last month", "previous month"],
    "this_month_en": ["this month", "current month"],
    "last_year_en": ["last year", "previous year"],
    "this_year_en": ["this year", "current year"],
    "last_week_en": ["last week", "past week"],
}
```

### 9.4 交易類型映射（PoC）

```python
TRANSACTION_TYPES = {
    # 中文
    "101": ["採購", "買進", "進貨", "收料"],
    "202": ["銷售", "賣出", "出貨"],

    # 英文（待開發）
    "101_en": ["purchase", "procurement", "buy", "receipt"],
    "202_en": ["sales", "sell", "shipment", "outbound"],
}
```

### 9.5 指代消解（多語言）

```python
# CoreferenceResolver - 多語言指代

REFERENCE_TERMS = {
    # 中文
    "proximal": ["這個", "這", "它", "此"],
    "distal": ["那個", "那", "彼"],
    "time": ["上次", "這次", "最近"],

    # 英文（待開發）
    "proximal_en": ["this", "it", "the"],
    "distal_en": ["that", "those"],
    "time_en": ["last time", "this time", "recently"],
}
```

### 9.6 Clarification 兜底機制

```
┌─────────────────────────────────────────────────────────┐
│  英文查詢：「last month procurement」                    │
│      │                                                   │
│      ▼                                                   │
│  規則引擎：未識別                                        │
│      │                                                   │
│      ▼                                                   │
│  Clarification：                                        │
│  {                                                      │
│    "need_clarification": true,                          │
│    "question": "請問「last month」是指？",             │
│    "options": ["January 2025", "December 2024"]         │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
```

### 9.7 產品化階段規劃

| 階段 | 語言 | 實現方式 |
|------|------|---------|
| PoC | 中文 | 規則引擎 |
| Phase 2 | 繁體中文 | 擴充規則 |
| Phase 3 | 英文 | LLM + 規則混合 |
| Phase 4 | 多語言 | 統一 LLM 理解 |

### 9.8 LLM（ 多語言理解產品化）

```python
# 產品化階段：交給 LLM 處理多語言

async def extract_multilingual(user_input: str) -> Dict:
    """多語言結構化提取"""

    prompt = """
    你是一個多語言數據助手。

    任務：從用戶輸入中提取查詢參數。

    支持語言：簡體中文、繁體中文、英文。

    【輸入】
    {user_input}

    【輸出】
    {
      "intent": "QUERY_PURCHASE",
      "material_id": "RM05-008",
      "time_type": "last_month",
      "transaction_type": "101"
    }
    """

    result = await llm.generate(prompt)
    return parse_json(result)
```

### 9.9 注意事項

1. **優先級**：先滿足中文用戶，英文支持為輔
2. **精準度**：英文表達可能有歧義，Clarification 是兜底
3. **可擴充**：規則引擎易於新增語言支持

---

## 十、與 AI-Box 整合

### 10.1 可複用模組

| 模組 | 說明 | 可移植到 |
|------|------|----------|
| `router.py` | 任務路由 | 所有 Agent |
| `extractor.py` | 結構化提取 + Clarification | 所有 Agent |
| `coreference_resolver.py` | 指代消解 | 所有 Agent |
| `models/query_spec.py` | 通用查詢模型 | 所有 Agent |

### 10.2 領域特定模組

| 模組 | 說明 | MM-Agent 專用 |
|------|------|---------------|
| `bpa/` | 業務邏輯 | ✅ |
| `sql_generator.py` | SQL 模板 | ✅ |
| `services/schema_registry.py` | Schema | ✅ |

### 10.3 移植策略

```
MM-Agent PoC
    │
    ▼ 成功驗證
┌─────────────────────────┐
│  抽象通用模組            │
│  - router.py            │
│  - extractor.py         │
│  - coreference_resolver │
│  - models/              │
└─────────────────────────┘
    │
    ▼ AI-Box 產品化
┌─────────────────────────┐
│  AI-Box Agent Framework │
│                         │
│  ┌───────────┐  ┌─────┐│
│  │ HR Agent │  │...  ││
│  └───────────┘  └─────┘│
└─────────────────────────┘
```

---

**文件結束**
職責清晰、層次分明、AI 發力
```

**設計原則**：
- 每一層只做一件事
- Schema 統一管理（解決零散問題）
- AI 專注理解，規則專注轉換
- PoC 階段優先滿足功能

---

### 1.2 架構圖

```
用戶輸入 (NLP)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  GenAI (Router)                                            │
│  職責：                                                    │
│  ├─ 意圖過濾（打錯字 / 打招呼 / 非相關）                    │
│  ├─ 任務路由（轉發到對應 BPA）                              │
│  └─ 簡單指代消解（this/that）                              │
│  技術：LLM（分類 + 指代）                                   │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  BPA (MM-Agent)                                           │
│  職責：                                                    │
│  ├─ 業務意圖分類（簡單查詢 / 複雜任務）                     │
│  ├─ 語義分析（what/when/how/where）                       │
│  ├─ 指代消解（「那個料號」→ RM05-008）                     │
│  ├─ 簡單查詢 → 結構化需求 → Data-Agent                     │
│  └─ 複雜任務 → Todo 規劃 + 逐步執行                       │
│  技術：LLM（理解） + 規則（任務分類）                       │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  Data-Agent                                               │
│  職責：                                                    │
│  ├─ Schema Registry（真值來源，統一管理）                  │
│  ├─ Text-to-SQL（混合模式）                                │
│  │   ├─ 規則引擎：常見模式（料號查詢、庫存查詢）          │
│  │   └─ LLM：複雜查詢（自然語句、模糊需求）               │
│  ├─ DuckDB 查詢（SeaweedFS）                              │
│  └─ 結果驗證（欄位類型、數據範圍）                         │
│  技術：規則引擎 + LLM + DuckDB                             │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  GenAI (補全) - PoC 階段                                   │
│  職責：                                                    │
│  ├─ 結果格式化（表格、列表）                                │
│  └─ 簡單自然語言說明                                       │
│  技術：Prompt Template                                     │
└─────────────────────────────────────────────────────────────┘
```

---

### 1.3 職責對照表

| 層次 | 組件 | 輸入 | 輸出 | 技術 |
|------|------|------|------|------|
| L1 | GenAI (Router) | 用戶原始輸入 | 清洗後意圖 / 拒絕回覆 | LLM |
| L2 | BPA (MM-Agent) | 清洗後意圖 | 結構化需求 / Todo 列表 | LLM + 規則 |
| L3 | Data-Agent | 結構化需求 | SQL 執行結果 | 規則 + LLM |
| L4 | GenAI (補全) | SQL 結果 | 自然語言回覆 | Prompt |

---

## 二、組件詳細設計

### 2.1 GenAI (Router)

**職責**：
1. 意圖過濾（排除無關請求）
2. 簡單指代消解
3. 任務路由

**意圖類型**：

```python
class TaskType(Enum):
    GREETING = "greeting"        # 打招呼
    ERROR_INPUT = "error_input"  # 錯誤輸入
    QUERY = "query"             # 簡單查詢
    COMPLEX = "complex"          # 複雜任務
    OUT_OF_SCOPE = "out_of_scope"  # 非任務範圍
```

**處理邏輯**：

| 輸入類型 | 處理方式 |
|----------|----------|
| 打招呼 | 直接回覆問候語 |
| 錯誤輸入 | 要求重新輸入 |
| 非相關問題 |礼貌拒绝 |
| 簡單查詢 | 轉發 BPA |
| 複雜任務 | 轉發 BPA |

**Router Prompt**：

```
你是智能助手路由系統。

任務：分析用戶輸入，分類並過濾。

【分類規則】
1. 打招呼：「你好」「早安」「嗨」等
2. 錯誤輸入：乱码、无意义字符、过短
3. 非任務範圍：與庫存/採購/銷售無關的問題
4. 簡單查詢：單一數據需求（如「RM05-008 上月買進多少」）
5. 複雜任務：多步驟、多條件、分析需求

【輸出格式】
{
  "task_type": "query",
  "cleaned_input": "RM05-008 上月買進多少",
  "simple_reference": null,  // this/that 的指代
  "response": null,          // 直接回覆（如打招呼）
  "confidence": 0.95
}
```

---

### 2.2 BPA (MM-Agent)

**職責**：
1. 業務意圖分類
2. 語義分析
3. 指代消解（業務相關）
4. 簡單查詢 → 結構化需求
5. 複雜任務 → Todo 規劃

**意圖類型**：

```python
class QueryIntent(Enum):
    QUERY_STOCK = "QUERY_STOCK"           # 庫存查詢
    QUERY_PURCHASE = "QUERY_PURCHASE"     # 採購交易查詢
    QUERY_SALES = "QUERY_SALES"           # 銷售交易查詢
    ANALYZE_SHORTAGE = "ANALYZE_SHORTAGE"  # 缺料分析
    GENERATE_ORDER = "GENERATE_ORDER"     # 生成訂單
```

**QuerySpec 結構**：

```python
class QuerySpec(BaseModel):
    """結構化查詢需求"""

    # 意圖
    intent: QueryIntent

    # 參數
    material_id: Optional[str] = None        # 料號
    warehouse: Optional[str] = None           # 倉庫
    time_type: Optional[TimeType] = None      # 時間類型
    time_value: Optional[str] = None          # 時間值
    transaction_type: Optional[str] = None   # 交易類型
    material_category: Optional[str] = None   # 物料類別
    aggregation: Optional[str] = None         # 聚合函數
    order_by: Optional[str] = None            # 排序
    limit: int = 100

    # 置信度
    confidence: float = 1.0
    missing_fields: List[str] = []
```

**簡單 vs 複雜判斷**：

| 判斷維度 | 簡單查詢 | 複雜任務 |
|----------|----------|----------|
| 條件數量 | 1 個 | 2 個以上 |
| 實體數量 | 1 個 | 2 個以上 |
| 關鍵詞 | 無 | 「分析」「比較」「排名」「ABC」 |
| 輸出 | 單一結果 | 複合結果 |

**Todo 結構**：

```python
class TodoItem(BaseModel):
    """待辦事項"""
    step: int
    description: str
    query_spec: Optional[QuerySpec] = None
    status: str = "pending"  # pending / done / failed
    result: Optional[Any] = None

class TodoPlan(BaseModel):
    """任務規劃"""
    task_type: str = "complex"
    title: str
    steps: List[TodoItem]
    requires_knowledge: bool = False  # 是否需要外部知識
```

**BPA Prompt**：

```
你是庫存管理 BPA。

任務：分析用戶需求，生成結構化查詢或任務規劃。

【意圖分類】
- QUERY_STOCK：查詢庫存
- QUERY_PURCHASE：查詢採購交易
- QUERY_SALES：查詢銷售交易
- ANALYZE_SHORTAGE：缺料分析
- GENERATE_ORDER：生成訂單

【複雜任務判斷】
- 多個料號
- 多個條件（時間+倉庫+類別）
- 包含「分析」「比較」「排名」「ABC」

【指代消解】
- 「那個料號」→ 從上下文獲取
- 「上次」→ 從上下文獲取

【輸出格式】
{
  "intent": "QUERY_PURCHASE",
  "is_complex": false,
  "query_spec": {
    "material_id": "RM05-008",
    "time_type": "last_month",
    "transaction_type": "101"
  },
  "confidence": 0.95
}
```

---

### 2.3 Data-Agent

**職責**：
1. Schema Registry 管理
2. Text-to-SQL（混合模式）
3. DuckDB 查詢
4. 結果驗證

**架構**：

```
Data-Agent
├── Schema Registry（真值來源）
│   ├── tables/          # 表結構
│   ├── concepts/        # 概念映射
│   └── intent_templates/ # 意圖模板
│
├── Text-to-SQL Engine
│   ├── Rule Engine      # 常見模式
│   └── LLM Generator    # 複雜查詢
│
├── DuckDB Executor
│   └── Query Runner
│
└── Result Validator
    └── Type/Range Check
```

**Schema Registry 結構**：

```json
{
  "tables": {
    "ima_file": {
      "columns": [
        {"id": "ima01", "name": "料號", "type": "VARCHAR"},
        {"id": "ima02", "name": "品名", "type": "VARCHAR"},
        {"id": "ima08", "name": "物料類別", "type": "VARCHAR"}
      ]
    },
    "img_file": {
      "columns": [
        {"id": "img01", "name": "料號", "type": "VARCHAR"},
        {"id": "img02", "name": "倉庫", "type": "VARCHAR"},
        {"id": "img10", "name": "庫存數量", "type": "DECIMAL"}
      ]
    },
    "tlf_file": {
      "columns": [
        {"id": "tlf01", "name": "料號", "type": "VARCHAR"},
        {"id": "tlf06", "name": "交易日期", "type": "DATE"},
        {"id": "tlf10", "name": "數量", "type": "DECIMAL"},
        {"id": "tlf19", "name": "交易類型", "type": "VARCHAR"}
      ]
    }
  },
  "concepts": {
    "MATERIAL_CATEGORY": {
      "plastic": {"keywords": ["塑料件", "塑膠件"], "target_field": "ima02"},
      "metal": {"keywords": ["金屬件"], "target_field": "ima02"}
    },
    "TRANSACTION_TYPE": {
      "101": {"keywords": ["採購", "買進", "進貨"], "target_field": "tlf19"},
      "202": {"keywords": ["銷售", "賣出", "出貨"], "target_field": "tlf19"}
    },
    "WAREHOUSE": {
      "W01": {"keywords": ["原料倉", "原料"], "target_field": "img02"},
      "W02": {"keywords": ["成品倉", "成品"], "target_field": "img02"}
    }
  },
  "intent_templates": {
    "QUERY_PURCHASE": {
      "primary_table": "tlf_file",
      "joins": [{"table": "ima_file", "on": "tlf01 = ima01"}],
      "output_fields": ["tlf01", "ima02", "SUM(tlf10)"],
      "group_by": ["tlf01", "ima02"]
    }
  }
}
```

**Text-to-SQL 流程**：

```
QuerySpec
    │
    ▼
┌─────────────────┐
│ 意圖解析        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ 規則引擎匹配    │────▶│ 模板生成 SQL   │
│ (常見模式)      │     │ (確定性)        │
└─────────────────┘     └─────────────────┘
         │
         ▼ (未匹配)
┌─────────────────┐     ┌─────────────────┐
│ LLM 生成        │────▶│ Schema Hints   │
│ (複雜查詢)      │     │ (約束)          │
└─────────────────┘     └─────────────────┘
```

---

### 2.4 GenAI (補全)

**PoC 階段職責**：
1. 結果格式化（表格）
2. 簡單自然語言說明

**不包含**：
- 深度數據分析
- 建議生成
- 複雜推論

**補全 Prompt** ：

```
你是一個數據助手。

任務：將查詢結果格式化為用戶易讀的形式。

【輸出要求】
1. 表格形式（markdown）
2. 標題說明
3. 簡單統計

【示例】
查詢結果：
料號       | 品名           | 數量
RM05-008  | 塑料原料 A     | 1,000
RM05-009  | 塑料原料 B     | 2,500

總計：3,500
```

---

## 三、數據流

### 3.1 簡單查詢流程

```
用戶：「RM05-008 上月買進多少」
    │
    ▼
Router → TaskType.QUERY
    │
    ▼
BPA → QuerySpec {
  intent: QUERY_PURCHASE,
  material_id: RM05-008,
  time_type: last_month,
  transaction_type: 101
}
    │
    ▼
Data-Agent → SQL {
  SELECT tlf01, ima02, SUM(tlf10)
  FROM tlf_file LEFT JOIN ima_file ON tlf01 = ima01
  WHERE tlf01 = 'RM05-008' 
    AND tlf19 = '101'
    AND tlf06 >= last_month
  GROUP BY tlf01, ima02
}
    │
    ▼
GenAI 補全 → 表格 + 說明
```

### 3.2 複雜任務流程

```
用戶：「分析 RM05 系列的庫存 ABC 分類」
    │
    ▼
Router → TaskType.COMPLEX
    │
    ▼
BPA → TodoPlan {
  title: "RM05 系列庫存 ABC 分類分析",
  steps: [
    {step: 1, description: "查詢 RM05 系列庫存", query_spec: {...}},
    {step: 2, description: "ABC 分類計算", requires_knowledge: true},
    {step: 3, description: "生成報告"}
  ]
}
    │
    ▼
執行 Step 1 → Data-Agent → 庫存數據
    │
    ▼
執行 Step 2 → 知識庫 → ABC 分類算法
    │
    ▼
執行 Step 3 → 整合結果 → 最終報告
```

---

## 四、Schema 統一管理

### 4.1 問題診斷（舊架構）

| 問題 | 原因 | 影響 |
|------|------|------|
| Schema 零散 | 多個文件、多個位置 | 維護困難 |
| 映射不一致 | 同一概念多處定義 | 錯誤來源 |
| 缺乏約束 | 沒有統一真值 | AI 臆測 |

### 4.2 解決方案

**單一 Schema Registry**：

```
metadata/
└── schema_registry.json   # 唯一真值來源

mm_agent/
└── services/
    └── schema_registry.py  # 訪問接口
```

**使用原則**：
1. 所有概念映射必須在 `schema_registry.json` 中定義
2. 所有代碼通過 `SchemaRegistry` 類訪問
3. 禁止硬編碼映射關係

---

## 五、與現有系統整合

### 5.1 現有組件

| 組件 | 路徑 | 狀態 |
|------|------|------|
| NLP 前端 | `frontend/src/pages/NLP.tsx` | 需整合 |
| MM-Agent | `mm_agent/main.py` | 需改造 |
| Data-Agent | `data_agent/` | 需改造 |

### 5.2 整合方式

```
┌─────────────────────────────────────────────────────────┐
│  前端 (NLP.tsx)                                        │
│  ├─ 調用 MM-Agent API                                 │
│  └─ 顯示結果（表格 + 說明）                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  MM-Agent (main.py)                                    │
│  ├─ Router → BPA → SQL Generator                       │
│  └─ 調用 Data-Agent API                               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Data-Agent (data_agent/)                              │
│  ├─ Schema Registry                                    │
│  ├─ Text-to-SQL Engine                                │
│  └─ DuckDB 查詢                                        │
└─────────────────────────────────────────────────────────┘
```

---

## 六、文件結構

```
datalake-system/
├── metadata/
│   └── schema_registry.json       # Schema 真值來源
│
├── mm_agent/
│   ├── router.py                  # GenAI (Router)
│   ├── bpa/                       # BPA 模組
│   │   ├── __init__.py
│   │   ├── intent_classifier.py   # 意圖分類
│   │   ├── semantic_analyzer.py   # 語義分析
│   │   ├── todo_planner.py        # Todo 規劃
│   │   └── models.py              # BPA 模型
│   │
│   ├── services/
│   │   ├── schema_registry.py     # Schema 訪問
│   │   └── text_to_sql.py         # Text-to-SQL
│   │
│   ├── sql_generator.py           # SQL 生成器
│   └── main.py                    # 入口整合
│
├── data_agent/
│   ├── agent.py                   # Data-Agent 主體
│   ├── schema_service.py          # Schema 服務
│   └── text_to_sql.py             # Text-to-SQL
│
└── frontend/
    └── src/
        └── pages/
            └── NLP.tsx           # 前端整合
```

---

## 七、實現計劃

### Phase 1：基礎設施

- [ ] 統一 Schema Registry（整合現有 schema）
- [ ] 實現 Router（GenAI 第一層）
- [ ] 實現 BPA 核心（意圖分類 + 語義分析）

### Phase 2：核心功能

- [ ] 實現 Data-Agent Text-to-SQL（混合模式）
- [ ] 實現 SQL Generator
- [ ] 整合 MM-Agent → Data-Agent

### Phase 3：完善功能

- [ ] 實現 Todo 規劃（複雜任務）
- [ ] 實現 GenAI 補全（表格格式化）
- [ ] 前端整合

### Phase 4：測試優化

- [ ] 單元測試
- [ ] 整合測試
- [ ] 效能優化

---

## 八、優勢

### 8.1 職責清晰

| 舊架構 | 新架構 |
|--------|--------|
| 多層語義分析 | 三層分明 |
| Schema 零散 | 統一 Registry |
| 混合模式 | 規則 + AI 分工 |

### 8.2 可維護性

- **修改意圖邏輯** → 只改 BPA
- **修改 Schema** → 只改 Registry
- **修改 SQL 生成** → 只改 Text-to-SQL

### 8.3 可擴展性

- **增加新意圖** → 只加 BPA 分類
- **增加新 Schema** → 只加 Registry
- **增加新數據源** → 只改 Data-Agent

---

## 九、注意事項

### 9.1 AI 的角色

- **Router**：LLM 做分類，不做轉換
- **BPA**：LLM 做理解，規則做分流
- **Data-Agent**：規則做轉換，LLM 做複雜補充

### 9.2 Schema 的使用

- **不是實時查表**，而是注入到 Prompt
- LLM 知道 Schema 後，直接輸出結構化參數
- SQL Generator 根據參數查表生成 SQL

### 9.3 PoC 階段優先級

1. ✅ Router 過濾
2. ✅ BPA 意圖分類
3. ✅ Data-Agent Text-to-SQL
4. ⏳ Todo 規劃
5. ⏳ GenAI 補全

---

**文件結束**
