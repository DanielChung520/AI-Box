# 架構白皮書：以 Agent 為核心、以知識為資產的企業級 AI 系統

## 1. 前言

隨著生成式 AI 與 Agentic AI 的快速演進，企業逐漸從「單一模型驅動」邁向「多 Agent 協作」的系統型態。然而，多數實作仍停留在工具鏈整合或流程自動化層級，缺乏對**知識資產治理**與**長期可演化架構**的整體設計。

本白皮書提出一套以  **AI-Box 為 Agent Runtime 核心** 、以  **Knowledge Service 為平台級知識平面（Knowledge Plane）** 、並透過 **MCP（Model Context Protocol）** 串接業務流程 Agent（BPA）的企業級架構，目標在於：

* 降低 Agent 系統的複雜度與耦合度
* 將知識從 Agent 中解耦，成為可治理、可交易的資產
* 支援企業內外多知識源並存的長期演進

---

## 2. 設計動機與核心問題

### 2.1 傳統 Agent 架構的限制

在許多現行設計中，每個執行層 Agent 被視為一個「全功能單元」，同時負責：

* 任務執行
* 專業知識保存
* 向量檢索與關係推理

此種設計在規模化後，將導致：

* 向量資料庫與圖譜重複部署，資源浪費
* 知識版本分裂，語意不一致
* 知識生命週期難以治理

### 2.2 核心問題定義

本架構嘗試回答以下關鍵問題：

1. 知識是否應該屬於 Agent？
2. 如何讓知識成為企業級、跨 Agent 的共享資產？
3. 如何在不犧牲彈性的前提下，避免系統過度複雜？

---

## 3. 架構總覽

本系統由三個主要平面構成：

1. **AI-Box（Agent Runtime & Governance Core）**
2. **Knowledge Service（Knowledge Plane）**
3. **Business Process Agent（BPA）生態系**

三者透過 MCP 進行鬆耦合串接。

---

## 4. AI-Box：Agent Runtime 與治理核心

### 4.1 角色定位

AI-Box 並非「所有能力的集中點」，而是：

* Agent 的執行環境（Runtime）
* 能力發現與協調中心（Orchestrator Agent）
* 安全、信任與存取邊界的治理單元

### 4.2 核心組件

* **Orchestrator Agent** ：
* 意圖解析
* 能力發現（Capability Discovery）
* 任務分派（不直接執行）
* **Support Agents** ：
* 文件處理
* 系統操作
* 診斷與回饋

AI-Box 本身 **不承擔長期知識保存責任** 。

---

## 5. Knowledge Service：企業級知識平面

### 5.1 設計原則

* 知識是平台級資產，不屬於任何單一 Agent
* 知識必須可治理、可版本化、可被多方消費
* Agent 僅透過契約（API / MCP）取用知識

### 5.2 組成結構

#### 5.2.1 Storage Layer

* **Vector Store（Qdrant）** ：
* 文件語意
* 經驗片段
* 非結構化知識
* **Graph Store（ArangoDB）** ：
* Entity / Process / Asset
* 關係、約束、依賴

#### 5.2.2 Knowledge Governance Layer

由 **Knowledge Curator Agent** 負責：

* 知識上架（Ingestion）
* Chunk / Entity 對齊
* Ontology 與 Schema 管理
* 版本與演進控制
* 權限與存取策略

#### 5.2.3 Access Layer

* MCP-based Knowledge API
* Hybrid Retrieval（Vector + Graph）
* 語意與關係混合查詢

---

## 6. Business Process Agent（BPA）作為獨立服務

### 6.1 BPA 的定位

BPA 是業務流程的智慧組合者，而非知識的唯一擁有者。

其特性包括：

* 可維持自身私有知識庫
* 可選擇性使用 Knowledge Service
* 可同時參照多個知識來源

### 6.2 去中心化但可組合的設計

此設計避免：

* Vendor Lock-in
* 強制知識集中

同時保留：

* 跨組織協作
* 知識交叉驗證的可能性

---

## 7. MCP 作為連接契約

MCP 在此架構中扮演：

* 能力宣告（Capability Contract）
* 知識存取協議
* 信任邊界的技術實現

其存在使得：

* Knowledge Service 可獨立部署
* 第三方知識庫可被替換或並存

---

## 8. 商業與策略價值

### 8.1 從賣系統到賣知識

本架構允許：

* 系統銷售（AI-Box）
* 知識服務訂閱
* 領域知識包（Domain Knowledge Assets）交易

### 8.2 長期演進性

* 知識隨時間累積，形成護城河
* Agent 可替換、可升級
* 架構不因模型更迭而失效

---

## 9. 設計原則總結

* Agents 擁有技能，不擁有知識
* 知識是可治理、可版本化的資產
* 微服務透過契約取用知識，而非自行保存
* 私有與公共知識可並存且可組合

---

## 10. 結語

此架構嘗試為企業級 Agentic AI 提供一條可長期演進的路徑，使 AI 不僅是工具，而是可被治理、被信任、被交易的智慧基礎設施。

後續文件將進一步定義  **Knowledge Service Layer Specification** ，並引入 **Knowledge Assets（KA）與 KA-Agent** 的完整模型。
