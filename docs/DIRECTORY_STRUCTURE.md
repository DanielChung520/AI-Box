# AI-Box 目錄結構文字稿

**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**用途**: 詳細說明重構後的目標目錄結構

## 📐 完整目錄結構

```
AI-Box/
│
├── genai/                                    # 1. GenAI 相關組件
│   ├── __init__.py
│   ├── api/                                  # 界面層 FastAPI（GenAI 相關路由）
│   │   ├── __init__.py
│   │   ├── routers/                          # GenAI 路由
│   │   │   ├── __init__.py
│   │   │   ├── langchain.py                 # LangChain 工作流路由
│   │   │   ├── rag.py                       # RAG 檢索路由
│   │   │   ├── ner.py                       # NER（命名實體識別）路由
│   │   │   ├── re.py                        # RE（關係抽取）路由
│   │   │   ├── rt.py                        # RT（關係類型分類）路由
│   │   │   ├── triple_extraction.py         # 三元組提取路由
│   │   │   ├── kg_builder.py                # 知識圖譜構建路由
│   │   │   ├── kg_query.py                  # 知識圖譜查詢路由
│   │   │   ├── context_record.py            # Context Record 路由
│   │   │   ├── aam_async_tasks.py           # AAM 異步任務路由
│   │   │   └── chunk_processing.py          # 文件分塊處理路由
│   │   ├── services/                         # GenAI 業務服務
│   │   │   ├── __init__.py
│   │   │   ├── ner_service.py               # NER 服務
│   │   │   ├── re_service.py                # RE 服務
│   │   │   ├── rt_service.py                # RT 服務
│   │   │   ├── triple_extraction_service.py # 三元組提取服務
│   │   │   └── kg_builder_service.py        # 知識圖譜構建服務
│   │   └── models/                           # GenAI 相關模型
│   │       ├── __init__.py
│   │       ├── ner_models.py                # NER 數據模型
│   │       ├── re_models.py                 # RE 數據模型
│   │       ├── rt_models.py                 # RT 數據模型
│   │       ├── triple_models.py             # 三元組數據模型
│   │       └── kg_models.py                 # 知識圖譜數據模型
│   ├── workflows/                            # 工作流引擎
│   │   ├── __init__.py
│   │   ├── langchain/                       # LangChain 工作流
│   │   │   ├── __init__.py
│   │   │   ├── workflow.py                 # LangChain 工作流實現
│   │   │   ├── settings.py                 # LangChain 配置
│   │   │   └── state.py                    # 狀態定義
│   │   ├── rag/                             # RAG 相關
│   │   │   ├── __init__.py
│   │   │   ├── hybrid_rag.py               # 混合 RAG
│   │   │   ├── retrieval_service.py        # 檢索服務
│   │   │   └── strategies.py               # 檢索策略
│   │   └── context/                         # Context Record
│   │       ├── __init__.py
│   │       ├── recorder.py                 # Context 記錄器
│   │       ├── manager.py                  # Context 管理器
│   │       ├── persistence.py              # Context 持久化
│   │       ├── storage.py                  # Context 存儲
│   │       └── window.py                   # Context 窗口管理
│   └── prompt/                              # Prompt 管理
│       ├── __init__.py
│       └── manager.py                      # Prompt 管理器
│
├── mcp/                                     # 2. MCP Server 和 Client
│   ├── __init__.py
│   ├── server/                              # MCP Server
│   │   ├── __init__.py
│   │   ├── protocol/                        # MCP 協議定義
│   │   │   ├── __init__.py
│   │   │   ├── models.py                   # MCP 協議模型
│   │   │   └── messages.py                 # MCP 消息定義
│   │   ├── server.py                        # MCP Server 核心實現
│   │   ├── config.py                        # MCP Server 配置
│   │   ├── monitoring.py                    # MCP Server 監控
│   │   └── tools/                           # MCP 工具
│   │       ├── __init__.py
│   │       ├── registry.py                 # 工具註冊表
│   │       ├── base.py                     # 工具基類
│   │       ├── task_analyzer.py            # Task Analyzer 工具
│   │       └── file_tool.py                # 文件工具
│   └── client/                              # MCP Client
│       ├── __init__.py
│       ├── client.py                        # MCP Client 核心
│       └── connection/                      # 連接管理
│           ├── __init__.py
│           ├── manager.py                  # 連接管理器
│           ├── pool.py                     # 連接池
│           └── strategies.py               # 連接策略
│
├── database/                                # 3. Database 相關組件（多個服務）
│   ├── __init__.py
│   ├── chromadb/                            # ChromaDB 服務（單一服務）
│   │   ├── __init__.py
│   │   ├── client.py                       # ChromaDB 客戶端
│   │   ├── collection.py                   # Collection 封裝
│   │   ├── utils.py                        # 工具函數
│   │   └── exceptions.py                   # 異常定義
│   ├── arangodb/                            # ArangoDB 服務（單一服務）
│   │   ├── __init__.py
│   │   ├── client.py                       # ArangoDB 客戶端
│   │   ├── collection.py                   # Collection 封裝
│   │   ├── graph.py                        # Graph 操作
│   │   ├── queries.py                      # AQL 查詢封裝
│   │   ├── settings.py                     # ArangoDB 配置
│   │   └── exceptions.py                   # 異常定義
│   ├── redis/                               # Redis 服務（如果需要單獨封裝）
│   │   ├── __init__.py
│   │   └── client.py                       # Redis 客戶端
│   └── personnel/                           # Personnel Data 服務
│       ├── __init__.py
│       ├── models.py                       # Personnel 數據模型
│       ├── service.py                      # Personnel 服務
│       └── api.py                          # Personnel API
│
├── llm/                                     # 4. LLM 模型層
│   ├── __init__.py
│   ├── moe/                                 # MoE（Mixture of Experts）
│   │   ├── __init__.py
│   │   └── moe_manager.py                  # MoE 管理器
│   ├── abstraction/                         # 模型抽象層
│   │   ├── __init__.py
│   │   ├── base_client.py                  # 基礎 LLM 客戶端接口
│   │   ├── factory.py                      # LLM 客戶端工廠
│   │   └── adapter.py                      # 適配器模式
│   ├── clients/                             # LLM 客戶端實現
│   │   ├── __init__.py
│   │   ├── ollama.py                       # Ollama 客戶端
│   │   ├── chatgpt.py                      # ChatGPT 客戶端
│   │   ├── gemini.py                       # Gemini 客戶端
│   │   ├── grok.py                         # Grok 客戶端
│   │   └── qwen.py                         # Qwen 客戶端
│   ├── routing/                             # LLM 路由策略
│   │   ├── __init__.py
│   │   ├── dynamic_router.py               # 動態路由器
│   │   ├── strategies/                     # 各種路由策略
│   │   │   ├── __init__.py
│   │   │   ├── task_type_strategy.py      # 任務類型策略
│   │   │   ├── complexity_strategy.py     # 複雜度策略
│   │   │   ├── cost_strategy.py           # 成本策略
│   │   │   └── latency_strategy.py        # 延遲策略
│   │   └── evaluator.py                    # 路由評估器
│   ├── load_balancer.py                    # 負載均衡
│   ├── failover.py                         # 故障轉移
│   ├── router.py                           # LLM 路由器
│   └── config.py                           # LLM 配置
│
├── agents/                                  # 5. Agent 服務層
│   ├── __init__.py
│   ├── infra/                               # Agent 基礎設施
│   │   ├── __init__.py
│   │   ├── memory/                          # 記憶管理（從 agent_process/memory/ 整合）
│   │   │   ├── __init__.py
│   │   │   ├── manager.py                  # Memory Manager 實現
│   │   │   └── aam/                         # AAM（記憶增強模組）
│   │   │       ├── __init__.py
│   │   │       ├── aam_core.py             # AAM 核心管理器
│   │   │       ├── models.py               # AAM 數據模型
│   │   │       ├── storage_adapter.py      # 存儲適配器
│   │   │       ├── context_integration.py   # Context 集成
│   │   │       ├── kg_query_integration.py  # KG 查詢集成
│   │   │       ├── kg_builder_integration.py # KG 構建集成
│   │   │       ├── hybrid_rag.py           # 混合 RAG
│   │   │       ├── realtime_retrieval.py   # 實時檢索
│   │   │       ├── knowledge_extraction_agent.py # 知識提取 Agent
│   │   │       └── async_processor.py       # 異步處理器
│   │   └── tools/                           # 工具註冊表（從 agent_process/tools/ 整合）
│   │       ├── __init__.py
│   │       └── registry.py                 # Tool Registry 實現
│   ├── services/                            # Agent 協調服務
│   │   ├── __init__.py
│   │   ├── registry/                        # Agent 註冊服務
│   │   │   ├── __init__.py
│   │   │   ├── registry.py                 # Agent Registry 核心
│   │   │   ├── discovery.py                # Agent 發現服務
│   │   │   ├── health_monitor.py           # 健康檢查監控
│   │   │   ├── auto_registration.py        # 自動註冊服務
│   │   │   ├── task_executor.py            # 任務執行器
│   │   │   ├── adapter.py                  # 適配器
│   │   │   └── models.py                   # Registry 數據模型
│   │   ├── orchestrator/                    # Agent 協調器
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py             # Orchestrator 核心
│   │   │   └── models.py                   # Orchestrator 數據模型
│   │   ├── processing/                      # 結果處理
│   │   │   ├── __init__.py
│   │   │   ├── aggregator.py               # 結果聚合器
│   │   │   └── report_generator.py         # 報告生成器
│   │   └── file_service/                    # Agent 文件服務
│   │       ├── __init__.py
│   │       ├── file_service.py             # 文件服務核心
│   │       └── models.py                   # 文件服務數據模型
│   ├── core/                                # 核心 Agent 實現
│   │   ├── __init__.py
│   │   ├── planning/                        # Planning Agent
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                    # Planning Agent 實現
│   │   │   ├── handlers.py                 # MCP Handlers
│   │   │   └── models.py                   # Planning 數據模型
│   │   ├── execution/                       # Execution Agent
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                    # Execution Agent 實現
│   │   │   ├── handlers.py                 # MCP Handlers
│   │   │   └── models.py                   # Execution 數據模型
│   │   └── review/                          # Review Agent
│   │       ├── __init__.py
│   │       ├── agent.py                    # Review Agent 實現
│   │       ├── handlers.py                 # MCP Handlers
│   │       └── models.py                   # Review 數據模型
│   ├── workflows/                           # Agent 工作流引擎
│   │   ├── __init__.py
│   │   ├── langchain_graph/                # LangChain Graph 工作流
│   │   │   ├── __init__.py
│   │   │   └── workflow.py                 # LangChain Graph 工作流實現
│   │   ├── crewai/                          # CrewAI 工作流
│   │   │   ├── __init__.py
│   │   │   ├── workflow.py                 # CrewAI 工作流實現
│   │   │   ├── process_engine.py           # Process Engine
│   │   │   ├── agent_roles.py              # Agent 角色定義
│   │   │   ├── settings.py                 # CrewAI 配置
│   │   │   └── ...
│   │   ├── autogen/                         # AutoGen 工作流
│   │   │   ├── __init__.py
│   │   │   ├── workflow.py                 # AutoGen 工作流實現
│   │   │   ├── coordinator.py              # AutoGen 協調器
│   │   │   ├── settings.py                 # AutoGen 配置
│   │   │   └── ...
│   │   └── hybrid_orchestrator.py          # 混合編排器
│   └── task_analyzer/                       # 任務分析
│       ├── __init__.py
│       ├── analyzer.py                     # 任務分析器
│       ├── workflow_selector.py            # 工作流選擇器
│       ├── decision_engine.py              # 決策引擎
│       ├── llm_router.py                   # LLM 路由器
│       └── models.py                       # 任務分析數據模型
│
├── system/                                  # 6. 系統管理
│   ├── __init__.py
│   ├── security/                            # 安全服務
│   │   ├── __init__.py
│   │   ├── auth.py                         # 認證服務
│   │   ├── middleware.py                   # 安全中間件
│   │   ├── dependencies.py                 # 安全依賴注入
│   │   ├── config.py                       # 安全配置
│   │   └── models.py                       # 安全數據模型
│   ├── infra/                               # 基礎設施
│   │   ├── __init__.py
│   │   ├── config/                          # 配置管理
│   │   │   ├── __init__.py
│   │   │   └── config.py                   # 配置讀取工具
│   │   ├── logging/                         # 日誌管理
│   │   │   ├── __init__.py
│   │   │   ├── logger.py                   # 日誌器
│   │   │   └── formatter.py                # 日誌格式化器
│   │   └── monitoring/                      # 監控
│   │       ├── __init__.py
│   │       └── metrics.py                  # 指標收集
│   └── n8n/                                 # n8n 工作流集成（未來）
│       ├── __init__.py
│       └── workflows/                       # n8n 工作流定義
│
├── api/                                     # API 界面層（統一入口）
│   ├── __init__.py
│   ├── main.py                              # FastAPI 主應用
│   ├── routers/                             # 所有 API 路由
│   │   ├── __init__.py
│   │   ├── health.py                        # 健康檢查路由
│   │   ├── agents.py                        # Agents 路由
│   │   ├── agent_registry.py                # Agent Registry 路由
│   │   ├── agent_catalog.py                 # Agent Catalog 路由
│   │   ├── agent_files.py                   # Agent Files 路由
│   │   ├── orchestrator.py                  # Orchestrator 路由
│   │   ├── workflows.py                     # Workflows 路由
│   │   ├── reports.py                       # Reports 路由
│   │   ├── file_upload.py                   # 文件上傳路由
│   │   ├── file_metadata.py                 # 文件元數據路由
│   │   ├── chromadb.py                      # ChromaDB 路由
│   │   ├── llm.py                           # LLM 路由
│   │   ├── mcp.py                           # MCP 路由
│   │   └── ... (其他路由)
│   ├── middleware/                          # 中間件
│   │   ├── __init__.py
│   │   ├── request_id.py                    # Request ID 中間件
│   │   ├── logging.py                       # 日誌中間件
│   │   └── error_handler.py                 # 錯誤處理中間件
│   └── core/                                # API 核心功能
│       ├── __init__.py
│       ├── response.py                      # 統一響應格式
│       ├── settings.py                      # API 設置
│       └── version.py                       # 版本信息
│
├── storage/                                 # 文件存儲（基礎設施）
│   ├── __init__.py
│   ├── file_storage.py                      # 文件存儲抽象
│   └── models.py                            # 存儲數據模型
│
├── data/                                   # 數據目錄（運行時數據，不提交到 Git）
│   ├── datasets/                            # 數據集目錄
│   │   ├── files/                           # 用戶上傳的文件存儲目錄
│   │   │   └── [hash]/                     # 按文件 ID 前2個字符分組的文件
│   │   ├── autogen/                         # AutoGen 相關數據
│   │   │   └── checkpoints/                 # AutoGen 任務檢查點文件
│   │   ├── agent_files/                     # Agent 產出的文件（HTML/PDF等）
│   │   ├── arangodb/                        # ArangoDB 種子數據
│   │   │   ├── schema.yml                   # 數據庫架構定義
│   │   │   └── seed_data.json               # 初始數據
│   │   ├── crewai/                          # CrewAI 相關數據
│   │   │   └── agent_templates.yaml         # Agent 模板文件
│   │   └── chromadb/                        # ChromaDB 相關數據
│   └── chroma_data/                         # ChromaDB 數據目錄（運行時數據）
│       └── ...                              # ChromaDB 持久化模式的數據文件
│                                           # 包含: chroma.sqlite3, index/ 等
│
├── services/                               # 適配器目錄（向後兼容，保留）
│   ├── __init__.py
│   ├── agent_registry/                     # Agent Registry 適配器
│   │   └── __init__.py                    # 重新導出 agents.services.registry
│   ├── security/                           # Security 適配器
│   │   └── __init__.py                    # 重新導出 system.security
│   ├── file_server/                        # File Server 適配器
│   │   └── __init__.py                    # 重新導出 agents.services.file_service
│   ├── result_processor/                   # Result Processor 適配器
│   │   └── __init__.py                    # 重新導出 agents.services.processing
│   ├── mcp_server/                         # MCP Server 適配器
│   │   ├── __init__.py
│   │   └── tools/                          # MCP 工具配置
│   │       └── config.yaml                # MCP 工具配置文件
│   └── api/                                # API 適配器
│       ├── __init__.py
│       ├── routers/                        # 路由適配器（GenAI 路由）
│       │   ├── __init__.py
│       │   ├── aam_async_tasks.py         # 重新導出 genai.api.routers.aam_async_tasks
│       │   ├── chunk_processing.py         # 重新導出 genai.api.routers.chunk_processing
│       │   ├── kg_builder.py              # 重新導出 genai.api.routers.kg_builder
│       │   ├── kg_query.py                # 重新導出 genai.api.routers.kg_query
│       │   ├── ner.py                     # 重新導出 genai.api.routers.ner
│       │   ├── re.py                      # 重新導出 genai.api.routers.re
│       │   ├── rt.py                      # 重新導出 genai.api.routers.rt
│       │   └── triple_extraction.py       # 重新導出 genai.api.routers.triple_extraction
│       ├── middleware/                     # 中間件適配器
│       │   ├── __init__.py
│       │   ├── error_handler.py           # 重新導出 api.middleware.error_handler
│       │   ├── logging.py                 # 重新導出 api.middleware.logging
│       │   └── request_id.py              # 重新導出 api.middleware.request_id
│       └── core/                           # 核心適配器
│           ├── __init__.py
│           ├── response.py                # 重新導出 api.core.response
│           ├── settings.py                # 重新導出 api.core.settings
│           └── version.py                 # 重新導出 api.core.version
│
├── chroma_data/                            # ChromaDB 數據目錄（運行時數據，不提交到 Git）
│   └── ...                                 # ChromaDB 持久化模式的數據文件
│                                           # 包含: chroma.sqlite3, index/ 等
│
├── datasets/                               # 數據集目錄（運行時數據，部分不提交到 Git）
│   ├── files/                              # 用戶上傳的文件存儲目錄
│   │   └── [hash]/                        # 按文件 ID 前2個字符分組的文件
│   ├── autogen/                            # AutoGen 相關數據
│   │   └── checkpoints/                   # AutoGen 任務檢查點文件
│   ├── agent_files/                        # Agent 產出的文件（HTML/PDF等）
│   ├── arangodb/                           # ArangoDB 種子數據
│   │   ├── schema.yml                     # 數據庫架構定義
│   │   └── seed_data.json                 # 初始數據
│   ├── crewai/                             # CrewAI 相關數據
│   │   └── agent_templates.yaml           # Agent 模板文件
│   └── chromadb/                           # ChromaDB 相關數據
│

├── docs/                                    # 文檔
│   ├── architecture.md                      # 架構文檔
│   ├── api_reference.md                     # API 參考
│   ├── DIRECTORY_REFACTORING_PLAN.md        # 目錄重構計劃
│   ├── DIRECTORY_STRUCTURE.md               # 目錄結構（本文檔）
│   └── ...
│
├── tests/                                   # 測試（重構後重新組織）
│   ├── __init__.py
│   ├── genai/                               # GenAI 測試
│   │   ├── __init__.py
│   │   ├── test_ner.py
│   │   ├── test_re.py
│   │   └── ...
│   ├── mcp/                                 # MCP 測試
│   │   ├── __init__.py
│   │   ├── test_server.py
│   │   └── test_client.py
│   ├── database/                            # Database 測試
│   │   ├── __init__.py
│   │   ├── test_chromadb.py
│   │   └── test_arangodb.py
│   ├── llm/                                 # LLM 測試
│   │   ├── __init__.py
│   │   └── test_moe.py
│   ├── agents/                              # Agents 測試
│   │   ├── __init__.py
│   │   └── test_registry.py
│   ├── system/                              # System 測試
│   │   ├── __init__.py
│   │   └── test_security.py
│   └── api/                                 # API 測試
│       ├── __init__.py
│       └── test_routes.py
│
├── tests_backup/                            # 測試備份（遷移期間）
│   └── ... (現有測試代碼備份)
│
├── scripts/                                 # 腳本
│   ├── setup.sh                             # 設置腳本
│   └── ...
│
├── config/                                  # 配置文件
│   ├── config.example.json                  # 配置示例
│   └── config.json                          # 實際配置（不提交到 Git）
│
├── backup/                                  # 備份目錄
│   ├── refactoring/                         # 重構期間的舊代碼備份
│   └── ...
│
├── .gitignore                               # Git 忽略文件
├── .cursorignore                            # Cursor 忽略文件
├── pytest.ini                               # Pytest 配置
├── requirements.txt                         # Python 依賴
├── README.md                                # 項目說明
└── ...
```

---

## 📋 各組件詳細說明

### 1. genai/ - GenAI 相關組件

**職責**: 所有 GenAI 相關的功能，包括 LangChain、RAG、NER/RE/RT、Context Record

**結構說明**:

- `api/` - GenAI 相關的 FastAPI 路由、服務和模型
- `workflows/` - 工作流引擎（LangChain、RAG、Context）
- `prompt/` - Prompt 管理

**遷移來源**:

- `services/api/routers/ner.py` → `genai/api/routers/ner.py`
- `services/api/routers/re.py` → `genai/api/routers/re.py`
- `agent_process/context/` → `genai/workflows/context/`
- `agent_process/retrieval/` → `genai/workflows/rag/`

---

### 2. mcp/ - MCP Server 和 Client

**職責**: MCP 協議的服務器和客戶端實現

**結構說明**:

- `server/` - MCP Server 框架、協議定義、工具註冊
- `client/` - MCP Client 實現、連接管理

**遷移來源**:

- `mcp_server/` → `mcp/server/`
- `mcp_client/` → `mcp/client/`
- `services/mcp_server/` → 整合到 `mcp/server/`

---

### 3. database/ - Database 相關組件

**職責**: 所有數據庫服務的封裝

**結構說明**:

- `chromadb/` - ChromaDB 單一服務
- `arangodb/` - ArangoDB 單一服務
- `redis/` - Redis 服務（如需要）
- `personnel/` - Personnel Data 服務

**遷移來源**:

- `databases/chromadb/` → `database/chromadb/`
- `databases/arangodb/` → `database/arangodb/`

---

### 4. llm/ - LLM 模型層

**職責**: LLM 模型管理、路由、負載均衡

**結構說明**:

- `moe/` - MoE 管理器
- `abstraction/` - 模型抽象層
- `clients/` - 各種 LLM 客戶端實現
- `routing/` - LLM 路由策略

**遷移來源**:

- `llm/moe_manager.py` → `llm/moe/moe_manager.py`
- `llm/clients/` → `llm/clients/` (保持，更新導入)
- `llm/routing/` → `llm/routing/` (保持，更新導入)

---

### 5. agents/ - Agent 服務層

**職責**: Agent 的協調、註冊、執行

**結構說明**:

- `services/` - Agent 協調服務（註冊、協調、處理、文件服務）
- `core/` - 核心 Agent 實現（Planning、Execution、Review）
- `workflows/` - Agent 工作流引擎
- `task_analyzer/` - 任務分析

**遷移來源**:

- `services/agent_registry/` → `agents/services/registry/`
- `agents/orchestrator/` → `agents/services/orchestrator/`
- `agents/planning/` → `agents/core/planning/`

---

### 6. system/ - 系統管理

**職責**: 系統級功能（安全、配置、日誌、監控）

**結構說明**:

- `security/` - 安全服務
- `infra/` - 基礎設施（配置、日誌、監控）
- `n8n/` - n8n 工作流集成（未來）

**遷移來源**:

- `services/security/` → `system/security/`
- `core/config.py` → `system/infra/config/config.py`

---

### 7. api/ - API 界面層

**職責**: 對外 API 接口，整合所有服務

**結構說明**:

- `main.py` - FastAPI 主應用
- `routers/` - 所有 API 路由（引用各組件的路由）
- `middleware/` - 中間件
- `core/` - API 核心功能

**遷移來源**:

- `services/api/main.py` → `api/main.py`
- `services/api/routers/*` → `api/routers/*` (整合並引用新位置)
- `services/api/middleware/` → `api/middleware/`

---

## 🔄 遷移對應關係

### 主要遷移對應表

| 原路徑 | 新路徑 | 備註 |
|--------|--------|------|
| `databases/chromadb/` | `database/chromadb/` | 單一服務 |
| `databases/arangodb/` | `database/arangodb/` | 單一服務 |
| `llm/moe_manager.py` | `llm/moe/moe_manager.py` | 重組結構 |
| `mcp_server/` | `mcp/server/` | 重命名 |
| `mcp_client/` | `mcp/client/` | 重命名 |
| `services/api/routers/ner.py` | `genai/api/routers/ner.py` | 組件分離 |
| `services/agent_registry/` | `agents/services/registry/` | 組件分離 |
| `agents/planning/mcp_server.py` | `agents/core/planning/handlers.py` | 重命名 |
| `services/security/` | `system/security/` | 組件分離 |
| `services/api/main.py` | `api/main.py` | 統一入口 |

---

### 8. agents/infra/ - Agent 基礎設施

**職責**: Agent 的基礎設施組件（記憶管理、工具註冊表）

**結構說明**:

- `memory/` - 記憶管理器（MemoryManager）和 AAM（記憶增強模組）
- `tools/` - 工具註冊表（ToolRegistry）

**遷移來源**:

- `agent_process/memory/` → `agents/infra/memory/` (已整合)
- `agent_process/tools/` → `agents/infra/tools/` (已整合)

**整合狀態**:

- ✅ `agent_process/memory/` → `agents/infra/memory/` (已整合)
- ✅ `agent_process/tools/` → `agents/infra/tools/` (已整合)
- ✅ `agent_process/` 目錄已刪除

**其他遷移**:

- ✅ `agent_process/context/` → `genai/workflows/context/` (已遷移)
- ✅ `agent_process/retrieval/` → `genai/workflows/rag/` (已遷移)
- ✅ `agent_process/prompt/` → `genai/prompt/` (已遷移)

---

### 9. services/ - 適配器目錄

**職責**: 提供向後兼容的適配器，重新導出新位置的模組

**結構說明**:

- `agent_registry/` - 重新導出 `agents.services.registry`
- `security/` - 重新導出 `system.security`
- `file_server/` - 重新導出 `agents.services.file_service`
- `result_processor/` - 重新導出 `agents.services.processing`
- `mcp_server/` - 重新導出 `mcp.server`
- `api/` - 重新導出 `api` 和 `genai.api.routers`

**保留原因**:

- 確保舊代碼仍可使用 `services.*` 路徑
- 提供平滑的遷移過渡期
- 所有適配器文件只包含重新導出語句

**遷移狀態**:

- ✅ 所有實際文件已遷移到新位置
- ✅ 只保留適配器文件（`__init__.py`）
- ✅ 適配器確保向後兼容

---

### 10. data/ - 數據目錄

**職責**: 統一管理所有運行時數據目錄

**結構說明**:

- `datasets/` - 數據集目錄（用戶文件、檢查點、種子數據等）
- `chroma_data/` - ChromaDB 數據目錄（向量數據文件）

**特點**:

- 運行時數據（不提交到 Git）
- 統一管理所有數據目錄，便於維護和備份

**子目錄說明**:

#### data/datasets/ - 數據集目錄

**結構**:

- `files/` - 用戶上傳的文件存儲目錄（通過 API 上傳）
- `autogen/checkpoints/` - AutoGen 長時程任務的檢查點文件
- `agent_files/` - Agent 產出的文件（HTML/PDF 等）
- `arangodb/` - ArangoDB 種子數據（架構定義、初始數據）
- `crewai/` - CrewAI 相關數據（Agent 模板文件）
- `chromadb/` - ChromaDB 相關數據

**代碼位置**:

- `storage/file_storage.py` - 默認路徑: `./data/datasets/files`
- `agents/autogen/long_horizon.py` - 檢查點路徑: `./data/datasets/autogen/checkpoints`
- `agents/services/file_service/agent_file_service.py` - Agent 文件路徑: `./data/datasets/agent_files`

#### data/chroma_data/ - ChromaDB 數據目錄

**結構**:

- 運行時自動創建的數據目錄
- 包含 ChromaDB 的向量數據文件（`.sqlite3`、索引文件等）

**特點**:

- 運行時數據（不提交到 Git）
- 使用持久化模式時自動創建
- 默認路徑: `./data/chroma_data`（可在 `database/chromadb/client.py` 中配置）

**代碼位置**:

- `database/chromadb/client.py` - 定義 `persist_directory` 參數

**遷移來源**:

- `chroma_data/` → `data/chroma_data/` (已移動)
- `datasets/` → `data/datasets/` (已移動)

---

## 📊 目錄分類

### 核心代碼目錄（提交到 Git）

- `api/` - API 界面層
- `agents/` - Agent 服務層（包含 infra/ 基礎設施）
- `database/` - 數據庫模組
- `genai/` - GenAI 模組
- `llm/` - LLM 模組
- `mcp/` - MCP 模組
- `storage/` - 文件存儲
- `system/` - 系統管理
- `services/` - 適配器目錄（只包含適配器文件）

### 運行時數據目錄（不提交到 Git）

- `data/chroma_data/` - ChromaDB 數據文件
- `data/datasets/files/` - 用戶上傳的文件
- `data/datasets/autogen/checkpoints/` - AutoGen 檢查點
- `data/datasets/agent_files/` - Agent 產出文件

### 配置文件目錄（部分提交到 Git）

- `config/` - 配置文件（`config.json` 不提交）
- `datasets/arangodb/` - 數據庫種子數據（可以提交）
- `datasets/crewai/` - CrewAI 模板文件（可以提交）

### 其他目錄

- `docs/` - 文檔目錄
- `tests/` - 測試目錄
- `scripts/` - 腳本目錄
- `backup/` - 備份目錄（不提交）

---

## 🔄 遷移對應關係（更新）

### 主要遷移對應表

| 原路徑 | 新路徑 | 狀態 | 備註 |
|--------|--------|------|------|
| `databases/chromadb/` | `database/chromadb/` | ✅ 已遷移 | 單一服務 |
| `databases/arangodb/` | `database/arangodb/` | ✅ 已遷移 | 單一服務 |
| `llm/moe_manager.py` | `llm/moe/moe_manager.py` | ✅ 已遷移 | 重組結構 |
| `mcp_server/` | `mcp/server/` | ✅ 已遷移 | 重命名 |
| `mcp_client/` | `mcp/client/` | ✅ 已遷移 | 重命名 |
| `services/api/routers/ner.py` | `genai/api/routers/ner.py` | ✅ 已遷移 | 組件分離 |
| `services/agent_registry/` | `agents/services/registry/` | ✅ 已遷移 | 組件分離 |
| `agents/planning/mcp_server.py` | `agents/core/planning/handlers.py` | ✅ 已遷移 | 重命名 |
| `services/security/` | `system/security/` | ✅ 已遷移 | 組件分離 |
| `services/api/main.py` | `api/main.py` | ✅ 已遷移 | 統一入口 |
| `agent_process/context/` | `genai/workflows/context/` | ✅ 已遷移 | 保留適配器 |
| `agent_process/retrieval/` | `genai/workflows/rag/` | ✅ 已遷移 | 保留適配器 |
| `agent_process/prompt/` | `genai/prompt/` | ✅ 已遷移 | 保留適配器 |
| `agent_process/memory/` | `agents/infra/memory/` | ✅ 已整合 | 整合到 agents/infra/ |
| `agent_process/tools/` | `agents/infra/tools/` | ✅ 已整合 | 整合到 agents/infra/ |
| `chroma_data/` | `data/chroma_data/` | ✅ 已移動 | 統一數據目錄 |
| `datasets/` | `data/datasets/` | ✅ 已移動 | 統一數據目錄 |

---

## 📝 注意事項（更新）

1. **導入路徑更新**: 所有遷移都需要更新導入路徑
2. **依賴關係**: 注意模組間的依賴關係，按順序遷移
3. **測試覆蓋**: 每個模組遷移後都需要進行測試
4. **文檔同步**: 更新相關文檔中的路徑引用
5. **適配器保留**: 適配器確保向後兼容，舊代碼仍可使用原路徑
6. **運行時數據**: `data/chroma_data/` 和 `data/datasets/files/` 等運行時數據目錄不提交到 Git
7. **基礎設施整合**: `agent_process/memory/` 和 `agent_process/tools/` 已整合到 `agents/infra/` 下
8. **數據目錄統一**: 所有運行時數據目錄統一放在 `data/` 下，便於管理

---

**最後更新**: 2025-11-30
**維護者**: Daniel Chung

---

## 📝 注意事項（更新）

1. **導入路徑更新**: 所有遷移都需要更新導入路徑
2. **依賴關係**: 注意模組間的依賴關係，按順序遷移
3. **測試覆蓋**: 每個模組遷移後都需要進行測試
4. **文檔同步**: 更新相關文檔中的路徑引用
5. **適配器保留**: 適配器確保向後兼容，舊代碼仍可使用原路徑
6. **運行時數據**: `data/chroma_data/` 和 `data/datasets/files/` 等運行時數據目錄不提交到 Git
7. **基礎設施整合**: `agent_process/memory/` 和 `agent_process/tools/` 已整合到 `agents/infra/` 下
8. **數據目錄統一**: 所有運行時數據目錄統一放在 `data/` 下，便於管理

---

**最後更新**: 2025-11-30
**維護者**: Daniel Chung
