# Orchestrator API 文檔

**創建日期**: 2026-01-12
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-13
**版本**: v4.0

---

## 概述

Orchestrator API 提供 Agent 協調、任務分發和執行管理功能。

**v4.0 架構變更**（2026-01-13）：

- ✅ **與 Task Analyzer 集成**：Orchestrator 與 v4.0 Task Analyzer 的 5 層處理流程（L1-L5）完全集成
- ✅ **Task DAG 執行**：支持執行 Task Analyzer L3 層生成的 Task DAG
- ✅ **策略檢查集成**：與 Task Analyzer L4 層的策略檢查結果集成
- ✅ **執行記錄追蹤**：支持 Task Analyzer L5 層的執行記錄和觀察功能

## API 端點

### 處理自然語言請求

處理自然語言請求，自動分析任務並執行。

**請求格式**:

```json
{
  "task": "查詢系統配置",
  "user_id": "user_123",
  "context": {
    "tenant_id": "tenant_123"
  }
}
```

**響應格式**:

```json
{
  "task_id": "task_123",
  "status": "completed",
  "result": {
    "config": {}
  }
}
```

### 提交任務

提交結構化任務。

**請求格式**:

```json
{
  "task_type": "query",
  "task_data": {
    "action": "query",
    "scope": "genai.policy"
  },
  "required_agents": ["system_config_agent"],
  "priority": 0,
  "timeout": 30
}
```

**響應格式**:

```json
{
  "task_id": "task_123"
}
```

### 查詢任務狀態

查詢任務執行狀態。

**請求格式**:

```
GET /api/orchestrator/tasks/{task_id}
```

**響應格式**:

```json
{
  "task_id": "task_123",
  "status": "running",
  "result": null,
  "error": null,
  "agent_id": "system_config_agent",
  "started_at": "2026-01-12T10:00:00Z",
  "completed_at": null
}
```

### 發現 Agent

發現可用的 Agent。

**請求格式**:

```
GET /api/orchestrator/agents?required_capabilities=query&agent_type=system
```

**響應格式**:

```json
{
  "agents": [
    {
      "agent_id": "system_config_agent",
      "agent_type": "system",
      "capabilities": ["query", "update"],
      "status": "online"
    }
  ]
}
```

## 任務狀態

- `pending`: 待處理
- `assigned`: 已分配
- `running`: 運行中
- `completed`: 已完成
- `failed`: 失敗
- `cancelled`: 已取消

## 使用示例

### Python 示例

```python
from agents.services.orchestrator.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()

# 處理自然語言請求
result = await orchestrator.process_natural_language_request(
    task="查詢系統配置",
    user_id="user_123",
    context={"tenant_id": "tenant_123"}
)

# 提交任務
task_id = orchestrator.submit_task(
    task_type="query",
    task_data={"action": "query"},
    required_agents=["system_config_agent"]
)

# 查詢任務狀態
status = orchestrator.get_task_status(task_id)
```

## 版本信息

- **當前版本**: v4.0
- **API 版本**: 1.0
- **最後更新**: 2026-01-13

## v4.0 架構變更詳情

### Task DAG 執行支持

Orchestrator 現在支持執行 Task Analyzer L3 層生成的 Task DAG：

**請求格式**：

```json
{
  "task_dag": {
    "task_graph": [
      {
        "id": "T1",
        "capability": "edit_document",
        "agent": "document_editing_agent",
        "depends_on": []
      }
    ],
    "reasoning": "需要編輯 API 規格文檔"
  },
  "context": {
    "user_id": "user_123",
    "session_id": "session_123"
  }
}
```

**響應格式**：

```json
{
  "task_id": "task_123",
  "status": "completed",
  "execution_record": {
    "intent": "document_editing",
    "task_count": 1,
    "execution_success": true,
    "latency_ms": 150,
    "task_results": []
  }
}
```

### 策略檢查集成

Orchestrator 在執行任務前會檢查 Task Analyzer L4 層的策略驗證結果：

- 如果 `policy_validation.allowed = false`，任務將被拒絕
- 如果 `policy_validation.requires_confirmation = true`，任務需要用戶確認
- 如果 `policy_validation.risk_level = "high"`，任務需要額外的安全檢查

### 執行記錄追蹤

Orchestrator 支持 Task Analyzer L5 層的執行記錄功能：

- 記錄任務執行時間和性能指標
- 追蹤任務執行結果和錯誤信息
- 支持任務回放和重試
