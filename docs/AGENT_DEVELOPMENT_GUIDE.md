# AI-Box Agent 開發手冊

**版本**: 1.0
**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**最後修改日期**: 2025-01-27
**適用系統**: AI-Box Agent Platform

---

## 目錄

1. [概覽](#1-概覽)
2. [如何開始](#2-如何開始)
3. [內部開發規範與通信標準](#3-內部開發規範與通信標準)
4. [協作夥伴開發規範與通信方式](#4-協作夥伴開發規範與通信方式)
5. [附錄](#5-附錄)

---

## 1. 概覽

### 1.1 AI-Box Agent Platform 簡介

AI-Box Agent Platform 是一個基於微服務架構的 Agent 協作平台，支持多團隊獨立開發和部署 Agent 服務。平台採用協調層與執行層分離的設計，通過標準化的協議接口實現 Agent 之間的通信和協作。

**核心特性**:
- ✅ **職責分離**: 協調層負責任務路由和調度，執行層負責具體 Agent 邏輯
- ✅ **獨立部署**: Agent 執行服務可以獨立部署和擴展
- ✅ **多協議支持**: 支持 HTTP REST API 和 MCP Protocol 兩種通信方式
- ✅ **團隊協作**: 支持不同團隊獨立開發和部署 Agent 服務
- ✅ **服務發現**: 自動化的 Agent 註冊和發現機制
- ✅ **負載均衡**: 支持多實例部署和負載均衡

### 1.2 架構設計

#### 1.2.1 整體架構

```
┌─────────────────────────────────────────────────────────┐
│              AI-Box 協調層（內建服務）                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Agent Registry（註冊表）                       │   │
│  │  - Agent 服務發現                               │   │
│  │  - 健康檢查                                     │   │
│  │  - 負載均衡                                     │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Agent Orchestrator（協調器）                    │   │
│  │  - 任務路由                                     │   │
│  │  - 任務分發                                     │   │
│  │  - 結果聚合                                     │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Task Analyzer（任務分析器）                     │   │
│  │  - 任務分類                                     │   │
│  │  - Agent 選擇                                   │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        ↓ HTTP / MCP
┌─────────────────────────────────────────────────────────┐
│          Agent 執行服務（獨立服務，可選部署）            │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Planning Agent Service                         │   │
│  │  - 計劃生成                                     │   │
│  │  - 計劃驗證                                     │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Execution Agent Service                        │   │
│  │  - 任務執行                                     │   │
│  │  - 狀態管理                                     │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Review Agent Service                            │   │
│  │  - 結果審查                                     │   │
│  │  - 質量檢查                                     │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Custom Agent Service（自定義 Agent）            │   │
│  │  - 團隊特定功能                                 │   │
│  │  - 業務邏輯                                     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              基礎設施層（共享）                         │
│  - Memory Manager（記憶管理）                           │
│  - Tool Registry（工具註冊表）                          │
│  - LLM Clients（LLM 客戶端）                            │
│  - Database（數據庫）                                   │
└─────────────────────────────────────────────────────────┘
```

#### 1.2.2 通信協議

**HTTP REST API**:
- 簡單易用，標準化
- 易於調試和監控
- 支持負載均衡和反向代理
- 適合簡單的請求-響應場景

**MCP Protocol**:
- 高性能，低延遲
- 支持雙向通信
- 適合實時協作場景
- 支持複雜的 Agent 協作

### 1.3 架構適應性

#### 1.3.1 內部開發團隊

**特點**:
- 直接訪問 AI-Box 內部服務
- 可以使用內部 API 和 SDK
- 緊密集成到 AI-Box 生態系統

**適用場景**:
- 核心 Agent（Planning、Execution、Review）
- 與 AI-Box 深度集成的 Agent
- 需要訪問內部資源的 Agent

#### 1.3.2 協作夥伴團隊

**特點**:
- 通過標準協議接口通信
- 獨立的部署和運維
- 最小化對 AI-Box 的依賴

**適用場景**:
- 第三方開發的 Agent
- 獨立部署的 Agent 服務
- 需要隔離的 Agent

---

## 2. 如何開始

### 2.1 Agent 註冊流程

#### 2.1.1 註冊步驟

1. **準備 Agent 服務**
   - 實現 Agent Service Protocol 接口
   - 配置服務端點（HTTP 或 MCP）
   - 準備服務元數據

2. **向 Registry 註冊**
   - 發送註冊請求到 Agent Registry
   - 提供 Agent 信息和端點配置
   - 等待審核（內部 Agent 自動通過）

3. **健康檢查**
   - Registry 自動進行健康檢查
   - Agent 服務需要實現 `/health` 端點
   - 定期發送心跳

4. **服務發現**
   - 其他服務通過 Registry 發現 Agent
   - 根據能力和狀態選擇 Agent

#### 2.1.2 註冊請求示例

**HTTP 註冊請求**:

```python
import httpx
from agents.services.registry.models import (
    AgentRegistrationRequest,
    AgentEndpoints,
    AgentMetadata,
    AgentPermissionConfig,
)
from agents.services.protocol.base import AgentServiceProtocolType

# 準備註冊請求
registration_request = AgentRegistrationRequest(
    agent_id="agent-research-team-a",
    agent_type="research",
    name="Research Agent (Team A)",
    endpoints=AgentEndpoints(
        http="http://agent-research-service:8000",
        mcp="ws://agent-research-service:8002",
        protocol=AgentServiceProtocolType.HTTP
    ),
    capabilities=["research", "web_search", "data_analysis"],
    metadata=AgentMetadata(
        version="1.0.0",
        description="Advanced research agent for AI trends",
        author="Team A",
        tags=["research", "ai", "analysis"]
    ),
    permissions=AgentPermissionConfig(
        read=True,
        write=False,
        execute=True,
        admin=False
    )
)

# 發送註冊請求
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://agent-registry:8080/api/v1/agents/register",
        json=registration_request.model_dump(),
        headers={"Authorization": f"Bearer {api_key}"}
    )
    response.raise_for_status()
    print(f"Agent registered: {response.json()}")
```

**MCP 註冊請求**:

```python
from agents.services.protocol.mcp_client import MCPAgentServiceClient

# 連接到 Registry MCP Server
registry_client = MCPAgentServiceClient(
    server_url="ws://agent-registry:8080/mcp",
    server_name="agent-registry"
)

await registry_client.initialize()

# 調用註冊工具
result = await registry_client.call_tool(
    "agents/register",
    arguments={
        "agent_id": "agent-research-team-a",
        "agent_type": "research",
        "name": "Research Agent (Team A)",
        "endpoints": {
            "http": "http://agent-research-service:8000",
            "mcp": "ws://agent-research-service:8002",
            "protocol": "http"
        },
        "capabilities": ["research", "web_search", "data_analysis"],
        "metadata": {
            "version": "1.0.0",
            "description": "Advanced research agent",
            "author": "Team A"
        }
    }
)

print(f"Registration result: {result}")
```

### 2.2 Agent 信息模型

#### 2.2.1 必需信息

```python
class AgentRegistrationRequest(BaseModel):
    """Agent 註冊請求"""

    agent_id: str  # Agent 唯一標識符
    agent_type: str  # Agent 類型（planning/execution/review/custom）
    name: str  # Agent 顯示名稱
    endpoints: AgentEndpoints  # 服務端點配置
    capabilities: List[str]  # 能力列表
    metadata: Optional[AgentMetadata]  # 元數據
    permissions: Optional[AgentPermissionConfig]  # 權限配置
```

#### 2.2.2 端點配置

```python
class AgentEndpoints(BaseModel):
    """Agent 端點配置"""

    http: Optional[str]  # HTTP 端點 URL（例如：http://agent-service:8000）
    mcp: Optional[str]  # MCP 端點 URL（例如：ws://agent-service:8002）
    protocol: AgentServiceProtocolType  # 默認協議類型（HTTP 或 MCP）
```

#### 2.2.3 元數據

```python
class AgentMetadata(BaseModel):
    """Agent 元數據"""

    version: str  # Agent 版本（例如："1.0.0"）
    description: Optional[str]  # Agent 描述
    author: Optional[str]  # 開發者/團隊
    tags: List[str]  # 標籤列表
    capabilities: Dict[str, Any]  # 能力描述（詳細信息）
```

---

## 3. 內部開發規範與通信標準

### 3.1 Agent Service Protocol 接口

所有內部開發的 Agent 必須實現 `AgentServiceProtocol` 接口：

```python
from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)

class MyAgentService(AgentServiceProtocol):
    """內部 Agent 服務實現"""

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        執行任務

        Args:
            request: Agent 服務請求

        Returns:
            Agent 服務響應
        """
        # 實現任務執行邏輯
        result = await self._process_task(request.task_data)

        return AgentServiceResponse(
            task_id=request.task_id,
            status="success",
            result=result,
        )

    async def health_check(self) -> AgentServiceStatus:
        """健康檢查"""
        # 檢查服務狀態
        if self._is_healthy():
            return AgentServiceStatus.AVAILABLE
        return AgentServiceStatus.UNAVAILABLE

    async def get_capabilities(self) -> Dict[str, Any]:
        """獲取服務能力"""
        return {
            "capabilities": ["task_execution", "data_analysis"],
            "version": "1.0.0",
        }
```

### 3.2 HTTP Agent Service 實現

#### 3.2.1 FastAPI 實現示例

```python
from fastapi import FastAPI, HTTPException
from agents.services.protocol.base import (
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)
from agents.core.planning.agent import PlanningAgent

app = FastAPI(title="Planning Agent Service")

# 初始化 Agent
agent = PlanningAgent()

@app.post("/v1/execute", response_model=AgentServiceResponse)
async def execute(request: AgentServiceRequest):
    """
    執行任務

    實現 AgentServiceProtocol.execute 接口
    """
    try:
        # 調用 Agent 執行任務
        result = await agent.execute_plan(
            task=request.task_data.get("task"),
            context=request.context or {},
        )

        return AgentServiceResponse(
            task_id=request.task_id,
            status="success",
            result=result.model_dump() if hasattr(result, "model_dump") else result,
        )
    except Exception as e:
        return AgentServiceResponse(
            task_id=request.task_id,
            status="error",
            error=str(e),
        )

@app.get("/v1/health")
async def health():
    """
    健康檢查

    實現 AgentServiceProtocol.health_check 接口
    """
    try:
        # 檢查 Agent 狀態
        if agent.is_available():
            return {"status": AgentServiceStatus.AVAILABLE.value}
        return {"status": AgentServiceStatus.UNAVAILABLE.value}
    except Exception:
        return {"status": AgentServiceStatus.ERROR.value}

@app.get("/v1/capabilities")
async def capabilities():
    """
    獲取服務能力

    實現 AgentServiceProtocol.get_capabilities 接口
    """
    return {
        "capabilities": ["plan_generation", "plan_validation"],
        "protocol": "http",
        "version": "1.0.0",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 3.2.2 使用 Agent Service Client

```python
from agents.services.protocol.http_client import HTTPAgentServiceClient
from agents.services.protocol.base import AgentServiceRequest

# 創建 Client
client = HTTPAgentServiceClient(
    base_url="http://planning-agent-service:8000",
    timeout=60.0,
    api_key="your-api-key"
)

# 執行任務
request = AgentServiceRequest(
    task_id="task-123",
    task_type="planning",
    task_data={"task": "生成研究計劃"},
    context={"user_id": "user-123"},
)

response = await client.execute(request)
print(f"Result: {response.result}")
```

### 3.3 MCP Agent Service 實現

#### 3.3.1 MCP Server 實現示例

```python
from mcp.server.server import MCPServer
from mcp.server.protocol.models import MCPTool, MCPToolCallRequest
from agents.core.planning.agent import PlanningAgent
import json

# 初始化 Agent
agent = PlanningAgent()

# 創建 MCP Server
mcp_server = MCPServer("planning-agent")

@mcp_server.tool("execute_task")
async def execute_task(
    task: str,
    context: dict = None,
    **kwargs
) -> dict:
    """
    執行計劃任務

    Args:
        task: 任務描述
        context: 上下文信息

    Returns:
        執行結果
    """
    try:
        result = await agent.execute_plan(
            task=task,
            context=context or {},
        )

        return {
            "status": "success",
            "result": result.model_dump() if hasattr(result, "model_dump") else result,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }

@mcp_server.tool("health_check")
async def health_check() -> dict:
    """健康檢查"""
    return {
        "status": "available" if agent.is_available() else "unavailable"
    }
```

#### 3.3.2 使用 MCP Client

```python
from agents.services.protocol.mcp_client import MCPAgentServiceClient
from agents.services.protocol.base import AgentServiceRequest

# 創建 MCP Client
client = MCPAgentServiceClient(
    server_url="ws://planning-agent-service:8002",
    server_name="planning-agent"
)

# 執行任務
request = AgentServiceRequest(
    task_id="task-123",
    task_type="planning",
    task_data={"task": "生成研究計劃"},
    context={"user_id": "user-123"},
)

response = await client.execute(request)
print(f"Result: {response.result}")
```

### 3.4 內部開發最佳實踐

#### 3.4.1 代碼結構

```
agent-planning-service/
├── main.py                 # FastAPI 入口
├── agent.py                # Agent 核心邏輯
├── models.py               # 數據模型
├── handlers.py             # MCP Handlers（可選）
├── config.py               # 配置管理
├── Dockerfile              # Docker 配置
├── requirements.txt        # 依賴
└── README.md              # 文檔
```

#### 3.4.2 配置管理

```python
# config.py
from pydantic_settings import BaseSettings

class AgentConfig(BaseSettings):
    """Agent 配置"""

    agent_id: str = "planning-agent"
    agent_name: str = "Planning Agent"
    version: str = "1.0.0"

    # 服務配置
    host: str = "0.0.0.0"
    port: int = 8000

    # Registry 配置
    registry_endpoint: str = "http://agent-registry:8080"
    registry_api_key: str = ""

    # LLM 配置
    llm_endpoint: str = "http://llm-service:8001"

    class Config:
        env_file = ".env"
        env_prefix = "AGENT_"

config = AgentConfig()
```

#### 3.4.3 錯誤處理

```python
from agents.services.protocol.base import AgentServiceResponse

async def execute_with_error_handling(
    request: AgentServiceRequest
) -> AgentServiceResponse:
    """帶錯誤處理的執行方法"""
    try:
        # 執行任務
        result = await agent.execute(request.task_data)

        return AgentServiceResponse(
            task_id=request.task_id,
            status="success",
            result=result,
        )
    except ValueError as e:
        # 業務邏輯錯誤
        return AgentServiceResponse(
            task_id=request.task_id,
            status="error",
            error=f"Validation error: {str(e)}",
        )
    except TimeoutError:
        # 超時錯誤
        return AgentServiceResponse(
            task_id=request.task_id,
            status="error",
            error="Task execution timeout",
        )
    except Exception as e:
        # 未知錯誤
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return AgentServiceResponse(
            task_id=request.task_id,
            status="error",
            error="Internal server error",
        )
```

#### 3.4.4 日誌記錄

```python
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def log_request(request: AgentServiceRequest):
    """記錄請求日誌"""
    logger.info(
        json.dumps({
            "event": "agent_request",
            "task_id": request.task_id,
            "task_type": request.task_type,
            "timestamp": datetime.utcnow().isoformat(),
        })
    )

def log_response(response: AgentServiceResponse):
    """記錄響應日誌"""
    logger.info(
        json.dumps({
            "event": "agent_response",
            "task_id": response.task_id,
            "status": response.status,
            "timestamp": datetime.utcnow().isoformat(),
        })
    )
```

---

## 4. 協作夥伴開發規範與通信方式

### 4.1 協作夥伴開發規範

#### 4.1.1 協議要求

協作夥伴開發的 Agent 必須實現以下協議之一：

1. **HTTP REST API**（推薦）
   - 實現標準的 RESTful API
   - 支持 JSON 格式的請求/響應
   - 實現健康檢查端點

2. **MCP Protocol**
   - 實現 MCP Server 接口
   - 支持標準的 MCP 方法
   - 實現工具列表和調用接口

#### 4.1.2 最小實現要求

**HTTP REST API 最小實現**:

```python
# 必需端點
POST /v1/execute      # 執行任務
GET  /v1/health       # 健康檢查
GET  /v1/capabilities # 獲取能力
```

**MCP Protocol 最小實現**:

```python
# 必需方法
initialize()      # 初始化連接
tools/list        # 列出工具
tools/call        # 調用工具
```

### 4.2 HTTP REST API 實現示例

#### 4.2.1 完整實現示例

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
app = FastAPI(title="Partner Agent Service")

# ============================================================================
# 數據模型（必須與 AI-Box Protocol 兼容）
# ============================================================================

class ExecuteRequest(BaseModel):
    """執行請求（兼容 AgentServiceRequest）"""
    task_id: str
    task_type: str
    task_data: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class ExecuteResponse(BaseModel):
    """執行響應（兼容 AgentServiceResponse）"""
    task_id: str
    status: str  # success, error, pending
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# ============================================================================
# Agent 核心邏輯
# ============================================================================

class PartnerAgent:
    """協作夥伴 Agent 實現"""

    def __init__(self):
        self.agent_id = "partner-agent-001"
        self.version = "1.0.0"

    async def execute_task(
        self,
        task_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        執行任務

        這是協作夥伴需要實現的核心邏輯
        """
        # 實現具體的任務執行邏輯
        task = task_data.get("task", "")

        # 示例：簡單的任務處理
        result = {
            "task": task,
            "status": "completed",
            "output": f"Processed: {task}",
        }

        return result

# 初始化 Agent
agent = PartnerAgent()

# ============================================================================
# API 端點實現
# ============================================================================

@app.post("/v1/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest):
    """
    執行任務端點

    必須實現此端點以兼容 AI-Box Protocol
    """
    try:
        logger.info(f"Received task: {request.task_id}")

        # 執行任務
        result = await agent.execute_task(
            task_data=request.task_data,
            context=request.context,
        )

        return ExecuteResponse(
            task_id=request.task_id,
            status="success",
            result=result,
        )
    except Exception as e:
        logger.error(f"Task execution failed: {e}", exc_info=True)
        return ExecuteResponse(
            task_id=request.task_id,
            status="error",
            error=str(e),
        )

@app.get("/v1/health")
async def health():
    """
    健康檢查端點

    必須實現此端點供 Registry 進行健康檢查
    """
    try:
        # 檢查服務狀態
        # 可以檢查數據庫連接、外部服務等
        is_healthy = True  # 實際的健康檢查邏輯

        if is_healthy:
            return {
                "status": "available",
                "agent_id": agent.agent_id,
                "version": agent.version,
            }
        else:
            return {
                "status": "unavailable",
                "agent_id": agent.agent_id,
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
        }

@app.get("/v1/capabilities")
async def capabilities():
    """
    獲取服務能力端點

    必須實現此端點供 Registry 了解 Agent 能力
    """
    return {
        "capabilities": ["task_execution", "custom_feature"],
        "protocol": "http",
        "version": agent.version,
        "agent_id": agent.agent_id,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 4.3 MCP Protocol 實現示例

#### 4.3.1 完整實現示例

```python
import asyncio
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

logger = logging.getLogger(__name__)

# ============================================================================
# Agent 核心邏輯
# ============================================================================

class PartnerAgent:
    """協作夥伴 Agent 實現"""

    def __init__(self):
        self.agent_id = "partner-agent-001"
        self.version = "1.0.0"

    async def execute_task(
        self,
        task_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """執行任務"""
        task = task_data.get("task", "")
        result = {
            "task": task,
            "status": "completed",
            "output": f"Processed: {task}",
        }
        return result

agent = PartnerAgent()

# ============================================================================
# MCP Server 實現
# ============================================================================

app = FastAPI(title="Partner Agent MCP Server")

@app.post("/mcp")
async def handle_mcp_request(request: Dict[str, Any]):
    """
    處理 MCP 請求

    必須實現此端點以支持 MCP Protocol
    """
    try:
        # 驗證請求格式
        if request.get("jsonrpc") != "2.0":
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request"
                    }
                }
            )

        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        # 路由到對應的方法
        if method == "initialize":
            result = await handle_initialize(params)
        elif method == "tools/list":
            result = await handle_list_tools()
        elif method == "tools/call":
            result = await handle_call_tool(params)
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            )

        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        )

    except Exception as e:
        logger.error(f"MCP request handling failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {"details": str(e)}
                }
            }
        )

async def handle_initialize(params: Dict[str, Any]) -> Dict[str, Any]:
    """處理初始化請求"""
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": agent.agent_id,
            "version": agent.version
        },
        "capabilities": {
            "tools": {}
        }
    }

async def handle_list_tools() -> Dict[str, Any]:
    """處理工具列表請求"""
    return {
        "tools": [
            {
                "name": "execute_task",
                "description": "執行任務",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "任務描述"
                        },
                        "context": {
                            "type": "object",
                            "description": "上下文信息"
                        }
                    },
                    "required": ["task"]
                }
            }
        ]
    }

async def handle_call_tool(params: Dict[str, Any]) -> Dict[str, Any]:
    """處理工具調用請求"""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if tool_name == "execute_task":
        try:
            # 執行任務
            result = await agent.execute_task(
                task_data={"task": arguments.get("task", "")},
                context=arguments.get("context"),
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "status": "success",
                            "result": result,
                        })
                    }
                ],
                "isError": False
            }
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "status": "error",
                            "error": str(e),
                        })
                    }
                ],
                "isError": True
            }
    else:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "error": f"Unknown tool: {tool_name}"
                    })
                }
            ],
            "isError": True
        }

@app.get("/health")
async def health():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "agent_id": agent.agent_id,
        "version": agent.version
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 4.4 協作夥伴開發最佳實踐

#### 4.4.1 認證和安全

```python
from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """驗證認證 Token"""
    token = credentials.credentials

    # 驗證 Token（可以調用 AI-Box 認證服務）
    if not is_valid_token(token):
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )

    return token

@app.post("/v1/execute")
async def execute(
    request: ExecuteRequest,
    token: str = Depends(verify_token)
):
    """需要認證的執行端點"""
    # 執行任務
    ...
```

#### 4.4.2 錯誤處理標準

```python
class AgentError(Exception):
    """Agent 錯誤基類"""
    pass

class ValidationError(AgentError):
    """驗證錯誤"""
    pass

class ExecutionError(AgentError):
    """執行錯誤"""
    pass

@app.post("/v1/execute")
async def execute(request: ExecuteRequest):
    """帶標準錯誤處理的執行端點"""
    try:
        # 驗證請求
        if not request.task_data:
            raise ValidationError("task_data is required")

        # 執行任務
        result = await agent.execute_task(request.task_data)

        return ExecuteResponse(
            task_id=request.task_id,
            status="success",
            result=result,
        )
    except ValidationError as e:
        return ExecuteResponse(
            task_id=request.task_id,
            status="error",
            error=f"Validation error: {str(e)}",
        )
    except ExecutionError as e:
        return ExecuteResponse(
            task_id=request.task_id,
            status="error",
            error=f"Execution error: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return ExecuteResponse(
            task_id=request.task_id,
            status="error",
            error="Internal server error",
        )
```

#### 4.4.3 監控和日誌

```python
import time
from datetime import datetime

@app.middleware("http")
async def log_requests(request, call_next):
    """請求日誌中間件"""
    start_time = time.time()

    # 記錄請求
    logger.info(
        json.dumps({
            "event": "request_start",
            "path": request.url.path,
            "method": request.method,
            "timestamp": datetime.utcnow().isoformat(),
        })
    )

    # 處理請求
    response = await call_next(request)

    # 記錄響應
    process_time = time.time() - start_time
    logger.info(
        json.dumps({
            "event": "request_end",
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "process_time": process_time,
            "timestamp": datetime.utcnow().isoformat(),
        })
    )

    return response

@app.get("/metrics")
async def metrics():
    """Prometheus 指標端點"""
    return """
# Agent metrics
agent_requests_total 100
agent_errors_total 2
agent_execution_time_seconds 1.5
"""
```

---

## 5. 附錄

### 5.1 完整項目結構示例

```
agent-service/
├── main.py                 # 服務入口
├── agent.py                # Agent 核心邏輯
├── models.py               # 數據模型
├── config.py               # 配置管理
├── handlers.py             # MCP Handlers（可選）
├── Dockerfile              # Docker 配置
├── docker-compose.yml      # Docker Compose 配置
├── requirements.txt        # Python 依賴
├── .env.example           # 環境變數示例
├── README.md              # 項目文檔
└── tests/                 # 測試文件
    ├── test_agent.py
    ├── test_api.py
    └── test_integration.py
```

### 5.2 環境變數配置

**必需環境變數**:
```bash
AGENT_ID=agent-research-001
AGENT_NAME=Research Agent
AGENT_VERSION=1.0.0
AGENT_REGISTRY_ENDPOINT=http://agent-registry:8080
AGENT_REGISTRY_API_KEY=your-api-key
PORT=8000
```

**可選環境變數**:
```bash
LOG_LEVEL=INFO
DATABASE_URL=postgresql://user:pass@localhost/db
LLM_ENDPOINT=http://llm-service:8001
```

### 5.3 Docker 配置示例

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製代碼
COPY . .

# 暴露端口
EXPOSE 8000

# 啟動服務
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.4 測試示例

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    """測試健康檢查端點"""
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "available"

def test_execute_task():
    """測試任務執行端點"""
    request = {
        "task_id": "test-123",
        "task_type": "test",
        "task_data": {"task": "test task"},
    }
    response = client.post("/v1/execute", json=request)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

### 5.5 常見問題

**Q: 如何選擇 HTTP 還是 MCP Protocol？**

A:
- **HTTP REST API**: 適合簡單的請求-響應場景，易於實現和調試
- **MCP Protocol**: 適合需要雙向通信或實時協作的場景

**Q: Agent 註冊後多久可以開始使用？**

A: 內部 Agent 註冊後立即可用。協作夥伴 Agent 需要等待審核通過。

**Q: 如何實現 Agent 間通信？**

A: 通過 Agent Registry 發現其他 Agent，然後使用 Agent Service Client 調用。

**Q: 如何處理 Agent 服務的擴展？**

A: 可以部署多個 Agent 實例，Registry 會自動進行負載均衡。

---

**文檔結束**
