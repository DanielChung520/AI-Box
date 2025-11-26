# AI-Box 專案目錄結構說明

## 概述

本文檔詳細說明 AI-Box 專案的目錄結構設計，解釋看似重複的目錄之間的關係和設計意圖。

## 完整目錄樹

```
AI-Box/
├── agent_process/              # Agent 通用處理組件（可被多個 Agent 共享）
├── agents/                     # 具體的 Agent 實現（Planning, Execution, Review 等）
├── api_gateway/                # ⚠️ 舊版 API Gateway（已遷移至 services/api）
├── config/                     # 專案配置文件
├── core/                       # 核心工具模組（配置讀取等）
├── databases/                  # 資料庫 SDK 封裝（客戶端庫）
├── datasets/                   # 數據存儲目錄（運行時數據、Schema、種子數據）
├── docs/                       # 文檔目錄
├── infra/                      # 基礎設施配置腳本
├── k8s/                        # Kubernetes 部署配置
├── llm/                        # LLM 路由和負載均衡
├── mcp_client/                 # MCP Client 實現
├── mcp_server/                 # MCP Server 核心實現（協議、服務器類）
├── services/                   # 可部署的服務（獨立進程）
│   ├── api/                   # FastAPI 服務（從 api_gateway 遷移）
│   ├── mcp-server/            # MCP Server 服務包裝（啟動入口、配置）
│   └── security/              # 安全模組
├── scripts/                    # 工具腳本
└── tests/                      # 測試代碼
```

---

## 重要目錄對比說明

### 1. `databases/` vs `datasets/`

這兩個目錄的用途完全不同：

#### `databases/` - 資料庫客戶端 SDK 封裝

**用途**：提供資料庫操作的 Python 客戶端庫封裝

**內容**：
- `databases/chromadb/` - ChromaDB 客戶端封裝
  - `client.py` - 客戶端類，提供連線池管理
  - `collection.py` - Collection 封裝類
  - `utils.py` - 工具函數
  - `README.md` - 使用文檔

- `databases/arangodb/` - ArangoDB 客戶端封裝
  - `client.py` - 客戶端類，提供連線管理
  - `graph.py` - 圖操作封裝
  - `queries.py` - 預定義查詢
  - `settings.py` - 配置管理
  - `README.md` - 使用文檔

**使用方式**：
```python
from databases.chromadb import ChromaDBClient
from databases.arangodb import ArangoDBClient

# 使用封裝的客戶端
client = ChromaDBClient()
```

#### `datasets/` - 數據存儲目錄

**用途**：存放實際的數據文件和配置

**內容**：
- `datasets/chromadb/` - ChromaDB 運行時數據存儲目錄（持久化模式）
- `datasets/arangodb/` - ArangoDB 相關數據
  - `schema.yml` - Schema 定義文件
  - `seed_data.json` - 種子數據（初始數據）

**設計意圖**：
- `databases/` = **代碼庫**（如何操作資料庫）
- `datasets/` = **數據庫**（實際存儲的數據）

**類比**：
- `databases/` 類似於 "驅動程序" 或 "SDK"
- `datasets/` 類似於 "數據目錄" 或 "數據庫文件夾"

---

### 2. `mcp_server/` vs `services/mcp-server/`

這兩個目錄是**分層設計**的結果：

#### `mcp_server/` - MCP Server 核心實現

**用途**：MCP 協議和服務器的核心實現（可復用的庫）

**內容**：
- `mcp_server/server.py` - `MCPServer` 核心類
- `mcp_server/protocol/models.py` - MCP 協議數據模型

**特點**：
- 純 Python 類和函數
- 不依賴 FastAPI 或其他 Web 框架
- 可以被其他模組導入使用
- 類似於一個"庫"或"SDK"

**使用方式**：
```python
from mcp_server.server import MCPServer

# 創建服務器實例
server = MCPServer(name="my-server")
```

#### `services/mcp-server/` - MCP Server 服務包裝

**用途**：將 MCP Server 包裝成一個可獨立運行的服務

**內容**：
- `services/mcp-server/main.py` - 服務啟動入口
- `services/mcp-server/config.py` - 服務配置管理
- `services/mcp-server/monitoring.py` - 監控指標
- `services/mcp-server/tools/` - 工具實現和註冊
- `services/mcp-server/README.md` - 服務文檔

**特點**：
- 包含完整的服務配置（host, port, 環境變數）
- 提供服務啟動入口（`main()` 函數）
- 包含工具註冊邏輯
- 可以被 Docker/K8s 部署

**設計意圖**：
- `mcp_server/` = **核心實現**（可復用的庫）
- `services/mcp-server/` = **服務包裝**（可部署的服務）

**類比**：
- `mcp_server/` 類似於 "庫文件"（如 `requests` 庫）
- `services/mcp-server/` 類似於 "應用程序"（如使用 `requests` 構建的 Web 服務）

**使用方式**：
```bash
# 作為服務啟動
python -m services.mcp_server.main

# 在 Docker 中運行
docker-compose up mcp-server
```

---

### 3. `agents/` vs `agent_process/`

這兩個目錄是**職責分離**的設計：

#### `agents/` - 具體的 Agent 實現

**用途**：實現具體的 Agent 類（業務邏輯層）

**內容**：
- `agents/planning/agent.py` - PlanningAgent 類
- `agents/execution/agent.py` - ExecutionAgent 類
- `agents/review/agent.py` - ReviewAgent 類
- `agents/task_analyzer/analyzer.py` - TaskAnalyzer 類
- `agents/orchestrator/orchestrator.py` - AgentOrchestrator 類

**特點**：
- 每個子目錄對應一個具體的 Agent 類型
- 包含 Agent 的業務邏輯
- 使用 `agent_process/` 中的組件
- 可以有對應的 MCP Server 實現

**使用方式**：
```python
from agents.planning.agent import PlanningAgent
from agents.execution.agent import ExecutionAgent

# 使用具體的 Agent
planning = PlanningAgent()
plan = planning.generate_plan(request)
```

#### `agent_process/` - Agent 通用處理組件

**用途**：提供 Agent 運行的通用組件（基礎設施層）

**內容**：
- `agent_process/tools/registry.py` - 工具註冊表（所有 Agent 共享）
- `agent_process/memory/manager.py` - 記憶管理器
- `agent_process/prompt/manager.py` - 提示管理器
- `agent_process/retrieval/manager.py` - 檢索管理器
- `agent_process/context/recorder.py` - 上下文記錄器

**特點**：
- 提供通用的、可復用的組件
- 不包含具體的業務邏輯
- 可以被多個 Agent 共享使用
- 類似於"中間件"或"工具庫"

**設計意圖**：
- `agents/` = **業務邏輯**（具體做什麼）
- `agent_process/` = **基礎設施**（如何做）

**類比**：
- `agents/` 類似於 "應用程序"（如郵件客戶端）
- `agent_process/` 類似於 "操作系統 API"（如文件系統、網絡庫）

**使用方式**：
```python
from agent_process.tools import ToolRegistry
from agent_process.memory import MemoryManager

# 多個 Agent 共享同一套工具和記憶系統
tool_registry = ToolRegistry()
memory_manager = MemoryManager()

planning = PlanningAgent(memory_manager=memory_manager)
execution = ExecutionAgent(tool_registry=tool_registry)
```

**依賴關係**：
```
agents/ (依賴) → agent_process/
```

---

## 目錄設計原則

### 1. 分層架構

```
┌─────────────────────────────────────┐
│   services/ (服務層 - 可部署)       │
│   - api/                            │
│   - mcp-server/                     │
└──────────────┬──────────────────────┘
               │ 使用
┌──────────────▼──────────────────────┐
│   agents/ (業務邏輯層)              │
│   - planning/                       │
│   - execution/                      │
└──────────────┬──────────────────────┘
               │ 使用
┌──────────────▼──────────────────────┐
│   agent_process/ (基礎設施層)       │
│   - tools/                          │
│   - memory/                         │
└──────────────┬──────────────────────┘
               │ 使用
┌──────────────▼──────────────────────┐
│   databases/ (數據訪問層)           │
│   - chromadb/                       │
│   - arangodb/                       │
└─────────────────────────────────────┘
```

### 2. 職責分離

- **代碼 vs 數據**：`databases/` (代碼) vs `datasets/` (數據)
- **核心 vs 服務**：`mcp_server/` (核心) vs `services/mcp-server/` (服務)
- **業務 vs 基礎設施**：`agents/` (業務) vs `agent_process/` (基礎設施)

### 3. 可復用性

- `mcp_server/` 可以被其他項目復用
- `agent_process/` 可以被所有 Agent 共享
- `databases/` 可以被其他模組使用

### 4. 可部署性

- `services/` 目錄下的每個子目錄都是一個可獨立部署的服務
- 每個服務都有獨立的配置和啟動入口

---

## 遷移歷史

### `api_gateway/` → `services/api/`

- **原因**：統一服務目錄結構，所有服務都在 `services/` 下
- **狀態**：`api_gateway/` 保留作為兼容層，但新代碼應使用 `services/api/`

---

## 建議的目錄使用指南

### 開發新功能時

1. **如果是新的 Agent**：
   - 在 `agents/` 下創建新的子目錄
   - 使用 `agent_process/` 中的組件

2. **如果是新的資料庫操作**：
   - 在 `databases/` 下擴展現有封裝
   - 數據文件放在 `datasets/` 對應目錄

3. **如果是新的服務**：
   - 在 `services/` 下創建新的服務目錄
   - 包含配置、主入口、README

4. **如果是新的工具**：
   - 在 `agent_process/tools/` 下添加
   - 或創建 `services/*/tools/` 下的服務特定工具

---

## 總結

| 目錄對 | 關係 | 設計原則 |
|--------|------|----------|
| `databases/` vs `datasets/` | 代碼 vs 數據 | 職責分離 |
| `mcp_server/` vs `services/mcp-server/` | 核心 vs 服務 | 分層架構 |
| `agents/` vs `agent_process/` | 業務 vs 基礎設施 | 職責分離 |

這些看似重複的目錄實際上是**分層設計**和**職責分離**的體現，有助於：
- 提高代碼復用性
- 降低耦合度
- 便於獨立測試和部署
- 符合單一職責原則

---

**最後更新**: 2025-11-26
**維護人**: Daniel Chung
