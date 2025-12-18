<!--
文件說明：GenAI 模型調用、Pipeline、上下文流程盤點（含 Mermaid 8.8 流程圖）
創建日期：2025-12-13 13:18:56 (UTC+8)
創建人：Daniel Chung
最後修改日期：2025-12-13 23:34:17 (UTC+8)
-->

# GenAI Pipeline 流程總覽

本文檔盤點 AI-Box 專案中與 **GenAI 模型調用**、**文本抽取 Pipeline（NER/RE/RT/Triple）**、**文件上傳後處理 Pipeline（分塊/向量化/KG）**、以及 **上下文（Context/Memory/Window/Persistence）** 相關的主要流程。

> **Mermaid 版本**：8.8（本文所有 Mermaid 圖使用 8.8 可用語法）

---

## 1. 關鍵模組與入口（檔案定位）

| 分類 | 檔案 | 說明 |
|------|------|------|
| API 入口 | `api/main.py` | 掛載路由 |
| LLM 統一介面 | `llm/clients/base.py` | generate/chat/embeddings |
| LLM 工廠 | `llm/clients/factory.py` | 多 Provider 工廠 |
| MoE 管理器 | `llm/moe/moe_manager.py` | 跨 provider 路由/負載/故障轉移 |
| Ollama Client | `llm/clients/ollama.py` | HTTP client 含節點路由 |
| GenAI User Config API | `api/routers/genai_user_config.py` | 使用者自帶 provider API key（狀態查詢/寫入/刪除） |
| GenAI Tenant Config API | `api/routers/genai_tenant_config.py` | 租戶政策/租戶級 secrets 管理（多租戶前置） |
| GenAI Secret Encryption | `services/api/services/genai_secret_encryption_service.py` | 使用者/租戶敏感資訊加密（AES-256-GCM；key 在 .env） |
| GenAI Config Resolver | `services/api/services/genai_config_resolver_service.py` | 合併 system/tenant/user 設定並注入 allowlist + credentials |
| GenAI Tenant Policy Store | `services/api/services/genai_tenant_policy_service.py` | 租戶政策 + 租戶級 API key（DB 優先 + fallback） |
| GenAI User Secret Store | `services/api/services/genai_user_llm_secret_service.py` | 使用者 API key（DB 優先 + fallback） |
| GenAI Chat Request Store | `services/api/services/genai_chat_request_store_service.py` | request_id 狀態存儲（Redis 優先 + fallback） |
| GenAI Chat RQ Job | `workers/genai_chat_job.py` | RQ worker 執行 request_id 任務入口 |
| NER 服務 | `genai/api/services/ner_service.py` | 命名實體識別 |
| RE 服務 | `genai/api/services/re_service.py` | 關係抽取 |
| RT 服務 | `genai/api/services/rt_service.py` | 關係類型分類 |
| Triple 服務 | `genai/api/services/triple_extraction_service.py` | 三元組提取 |
| 文件上傳 | `api/routers/file_upload.py` | 上傳+非同步處理（RQ） |
| RQ Queue | `database/rq/queue.py` | 隊列管理 |
| Worker Tasks | `workers/tasks.py` | RQ 任務函數（包裝 async pipeline） |
| Embedding | `services/api/services/embedding_service.py` | 向量化 |
| KG 抽取 | `services/api/services/kg_extraction_service.py` | KG 抽取（chunk 可續跑） |
| Context Manager | `genai/workflows/context/manager.py` | 上下文管理 |
| Context Recorder | `genai/workflows/context/recorder.py` | Redis/memory 記錄器 |
| Context Window | `genai/workflows/context/window.py` | 上下文截斷 |

---


## 1.1 產品級對話入口（前端輸入框）與模型選擇（Auto/指定/收藏）

> 重要：本文件作為「開發指導核心」，因此把你補充的兩個能力（模型選擇參數化、Agent 編排與 per-agent 模型策略）納入架構指引。

### 1.1.1 Model Selector（前端）→ MoE（後端）

- **前端**：`ai-bot/src/components/ChatInput.tsx` 已有 `Auto` 與多模型列表（含 Ollama/ChatGPT/Gemini/Qwen/Grok）。
- **後端**：`llm/moe/moe_manager.py` 提供統一 `chat()/generate()`，可依 `task_classification` 做 Auto routing。
- **系統參數（JSON）**：專案已有 `config/config.json`（由 `system/infra/config/config.py` 載入）。未來可把你說的「系統參數 json」放在此處（例如 cost/latency/quality 偏好、強制 provider、黑白名單等）。

建議將前端選擇抽象成以下 request 形狀（**產品級 Chat API** 需支援）：

- `model_selector.mode`: `auto` | `manual` | `favorite`
- `model_selector.model_id`: manual/favorite 時必填（例如 `gpt-4-turbo`、`qwen3-coder:30b`）
- `model_selector.policy_overrides`: 可選（對應「系統參數 json」覆蓋，例如 cost_threshold、low_latency）

> 補充：目前 repo 中的 `/api/v1/llm/*` 仍偏「基礎 LLM 服務端點」，尚未作為前端輸入框的產品級入口；產品級 Chat API 建議獨立 `/api/v1/chat/*` 並在此統一串接 MoE + Context/Memory。

### 1.1.2 Agent Selector（Auto/指定）與任務型 Agent（下一迭代）

- **任務分析基礎已存在**：`agents/task_analyzer/analyzer.py` 會產出 workflow 選擇 + LLM 路由建議（provider/model）。
- **代理平台骨架已存在**：Registry/Orchestrator/MCP executor：`agents/services/orchestrator/orchestrator.py`、`agents/services/registry/task_executor.py`。

**下一迭代（G7）要落地的能力**：
- 任務型 Agent 池：Security / Status / Report / WebCrawler / Knowledge（等）
- **per-agent / per-subtask 的模型策略**：
  - 例：Security 用高可靠模型；WebCrawler/整理用低成本模型；Report 用長上下文模型

### 1.1.3 指導性流程圖（前端輸入框 → 模型/代理路由）

```mermaid
graph TD
  U["Frontend Input"]:::client --> CHAT["Chat Product API /api/v1/chat"]:::api

  CHAT -->|task text + context| TA["TaskAnalyzer"]:::service
  TA -->|task_classification| MS["Model Selector"]:::service

  MS -->|mode=auto| MOE["LLMMoEManager"]:::service
  MS -->|mode=manual/favorite| OV["Model Override"]:::service

  OV --> MOE
  MOE --> LLM["LLM Provider(s)"]:::llm

  TA -->|next iteration| AS["Agent Selector (G7)"]:::service
  AS --> ORCH["Agent Orchestrator"]:::service
  ORCH --> AG["Task Agents (Security/Report/WebCrawler/...) "]:::worker

  classDef client fill:#a8e6cf,stroke:#333,stroke-width:2px
  classDef api fill:#88d8b0,stroke:#333,stroke-width:2px
  classDef service fill:#ffeaa7,stroke:#333,stroke-width:2px
  classDef worker fill:#f39c12,stroke:#333,stroke-width:2px
  classDef llm fill:#fd79a8,stroke:#333,stroke-width:2px
```
---

### 1.1.4 可靠的背景作業（request_id lifecycle）與排定隊列（local / RQ）

- **需求背景**：使用者送出訊息後即使離開頁面，後端仍要持續處理；前端可用 `request_id` 輪詢結果或 `abort`。
- **API**（產品級 Chat）：
  - `POST /api/v1/chat/requests`：回 `202` + `request_id`，支援 `executor=local|rq`
  - `GET /api/v1/chat/requests/{request_id}`：查狀態（queued/running/succeeded/failed/aborted）
  - `POST /api/v1/chat/requests/{request_id}/abort`：中止（set abort flag + cancel local task）
- **存儲**：`services/api/services/genai_chat_request_store_service.py`（Redis-first + memory fallback, TTL）
- **RQ**：
  - queue：`database/rq/queue.py` 的 `GENAI_CHAT_QUEUE = "genai_chat"`
  - worker entry：`workers/genai_chat_job.py::run_genai_chat_request`
- **何時用 RQ**：
  - **短任務/低延遲**：local background task
  - **長任務/Agent 編排**：RQ（可跨進程、可重啟續跑）

### 1.1.5 多租戶前置：tenant/org policy + user config（含 user API key）

- **tenant_id 來源**：HTTP header `X-Tenant-ID`（fallback：`user.metadata.tenant_id`；default=`default`）
- **Policy 合併順序**：system(config) → tenant(DB) → user(DB；本階段先做 secrets) → request（僅允許收斂，不擴權）
- **租戶政策（非敏感）**：`services/api/services/genai_tenant_policy_service.py`
- **使用者 secrets（敏感）**：`services/api/services/genai_user_llm_secret_service.py`
- **加密**：`services/api/services/genai_secret_encryption_service.py`，環境變數 `GENAI_SECRET_ENCRYPTION_KEY`
- **解析器**：`services/api/services/genai_config_resolver_service.py` 產出 effective allowlist 與 provider API key（user > tenant）
- **管理 API**：
  - `PUT/GET /api/v1/genai/tenants/{tenant_id}/policy`
  - `PUT/DELETE /api/v1/genai/tenants/{tenant_id}/secrets/*`
  - `PUT/GET/DELETE /api/v1/genai/user/secrets*`

### 1.1.6 多模型調用 + Ollama（本地與公司 service）

- **模型清單 API**：`GET /api/v1/chat/models`
  - 靜態來源：`config/config.json` → `genai.model_registry.models`
  - 動態來源：Ollama `/api/tags`（可同時配置本地與公司 Ollama nodes；快取 TTL）
  - 預設套用 effective policy（system/tenant）
- **MoE 呼叫**：`LLMMoEManager.chat()/generate()` 支援 Auto/Manual/Favorite
  - Auto 時依 allowlist 的 `allowed_providers` 做路由/負載/故障轉移
  - per-request credentials 由 `context.llm_api_keys` 注入（避免全域 env 汙染與併發風險）

## 2. 全域總覽流程（已對齊「文件上傳→向量→圖譜」文件）

```mermaid
graph TD
  A["Client / Frontend"]:::client -->|HTTP| B["FastAPI API Gateway"]:::api

  subgraph API_Routers
    B --> TA["text-analysis API"]:::api
    B --> FU["files upload API"]:::api
    B --> LLM_API["llm API"]:::api
  end

  subgraph GenAI_Services
    TA --> NER["NERService"]:::service
    TA --> RE["REService"]:::service
    TA --> RT["RTService"]:::service
    TA --> TR["TripleExtractionService"]:::service
  end

  subgraph File_Pipeline
    FU -->|enqueue| Q["RQ Queue"]:::queue
    Q --> W["RQ Worker"]:::worker

    W --> P["File Processing Pipeline"]:::process
    P --> CP["Parse and Chunk"]:::process

    P --> EMB["EmbeddingService"]:::service
    EMB --> VS["ChromaDB"]:::database

    P --> KGE["KGExtractionService"]:::service
    KGE --> TRF["TripleExtractionService"]:::service
    TRF --> NERF["NER"]:::service
    TRF --> REF["RE"]:::service
    TRF --> RTF["RT"]:::service

    KGE --> ADB_KG[("ArangoDB Graph")]
  end

  subgraph LLM_Stack
    NER --> OC["OllamaClient"]:::llm
    RE --> OC
    RT --> OC
    TR --> OC
    LLM_API --> OC
    OC --> OLLAMA[("Ollama Service")]
  end

  subgraph Storage_and_State
    RDS[("Redis")]
    ADB_META[("ArangoDB Metadata")]
  end

  FU -->|create metadata| ADB_META
  P -->|status update| RDS

  classDef client fill:#a8e6cf,stroke:#333,stroke-width:2px
  classDef api fill:#88d8b0,stroke:#333,stroke-width:2px
  classDef service fill:#ffeaa7,stroke:#333,stroke-width:2px
  classDef queue fill:#fdcb6e,stroke:#333,stroke-width:2px
  classDef worker fill:#f39c12,stroke:#333,stroke-width:2px
  classDef process fill:#74b9ff,stroke:#333,stroke-width:2px
  classDef database fill:#a29bfe,stroke:#333,stroke-width:2px
  classDef llm fill:#fd79a8,stroke:#333,stroke-width:2px
```

---

## 3. 文本抽取流程（/api/v1/text-analysis）

### 3.1 同步請求時序（以 triples 為例）

```mermaid
sequenceDiagram
  participant C as Client
  participant API as FastAPI
  participant TR as TripleService
  participant NER as NERService
  participant RE as REService
  participant RT as RTService
  participant O as OllamaClient
  participant S as Ollama

  rect rgb(200, 230, 201)
    Note over C,API: 請求階段
    C->>API: POST /api/v1/text-analysis/triples
    API->>TR: extract_triples
  end

  rect rgb(255, 243, 224)
    Note over TR,NER: NER 階段
    alt enable_ner is true
      TR->>NER: extract_entities
      NER->>O: generate with purpose ner
      O->>S: POST /api/generate
      S-->>O: response
      O-->>NER: text content
      NER-->>TR: entities list
    end
  end

  rect rgb(227, 242, 253)
    Note over TR,RE: RE 階段
    TR->>RE: extract_relations
    RE->>O: generate with purpose re
    O->>S: POST /api/generate
    S-->>O: response
    O-->>RE: text content
    RE-->>TR: relations list
  end

  rect rgb(248, 187, 208)
    Note over TR,RT: RT 階段
    TR->>RT: classify_relation_types_batch
    RT->>O: generate with purpose rt_batch
    O->>S: POST /api/generate
    S-->>O: response
    O-->>RT: text content
    RT-->>TR: relation_types
  end

  rect rgb(200, 230, 201)
    Note over TR,C: 回應階段
    TR-->>API: triples list
    API-->>C: 200 OK with triples
  end
```

---

## 4. 文件上傳 → RQ 非同步處理流程（分塊 / 向量化 / 圖譜）

> 本章已對齊：
> - `docs/文件上傳向量圖譜/文件操作.md`
> - `docs/文件上傳向量圖譜/圖譜化流程NER-RE-RT標簽化工作流程.md`

### 4.1 主流程時序（上傳→分塊→向量→圖譜）

```mermaid
sequenceDiagram
  participant C as Client
  participant API as FastAPI
  participant R as Redis
  participant Q as RQ Queue
  participant W as RQ Worker
  participant P as Pipeline
  participant E as EmbeddingService
  participant V as ChromaDB
  participant K as KGExtractionService
  participant T as TripleExtractionService
  participant A as ArangoDB

  rect rgb(200, 230, 201)
    Note over C,Q: 上傳與入隊
    C->>API: POST /api/v1/files/upload
    API->>R: SET upload progress
    API->>Q: enqueue file processing task
    API-->>C: 200 OK with file_id
  end

  rect rgb(255, 243, 224)
    Note over W,P: Chunking 階段
    W->>Q: fetch job
    W->>P: run async pipeline
    P->>R: status chunking processing
    P->>R: status chunking completed
  end

  rect rgb(227, 242, 253)
    Note over P,E: Vectorization 階段
    P->>R: status vectorization processing
    P->>E: generate_embeddings_batch
    E-->>P: embeddings
    P->>V: store vectors
    P->>R: status vectorization completed
  end

  rect rgb(248, 187, 208)
    Note over P,K: KG Extraction 階段（NER→RE→RT）
    Note over K: 若已有向量，可由向量資料重建 chunks 以避免重複分塊

    P->>R: status kg_extraction processing
    P->>K: extract_triples_from_chunks
    K->>T: extract_triples per chunk
    T-->>K: triples
    K->>A: upsert graph entities/relations
    K-->>P: progress + remaining_chunks
    P->>R: status kg_extraction updated
  end

  rect rgb(209, 196, 233)
    Note over C,API: 狀態查詢（前端輪詢）
    C->>API: GET /api/v1/files/{file_id}/processing-status
    API->>R: GET processing status
    R-->>API: status data
    API-->>C: 200 OK with status
  end
```

### 4.2 你文件中定義的「銜接點」核對結果

- **流程一致**：`文件操作.md` 所描述的 **RQ 非同步模式**（上傳→分塊→向量→圖譜）與本總覽一致。
- **可續跑一致**：`文件操作.md` 的 **圖譜分塊可續跑**（chunk 完成即寫入 ArangoDB、time budget 用盡會 enqueue 下一輪、Redis lock 防重複）與本總覽一致。
- **NER/RE/RT 銜接一致**：`圖譜化流程NER-RE-RT標簽化工作流程.md` 的 **NER→RE→RT→Triple→ArangoDB** 與本總覽一致（已在 2/4 章圖中標註 TripleExtractionService 介入）。
- **需要補充（已補）**：本總覽原本沒有明確畫出 **ArangoDB Graph** 與 **TripleExtractionService（NER/RE/RT）** 在文件處理的落點；已在「全域總覽」與「文件上傳時序」補上。

### 4.3 觀測與 API（對齊 `文件操作.md`）

- **上傳**：`POST /api/v1/files/upload`
- **處理狀態（前端輪詢）**：`GET /api/v1/files/{file_id}/processing-status`
  - 會包含 `chunking / vectorization / storage / kg_extraction` 狀態與進度
  - `kg_extraction` 會包含 `job_id / next_job_id / total_chunks / completed_chunks / remaining_chunks / failed_chunks / failed_permanent_chunks`
- **KG 分塊狀態（更完整）**：`GET /api/v1/files/{file_id}/kg/chunk-status`
- **KG 三元組列表**：`GET /api/v1/files/{file_id}/kg/triples?limit=100&offset=0`
- **重新生成（向量/圖譜）**：`POST /api/v1/files/{file_id}/regenerate`（body: `{"type":"vector"}` 或 `{"type":"graph"}`）

---

## 5. 上下文流程

```mermaid
graph TD
  subgraph Producer
    U["User"]:::client --> AG["Agent or Workflow"]:::service
    AG -->|record_message| CR["ContextRecorder"]:::service
  end

  subgraph Storage
    CR -->|Redis List with TTL| RDS[("Redis")]:::database
    CR -->|fallback| MEM[("In-Memory")]:::memory
  end

  subgraph Consumption
    CR -->|get_messages| CM["ContextManager"]:::service
    CM --> CW["ContextWindow truncate"]:::process
    CW --> MSG["LLM messages"]:::output
  end

  subgraph Persistence
    CM -->|persist_context| CP["ContextPersistence"]:::service
    CP --> ADB[("ArangoDB")]:::database
  end

  MSG --> LLM["LLM Client"]:::llm

  classDef client fill:#a8e6cf,stroke:#333,stroke-width:2px
  classDef service fill:#ffeaa7,stroke:#333,stroke-width:2px
  classDef database fill:#a29bfe,stroke:#333,stroke-width:2px
  classDef memory fill:#74b9ff,stroke:#333,stroke-width:2px
  classDef process fill:#81ecec,stroke:#333,stroke-width:2px
  classDef output fill:#dfe6e9,stroke:#333,stroke-width:2px
  classDef llm fill:#fd79a8,stroke:#333,stroke-width:2px
```

---

## 6. LLM MoE 路由流程

```mermaid
graph TD
  REQ["Request"]:::client --> MOE["LLMMoEManager"]:::moe

  MOE --> LB["LoadBalancer"]:::router
  MOE --> DR["DynamicRouter"]:::router

  LB --> SELECT["select_provider"]:::process
  DR --> SELECT

  SELECT --> CLIENT["get_client by provider"]:::factory

  CLIENT --> CHATGPT["ChatGPTClient"]:::llm_gpt
  CLIENT --> GEMINI["GeminiClient"]:::llm_gemini
  CLIENT --> OLLAMA["OllamaClient"]:::llm_ollama
  CLIENT --> QWEN["QwenClient"]:::llm_qwen

  CHATGPT --> CALL["call LLM API"]:::process
  GEMINI --> CALL
  OLLAMA --> CALL
  QWEN --> CALL

  CALL -->|success| SUCCESS["mark_success"]:::success
  CALL -->|failure| FAIL["mark_failure"]:::fail
  FAIL --> FAILOVER["failover to next provider"]:::failover
  FAILOVER --> CLIENT

  classDef client fill:#a8e6cf,stroke:#333,stroke-width:2px
  classDef moe fill:#6c5ce7,stroke:#fff,stroke-width:2px,color:#fff
  classDef router fill:#fdcb6e,stroke:#333,stroke-width:2px
  classDef process fill:#74b9ff,stroke:#333,stroke-width:2px
  classDef factory fill:#81ecec,stroke:#333,stroke-width:2px
  classDef llm_gpt fill:#00b894,stroke:#333,stroke-width:2px
  classDef llm_gemini fill:#0984e3,stroke:#fff,stroke-width:2px,color:#fff
  classDef llm_ollama fill:#e17055,stroke:#333,stroke-width:2px
  classDef llm_qwen fill:#d63031,stroke:#fff,stroke-width:2px,color:#fff
  classDef success fill:#00b894,stroke:#333,stroke-width:2px
  classDef fail fill:#d63031,stroke:#fff,stroke-width:2px,color:#fff
  classDef failover fill:#fdcb6e,stroke:#333,stroke-width:2px
```

---

## 7. 除錯觀察點

| 流程 | 觀察方式 |
|------|----------|
| 文本抽取 | 直接打 `/text-analysis/*`，觀察回傳與服務 log |
| 文件處理 | `GET /api/v1/files/{file_id}/processing-status` 看每階段狀態 |
| KG 分塊 | `GET /api/v1/files/{file_id}/kg/chunk-status` 看 chunk 級結果 |
| Worker | 查看 `logs/rq_worker_*.log` |
| FastAPI | 查看 `logs/fastapi.log` |

---

## 顏色圖例

| 顏色 | 類別 |
|------|------|
| 🟢 綠色 | Client / 成功 |
| 🟡 黃色 | Service / Router |
| 🔵 藍色 | Process / Memory |
| 🟣 紫色 | Database / MoE |
| 🩷 粉色 | LLM Client |
| 🔴 紅色 | External / 失敗 |
