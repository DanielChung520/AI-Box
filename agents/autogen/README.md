# AutoGen 工作流整合模組

**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**最後修改日期**: 2025-01-27

## 概述

AutoGen 工作流整合模組提供 Long-horizon 自動規劃與多步驟任務處理能力，支援複雜度 60-80 的任務。本模組實現了 Execution Planning、多 Agent 協作、狀態持久化和成本控制等功能。

## 功能特性

- **Execution Planning**: 自動生成多步驟執行計劃，支援計劃驗證和重規劃
- **多 Agent 協作**: 規劃 Agent、執行 Agent、評估 Agent 協同工作
- **狀態持久化**: Checkpoint 機制支援任務暫停/恢復
- **成本控制**: Token 使用量預估和預算控制
- **長程記憶**: 與 Memory Manager 整合，支援長期記憶存儲和檢索
- **失敗恢復**: 自動重試機制和失敗處理策略

## 目錄結構

```
agents/autogen/
├── __init__.py              # 模組初始化
├── config.py                 # 配置載入
├── llm_adapter.py           # LLM 適配器
├── agent_roles.py           # Agent 角色定義
├── conversation.py          # 會話管理
├── tool_adapter.py          # 工具適配器
├── coordinator.py           # Agent 協調器
├── planner.py               # 執行計劃生成器
├── cost_estimator.py        # 成本估算器
├── state_mapper.py          # 狀態映射器（混合模式）
├── long_horizon.py          # 長時程任務管理
├── factory.py               # Workflow Factory
├── workflow.py              # Workflow Runner
├── tests/                   # 單元測試
└── README.md                # 本文檔
```

## 配置

在 `config/config.json` 中配置 AutoGen 工作流：

```json
{
  "workflows": {
    "autogen": {
      "enable_planning": true,
      "max_steps": 20,
      "planning_mode": "auto",
      "auto_retry": true,
      "max_rounds": 10,
      "budget_tokens": 100000,
      "default_llm": "gpt-oss:20b",
      "enable_tools": true,
      "enable_memory": true,
      "checkpoint_enabled": true,
      "checkpoint_dir": "./datasets/autogen/checkpoints"
    }
  }
}
```

### 配置項說明

| 配置項 | 類型 | 默認值 | 說明 |
|--------|------|--------|------|
| `enable_planning` | boolean | true | 是否啟用 Execution Planning |
| `max_steps` | integer | 20 | 最大執行步驟數 |
| `planning_mode` | string | "auto" | 規劃模式: auto/manual/hybrid |
| `auto_retry` | boolean | true | 是否啟用自動重試 |
| `max_rounds` | integer | 10 | 最大迭代輪數 |
| `budget_tokens` | integer | 100000 | Token 預算上限 |
| `default_llm` | string | "gpt-oss:20b" | 預設 LLM 模型 ID |
| `enable_tools` | boolean | true | 是否啟用工具/函式呼叫 |
| `enable_memory` | boolean | true | 是否啟用 Working Memory |
| `checkpoint_enabled` | boolean | true | 是否啟用狀態持久化 |
| `checkpoint_dir` | string | "./datasets/autogen/checkpoints" | Checkpoint 保存目錄 |

## 使用示例

### 基本使用

```python
from agents.workflows.base import WorkflowRequestContext
from agents.autogen.factory import AutoGenWorkflowFactory

# 創建 Factory
factory = AutoGenWorkflowFactory()

# 構建 Workflow
ctx = WorkflowRequestContext(
    task_id="task-001",
    task="制定一個包含多個步驟的詳細執行計劃",
)
workflow = factory.build_workflow(ctx)

# 執行 Workflow
result = await workflow.run()
print(f"狀態: {result.status}")
print(f"輸出: {result.output}")
```

### 通過 Workflow Factory Router 使用

```python
from agents.workflows.factory_router import get_workflow_factory_router
from agents.task_analyzer.models import WorkflowType
from agents.workflows.base import WorkflowRequestContext

router = get_workflow_factory_router()
factory = router.get_factory(WorkflowType.AUTOGEN)

ctx = WorkflowRequestContext(
    task_id="task-002",
    task="複雜任務",
)
workflow = factory.build_workflow(ctx)
result = await workflow.run()
```

### 手動創建執行計劃

```python
from agents.autogen.planner import ExecutionPlanner
from agents.autogen.llm_adapter import AutoGenLLMAdapter

planner = ExecutionPlanner()
llm_adapter = AutoGenLLMAdapter(model_name="gpt-oss:20b")

plan = await planner.generate_plan(
    task="任務描述",
    llm_adapter=llm_adapter,
    max_steps=10,
)

print(f"計劃 ID: {plan.plan_id}")
print(f"步驟數: {len(plan.steps)}")
print(f"可行性分數: {plan.feasibility_score}")
```

### 成本估算

```python
from agents.autogen.cost_estimator import CostEstimator

estimator = CostEstimator()
cost_estimate = estimator.estimate_plan_cost(plan, model_name="gpt-oss:20b")

print(f"總 Token 數: {cost_estimate.total_tokens}")
print(f"估算成本: ${cost_estimate.estimated_cost:.4f}")

# 檢查預算
within_budget, msg = estimator.check_budget(cost_estimate, budget_tokens=100000)
print(msg)
```

### 狀態持久化和恢復

```python
from agents.autogen.long_horizon import LongHorizonTaskManager

manager = LongHorizonTaskManager(
    checkpoint_dir="./datasets/autogen/checkpoints"
)

# 保存檢查點
manager.save_checkpoint(plan)

# 恢復計劃
restored_plan = manager.restore_plan_from_checkpoint(plan.plan_id)
```

## API 文檔

### ExecutionPlanner

執行計劃生成器，負責生成、驗證和修訂執行計劃。

#### 方法

- `generate_plan(task, llm_adapter, max_steps, context) -> ExecutionPlan`: 生成執行計劃
- `revise_plan(plan, feedback, llm_adapter) -> ExecutionPlan`: 基於反饋修訂計劃
- `_validate_plan(plan) -> float`: 驗證計劃可行性（返回 0.0-1.0 分數）

### CostEstimator

成本估算器，提供 Token 使用量預估和成本計算。

#### 方法

- `estimate_plan_cost(plan, model_name) -> CostEstimate`: 估算計劃成本
- `check_budget(estimate, budget_tokens) -> tuple[bool, str]`: 檢查預算限制

### LongHorizonTaskManager

長時程任務管理器，提供狀態持久化、失敗恢復和資源控制。

#### 方法

- `save_checkpoint(plan, additional_state) -> bool`: 保存檢查點
- `load_checkpoint(plan_id) -> Optional[Dict]`: 載入檢查點
- `restore_plan_from_checkpoint(plan_id) -> Optional[ExecutionPlan]`: 恢復計劃
- `handle_failure(plan, failed_step_id, error, max_retries) -> bool`: 處理失敗步驟
- `check_resource_limits(plan, budget_tokens, max_rounds) -> tuple[bool, str]`: 檢查資源限制

## 整合點

### 與 Task Analyzer 整合

Task Analyzer 會根據任務複雜度和步數需求自動選擇 AutoGen：

- 複雜度 60-80 且 Steps > 5 時優先選擇 AutoGen
- 規劃類任務（TaskType.PLANNING）優先使用 AutoGen

### 與 Context Recorder 整合

Execution Planning 結果會自動寫入 Context Recorder，支援計劃查詢和回放。

### 與 Telemetry 整合

成本/tokens 使用情況會記錄到 Telemetry 系統，支援 Prometheus 指標輸出。

### 與 LangGraph 狀態同步

通過 `StateMapper` 實現 AutoGen 計劃與 LangGraph 狀態的轉換，為 WBS 3.4 混合模式做準備。

## 測試

### 運行單元測試

```bash
pytest agents/autogen/tests/
```

### 運行集成測試

```bash
pytest tests/autogen/
```

### 運行 Smoke Test

```bash
python scripts/test_autogen_smoke.py
```

### 運行安裝驗證

```bash
python scripts/test_autogen_install.py
```

## 注意事項

1. **版本鎖定**: pyautogen 版本鎖定為 `>=0.2.0,<0.3.0` 以確保 API 相容性
2. **資源控制**: 長時程任務需要配置適當的 `budget_tokens` 和 `max_rounds` 限制
3. **Checkpoint 目錄**: 確保 `checkpoint_dir` 目錄有寫入權限
4. **LLM 配置**: 確保 LLM Router 正確配置，AutoGen 依賴 LLM 適配器

## 相關文檔

- [WBS 3.3 子計劃](../../docs/plans/phase3/wbs-3.3-autogen.md)
- [Workflow 基礎協議](../workflows/base.py)
- [CrewAI 整合](../crewai/README.md)
- [LangGraph 整合](../workflows/langchain_graph/README.md)
