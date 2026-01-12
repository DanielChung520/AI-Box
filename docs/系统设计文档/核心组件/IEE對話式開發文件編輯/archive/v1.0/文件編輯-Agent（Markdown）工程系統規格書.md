# 文件編輯 Agent（Markdown）工程系統規格書

<!-- Notion Page ID: 2e310eba-142a-8005-99a3-d8585bc3229e -->
<!-- Last synced: 2026-01-11T02:07:23.453Z -->

---

> 本文件為 工程實作導向 的系統規格（Engineering Specification），定義「文件編輯 Agent」在整體 Agent Orchestration 架構中的 職責、邊界、介面與流程。本 Agent 不負責任務理解與能力調度，僅在合法授權下，執行受控、可審計的 Markdown 文件編輯行為。
---

## 1. 系統定位與設計原則

![image](https://prod-files-secure.s3.us-west-2.amazonaws.com/70f756a7-bfe3-41a8-8231-b3a870987d51/7762433c-d1fd-40ad-876c-e2ab31f30939/image.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466757KAAH2%2F20260111%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260111T020711Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEAEaCXVzLXdlc3QtMiJHMEUCIGDLxWQ1zPtrfWPP%2FOXJAGG2qGcorAzZfJiww4lQ%2FQSbAiEA7pgUAK5z2j78tn%2FqqPD%2FyoW4OZ%2FjltfbkYNn5haxg%2BIqiAQIyv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2Mzc0MjMxODM4MDUiDNmUYfdRXFRAZTa2jCrcA4kz3proChI1aBKHkxUIiFFuEeiqD07OLkI1A6rvOuTahEu2ZzT5wY3Fd3LzpZQxYaWT%2FXEMRSzLwfOnkIayThahLKArtUHuuM6V%2Bl31ospcDa9uSRtuPD7TC%2FL7Zun46qUPhjghO8lwovDY0Hv%2Fokz5bjtV3kfn2NoiLTi%2FvoJy0XGyhAqS%2BjIuY3iRUnct7su6lhRdUyH5S56Zk0pDxmaSFUzEU1bgDezsVxLhmTa%2F5Z9cfSYAJMt7NJ9iIC18RWpN2OZ3sdrvLA4fWdfmhrwnHyPSW4iHHFcITSdgXyVUjegCoYncqMLycwFCJx%2BJB3VNYMOJUGT1fAro0pTvrLK%2BaA3l5mTDFpLCqTcbI6t9uP1%2FyMExcDIPQ3D56QfifOfzjuiuAlPTG2PqyqwlCVAHyKIw9zLErBdeaTSqruJgrvTFM1xr19s%2Bs4xb37tRbG%2Batn1MRSUeFdNLNLjwTp3fR4srVboGjtySjVMQ98tQ%2BUeQoDKj3zYkD1hWqaDeQgWqJUB0nlAT0yXakEY0LLT%2B89EfU%2BRLpvqF3APl335gTu55uw%2FAsfvRCGBzYPsJdZDRbDmQJ0LTUyATr1jNatwdLSVFS0nVOIlginPGT%2Fxtjr%2FlomDpPOZwbi1NMKzti8sGOqUBOeum%2BiRJX1HaaLT5bzvjpcTNqKZhPVXG%2BXVM77Mss%2Ben67wC%2BSvfmFkVK7FZ93%2FVmeAf9%2FWGGs3hfy6GYfXolICS6n5yOWft22%2FhigxYDSr0lHM8T1xetZzUfhVqK89P61Q8WUmQK1b2Gq5YSj4ZwFuR0XTFGIlri542c%2BdDVmdHQ5oKrHHKmifUsTxjvjZBD8pImdaxcEt%2BJC2KzWdDfraF%2B4lF&X-Amz-Signature=a378e341ba47af8b60dcd15c6a270d7d1d05b2d7733a639761da349435c6299a&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)

### 1.1 系統定位

文件編輯 Agent（以下簡稱 DEA, Document Editing Agent）屬於：- **Domain Execution Layer Agent**

- 專職處理 **Markdown 文件的結構化編輯**
- 永遠在 **Orchestrator Agent 授權之後** 才能被調用
其角色是：> 在既定文件（DocID）與既定版本基礎上，根據明確的編輯意圖（Intent），產生可驗證、可回滾的內容變更（Patch / Diff）。

---

### 1.2 核心設計原則

1. **Document ≠ File**
文件是一個具備生命週期、版本與治理規則的「知識物件」，而非單一檔案。1. **Edit ≠ Generate**
所有編輯行為必須以 Patch / Delta 形式表達，而非直接覆寫全文。1. **Intent-driven Editing**
編輯必須由結構化 Intent 觸發，而非自然語言即時生成。1. **Governance-first**
無 DocID、無合法版本狀態，不得編輯。1. **Auditable & Deterministic**
每一次編輯行為皆可追溯來源、原因與影響範圍。---

## 2. 系統邊界（Scope Definition）

### 2.1 DEA 負責的事項（IN SCOPE）

- Markdown 文件解析（AST / Block Level）
- 編輯意圖（Edit Intent）解析與驗證
- 編輯位置定位（章節 / Block / Anchor）
- Patch / Diff 生成
- 編輯後文件重組
- 編輯結果驗證（結構 / 約束）

---

### 2.2 DEA 明確不負責的事項（OUT OF SCOPE）

- 任務意圖理解（由 Orchestrator 負責）
- 文件註冊 / DocID 生成
- 版本授權與合法性裁決
- 使用者權限與安全稽核
- 模型資源選擇（MoE）
- 文件最終提交與發布

---

## 3. 系統前置條件（Preconditions）

DEA 在被呼叫前，**必須已滿足以下條件**：1. Orchestrator 已判定此任務為「文件編輯任務」

1. Document Registry 已存在合法 DocID
1. 目標文件處於可編輯狀態（draft / editing）
1. 已建立可寫入的新版本（Version Context）
1. 已完成必要的 Security / Audit 授權
若任一條件不成立，DEA **必須拒絕執行**。---

## 4. 核心資料模型

### 4.1 Document Context

```plain text
DocumentContext
- doc_id
- task_id
- current_version_id
- file_path
- format: markdown

```

---

### 4.2 Edit Intent（編輯意圖）

Edit Intent 為 **文件編輯 Agent 的核心控制語言（DSL）**，用以描述「**允許被執行的編輯行為**」，而非生成提示。Edit Intent DSL 的設計目標是：- 可機器驗證（Machine-validatable）

- 可治理（Governance-aware）
- 可演進（Versionable / Extensible）
- 可作為模型訓練與審計資料

---

### 4.2.1 設計原則（DSL Design Principles）

1. **Intent ≠ Prompt**
DSL 不描述「怎麼寫」，只描述「要改什麼、改到哪裡、允許怎麼改」。1. **Declarative First**
Intent 為宣告式語言，不包含流程控制（if / loop）。1. **Bounded Action Space**
每一個 Intent 都映射到有限的 Patch Operation。1. **Composable but Restricted**
可組合多個 Intent，但必須可線性拆解為獨立 Patch。---

### 4.2.2 Edit Intent DSL 基本結構

```json
{
  "intent_id": "INTENT-20260109-001",
  "intent_type": "insert | update | delete | refactor | summarize",
  "scope": {
    "doc_id": "DOC-20260109-0001",
    "version_id": "v3"
  },
  "target": {
    "selector": "heading | block | anchor",
    "expression": "## Architecture Overview"
  },
  "action": {
    "mode": "append | replace | inline | restructure",
    "content_policy": "generate | transform | remove"
  },
  "constraints": {
    "style": "technical",
    "length": "short | medium | long",
    "preserve_existing": true,
    "allowed_sections": ["Architecture Overview"],
    "forbidden_operations": ["delete"]
  },
  "audit": {
    "requested_by": "orchestrator-agent",
    "reason": "expand architecture documentation"
  }
}

```

---

### 4.2.3 Intent Type 語義定義

<!-- Table: 2e310eba-142a-8020-b2b3-deb41e4ed30e -->
> 規範：DEA 不得自行升級 intent_type。
---

### 4.2.4 Target Selector DSL

Target 為 **可解析表達式**，而非模糊描述。```plain text
heading("Architecture Overview")
block(id="block-23")
anchor("data-lake-design")

```
解析失敗時必須拒絕執行。---
### 4.2.5 Action Mode 語義

<!-- Table: 2e310eba-142a-80f0-b7ca-fb2dd3edaaa5 -->
---
### 4.2.6 Constraints（約束子語言）
Constraints 為 **治理與安全邊界的主要載體**。```json
{
  "max_tokens": 300,
  "no_external_reference": true,
  "style_guide": "enterprise-tech-v1",
  "semantic_drift": "disallow"
}

```

---

### 4.2.7 Intent → Patch 映射規則

```plain text
Edit Intent DSL
      ↓ (validated)
Semantic Patch (optional)
      ↓
Block Patch (mandatory)
      ↓
Text Patch (compatible)

```

DEA 必須能說明：- 每一個 Block Patch 來自哪一個 Intent

- 每一個 Intent 產生了哪些結構變更

---

### 4.2.8 Intent Versioning（DSL 演進）

```json
"intent_schema_version": "1.0"

```

- 不同版本 DSL 可並存
- DEA 需具備向後相容能力

---

### 4.3 Patch / Diff Model

本系統中的 Patch 不僅是文字差異，而是 **可治理、可語義理解的變更單元**。Patch 為 DEA 對外唯一輸出成果。Patch 分為三個層級，由低到高：1. Text Patch（文字層）

1. Block Patch（結構層）
1. Semantic Patch（語義層，進階）

---

### 4.3.1 Text Patch（Unified Diff）

適用場景：- 與 Git / SCM 相容

- 最終存儲、審計、回滾

```plain text
@@ -12,6 +12,18 @@
 原有內容
+ 新增內容

```

**特性**- 不理解 Markdown 結構

- 僅作為最低層輸出格式
- 不建議用於編輯邏輯判斷

---

### 4.3.2 Block Patch（結構化 Patch，核心）

Block Patch 為 DEA 的 **主要內部與對外建議格式**，基於 Markdown AST / Block。```json
{
  "patch_type": "block",
  "patch_id": "PATCH-456",
  "doc_id": "DOC-20260109-0001",
  "base_version": "v3",
  "operations": [
    {
      "op": "insert",
      "target": {
        "block_type": "section",
        "heading": "## Architecture Overview"
      },
      "position": "after",
      "content": "### Data Lake Design
..."
    }
  ]
}

```
**支援操作（op）**- insert
- update
- delete
- move
- replace
**優點**- 與 Markdown 結構一致
- 可驗證、不易破壞文件
- 可轉換為 Text Patch
---
### 4.3.3 Semantic Patch（語義 Patch，進階）
Semantic Patch 描述的是「**意圖造成的語義變更**」，而非實際文字。```json
{
  "patch_type": "semantic",
  "intent_id": "INTENT-123",
  "effect": "expand_section",
  "target": "Architecture Overview",
  "summary": "補充資料湖與 ETL 流程設計",
  "generated_blocks": ["block-23", "block-24"]
}

```

**用途**- 高階審計 / 人類 Review

- 作為長期知識演化記錄
- 私有模型微調資料

---

### 4.3.4 Patch 轉換關係

```plain text
Semantic Patch
      ↓
Block Patch  ←（DEA 核心產物）
      ↓
Text Patch (unified diff)

```

> 規範要求：

- DEA 至少必須輸出 Block Patch
- Text Patch 為必要相容層
- Semantic Patch 為選配但強烈建議

---

```plain text
DocumentPatch
- patch_id
- doc_id
- version_id
- target_range
- diff_content
- generated_at
- generated_by

```

---

## 5. 內部模組架構

### 5.1 模組分解

```plain text
Document Editing Agent
 ├── Intent Validator
 ├── Markdown Parser (AST)
 ├── Target Locator
 ├── Content Generator (LLM-bound)
 ├── Patch Generator
 ├── Validator & Linter

```

---

### 5.2 模組職責說明

### Intent Validator

- 驗證 Intent schema 合法性
- 檢查是否超出允許編輯範圍

### Markdown Parser

- 將 md 轉為 AST / Block 結構
- 保留 heading hierarchy

### Target Locator

- 根據 Intent 定位插入或修改位置
- 支援 heading / anchor / index

### Content Generator

- 僅在「指定上下文 + 約束」下生成內容
- 不得讀取全文（最小上下文原則）

### Patch Generator

- 產生 unified diff 或 block-level patch

### Validator & Linter

- Markdown 結構檢查
- 樣式 / 長度 / 約束檢查

---

## 6. 標準執行流程（Happy Path）

```plain text
接收 DocumentContext + Edit Intent
 ↓
Intent Validator
 ↓
Parse Markdown → AST
 ↓
Locate Target Block
 ↓
Assemble Minimal Context
 ↓
Generate Content (LLM)
 ↓
Build Patch / Diff
 ↓
Validate Result
 ↓
Return Patch + Preview

```

---

## 7. 失敗與拒絕策略

DEA 必須在以下情況 **主動拒絕執行**：- Intent 無法解析或超出權限

- 目標章節不存在且不允許自動建立
- Patch 將破壞文件結構
- 生成內容違反約束（風格 / 長度 / 規範）
回傳結果應包含：- 拒絕原因（Machine-readable）
- 可修正建議（Optional）

---

## 8. 與其他系統的介面

### 8.1 與 Orchestrator

- 輸入：已授權的 Edit Task Context
- 輸出：Patch / Validation Result

### 8.2 與 Version Controller

- 不直接寫檔
- 僅回傳 Patch

### 8.3 與 RAG / GraphRAG（間接）

- 僅在 Intent 指示且授權下使用
- 不自行決定資料來源

---

## 9. 非功能性需求（NFR）

- **Determinism**：同一 Intent 在相同上下文下結果可重現
- **Latency**：單次編輯 < 可配置 SLA
- **Observability**：完整 log / trace / patch history
- **Extensibility**：可支援其他格式（如 AsciiDoc）

---
文件編輯 Agent 並非寫作工具，而是：> 一個在治理框架內，執行可控、可追溯、可演進的「知識資產變更引擎」。
它的價值不在於生成能力，而在於 **結構、邊界與責任劃分**。
