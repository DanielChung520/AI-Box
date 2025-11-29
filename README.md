# AI-Box

**版本**: 1.0.0
**最後更新**: 2025-01-27
**開發者**: Daniel Chung
**授權**: MIT License

---

## 📖 專案簡介

AI-Box 是一個統一的 AI Agent 管理與協調平台，提供多種 Agent 框架整合（AutoGen、CrewAI、LangGraph）、任務分析、工作流編排、記憶管理、知識圖譜構建等功能。系統採用微服務架構，支援 MCP (Model Context Protocol) 協議，提供完整的 RESTful API 接口。

### 核心特性

- 🤖 **多 Agent 框架支援**: AutoGen、CrewAI、LangGraph 混合模式
- 🧠 **智能任務分析**: 自動分析任務複雜度並選擇合適的工作流
- 💾 **記憶管理系統 (AAM)**: 短期記憶（Redis）+ 長期記憶（ChromaDB）+ 知識圖譜（ArangoDB）
- 🔄 **工作流編排**: 支援動態切換和混合模式編排
- 📊 **知識圖譜**: 自動構建和查詢知識圖譜
- 🔌 **MCP 協議**: 標準化的 Agent 通信協議
- 🚀 **RESTful API**: 完整的 API 接口文檔
- 🔀 **LLM 路由與負載均衡**: 多層級 LLM 路由和負載均衡系統

---

## 📁 專案目錄結構

```
AI-Box/
├── agent_process/          # Agent 處理核心模組
│   ├── context/           # 上下文管理（歷史、窗口、持久化）
│   ├── memory/            # 記憶管理
│   │   └── aam/          # AAM (記憶增強模組)
│   ├── prompt/            # Prompt 管理
│   ├── retrieval/         # 檢索管理
│   └── tools/             # 工具註冊
│
├── agents/                 # Agent 實現
│   ├── autogen/           # AutoGen Agent 實現
│   ├── crewai/            # CrewAI Agent 實現
│   ├── execution/         # 執行 Agent
│   ├── orchestrator/      # 編排器（基礎協調器）
│   ├── planning/          # 規劃 Agent
│   ├── review/            # 審查 Agent
│   ├── task_analyzer/     # 任務分析器
│   └── workflows/         # 工作流引擎（混合編排器）
│
├── services/              # 服務層
│   ├── api/               # FastAPI 服務（統一 API Gateway）
│   │   ├── clients/      # 客戶端（已統一使用 llm/clients）
│   │   ├── core/         # 核心功能
│   │   ├── main.py       # 主入口
│   │   ├── middleware/   # 中間件
│   │   ├── models/       # 數據模型
│   │   ├── processors/   # 文件處理器
│   │   ├── routers/      # 路由
│   │   └── services/     # 業務服務
│   ├── mcp_server/       # MCP Server 服務
│   └── security/          # 安全服務
│
├── databases/             # 數據庫適配器
│   ├── arangodb/          # ArangoDB 適配器
│   └── chromadb/          # ChromaDB 適配器
│
├── llm/                   # LLM 路由與客戶端
│   ├── clients/           # LLM 客戶端（統一接口）
│   │   ├── ollama.py     # Ollama 客戶端（統一實現）
│   │   ├── factory.py    # LLM 客戶端工廠
│   │   └── base.py       # 基礎接口定義
│   ├── router.py          # LLM 節點路由器（節點層級）
│   ├── load_balancer.py   # 多 LLM 負載均衡器（提供商層級）
│   └── routing/           # 路由策略
│       ├── dynamic.py     # 動態路由器（策略層級）
│       └── strategies.py # 路由策略實現
│
├── mcp_client/            # MCP 客戶端
├── mcp_server/            # MCP 服務器
├── core/                  # 核心功能
├── config/                 # 配置文件
├── tests/                  # 測試文件
├── docs/                   # 文檔
│   └── architecture/      # 架構文檔
│       ├── llm-routing-architecture.md    # LLM 路由架構
│       ├── orchestrator-usage.md          # Orchestrator 使用指南
│       └── factory-interface-spec.md      # Factory 接口規範
├── scripts/               # 腳本
├── infra/                 # 基礎設施配置
├── k8s/                   # Kubernetes 配置
└── backup/                 # 備份目錄
    ├── api-gateway-removed/    # API Gateway 備份（已移除重複實現）
    └── ollama-client-duplicate/ # OllamaClient 備份（已統一實現）
```

---

## 🚀 快速開始

### 環境要求

- Python >= 3.11
- Redis (用於短期記憶)
- ChromaDB (用於向量存儲)
- ArangoDB (用於知識圖譜，可選)
- Ollama (用於本地 LLM，可選)

### 安裝步驟

1. **克隆專案**
   ```bash
   git clone <repository-url>
   cd AI-Box
   ```

2. **創建虛擬環境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   ```

3. **安裝依賴**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置環境**
   ```bash
   cp config/config.example.json config/config.json
   # 編輯 config/config.json 設置數據庫連接等配置
   ```

5. **啟動服務**
   ```bash
   uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **訪問 API 文檔**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

---

## 📚 核心模組說明

### 1. Agent Process (agent_process/)

Agent 處理核心模組，提供上下文管理、記憶管理、檢索等功能。

#### Context (上下文管理)
- `history.py`: 歷史記錄管理
- `manager.py`: 上下文管理器
- `persistence.py`: 持久化
- `window.py`: 窗口管理

#### Memory (記憶管理)
- `manager.py`: 記憶管理器
- `aam/`: AAM (記憶增強模組)
  - `aam_core.py`: AAM 核心管理器
  - `async_processor.py`: 異步任務處理器
  - `hybrid_rag.py`: 混合 RAG 檢索
  - `kg_builder_integration.py`: 知識圖譜構建整合
  - `kg_query_integration.py`: 知識圖譜查詢整合
  - `knowledge_extraction_agent.py`: 知識提取 Agent
  - `realtime_retrieval.py`: 實時檢索
  - `storage_adapter.py`: 存儲適配器

### 2. Agents (agents/)

各種 Agent 實現和框架整合。

#### AutoGen (agents/autogen/)
- 實現 AutoGen 框架的 Agent
- 支援多 Agent 協作、計劃執行、成本估算

#### CrewAI (agents/crewai/)
- 實現 CrewAI 框架的多角色協作
- 支援任務調度、Token 預算管理

#### Task Analyzer (agents/task_analyzer/)
- 任務分析和分類
- 工作流選擇和 LLM 路由（任務層級）

#### Orchestrator (agents/orchestrator/)
- **AgentOrchestrator**: 基礎協調器，適用於簡單任務
- 詳見 [Orchestrator 使用指南](docs/architecture/orchestrator-usage.md)

#### Workflows (agents/workflows/)
- **HybridOrchestrator**: 混合工作流編排器，適用於複雜任務
- 支援 AutoGen、LangGraph、CrewAI 動態切換
- 詳見 [Orchestrator 使用指南](docs/architecture/orchestrator-usage.md)

### 3. Services (services/api/)

統一 API Gateway，提供各種業務服務和 API 接口。

#### 主要路由
- `agents.py`: Agent 管理
- `chromadb.py`: ChromaDB 操作
- `kg_builder.py`: 知識圖譜構建
- `kg_query.py`: 知識圖譜查詢
- `llm.py`: LLM 推理（使用統一 OllamaClient）
- `ner.py`: 命名實體識別
- `re.py`: 關係抽取
- `rt.py`: 關係類型分類
- `task_analyzer.py`: 任務分析
- `orchestrator.py`: Agent 協調

#### 文件處理器
- 支援 PDF、DOCX、CSV、JSON、HTML、Markdown、TXT、XLSX
- 使用 `ParserFactory` 統一管理

### 4. LLM 路由與負載均衡 (llm/)

多層級 LLM 路由和負載均衡系統。

#### 層級架構
1. **任務層級** (`agents/task_analyzer/llm_router.py`): 根據任務類型選擇 LLM 提供商
2. **策略層級** (`llm/routing/dynamic.py`): 動態路由策略管理
3. **提供商層級** (`llm/load_balancer.py`): 多 LLM 提供商負載均衡
4. **節點層級** (`llm/router.py`): Ollama 節點負載均衡

詳見 [LLM 路由架構文檔](docs/architecture/llm-routing-architecture.md)

#### LLM 客戶端
- **統一接口**: `llm/clients/base.py` 定義 `BaseLLMClient` 接口
- **Ollama 客戶端**: `llm/clients/ollama.py` 統一實現（已移除重複實現）
- **客戶端工廠**: `llm/clients/factory.py` 統一創建和管理 LLM 客戶端

### 5. Databases (databases/)

數據庫適配器，提供統一的數據庫接口。

- **ArangoDB**: 圖數據庫，用於知識圖譜
- **ChromaDB**: 向量數據庫，用於長期記憶

---

## 🏗️ 架構文檔

專案提供完整的架構文檔，幫助理解系統設計：

- [LLM 路由/負載均衡器層級架構](docs/architecture/llm-routing-architecture.md)
  - 說明 4 個層級的職責和關係
  - 提供使用場景示例

- [Orchestrator 使用場景指南](docs/architecture/orchestrator-usage.md)
  - 對比 AgentOrchestrator 和 HybridOrchestrator
  - 提供選擇指南和遷移建議

- [Factory 接口規範](docs/architecture/factory-interface-spec.md)
  - 定義統一的 Factory 接口規範
  - 對比現有 Factory 實現

---

## 🔧 配置說明

配置文件位於 `config/config.json`。

主要配置項：
- **databases**: 數據庫連接配置
- **services**: 服務配置
- **agents**: Agent 配置
- **security**: 安全配置
- **llm**: LLM 客戶端配置

---

## 🧪 測試

```bash
# 運行所有測試
pytest

# 運行特定測試
pytest tests/agent_process/test_aam_core.py
```

---

## 📝 開發規範

詳見 `.cursor/rules/develop-rule.mdc` 開發規範文件。

### 代碼質量檢查

```bash
# 格式化代碼
black .

# 檢查代碼風格
ruff check .

# 類型檢查
mypy .

# 運行所有檢查
pre-commit run --all-files
```

---

## 📖 API 文檔

啟動服務後，訪問以下地址查看 API 文檔：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🔄 最近更新

### 2025-01-27

- ✅ **統一 OllamaClient 實現**: 移除重複的 `services/api/clients/ollama_client.py`，統一使用 `llm/clients/ollama.py`
- ✅ **移除重複 API Gateway**: 統一使用 `services/api/` 作為唯一 API Gateway
- ✅ **建立架構文檔**: 新增 LLM 路由架構、Orchestrator 使用指南、Factory 接口規範文檔
- ✅ **代碼清理**: 移除重複功能，統一接口實現

---

## 📄 授權

本專案採用 MIT License 授權。

---

## 📞 聯繫方式

- **開發者**: Daniel Chung
- **Email**: daniel.chung@example.com

---

**最後更新**: 2025-01-27
