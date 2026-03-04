# API v2/chat 升級計劃

**版本**: 2.0.0  
**創建日期**: 2026-03-02  
**作者**: Daniel Chung  
**最後修改日期**: 2026-03-02

---

## 1. 概述

本文檔描述 AI-Box Top Orchestrator 層的 Chat API v2 升級計劃。基於 flowchat.md 設計架構，整合 `OrchestratorIntentRAG` 作為統一意圖分類入口，OrchestratorService 作為**閘道/路由器**調度外部服務。

### 1.1 核心原則

```
OrchestratorService = 閘道/路由器
    │
    ├── 不實作任務編排 → 調用外部 Task Orchestrator
    ├── 不實作知識檢索 → 調用外部 KA-Agent
    └── 只負責：路由 + 協調 + 監督
```

### 1.2 目標

- **統一入口**: v2/chat 整合所有模式（流式/非流式/異步/同步）
- **單一意圖分類**: 使用 `OrchestratorIntentRAG` 取代多層關鍵詞匹配
- **外部調用**: 任務編排、知識檢索等由外部服務處理
- **棄用 v1**: 將 v1 功能遷移到 v2

### 1.3 設計原則

1. **閘道模式**: OrchestratorService 只負責路由和協調
2. **外部服務**: 任務編排、知識庫等調用外部服務
3. **意圖優先**: 第一層使用 OrchestratorIntentRAG 進行意圖分類
4. **職責分離**: Orchestrator 負責調度，Agent 負責執行

---

## 2. 架構設計

### 2.1 整體架構

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API 入口層                                    │
│                         POST /api/v2/chat                                 │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ChatConfig 解析                                  │
│              根據 stream/async_mode 參數決定處理模式                       │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Sync Handler   │    │ Stream Handler │    │ Async Handler   │
│  (非流式)       │    │ (流式 SSE)     │    │ (異步 202)      │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    OrchestratorService (閘道/路由器)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    ┌────────────────────────────────────────────────────────────────┐     │
│    │ Step 1: 提取用戶輸入                                           │     │
│    └────────────────────────────────────────────────────────────────┘     │
│                              ↓                                             │
│    ┌────────────────────────────────────────────────────────────────┐     │
│    │ Step 2: 調用 OrchestratorIntentRAG 進行意圖分類                  │     │
│    │         → intent_name + action_strategy                        │     │
│    └────────────────────────────────────────────────────────────────┘     │
│                              ↓                                             │
│    ┌────────────────────────────────────────────────────────────────┐     │
│    │ Step 3: 根據 action_strategy 調度外部服務                        │     │
│    └────────────────────────────────────────────────────────────────┘     │
│                              ↓                                             │
│    ┌──────────────┬──────────────┬──────────────┬──────────────┐          │
│    ↓              ↓              ↓              ↓              ↓          │
│ ┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐          │
│ │ Direct │  │   LLM    │  │ KA-Agent │  │   Task   │  │  BPA   │          │
│ │Response│  │  (MoE)   │  │(知識庫)  │  │Orchestr. │  │(MM/DA) │          │
│ └────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘          │
│    (本地)     (外部)       (外部)       (外部)       (外部)              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 外部服務調用

| 類型 | 外部服務 | 說明 |
|------|----------|------|
| **知識檢索** | KA-Agent | 知識庫問答 |
| **任務編排** | Task Orchestrator | 複雜任務分解與執行 |
| **業務處理** | MM-Agent / DA-Agent | 業務數據查詢 |
| **一般對話** | MoE | LLM 對話 |

### 2.3 目錄結構

```
api/routers/chat_module/
├── __init__.py
├── router.py                          # 主路由
├── config.py                          # [NEW] Chat 配置
├── services/
│   ├── __init__.py
│   ├── orchestrator_service.py        # [NEW] 閘道/路由器
│   ├── chat_pipeline.py               # [待重構] 委派給 Orchestrator
│   └── external_client/                # [NEW] 外部服務客戶端
│       ├── __init__.py
│       ├── ka_agent_client.py         # KA-Agent 客戶端
│       ├── task_orchestrator_client.py # 任務編排客戶端
│       ├── mm_agent_client.py         # MM-Agent 客戶端
│       └── moe_client.py              # MoE 客戶端
├── handlers/
│   ├── __init__.py
│   ├── base.py
│   ├── sync_handler.py                # [重構] 使用 OrchestratorService
│   ├── stream_handler.py               # [重構] 使用 OrchestratorService
│   └── async_handler.py               # [NEW] 異步處理
└── ...
```

---

## 3. API 端點

### 3.1 端點總覽

| 方法 | 路徑 | 說明 | 響應 |
|------|------|------|------|
| POST | `/api/v2/chat` | 統一入口 | 取決於 `stream` 參數 |
| POST | `/api/v2/chat/execute` | 執行並等待結果 | JSONResponse |
| GET | `/api/v2/chat/requests/{request_id}` | 查詢異步請求狀態 | JSONResponse |
| POST | `/api/v2/chat/requests/{request_id}/retry` | 重試異步請求 | JSONResponse |
| POST | `/api/v2/chat/requests/{request_id}/abort` | 中止異步請求 | JSONResponse |

### 3.2 統一入口

#### POST `/api/v2/chat`

**請求參數**:

```python
class ChatRequest(BaseModel):
    # 訊息
    messages: List[Message]
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    
    # 處理模式
    stream: bool = False
    async_mode: bool = False
    timeout: int = 120
    
    # Agent 選擇
    agent_id: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    
    # 模型選擇
    model_selector: Optional[ModelSelector] = None
    
    # 意圖分類
    intent_threshold: float = 0.6
```

---

## 4. OrchestratorService

### 4.1 職責

| 職責 | 說明 |
|------|------|
| **意圖分類** | 調用 OrchestratorIntentRAG |
| **路由决策** | 根據意圖選擇調用哪個外部服務 |
| **調度協調** | 調用外部服務 |
| **結果整合** | 彙整各外部服務的回覆 |
| **監督** | 錯誤處理、超時、異常恢复 |

### 4.2 處理策略

#### DIRECT_RESPONSE (本地生成)

直接生成簡單回覆，適用於問候、感謝等場景。

```
用戶: "你好"
    ↓
OrchestratorIntentRAG → GREETING, DIRECT_RESPONSE
    ↓
OrchestratorService._handle_direct_response()
    → 返回: "您好！很高興為您服務。"
```

#### LLM (MoE)

調用 MoE 進行一般對話處理。

```
用戶: "幫我寫一首詩"
    ↓
OrchestratorIntentRAG → UNKNOWN/ GENERAL_QA, LLM_FALLBACK
    ↓
OrchestratorService._route_to_llm()
    → 調用 MoE 客戶端
    → 返回 LLM 回覆
```

#### KNOWLEDGE_RAG (KA-Agent)

轉發到 KA-Agent 進行知識庫檢索。

```
用戶: "什麼是 ERP？"
    ↓
OrchestratorIntentRAG → GENERAL_QA, KNOWLEDGE_RAG
    ↓
OrchestratorService._route_to_ka_agent()
    → 調用 KA-Agent 客戶端
    → 返回知識庫檢索結果
```

#### TASK_ORCHESTRATION (Task Orchestrator)

轉發到任務編排服務處理複雜任務。

```
用戶: "幫我分析銷售數據並生成報告"
    ↓
OrchestratorIntentRAG → COMPLEX_TASK, ROUTE_TO_TASK_ORCHESTRATOR
    ↓
OrchestratorService._route_to_task_orchestrator()
    → 調用 Task Orchestrator 客戶端
    → 返回任務執行結果
```

#### ROUTE_TO_BPA (業務代理)

轉發到業務代理處理。

```
用戶: "查詢料號庫存"
    ↓
OrchestratorIntentRAG → BUSINESS_QUERY, ROUTE_TO_AGENT
    ↓
OrchestratorService._route_to_bpa()
    → 選擇 MM-Agent
    → 調用 MM-Agent 客戶端
    → 返回業務處理結果
```

#### ROUTE_TO_SPECIFIC_AGENT

轉發到用戶指定的 Agent。

```
用戶: [選擇文件編輯 Agent] "幫我修改這段程式碼"
    ↓
OrchestratorIntentRAG → AGENT_WORK, ROUTE_TO_SPECIFIC_AGENT
    ↓
OrchestratorService._route_to_specific_agent()
    → 使用 user_selected_agent_id
    → 調用指定 Agent 客戶端
    → 返回結果
```

---

## 5. 外部服務客戶端

### 5.1 KAAgentClient

```python
class KAAgentClient:
    """KA-Agent 客戶端 - 知識庫問答"""
    
    async def query(self, question: str, context: dict) -> str:
        """調用 KA-Agent 進行知識庫檢索"""
        # HTTP 調用 KA-Agent
        # 返回檢索結果
        pass
```

### 5.2 TaskOrchestratorClient

```python
class TaskOrchestratorClient:
    """任務編排客戶端 - 複雜任務處理"""
    
    async def execute(self, task: str, context: dict) -> dict:
        """調用 Task Orchestrator 執行複雜任務"""
        # HTTP 調用 Task Orchestrator
        # 返回任務執行結果
        pass
```

### 5.3 MMAgentClient

```python
class MMAgentClient:
    """MM-Agent 客戶端 - 物料管理業務"""
    
    async def execute(self, instruction: str, context: dict) -> str:
        """調用 MM-Agent 處理業務"""
        # HTTP 調用 MM-Agent
        # 返回業務處理結果
        pass
```

### 5.4 MoEClient

```python
class MoEClient:
    """MoE 客戶端 - LLM 對話"""
    
    async def chat(self, messages: list, config: dict) -> str:
        """調用 MoE 進行對話"""
        # HTTP 調用 MoE
        # 返回 LLM 回覆
        pass
```

---

## 6. 配置

### 6.1 ChatConfig

```python
class ChatConfig:
    # 處理模式
    stream: bool = False
    async_mode: bool = False
    timeout: int = 120
    
    # 意圖分類
    intent_rag_enabled: bool = True
    intent_threshold: float = 0.6
    
    # LLM
    default_model: str = "auto"
    temperature: float = 0.7
    max_tokens: int = 4096
    
    # Agent
    default_agent: Optional[str] = None
    allowed_agents: Optional[List[str]] = None
    
    # 外部服務端點
    ka_agent_endpoint: str = "http://localhost:8000"
    task_orchestrator_endpoint: str = "http://localhost:8000"
    mm_agent_endpoint: str = "http://localhost:8003"
```

---

## 7. 遷移計劃

### Phase 1: 基礎設施

- [ ] 建立 `config.py`
- [ ] 建立 `orchestrator_service.py`
- [ ] 建立外部服務客戶端框架

### Phase 2: 意圖處理

- [ ] 實現 DIRECT_RESPONSE
- [ ] 實現 LLM 調用 (MoEClient)
- [ ] 實現 KNOWLEDGE_RAG (KAAgentClient)
- [ ] 實現 ROUTE_TO_BPA (MMAgentClient)

### Phase 3: 外部服務

- [ ] 實現 TASK_ORCHESTRATION (TaskOrchestratorClient)
- [ ] 實現 ROUTE_TO_SPECIFIC_AGENT

### Phase 4: 模式支援

- [ ] 完善流式處理
- [ ] 實現 async_handler
- [ ] 實現 execute 端點

### Phase 5: 遷移

- [ ] 遷移 v1 功能到 v2
- [ ] 更新前端調用
- [ ] 棄用 v1

---

## 8. 與 v1 對比

### 8.1 架構對比

| 維度 | v1 | v2 |
|------|----|----|
| 入口 | 多端點分散 | 統一入口 `/api/v2/chat` |
| 意圖分類 | `classify_gai_intent()` (關鍵詞) | `OrchestratorIntentRAG` (向量) |
| 處理方式 | 內含多層邏輯 | 調度外部服務 |
| 架構 | Monolithic | Gateway + External Services |

### 8.2 職責對比

| v1 問題 | v2 解決 |
|---------|---------|
| 太多層語義分析 | OrchestratorIntentRAG 統一分類 |
| 內部實作複雜 | 外部服務調用 |
| 維護困難 | 職責分離 |

---

## 9. 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.0.0 | 2026-03-02 | 初始版本 |
| 2.0.0 | 2026-03-02 | 修正為閘道/路由器架構，外部服務調用 |
