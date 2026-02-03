# Knowledge Service Layer Specification (KSLS)

> Engineering-Oriented Architecture & Capability Specification

---

## 1. 文件目的與範圍

本文件定義 **Knowledge Service Layer（KSL）** 的工程級系統規格，用以支援 Agent-Oriented 企業 AI 架構中的知識治理、存取與資產化需求。

本規格假設：

* Agent 不直接持有長期知識
* 知識作為平台級資產，需可治理、可版本化、可交易
* KSL 可被 AI-Box、BPA 與第三方系統共同使用

---

## 2. 系統定位與責任邊界

### 2.1 KSL 的責任

Knowledge Service Layer 負責：

* 知識的結構化與語意化表示
* 知識生命週期管理
* 跨 Agent 的一致性檢索
* 知識資產（Knowledge Assets, KA）的封裝與治理

### 2.2 明確不負責事項

KSL  **不負責** ：

* 任務推理或決策
* Agent orchestration
* Workflow state 管理

---

## 3. 核心設計原則

1. **Knowledge is not memory**
2. **Assets over documents**
3. **Governance before retrieval**
4. **Contracts over coupling**

---

## 4. 高階系統架構

### 4.1 邏輯分層

1. Storage Layer
2. Knowledge Governance Layer
3. Knowledge Asset Layer
4. Access & Contract Layer

---

## 5. Storage Layer Specification

### 5.1 Vector Store（Qdrant）

 **用途** ：

* 非結構化知識
* 經驗性內容
* 語意相似度檢索

 **基本 Schema（概念）** ：

* vector_id
* embedding
* ka_id
* entity_refs[]
* created_at
* version

---

### 5.2 Graph Store（ArangoDB）

 **用途** ：

* Entity / Process / Asset
* 關係、約束、依賴

 **核心節點類型** ：

* Entity
* Relation
* Process
* KnowledgeAsset

---

## 6. Knowledge Assets（KA）模型

### 6.1 KA 定義

Knowledge Asset 是一個具備治理屬性的知識封裝單位，可被 Agent 作為「可信知識來源」使用。

### 6.2 KA 核心屬性

* ka_id
* domain
* description
* owner
* provenance
* license
* lifecycle_state
* version
* validity_scope

### 6.3 KA 與底層資料的關係

* 一個 KA 可對應：
  * 多個向量片段
  * 多個圖譜節點與關係

---

## 7. Knowledge Governance Layer

### 7.1 Knowledge Curator Agent

 **職責** ：

* 知識上架（ingestion）
* Chunk 與 Entity 對齊
* Ontology / Schema 管理
* 版本與演進控制

---

## 8. KA-Agent Specification

### 8.1 定位與角色

KA-Agent（Knowledge Asset Agent）是 Knowledge Service Layer 中**唯一負責知識資產化與治理執行**的系統代理，其核心任務是將原始知識轉換為可被治理、可被審計、可被多 Agent 使用的 Knowledge Assets（KA）。

KA-Agent 不參與業務推理、不生成業務決策內容，也不負責 Agent 協調，其角色聚焦於 Knowledge Plane。

---

### 8.2 核心職責範圍

#### 8.2.1 Knowledge Ingestion & Assetization

KA-Agent 負責知識上架流程，包含但不限於：

* 接收原始知識來源（文件、資料庫、API、第三方知識庫）
* 向量化處理（Embedding Generation）
* Ontology 對齊與 Schema 驗證
* Entity / Relation 抽取
* 知識圖譜化（Graph Materialization）
* 將處理後結果封裝為一個或多個 Knowledge Assets（KA）

KA-Agent 必須遵守既定 Ontology 與 Schema Contract，但不負責定義 Ontology 本身。

---

#### 8.2.2 Versioned Knowledge Update

KA-Agent 不允許覆寫既有 Knowledge Asset。所有更新行為必須：

* 建立新版本 KA
* 維護版本關聯（supersedes / superseded_by）
* 更新舊版本狀態（Active → Deprecated）

此設計確保：

* 既有 Agent 行為不被破壞
* 新 Agent 可明確識別最新知識

---

#### 8.2.3 Retrieval Enablement

KA-Agent 提供標準化的檢索能力支援，但不參與查詢策略決策。

其責任包含：

* 定義可用的 KA-scoped retrieval view
* 支援 semantic query、graph constraint 與 metadata filter
* 確保檢索結果可追溯至 KA 與版本

KA-Agent 不為 BPA 客製檢索邏輯，也不對結果做業務層判斷。

---

#### 8.2.4 Security Enforcement & Audit

KA-Agent 為 Knowledge Service Layer 的 Policy Enforcement Point（PEP），其責任包含：

* 驗證呼叫者身份與 MCP capability scope
* 驗證 KA 存取權限與 domain isolation
* 記錄完整審計軌跡（誰、何時、以何種方式存取哪個 KA）

Policy 的定義由外部治理機制負責，KA-Agent 僅負責執行與記錄。

---

#### 8.2.5 Knowledge Provenance & Trust Hints

KA-Agent 必須維護每個 KA 的知識來源與可信度提示，包括：

* 原始來源與建立方式
* 最近更新時間與頻率
* 是否經人工審核或驗證

KA-Agent 提供 trust_hint 與 freshness 等輔助資訊，但不對知識正確性作最終裁定。

---

#### 8.2.6 Lifecycle State Enforcement

KA-Agent 是唯一可變更 Knowledge Asset lifecycle 狀態的系統元件，包含：

* Draft → Active
* Active → Deprecated
* Deprecated → Archived

所有狀態轉換必須被審計並可回溯。

---

## 9. 知識生命週期管理

### 9.1 狀態模型

* Draft
* Active
* Deprecated
* Archived

### 9.2 狀態轉換規則

* Draft → Active：完成治理審核
* Active → Deprecated：新版本或失效

---

## 10. Access & Contract Layer

### 10.1 MCP-based Interface

* capability:knowledge.query
* capability:knowledge.traverse
* capability:ka.list
* capability:ka.retrieve

---

## 11. Retrieval 行為定義

### 11.1 Query 類型

* Semantic Query
* Graph Constraint Query
* Hybrid Query

### 11.2 回傳內容

* content
* ka_id
* confidence_hint
* freshness

---

## 12. 多知識源與仲裁

KSL 支援：

* 本地 Knowledge Assets
* 第三方知識庫
* 私有 BPA 知識源

仲裁策略由呼叫端 Agent 決定。

---

## 13. 安全與權限

* KA-level Access Control
* Domain-based Isolation
* Audit Log

---

## 14. 可觀測性與演進

* Usage Metrics
* KA Coverage
* Knowledge Drift Detection

---

## 15. 未來擴展方向

* Knowledge Marketplace
* Cross-Org Knowledge Federation
* Trust Scoring for KA

---

## 16. 結語

Knowledge Service Layer 不是單純的資料存取服務，而是企業 AI 系統中可被治理與交易的知識基礎設施。
