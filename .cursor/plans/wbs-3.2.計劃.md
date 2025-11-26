<!-- 06ccb08c-6397-42b6-893f-4069045ae96e 642eb820-d101-43d9-b3bf-6b3c0111147d -->
# CrewAI 整合實施計劃

## 1. 概述

本計劃基於 WBS 3.2 子計劃，在 7.5 個工作日內完成 CrewAI 多角色協作引擎的完整整合，支持 50-70 分複雜度任務的多角色協作場景。

## 2. 任務拆解與實施順序

### T3.2.1: CrewAI 基礎設置 (0.5 天)

**目標**: 安裝 CrewAI 套件，建立配置結構，串接 LLM Router

**實施步驟**:

1. 在 `requirements.txt` 中添加 `crewai>=0.28.0` 依賴
2. 在 `config/config.example.json` 的 `workflows` 區塊添加 `crewai` 配置：

   - `enable_crew`: 開關
   - `max_agents`: 最大 Agent 數量（預設 5）
   - `collaboration_mode`: 預設流程模式（sequential/hierarchical/consensual）
   - `token_budget`: Token 預算上限
   - `default_llm`: 預設 LLM 模型
   - `enable_tools`: 是否啟用工具
   - `enable_memory`: 是否啟用記憶

3. 創建 `agents/crewai/__init__.py`
4. 創建 `agents/crewai/settings.py`，參考 `agents/workflows/settings.py` 的實現模式
5. 創建 `agents/crewai/llm_adapter.py`，封裝 LLM Router 調用，提供 CrewAI 所需的 LLM 接口

**交付物**:

- `requirements.txt` 更新
- `config/config.example.json` 更新
- `agents/crewai/settings.py`
- `agents/crewai/llm_adapter.py`

### T3.2.2: Crew Manager 實現 (2 天)

**目標**: 實現隊伍定義、角色權限、資源配額、觀測指標管理

**實施步驟**:

1. 創建 `agents/crewai/models.py`，定義數據模型：

   - `CrewConfig`: 隊伍配置
   - `AgentRole`: 角色定義（包含 role, goal, backstory, tools）
   - `CrewResourceQuota`: 資源配額（token_budget, max_iterations, timeout）
   - `CrewMetrics`: 觀測指標（agent_count, task_count, token_usage, execution_time）

2. 創建 `agents/crewai/manager.py`，實現 `CrewManager` 類：

   - `create_crew()`: 創建隊伍
   - `add_agent()`: 添加 Agent 到隊伍
   - `remove_agent()`: 移除 Agent
   - `get_crew()`: 獲取隊伍信息
   - `list_crews()`: 列出所有隊伍
   - `update_resource_quota()`: 更新資源配額
   - `get_metrics()`: 獲取觀測指標

3. 創建 `agents/crewai/crew_registry.py`，實現隊伍註冊表（類似 ToolRegistry 模式）
4. 創建 `services/api/routers/crewai.py`，提供 REST API：

   - `POST /api/v1/crews`: 創建隊伍
   - `GET /api/v1/crews`: 列出隊伍
   - `GET /api/v1/crews/{crew_id}`: 獲取隊伍詳情
   - `PUT /api/v1/crews/{crew_id}`: 更新隊伍
   - `DELETE /api/v1/crews/{crew_id}`: 刪除隊伍
   - `GET /api/v1/crews/{crew_id}/metrics`: 獲取觀測指標

**交付物**:

- `agents/crewai/models.py`
- `agents/crewai/manager.py`
- `agents/crewai/crew_registry.py`
- `services/api/routers/crewai.py`
- `tests/crewai/test_manager.py`（單元測試）

### T3.2.3: Process Engine 實現 (2 天)

**目標**: 實現 Sequential、Hierarchical、Consensual 三種流程模板與切換邏輯

**實施步驟**:

1. 創建 `agents/crewai/process_engine.py`，實現 `ProcessEngine` 類：

   - `create_sequential_process()`: 創建順序流程（Agent 按順序執行）
   - `create_hierarchical_process()`: 創建層級流程（Manager Agent 協調其他 Agent）
   - `create_consensual_process()`: 創建共識流程（多 Agent 協商達成共識）
   - `switch_process()`: 動態切換流程模式

2. 創建 `agents/crewai/process_templates.py`，定義流程模板配置：

   - 每種流程模式的預設參數
   - 流程切換條件邏輯

3. 創建 `agents/crewai/token_budget.py`，實現 Token 預算控制：

   - `TokenBudgetGuard`: 監控 Token 使用
   - `check_budget()`: 檢查是否超預算
   - `record_usage()`: 記錄 Token 使用量

4. 整合到 `agents/crewai/workflow.py`，實現 `WorkflowRunner` 協議：

   - 實現 `run()` 方法，執行 CrewAI 工作流
   - 整合 Context Recorder 記錄執行過程
   - 整合 Telemetry 發送觀測事件

**交付物**:

- `agents/crewai/process_engine.py`
- `agents/crewai/process_templates.py`
- `agents/crewai/token_budget.py`
- `agents/crewai/workflow.py`
- `tests/crewai/test_process_engine.py`（單元測試）

### T3.2.4: Agent 模板開發 (1.5 天)

**目標**: 開發標準 Agent 模板，覆蓋規劃/研究/執行/評審等角色，並與 Tool Registry 對接

**實施步驟**:

1. 創建 `agents/crewai/agent_templates.py`，定義標準 Agent 模板：

   - `PlanningAgentTemplate`: 規劃 Agent（任務分解、策略制定）
   - `ResearchAgentTemplate`: 研究 Agent（信息收集、資料分析）
   - `ExecutionAgentTemplate`: 執行 Agent（工具調用、任務執行）
   - `ReviewAgentTemplate`: 評審 Agent（結果驗證、質量檢查）
   - `WritingAgentTemplate`: 寫作 Agent（文檔生成、報告撰寫）

2. 創建 `agents/crewai/tool_adapter.py`，實現工具適配層：

   - 將 `ToolRegistry` 中的工具轉換為 CrewAI 可用的工具格式
   - 處理工具調用的異步/同步轉換
   - 處理工具錯誤和重試邏輯

3. 創建 `agents/crewai/agent_factory.py`，實現 Agent 工廠：

   - `create_agent_from_template()`: 從模板創建 Agent
   - `create_custom_agent()`: 創建自定義 Agent
   - `configure_agent_tools()`: 配置 Agent 工具

4. 創建 `datasets/crewai/agent_templates.yaml`，定義 Agent 模板配置（YAML 格式）

**交付物**:

- `agents/crewai/agent_templates.py`
- `agents/crewai/tool_adapter.py`
- `agents/crewai/agent_factory.py`
- `datasets/crewai/agent_templates.yaml`
- `tests/crewai/test_agent_templates.py`（單元測試）

### T3.2.5: Task 管理系統 (1.5 天)

**目標**: 實現任務定義、排程、狀態跟蹤與審批系統

**實施步驟**:

1. 創建 `agents/crewai/task_registry.py`，實現 `TaskRegistry` 類：

   - `register_task()`: 註冊任務
   - `get_task()`: 獲取任務信息
   - `update_task_status()`: 更新任務狀態
   - `list_tasks()`: 列出任務
   - `get_task_history()`: 獲取任務執行歷史

2. 創建 `agents/crewai/task_scheduler.py`，實現任務排程：

   - `schedule_task()`: 排程任務
   - `cancel_task()`: 取消任務
   - `get_task_queue()`: 獲取任務隊列
   - `prioritize_task()`: 調整任務優先級

3. 創建 `agents/crewai/task_models.py`，定義任務數據模型：

   - `CrewTask`: 任務定義（task_id, description, assigned_agent, status, priority）
   - `TaskStatus`: 任務狀態枚舉（pending, in_progress, completed, failed, cancelled）
   - `TaskResult`: 任務執行結果

4. 整合到 `agents/crewai/workflow.py`，實現任務狀態同步：

   - 任務開始時記錄到 Task Registry
   - 任務執行過程中更新狀態
   - 任務完成時回寫結果到 Context Recorder

5. 創建 `services/api/routers/crewai_tasks.py`，提供任務管理 API：

   - `POST /api/v1/crewai/tasks`: 創建任務
   - `GET /api/v1/crewai/tasks`: 列出任務
   - `GET /api/v1/crewai/tasks/{task_id}`: 獲取任務詳情
   - `PUT /api/v1/crewai/tasks/{task_id}/status`: 更新任務狀態
   - `GET /api/v1/crewai/tasks/{task_id}/history`: 獲取任務歷史

**交付物**:

- `agents/crewai/task_registry.py`
- `agents/crewai/task_scheduler.py`
- `agents/crewai/task_models.py`
- `services/api/routers/crewai_tasks.py`
- `tests/crewai/test_task_registry.py`（單元測試）

## 3. 整合點實現

### 3.1 與 Orchestrator 整合

在 `agents/orchestrator/orchestrator.py` 中添加 CrewAI 調用邏輯：

- 當 Task Analyzer 選擇 CrewAI 工作流時，Orchestrator 調用 CrewAI Workflow
- 通過 MCP 工具暴露 CrewAI 功能（參考 `agents/planning/mcp_server.py` 的實現模式）

### 3.2 與 Task Analyzer 整合

在 `agents/task_analyzer/workflow_selector.py` 中確保 CrewAI 選擇邏輯正確：

- 複雜度 50-70 分且需要多角色時選擇 CrewAI
- 傳遞正確的配置參數給 CrewAI Workflow

### 3.3 與 Tool Registry 整合

通過 `agents/crewai/tool_adapter.py` 實現：

- 自動發現 Tool Registry 中的工具
- 將工具轉換為 CrewAI 格式
- 處理工具調用的錯誤和重試

### 3.4 與 Context Recorder 整合

在 `agents/crewai/workflow.py` 中：

- 任務開始時記錄初始狀態
- 每個 Agent 執行時記錄中間結果
- 任務完成時記錄最終結果
- 使用 `agent_process/context/recorder.py` 的 API

### 3.5 與 LLM Router 整合

通過 `agents/crewai/llm_adapter.py` 實現：

- 封裝 `llm/router.py` 的調用
- 提供 CrewAI 所需的 LLM 接口（ChatOpenAI 兼容接口）
- 處理 LLM 調用的錯誤和重試

## 4. 文件結構

```
agents/
  crewai/
    __init__.py
    settings.py              # 配置載入（參考 workflows/settings.py）
    llm_adapter.py           # LLM Router 適配層
    models.py                # 數據模型
    manager.py               # Crew Manager
    crew_registry.py         # 隊伍註冊表
    process_engine.py        # Process Engine
    process_templates.py     # 流程模板
    token_budget.py          # Token 預算控制
    agent_templates.py       # Agent 模板
    tool_adapter.py          # Tool Registry 適配層
    agent_factory.py         # Agent 工廠
    task_registry.py         # Task Registry
    task_scheduler.py        # Task Scheduler
    task_models.py           # Task 數據模型
    workflow.py              # Workflow 實現（實現 WorkflowRunner）
    factory.py               # Workflow Factory（實現 WorkflowFactoryProtocol）

services/api/routers/
  crewai.py                  # Crew Manager API
  crewai_tasks.py            # Task 管理 API

datasets/crewai/
  agent_templates.yaml       # Agent 模板配置

tests/crewai/
  test_manager.py
  test_process_engine.py
  test_agent_templates.py
  test_task_registry.py
  test_workflow.py           # E2E 測試
```

## 5. 配置更新

在 `config/config.example.json` 中添加：

```json
{
  "workflows": {
    "crewai": {
      "enable_crew": true,
      "max_agents": 5,
      "collaboration_mode": "sequential",
      "token_budget": 100000,
      "default_llm": "gpt-oss:20b",
      "enable_tools": true,
      "enable_memory": true,
      "process_timeout": 3600,
      "max_iterations": 20
    }
  }
}
```

## 6. 測試要求

### 單元測試

- Crew Manager 的創建、更新、刪除功能
- Process Engine 的三種流程模式
- Agent 模板的創建和配置
- Task Registry 的任務管理功能
- Tool Adapter 的工具轉換功能

### 集成測試

- CrewAI 任務全流程執行（從 Task Analyzer 選擇到結果回寫）
- 三種流程模式的切換測試
- Token Budget 控制測試
- 與 Tool Registry 的整合測試
- 與 Context Recorder 的整合測試

### E2E 測試

- 完整的多角色協作任務（例如：研究競爭對手並制定策略）
- 任務狀態查詢 API 測試
- 觀測指標收集測試

## 7. 風險緩解

1. **CrewAI 與既有工具不兼容**: 建立工具適配層，如無法適配則回退至 LangChain Workflow
2. **Token 成本暴增**: 在 Process Engine 中加入 Token Budget 守門與分支停損
3. **流程狀態同步延遲**: 透過事件匯流排（Redis Stream）實作即時狀態推送（後續優化）

## 8. 驗收標準

- Task Analyzer 在判斷需多角色時可切換到 CrewAI，整個任務全程成功完成
- 三種流程模板可透過配置檔切換並通過集成測試
- 各 Agent 模板均能調用 Tool Registry 工具並回寫結果
- Task 管理系統可提供任務狀態查詢 API
- 所有單元測試和集成測試通過

### To-dos

- [ ] T3.2.1: CrewAI 基礎設置 - 安裝套件、建立配置結構、串接 LLM Router
- [ ] T3.2.2: Crew Manager 實現 - 隊伍定義、角色權限、資源配額、觀測指標管理
- [ ] T3.2.3: Process Engine 實現 - Sequential/Hierarchical/Consensual 三種流程模板與切換邏輯
- [ ] T3.2.4: Agent 模板開發 - 規劃/研究/執行/評審等標準角色模板，與 Tool Registry 對接
- [ ] T3.2.5: Task 管理系統 - 任務定義、排程、狀態跟蹤與審批
- [ ] 整合 Orchestrator - 在 Orchestrator 中添加 CrewAI 調用邏輯
- [ ] 整合 Task Analyzer - 確保 CrewAI 選擇邏輯正確
- [ ] 整合 Context Recorder - 在 Workflow 中實現狀態記錄
- [ ] 編寫單元測試、集成測試和 E2E 測試
