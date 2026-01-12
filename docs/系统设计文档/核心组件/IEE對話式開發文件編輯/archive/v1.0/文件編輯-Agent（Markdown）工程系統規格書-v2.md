# 文件編輯 Agent（Markdown）工程系統規格書 v2.0

**代碼功能說明**: 文件編輯 Agent（Markdown）工程系統規格書 v2.0 - 經可行性評估與詳細技術規範補充後的完整版本
**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-11

---

> 本文件為 工程實作導向 的系統規格（Engineering Specification），定義「文件編輯 Agent」在整體 Agent Orchestration 架構中的 職責、邊界、介面與流程。本 Agent 不負責任務理解與能力調度，僅在合法授權下，執行受控、可審計的 Markdown 文件編輯行為。
>
> **版本說明**: v2.0 版本基於 v1.0 的可行性評估與技術審查，補充了可機器驗證的 DSL 規範、LLM 可重現策略、錯誤處理機制、觀測性模型等工程實作所需細節，並明確了 Markdown 標準、Target Selector 唯一性、Constraints 可驗證性等關鍵技術決策。

---

## 1. 系統定位與設計原則

### 1.1 系統定位

文件編輯 Agent（以下簡稱 DEA, Document Editing Agent）屬於：

- **Domain Execution Layer Agent**
- 專職處理 **Markdown 文件的結構化編輯**
- 永遠在 **Orchestrator Agent 授權之後** 才能被調用

其角色是：

> 在既定文件（DocID）與既定版本基礎上，根據明確的編輯意圖（Intent），產生可驗證、可回滾的內容變更（Patch / Diff）。

### 1.2 核心設計原則

1. **Document ≠ File**
   文件是一個具備生命週期、版本與治理規則的「知識物件」，而非單一檔案。

2. **Edit ≠ Generate**
   所有編輯行為必須以 Patch / Delta 形式表達，而非直接覆寫全文。

3. **Intent-driven Editing**
   編輯必須由結構化 Intent 觸發，而非自然語言即時生成。

4. **Governance-first**
   無 DocID、無合法版本狀態，不得編輯。

5. **Auditable & Deterministic**
   每一次編輯行為皆可追溯來源、原因與影響範圍。結果必須可重現。

6. **Machine-verifiable Constraints**
   所有約束條件必須可機器驗證，不得使用模糊描述。

---

## 2. Markdown 標準與支援範圍

### 2.1 標準規範

**指定 Markdown 標準**：

- **CommonMark 1.x** 作為基礎標準
- **GitHub Flavored Markdown (GFM)** 作為擴展標準

### 2.2 支援特性清單

#### 2.2.1 完全支援（Fully Supported）

- 標題（Heading）：`#` 至 `######`（H1-H6）
- 段落（Paragraph）
- 強調（Emphasis）：`*italic*`、`**bold**`
- 列表（List）：
  - 有序列表（Ordered List）
  - 無序列表（Unordered List）
  - 任務列表（Task List，GFM）：`- [ ]`、`- [x]`
- 程式碼（Code）：
  - 行內程式碼（Inline Code）：`` `code` ``
  - 程式碼區塊（Code Block）：``````language ```
- 連結（Link）：`[text](url)`、`[text][reference]`
- 圖片（Image）：`![alt](url)`
- 引用（Blockquote）：`> quote`
- 水平線（Horizontal Rule）：`---`、`***`
- 表格（Table，GFM）：`| header | header |`
- 換行（Line Break）：雙空格 + 換行、`<br>`
- HTML 片段（HTML Fragments）：限制性支援（見 2.2.3）

#### 2.2.2 部分支援（Partial Support）

- **Front Matter（YAML）**：
  - 視為獨立 block，僅允許讀取
  - 不允許直接編輯 Front Matter 內容
  - 如需修改，必須通過文件層級操作（由 Version Controller 處理）

#### 2.2.3 限制性支援（Restricted Support）

- **HTML 內嵌**：
  - 允許在段落中嵌入簡單 HTML 標籤（如 `<strong>`、`<em>`、`<br>`）
  - 禁止嵌入腳本（`<script>`）、樣式（`<style>`）或複雜 HTML 結構
  - HTML 片段在編輯時可能被轉換為對應的 Markdown 語法

- **擴充語法（Extensions）**：
  - Admonition blocks（如 `!!! note`）等擴充語法不直接支援
  - 如需支援，必須通過 AST 擴展機制明確定義

#### 2.2.4 不支援（Not Supported）

- MathJax / LaTeX 數學公式（未來可擴展）
- Mermaid / 圖表語法（由專用渲染器處理）
- 自定義擴展語法（除非明確定義）

### 2.3 AST 解析策略

- 使用 **CommonMark 相容的 AST 解析器**（推薦：`markdown-it`、`remark`、`markdown-ast`）
- AST 節點類型必須映射到標準 Markdown 語法
- 保留 heading hierarchy、block 結構、inline 結構的完整資訊
- 解析後的 AST 必須支援可逆轉換（AST → Markdown）

---

## 3. 系統邊界（Scope Definition）

### 3.1 DEA 負責的事項（IN SCOPE）

- Markdown 文件解析（AST / Block Level）
- 編輯意圖（Edit Intent）解析與驗證
- 編輯位置定位（章節 / Block / Anchor）
- Patch / Diff 生成（Block Patch + Text Patch）
- 編輯後文件重組
- 編輯結果驗證（結構 / 約束 / 語義漂移）
- LLM 內容生成（在約束範圍內）
- 最小上下文裝配
- 可重現性保證（固定模型版本、溫度、種子）

### 3.2 DEA 明確不負責的事項（OUT OF SCOPE）

- 任務意圖理解（由 Orchestrator 負責）
- 文件註冊 / DocID 生成（由 Document Registry 負責）
- 版本授權與合法性裁決（由 Version Controller 負責）
- 使用者權限與安全稽核（由 Security Service 負責）
- 模型資源選擇（MoE，由 Orchestrator / MoE System 負責）
- 文件最終提交與發布（由 Version Controller 負責）
- 併發編輯衝突解決（由 Version Controller 負責，DEA 僅提供 Patch）
- 外部資料來源選擇（由 Orchestrator 負責，DEA 僅使用提供的上下文）

---

## 4. 系統前置條件（Preconditions）

DEA 在被呼叫前，**必須已滿足以下條件**：

1. Orchestrator 已判定此任務為「文件編輯任務」
2. Document Registry 已存在合法 DocID
3. 目標文件處於可編輯狀態（`draft` / `editing`）
4. 已建立可寫入的新版本（Version Context）
5. 已完成必要的 Security / Audit 授權
6. DocumentContext 包含完整的 `doc_id`、`version_id`、`doc_registry_endpoint`、`version_context_id`、`editability_state`、`actor_id`、`permission_scope`

若任一條件不成立，DEA **必須拒絕執行**，並返回對應的錯誤碼（見 9.1 錯誤碼清單）。

---

## 5. 核心資料模型

### 5.1 Document Context

```json
{
  "$schema": "https://schema.aibox.com/document-context/v1.0",
  "doc_id": "DOC-20260109-0001",
  "task_id": "TASK-20260109-001",
  "current_version_id": "v3",
  "file_path": "/docs/architecture.md",
  "format": "markdown",
  "doc_registry_endpoint": "https://registry.example.com/api/v1",
  "version_context_id": "version-context-123",
  "editability_state": "editing",
  "actor_id": "user-123",
  "permission_scope": ["read", "edit"]
}
```

**欄位說明**：

- `doc_id`（必需）：文件唯一標識
- `task_id`（必需）：關聯任務 ID
- `current_version_id`（必需）：當前版本 ID
- `file_path`（必需）：文件路徑
- `format`（必需）：文件格式，固定為 `"markdown"`
- `doc_registry_endpoint`（必需）：Document Registry API 端點
- `version_context_id`（必需）：版本上下文 ID
- `editability_state`（必需）：可編輯狀態（`"draft"` | `"editing"` | `"locked"`）
- `actor_id`（必需）：執行編輯的操作者 ID
- `permission_scope`（必需）：權限範圍列表（`["read"]` | `["read", "edit"]` | `["read", "edit", "delete"]`）

### 5.2 Edit Intent（編輯意圖）

Edit Intent 為 **文件編輯 Agent 的核心控制語言（DSL）**，用以描述「**允許被執行的編輯行為**」，而非生成提示。

Edit Intent DSL 的設計目標是：

- 可機器驗證（Machine-validatable）
- 可治理（Governance-aware）
- 可演進（Versionable / Extensible）
- 可作為模型訓練與審計資料

#### 5.2.1 設計原則（DSL Design Principles）

1. **Intent ≠ Prompt**
   DSL 不描述「怎麼寫」，只描述「要改什麼、改到哪裡、允許怎麼改」。

2. **Declarative First**
   Intent 為宣告式語言，不包含流程控制（if / loop）。

3. **Bounded Action Space**
   每一個 Intent 都映射到有限的 Patch Operation。

4. **Composable but Restricted**
   可組合多個 Intent，但必須可線性拆解為獨立 Patch。

5. **Machine-verifiable Constraints**
   所有約束條件必須可機器驗證，使用量化指標而非模糊描述。

#### 5.2.2 Edit Intent DSL JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schema.aibox.com/edit-intent/v2.0",
  "title": "Edit Intent DSL Schema v2.0",
  "type": "object",
  "required": ["intent_id", "intent_schema_version", "intent_type", "scope", "target", "action", "constraints", "audit"],
  "properties": {
    "intent_id": {
      "type": "string",
      "pattern": "^INTENT-[0-9]{8}-[0-9]{3}$",
      "description": "Intent 唯一標識"
    },
    "intent_schema_version": {
      "type": "string",
      "enum": ["2.0"],
      "description": "Intent DSL Schema 版本"
    },
    "intent_type": {
      "type": "string",
      "enum": ["insert", "update", "delete", "refactor", "summarize"],
      "description": "Intent 類型"
    },
    "scope": {
      "type": "object",
      "required": ["doc_id", "version_id"],
      "properties": {
        "doc_id": {"type": "string"},
        "version_id": {"type": "string"}
      }
    },
    "target": {
      "$ref": "#/$defs/targetSelector"
    },
    "action": {
      "$ref": "#/$defs/action"
    },
    "constraints": {
      "$ref": "#/$defs/constraints"
    },
    "audit": {
      "$ref": "#/$defs/audit"
    }
  },
  "$defs": {
    "targetSelector": {
      "type": "object",
      "required": ["type"],
      "oneOf": [
        {"$ref": "#/$defs/headingSelector"},
        {"$ref": "#/$defs/anchorSelector"},
        {"$ref": "#/$defs/blockSelector"}
      ]
    },
    "headingSelector": {
      "type": "object",
      "required": ["type", "text"],
      "properties": {
        "type": {"const": "heading"},
        "text": {"type": "string"},
        "level": {"type": "integer", "minimum": 1, "maximum": 6},
        "occurrence": {"type": "integer", "minimum": 1},
        "path": {"type": "string", "pattern": "^/[^/]+(/[^/]+)*$"},
        "regex": {"type": "string"}
      }
    },
    "anchorSelector": {
      "type": "object",
      "required": ["type", "value"],
      "properties": {
        "type": {"const": "anchor"},
        "value": {"type": "string"}
      }
    },
    "blockSelector": {
      "type": "object",
      "required": ["type", "block_id"],
      "properties": {
        "type": {"const": "block"},
        "block_id": {"type": "string"}
      }
    },
    "action": {
      "type": "object",
      "required": ["mode", "content_policy"],
      "properties": {
        "mode": {
          "type": "string",
          "enum": ["append", "replace", "inline", "restructure"]
        },
        "content_policy": {
          "type": "string",
          "enum": ["generate", "transform", "remove"]
        }
      }
    },
    "constraints": {
      "type": "object",
      "properties": {
        "max_tokens": {"type": "integer", "minimum": 1, "maximum": 10000},
        "max_chars": {"type": "integer", "minimum": 1},
        "style_guide": {"type": "string"},
        "semantic_drift": {"$ref": "#/$defs/semanticDrift"},
        "no_external_reference": {"type": "boolean"},
        "preserve_existing": {"type": "boolean"},
        "allowed_sections": {"type": "array", "items": {"type": "string"}},
        "forbidden_operations": {"type": "array", "items": {"type": "string"}}
      }
    },
    "semanticDrift": {
      "type": "object",
      "properties": {
        "ner_change_rate_max": {"type": "number", "minimum": 0, "maximum": 1},
        "keywords_overlap_min": {"type": "number", "minimum": 0, "maximum": 1}
      }
    },
    "audit": {
      "type": "object",
      "required": ["requested_by", "reason"],
      "properties": {
        "requested_by": {"type": "string"},
        "reason": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"}
      }
    }
  }
}
```

#### 5.2.3 Intent Type 語義定義

| Intent Type | 語義 | 允許的 action.mode | 允許的 action.content_policy | 說明 |
|------------|------|-------------------|---------------------------|------|
| `insert` | 新增內容 | `append` | `generate` | 在目標位置後新增內容 |
| `update` | 更新現有內容 | `replace`、`inline` | `transform`、`generate` | 修改現有 block 的內容 |
| `delete` | 刪除內容 | - | `remove` | 刪除目標 block（不生成新內容） |
| `refactor` | 重構結構 | `restructure` | `transform` | 僅改變結構（標題層級、block 順序），不改變語義 |
| `summarize` | 摘要內容 | `replace` | `transform` | 將目標內容摘要為更簡潔版本，必須保留核心語義 |

**重要約束**：

- `refactor` 必須保證「不新增語義」：僅允許 move、heading 層級調整，不改變文本內容
- `summarize` 必須使用 `replace` mode，且必須通過語義漂移檢查
- `delete` 不允許 `generate` content_policy
- `insert` 不允許 `remove` content_policy

#### 5.2.4 Target Selector DSL（詳細規範）

Target Selector 為 **可解析表達式**，必須能唯一定位目標 block。

##### 5.2.4.1 Heading Selector

```json
{
  "type": "heading",
  "text": "Architecture Overview",
  "level": 2,
  "occurrence": 1,
  "path": "/Architecture Overview/Data Lake Design"
}
```

**欄位說明**：

- `type`（必需）：固定為 `"heading"`
- `text`（必需）：標題文字（精確匹配）
- `level`（選填）：標題層級（1-6），用於消除歧義
- `occurrence`（選填）：出現次序（從 1 開始），用於處理重複標題
- `path`（選填）：標題路徑，例如 `"/Architecture Overview/Data Lake Design"`，用於唯一定位
- `regex`（選填）：正則表達式模式，用於模糊匹配（不推薦，僅在必要時使用）

**解析規則**：

1. 優先使用 `path` 進行精確匹配（如果提供）
2. 其次使用 `text + level + occurrence` 組合匹配
3. 僅使用 `text` 時，如果存在多個匹配，返回 `TARGET_AMBIGUOUS` 錯誤
4. 解析失敗返回 `TARGET_NOT_FOUND` 錯誤，並在 `details.candidates` 中提供可能的匹配列表

**範例**：

```json
// 精確匹配：使用路徑
{"type": "heading", "path": "/Architecture Overview/Data Lake Design"}

// 組合匹配：文字 + 層級 + 次序
{"type": "heading", "text": "Architecture Overview", "level": 2, "occurrence": 1}

// 簡單匹配（不推薦，可能有歧義）
{"type": "heading", "text": "Architecture Overview"}
```

##### 5.2.4.2 Anchor Selector

```json
{
  "type": "anchor",
  "value": "data-lake-design"
}
```

**Anchor 定義**：

- Anchor 為 HTML `id` 屬性或註解標記（`<!-- anchor: xyz -->`）
- HTML id 格式：由標題自動生成（例如 `## Architecture Overview` → `id="architecture-overview"`）
- 註解標記格式：`<!-- anchor: anchor-name -->`，必須在目標 block 之前
- Anchor 必須唯一，重複 anchor 視為錯誤

**解析規則**：

1. 優先查找 HTML `id` 屬性
2. 其次查找註解標記
3. 解析失敗返回 `TARGET_NOT_FOUND` 錯誤

##### 5.2.4.3 Block Selector

```json
{
  "type": "block",
  "block_id": "block-23"
}
```

**Block ID 定義**：

- Block ID 為系統生成的穩定標識
- 生成算法：`SHA256(content + structural_position)[:16]`（內容雜湊 + 結構位置的前 16 字符）
- 結構位置：`{parent_heading_path}/{block_index_in_section}`
- Block ID 必須持久化到文件元數據中
- Block ID 版本：`block_id_version` 欄位記錄生成算法版本

**解析規則**：

1. 從文件元數據中查找 `block_id`
2. 如果找不到，返回 `TARGET_NOT_FOUND` 錯誤
3. 如果 block_id 格式不合法，返回 `TARGET_SELECTOR_INVALID` 錯誤

##### 5.2.4.4 解析失敗處理

當 Target Selector 無法解析時，必須返回結構化錯誤：

```json
{
  "code": "TARGET_NOT_FOUND",
  "message": "Target selector could not be resolved",
  "details": {
    "selector": {"type": "heading", "text": "Non-existent Section"},
    "candidates": [
      {"type": "heading", "text": "Architecture Overview", "level": 2},
      {"type": "heading", "text": "Data Lake Design", "level": 3}
    ]
  },
  "suggestions": [
    {
      "action": "update_selector",
      "example": {"type": "heading", "text": "Architecture Overview", "level": 2}
    }
  ]
}
```

#### 5.2.5 Action Mode 語義

| Action Mode | 語義 | 適用 Intent Type | 說明 |
|------------|------|-----------------|------|
| `append` | 在目標後新增 | `insert` | 在目標 block 之後插入新內容 |
| `replace` | 完整替換 | `update`、`summarize` | 將目標 block 完全替換為新內容 |
| `inline` | 行內修改 | `update` | 僅修改目標 block 內的特定部分 |
| `restructure` | 重構結構 | `refactor` | 僅改變結構，不改變內容 |

#### 5.2.6 Constraints（約束子語言 - 標準化規範）

Constraints 為 **治理與安全邊界的主要載體**，所有約束必須可機器驗證。

##### 5.2.6.1 長度約束（Length Constraints）

```json
{
  "max_tokens": 300,
  "max_chars": 1500
}
```

- `max_tokens`（選填）：最大 Token 數（使用與 LLM 相同的 tokenizer）
- `max_chars`（選填）：最大字元數（UTF-8 編碼）
- 兩者至少提供一個
- 如果兩者都提供，以較嚴格者為準

**廢棄欄位**：`length: "short | medium | long"` 不再使用（v2.0）

##### 5.2.6.2 樣式指南（Style Guide）

```json
{
  "style_guide": "enterprise-tech-v1"
}
```

- `style_guide`（選填）：樣式指南 ID
- 樣式指南必須映射到可執行的 linter 規則集
- 支援的樣式指南：
  - `"enterprise-tech-v1"`：企業技術文件風格（禁止第一人稱、表格標頭要求、術語表）
  - `"academic-v1"`：學術風格（引用格式、術語一致性）
  - `"casual-v1"`：隨意風格（允許口語化表達）

**檢查規則**：

- 語氣檢查（禁止第一人稱、禁止命令式）
- 術語表檢查（必須使用標準術語，禁止俚語）
- 格式檢查（表格標頭、列表格式）

##### 5.2.6.3 語義漂移（Semantic Drift）

```json
{
  "semantic_drift": {
    "ner_change_rate_max": 0.1,
    "keywords_overlap_min": 0.8
  }
}
```

- `ner_change_rate_max`（選填）：命名實體變更率上限（0-1）
- `keywords_overlap_min`（選填）：關鍵詞集合交集比例下限（0-1）

**檢查邏輯**：

1. 提取原文的命名實體（NER）和關鍵詞
2. 提取生成內容的命名實體和關鍵詞
3. 計算變更率：`changed_entities / total_entities`
4. 計算交集比例：`intersection(keywords_original, keywords_generated) / union(keywords_original, keywords_generated)`
5. 如果超出限制，返回 `CONSTRAINT_VIOLATION` 錯誤

**簡化形式**：

```json
{
  "semantic_drift": "disallow"
}
```

等同於：

```json
{
  "semantic_drift": {
    "ner_change_rate_max": 0.0,
    "keywords_overlap_min": 1.0
  }
}
```

##### 5.2.6.4 外部參照（External Reference）

```json
{
  "no_external_reference": true
}
```

- `no_external_reference`（選填，預設 `false`）：是否禁止外部參照

**檢查規則**：

1. 禁止外部 URL（`http://`、`https://`、`ftp://`）
2. 禁止引用未在上下文中提及的事實
3. 允許引用文件內其他章節（`[Section Name](#anchor)`）
4. 允許引用已提供的上下文資料

##### 5.2.6.5 其他約束

```json
{
  "preserve_existing": true,
  "allowed_sections": ["Architecture Overview", "Data Lake Design"],
  "forbidden_operations": ["delete"]
}
```

- `preserve_existing`（選填）：是否保留現有內容（適用於 `update` intent）
- `allowed_sections`（選填）：允許編輯的章節列表
- `forbidden_operations`（選填）：禁止的操作列表

#### 5.2.7 Intent → Patch 映射規則

```
Edit Intent DSL
      ↓ (validated)
Semantic Patch (optional)
      ↓
Block Patch (mandatory)
      ↓
Text Patch (compatible)
```

DEA 必須能說明：

- 每一個 Block Patch 來自哪一個 Intent（通過 `intent_id` 欄位）
- 每一個 Intent 產生了哪些結構變更

#### 5.2.8 Intent Versioning（DSL 演進）

```json
{
  "intent_schema_version": "2.0"
}
```

- 不同版本 DSL 可並存
- DEA 需具備向後相容能力（支援 v1.0 和 v2.0）
- 版本號遵循語義化版本（Semantic Versioning）

---

## 6. Patch / Diff Model

本系統中的 Patch 不僅是文字差異，而是 **可治理、可語義理解的變更單元**。Patch 為 DEA 對外唯一輸出成果。

Patch 分為三個層級，由低到高：

1. Text Patch（文字層）
2. Block Patch（結構層）
3. Semantic Patch（語義層，進階）

### 6.1 Text Patch（Unified Diff）

**適用場景**：

- 與 Git / SCM 相容
- 最終存儲、審計、回滾

**格式規範**：

使用標準 Unified Diff 格式（與 `git diff` 相容）：

```
@@ -12,6 +12,18 @@ section header
 原有內容
 更多原有內容
+新增內容第一行
+新增內容第二行
 原有內容繼續
```

**特性**：

- 不理解 Markdown 結構
- 僅作為最低層輸出格式
- 不建議用於編輯邏輯判斷
- 必須包含上下文行（context lines，預設 3 行）

**規範要求**：

- 必須使用 UTF-8 編碼
- 行號從 1 開始
- 必須包含檔案路徑標頭（`--- a/path`、`+++ b/path`）

### 6.2 Block Patch（結構化 Patch，核心）

Block Patch 為 DEA 的 **主要內部與對外建議格式**，基於 Markdown AST / Block。

#### 6.2.1 Block Patch Schema

```json
{
  "$schema": "https://schema.aibox.com/block-patch/v2.0",
  "patch_type": "block",
  "patch_id": "PATCH-20260109-001",
  "doc_id": "DOC-20260109-0001",
  "base_version": "v3",
  "intent_id": "INTENT-20260109-001",
  "generated_at": "2026-01-09T10:30:00Z",
  "generated_by": "dea-v2.0",
  "model_version": "gpt-4-turbo-preview-2026-01-09",
  "context_digest": "sha256:abc123...",
  "operations": [
    {
      "op": "insert",
      "target_selector": {
        "type": "heading",
        "text": "Architecture Overview",
        "level": 2
      },
      "position": "after",
      "content": "### Data Lake Design\n\nData Lake 採用...",
      "metadata": {
        "created_at": "2026-01-09T10:30:00Z",
        "created_by": "dea-v2.0",
        "intent_id": "INTENT-20260109-001"
      }
    }
  ]
}
```

#### 6.2.2 Operation Schema

```json
{
  "op": "insert | update | delete | move | replace",
  "target_selector": { /* Target Selector 物件 */ },
  "position": "before | after | inside | start | end",
  "content": "markdown subtree | null",
  "source_selector": { /* 僅 move 操作需要 */ },
  "metadata": {
    "created_at": "ISO 8601 timestamp",
    "created_by": "agent-version",
    "intent_id": "INTENT-xxx"
  }
}
```

**Operation 類型說明**：

- `insert`：在目標位置後插入新內容
  - 需要：`target_selector`、`position`、`content`
- `update`：更新目標 block 的內容
  - 需要：`target_selector`、`content`
  - `position` 固定為 `"inside"`
- `delete`：刪除目標 block
  - 需要：`target_selector`
  - `content` 為 `null`
- `move`：移動 block 到新位置
  - 需要：`source_selector`、`target_selector`、`position`
  - `content` 為 `null`（使用源 block 的內容）
- `replace`：完整替換目標 block
  - 需要：`target_selector`、`content`
  - `position` 固定為 `"inside"`

**Position 說明**：

- `before`：在目標 block 之前
- `after`：在目標 block 之後
- `inside`：在目標 block 內部（適用於 update、replace）
- `start`：在目標 block 的開始處（適用於 insert）
- `end`：在目標 block 的結束處（適用於 insert）

#### 6.2.3 Block Patch 規範要求

- 每個 Block Patch 必須可轉換為 Text Patch
- 轉換失敗視為驗證失敗（返回 `PATCH_CONVERSION_FAILED` 錯誤）
- 每個 Operation 必須可獨立 revert（原子性）
- Block Patch 必須包含完整的審計資訊（`generated_at`、`generated_by`、`model_version`、`context_digest`）

### 6.3 Semantic Patch（語義 Patch，進階）

Semantic Patch 描述的是「**意圖造成的語義變更**」，而非實際文字。

```json
{
  "patch_type": "semantic",
  "intent_id": "INTENT-20260109-001",
  "effect": "expand_section",
  "target": "Architecture Overview",
  "summary": "補充資料湖與 ETL 流程設計",
  "generated_blocks": ["block-23", "block-24"],
  "semantic_changes": {
    "added_concepts": ["Data Lake", "ETL Pipeline"],
    "preserved_concepts": ["Architecture", "Design"]
  }
}
```

**用途**：

- 高階審計 / 人類 Review
- 作為長期知識演化記錄
- 私有模型微調資料

**規範要求**：

- Semantic Patch 為選配但強烈建議
- 如果提供，必須與 Block Patch 保持一致

### 6.4 Patch 轉換關係

```
Semantic Patch
      ↓
Block Patch  ←（DEA 核心產物）
      ↓
Text Patch (unified diff)
```

**規範要求**：

- DEA 至少必須輸出 Block Patch
- Text Patch 為必要相容層（必須可轉換）
- Semantic Patch 為選配但強烈建議
- 轉換過程必須可逆（Text Patch → Block Patch 可能損失結構資訊，但 Block Patch → Text Patch 必須完整）

---

## 7. LLM 生成行為與可重現策略

### 7.1 可重現性要求

DEA 必須保證同一 Intent 在相同上下文下結果可重現（Determinism）。

### 7.2 固定配置

**必須固定的參數**：

```json
{
  "model_version": "gpt-4-turbo-preview-2026-01-09",
  "temperature": 0.0,
  "top_p": 1.0,
  "seed": 12345,
  "max_tokens": 1000,
  "presence_penalty": 0.0,
  "frequency_penalty": 0.0
}
```

**配置說明**：

- `model_version`（必需）：固定的模型版本（包含版本號和日期）
- `temperature`（必需）：固定為 `0.0`（禁用隨機性）
- `top_p`（必需）：固定為 `1.0`
- `seed`（選填）：隨機種子（如果模型支援）
- `max_tokens`（必需）：最大生成 Token 數
- `presence_penalty`、`frequency_penalty`（必需）：固定為 `0.0`

**禁止使用的特性**：

- 禁止使用不確定性特性（如 `logit_bias` 的動態調整）
- 禁止使用 stream 模式（必須等待完整響應）
- 禁止使用不確定性的採樣策略

### 7.3 最小上下文策略

**原則**：DEA 不得讀取全文，僅使用最小必要的上下文。

**上下文裝配策略**：

1. **目標 Block**：目標 block 及其直接子 block
2. **祖先 Heading**：向上抓取 n 個祖先 heading（預設 n=2，可配置）
3. **相鄰 Block**：向下抓取 m 個相鄰 block（預設 m=3，可配置）
4. **可配置上限**：`max_context_blocks`（預設 50 blocks）

**配置參數**：

```json
{
  "context_strategy": {
    "include_ancestors": 2,
    "include_siblings": 3,
    "max_context_blocks": 50,
    "include_section_boundary": true
  }
}
```

**上下文摘要**：

- 對最小上下文計算雜湊（SHA-256）：`context_digest`
- `context_digest` 必須包含在 Block Patch 的 `metadata` 中
- 用於審計和可重現性驗證

### 7.4 輸出校驗流程

生成內容必須通過以下檢查（按順序執行）：

1. **結構檢查**：Markdown 語法正確性
2. **長度檢查**：符合 `max_tokens` / `max_chars` 約束
3. **樣式檢查**：符合 `style_guide` 規則
4. **語義漂移檢查**：符合 `semantic_drift` 指標
5. **外部參照檢查**：符合 `no_external_reference` 約束

**檢查失敗處理**：

- 如果任何檢查失敗，返回 `CONSTRAINT_VIOLATION` 錯誤
- 錯誤訊息必須包含具體的違規項目和修正建議
- 不允許「部分通過」或「降級處理」

---

## 8. 內部模組架構

### 8.1 模組分解

```
Document Editing Agent
 ├── Intent Validator
 ├── Markdown Parser (AST)
 ├── Target Locator
 ├── Context Assembler
 ├── Content Generator (LLM-bound)
 ├── Patch Generator
 ├── Validator & Linter
 ├── Audit Logger
```

### 8.2 模組職責說明

#### Intent Validator

- 驗證 Intent schema 合法性（使用 JSON Schema）
- 檢查 Intent Type 與 Action Mode 的相容性
- 檢查是否超出允許編輯範圍
- 驗證 Constraints 的格式和有效性

#### Markdown Parser

- 將 md 轉為 AST / Block 結構
- 保留 heading hierarchy、block 結構、inline 結構
- 生成 Block ID（如果尚未生成）
- 驗證 Markdown 語法正確性

#### Target Locator

- 根據 Target Selector 定位目標 block
- 支援 heading / anchor / block 三種選擇器
- 處理歧義情況（返回候選列表）
- 驗證目標 block 的存在性和可編輯性

#### Context Assembler

- 根據最小上下文策略裝配上下文
- 計算 `context_digest`
- 優化上下文大小（不超過 `max_context_blocks`）

#### Content Generator

- 僅在「指定上下文 + 約束」下生成內容
- 使用固定 LLM 配置（temperature=0、固定模型版本）
- 調用 LLM API 生成內容
- 記錄生成參數（用於審計）

#### Patch Generator

- 產生 Block Patch（主要格式）
- 產生 Text Patch（unified diff）
- 產生 Semantic Patch（選配）
- 確保 Patch 的原子性和可回滾性

#### Validator & Linter

- Markdown 結構檢查（標題階層連續性、禁止空標題、禁止重複 id）
- 樣式檢查（`style_guide` 規則）
- 長度檢查（`max_tokens` / `max_chars`）
- 語義漂移檢查（`semantic_drift` 指標）
- 外部參照檢查（`no_external_reference`）

#### Audit Logger

- 記錄所有編輯事件（intent_validated、target_located、content_generated、patch_built、patch_validated、patch_returned）
- 記錄耗時和資源使用
- 存儲 Patch 與 Intent 的關聯
- 生成審計日誌（不可變、含雜湊）

---

## 9. 標準執行流程（Happy Path）

```
接收 DocumentContext + Edit Intent
 ↓
Intent Validator（驗證 Schema 與相容性）
 ↓
Parse Markdown → AST（生成 Block ID）
 ↓
Target Locator（定位目標 Block）
 ↓
Context Assembler（裝配最小上下文）
 ↓
Content Generator（LLM 生成內容）
 ↓
Output Validator（校驗生成內容）
 ↓
Patch Generator（生成 Block Patch + Text Patch）
 ↓
Patch Validator（驗證 Patch 完整性）
 ↓
Audit Logger（記錄審計資訊）
 ↓
Return Patch + Preview + Audit Info
```

**錯誤處理**：

- 任何步驟失敗，立即返回對應錯誤碼
- 不允許部分執行或降級處理
- 錯誤訊息必須包含修正建議

---

## 10. 失敗與拒絕策略

### 10.1 錯誤碼清單

DEA 必須在以下情況 **主動拒絕執行**，並返回對應錯誤碼：

| 錯誤碼 | HTTP 狀態碼 | 說明 | 可修正建議 |
|--------|------------|------|-----------|
| `INTENT_SCHEMA_INVALID` | 400 | Intent Schema 不合法 | 檢查 JSON Schema 格式 |
| `INTENT_TYPE_INCOMPATIBLE` | 400 | Intent Type 與 Action Mode 不相容 | 參考相容性矩陣 |
| `TARGET_NOT_FOUND` | 404 | 目標 Selector 無法解析 | 檢查 selector 語法，查看候選列表 |
| `TARGET_AMBIGUOUS` | 400 | 目標 Selector 存在多個匹配 | 使用更精確的 selector（加入 level、occurrence、path） |
| `TARGET_SELECTOR_INVALID` | 400 | Target Selector 格式不合法 | 檢查 selector 類型與欄位 |
| `CONSTRAINT_VIOLATION` | 400 | 生成內容違反約束 | 檢查具體違規項目（結構、長度、樣式、語義漂移、外部參照） |
| `STRUCTURE_BREAK` | 400 | Patch 將破壞文件結構 | 檢查 Patch 操作是否合法 |
| `SECURITY_DENIED` | 403 | 安全檢查失敗 | 檢查權限與授權 |
| `CONTEXT_EXCEEDS_LIMIT` | 400 | 上下文超出限制 | 調整 `max_context_blocks` 或簡化目標 |
| `PATCH_CONFLICT` | 409 | Patch 與現有內容衝突 | 檢查文件是否已被修改 |
| `PATCH_CONVERSION_FAILED` | 500 | Block Patch 轉換為 Text Patch 失敗 | 內部錯誤，需修復 |
| `LLM_GENERATION_FAILED` | 500 | LLM 生成失敗 | 檢查 LLM API 狀態 |
| `VERSION_MISMATCH` | 409 | 版本不匹配 | 檢查 `version_id` 是否為最新 |
| `EDITABILITY_DENIED` | 403 | 文件不可編輯 | 檢查 `editability_state` |

### 10.2 錯誤回傳格式

```json
{
  "success": false,
  "error": {
    "code": "TARGET_NOT_FOUND",
    "message": "Target selector could not be resolved",
    "details": {
      "selector": {
        "type": "heading",
        "text": "Non-existent Section"
      },
      "candidates": [
        {
          "type": "heading",
          "text": "Architecture Overview",
          "level": 2,
          "path": "/Architecture Overview"
        },
        {
          "type": "heading",
          "text": "Data Lake Design",
          "level": 3,
          "path": "/Architecture Overview/Data Lake Design"
        }
      ]
    },
    "suggestions": [
      {
        "action": "update_selector",
        "example": {
          "type": "heading",
          "text": "Architecture Overview",
          "level": 2
        },
        "description": "使用更精確的 selector，加入 level 欄位"
      }
    ]
  },
  "timestamp": "2026-01-09T10:30:00Z",
  "request_id": "req-123456"
}
```

### 10.3 拒絕策略

DEA 必須在以下情況 **主動拒絕執行**：

- Intent 無法解析或超出權限
- 目標章節不存在且不允許自動建立
- Patch 將破壞文件結構
- 生成內容違反約束（風格 / 長度 / 規範 / 語義漂移）
- 上下文超出限制
- 安全檢查失敗
- 版本不匹配

**回傳結果必須包含**：

- 拒絕原因（Machine-readable 錯誤碼）
- 錯誤詳情（`details` 物件）
- 可修正建議（`suggestions` 陣列，選填但強烈建議）

---

## 11. 觀測性與審計

### 11.1 事件模型

DEA 必須記錄以下事件（按時間順序）：

| 事件名稱 | 說明 | 記錄欄位 |
|---------|------|---------|
| `intent_received` | 接收到 Intent | `intent_id`、`timestamp`、`actor_id` |
| `intent_validated` | Intent 驗證完成 | `intent_id`、`validation_result`、`duration_ms` |
| `target_located` | 目標定位完成 | `intent_id`、`target_selector`、`target_block_id`、`duration_ms` |
| `context_assembled` | 上下文裝配完成 | `intent_id`、`context_digest`、`context_size_blocks`、`duration_ms` |
| `content_generated` | 內容生成完成 | `intent_id`、`model_version`、`tokens_used`、`duration_ms` |
| `output_validated` | 輸出校驗完成 | `intent_id`、`validation_result`、`duration_ms` |
| `patch_built` | Patch 構建完成 | `intent_id`、`patch_id`、`patch_type`、`operations_count`、`duration_ms` |
| `patch_validated` | Patch 驗證完成 | `patch_id`、`validation_result`、`duration_ms` |
| `patch_returned` | Patch 返回完成 | `patch_id`、`total_duration_ms` |

### 11.2 審計存儲

**Patch 與 Intent 關聯**：

- 每個 Patch 必須包含 `intent_id`
- 每個 Intent 可以對應多個 Patch（如果拆分為多個操作）
- 關聯關係必須持久化到審計存儲

**不可變存儲**：

- Patch 與 Intent 必須以不可變方式存儲
- 每個記錄必須包含雜湊（SHA-256）
- 建議使用簽章（Digital Signature）確保完整性

**存儲結構**：

```json
{
  "patch_id": "PATCH-20260109-001",
  "intent_id": "INTENT-20260109-001",
  "doc_id": "DOC-20260109-0001",
  "version_id": "v3",
  "patch_content": { /* Block Patch JSON */ },
  "patch_hash": "sha256:abc123...",
  "patch_signature": "sig:xyz789...",
  "generated_at": "2026-01-09T10:30:00Z",
  "generated_by": "dea-v2.0",
  "model_version": "gpt-4-turbo-preview-2026-01-09",
  "context_digest": "sha256:def456...",
  "events": [ /* 事件列表 */ ]
}
```

### 11.3 SLA 指標

**性能指標**：

- 單次編輯延遲：< 可配置 SLA（預設 30 秒）
- Intent 驗證延遲：< 100ms
- 目標定位延遲：< 200ms
- 上下文裝配延遲：< 300ms
- LLM 生成延遲：< 可配置 SLA（預設 20 秒）
- Patch 構建延遲：< 500ms

**超時策略**：

- 如果 LLM 生成超時，返回 `LLM_GENERATION_FAILED` 錯誤
- 不允許分段編輯或部分結果
- 超時必須記錄到審計日誌

---

## 12. 併發編輯與整合

### 12.1 併發編輯策略

**樂觀鎖（Optimistic Locking）**：

- DEA 不直接處理併發編輯衝突
- 使用 `version_id` 進行版本檢查
- 如果 `version_id` 不匹配，返回 `VERSION_MISMATCH` 錯誤
- 衝突解決由 Version Controller 負責

**鎖定模式（Locking Mode）**：

- DEA 不實作文件鎖定
- 鎖定由 Version Controller 或 Document Registry 處理
- DEA 僅檢查 `editability_state`（如果為 `"locked"`，返回 `EDITABILITY_DENIED` 錯誤）

### 12.2 多 Intent 序列化

**線性拆解規則**：

- 多個 Intent 必須線性拆解為獨立 Patch
- 每個 Patch 必須可獨立執行
- 執行順序必須明確（按 Intent 順序）

**目標偏移處理**：

- 如果前一個 Patch 改變了文件結構，後續 Patch 的目標位置可能偏移
- 解決方案：在生成第二個 Patch 前，套用第一個 Patch 的模擬（dry-run），更新目標定位
- 或：使用 Block ID 而非位置索引（Block ID 不隨結構變更而改變）

### 12.3 與版本控制的交互

**交互流程**：

1. DEA 接收 Intent，生成 Patch
2. DEA 返回 Patch + Preview（不直接提交）
3. Version Controller 接收 Patch，進行衝突檢查
4. Version Controller 合併 Patch（如果需要）
5. Version Controller 提交變更（或拒絕）

**DEA 職責邊界**：

- DEA 僅負責生成 Patch
- DEA 不負責衝突解決
- DEA 不負責最終提交
- DEA 可以提供 Preview（預覽變更後的內容）

---

## 13. 安全治理

### 13.1 權限模型

**權限檢查**：

- DEA 必須檢查 `permission_scope`（來自 DocumentContext）
- 最低權限要求：`["read", "edit"]`
- 如果權限不足，返回 `SECURITY_DENIED` 錯誤

**權限範圍映射**：

| 操作 | 所需權限 |
|------|---------|
| `insert`、`update` | `["read", "edit"]` |
| `delete` | `["read", "edit", "delete"]` |
| `refactor`、`summarize` | `["read", "edit"]` |

### 13.2 資料洩漏防範

**Prompt 注入防範**：

- 禁止外部連結生成（如果 `no_external_reference: true`）
- 檢查生成內容是否包含敏感資訊（PII、保密資訊）
- 使用內容過濾器（Content Filter）掃描生成內容

**上下文洩漏防範**：

- 最小上下文策略（不讀取全文）
- 上下文摘要記錄（`context_digest`）用於審計
- 禁止在生成內容中引用未提供的上下文

**敏感資訊檢測**：

- 檢查生成內容是否包含 PII（個人識別資訊）
- 檢查是否包含保密資訊（關鍵字掃描）
- 如果檢測到敏感資訊，返回 `SECURITY_DENIED` 錯誤（可選：記錄警告）

### 13.3 審計與合規

**審計要求**：

- 所有編輯操作必須記錄到審計日誌
- 審計日誌必須包含：`actor_id`、`intent_id`、`patch_id`、`timestamp`、`action_type`、`target_selector`
- 審計日誌必須不可變、含雜湊、可追溯

**合規要求**：

- 符合資料保護法規（GDPR、個資法等）
- 符合企業安全政策
- 支援資料分類標籤（`data_classification`、`sensitivity_labels`）

---

## 14. 與其他系統的介面

### 14.1 與 Orchestrator

**輸入契約**：

- 輸入：`DocumentContext + Edit Intent`
- 格式：JSON（符合 DocumentContext 和 Edit Intent Schema）
- 認證：通過 API Key 或 Token

**輸出契約**：

- 成功：`PatchResponse`（包含 Block Patch + Text Patch + Preview + Audit Info）
- 失敗：`ErrorResponse`（包含錯誤碼、錯誤詳情、修正建議）

**接口規範**：

```json
POST /api/v1/document-editing-agent/edit
Content-Type: application/json
Authorization: Bearer <token>

{
  "document_context": { /* DocumentContext */ },
  "edit_intent": { /* Edit Intent */ }
}

Response 200 OK:
{
  "success": true,
  "patch": { /* Block Patch */ },
  "text_patch": "--- a/file.md\n+++ b/file.md\n...",
  "preview": "預覽內容（選填）",
  "audit_info": { /* 審計資訊 */ }
}

Response 4xx/5xx:
{
  "success": false,
  "error": { /* ErrorResponse */ }
}
```

### 14.2 與 Version Controller

**交互方式**：

- DEA 不直接寫檔
- DEA 僅回傳 Patch
- Version Controller 負責接收 Patch、檢查衝突、合併、提交

**Patch 提交接口**：

- 由 Version Controller 提供
- DEA 不直接調用
- 如果需要，DEA 可以提供 Preview 供 Version Controller 使用

### 14.3 與 RAG / GraphRAG（間接）

**使用規則**：

- DEA 不自行決定資料來源
- 僅在 Intent 指示且授權下使用外部資料
- 外部資料必須由 Orchestrator 提供（作為上下文的一部分）
- DEA 不直接調用 RAG / GraphRAG API

---

## 15. 非功能性需求（NFR）

### 15.1 Determinism（可重現性）

- **要求**：同一 Intent 在相同上下文下結果可重現
- **實作**：固定模型版本、temperature=0、固定種子、標準化前處理與後處理
- **驗證**：使用 `context_digest` 驗證上下文一致性

### 15.2 Latency（延遲）

- **要求**：單次編輯 < 可配置 SLA（預設 30 秒）
- **測量**：從接收 Intent 到返回 Patch 的總時間
- **優化**：最小上下文策略、並行處理（如果可能）、快取（如果適用）

### 15.3 Observability（觀測性）

- **要求**：完整 log / trace / patch history
- **實作**：結構化日誌、事件追蹤、審計存儲
- **工具**：支援 OpenTelemetry、Prometheus metrics、分散式追蹤

### 15.4 Extensibility（可擴展性）

- **要求**：可支援其他格式（如 AsciiDoc）
- **實作**：抽象化 Markdown Parser、支援多種 AST 格式
- **當前範圍**：僅支援 Markdown（v2.0）

### 15.5 Reliability（可靠性）

- **要求**：高可用性（99.9% uptime）
- **實作**：錯誤處理、重試機制（適用於 LLM API 調用）、降級策略（如果可能）
- **監控**：健康檢查端點、錯誤率監控、延遲監控

---

## 16. 最小可行版本（MVP）路線

### 16.1 MVP 範圍定義

**支援的功能**：

1. ✅ **Markdown 標準**：CommonMark + GFM（表格、任務清單、程式碼區塊）
2. ✅ **Target Selector**：僅支援 heading 精確匹配（text + level + occurrence），不含 anchor；block id 使用臨時位置位址方案
3. ✅ **Intent Type**：僅支援 `insert`、`update`、`delete`；`summarize`、`refactor` 延後
4. ✅ **Constraints**：僅執行 `max_tokens`、`no_external_reference`、`style_guide` 的基本 lint
5. ✅ **LLM 配置**：temperature=0，固定模型版本；最小上下文只包含目標 section 與上一層父節點內容
6. ✅ **Patch 輸出**：Block Patch + Text Patch；提供預覽片段
7. ✅ **錯誤處理**：完整錯誤碼與回傳格式；基本審計欄位（intent_id、patch_id、model_version、context_digest）

**不支援的功能（未來版本）**：

- ❌ Anchor Selector
- ❌ Block ID 持久化（使用臨時方案）
- ❌ `summarize`、`refactor` Intent Type
- ❌ Semantic Drift 檢查（指標化）
- ❌ Style Guide 完整規則集
- ❌ Semantic Patch 輸出
- ❌ 併發編輯鎖定機制
- ❌ 進階安全檢查（PII 檢測）

### 16.2 MVP 實作優先級

**P0（必要，直接影響可用性）**：

1. Markdown 標準與 AST 解析策略
2. Target Selector 可唯一定位（heading 精確匹配）
3. Intent DSL JSON Schema 與錯誤碼設計
4. Block Patch schema 與 Text Patch 轉換流程
5. LLM 最小上下文策略與可重現配置
6. 驗證與 Linter 基本規則（結構、長度、禁止外部參照）

**P1（提高品質與治理）**：

1. Semantic Drift 指標化與檢查器
2. Style Guide 規則集與術語表
3. 觀測性與審計事件模型、簽章與雜湊
4. 併發編輯鎖與 rebase 機制

**P2（進階能力）**：

1. Semantic Patch 的詳細定義與輸出
2. Refactor 的機器驗證邏輯
3. GraphRAG / 外部資料使用的授權與審計

### 16.3 MVP 驗證標準

**功能驗證**：

- ✅ 可以成功解析 CommonMark + GFM Markdown
- ✅ 可以精確定位 heading target
- ✅ 可以生成合法的 Block Patch 和 Text Patch
- ✅ 可以驗證生成內容的結構、長度、外部參照
- ✅ 可以重現相同的編輯結果（使用相同的 Intent 和上下文）

**性能驗證**：

- ✅ 單次編輯延遲 < 30 秒（P95）
- ✅ Intent 驗證延遲 < 100ms
- ✅ 目標定位延遲 < 200ms

**可靠性驗證**：

- ✅ 錯誤處理正確（返回對應錯誤碼）
- ✅ 審計日誌完整（包含所有必要欄位）
- ✅ Patch 可回滾（Block Patch → Text Patch → 原始文件）

---

## 17. 總結

文件編輯 Agent 並非寫作工具，而是：

> 一個在治理框架內，執行可控、可追溯、可演進的「知識資產變更引擎」。

它的價值不在於生成能力，而在於 **結構、邊界與責任劃分**。

**v2.0 版本的關鍵改進**：

1. ✅ 明確了 Markdown 標準與支援範圍（CommonMark + GFM）
2. ✅ 詳細規範了 Target Selector DSL（heading/anchor/block 的唯一定位）
3. ✅ 標準化了 Constraints（可機器驗證的量化指標）
4. ✅ 完整化了 Patch 規範（Block Patch operation schema、Text Patch 格式）
5. ✅ 定義了 LLM 可重現策略（固定配置、最小上下文）
6. ✅ 補充了錯誤碼清單與回傳格式
7. ✅ 建立了觀測性與審計事件模型
8. ✅ 說明了併發編輯與整合策略
9. ✅ 加強了安全治理規範
10. ✅ 提供了 MVP 路線與優先級

**下一步行動**：

1. 根據 MVP 範圍開始實作 P0 項目
2. 建立 JSON Schema 驗證機制
3. 實作 Markdown Parser（CommonMark + GFM）
4. 實作 Target Locator（heading 精確匹配）
5. 實作 LLM Content Generator（固定配置、最小上下文）
6. 實作 Patch Generator（Block Patch + Text Patch）
7. 實作 Validator & Linter（基本規則）
8. 實作錯誤處理與審計日誌

---

**文件版本**: v2.0
**最後更新日期**: 2026-01-11
**維護人**: Daniel Chung
