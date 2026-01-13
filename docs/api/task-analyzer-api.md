# Task Analyzer API 文檔

**創建日期**: 2026-01-12
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-13
**版本**: v4.0

---

## 概述

Task Analyzer API 提供任務分析和語義理解功能，支持從自然語言請求到結構化任務分析的完整流程。

**v4.0 架構變更**（2026-01-13）：

- ✅ **5層處理流程**：從 v3 的 4 層路由架構升級為 v4.0 的 5 層處理流程（L1-L5）
- ✅ **L1 語義理解層**：純語義理解輸出（`SemanticUnderstandingOutput`），不產生 intent，不指定 agent
- ✅ **L2 意圖抽象層**：基於 Intent DSL 的固定意圖集合，版本化管理
- ✅ **L3 能力映射層**：基於 Capability Registry 的能力發現和 Task DAG 規劃
- ✅ **L4 策略檢查層**：執行前的權限、風險、策略和資源限制檢查
- ✅ **L5 執行觀察層**：任務執行和結果觀察，支持回放和重試
- ✅ **測試驗證完成**：階段七測試驗證已完成，共 12 個測試用例（端到端 5 個、性能 3 個、回歸 2 個、壓力 2 個）

## API 端點

### 分析任務

分析用戶的自然語言請求，返回結構化的任務分析結果。

**請求格式**:

```json
{
  "task": "查詢系統配置",
  "context": {
    "user_id": "user_123",
    "tenant_id": "tenant_123"
  },
  "user_id": "user_123",
  "session_id": "session_123",
  "specified_agent_id": "agent_123"
}
```

**請求參數**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `task` | string | 是 | 任務描述（自然語言） |
| `context` | object | 否 | 上下文信息 |
| `user_id` | string | 否 | 用戶 ID |
| `session_id` | string | 否 | 會話 ID |
| `specified_agent_id` | string | 否 | 前端指定的 Agent ID |

**響應格式**:

```json
{
  "task_id": "task_123",
  "task_type": "query",
  "workflow_type": "langchain",
  "llm_provider": "chatgpt",
  "confidence": 0.95,
  "requires_agent": true,
  "suggested_agents": ["system_config_agent"],
  "suggested_tools": [],
  "analysis_details": {
    "semantic_understanding": {
      "topics": ["系統配置", "GenAI"],
      "entities": ["tenant_policy"],
      "action_signals": ["query", "read"],
      "modality": "text",
      "certainty": 0.95
    },
    "matched_intent": {
      "name": "config_query",
      "domain": "system",
      "target": "system_config_agent",
      "output_format": "structured",
      "depth": "Basic",
      "version": "1.0.0"
    },
    "task_dag": {
      "task_graph": [
        {
          "id": "T1",
          "capability": "query",
          "agent": "system_config_agent",
          "depends_on": []
        }
      ],
      "reasoning": "查詢系統配置"
    },
    "policy_validation": {
      "allowed": true,
      "requires_confirmation": false,
      "risk_level": "low",
      "reasons": []
    },
    "execution_record": {
      "intent": "config_query",
      "task_count": 1,
      "execution_success": true,
      "latency_ms": 150
    }
  },
  "router_decision": {
    "topics": ["系統配置", "GenAI"],
    "entities": ["tenant_policy"],
    "action_signals": ["query", "read"],
    "modality": "text",
    "intent_type": "query",
    "needs_tools": false,
    "needs_agent": false
  },
  "decision_result": {
    "task_dag": {
      "task_graph": [
        {
          "id": "T1",
          "capability": "query",
          "agent": "system_config_agent",
          "depends_on": []
        }
      ],
      "reasoning": "查詢系統配置"
    }
  }
}
```

**響應字段說明**:

| 字段 | 類型 | 說明 |
|------|------|------|
| `task_id` | string | 任務 ID |
| `task_type` | string | 任務類型（query/execution/review/planning/complex/log_query） |
| `workflow_type` | string | 工作流類型（langchain/crewai/autogen/hybrid） |
| `llm_provider` | string | LLM 提供商 |
| `confidence` | float | 置信度（0-1） |
| `requires_agent` | boolean | 是否需要啟動 Agent |
| `suggested_agents` | array | 建議使用的 Agent 列表 |
| `suggested_tools` | array | 建議使用的工具列表 |
| `analysis_details` | object | 分析詳情（v4.0 新增字段） |
| `analysis_details.semantic_understanding` | object | L1 語義理解輸出（v4.0 新增） |
| `analysis_details.matched_intent` | object | L2 匹配的 Intent（v4.0 新增） |
| `analysis_details.task_dag` | object | L3 生成的 Task DAG（v4.0 新增） |
| `analysis_details.policy_validation` | object | L4 策略驗證結果（v4.0 新增） |
| `analysis_details.execution_record` | object | L5 執行記錄（v4.0 新增） |
| `router_decision` | object | Router 決策（L1 層輸出，v3 兼容字段） |
| `decision_result` | object | 決策引擎結果（包含 Task DAG） |

## 任務類型

- `query`: 查詢類任務
- `execution`: 執行類任務
- `review`: 審查類任務
- `planning`: 規劃類任務
- `complex`: 複雜任務
- `log_query`: 日誌查詢類任務

## 工作流類型

- `langchain`: LangChain/Graph 工作流
- `crewai`: CrewAI 工作流
- `autogen`: AutoGen 工作流
- `hybrid`: 混合模式

## 錯誤處理

### 錯誤響應格式

```json
{
  "error": "錯誤信息",
  "error_code": "ERROR_CODE",
  "details": {}
}
```

### 常見錯誤碼

- `INVALID_REQUEST`: 無效的請求
- `LLM_ERROR`: LLM 調用錯誤
- `DATABASE_ERROR`: 數據庫錯誤
- `RAG_ERROR`: RAG 檢索錯誤
- `POLICY_ERROR`: Policy 檢查錯誤

## 使用示例

### Python 示例

```python
from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import TaskAnalysisRequest

analyzer = TaskAnalyzer()

request = TaskAnalysisRequest(
    task="查詢系統配置",
    context={"user_id": "user_123"},
    user_id="user_123"
)

result = await analyzer.analyze(request)

print(f"任務類型: {result.task_type}")
print(f"建議 Agent: {result.suggested_agents}")
```

### cURL 示例

```bash
curl -X POST http://localhost:8000/api/task/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "task": "查詢系統配置",
    "context": {
      "user_id": "user_123"
    },
    "user_id": "user_123"
  }'
```

## 性能指標

- **端到端響應時間**: ≤3秒（P95）
- **L1 層級響應時間**: ≤1秒（P95）
- **RAG 檢索時間**: ≤200ms（P95）
- **Policy 檢查時間**: ≤100ms（P95）

## 版本信息

- **當前版本**: v4.0
- **API 版本**: 1.0
- **最後更新**: 2026-01-13

## v4.0 架構變更詳情

### L1: Semantic Understanding Layer（語義理解層）

**輸出格式**：

```json
{
  "semantic_understanding": {
    "topics": ["document", "system_design"],
    "entities": ["Document Editing Agent", "API Spec"],
    "action_signals": ["design", "refine"],
    "modality": "instruction",
    "certainty": 0.92
  }
}
```

**特點**：

- 純語義理解，不產生 intent
- 不指定 agent
- 不使用 RAG

### L2: Intent & Task Abstraction Layer（意圖與任務抽象層）

**輸出格式**：

```json
{
  "matched_intent": {
    "name": "document_editing",
    "domain": "document",
    "target": "document_editing_agent",
    "output_format": "structured",
    "depth": "Advanced",
    "version": "1.0.0"
  }
}
```

**特點**：

- 基於 Intent DSL 的固定意圖集合
- 版本化管理
- 支持 Fallback Intent

### L3: Capability Mapping & Task Planning Layer（能力映射與任務規劃層）

**輸出格式**：

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
  }
}
```

**特點**：

- 基於 Capability Registry 的能力發現
- 支持多步驟任務規劃
- 支持任務依賴關係

### L4: Constraint Validation & Policy Check Layer（約束驗證與策略檢查層）

**輸出格式**：

```json
{
  "policy_validation": {
    "allowed": true,
    "requires_confirmation": false,
    "risk_level": "low",
    "reasons": []
  }
}
```

**特點**：

- 執行前的權限檢查
- 風險評估
- 策略驗證
- 資源限制檢查

### L5: Execution + Observation Layer（執行與觀察層）

**輸出格式**：

```json
{
  "execution_record": {
    "intent": "document_editing",
    "task_count": 1,
    "execution_success": true,
    "user_correction": false,
    "latency_ms": 150,
    "task_results": [],
    "trace_id": "trace_123",
    "user_id": "user_123",
    "session_id": "session_123",
    "agent_ids": ["document_editing_agent"]
  }
}
```

**特點**：

- 任務執行記錄
- 性能指標追蹤
- 支持回放和重試
- 用戶糾正追蹤

## 測試驗證

**階段七測試驗證已完成**（2026-01-13）：

- ✅ **端到端測試**：5 個測試用例，測試 L1-L5 完整流程
- ✅ **性能測試**：3 個測試用例，測試各層級性能指標
- ✅ **回歸測試**：2 個測試用例，確保 v3 功能兼容性
- ✅ **壓力測試**：2 個測試用例，測試高並發場景

**測試文件位置**：

- `tests/integration/e2e/test_task_analyzer_v4_e2e.py`
- `tests/performance/test_task_analyzer_v4_performance.py`
- `tests/regression/test_task_analyzer_v3_compatibility.py`
- `tests/performance/test_task_analyzer_v4_stress.py`
