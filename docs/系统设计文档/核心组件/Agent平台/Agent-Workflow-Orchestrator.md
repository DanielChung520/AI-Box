# Agent Workflow Orchestrator 架構設計

**版本**: v1.0.0  
**日期**: 2026-02-08  
**作者**: AI-Box Team

> **本文檔描述**：所有 Agent（MM-Agent、KA-Agent、Data-Agent 等）共用的 ReAct 工作流執行引擎與 Saga 補償模式的整合設計

---

## 1. 概述

本文檔描述 AI-Box 平台中用於**所有 Agent 的通用工作流編排服務**，目標是提供企業級的 AI 工作流可靠性保障。

### 1.1 設計目標

| 目標 | 說明 |
|------|------|
| **狀態持久化** | 工作流狀態存入 ArangoDB，服務重啟可恢復 |
| **Saga 補償** | 每步執行記錄補償動作，失敗時自動回滾 |
| **RQ 任務隊列** | 利用現有 RQ + Redis 實現非同步執行 |
| **斷線恢復** | 用戶可透過 session_id 恢復工作流 |
| **Agent 通用** | MM-Agent、KA-Agent、Data-Agent 等皆可使用 |

### 1.2 核心元件

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Agent Workflow Orchestrator                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  Planner   │  │  Executor   │  │  Tracker    │  │  SagaMgr   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │  RQ Queue    │      │  ArangoDB    │      │   Redis      │
    │ (非同步執行)  │      │  (持久化)    │      │  (鎖/緩存)   │
    └──────────────┘      └──────────────┘      └──────────────┘
```

### 1.3 適用 Agent

| Agent | 使用場景 |
|-------|----------|
| **MM-Agent** | 庫存管理、ABC 分類、採購建議 |
| **KA-Agent** | 知識檢索、問答系統、文件摘要 |
| **Data-Agent** | 數據查詢、SQL 生成、報表生成 |
| **自定義 Agent** | 任何需要多步驟執行的業務場景 |

---

## 2. Agent-Todo 作業規範

### 2.1 Todo 狀態機

```
                    ┌────────────────┐
                    │    PENDING    │ ←─── 新建
                    └───────┬────────┘
                            │ dispatch
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  DISPATCHED │ │   FAILED     │ │  (重試)      │
    └───────┬──────┘ └───────┬──────┘ └──────┬───────┘
            │                │               │
            │ exec           │ retry         │
            ▼                │               │
    ┌──────────────┐         │               │
    │  EXECUTING  │ ────────┴───────────────┘
    └───────┬──────┘
            │
    ┌───────┴───────┐
    ▼               ▼
┌──────────┐   ┌──────────┐
│ COMPLETED│   │  FAILED   │
└──────────┘   └─────┬──────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
        ┌─────────┐    ┌─────────┐
        │  Retry  │    │ Compensate
        └─────────┘    └─────────┘
```

### 2.2 狀態轉移規則

| 當前狀態 | 下一狀態 | 事件 | 說明 |
|----------|----------|------|------|
| PENDING | DISPATCHED | dispatched | 已分派 |
| DISPATCHED | EXECUTING | agent_ack | Agent 確認執行 |
| DISPATCHED | FAILED | fail | 分派失敗 |
| EXECUTING | COMPLETED | done | 執行成功 |
| EXECUTING | FAILED | fail | 執行失敗 |
| FAILED | DISPATCHED | retry | 重試 |
| FAILED | COMPLETED | skip | 跳過/補償 |

### 2.3 Todo 類型定義

```python
class TodoType(str, Enum):
    KNOWLEDGE_RETRIEVAL = "KNOWLEDGE_RETRIEVAL"  # 知識檢索
    DATA_QUERY = "DATA_QUERY"                      # 數據查詢
    COMPUTATION = "COMPUTATION"                    # 計算任務
    RESPONSE_GENERATION = "RESPONSE_GENERATION"   # 回覆生成
    CUSTOM = "CUSTOM"                             # 自定義動作
```

### 2.4 前置條件檢查

每個 Todo 執行前需檢查：

| 條件類型 | 檢查內容 |
|----------|----------|
| SCHEMA_READY | 數據庫 Schema 是否就緒 |
| DATA_AVAILABLE | 依賴數據是否可用 |
| AGENT_AVAILABLE | 目標服務是否可訪問 |
| DEPENDENCY_COMPLETED | 前置步驟是否完成 |
| USER_CONFIRMED | 是否需要用戶確認 |

---

## 3. Saga 補償模式

### 3.1 Saga 執行流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Saga 執行流程                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 1: 知識檢索 ──✅──→ 記錄補償: delete_knowledge_cache              │
│                                                                         │
│  Step 2: 數據查詢 ──✅──→ 記錄補償: rollback_temp_table                  │
│                                                                         │
│  Step 3: 資料清理 ──✅──→ 記錄補償: restore_original_data               │
│                                                                         │
│  Step 4: ABC計算  ──❌──→ 觸發補償鏈                                     │
│                    │                                                   │
│                    ▼                                                   │
│              倒序執行補償:                                               │
│              1. restore_original_data                                   │
│              2. rollback_temp_table                                     │
│              3. delete_knowledge_cache                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 補償動作定義

```python
class CompensationAction(BaseModel):
    """補償動作定義"""

    action_id: str
    step_id: int
    action_type: str          # 原動作類型
    compensation_type: str    # 補償類型
    params: Dict[str, Any]   # 補償參數
    created_at: datetime


class SagaStep(BaseModel):
    """Saga 步驟定義"""

    step_id: int
    action: str               # 執行動作
    compensation: str         # 補償動作
    parameters: Dict[str, Any]
    result_key: Optional[str]  # 結果存儲鍵
```

### 3.3 補償策略

| 場景 | 補償策略 |
|------|----------|
| 網絡超時 | 重試 3 次 → 失敗 → 執行補償 |
| 服務不可用 | 快速失敗 → 執行補償 |
| 數據錯誤 | 標記失敗 → 執行補償 |
| 用戶取消 | 執行所有已完成步驟的補償 |

---

## 4. RQ 任務隊列整合

### 4.1 使用現有 RQ Queue

```python
from database.rq.queue import get_task_queue, GENAI_CHAT_QUEUE

# 獲取工作流執行隊列
workflow_queue = get_task_queue(GENAI_CHAT_QUEUE)
```

### 4.2 任務定義

```python
from rq import job
from redis import Redis
from rq.connection import Connection

@job(workflow_queue, connection=Redis())
def execute_step_task(
    workflow_id: str,
    step_id: int,
    action_type: str,
    instruction: str,
    parameters: Dict[str, Any],
    compensation_key: str,
    agent_name: str,  # 新增：執行此步驟的 Agent 名稱
):
    """執行單一步驟的 RQ 任務"""
    from shared.agents.workflow.saga_executor import execute_with_compensation

    result = await execute_with_compensation(
        workflow_id=workflow_id,
        step_id=step_id,
        action_type=action_type,
        instruction=instruction,
        parameters=parameters,
        compensation_key=compensation_key,
        agent_name=agent_name,
    )
    return result.model_dump()
```

### 4.3 重試配置

```python
from rq.retry import Retry
from shared.agents.todo.retry import RetryConfig

retry_config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    jitter=True,
)

# RQ 重試配置
rq_retry = Retry(
    max=retry_config.max_attempts,
    interval=[retry_config.initial_delay * (retry_config.backoff_factor ** i)
              for i in range(retry_config.max_attempts)],
)

# 入隊執行
job = workflow_queue.enqueue(
    execute_step_task,
    workflow_id=wf_id,
    step_id=step_id,
    agent_name=agent_name,  # 指定執行的 Agent
    retry=rq_retry,
)
```

---

## 5. 工作流持久化

### 5.1 WorkflowState 結構

```python
class WorkflowState(BaseModel):
    """工作流狀態（持久化到 ArangoDB）"""

    workflow_id: str                    # 工作流唯一標識
    session_id: str                    # 用戶會話 ID
    agent_name: str                    # 執行此工作流的 Agent 名稱
    instruction: str                    # 原始指令
    task_type: str                     # 任務類型

    # 計劃
    plan: Optional[Dict[str, Any]] = None
    steps: List[SagaStep] = []

    # 執行狀態
    current_step: int = 0
    completed_steps: List[int] = []
    failed_steps: List[int] = []

    # 結果
    results: Dict[str, Any] = {}
    final_response: Optional[str] = None

    # Saga 補償
    compensations: List[CompensationAction] = []
    compensation_history: List[Dict] = []

    # 狀態
    status: str = "pending"           # pending/running/completed/failed/compensating
    error: Optional[str] = None

    # 時間戳
    created_at: datetime = datetime.utcnow()
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 用戶交互
    waiting_for_user: bool = False
    user_response: Optional[str] = None
```

### 5.2 ArangoDB Collection

```javascript
// Collection: ai_workflows
{
  "_key": "WF-20260208-ABC123",
  "workflow_id": "WF-20260208-ABC123",
  "session_id": "sess-001",
  "agent_name": "mm-agent",           // 新增：Agent 名稱
  "instruction": "請幫我做庫存ABC分類表",
  "task_type": "abc_classification",
  "status": "running",
  "current_step": 3,
  "completed_steps": [1, 2],
  "failed_steps": [],
  "results": {
    "1": {"knowledge": "...", "source": "ka_agent"},
    "2": {"data": [...], "sql": "..."}
  },
  "compensations": [
    {
      "action_id": "COMP-001",
      "step_id": 1,
      "action_type": "knowledge_retrieval",
      "compensation_type": "delete_cache",
      "params": {"query_hash": "..."}
    }
  ],
  "created_at": "2026-02-08T10:00:00Z",
  "updated_at": "2026-02-08T10:05:00Z"
}

// Collection: ai_workflow_history
{
  "_key": "HIST-WF-20260208-ABC123",
  "workflow_id": "WF-20260208-ABC123",
  "event": "step_completed",
  "step_id": 2,
  "details": {...},
  "timestamp": "2026-02-08T10:03:00Z"
}
```

---

## 6. API Endpoints

### 6.1 工作流管理

| Method | Endpoint | 功能 |
|--------|----------|------|
| POST | `/api/v1/workflows` | 建立新工作流 |
| GET | `/api/v1/workflows/{id}` | 獲取工作流狀態 |
| POST | `/api/v1/workflows/{id}/execute-step` | 執行下一步 |
| POST | `/api/v1/workflows/{id}/resume` | 恢復工作流 |
| POST | `/api/v1/workflows/{id}/cancel` | 取消工作流 |
| DELETE | `/api/v1/workflows/{id}` | 刪除工作流 |
| GET | `/api/v1/workflows/{id}/history` | 獲取執行歷史 |
| GET | `/api/v1/workflows?session_id={id}` | 獲取會話的所有工作流 |

### 6.2 補償管理

| Method | Endpoint | 功能 |
|--------|----------|------|
| POST | `/api/v1/workflows/{id}/compensate` | 手動觸發補償 |
| GET | `/api/v1/workflows/{id}/compensation-status` | 查詢補償狀態 |

---

## 7. 執行流程詳細設計

### 7.1 建立工作流

```python
from shared.agents.workflow import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()

async def create_workflow(
    instruction: str,
    session_id: str,
    agent_name: str,
    user_id: Optional[str] = None,
) -> WorkflowState:
    """建立新工作流"""

    # 1. 創建工作流（LLM 生成計劃 + 初始化狀態）
    workflow = await orchestrator.create(
        instruction=instruction,
        session_id=session_id,
        agent_name=agent_name,
        user_id=user_id,
    )

    return workflow
```

### 7.2 執行步驟（帶 Saga）

```python
async def execute_step(
    workflow_id: str,
    step_id: int,
    user_response: Optional[str] = None,
) -> ExecutionResult:
    """執行單一步驟（帶 Saga 補償）"""

    # 1. 獲取工作流狀態
    workflow = await orchestrator.get_state(workflow_id)

    # 2. 檢查狀態
    if workflow.status not in ["pending", "running"]:
        raise InvalidWorkflowStatusError(workflow.status)

    # 3. 獲取步驟
    step = workflow.get_step(step_id)

    # 4. RQ 任務入隊
    job = workflow_queue.enqueue(
        execute_step_task,
        workflow_id=workflow_id,
        step_id=step_id,
        action_type=step.action,
        instruction=step.instruction,
        parameters=step.parameters,
        compensation_key=f"{workflow_id}:{step_id}",
        agent_name=workflow.agent_name,
        retry=rq_retry,
    )

    # 5. 等待結果
    result = job.result

    # 6. 更新狀態
    if result.success:
        await orchestrator.complete_step(workflow_id, step_id, result.data)
    else:
        await orchestrator.fail_step(workflow_id, step_id, result.error)

    return result
```

### 7.3 補償執行

```python
async def execute_compensation(workflow_id: str) -> CompensationResult:
    """執行補償（倒序）"""
    return await orchestrator.compensate(workflow_id)
```

---

## 8. 斷線恢復設計

### 8.1 恢復流程

```
用戶斷線 → 重新連線 → 獲取 session_id → 查詢工作流狀態 → 恢復執行

1. 用戶訪問 /api/v1/workflows?session_id=xxx
2. 返回該會話的所有工作流（含狀態）
3. 用戶選擇繼續執行的工作流
4. 調用 /api/v1/workflows/{id}/resume
5. 系統恢復執行
```

### 8.2 Heartbeat 機制

```python
class HeartbeatManager:
    """心跳管理器"""

    async def start_heartbeat(
        self,
        workflow_id: str,
        step_id: int,
        interval: float = 5.0,
    ):
        """啟用心跳"""
        while True:
            await arango.update_heartbeat(workflow_id, step_id)
            await asyncio.sleep(interval)

    async def check_timeout(self, workflow_id: str, timeout: float = 300.0) -> bool:
        """檢查是否超時"""
        last_heartbeat = await arango.get_last_heartbeat(workflow_id)
        if not last_heartbeat:
            return True

        elapsed = (datetime.utcnow() - last_heartbeat).total_seconds()
        return elapsed > timeout
```

---

## 9. Agent 整合範例

### 9.1 MM-Agent 整合

```python
# mm_agent/chain/react_executor.py
from shared.agents.workflow import WorkflowOrchestrator

class MMReActExecutor:
    def __init__(self):
        self.orchestrator = WorkflowOrchestrator()

    async def execute_workflow(self, instruction: str, session_id: str):
        # 創建工作流
        workflow = await self.orchestrator.create(
            instruction=instruction,
            session_id=session_id,
            agent_name="mm-agent",
        )

        # 執行所有步驟
        while workflow.current_step < len(workflow.steps):
            result = await self.orchestrator.execute_step(
                workflow.workflow_id,
                workflow.current_step + 1,
            )
            if not result.success:
                await self.orchestrator.compensate(workflow.workflow_id)
                break

        return self.orchestrator.get_result(workflow.workflow_id)
```

### 9.2 KA-Agent 整合

```python
# ka_agent/workflow.py
from shared.agents.workflow import WorkflowOrchestrator

class KAWorkflowExecutor:
    def __init__(self):
        self.orchestrator = WorkflowOrchestrator()

    async def process_query(self, query: str, session_id: str):
        # 創建工作流（LLM 會規劃：知識檢索 → 生成答案）
        workflow = await self.orchestrator.create(
            instruction=query,
            session_id=session_id,
            agent_name="ka-agent",
        )

        # 執行
        return await self.orchestrator.execute_all(workflow.workflow_id)
```

---

## 10. 監控與審計

### 10.1 監控指標

| 指標 | 說明 |
|------|------|
| workflow_created | 工作流創建數 |
| workflow_completed | 工作流完成數 |
| workflow_failed | 工作流失敗數 |
| compensation_triggered | 補償觸發次數 |
| step_execution_time | 步驟執行時間 |

### 10.2 審計日誌

```python
class AuditLogger:
    """審計日誌記錄器"""

    async def log_event(
        self,
        event_type: str,
        workflow_id: str,
        step_id: Optional[int],
        actor: str,
        agent_name: str,
        details: Dict[str, Any],
    ):
        """記錄審計事件"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "workflow_id": workflow_id,
            "step_id": step_id,
            "actor": actor,
            "agent_name": agent_name,
            "details": details,
        }
        await arango.create_audit_log(entry)
```

---

## 11. 實作順序

### Phase 1: 基礎設施（1-2 天）

- [ ] 創建 `shared/agents/workflow/` 目錄結構
- [ ] 實現 `WorkflowState` 模型（持久化版本）
- [ ] 實現 ArangoDB CRUD 操作
- [ ] 實現 Saga 補償動作定義
- [ ] 實現 `SagaManager` 類

### Phase 2: RQ 整合（1-2 天）

- [ ] 封裝 RQ 任務執行器
- [ ] 實現帶重試的步驟執行
- [ ] 實現 Heartbeat 機制
- [ ] 實現斷線恢復 API

### Phase 3: Agent 整合（1-2 天）

- [ ] 更新 MM-Agent 使用新的 Orchestrator
- [ ] 整合 KA-Agent
- [ ] 整合 Data-Agent（可選）
- [ ] 實現審計日誌
- [ ] 整合測試

---

## 12. 代碼結構

```
shared/agents/workflow/
├── __init__.py
├── schema.py              # 數據模型（WorkflowState, SagaStep, CompensationAction）
├── state_machine.py       # 狀態機（來自 shared/agents/todo/state_machine.py）
├── planner.py             # LLM 計劃生成器
├── executor.py            # 步驟執行器
├── saga.py               # Saga 補償管理器
├── api.py                # API 路由（可選）
└── registry.py            # Agent 註冊表（用於查找 Agent 服務）
```

---

## 13. 參考資料

- [Agent-Todo Schema](../../../../shared/agents/todo/schema.py)
- [Agent-Todo State Machine](../../../../shared/agents/todo/state_machine.py)
- [Agent-Todo Preconditions](../../../../shared/agents/todo/preconditions.py)
- [Agent-Todo Retry](../../../../shared/agents/todo/retry.py)
- [RQ Queue](../../../../database/rq/queue.py)

---

## 附錄 A: 錯誤碼定義

| 錯誤碼 | 說明 |
|--------|------|
| WORKFLOW_NOT_FOUND | 工作流不存在 |
| INVALID_STATUS | 狀態轉移無效 |
| STEP_FAILED | 步驟執行失敗 |
| COMPENSATION_FAILED | 補償執行失敗 |
| PRECONDITION_FAILED | 前置條件檢查失敗 |
| TIMEOUT | 執行超時 |
| USER_CANCELLED | 用戶取消 |
| AGENT_NOT_FOUND | Agent 未註冊 |
| AGENT_UNAVAILABLE | Agent 不可用 |
