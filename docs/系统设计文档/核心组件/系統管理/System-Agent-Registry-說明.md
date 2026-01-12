# System Agent Registry 說明文檔

**創建日期**: 2026-01-09
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-09

## 概述

System Agent Registry（系統 Agent 註冊表）是一個獨立的 Agent 註冊表，專門用於存儲和管理系統內部的支援層 Agent（System Agents）。這些 Agent 是系統的核心組件，不會在前端註冊表中顯示，僅供系統內部調用。

## System Agents 定義

System Agents 是系統內部的支援層 Agent，包括但不限於：

1. **安全審計 Agent** (`security-manager-agent`)
   - 類型：`security_audit`
   - 功能：安全審計和管理服務，提供智能風險評估、權限檢查和驗證
   - 能力：`security_audit`, `risk_assessment`, `permission_check`

2. **Report Agent** (`report-agent`)
   - 類型：`report`
   - 功能：報告生成和管理服務（未來添加）
   - 能力：`report_generation`, `report_management`

3. **文件編輯 Agent** (`document-editing-agent`)
   - 類型：`document_editing`
   - 功能：文件編輯服務，支持 Markdown 文件的 AI 驅動編輯
   - 能力：`document_editing`, `file_editing`, `markdown_editing`, `streaming_editing`, `execution`, `action`

4. **其他陸續定義中...**

## 特點

### 1. 獨立存儲

System Agent Registry 存儲在 ArangoDB 中，使用獨立的 Collection：`system_agent_registry`。

### 2. 不會在前端顯示

System Agents 標記為 `is_system_agent=True`，在查詢 Agent 列表時會自動過濾，不會在前端註冊表中顯示。

### 3. 系統內部調用

System Agents 僅供系統內部調用，不會暴露給前端用戶選擇或配置。

## 數據結構

### SystemAgentRegistryModel

```python
{
    "_key": "document-editing-agent",  # Agent ID（作為主鍵）
    "agent_id": "document-editing-agent",
    "agent_type": "document_editing",
    "name": "Document Editing Agent",
    "description": "文件編輯服務，支持 Markdown 文件的 AI 驅動編輯",
    "capabilities": ["document_editing", "file_editing", "markdown_editing", "streaming_editing"],
    "version": "1.0.0",
    "status": "online",  # online, offline, maintenance
    "is_active": true,
    "is_system_agent": true,  # System Agent 標記
    "metadata": {
        "is_system_agent": true,
        "is_internal": true,
        "category": "system_support"
    },
    "created_at": "2026-01-09T10:00:00.000000",
    "updated_at": "2026-01-09T10:00:00.000000"
}
```

## 註冊流程

### 1. 註冊到 System Agent Registry（ArangoDB）

首先將 System Agent 註冊到 ArangoDB 中的 `system_agent_registry` Collection：

```python
from services.api.services.system_agent_registry_store_service import (
    get_system_agent_registry_store_service,
)

system_agent_store = get_system_agent_registry_store_service()
system_agent_store.register_system_agent(
    agent_id="document-editing-agent",
    agent_type="document_editing",
    name="Document Editing Agent",
    description="文件編輯服務，支持 Markdown 文件的 AI 驅動編輯",
    capabilities=["document_editing", "file_editing", "markdown_editing"],
    version="1.0.0",
    metadata={
        "is_system_agent": True,
        "is_internal": True,
        "category": "system_support",
    },
)
```

### 2. 註冊到 Agent Registry（內存）

然後將 System Agent 註冊到內存的 Agent Registry，此時會自動檢查 System Agent Registry 並標記為 `is_system_agent=True`：

```python
from agents.services.registry.registry import get_agent_registry
from agents.services.registry.models import AgentRegistrationRequest

registry = get_agent_registry()
request = AgentRegistrationRequest(
    agent_id="document-editing-agent",
    agent_type="document_editing",
    name="Document Editing Agent",
    endpoints=AgentEndpoints(
        http=None,
        mcp=None,
        protocol=AgentServiceProtocolType.HTTP,
        is_internal=True,
    ),
    capabilities=["document_editing", "file_editing"],
    metadata=AgentMetadata(...),
    permissions=AgentPermissionConfig(),
)

success = registry.register_agent(request, instance=document_editing_agent)
```

### 3. 自動標記為 System Agent

當註冊到 Agent Registry 時，系統會自動檢查 System Agent Registry（ArangoDB），如果該 Agent 存在於 System Agent Registry 中，則標記為 `is_system_agent=True`。

## 查詢和過濾

### 1. 前端查詢（自動過濾 System Agents）

前端查詢 Agent 列表時，默認會過濾 System Agents：

```python
# 前端 API：/agents/catalog
# 自動過濾 is_system_agent=True 的 Agent
agents = registry.list_agents(include_system_agents=False)  # 默認值
```

### 2. 系統內部查詢（包括 System Agents）

系統內部查詢時，可以選擇包括 System Agents：

```python
# 系統內部調用：包括 System Agents
agents = registry.list_agents(include_system_agents=True)
```

### 3. 直接查詢 System Agent Registry

可以直接從 System Agent Registry（ArangoDB）查詢：

```python
from services.api.services.system_agent_registry_store_service import (
    get_system_agent_registry_store_service,
)

system_agent_store = get_system_agent_registry_store_service()

# 查詢單個 System Agent
agent = system_agent_store.get_system_agent("document-editing-agent")

# 列出所有 System Agents
agents = system_agent_store.list_system_agents(
    agent_type="document_editing",
    is_active=True,
    status="online",
)
```

## 索引

System Agent Registry 創建了以下索引以提高查詢性能：

1. **agent_type 索引**：按 Agent 類型查詢
2. **is_system_agent 索引**：過濾 System Agent
3. **status 索引**：按狀態查詢
4. **is_active 索引**：按啟用狀態查詢
5. **複合索引：agent_type + is_active**：組合查詢
6. **複合索引：is_system_agent + is_active + status**：組合查詢

## 文件編輯 Agent 追蹤結果

### 實際使用的 Agent ID

經過追蹤，系統中實際使用的文件編輯 Agent ID 為：

- **Agent ID**: `document-editing-agent`（連字符格式）
- **Agent 類型**: `document_editing`
- **工具名稱**: `document_editing`（下劃線格式，用於前端工具選擇）

### 使用位置

1. **Agent 定義**：
   - 文件：`agents/builtin/document_editing/agent.py`
   - Agent ID：`self.agent_id = "document-editing-agent"`

2. **路由邏輯**：
   - 文件：`agents/task_analyzer/router_llm.py`
   - 引用：`document-editing-agent`（在 System Prompt 中）

3. **決策引擎**：
   - 文件：`agents/task_analyzer/decision_engine.py`
   - 匹配邏輯：`if agent.agent_id == "document-editing-agent"`

4. **前端工具**：
   - 文件：`ai-bot/src/components/AssistantMaintenanceModal.tsx`
   - 工具名稱：`document_editing`（下劃線格式）

## 註冊位置

System Agents 的註冊邏輯位於：

- **文件**: `agents/builtin/__init__.py`
- **函數**: `register_builtin_agents()`
- **調用位置**: `api/main.py`（系統啟動時）

## API 端點

### System Agent Registry Store Service

- **文件**: `services/api/services/system_agent_registry_store_service.py`
- **主要方法**:
  - `register_system_agent()`: 註冊 System Agent
  - `get_system_agent()`: 獲取 System Agent
  - `update_system_agent()`: 更新 System Agent
  - `list_system_agents()`: 列出 System Agents
  - `unregister_system_agent()`: 取消註冊 System Agent

### 前端 API（自動過濾 System Agents）

- **GET /agents/catalog**: 獲取 Agent 目錄（不包括 System Agents）
- **GET /agents/discover**: 發現可用 Agent（不包括 System Agents）

### 系統內部 API（可選包括 System Agents）

- **GET /orchestrator/agents**: 列出 Agent（可選包括 System Agents）

## 相關文件

- **System Agent Registry Store Service**: `services/api/services/system_agent_registry_store_service.py`
- **Agent Registry 註冊邏輯**: `agents/builtin/__init__.py`
- **Agent Registry 模型**: `agents/services/registry/models.py`
- **Agent Discovery**: `agents/services/registry/discovery.py`
- **Agent Catalog API**: `api/routers/agent_catalog.py`

## 未來擴展

### 1. Report Agent

當 Report Agent 實現後，可以在 `agents/builtin/__init__.py` 的 `register_builtin_agents()` 函數中添加註冊邏輯：

```python
# Report Agent（未來添加）
report_agent = _builtin_agents.get("report_agent")
if report_agent:
    report_agent_id = "report-agent"
    # 先註冊到 System Agent Registry（ArangoDB）
    system_agent_store.register_system_agent(
        agent_id=report_agent_id,
        agent_type="report",
        name="Report Agent",
        description="報告生成和管理服務",
        capabilities=["report_generation", "report_management"],
        version="1.0.0",
        metadata={
            "is_system_agent": True,
            "is_internal": True,
            "category": "system_support",
        },
    )
    # 然後註冊到 Agent Registry（內存）
    # ...
```

### 2. 其他 System Agents

其他 System Agents 可以按照相同的模式註冊：

1. 先註冊到 System Agent Registry（ArangoDB）
2. 然後註冊到 Agent Registry（內存）
3. 系統會自動標記為 `is_system_agent=True`

## 注意事項

1. **註冊順序**：必須先註冊到 System Agent Registry（ArangoDB），然後再註冊到 Agent Registry（內存），這樣才能正確標記為 `is_system_agent=True`。

2. **前端過濾**：前端 API 會自動過濾 System Agents，無需手動處理。

3. **系統內部調用**：系統內部查詢時，可以選擇包括 System Agents（`include_system_agents=True`）。

4. **命名規範**：
   - Agent ID：使用連字符格式（如 `document-editing-agent`）
   - 工具名稱：使用下劃線格式（如 `document_editing`）
   - Agent 類型：使用下劃線格式（如 `document_editing`）

---

**文檔版本**: v1.0
**最後更新**: 2026-01-09
**維護人**: Daniel Chung
