# Agent 專業知識上架管理

**最後更新**: 2026-01-27 25:00 UTC+8  
**維護人**: Daniel Chung  
**版本**: v2.1

**本文檔定義 AI-Box Agent 平台的知識架構、管理策略與標準上架流程**，適用於所有 Agent（如 KA-Agent、MM-Agent 等）。

---

## 1. 概述

### 1.1 適用範圍

本流程適用於所有需要上架知識庫的 Agent，包括但不限於：
- **KA-Agent**（Knowledge Architect Agent）
- **MM-Agent**（Material Management Agent）
- **PO-Agent**（Procurement Agent）
- 其他執行層 Agent

### 1.2 核心願景

在 AI-Box 的微服務架構中，每個執行層 Agent（如物料管理員、採購管理員）應被視為具備「**大腦（LLM）**」、「**知識（Knowledge Base）**」與「**技能（Tools/Skills）**」的獨立個體。為了平衡開發靈活性與系統資源利用率，我們採用 **「共享基礎設施、邏輯空間隔離」** 的知識架構。

### 1.3 核心原則

1. **統一流程**：所有 Agent 使用相同的上架流程和核心代碼
2. **Ontology 優先**：必須先導入 Ontology，再執行知識庫上架
3. **自動化處理**：上架後自動執行分塊、向量化、圖譜提取、知識資產編碼
4. **測試優先**：測試流程不包含補跑，問題需定位根因並修復
5. **共享基礎設施**：Agent 不重複安裝數據庫進程，統一使用知識中心
6. **邏輯空間隔離**：每個 Agent 擁有獨立的知識空間，通過 `task_id`（Agent 代碼）隔離

### 1.4 架構藍圖

```
[ 執行層 Agent 微服務 ] (如: 物料 Agent)
      │
      ├── 專業技能 (Skills): 封裝在 Agent 代碼中的 Python 邏輯 (如: 補貨算法)
      │
      └── 專業知識 (Knowledge): 通過 API 訪問 AI-Box 統一知識中心
                │
                ▼ [ 統一知識中心 / Knowledge Service ]
                │
                ├── [ 向量空間 ] (Qdrant)
                │    ├── Collection: file_{file_id} (按 task_id 組織)
                │    └── 統一 Embedding 模型，確保向量維度一致
                │
                └── [ 圖譜空間 ] (ArangoDB)
                     ├── Collection: entities (實體，含 file_id 標籤)
                     └── Collection: relations (關係，含 file_id 標籤)
```

**架構特點**：
- **共享基礎設施**：所有 Agent 共用 Qdrant、ArangoDB、SeaweedFS，不重複安裝
- **邏輯空間隔離**：通過 `task_id`（Agent 代碼）標記，實現知識空間隔離
- **統一 Embedding**：由系統統一提供模型進行向量轉換，確保不同 Agent 之間的向量維度一致，便於未來進行跨域關聯

### 1.5 知識隔離與共享策略

#### 1.5.1 邏輯空間隔離 (Multi-tenancy)

- **Agent 代碼 = 任務名稱**：每個 Agent 擁有唯一的 `task_id`（Agent 代碼），作為知識空間的邏輯標識
- **任務命名規範**：**Agent 任務必須以 `-Agent` 後綴命名**（如 `KA-Agent`、`MM-Agent`、`NewAgent-Agent`），系統依此規範自動識別 Agent 任務
- **知識標記**：所有向量數據和圖譜節點通過 `task_id` 標記，實現邏輯隔離
- **自動過濾**：Agent 在執行 RAG（檢索增強生成）時，系統自動過濾僅限於其 `task_id` 的知識空間

#### 1.5.2 資源共享機制

- **不重複安裝**：執行層微服務不自行安裝數據庫進程，統一使用 AI-Box 知識中心
- **統一 Embedding**：由系統統一提供模型進行向量轉換，確保不同 Agent 之間的向量維度一致，便於未來進行跨域關聯
- **統一存儲**：SeaweedFS 統一存儲原始文件，按 `task_id` 組織目錄結構

### 1.6 上架識別與授權（設計規範）

| 維度 | 說明 | 現狀 | 未來擴展 |
|------|------|------|----------|
| **Agent 代碼** | Agent 的唯一識別，即**任務名稱**（`task_id`） | 上架時指定 `--task-id`，如 `KA-Agent`、`MM-Agent` | 與 Agent 註冊／Registry 對齊 |
| **任務命名規範** | **Agent 任務必須以 `-Agent` 後綴命名** | `*-Agent` 後綴（如 `KA-Agent`、`MM-Agent`） | 系統依此規範自動識別 Agent 任務 |
| **上架用戶** | 執行上架操作的使用者 | **systemAdmin**（固定） | **可指定授權用戶**（如 `--user`），由權限與授權機制管控 |
| **知識庫路徑** | 待上架知識檔案的來源目錄 | **上架時指定** `--knowledge-base-path` | 支援絕對路徑或相對專案根目錄 |
| **Ontology 路徑** | Domain/Major Ontology 檔案所在目錄 | **上架時指定** `--ontology-path` | 可指定目錄（自動掃描 domain/major）或具體檔案 |

**要點**：
- **Agent 代碼 = 任務名稱**：上架時以 `--task-id` 指定，即 Agent 識別；上架後文件歸屬於該 `task_id`，前端任務列表以該名稱呈現。
- **任務命名規範（強制）**：**Agent 任務必須以 `-Agent` 後綴命名**（如 `KA-Agent`、`MM-Agent`），系統依此規範自動識別 Agent 任務並啟用對應的知識庫上架流程。非 `*-Agent` 後綴的任務視為一般任務，不支援 Agent 知識庫上架功能。
- **上架用戶**：現為 **systemAdmin**；**未來可指定授權用戶**（如 `--user`），由權限與授權機制管控。
- **路徑均為指定**：**知識庫路徑**、**Ontology 路徑**由上架指令明確指定（`--knowledge-base-path`、`--ontology-path`），不依賴預設目錄結構。

---

## 2. Agent 技能與知識的對接流程

Agent 的知識上架與使用遵循以下流程：

1. **整理文件**：將專業技術文檔（如 ERP 手冊、行業規格）整理至指定目錄
2. **導入 Ontology**：將 Domain/Major Ontology 導入系統，定義知識領域結構
3. **上架知識庫**：將知識文件上傳至系統，自動執行分塊、向量化、圖譜提取
4. **知識資產編碼**：系統自動進行 Ontology 對齊、生成 KNW-Code，寫入 `file_metadata`
5. **能力註冊**：Agent 在 MCP Server 中註冊時，聲明其具備訪問該知識庫的能力（通過 `task_id` 關聯）
6. **推理執行**：當 Agent 收到指令時，透過 `Knowledge Service` 獲取專業背景（RAG），結合 LLM 進行決策

**優勢**：
- **低開銷**：顯著降低微服務的內存與磁碟佔用
- **快部署**：新增一個專業 Agent 只需編寫業務代碼與配置知識庫權限
- **跨域協同**：Orchestrator 可以跨知識庫進行全局分析（例如：物料風險影響到採購決策）

---

## 3. 任務名稱與路徑規範

### 2.1 任務名稱（Agent 代碼）

- **任務 ID**：即 Agent 代碼，上架時通過 `--task-id` 指定（如 `KA-Agent`、`MM-Agent`）。
- **顯示名稱**：與任務 ID 相同，前端任務列表顯示此名稱。

### 2.2 路徑為指定參數

- **知識庫路徑**（`--knowledge-base-path`）：待上架檔案所在的**目錄**，上架時**必填**（或等價的配置）。腳本將該目錄下符合條件的檔案上傳。
- **Ontology 路徑**（`--ontology-path`）：Domain/Major Ontology 所在的**目錄**（或具體檔案），導入時**必填**。可約定目錄內含 `*-domain.json`、`*-major.json` 等檔名 pattern。

### 2.3 目錄結構範例（僅供參考，實際以指定路徑為準）

```
# 常見約定（可選），實際路徑由上架指令指定
docs/系统设计文档/核心组件/Agent平台/
├── KA-Agent/
│   ├── Ontology/
│   │   ├── ka-agent-domain.json
│   │   └── ka-agent-major.json
│   └── 知識庫/
│       └── ...
├── MM-Agent/
│   ├── Ontology/
│   │   ├── mm-agent-domain.json
│   │   └── mm-agent-major.json
│   └── 知識庫/
│       └── ...
└── Agent專業知識知識上架管理.md
```

---

## 4. 上架流程

### 3.1 流程總覽

```
┌─────────────────┐
│ 1. 導入 Ontology │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 上架知識庫    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. 自動處理      │
│ (分塊→向量化→   │
│  圖譜→編碼)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. 驗收          │
└─────────────────┘
```

### 3.2 步驟詳解

#### 步驟 1：導入 Ontology

**目的**：將 Agent 的 Domain 和 Major Ontology 導入系統

**執行方式**：

```bash
# 使用統一腳本，指定 Ontology 路徑
python scripts/agent_onboarding.py --step ontology \
  --ontology-path "/path/to/Agent/Ontology"

# 或同時指定任務名稱（用於日誌／清理等）
python scripts/agent_onboarding.py --step ontology \
  --task-id KA-Agent \
  --ontology-path "docs/系统设计文档/核心组件/Agent平台/KA-Agent/Ontology"
```

**執行內容**：
- 自 `--ontology-path` 指定目錄讀取 Domain/Major Ontology（如 `*-domain.json`、`*-major.json`）
- 寫入 ArangoDB `ontologies` collection（系統級，`tenant_id=None`）
- 若 Ontology 已存在，自動跳過導入（避免重複）

**注意**：
- Ontology 導入**僅需第一次執行**，後續測試可跳過此步驟
- Ontology 必須在知識庫上架**之前**導入
- **Ontology 路徑為上架時指定**，不依賴預設目錄

#### 步驟 2：上架知識庫

**目的**：將 Agent 知識庫文件上傳至系統

**前提條件**：
- ✅ **API 服務**已啟動（如 `http://localhost:8000`）
- ✅ **RQ Worker** 已啟動，監聽 `file_processing`、`vectorization`、`kg_extraction`
  ```bash
  python -m workers.service --queues file_processing vectorization kg_extraction --num-workers 3
  ```
- ✅ **Redis** 與 API 使用同一實例
- ✅ **API 環境**已安裝 `rq`

**執行方式**：

```bash
# 統一腳本：指定任務名稱（Agent 代碼）、知識庫路徑、上架用戶
export SYSTEADMIN_PASSWORD="你的 systemAdmin 密碼"
python scripts/agent_onboarding.py --step upload \
  --task-id KA-Agent \
  --knowledge-base-path "docs/系统设计文档/核心组件/Agent平台/KA-Agent/知識庫" \
  [--user systemAdmin]
```

**執行內容**：
- 以 **上架用戶** 登入（現階段為 `systemAdmin`；**未來可指定授權用戶**）
- 建立/確認任務（`task_id` = **Agent 代碼**，即任務名稱）
- 上傳 `--knowledge-base-path` 指定目錄下所有符合條件的檔案
- 使用 `POST /api/v1/files/v2/upload` API
- 上傳成功後自動入隊，由 RQ Worker 執行後續處理

**參數說明**：
- `--task-id`：**Agent 代碼 = 任務名稱**（如 `KA-Agent`、`MM-Agent`），必填
- `--knowledge-base-path`：**知識庫檔案路徑**（目錄），必填
- `--user`：上架用戶；現階段默認 `systemAdmin`，**未來可指定授權用戶**
- `--password`：上架用戶密碼（或 `SYSTEADMIN_PASSWORD` 等環境變數）
- `--api-base`：API 服務地址（默認 `http://localhost:8000`）
- `--upload-timeout`：單檔上傳 timeout（秒，默認 300，大檔可調高）

#### 步驟 3：自動處理（由 RQ Worker 執行）

**處理流程**：
1. **分塊**（Chunking）：將文件分割為可處理的文本塊
2. **向量化**（Vectorization）：生成文本向量，存儲至 Qdrant
3. **圖譜提取**（KG Extraction）：提取實體和關係，存儲至 ArangoDB
4. **知識資產編碼**（Knowledge Asset Encoding）：
   - Ontology 對齊（Domain/Major）
   - 生成 KNW-Code
   - 寫入 `file_metadata` 的 KA 屬性

**注意**：
- 處理過程由 RQ Worker 非同步執行
- 大檔或 PDF 處理時間較長，需耐心等待
- 若處理未完成，應**定位根因並修復**，而非使用補跑

#### 步驟 4：驗收

**驗收目標**：

| # | 目標 | 驗收方式 |
|---|------|----------|
| **1** | 上架用戶登錄，前端能看到以 **任務名稱（Agent 代碼）** 顯示的任務 | 前端登入 → 任務區檢視 |
| **2** | 任務文件區能看到知識文件，並能查看向量及圖譜 | 前端任務 → 文件列表 → 單檔詳情（向量/圖譜） |
| **3** | Qdrant、SeaweedFS Dashboard 能看到資料 | Qdrant Dashboard、SeaweedFS Dashboard |

**驗收步驟**：
1. 以上架用戶（如 **systemAdmin**）登入前端，確認任務列表中存在以 **任務名稱（Agent 代碼）** 命名的任務
2. 進入該任務 → 任務文件區，確認可見知識文件
3. 點選單檔，確認可查看向量（Qdrant collection）與圖譜（entities/relations）
4. 開啟 **Qdrant Dashboard**、**SeaweedFS**，確認能見到對應向量與檔案

---

## 5. 統一腳本使用說明

### 4.1 腳本位置

```
scripts/agent_onboarding.py
```

### 4.2 基本用法

```bash
# 導入 Ontology（指定 Ontology 路徑）
python scripts/agent_onboarding.py --step ontology \
  --ontology-path "/path/to/Ontology"

# 上架知識庫（指定任務名稱、知識庫路徑、上架用戶）
python scripts/agent_onboarding.py --step upload \
  --task-id KA-Agent \
  --knowledge-base-path "/path/to/知識庫" \
  [--user systemAdmin]

# 完整流程（Ontology + 上架，路徑均指定）
python scripts/agent_onboarding.py --step all \
  --task-id KA-Agent \
  --ontology-path "/path/to/Ontology" \
  --knowledge-base-path "/path/to/知識庫"
```

### 4.3 參數說明

| 參數 | 說明 | 必填 | 默認值 |
|------|------|------|--------|
| `--step` | 執行步驟：`ontology`、`upload`、`all`、`cleanup` | ✅ | - |
| `--task-id` | **Agent 代碼 = 任務名稱**（如 `KA-Agent`、`MM-Agent`） | upload/all/cleanup 必填 | - |
| `--ontology-path` | **Ontology 路徑**（目錄，含 domain/major JSON） | ontology/all 必填 | - |
| `--knowledge-base-path` | **知識庫檔案路徑**（目錄） | upload/all 必填 | - |
| `--user` | 上架用戶；現階段固定 `systemAdmin` | ❌ | `systemAdmin` |
| `--password` | 上架用戶密碼 | ❌ | 環境變數 `SYSTEADMIN_PASSWORD` 等 |
| `--api-base` | API 服務地址 | ❌ | `http://localhost:8000` |
| `--upload-timeout` | 單檔上傳 timeout（秒） | ❌ | `300` |

**設計要點**：
- **Agent 代碼 = 任務名稱**：`--task-id` 即 Agent 識別，上架後任務以該名稱呈現。
- **路徑均為指定**：`--ontology-path`、`--knowledge-base-path` 由上架時明確傳入，不依賴預設目錄。
- **上架用戶**：現為 `systemAdmin`；**未來可透過 `--user` 指定授權用戶**。

### 4.4 示例

```bash
# 示例 1：KA-Agent 完整上架（指定路徑）
export SYSTEADMIN_PASSWORD="systemAdmin@2026"
python scripts/agent_onboarding.py --step all \
  --task-id KA-Agent \
  --ontology-path "docs/系统设计文档/核心组件/Agent平台/KA-Agent/Ontology" \
  --knowledge-base-path "docs/系统设计文档/核心组件/Agent平台/KA-Agent/知識庫"

# 示例 2：MM-Agent 上架（大檔，調整 timeout）
python scripts/agent_onboarding.py --step upload \
  --task-id MM-Agent \
  --knowledge-base-path "datalake-system/.ds-docs/MM-Agent/知識庫" \
  --password "systemAdmin@2026" \
  --upload-timeout 600

# 示例 3：僅導入 Ontology（指定路徑）
python scripts/agent_onboarding.py --step ontology \
  --ontology-path "docs/系统设计文档/核心组件/Agent平台/PO-Agent/Ontology"

# 示例 4：未來擴展 — 指定授權用戶上架（待實現）
# python scripts/agent_onboarding.py --step upload \
#   --task-id KA-Agent \
#   --knowledge-base-path "..." \
#   --user "authorized_user_id"
```

---

## 6. 故障排除

### 5.1 常見問題

| 問題 | 可能原因 | 處理方式 |
|------|----------|----------|
| **無向量/圖譜** | RQ Worker 未運行或入隊失敗 | 啟動 RQ Worker，確認 Redis 連線 |
| **上傳 timeout** | 大檔上傳時間超過預設 timeout | 使用 `--upload-timeout 600` 或更高 |
| **處理未完成** | RQ job timeout 或記憶體不足 | 調整 RQ worker `job_timeout`，檢查系統資源 |
| **PDF 解析失敗** | PDF 格式問題或解析器錯誤 | 檢查 PDF 是否損壞，查看後端日誌 |

### 5.2 測試原則

**重要**：測試流程**不包含補跑**。若出現問題，應：
1. **定位根因**（檢查 RQ Worker、Redis、API 日誌）
2. **修復問題**
3. **清除測試資料**
4. **重新執行完整流程**（Ontology → 上架 → 驗收）

---

## 7. 清理測試資料

### 6.1 使用統一清理腳本

```bash
# 依任務名稱（Agent 代碼）清理
python scripts/agent_onboarding.py --step cleanup --task-id KA-Agent

# 或使用既有清理腳本
python scripts/cleanup_test_data.py --task-ids KA-Agent --force
```

### 6.2 清理內容

- **ArangoDB**：`user_tasks`、`file_metadata`、`entities`、`relations`（按 `task_id` = Agent 代碼過濾）
- **Qdrant**：對應 `file_id` 的 collections
- **SeaweedFS**：`/{bucket}/tasks/{task_id}/` 目錄下的文件

---

## 8. Agent 專屬文檔

每個 Agent 可以有自己的上架文檔（如 `KA-Agent/上架流程與邏輯檢討.md`），但應：
- **引用本文檔**作為通用流程說明
- **補充 Agent 專屬的特殊要求**（如 MM-Agent 的 PDF/大檔處理）
- **記錄測試結果和問題處理**

---

## 9. 未來擴展

| 項目 | 說明 |
|------|------|
| **指定授權用戶** | 除 `systemAdmin` 外，支援 `--user` 指定具上架權限的用戶；需與權限、授權機制整合 |
| **Agent 註冊對齊** | `--task-id`（Agent 代碼）與 Agent Registry 對齊，便於權限、審計與營運管理 |
| **路徑約定** | 持續以**指定路徑**為準；若需預設約定，可為個別 Agent 提供範例，但不取代顯式參數 |

---

## 10. 參考文檔

- [KA-Agent 上架流程與邏輯檢討](./KA-Agent/上架流程與邏輯檢討.md)
- [MM-Agent 上架流程與邏輯檢討](./MM-Agent/上架流程與邏輯檢討.md)
- [文件上傳功能架構說明 v4.0](../文件上傳向量圖譜/上傳的功能架構說明-v4.0.md)
- [KA-Agent 規格書](./KA-Agent/KA-Agent-規格書.md)
- [Agent 註冊-規格書](./Agent-註冊-規格書.md)（未來授權用戶、Agent 代碼對齊可參考）

---

**最後更新日期**: 2026-01-27 23:30 UTC+8  
**維護人**: Daniel Chung

---

## 附錄：歷史文檔

本文檔整合了以下文檔的內容：
- **Agent 標準上架流程**（v1.1）：具體的上架操作流程與腳本使用
- **Agent 專業知識與技能架構說明**（v1.0）：架構設計理念與知識隔離策略

合併後形成統一的 **Agent 專業知識上架管理** 文檔，涵蓋架構設計、上架流程與實作細節。
