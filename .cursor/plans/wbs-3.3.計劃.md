<!-- f6de6155-e32e-4e2b-83e3-9f1f16f41ce4 7624beb8-cc4a-4be7-b121-d0ff63014cb4 -->
# WBS 3.3 AutoGen 整合詳細實施計劃

## 1. 任務概述

根據 [WBS 3.3 子計劃](docs/plans/phase3/wbs-3.3-autogen.md) 和 [架構規劃](AI-Box-架構規劃.md)，實現 AutoGen 整合以支援複雜度 60-80 的長時程規劃任務。總工期：6 個工作日。

## 2. 任務拆解與實施步驟

### T3.3.1: AutoGen 基礎設置 (0.5 天)

**目標**: 安裝 AutoGen、建立配置模板、與 LLM Router 對接

**實施步驟**:

1. **依賴安裝**

   - 在 `requirements.txt` 中添加 `pyautogen>=0.2.0`（鎖定版本以確保 API 相容性）
   - 建立 `scripts/test_autogen_install.py` 驗證腳本

2. **配置模板建立**

   - 在 `config/config.example.json` 的 `workflows` 區塊中添加 `autogen` 配置：
     ```json
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
     ```


3. **LLM Router 適配**

   - 建立 `agents/autogen/llm_adapter.py`，封裝 LLM Router 調用以適配 AutoGen 的 LLM 接口
   - 參考 `agents/crewai/llm_adapter.py` 的實現模式

4. **目錄結構建立**

   - 建立 `agents/autogen/` 目錄
   - 建立 `agents/autogen/__init__.py`
   - 建立 `agents/autogen/config.py`（載入配置，參考 `agents/crewai/settings.py`）
   - 建立 `datasets/autogen/checkpoints/` 目錄用於狀態持久化

**交付物**:

- `requirements.txt` 更新
- `config/config.example.json` 更新
- `agents/autogen/config.py`
- `agents/autogen/llm_adapter.py`
- `scripts/test_autogen_install.py`

### T3.3.2: AutoGen Agent 實現 (2 天)

**目標**: 建立多 Agent 角色、會話管理、工具接口

**實施步驟**:

1. **Agent 角色定義**

   - 建立 `agents/autogen/agent_roles.py`，定義：
     - `PlanningAgent`: 負責生成執行計劃
     - `ExecutionAgent`: 負責執行具體步驟
     - `EvaluationAgent`: 負責評估執行結果
   - 每個 Agent 包含角色描述、系統提示詞、能力定義

2. **會話管理**

   - 建立 `agents/autogen/conversation.py`，實現：
     - 多 Agent 會話管理
     - 會話歷史記錄
     - 與 Context Recorder 整合（參考 `agent_process/context/recorder.py`）

3. **工具接口適配**

   - 建立 `agents/autogen/tool_adapter.py`，將 Tool Registry 的工具適配為 AutoGen 可用的函數
   - 參考 `agents/crewai/tool_adapter.py` 的實現模式
   - 支援 MCP 工具調用

4. **Agent 協作機制**

   - 建立 `agents/autogen/coordinator.py`，實現：
     - Agent 之間的通信協議
     - 任務分配邏輯
     - 協作流程編排

**交付物**:

- `agents/autogen/agent_roles.py`
- `agents/autogen/conversation.py`
- `agents/autogen/tool_adapter.py`
- `agents/autogen/coordinator.py`
- 單元測試：`agents/autogen/tests/test_agent_roles.py`
- 示例腳本：`scripts/autogen_multi_agent_demo.py`

### T3.3.3: Execution Planning (2 天)

**目標**: 實現規劃/重規劃、計畫驗證與成本估算

**實施步驟**:

1. **計畫生成器**

   - 建立 `agents/autogen/planner.py`，實現：
     - 多步驟計畫生成（基於 AutoGen 的 PlanningAgent）
     - 計畫結構化輸出（JSON 格式）
     - 計畫驗證邏輯（可行性檢查、資源需求評估）

2. **重規劃機制**

   - 在 `planner.py` 中實現：
     - 基於執行反饋的計畫修正
     - 失敗步驟的重試策略
     - 動態調整計畫步驟

3. **成本估算**

   - 建立 `agents/autogen/cost_estimator.py`，實現：
     - Token 使用量預估
     - 成本計算（基於 LLM 定價）
     - 預算控制機制

4. **計畫記錄與同步**

   - 將 Execution Planning 結果寫入 Context Recorder（參考 `agent_process/context/recorder.py`）
   - 建立計畫摘要格式，支援後續查詢和回放
   - 將 cost/tokens 記錄至 Telemetry（參考 `agents/workflows/langchain_graph/telemetry.py`）

5. **狀態同步準備**

   - 建立 `agents/autogen/state_mapper.py`，實現：
     - 將 AutoGen 計畫節點轉換為 LangGraph 狀態格式（為 WBS 3.4 混合模式做準備）
     - 輸出 partial plan 供 CrewAI 參照

**交付物**:

- `agents/autogen/planner.py`
- `agents/autogen/cost_estimator.py`
- `agents/autogen/state_mapper.py`
- 計畫生成 API 與驗證腳本
- 成本預估報告範本
- 單元測試：`agents/autogen/tests/test_planner.py`

### T3.3.4: Long-horizon 任務處理 (1.5 天)

**目標**: 實現狀態管理、持久化、長程記憶及失敗恢復

**實施步驟**:

1. **狀態持久化**

   - 建立 `agents/autogen/long_horizon.py`，實現：
     - Checkpoint 機制（保存執行狀態到 `datasets/autogen/checkpoints/`）
     - 狀態恢復功能
     - 狀態版本管理

2. **長程記憶整合**

   - 整合 Memory Manager（參考 `agent_process/memory/manager.py`）：
     - 長期記憶存儲（重要決策點、執行結果）
     - 記憶檢索（用於後續任務參考）

3. **失敗恢復機制**

   - 實現：
     - 自動重試邏輯（基於配置的 `auto_retry` 和 `max_rounds`）
     - 失敗點識別與恢復
     - 部分完成任務的狀態保存

4. **資源控制**

   - 實現：
     - Token 預算控制（基於 `budget_tokens` 配置）
     - 最大迭代數限制（基於 `max_rounds`）
     - 空閒監控與自動暫停機制

5. **Workflow 整合**

   - 建立 `agents/autogen/factory.py`，實現 `WorkflowFactoryProtocol`（參考 `agents/crewai/factory.py`）
   - 建立 `agents/autogen/workflow.py`，實現 `WorkflowRunner` 協議（參考 `agents/workflows/base.py`）
   - 更新 `agents/workflows/factory_router.py`，註冊 AutoGen Workflow Factory

**交付物**:

- `agents/autogen/long_horizon.py`
- `agents/autogen/factory.py`
- `agents/autogen/workflow.py`
- 狀態 dump/replay 文檔
- 長程任務示例腳本
- 單元測試：`agents/autogen/tests/test_long_horizon.py`

## 3. 整合點與依賴

### 3.1 與現有系統整合

1. **Workflow Factory 架構**

   - 遵循 `WorkflowFactoryProtocol` 和 `WorkflowRunner` 協議（定義於 `agents/workflows/base.py`）
   - 在 `agents/workflows/factory_router.py` 中註冊 AutoGen Factory

2. **Context Recorder**

   - Execution Planning 結果寫入 Context Recorder（使用 `agent_process/context/recorder.py`）
   - 支援計畫查詢和回放

3. **Telemetry 系統**

   - 成本/tokens 記錄至 Telemetry（參考 `agents/workflows/langchain_graph/telemetry.py`）
   - 支援 Prometheus 指標輸出

4. **Task Analyzer**

   - 更新 `agents/task_analyzer/workflow_selector.py`，確保複雜度 60-80 且 Steps > 5 時選擇 AutoGen
   - 配置已存在於 `workflow_selector.py`（`WorkflowType.AUTOGEN`）

5. **LLM Router**

   - 透過 `llm/router.py` 獲取 LLM 實例
   - 適配 AutoGen 的 LLM 接口

### 3.2 配置更新

- `config/config.example.json`: 添加 `workflows.autogen` 配置塊
- `requirements.txt`: 添加 `pyautogen>=0.2.0`

## 4. 測試策略

1. **單元測試**

   - 每個模組建立對應的測試文件（`agents/autogen/tests/`）
   - 測試覆蓋率目標：≥80%

2. **集成測試**

   - 建立 `tests/autogen/test_workflow_integration.py`
   - 測試與 Task Analyzer 的整合
   - 測試與 Context Recorder 的整合

3. **Smoke Test**

   - 建立 `scripts/test_autogen_smoke.py`，驗證基礎功能
   - 驗證版本相容性（鎖定 pyautogen 版本）

4. **樣板任務測試**

   - 建立複雜度 60-80 的樣板任務測試
   - 驗證 Execution Planning 和 Long-horizon 處理

## 5. 文檔要求

1. **API 文檔**

   - 各模組的 docstring
   - 使用示例

2. **配置文檔**

   - `config/config.example.json` 中的配置項說明
   - 環境變數說明（如有）

3. **整合文檔**

   - 與 LangGraph 狀態同步的說明（為 WBS 3.4 準備）
   - 與 CrewAI 的協作方式

## 6. 風險緩解

1. **AutoGen 版本變動**

   - 鎖定 `pyautogen>=0.2.0,<0.3.0` 版本
   - 建立 smoke test，若失敗切回上一版本

2. **長程任務資源佔用**

   - 配置最大迭代數、空閒監控與自動暫停機制
   - 實現 Token 預算控制

3. **狀態同步問題**

   - 在 Execution Planning 階段輸出狀態草稿
   - 撰寫契約測試確保狀態一致性

## 7. 驗收標準

- [ ] 複雜度 60-80 的樣板任務可由 AutoGen 自動規劃並成功執行
- [ ] Execution Planning 可輸出可讀計畫摘要、成本預估、以及可重播的狀態檔
- [ ] Long-horizon 任務可暫停/恢復並保持一致性，且失敗後可透過重試成功
- [ ] 與 Task Analyzer 整合，可根據複雜度和步數需求選擇 AutoGen
- [ ] 所有單元測試通過，覆蓋率 ≥80%
- [ ] Smoke test 通過

## 8. 文件清單

**新增文件**:

- `agents/autogen/__init__.py`
- `agents/autogen/config.py`
- `agents/autogen/llm_adapter.py`
- `agents/autogen/agent_roles.py`
- `agents/autogen/conversation.py`
- `agents/autogen/tool_adapter.py`
- `agents/autogen/coordinator.py`
- `agents/autogen/planner.py`
- `agents/autogen/cost_estimator.py`
- `agents/autogen/state_mapper.py`
- `agents/autogen/long_horizon.py`
- `agents/autogen/factory.py`
- `agents/autogen/workflow.py`
- `agents/autogen/tests/__init__.py`
- `agents/autogen/tests/test_agent_roles.py`
- `agents/autogen/tests/test_planner.py`
- `agents/autogen/tests/test_long_horizon.py`
- `scripts/test_autogen_install.py`
- `scripts/test_autogen_smoke.py`
- `scripts/autogen_multi_agent_demo.py`

**修改文件**:

- `requirements.txt` (添加 pyautogen)
- `config/config.example.json` (添加 workflows.autogen 配置)
- `agents/workflows/factory_router.py` (註冊 AutoGen Factory)
- `agents/task_analyzer/workflow_selector.py` (確保 AutoGen 選擇邏輯正確)

### To-dos

- [ ] T3.3.1: AutoGen 基礎設置 - 安裝依賴、建立配置模板、LLM Router 適配、目錄結構建立
- [ ] T3.3.2: AutoGen Agent 實現 - Agent 角色定義、會話管理、工具接口適配、Agent 協作機制
- [ ] T3.3.3: Execution Planning - 計畫生成器、重規劃機制、成本估算、計畫記錄與同步、狀態同步準備
- [ ] T3.3.4: Long-horizon 任務處理 - 狀態持久化、長程記憶整合、失敗恢復機制、資源控制、Workflow 整合
- [ ] 建立集成測試 - 與 Task Analyzer、Context Recorder、Telemetry 的整合測試
- [ ] 建立 Smoke Test - 驗證基礎功能和版本相容性
- [ ] 更新 Workflow Factory Router - 註冊 AutoGen Factory
- [ ] 撰寫文檔 - API 文檔、配置文檔、整合文檔
