# 狀態機機制規格書

**版本**: 1.0.0
**創建日期**: 2026-03-03
**創建人**: Daniel Chung
**最後修改日期**: 2026-03-03

## 1. 概述

### 1.1 目的

本文檔描述 OrchestratorIntentRAG 狀態機機制的設計規格，用於監督意圖分類結果的分發、執行和結果追蹤。

### 1.2 背景

根據 flowchat.md 流程圖，AI-Box 的意圖判斷層（Intent 判斷層）需要透過 OrchestratorIntentRAG 進行意圖分類，並根據分類結果進行路由：

```
H (業務意圖分析) → I (意圖判斷) → R2 (OrchestratorIntentRAG)
```

目前的實現缺少對 OrchestratorIntentRAG 執行過程的監督機制，需要建立狀態機來追蹤整個流程。

### 1.3 目標

1. **持久化存儲**：將意圖分類結果和路由決策持久化到資料庫
2. **狀態追蹤**：追蹤每個請求的狀態變化（分發 → 執行 → 完成/失敗）
3. **可觀測性**：提供查詢介面，可查看歷史狀態和當前狀態
4. **調試支持**：幫助開發人員追蹤和調試路由問題

---

## 2. 架構設計

### 2.1 系統架構

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AI-Box API Server                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    _process_chat_request                     │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │              OrchestratorIntentRAG 狀態機             │  │   │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │  │   │
│  │  │  │  分發   │→ │  執行   │→ │  結果   │→ │  歸檔   │ │  │   │
│  │  │  │ DISPATCH│  │ EXECUTE │  │ RESULT  │  │ARCHIVE  │ │  │   │
│  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      ArangoDB (持久化存儲)                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │               Collection: intent_routing_state               │   │
│  │  {                                                          │   │
│  │    "_key": "irs_xxx",                                      │   │
│  │    "request_id": "req_123",                                │   │
│  │    "session_id": "sess_abc",                               │   │
│  │    "task_id": "task_xyz",                                  │   │
│  │    "user_id": "user_001",                                  │   │
│  │    "user_query": "查詢料號庫存",                            │   │
│  │    "intent_name": "BUSINESS_QUERY",                        │   │
│  │    "action_strategy": "ROUTE_TO_AGENT",                    │   │
│  │    "confidence": 0.95,                                     │   │
│  │    "state": "COMPLETED",                                   │   │
│  │    "state_history": [...],                                 │   │
│  │    "created_at": "2026-03-03T10:00:00Z",                 │   │
│  │    "updated_at": "2026-03-03T10:00:01Z"                  │   │
│  │  }                                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心組件

| 組件 | 職責 | 位置 |
|------|------|------|
| `IntentRoutingStateManager` | 狀態機管理器，負責創建、更新、查詢狀態 | `agents/services/intent_routing_state_manager.py` |
| `IntentRoutingState` | 狀態數據模型 | `services/api/models/intent_routing_state.py` |
| API 端點 | 提供狀態查詢介面 | `api/routers/intent_routing.py` |

---

## 3. 數據模型

### 3.1 狀態類型

| 狀態 | 描述 | 持續時間 |
|------|------|----------|
| `PENDING` | 初始狀態，等待分類 | < 1s |
| `DISPATCHED` | 已分發到意圖分類 | 1-2s |
| `CLASSIFYING` | 正在進行意圖分類 | 2-5s |
| `ROUTE_DECIDED` | 路由決策已生成 | < 1s |
| `EXECUTING` | 正在執行路由目標 | 5-60s |
| `COMPLETED` | 完成 | - |
| `FAILED` | 失敗 | - |

### 3.2 意圖類型

| Intent | 描述 | 處理策略 |
|--------|------|----------|
| `GREETING` | 問候語 | DIRECT_RESPONSE |
| `THANKS` | 感謝 | DIRECT_RESPONSE |
| `CHITCHAT` | 閒聊 | DIRECT_RESPONSE |
| `GENERAL_QA` | 一般問答 | KNOWLEDGE_RAG |
| `BUSINESS_QUERY` | 業務查詢 | ROUTE_TO_AGENT |
| `BUSINESS_ACTION` | 業務操作 | ROUTE_TO_AGENT |
| `AGENT_WORK` | Agent 工作 | ROUTE_TO_AGENT |
| `UNKNOWN` | 未知 | DIRECT_RESPONSE |

### 3.3 處理策略

| 策略 | 描述 |
|------|------|
| `DIRECT_RESPONSE` | 直接使用 GenAI 回覆 |
| `KNOWLEDGE_RAG` | 知識庫檢索 |
| `ROUTE_TO_AGENT` | 轉發到外部 Agent |

### 3.4 數據結構

```python
class IntentRoutingState(BaseModel):
    """意圖路由狀態模型"""
    
    # 識別字段
    _key: str = Field(..., description="ArangoDB 文檔 key")
    request_id: str = Field(..., description="Request ID")
    session_id: str = Field(..., description="Session ID")
    task_id: Optional[str] = Field(None, description="Task ID")
    user_id: str = Field(..., description="用戶 ID")
    
    # 用戶輸入
    user_query: str = Field(..., description="用戶原始查詢")
    
    # 分類結果
    intent_name: str = Field(..., description="意圖類型")
    action_strategy: str = Field(..., description="處理策略")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    
    # 路由目標
    target_agent_id: Optional[str] = Field(None, description="目標 Agent ID")
    target_endpoint: Optional[str] = Field(None, description="目標端點 URL")
    
    # 執行結果
    execution_result: Optional[Dict[str, Any]] = Field(None, description="執行結果")
    execution_error: Optional[str] = Field(None, description="執行錯誤")
    
    # 狀態追蹤
    state: str = Field(..., description="當前狀態")
    state_history: List[StateTransition] = Field(default_factory=list, description="狀態歷史")
    
    # 時間戳
    created_at: datetime = Field(default_factory=datetime.utcnow, description="創建時間")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新時間")


class StateTransition(BaseModel):
    """狀態轉換記錄"""
    
    from_state: str = Field(..., description="來源狀態")
    to_state: str = Field(..., description="目標狀態")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="轉換時間")
    metadata: Optional[Dict[str, Any]] = Field(None, description="轉換元數據")
```

---

## 4. API 設計

### 4.1 創建狀態

**POST** `/api/v1/intent-routing/state`

```json
{
  "request_id": "req_123",
  "session_id": "sess_abc",
  "task_id": "task_xyz",
  "user_id": "user_001",
  "user_query": "查詢料號 ABC-123 的庫存"
}
```

Response:
```json
{
  "status": "success",
  "data": {
    "_key": "irs_xxx",
    "state": "PENDING",
    "created_at": "2026-03-03T10:00:00Z"
  }
}
```

### 4.2 更新狀態

**PUT** `/api/v1/intent-routing/state/{state_key}`

```json
{
  "state": "DISPATCHED",
  "intent_name": "BUSINESS_QUERY",
  "action_strategy": "ROUTE_TO_AGENT",
  "confidence": 0.95,
  "target_agent_id": "mm-agent",
  "target_endpoint": "http://localhost:8003/execute"
}
```

### 4.3 查詢狀態

**GET** `/api/v1/intent-routing/state/{state_key}`

Response:
```json
{
  "status": "success",
  "data": {
    "_key": "irs_xxx",
    "request_id": "req_123",
    "user_query": "查詢料號 ABC-123 的庫存",
    "intent_name": "BUSINESS_QUERY",
    "action_strategy": "ROUTE_TO_AGENT",
    "confidence": 0.95,
    "state": "COMPLETED",
    "state_history": [
      {"from_state": "PENDING", "to_state": "DISPATCHED", "timestamp": "..."},
      {"from_state": "DISPATCHED", "to_state": "CLASSIFYING", "timestamp": "..."},
      {"from_state": "CLASSIFYING", "to_state": "ROUTE_DECIDED", "timestamp": "..."},
      {"from_state": "ROUTE_DECIDED", "to_state": "EXECUTING", "timestamp": "..."},
      {"from_state": "EXECUTING", "to_state": "COMPLETED", "timestamp": "..."}
    ],
    "created_at": "2026-03-03T10:00:00Z",
    "updated_at": "2026-03-03T10:00:05Z"
  }
}
```

### 4.4 按會話查詢歷史

**GET** `/api/v1/intent-routing/history`

Query Parameters:
- `session_id`: Session ID
- `user_id`: User ID (可選)
- `limit`: 返回數量限制 (默認 20)

---

## 5. 實現計劃

### 5.1 Phase 1: 數據模型和基礎設施

1. 創建數據模型 `IntentRoutingState`
2. 創建 ArangoDB Collection `intent_routing_state`
3. 實現基礎的 CRUD 操作

### 5.2 Phase 2: 狀態機管理器

1. 實現 `IntentRoutingStateManager` 類
2. 實現狀態轉換邏輯
3. 實現狀態歷史記錄

### 5.3 Phase 3: 集成到 Chat 流程

1. 在 `_process_chat_request` 中集成狀態機
2. 在 OrchestratorIntentRAG 調用前後更新狀態
3. 在路由執行前後更新狀態

### 5.4 Phase 4: API 端點

1. 實現狀態查詢端點
2. 實現歷史查詢端點
3. 添加權限控制

---

## 6. 待確定事項

1. **Collection 命名**: `intent_routing_state` 是否合適？
2. **數據保留策略**: 歷史數據保留多久？30天？
3. **權限控制**: 是否需要租戶隔離？

---

## 7. 參考文檔

- [OrchestratorIntentRAG 客戶端](../agents/services/orchestrator_intent_rag_client.py)
- [flowchat.md](../flowchat.md)
- [現有 ObservabilityInfo 模型](../services/api/models/chat.py)
