# AI-Box Agent Platform 遷移指南

**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**最後修改日期**: 2025-01-27

## 目錄

1. [概述](#概述)
2. [遷移前準備](#遷移前準備)
3. [內部 Agent 遷移](#內部-agent-遷移)
4. [外部 Agent 遷移](#外部-agent-遷移)
5. [認證配置遷移](#認證配置遷移)
6. [API 遷移](#api-遷移)
7. [常見問題](#常見問題)

---

## 概述

本指南幫助開發者將現有的 Agent 遷移到新的 AI-Box Agent Platform 架構。

### 遷移目標

- 統一 Agent 管理（通過 Registry）
- 支持內部/外部 Agent 區分
- 實現安全認證機制
- 資源訪問控制

### 遷移原則

1. **向後兼容**：盡量保持現有 API 不變
2. **逐步遷移**：分階段進行，降低風險
3. **充分測試**：每個階段都要進行測試驗證

---

## 遷移前準備

### 1. 檢查現有代碼

```bash
find . -name "*agent*.py" -type f
grep -r "register.*agent" --include="*.py"
```

### 2. 備份現有代碼

```bash
git checkout -b backup/before-migration
git push origin backup/before-migration
git checkout -b migration/agent-platform
```

---

## 內部 Agent 遷移

### 步驟 1：實現 AgentServiceProtocol

**之前**：

```python
class MyAgent:
    def execute_task(self, task_data):
        return result
```

**之後**：

```python
from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)

class MyAgent(AgentServiceProtocol):
    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        result = self.execute_task(request.task_data)
        return AgentServiceResponse(
            task_id=request.task_id,
            status="completed",
            result=result,
        )

    async def health_check(self) -> AgentServiceStatus:
        return AgentServiceStatus.AVAILABLE

    async def get_capabilities(self) -> dict:
        return {"description": "My agent capabilities"}
```

### 步驟 2：註冊 Agent

```python
from agents.services.registry.registry import get_agent_registry
from agents.services.registry.models import (
    AgentRegistrationRequest,
    AgentEndpoints,
    AgentMetadata,
    AgentPermissionConfig,
)
from agents.services.protocol.base import AgentServiceProtocolType

async def register_core_agents():
    registry = get_agent_registry()
    my_agent = MyAgent()

    request = AgentRegistrationRequest(
        agent_id="my-agent",
        agent_type="custom",
        name="My Agent",
        endpoints=AgentEndpoints(
            is_internal=True,
            protocol=AgentServiceProtocolType.HTTP,
        ),
        capabilities=["action1"],
        metadata=AgentMetadata(
            version="1.0.0",
            description="My agent",
        ),
        permissions=AgentPermissionConfig(),
    )

    registry.register_agent(request, instance=my_agent)
```

### 步驟 3：更新調用代碼

**之前**：

```python
agent = MyAgent()
result = agent.execute_task(task_data)
```

**之後**：

```python
from agents.services.registry.registry = get_agent_registry()
from agents.services.protocol.base import AgentServiceRequest

registry = get_agent_registry()
agent = registry.get_agent("my-agent")

request = AgentServiceRequest(
    task_id="task-1",
    task_type="execute",
    task_data=task_data,
)
response = await agent.execute(request)
result = response.result
```

---

## 外部 Agent 遷移

### 步驟 1：實現 HTTP API

```python
from fastapi import FastAPI
from agents.services.protocol.base import (
    AgentServiceRequest,
    AgentServiceResponse,
)

app = FastAPI()

@app.post("/execute")
async def execute(request: AgentServiceRequest) -> AgentServiceResponse:
    result = process_task(request.task_data)
    return AgentServiceResponse(
        task_id=request.task_id,
        status="completed",
        result=result,
    )
```

### 步驟 2：配置認證

```python
request = AgentRegistrationRequest(
    agent_id="external-agent",
    agent_type="external",
    name="External Agent",
    endpoints=AgentEndpoints(
        http="https://my-service.example.com/api",
        is_internal=False,
        protocol=AgentServiceProtocolType.HTTP,
    ),
    permissions=AgentPermissionConfig(
        api_key="your-api-key",
        ip_whitelist=["192.168.1.0/24"],
        allowed_memory_namespaces=["my-namespace"],
    ),
)
```

---

## 認證配置遷移

### 內部 Agent 認證

```python
permissions = AgentPermissionConfig()  # 默認配置即可
```

### 外部 Agent 認證

#### 僅 API Key

```python
permissions = AgentPermissionConfig(
    api_key="secret-key",
)
```

#### API Key + IP 白名單

```python
permissions = AgentPermissionConfig(
    api_key="secret-key",
    ip_whitelist=["192.168.1.0/24"],
    require_ip_check=True,
)
```

---

## API 遷移

### 舊 API（已棄用）

```http
POST /api/v1/agents/{agent_id}/execute
```

### 新 API

```http
POST /api/v1/agents/execute
Content-Type: application/json

{
  "agent_id": "my-agent",
  "task": {
    "type": "execute",
    "data": {...}
  }
}
```

---

## 常見問題

### Q1: 如何保持向後兼容？

A: 可以在過渡期間同時支持舊 API 和新 API，逐步遷移客戶端。

### Q2: 外部 Agent 如何獲取資源訪問權限？

A: 在註冊時通過 `permissions` 配置資源訪問權限。

### Q3: 遷移後性能會受影響嗎？

A: 內部 Agent 直接調用，性能影響最小。外部 Agent 通過 HTTP/MCP，會有網絡延遲。

---

## 遷移檢查清單

- [ ] 備份現有代碼
- [ ] 更新 Agent 實現 `AgentServiceProtocol`
- [ ] 配置 Agent 註冊
- [ ] 更新調用代碼
- [ ] 配置認證（外部 Agent）
- [ ] 配置資源權限（外部 Agent）
- [ ] 運行測試
- [ ] 更新文檔
- [ ] 部署到生產環境

---

**文檔版本**: 1.0.0
**最後更新**: 2025-01-27
