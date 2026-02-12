# Agent Todo 作業規範

**版本**: 1.0  
**創建日期**: 2026-02-07  
**最後更新**: 2026-02-07  
**狀態**: Spec-First Development（逐步實作）

---

## 進度管制表

### 迭代總覽

| 迭代 | 狀態 | 開始日期 | 完成日期 | 說明 |
|------|------|----------|----------|-------|
| **v1.0** | ✅ 已完成 | 2026-02-07 | 2026-02-07 | Todo Schema、狀態機、ArangoDB Client、MM-Agent 整合 |
| **v1.1** | ✅ 已完成 | 2026-02-07 | 2026-02-07 | 前置條件檢查、重試策略、心跳回報 |
| **v2.0** | 📋 規劃中 | TBD | TBD | Artifacts、Context Refs、Dispatch API |

---

### v1.1 進度詳情

| 項目 | 文件路徑 | 狀態 | 備註 |
|------|----------|------|-------|
| Preconditions | `/home/daniel/ai-box/shared/agents/todo/preconditions.py` | ✅ 完成 | 含 Schema、Data、Agent 檢查 |
| Retry Policy | `/home/daniel/ai-box/shared/agents/todo/retry.py` | ✅ 完成 | 指數退避 + 熔斷器 |
| Heartbeat | `/home/daniel/ai-box/shared/agents/contracts/heartbeat.py` | ✅ 完成 | 進度回報 + 狀態追蹤 |

---

### v1.0 進度詳情

| 項目 | 文件路徑 | 狀態 | 備註 |
|------|----------|------|-------|
| Todo Schema | `/home/daniel/ai-box/shared/agents/todo/schema.py` | ✅ 完成 | 含 `TodoState`, `TodoType`, `ExecutionResult` |
| State Machine | `/home/daniel/ai-box/shared/agents/todo/state_machine.py` | ✅ 完成 | 含狀態轉移驗證 |
| ArangoDB Client | `/home/daniel/ai-box/shared/database/arango_client.py` | ✅ 完成 | 從 `.env` 讀取認證 |
| MM-Agent 整合 | `/home/daniel/ai-box/datalake-system/mm_agent/chain/react_executor.py` | ✅ 完成 | `TodoTracker` 類 |
| API 端點 | `/home/daniel/ai-box/datalake-system/mm_agent/main.py` | ✅ 完成 | `/api/v1/chat/auto-execute` |
| 測試驗證 | MM-Agent 運行 | ✅ 完成 | 工作流正常執行 |

---

### 已知問題

| 問題 | 狀態 | 說明 |
|------|------|-------|
| ArangoDB 唯一鍵衝突 | ✅ 已修復 | 使用 `uuid` 產生唯一 `_key` |
| MM-Agent 端口 | ✅ 已修復 | 8003 正常運行 |

---

## 代碼結構

```
/home/daniel/ai-box/shared/
├── agents/
│   ├── todo/
│   │   ├── __init__.py              # v1.0 ✅
│   │   ├── schema.py                 # v1.0 ✅
│   │   ├── state_machine.py          # v1.0 ✅
│   │   ├── preconditions.py          # v1.1 ✅
│   │   └── retry.py                 # v1.1 ✅
│   └── contracts/
│       └── heartbeat.py              # v1.1 ✅
└── database/
    └── arango_client.py            # v1.0 ✅
```

---

## MM-Agent 服務端口

| 服務 | 端口 | 狀態 | 說明 |
|------|------|------|-------|
| API Gateway | 8000 | ✅ 運行中 | AI-Box 主 API |
| MM-Agent | **8003** | ✅ 運行中 | ReAct 工作流引擎 |
| Vector Service | 8001 | ✅ 運行中 | ChromaDB |

---

**文件更新日期**: 2026-02-07

---

## 1. 共享基礎設施

### 1.1 代碼位置

```
/home/daniel/ai-box/shared/
├── agents/                          # 共享 Agent 基礎設施
│   ├── todo/                        # Todo 核心模組
│   │   ├── __init__.py
│   │   ├── schema.py                # Todo Schema 定義
│   │   ├── state_machine.py         # 狀態機引擎
│   │   ├── executor.py              # 執行器基類
│   │   └── errors.py                # 結構化錯誤定義
│   ├── exceptions/                  # 自定義異常
│   │   ├── __init__.py
│   │   ├── transition_error.py
│   │   └── precondition_error.py
│   └── contracts/                   # 執行契約
│       ├── __init__.py
│       ├── base_contract.py
│       └── heartbeat.py
├── database/                        # 共享資料庫
│   └── arango_client.py             # AI-Box ArangoDB 公共庫客戶端
└── utils/                           # 共享工具
    └── __init__.py
```

### 1.2 ArangoDB 公共庫配置

```json
{
  "host": "localhost:8529",
  "database": "ai_box_shared",
  "collection_prefix": "s_",
  "auth": ["root", "password"]
}
```

**Collection 命名規範**：
- `s_todos` - Todo 主表
- `s_todo_history` - 狀態轉移歷史
- `s_todo_artifacts` - 產出物清單
- `s_todo_contexts` - 上下文引用

---

## 2. ✅ v1.0 已完成（本次迭代）

### 2.1 Todo Schema（基礎結構）

```python
# shared/agents/todo/schema.py

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class TodoState(str, Enum):
    """Todo 狀態全集（不可擴充）"""
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TodoType(str, Enum):
    """任務類型（正面表列）"""
    KNOWLEDGE_RETRIEVAL = "KNOWLEDGE_RETRIEVAL"
    DATA_QUERY = "DATA_QUERY"
    COMPUTATION = "COMPUTATION"
    RESPONSE_GENERATION = "RESPONSE_GENERATION"
    NOTIFICATION = "NOTIFICATION"


class ExecutionResult(BaseModel):
    """執行結果結構"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional["StructuredError"] = None
    observation: str = ""


class StructuredError(BaseModel):
    """結構化錯誤"""
    code: str
    message: str
    context: Optional[Dict[str, Any]] = None
    recoverable: bool = False


class Todo(BaseModel):
    """Todo 基礎結構"""
    todo_id: str = Field(default_factory=lambda: f"TODO-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}")
    type: TodoType
    state: TodoState = TodoState.PENDING
    owner_agent: str
    instruction: str
    
    input: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[ExecutionResult] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
```

### 2.2 狀態機引擎

```python
# shared/agents/todo/state_machine.py

from typing import Dict, Set
from .schema import TodoState

VALID_TRANSITIONS: Dict[TodoState, Set[TodoState]] = {
    TodoState.PENDING: {TodoState.DISPATCHED},
    TodoState.DISPATCHED: {TodoState.EXECUTING, TodoState.FAILED},
    TodoState.EXECUTING: {TodoState.COMPLETED, TodoState.FAILED},
    TodoState.FAILED: {TodoState.DISPATCHED, TodoState.COMPLETED},
}


class TodoStateMachine:
    """Todo 狀態機"""
    
    @staticmethod
    def can_transition(current: TodoState, next_state: TodoState) -> bool:
        """檢查是否允許狀態轉移"""
        return next_state in VALID_TRANSITIONS.get(current, set())
    
    @staticmethod
    def validate_transition(current: TodoState, next_state: TodoState) -> None:
        """驗證狀態轉移，不允許則拋異常"""
        if not TodoStateMachine.can_transition(current, next_state):
            raise ValueError(f"Invalid transition: {current} -> {next_state}")
```

### 2.3 ArangoDB 客戶端

```python
# shared/database/arango_client.py

from typing import Optional, List, Dict, Any
from arango import ArangoClient
from shared.agents.todo.schema import Todo


class SharedArangoClient:
    """AI-Box 共享 ArangoDB 客戶端"""
    
    def __init__(self, host: str = "localhost:8529", db_name: str = "ai_box_shared"):
        self.client = ArangoClient(host=host)
        self.db = self.client.db(db_name)
        self._ensure_collections()
    
    def _ensure_collections(self):
        """確保 Collection 存在"""
        collections = ["s_todos", "s_todo_history"]
        for coll_name in collections:
            if not self.db.has_collection(coll_name):
                self.db.create_collection(coll_name)
    
    async def create_todo(self, todo: Todo) -> str:
        """建立 Todo"""
        doc = todo.model_dump()
        doc["_key"] = todo.todo_id
        self.db.collection("s_todos").insert(doc)
        return todo.todo_id
    
    async def update_todo_state(self, todo_id: str, state: str, result: Dict = None) -> bool:
        """更新 Todo 狀態"""
        update = {"state": state, "updated_at": datetime.utcnow().isoformat()}
        if result:
            update["result"] = result
        self.db.collection("s_todos").update({"_key": todo_id}, update)
        return True
    
    async def get_todo(self, todo_id: str) -> Optional[Todo]:
        """查詢 Todo"""
        doc = self.db.collection("s_todos").get(todo_id)
        if doc:
            return Todo(**doc)
        return None
```

---

## 3. ✅ v1.1 已完成

### 3.1 前後條件（Preconditions / Postconditions）

```python
# 已實作：/home/daniel/ai-box/shared/agents/todo/preconditions.py

class Precondition(BaseModel):
    """前置條件"""
    type: str  # SCHEMA_READY, DATA_AVAILABLE, etc.
    ref: str   # 引用資源


class Postcondition(BaseModel):
    """後置條件"""
    type: str   # RESULT_SCHEMA_VALID, ROW_COUNT_GT, etc.
    value: Any  # 期望值


class TodoWithConditions(Todo):
    """帶前後條件的 Todo"""
    preconditions: List[Precondition] = []
    postconditions: List[Postcondition] = []
```

### 3.2 Retry Policy

```python
# 已實作：/home/daniel/ai-box/shared/agents/todo/retry.py

class RetryPolicy(str, Enum):
    NONE = "NONE"
    LINEAR = "LINEAR"
    EXPONENTIAL_BACKOFF = "EXPONENTIAL_BACKOFF"


class TodoWithRetry(Todo):
    """帶重試策略的 Todo"""
    retry: Dict[str, Any] = {
        "max": 3,
        "policy": RetryPolicy.EXPONENTIAL_BACKOFF,
        "attempts": 0
    }
```

### 3.3 心跳與進度

```python
# 已實作：/home/daniel/ai-box/shared/agents/contracts/heartbeat.py

class Heartbeat(BaseModel):
    """心跳"""
    todo_id: str
    state: str
    progress: float = 0.0  # 0.0 - 1.0
    timestamp: datetime
    message: Optional[str] = None
```

---

## 4. 📋 v2.0 規劃中

### 4.1 Artifacts（產出物）

```python
# 規劃中

class ArtifactType(str, Enum):
    DATASET = "DATASET"
    REPORT = "REPORT"
    MODEL = "MODEL"
    DOCUMENT = "DOCUMENT"


class Artifact(BaseModel):
    """產出物"""
    artifact_id: str
    type: ArtifactType
    format: str  # JSON, CSV, PARQUET, etc.
    schema: str   # 資料 Schema 名稱
    location: str # S3 / File path
    size: Optional[int] = None
    checksum: Optional[str] = None
    created_at: datetime
```

### 4.2 Context Refs（上下文引用）

```python
# 規劃中

class ContextType(str, Enum):
    VECTOR = "VECTOR"      # 向量索引
    MEMORY = "MEMORY"       # 對話記憶
    ONTOLOGY = "ONTOLOGY"    # 本體關係


class ContextRef(BaseModel):
    """上下文引用"""
    type: ContextType
    ref_id: str  # kb:purchase_schema:v3, conv:20260129:query, etc.
```

### 4.3 Dispatch API（分派契約）

```python
# 規劃中

class DispatchRequest(BaseModel):
    """分派請求"""
    todo_id: str
    target_agent: str
    callback_url: Optional[str] = None


class DispatchResponse(BaseModel):
    """分派回應"""
    dispatched_at: datetime
    expected_completion: Optional[datetime] = None
    priority: str = "NORMAL"
```

---

## 5. 使用方式

### 5.1 AI-Box 主 API 調用

```python
# /home/daniel/ai-box/api/routers/todo.py

from fastapi import APIRouter, HTTPException
from shared.database.arango_client import SharedArangoClient
from shared.agents.todo.schema import Todo, TodoState

router = APIRouter(prefix="/api/v1/todo", tags=["todo"])

_arango = SharedArangoClient()


@router.post("/create")
async def create_todo(request: dict):
    """建立 Todo"""
    todo = Todo(**request)
    await _arango.create_todo(todo)
    return {"todo_id": todo.todo_id}


@router.post("/{todo_id}/dispatch")
async def dispatch_todo(todo_id: str, target_agent: str):
    """分派 Todo"""
    todo = await _arango.get_todo(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    # 狀態轉移：PENDING -> DISPATCHED
    await _arango.update_todo_state(todo_id, TodoState.DISPATCHED)
    
    return {"status": "dispatched", "agent": target_agent}


@router.post("/{todo_id}/complete")
async def complete_todo(todo_id: str, result: dict):
    """完成 Todo"""
    await _arango.update_todo_state(todo_id, TodoState.COMPLETED, result)
    return {"status": "completed"}
```

### 5.2 MM-Agent 調用示例

```python
# /home/daniel/ai-box/datalake-system/mm_agent/chain/todo_executor.py

from shared.database.arango_client import SharedArangoClient
from shared.agents.todo.schema import Todo, TodoType, TodoState

_arango = SharedArangoClient()


async def execute_with_todo(instruction: str, agent_type: str, execute_fn):
    """包裝執行流程為 Todo"""
    
    # 1. 建立 Todo
    todo = Todo(
        type=TodoType(agent_type),
        owner_agent=agent_type,
        instruction=instruction
    )
    await _arango.create_todo(todo)
    
    # 2. 分派
    await _arango.update_todo_state(todo.todo_id, TodoState.DISPATCHED)
    
    try:
        # 3. 執行
        result = await execute_fn()
        
        # 4. 完成
        await _arango.update_todo_state(
            todo.todo_id, 
            TodoState.COMPLETED,
            {"data": result}
        )
        return result
        
    except Exception as e:
        # 5. 失敗
        await _arango.update_todo_state(
            todo.todo_id,
            TodoState.FAILED,
            {"error": {"code": "EXECUTION_FAILED", "message": str(e)}}
        )
        raise
```

---

## 6. 遷移路線圖

### Phase 1: v1.0（當前）
```
MM-Agent
├── react_planner.py    ✅ 保持不變
├── react_executor.py   ⚠️ 添加 Todo 追蹤
└── main.py             ⚠️ 添加 Todo API 端點
```

### Phase 2: v1.1
```
MM-Agent
├── ✅ 添加 preconditions 檢查
├── ✅ 添加 retry policy
└── ✅ 添加 heartbeat 支援
```

### Phase 3: v2.0
```
共享模組
├── artifacts 存儲
├── context refs 追蹤
└── dispatch API
```

---

## 7. 測試覆蓋

### v1.0 測試

```python
# tests/shared/test_todo_schema.py

def test_todo_creation():
    todo = Todo(
        type=TodoType.DATA_QUERY,
        owner_agent="DA",
        instruction="查詢庫存"
    )
    assert todo.todo_id.startswith("TODO-")
    assert todo.state == TodoState.PENDING


def test_state_transition():
    machine = TodoStateMachine()
    assert machine.can_transition(TodoState.PENDING, TodoState.DISPATCHED)
    assert not machine.can_transition(TodoState.PENDING, TodoState.COMPLETED)
```

---

**文件結束**
