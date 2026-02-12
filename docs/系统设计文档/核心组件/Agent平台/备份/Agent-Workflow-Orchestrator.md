# Agent Workflow Orchestrator - Agent 公用工作流服務

**版本**: v1.0.0  
**日期**: 2026-02-08  
**作者**: AI-Box Team

---

## 1. 概述

本文檔描述 **Agent Workflow Orchestrator**，這是一個所有 Agent 公用的工作流服務，提供企業級的 AI 工作流可靠性保障。

### 1.1 設計目標

| 目標 | 說明 |
|------|------|
| **狀態持久化** | 工作流狀態存入 ArangoDB，服務重啟可恢復 |
| **Saga 補償** | 每步執行記錄補償動作，失敗時自動回滾 |
| **RQ 任務隊列** | 利用現有 RQ + Redis 實現非同步執行 |
| **斷線恢復** | 用戶可透過 session_id 恢復工作流 |
| **通用設計** | 所有 Agent（MM-Agent、KA-Agent、Data-Agent）都可使用 |

### 1.2 服務定位

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Agent Workflow Orchestrator                        │
│              (所有 Agent 的公用工作流服務)                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ MM-Agent   │  │ KA-Agent   │  │ Data-Agent │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │   RQ Queue  │      │  ArangoDB   │      │   Redis      │
    │ (非同步執行) │      │  (持久化)   │      │  (鎖/緩存)   │
    └──────────────┘      └──────────────┘      └──────────────┘
```

---

## 2. 核心元件

### 2.1 元件架構

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Workflow Orchestrator                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                     WorkflowService                           │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │ │
│  │  │   Planner  │  │  Executor  │  │    Saga   │          │ │
│  │  │ (LLM計劃)  │  │  (執行)    │  │  (補償)   │          │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                   Shared Components                          │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │ │
│  │  │    State   │  │   Heartbeat │  │  Recovery  │          │ │
│  │  │ (持久化)   │  │  (心跳)     │  │  (斷線恢復) │          │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 目錄結構

```
shared/agents/workflow/
├── __init__.py              # 模組導出
├── schema.py                 # 數據模型 (WorkflowState, SagaStep, Compensation)
├── state.py                 # 狀態管理器 (ArangoDB 持久化)
├── executor.py              # 執行器 (步驟執行, RQ, Heartbeat)
└── saga.py                  # Saga 補償管理器 (斷線恢復)
```

---

## 3. 數據模型

### 3.1 WorkflowState

```python
class WorkflowState(BaseModel):
    """工作流狀態（持久化到 ArangoDB）"""

    workflow_id: str           # 工作流唯一標識
    session_id: str           # 用戶會話 ID
    instruction: str          # 原始指令
    task_type: str           # 任務類型

    # 計劃
    steps: List[SagaStep]     # Saga 步驟列表

    # 執行狀態
    status: WorkflowStatus    # pending/running/completed/failed
    current_step: int         # 當前步驟
    completed_steps: List[int] # 已完成的步驟
    failed_steps: List[int]   # 失敗的步驟

    # 結果
    results: Dict[str, Any]   # 步驟結果
    final_response: str        # 最終回覆

    # Saga 補償
    compensations: List[CompensationAction]  # 補償動作
    compensation_history: List[Dict]          # 補償歷史

    # 心跳
    last_heartbeat: datetime # 最後心跳時間
```

### 3.2 SagaStep

```python
class SagaStep(BaseModel):
    """Saga 步驟定義"""

    step_id: int              # 步驟 ID
    action_type: str         # 行動類型 (knowledge_retrieval, data_query, etc.)
    description: str          # 步驟描述
    instruction: str           # 詳細執行指令

    # 補償定義
    compensation_type: str     # 補償類型
    compensation_params: Dict  # 補償參數

    # 執行狀態
    status: StepStatus        # pending/dispatched/executing/completed/failed
    retry_count: int          # 重試次數
    max_retries: int         # 最大重試次數
```

### 3.3 WorkflowStatus 狀態機

```
                    ┌────────────────┐
                    │    PENDING    │ ←─── 新建
                    └───────┬────────┘
                            │ start
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   RUNNING   │ │   PAUSED    │ │   FAILED     │
    └───────┬──────┘ └───────┬──────┘ └──────┬───────┘
            │                │               │
    ┌───────┴───────┐       │       ┌───────┴───────┐
    ▼               ▼       │       ▼               ▼
┌──────────┐  ┌──────────┐   │   ┌──────────┐  ┌──────────┐
│COMPLETED │  │ CANCELLED│   │   │RETRYABLE │  │COMPENSATE│
└──────────┘  └──────────┘   │   └──────────┘  └──────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              ┌──────────┐       ┌──────────┐
              │ RESUME   │       │ COMPENSATE│
              └──────────┘       └──────────┘
```

---

## 4. 服務接口

### 4.1 單例獲取

```python
from shared.agents.workflow import (
    get_workflow_state_manager,
    get_workflow_executor,
    get_heartbeat_manager,
    get_saga_manager,
    get_workflow_recovery_manager,
)

# 獲取管理器
state_manager = get_workflow_state_manager()
executor = get_workflow_executor()
heartbeat = get_heartbeat_manager()
saga = get_saga_manager()
recovery = get_workflow_recovery_manager()
```

### 4.2 狀態管理器

```python
# 初始化
await state_manager.initialize()

# CRUD 操作
await state_manager.create(workflow)
workflow = await state_manager.get(workflow_id)
await state_manager.update(workflow)
await state_manager.delete(workflow_id)

# 查詢
workflows = await state_manager.list_by_session(session_id)
workflows = await state_manager.list_by_status("running")

# 心跳
await state_manager.update_heartbeat(workflow_id)
is_timed_out = await state_manager.check_timeout(workflow_id, timeout=300.0)
```

### 4.3 執行器

```python
# 註冊動作處理器
executor.register_handler("custom_action", custom_handler)

# 執行步驟
result = await executor.execute_step(
    workflow=workflow,
    step=step,
    previous_results=workflow.results,
    user_response=None,
)
```

### 4.4 心跳管理器

```python
# 啟動心跳
await heartbeat.start(workflow_id, step_id, interval=5.0)

# 停止心跳
await heartbeat.stop(workflow_id)

# 檢查超時
timed_out = await heartbeat.check_all_timed_out(timeout=300.0)
```

### 4.5 Saga 補償

```python
# 註冊補償處理器
saga.register_compensation_handler(
    "rollback_table",
    rollback_table_handler,
)

# 執行所有補償
result = await saga.compensate_all(workflow)

# 從指定步驟開始補償
result = await saga.compensate_from(workflow, from_step_id=2)
```

### 4.6 斷線恢復

```python
# 獲取可恢復的工作流
recoverable = await recovery.get_recoverable_workflows(session_id)

# 恢復執行
result = await recovery.resume(workflow_id, user_response=None)

# 取消工作流（可選：強制補償）
result = await recovery.cancel(workflow_id, force=True)
```

---

## 5. RQ 任務隊列整合

### 5.1 使用現有 Queue

```python
from database.rq.queue import get_task_queue, GENAI_CHAT_QUEUE

queue = get_task_queue(GENAI_CHAT_QUEUE)
```

### 5.2 任務定義

```python
from rq import job

@job(queue)
def execute_step_task(
    workflow_id: str,
    step_id: int,
    action_type: str,
    instruction: str,
    parameters: Dict[str, Any],
    compensation_key: str,
    retry_count: int = 0,
):
    """執行單一步驟的 RQ 任務"""
    from shared.agents.workflow import get_workflow_executor

    async def run():
        executor = get_workflow_executor()
        # ... 執行邏輯
        return result

    # 運行異步任務
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(run())
    finally:
        loop.close()
```

### 5.3 重試配置

```python
from rq.retry import Retry
from shared.agents.todo.retry import RetryConfig

retry_config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    jitter=True,
)

rq_retry = Retry(
    max=retry_config.max_attempts,
    interval=[retry_config.initial_delay * (retry_config.backoff_factor ** i)
              for i in range(retry_config.max_attempts)],
)

# 入隊執行
job = queue.enqueue(
    execute_step_task,
    workflow_id=wf_id,
    step_id=step_id,
    retry=rq_retry,
)
```

---

## 6. ArangoDB Collections

### 6.1 ai_workflows

```javascript
{
  "_key": "WF-20260208-ABC123",
  "workflow_id": "WF-20260208-ABC123",
  "session_id": "sess-001",
  "user_id": "user-001",
  "instruction": "請幫我做庫存ABC分類表",
  "task_type": "abc_classification",
  "status": "running",
  "current_step": 2,
  "completed_steps": [1],
  "failed_steps": [],
  "results": {
    "1": {"knowledge": "...", "source": "ka_agent"}
  },
  "steps": [
    {
      "step_id": 1,
      "action_type": "knowledge_retrieval",
      "description": "掌握ABC理論",
      "status": "completed",
      "compensation_type": "delete_knowledge_cache"
    }
  ],
  "compensations": [
    {
      "action_id": "COMP-001",
      "step_id": 1,
      "action_type": "knowledge_retrieval",
      "compensation_type": "delete_knowledge_cache",
      "status": "pending"
    }
  ],
  "created_at": "2026-02-08T10:00:00Z",
  "updated_at": "2026-02-08T10:05:00Z"
}
```

### 6.2 ai_workflow_events

```javascript
{
  "_key": "EVT-20260208-001",
  "workflow_id": "WF-20260208-ABC123",
  "event_type": "step_completed",
  "step_id": 1,
  "to_status": "completed",
  "details": {"action_type": "knowledge_retrieval"},
  "actor": "system",
  "timestamp": "2026-02-08T10:03:00Z"
}
```

---

## 7. 使用範例

### 7.1 基本使用流程

```python
from shared.agents.workflow import (
    WorkflowState,
    SagaStep,
    get_workflow_state_manager,
    get_workflow_executor,
    get_heartbeat_manager,
)

# 1. 創建工作流
state_manager = get_workflow_state_manager()
await state_manager.initialize()

workflow = WorkflowState(
    session_id="sess-001",
    instruction="請幫我做庫存ABC分類表",
    task_type="abc_classification",
    steps=[
        SagaStep(
            step_id=1,
            action_type="knowledge_retrieval",
            description="掌握ABC理論",
            compensation_type="delete_knowledge_cache",
        ),
        SagaStep(
            step_id=2,
            action_type="data_query",
            description="查詢庫存數據",
            compensation_type="rollback_temp_table",
        ),
    ],
)

await state_manager.create(workflow)

# 2. 執行步驟
executor = get_workflow_executor()
heartbeat = get_heartbeat_manager()

step = workflow.steps[0]
await heartbeat.start(workflow.workflow_id, step.step_id)

result = await executor.execute_step(
    workflow=workflow,
    step=step,
    previous_results={},
)

await heartbeat.stop(workflow.workflow_id)

print(f"Step result: {result.success}")
```

### 7.2 處理失敗和補償

```python
from shared.agents.workflow import get_saga_manager

saga = get_saga_manager()

# 如果執行失敗，執行補償
if not result.success:
    compensation_result = await saga.compensate_all(workflow)
    print(f"Compensation completed: {compensation_result}")
```

### 7.3 斷線恢復

```python
from shared.agents.workflow import get_workflow_recovery_manager

recovery = get_workflow_recovery_manager()

# 用戶重新連線
recoverable = await recovery.get_recoverable_workflows("sess-001")
print(f"Found {len(recoverable)} recoverable workflows")

# 恢復執行
if recoverable:
    result = await recovery.resume(recoverable[0].workflow_id)
    print(f"Resumed: {result}")
```

---

## 8. Agent 整合範例

### 8.1 MM-Agent 整合

```python
from shared.agents.workflow import WorkflowState, SagaStep

# MM-Agent 生成計劃後，創建工作流
async def start_workflow(instruction: str, session_id: str):
    plan = await mm_planner.plan(instruction)

    workflow = WorkflowState(
        session_id=session_id,
        instruction=instruction,
        task_type=plan.task_type,
        steps=[
            SagaStep(
                step_id=s.step_id,
                action_type=s.action_type,
                description=s.description,
                instruction=s.instruction,
                compensation_type=get_compensation_type(s.action_type),
            )
            for s in plan.steps
        ],
    )

    await state_manager.create(workflow)
    return workflow
```

### 8.2 自定義動作處理器

```python
from shared.agents.workflow import get_workflow_executor

executor = get_workflow_executor()

@executor.register_handler("custom_analysis")
async def custom_analysis_handler(step: SagaStep, previous_results: Dict, user_response: str):
    """自定義分析處理器"""
    # 執行自定義邏輯
    result = await perform_analysis(step.instruction, previous_results)

    return TodoExecutionResult(
        success=True,
        data={"analysis_result": result},
        observation="自定義分析完成",
    )
```

---

## 9. 監控與審計

### 9.1 監控指標

| 指標 | 說明 |
|------|------|
| `workflow_created` | 工作流創建數 |
| `workflow_completed` | 工作流完成數 |
| `workflow_failed` | 工作流失敗數 |
| `compensation_triggered` | 補償觸發次數 |
| `step_execution_time` | 步驟執行時間 |
| `heartbeat_missed` | 心跳丟失次數 |

### 9.2 審計日誌

所有事件都會記錄到 `ai_workflow_events` Collection：

```javascript
{
  "event_type": "step_completed",
  "workflow_id": "WF-xxx",
  "step_id": 1,
  "actor": "MM-Agent",
  "details": {
    "action_type": "knowledge_retrieval",
    "duration_ms": 1250
  },
  "timestamp": "2026-02-08T10:00:00Z"
}
```

---

## 10. 錯誤處理

### 10.1 錯誤碼

| 錯誤碼 | 說明 |
|--------|------|
| `WORKFLOW_NOT_FOUND` | 工作流不存在 |
| `INVALID_STATUS` | 狀態轉移無效 |
| `STEP_FAILED` | 步驟執行失敗 |
| `COMPENSATION_FAILED` | 補償執行失敗 |
| `PRECONDITION_FAILED` | 前置條件檢查失敗 |
| `TIMEOUT` | 執行超時 |
| `USER_CANCELLED` | 用戶取消 |

### 10.2 恢復策略

| 場景 | 策略 |
|------|------|
| 網絡超時 | 重試 3 次 → 失敗 → 執行補償 |
| 服務不可用 | 快速失敗 → 執行補償 |
| 用戶取消 | 執行已完成步驟的補償 |
| 斷線 | 保存狀態 → 用戶可恢復 |

---

## 11. 文件清單

### 11.1 核心文件

| 文件 | 功能 |
|------|------|
| `shared/agents/workflow/__init__.py` | 模組導出 |
| `shared/agents/workflow/schema.py` | 數據模型定義 |
| `shared/agents/workflow/state.py` | 狀態管理器（持久化） |
| `shared/agents/workflow/executor.py` | 執行器 + RQ + Heartbeat |
| `shared/agents/workflow/saga.py` | Saga 補償 + 恢復 |

### 11.2 相關文件

| 文件 | 功能 |
|------|------|
| `shared/agents/todo/schema.py` | Todo Schema |
| `shared/agents/todo/state_machine.py` | 狀態機 |
| `shared/agents/todo/preconditions.py` | 前置條件 |
| `shared/agents/todo/retry.py` | 重試策略 |
| `database/rq/queue.py` | RQ 隊列 |

---

## 12. 下一步

- [ ] 整合測試
- [ ] 性能優化
- [ ] 文檔完善

---

**最後更新**: 2026-02-08
