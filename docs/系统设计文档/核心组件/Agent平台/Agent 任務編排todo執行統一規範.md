# Agent 任務編排todo執行統一規範

**版本**: v2.1.0
**創建日期**: 2026-02-08
**最後更新**: 2026-02-08
**狀態**: 正式版（BPA 架構、通用服務整合）

---

## 1. 概述

本文檔描述 **Agent 任務編排todo執行統一規範**，整合 Agent Todo 作業規範與 Workflow Orchestrator，提供企業級的 AI Agent 工作流可靠性保障。本規範涵蓋工作編排、執行、回饋及異常處理等核心功能。

### 1.1 設計目標

本規範旨在實現五個核心設計目標。首先是狀態持久化，透過 ArangoDB 儲存工作流狀態，確保服務重啟後可完整恢復執行進度，避免因系統故障導致的工作遺失。其次是 Saga 補償機制，每個執行步驟都會記錄對應的補償動作，當步驟失敗時能夠自動執行回滾，確保數據一致性。第三是 RQ 任務隊列整合，利用現有 Redis + RQ 實現非同步執行，提升系統吞吐量與可靠性。第四是斷線恢復機制，用戶可透過 session_id 恢復中斷的工作流，支援長時間運行的複雜任務。最後是通用設計，本框架適用於所有類型的 Agent，提供標準化的接口與擴展機制。

### 1.2 服務定位

本規範所定義的執行框架位於 AI-Box 架構的 Agent 層，作為所有 Agent 的共用基礎設施。

### 1.3 BPA (Business Process Agent) 定義

BPA 是**業務流程代理**，負責處理特定業務場景的對話與任務執行。

| 特性 | 說明 |
|------|------|
| **業務專用** | 針對特定業務領域（製造、採購、財務等） |
| **對話理解** | 理解用戶意圖，生成執行計劃 |
| **任務編排** | 透過 ReAct 模式編排執行步驟 |
| **統一交付** | 將執行步驟交付到 `agent_todo` 隊列 |

**現有 BPA**：
- **MM-Agent**：製造管理領域
- **PO-Agent**：採購管理領域（規劃中）
- **FI-Agent**：財務管理領域（規劃中）

### 1.4 通用服務

通用服務是 BPA 的輔助工具，提供專業能力的共享服務。

| 服務 | 角色 | 說明 |
|------|------|------|
| **Data-Agent** | 數據湖服務 | 協助 BPA 查詢數據湖數據（port: 8004） |
| **KA-Agent** | 知識庫服務 | 協助 BPA 獲取特定專業知識（port: 8000） |
| **RQ Worker** | 任務執行 | 執行 `agent_todo` 隊列中的任務 |

---

## 2. 數據模型

### 2.1 Todo Schema

Todo 是 Agent 執行作業的基本單元，每個 Todo 代表一個可追蹤的執行任務。

```python
class TodoState(str, Enum):
    """Todo 狀態全集（不可擴充）"""
    PENDING = "PENDING"       # 等待分派
    DISPATCHED = "DISPATCHED"  # 已分派
    EXECUTING = "EXECUTING"    # 執行中
    COMPLETED = "COMPLETED"    # 已完成
    FAILED = "FAILED"          # 失敗


class TodoType(str, Enum):
    """任務類型（正面表列）"""
    KNOWLEDGE_RETRIEVAL = "KNOWLEDGE_RETRIEVAL"   # 知識檢索 (KA-Agent)
    DATA_QUERY = "DATA_QUERY"                     # 資料查詢 (Data-Agent)
    DATA_CLEANING = "DATA_CLEANING"               # 資料清洗 (Data-Agent)
    COMPUTATION = "COMPUTATION"                   # 計算處理
    RESPONSE_GENERATION = "RESPONSE_GENERATION"   # 回覆生成
    NOTIFICATION = "NOTIFICATION"                  # 通知


class Todo(BaseModel):
    """Todo 基礎結構"""
    todo_id: str
    type: TodoType
    state: TodoState = TodoState.PENDING
    owner_agent: str
    instruction: str
    input: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[ExecutionResult] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
```

### 2.2 WorkflowState

WorkflowState 是工作流的頂層狀態容器，用於管理複雜的多步驟工作流程。

```python
class WorkflowStatus(str, Enum):
    """工作流狀態"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowState(BaseModel):
    """工作流狀態（持久化到 ArangoDB）"""
    workflow_id: str
    session_id: str
    instruction: str
    task_type: str
    steps: List["SagaStep"]
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: int = 0
    completed_steps: List[int] = []
    failed_steps: List[int] = []
    results: Dict[str, Any] = {}
    final_response: str = ""
    compensations: List["CompensationAction"] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 3. 狀態管理器

### 3.1 ArangoDB 客戶端

```python
class SharedArangoClient:
    """AI-Box 共享 ArangoDB 客戶端"""

    def __init__(self, host: str = "localhost:8529", db_name: str = "ai_box_shared"):
        self.client = ArangoClient(host=host)
        self.db = self.client.db(db_name, username="root", password="password")

    # Todo 操作
    async def create_todo(self, todo: Todo) -> str:
        doc = todo.model_dump()
        doc["_key"] = todo.todo_id
        self.db.collection("s_todos").insert(doc)
        return todo.todo_id

    async def update_todo(self, todo_id: str, state: str = None, result: Dict = None) -> bool:
        update = {"updated_at": datetime.utcnow().isoformat()}
        if state:
            update["state"] = state
        if result:
            update["result"] = result
        self.db.collection("s_todos").update({"_key": todo_id}, update)
        return True

    # Workflow 操作
    async def create_workflow(self, workflow: Dict) -> str:
        doc = workflow.copy()
        doc["_key"] = workflow["workflow_id"]
        self.db.collection("ai_workflows").insert(doc)
        return workflow["workflow_id"]
```

---

## 4. 執行引擎

### 4.1 WorkflowExecutor

```python
class WorkflowExecutor:
    """工作流執行器"""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, action_type: str, handler: Callable) -> None:
        """註冊動作處理器"""
        self._handlers[action_type] = handler

    async def execute_step(
        self,
        workflow: WorkflowState,
        step: SagaStep,
        previous_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """執行單一步驟"""
        handler = self._handlers.get(step.action_type)
        if not handler:
            return {"success": False, "error": f"No handler for: {step.action_type}"}

        try:
            result = await handler(step, previous_results)
            step.status = StepStatus.COMPLETED
            return result
        except Exception as e:
            step.status = StepStatus.FAILED
            return {"success": False, "error": str(e)}
```

---

## 5. Saga 補償管理

### 5.1 SagaManager

```python
class SagaManager:
    """Saga 補償管理器"""

    async def compensate_all(
        self,
        workflow: WorkflowState,
        context: Dict[str, Any],
        strategy: str = "compensate_all",
    ) -> Dict[str, Any]:
        """執行所有補償（倒序）"""
        results = []

        for step_id in reversed(workflow.completed_steps):
            compensation = None
            for comp in workflow.compensations:
                if comp.step_id == step_id and comp.status == "pending":
                    compensation = comp
                    break

            if compensation:
                result = await self.execute_compensation(compensation, context)
                results.append({"step_id": step_id, "success": result.get("success")})

        return {"total": len(results), "results": results}
```

---

## 6. 使用方式

### 6.1 BPA RQ 整合架構

**BPA 任務執行流程**：

```
用戶輸入 → BPA (MM-Agent/PO-Agent/FI-Agent)
                  │
                  ├─ ReAct Planner 生成執行計劃
                  │
                  └─ RQ 交付 → agent_todo 隊列
                                  │
                                  └─ RQ Worker
                                         │
                                         ├─ data_query → Data-Agent (8004)
                                         ├─ knowledge_retrieval → KA-Agent (8000)
                                         └─ response_generation → LLM
```

### 6.2 Worker 啟動

```bash
# 啟動 RQ Worker
cd /home/daniel/ai-box
./scripts/start_services.sh worker

# 監控 RQ Dashboard
./scripts/start_services.sh dashboard
```

---

## 7. MM-Agent 整合範例

```python
class TodoTracker:
    """Todo 追蹤器"""

    def __init__(self):
        self._arango = SharedArangoClient()

    async def create_todo(self, step_id: int, action_type: str, instruction: str) -> str:
        """為執行步驟建立 Todo"""
        todo = Todo(
            type=TodoType(action_type.upper()),
            owner_agent="MM-Agent",
            instruction=instruction,
        )
        return await self._arango.create_todo(todo)


class ReActEngine:
    """ReAct 模式引擎"""

    def __init__(self):
        self._workflows: Dict[str, WorkflowState] = {}

    async def start_workflow(self, instruction: str, session_id: str, steps: List[Dict]) -> Dict:
        """啟動工作流程"""
        workflow = WorkflowState(
            session_id=session_id,
            instruction=instruction,
            task_type="multi_step",
            steps=[SagaStep(**s) for s in steps],
        )
        self._workflows[session_id] = workflow
        return {"success": True, "workflow_id": workflow.workflow_id}
```

---

## 8. Workflow YAML 配置與 Skills 文件轉換規範

### 8.1 設計原則

| 原則 | 說明 |
|------|------|
| **配置化優於硬編碼** | 新流程只需新增 YAML，無需修改 Python |
| **人機協作** | skills.md 供人類閱讀，YAML 供系統執行 |
| **自動轉換** | 提供轉換工具，確保一致性 |
| **可擴展** | 新增 workflow 只需新增 YAML 檔案 |

### 8.2 架構關係

```
skills.md (業務定義)
        │
        ↓ 執行 convert_skills_to_yaml.py
        │
YAML Workflow (執行格式)
        │
        ↓ workflow_loader.py 載入
        │
MM-Agent ReAct Planner
```

---

## 9. YAML Workflow 配置

### 9.1 配置結構

```yaml
# ========================================
# Workflow: <英文名稱>
# ========================================

name: "<英文名稱>"              # 唯一識別符
description: "<描述>"           # 業務目標
version: "1.0.0"                # 版本號

triggers:                       # 觸發關鍵字
  - "<關鍵字1>"
  - "<關鍵字2>"

workflow:
  steps:
    - step_id: 1
      action_type: "<動作類型>"
      description: "<簡短描述>"
      instruction: |
        <詳細指令>
```

### 9.2 支援的 Action Type

| action_type | 說明 | 關鍵字 |
|-------------|------|--------|
| `data_query` | 數據查詢 | 查詢、拉取、提供、獲取 |
| `computation` | 計算分析 | 計算、分析、處理、生成 |
| `knowledge_retrieval` | 知識檢索 | 搜尋、彙整、了解 |
| `response_generation` | 回覆生成 | 報告、回覆、通知 |
| `data_cleaning` | 資料清洗 | 檢查、確認、驗證 |

### 9.3 配置範例

```yaml
# ========================================
# Workflow: inventory_monitoring
# ========================================

name: "inventory_monitoring"
description: "確保庫存數量準確，及時發現異常"
version: "1.0.0"

triggers:
  - "庫存監控"
  - "庫存異常"
  - "安全庫存"

workflow:
  steps:
    - step_id: 1
      action_type: "data_query"
      description: "查詢 ERP 庫存資料"
      instruction: |
        向 Data-Agent 發出自然語言查詢：『請查詢 ERP 庫存表中所有物料的實際庫存數量』

    - step_id: 2
      action_type: "data_cleaning"
      description: "資料完整性檢查"
      instruction: |
        確認所有物料都有編號、庫存數量與名稱

    - step_id: 3
      action_type: "computation"
      description: "計算庫存差異"
      instruction: |
        計算每個物料庫存差異：實際庫存 - 安全庫存
```

### 9.4 目錄結構

```
mm_agent/
├── workflows/                    # Workflow 配置目錄
│   ├── inventory_monitoring.yaml
│   ├── inbound_management.yaml
│   ├── outbound_management.yaml
│   ├── inventory_counting.yaml
│   ├── replenishment_planning.yaml
│   ├── exception_handling.yaml
│   └── reporting_analysis.yaml
└── chain/
    └── workflow_loader.py        # YAML 載入器
```

---

## 10. Workflow Loader

### 10.1 核心功能

```python
# mm_agent/chain/workflow_loader.py

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

WORKFLOW_DIR = Path(__file__).parent.parent / "workflows"


@dataclass
class WorkflowStep:
    step_id: int
    action_type: str
    description: str
    instruction: str


@dataclass
class Workflow:
    name: str
    description: str
    version: str
    triggers: List[str]
    steps: List[WorkflowStep]


class WorkflowLoader:
    """工作流載入器"""

    def __init__(self, workflow_dir: Path = WORKFLOW_DIR):
        self.workflow_dir = workflow_dir
        self._workflows: Dict[str, Workflow] = {}
        self._load_all_workflows()

    def _load_all_workflows(self):
        """載入所有 YAML 工作流配置"""
        if not self.workflow_dir.exists():
            logger.warning(f"Workflow 目錄不存在: {self.workflow_dir}")
            return

        yaml_files = list(self.workflow_dir.glob("*.yaml"))
        logger.info(f"找到 {len(yaml_files)} 個 workflow YAML 檔案")

        for yaml_file in yaml_files:
            try:
                workflow = self._load_workflow(yaml_file)
                if workflow:
                    self._workflows[workflow.name] = workflow
                    logger.info(f"已載入 workflow: {workflow.name} (v{workflow.version})")
            except Exception as e:
                logger.error(f"載入 workflow 失敗 {yaml_file}: {e}")

    def _load_workflow(self, file_path: Path) -> Optional[Workflow]:
        """載入單個工作流"""
        import yaml

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        steps = []
        for step_data in data.get("workflow", {}).get("steps", []):
            step = WorkflowStep(
                step_id=step_data.get("step_id", 0),
                action_type=step_data.get("action_type", ""),
                description=step_data.get("description", ""),
                instruction=step_data.get("instruction", ""),
            )
            steps.append(step)

        return Workflow(
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            triggers=data.get("triggers", []),
            steps=steps,
        )

    def match_workflow(self, instruction: str) -> Optional[Workflow]:
        """根據指令匹配工作流"""
        instruction_lower = instruction.lower()

        for workflow in self._workflows.values():
            for trigger in workflow.triggers:
                trigger_lower = trigger.lower()
                if trigger_lower in instruction_lower:
                    logger.info(f"匹配到 workflow: {workflow.name}")
                    return workflow

        return None

    def list_workflows(self) -> List[str]:
        """列出所有已載入的工作流"""
        return list(self._workflows.keys())


_workflow_loader: Optional[WorkflowLoader] = None


def get_workflow_loader() -> WorkflowLoader:
    """取得全域工作流載入器"""
    global _workflow_loader
    if _workflow_loader is None:
        _workflow_loader = WorkflowLoader()
    return _workflow_loader
```

### 10.2 與 ReAct Planner 整合

```python
# mm_agent/chain/react_planner.py

async def plan(self, instruction: str, context: Optional[Dict[str, Any]] = None) -> TodoPlan:
    """生成工作計劃"""

    # 首先嘗試從 workflow YAML 載入匹配的流程
    try:
        from .workflow_loader import get_workflow_loader

        loader = get_workflow_loader()
        workflow = loader.match_workflow(instruction)

        if workflow:
            logger.info(f"[ReActPlanner] 從 workflow YAML 載入: {workflow.name}")
            return self._workflow_based_plan(workflow, instruction)
    except Exception as e:
        logger.warning(f"[ReActPlanner] workflow 載入失敗，回退到 LLM 生成: {e}")

    # 回退到 LLM 生成
    ...
```

---

## 11. Skills 到 YAML 轉換

### 11.1 轉換工具

**檔案**: `scripts/convert_skills_to_yaml.py`

```bash
cd /home/daniel/ai-box/datalake-system
python3 scripts/convert_skills_to_yaml.py
```

### 11.2 轉換邏輯

| skills.md 欄位 | YAML 欄位 |
|---------------|-----------|
| `name` | `name` |
| `goal` | `description` |
| `triggers` | `triggers` |
| `steps[i]` | `workflow.steps[i]` |

### 11.3 Action Type 推斷

```python
ACTION_KEYWORDS = {
    "data_query": ["查詢", "拉取", "提供", "獲取"],
    "computation": ["計算", "分析", "處理", "比較", "生成"],
    "knowledge_retrieval": ["搜尋", "彙整", "了解", "理論"],
    "response_generation": ["報告", "回覆", "通知"],
    "data_cleaning": ["檢查", "確認", "驗證", "清洗"],
}


def get_action(text):
    for act, kws in ACTION_KEYWORDS.items():
        for kw in kws:
            if kw in text:
                return act
    return "data_query"
```

### 11.4 產生的文件

執行轉換後，產生以下 YAML 檔案：

| YAML 檔案 | 來源 Skill | Steps |
|-----------|-----------|-------|
| `inventory_monitoring.yaml` | 庫存監控 | 5 |
| `inbound_management.yaml` | 入庫管理 | 5 |
| `outbound_management.yaml` | 出庫管理 | 5 |
| `inventory_counting.yaml` | 盤點管理 | 7 |
| `replenishment_planning.yaml` | 補貨計劃 | 6 |
| `exception_handling.yaml` | 異常處理 | 6 |
| `reporting_analysis.yaml` | 報表分析 | 7 |

---

## 12. 觸發關鍵字配置

### 12.1 自動產生

轉換工具會從 skills.md 的 `triggers` 區塊複製觸發關鍵字。

### 12.2 手動優化

某些指令需要手動加入中文關鍵字以提升匹配率：

```python
TRIGGERS = {
    "inventory_monitoring": ["庫存監控", "庫存異常", "安全庫存"],
    "inbound_management": ["入庫", "收貨", "到貨"],
    "outbound_management": ["出庫", "揀料", "發貨"],
    "inventory_counting": ["盤點", "盤點作業", "庫存盤點"],
    "replenishment_planning": ["補貨", "補貨計劃", "再訂購點"],
    "exception_handling": ["異常處理", "異常", "缺料"],
    "reporting_analysis": ["報表分析", "庫存報表", "分析報告"],
}
```

---

## 13. 使用流程

### 13.1 新增 Workflow

**步驟 1**: 在 `skills.md` 中新增 Skill 定義

```markdown
# Skill: 新功能名稱 (New Feature)

name: new_feature
goal: "功能目標說明"

steps:
- "步驟1：執行什麼"
- "步驟2：執行什麼"

triggers:
- "觸發關鍵字1"
- "觸發關鍵字2"
```

**步驟 2**: 執行轉換

```bash
python3 scripts/convert_skills_to_yaml.py
```

**步驟 3**: 重啟 MM-Agent

```bash
pkill -f "uvicorn mm_agent.main:app"
cd /home/daniel/ai-box/datalake-system
nohup /home/daniel/ai-box/venv/bin/python -m uvicorn mm_agent.main:app --host 0.0.0.0 --port 8003 > /home/daniel/ai-box/logs/mm_agent.log 2>&1 &
```

### 13.2 測試 Workflow

```bash
curl -X POST http://localhost:8003/api/v1/chat/auto-execute \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "instruction": "<觸發關鍵字>"}'
```

### 13.3 驗證匹配

```python
from mm_agent.chain.workflow_loader import get_workflow_loader

loader = get_workflow_loader()
wf = loader.match_workflow("你的指令")
print(wf.name if wf else "未匹配")
```

---

## 14. 已知限制

| 限制 | 說明 | 解決方案 |
|------|------|----------|
| Action Type 推斷 | 關鍵字匹配可能不精確 | 手動微調 YAML |
| Triggers 解析 | skills.md 格式需一致 | 維持統一格式 |
| 全域快取 | MM-Agent 需重啟載入新 YAML | 重啟服務 |

---

## 15. 未來規劃

### 15.1 短期 (P1)

- [ ] 支援從多個來源載入 workflow
- [ ] 新增更多業務 workflow
- [ ] 完善 action_type 推斷邏輯

### 15.2 中期 (P2)

- [ ] 支援 workflow 版本管理
- [ ] 動態更新 workflow（無需重啟）
- [ ] Workflow 市場與模板庫

### 15.3 長期 (P3)

- [ ] 自動化技能推薦
- [ ] Workflow 編排視覺化
- [ ] 跨 Agent workflow 共用
