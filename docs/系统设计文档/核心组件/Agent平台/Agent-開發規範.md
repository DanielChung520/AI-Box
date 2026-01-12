# AI-Box Agent 開發指南

**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-11

## 目錄

1. [概覽](#概覽)
2. [架構概述](#架構概述)
3. [快速開始](#快速開始)
4. [內部 Agent 開發](#內部-agent-開發)
5. [外部 Agent 開發](#外部-agent-開發)
6. [認證配置](#認證配置)
7. [資源訪問控制](#資源訪問控制)
8. [API 參考](#api-參考)
9. [最佳實踐](#最佳實踐)
10. [故障排除](#故障排除)

---

## 概覽

### AI-Box Agent Platform 簡介

AI-Box Agent Platform 是一個統一的 Agent 管理和協調平台，支持：

- **內建 Agent**：系統核心服務（Registry Manager、Security Manager、Orchestrator Manager、Storage Manager）
- **內部 Agent**：AI-Box 內部業務邏輯 Agent（Planning、Execution、Review 等）
- **外部 Agent**：第三方或協作夥伴開發的 Agent

### 架構特點

- **統一註冊**：所有 Agent 通過 Registry 統一管理
- **智能路由**：內部 Agent 直接調用，外部 Agent 通過 HTTP/MCP 調用
- **安全認證**：內部 Agent 寬鬆認證，外部 Agent 嚴格認證（mTLS、API Key、簽名、IP 白名單）
- **資源控制**：內部 Agent 完整權限，外部 Agent 受限權限

---

## 架構概述

### 架構分離設計

AI-Box Agent Platform 採用協調層與執行層分離的架構設計，支持多團隊協作和獨立開發。

#### 整體架構

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
│  │  Workflow Engine Service                        │   │
│  │  - AutoGen 工作流                               │   │
│  │  - CrewAI 工作流                                │   │
│  │  - LangGraph 工作流                             │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

#### 設計目標

1. **職責分離**: 協調層負責任務路由和調度，執行層負責具體 Agent 邏輯
2. **獨立部署**: Agent 執行服務可以獨立部署和擴展
3. **多協議支持**: 支持 HTTP REST API 和 MCP Protocol 兩種通信方式
4. **團隊協作**: 支持不同團隊獨立開發和部署 Agent 服務

### 三層架構

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Platform                        │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Registry     │  │ Orchestrator │  │ Security     │  │
│  │ Manager      │  │ Manager      │  │ Manager      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│          內建 Agent（無需註冊，直接使用）                  │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Planning     │  │ Execution    │  │ Review       │  │
│  │ Agent        │  │ Agent        │  │ Agent        │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│          內部 Agent（註冊後直接調用）                     │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Partner      │  │ External     │  │ Custom       │  │
│  │ Agent 1      │  │ Agent 2      │  │ Agent 3      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│          外部 Agent（註冊後通過 HTTP/MCP 調用）           │
└─────────────────────────────────────────────────────────┘
```

### Agent 類型對比

| 特性 | 內建 Agent | 內部 Agent | 外部 Agent |
|------|-----------|-----------|-----------|
| 註冊方式 | 無需註冊（啟動時自動初始化） | 通過 Registry API 註冊 | 通過 Registry API 註冊 |
| 調用） | 直接調用實例 | HTTP/MCP Client |
| 認證要求 | 無（內部信任） | 寬鬆（服務標識可選） | 嚴格（mTLS、API Key、簽名、IP 白名單） |
| 資源權限 | 完整權限 | 完整權限 | 受限權限（需配置） |
| 部署位置 | AI-Box 內部 | AI-Box 內部 | 外部服務器 |

---

## 快速開始

### 1. 環境準備

```bash
# 克隆項目
git clone https://github.com/your-org/ai-box.git
cd ai-box

# 創建虛擬環境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac

# 安裝依賴
pip install -r requirements.txt
```

### 2. 配置環境變數

創建 `.env` 文件：

```env
# Agent Platform 配置
AGENT_REGISTRY_ENABLED=true
AGENT_HEALTH_CHECK_INTERVAL=60
AGENT_HEARTBEAT_TIMEOUT=300

# 安全配置
SECURITY_ENABLED=false  # 開發模式
```

### 3. 啟動服務

```bash
# 啟動 FastAPI 服務
./scripts/start_services.sh
```

---

## 內部 Agent 開發

### 實現 AgentServiceProtocol

```python
from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)

class MyInternalAgent(AgentServiceProtocol):
    """我的內部 Agent"""

    def __init__(self):
        self.agent_id = "my-internal-agent"

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """執行任務"""
        result = {"message": "Task completed"}
        return AgentServiceResponse(
            task_id=request.task_id,
            status="completed",
            result=result,
            metadata=request.metadata,
        )

    async def health_check(self) -> AgentServiceStatus:
        return AgentServiceStatus.AVAILABLE

    async def get_capabilities(self) -> dict:
        return {"description": "My internal agent capabilities"}
```

### 註冊內部 Agent

```python
from agents.services.registry.registry import get_agent_registry
from agents.services.registry.models import (
    AgentRegistrationRequest,
    AgentEndpoints,
    AgentMetadata,
    AgentPermissionConfig,
)
from agents.services.protocol.base import AgentServiceProtocolType

my_agent = MyInternalAgent()

request = AgentRegistrationRequest(
    agent_id="my-internal-agent",
    agent_type="custom",
    name="My Internal Agent",
    endpoints=AgentEndpoints(
        is_internal=True,
        protocol=AgentServiceProtocolType.HTTP,
    ),
    capabilities=["custom_action"],
    metadata=AgentMetadata(
        version="1.0.0",
        description="My custom internal agent",
    ),
    permissions=AgentPermissionConfig(),
)

registry = get_agent_registry()
success = registry.register_agent(request, instance=my_agent)
```

---

## 外部 Agent 開發

### 通信協議

外部 Agent 支持兩種通信協議：

#### HTTP REST API

**優點**:

- 簡單易用，標準化
- 易於調試和監控
- 支持負載均衡和反向代理

**端點示例**:

```http
POST /v1/execute
Content-Type: application/json

{
  "task_id": "task-123",
  "task_type": "planning",
  "task_data": {...},
  "context": {...},
  "metadata": {...}
}
```

#### MCP Protocol

**優點**:

- 高性能，低延遲
- 支持雙向通信
- 適合實時協作場景

**使用場景**:

- 需要實時狀態更新
- 複雜的 Agent 協作
- 高性能要求

### 實現 HTTP API

外部 Agent 需要實現符合 `AgentServiceProtocol` 的 HTTP API：

```python
from fastapi import FastAPI
from agents.services.protocol.base import (
    AgentServiceRequest,
    AgentServiceResponse,
)

app = FastAPI()

@app.post("/execute")
async def execute(request: AgentServiceRequest) -> AgentServiceResponse:
    result = {"message": "External task completed"}
    return AgentServiceResponse(
        task_id=request.task_id,
        status="completed",
        result=result,
    )

@app.get("/health")
async def health_check():
    return {"status": "available"}

@app.get("/capabilities")
async def get_capabilities():
    return {"description": "External agent capabilities"}
```

### 獨立 Agent 服務開發

#### 目錄結構

```
agent-planning-service/
├── main.py                 # FastAPI 入口
├── agent.py                # Agent 實現
├── models.py               # 數據模型
├── handlers.py             # MCP Handlers（可選）
├── Dockerfile              # Docker 配置
├── requirements.txt        # 依賴
└── README.md              # 文檔
```

#### Agent 服務註冊流程

1. **Agent 服務啟動**
   - Agent 服務啟動後，自動向 Registry 註冊
   - 提供服務端點（HTTP 或 MCP）
   - 聲明服務能力和元數據

2. **健康檢查**
   - Registry 定期檢查 Agent 服務健康狀態
   - 自動移除不可用的服務

3. **服務發現**
   - Orchestrator 通過 Registry 發現可用的 Agent 服務
   - 根據任務類型選擇合適的 Agent

### 註冊外部 Agent

```python
request = AgentRegistrationRequest(
    agent_id="my-external-agent",
    agent_type="external",
    name="My External Agent",
    endpoints=AgentEndpoints(
        http="https://my-service.example.com/api",
        is_internal=False,
        protocol=AgentServiceProtocolType.HTTP,
    ),
    permissions=AgentPermissionConfig(
        api_key="your-api-key-here",
        ip_whitelist=["192.168.1.0/24"],
        allowed_memory_namespaces=["my-namespace"],
    ),
)

# 通過 API 註冊
import requests
response = requests.post(
    "http://ai-box/api/v1/agents/register",
    json=request.model_dump(),
)
```

---

## 認證配置

### 內部 Agent 認證

內部 Agent 默認信任，可選地驗證服務標識。

### 外部 Agent 認證

外部 Agent 支持多種認證方式：

#### 1. API Key 認證

```python
permissions = AgentPermissionConfig(
    api_key="your-secret-api-key",
)
```

#### 2. mTLS 認證

```python
permissions = AgentPermissionConfig(
    server_certificate="-----BEGIN CERTIFICATE-----\n...",
    require_mtls=True,
)
```

#### 3. 請求簽名（HMAC-SHA256）

```python
permissions = AgentPermissionConfig(
    api_key="your-secret-api-key",
    require_signature=True,
)
```

#### 4. IP 白名單

```python
permissions = AgentPermissionConfig(
    ip_whitelist=["192.168.1.0/24", "10.0.0.1"],
    require_ip_check=True,
)
```

---

## 資源訪問控制

### 內部 Agent 權限

內部 Agent 擁有完整權限，無需配置。

### 外部 Agent 權限配置

```python
permissions = AgentPermissionConfig(
    allowed_memory_namespaces=["namespace1", "namespace2"],
    allowed_tools=["tool1", "tool2"],
    allowed_llm_providers=["ollama", "openai"],
    allowed_databases=["chromadb", "arangodb"],
    allowed_file_paths=["/allowed/path/"],
)
```

---

## API 參考

### Agent Service Protocol

所有 Agent 服務必須實現以下接口：

```python
from abc import ABC, abstractmethod

class AgentServiceProtocol(ABC):
    """Agent 服務協議接口"""

    @abstractmethod
    async def execute(request: AgentServiceRequest) -> AgentServiceResponse:
        """執行任務"""
        pass

    @abstractmethod
    async def health_check() -> AgentServiceStatus:
        """健康檢查"""
        pass

    @abstractmethod
    async def get_capabilities() -> Dict[str, Any]:
        """獲取服務能力"""
        pass
```

### Agent Registry API

#### 註冊 Agent

```http
POST /api/v1/agents/register
Content-Type: application/json

{
  "agent_id": "my-agent",
  "agent_type": "custom",
  "name": "My Agent",
  "endpoints": {
    "http": "https://example.com/api",
    "is_internal": false
  },
  "capabilities": ["action1"],
  "permissions": {
    "api_key": "secret-key"
  }
}
```

#### 執行 Agent 任務

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

## 最佳實踐

### 1. Agent 設計原則

- **單一職責**：每個 Agent 專注於一個特定任務
- **可組合性**：Agent 之間可以協作完成複雜任務
- **可擴展性**：易於添加新功能和能力

### 2. 服務設計

- **單一職責**: 每個 Agent 服務只負責一種類型的任務
- **無狀態**: Agent 服務應該是無狀態的，狀態存儲在共享數據庫
- **可擴展**: 支持水平擴展，多個實例可以並行運行

### 3. 錯誤處理

```python
async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
    try:
        result = process_task(request.task_data)
        return AgentServiceResponse(
            task_id=request.task_id,
            status="completed",
            result=result,
        )
    except ValueError as e:
        return AgentServiceResponse(
            task_id=request.task_id,
            status="error",
            error=str(e),
        )
```

**錯誤處理最佳實踐**:

- **優雅降級**: 服務不可用時，應該返回明確的錯誤信息
- **重試機制**: 協調層應該實現重試邏輯
- **超時處理**: 設置合理的超時時間

### 4. 日誌記錄

```python
import logging
logger = logging.getLogger(__name__)

async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
    logger.info(f"Executing task {request.task_id}")
    # ...
    logger.debug(f"Task {request.task_id} completed")
```

**監控和日誌最佳實踐**:

- **健康檢查**: 實現 `/health` 端點
- **指標收集**: 收集執行時間、成功率等指標
- **結構化日誌**: 使用結構化日誌格式

### 5. 安全性

- **認證**: 使用 API Key 或 OAuth 進行認證
- **授權**: 實現基於角色的訪問控制
- **加密**: 使用 HTTPS/WSS 進行通信

---

## 遷移計劃

### Phase 1: 接口抽象（已完成）

- ✅ 創建 Agent Service Protocol 接口定義
- ✅ 實現 HTTP 和 MCP Client
- ✅ 更新 Registry 支持 Client 創建

### Phase 2: 示例服務（進行中）

- ⏳ 創建 Planning Agent Service 示例
- ⏳ 實現服務註冊和健康檢查
- ⏳ 更新 Orchestrator 使用 Client

### Phase 3: 完整遷移

- ⏸️ 將所有 Agent 遷移到獨立服務
- ⏸️ 實現服務發現和負載均衡
- ⏸️ 添加監控和日誌

---

## 故障排除

### 常見問題

#### 1. Agent 註冊失敗

**問題**：外部 Agent 註冊時返回 400 錯誤

**解決方案**：

- 檢查是否提供了至少一種認證方式
- 驗證 `endpoints.is_internal` 設置正確
- 檢查端點 URL 格式是否正確

#### 2. 認證失敗

**問題**：外部 Agent 調用時返回 401 錯誤

**解決方案**：

- 檢查 API Key 是否正確
- 驗證請求簽名是否正確生成
- 確認 IP 地址在白名單中

---

---

**文檔版本**: 1.1.0
**最後更新**: 2026-01-11

**更新說明**: 整合 `ARCHITECTURE_AGENT_SEPARATION.md` 的內容，包括架構分離設計、通信協議、Agent Service Protocol、獨立服務開發、遷移計劃和最佳實踐。
