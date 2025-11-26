# AI-Box

Agent AI Box 系統 - 基於 GenAI 的智能代理系統

**版本**: 0.1.0
**創建日期**: 2025-10-25
**創建人**: Daniel Chung
**最後修改日期**: 2025-11-25 22:58 (UTC+8)

---

## 項目簡介

AI-Box 是一個基於 GenAI 的智能代理系統，整合了多種 AI 技術棧，實現從用戶請求到任務執行的端到端智能處理流程。

## 快速開始

### 前置要求

- Python 3.11+
- Node.js 18+
- Docker Desktop
- Git 2.40+

### 環境設置

1. 克隆倉庫

   ```bash
   git clone https://github.com/[username]/AI-Box.git
   cd AI-Box
   ```
2. 設置開發環境

   ```bash
   ./scripts/setup_dev_env.sh
   ```
3. 驗證環境

   ```bash
   ./scripts/verify_env.sh
   ```
4. 激活虛擬環境

   ```bash
   source venv/bin/activate
   ```
5. 建立配置檔

   ```bash
   cp config/config.example.json config/config.json
   # 編輯 config/config.json（非敏感參數）
   # 敏感資訊放在 .env 或 Kubernetes Secret
   ```

## 項目結構

```
AI-Box/
├── docs/                    # 文檔目錄
│   ├── plans/              # 計劃文檔
│   └── progress/           # 進度報告
├── services/                # 服務目錄
│   ├── api/                # FastAPI 服務
│   └── mcp-server/         # MCP Server 服務
├── mcp_server/             # MCP Server 核心實現
├── mcp_client/             # MCP Client 實現
├── agents/                  # Agent 實現
├── databases/              # 資料庫封裝
│   ├── chromadb/          # ChromaDB SDK 封裝
│   └── arangodb/          # ArangoDB SDK 封裝
├── scripts/                 # 腳本目錄
│   ├── setup_dev_env.sh    # 環境設置腳本
│   ├── verify_env.sh       # 環境驗證腳本
│   ├── test_mcp.sh         # MCP 測試腳本
│   ├── test_mcp.py         # MCP 測試腳本（Python）
│   └── performance/        # 性能測試腳本
│       └── chromadb_benchmark.py  # ChromaDB 性能測試
├── datasets/               # 數據存儲（Chromadb、ArangoDB、其他資料集）
│   ├── chromadb/
│   └── arangodb/
├── tests/                   # 測試目錄
│   ├── mcp/                # MCP 測試
│   └── api/                # API 測試
└── README.md               # 本文件
```

## 核心組件

### FastAPI 服務 (services/api)

統一的 API 入口，提供 Agent 管理、任務分析、協調等功能。

### MCP Server/Client

Model Context Protocol (MCP) 實現，提供統一的工具調用接口。

- **MCP Server**: 工具服務器，支持工具註冊和調用
- **MCP Client**: 客戶端實現，支持連線池、負載均衡、自動重連

詳細文檔請參考：

- [MCP Server 文檔](services/mcp-server/README.md)
- [WBS 1.2 計劃](docs/plans/phase1/wbs-1.2-mcp-platform.md)

### ChromaDB 向量資料庫

ChromaDB 作為 RAG 的核心向量存儲，提供高效的向量檢索功能。

- **SDK 封裝**: 連線池管理、錯誤處理、批量操作優化
- **API 路由**: 完整的 RESTful API 接口
- **性能優化**: 批量寫入、索引調整、性能測試工具

**快速使用**:

```python
from databases.chromadb import ChromaDBClient, ChromaCollection

# 初始化客戶端
client = ChromaDBClient(mode="persistent", persist_directory="./chroma_data")

# 創建或獲取集合
collection_obj = client.get_or_create_collection("my_collection")
collection = ChromaCollection(collection_obj, expected_embedding_dim=384)

# 添加文檔
collection.add(
    ids="doc1",
    embeddings=[[0.1, 0.2, ...]],  # 384 維向量
    documents="This is a test document",
    metadatas={"source": "test"}
)

# 向量檢索
results = collection.query(
    query_embeddings=[[0.1, 0.2, ...]],
    n_results=10
)
```

詳細文檔請參考：

- [ChromaDB SDK 文檔](databases/chromadb/README.md)
- [性能優化指南](docs/performance/chromadb-optimization.md)
- [部署指南](docs/deployment/chromadb-deployment.md)

### ArangoDB 圖資料庫

ArangoDB 為知識圖譜與圖查詢提供多模型存儲能力。

- **部署**：`docker-compose.yml` 內建單節點服務，Kubernetes 透過 `k8s/base/arangodb-*.yaml` StatefulSet。
- **初始化腳本**：`infra/arangodb/bootstrap.sh`（建立資料庫 / 集合 / 使用者）、`infra/arangodb/healthcheck.sh`（版本與角色檢查）。
- **備援**：支援 Active Failover，依 `docs/deployment/arangodb-deployment.md` 調整 `replicas` 與 PVC。
- **Schema 與資料**：`docs/datasets/arangodb-kg-schema.md`、`datasets/arangodb/schema.yml`、`datasets/arangodb/seed_data.json`。
- **資料匯入/查詢**：`scripts/arangodb_seed.py --reset`、`scripts/arangodb_query_demo.py --vertex entities/agent_planning --limit 5`。

```bash
# 初始化與健檢
./infra/arangodb/bootstrap.sh
./infra/arangodb/healthcheck.sh
```

```python
from databases.arangodb import ArangoDBClient
from databases.arangodb import queries as kg_queries

client = ArangoDBClient()
neighbors = kg_queries.fetch_neighbors(client, "entities/agent_planning")
subgraph = kg_queries.fetch_subgraph(client, "entities/agent_planning", max_depth=2)
client.close()
```

詳細文檔請參考：

- [ArangoDB SDK 文檔](databases/arangodb/README.md)
- [ArangoDB 部署指南](docs/deployment/arangodb-deployment.md)
- [知識圖譜 Schema](docs/datasets/arangodb-kg-schema.md)
- [配置樣板](config/config.example.json)

### 啟動服務

#### 啟動 FastAPI 服務

```bash
python -m services.api.main
# 或使用 docker-compose
docker-compose up api
```

#### 啟動 MCP Server

```bash
python -m services.mcp_server.main
# 或使用 docker-compose
docker-compose up mcp-server
```

#### 啟動 ChromaDB

```bash
# 使用 docker-compose
docker-compose up chromadb

# 或直接使用 ChromaDB SDK（持久化模式）
from databases.chromadb import ChromaDBClient
client = ChromaDBClient(mode="persistent")
```

#### 使用 Docker Compose 啟動所有服務

```bash
docker-compose up
```

### 測試

#### 測試 MCP Server/Client

```bash
# 使用 Shell 腳本
./scripts/test_mcp.sh

# 使用 Python 腳本（更詳細）
python scripts/test_mcp.py
```

#### 運行單元測試

```bash
pytest tests/

# 運行 ChromaDB 測試
pytest databases/chromadb/tests/
pytest tests/api/test_chromadb_api.py
```

#### 性能測試

```bash
# ChromaDB 性能測試
python scripts/performance/chromadb_benchmark.py \
    --num-docs 1000 \
    --num-queries 100 \
    --target-latency 200 \
    --output benchmark_report.json
```

## 開發規範

請參考 `.cursor/rules/develop-rule.mdc` 了解開發規範。

## 貢獻指南

請參考 `CONTRIBUTING.md` 了解如何貢獻代碼。

## 許可證

[待定]

## 聯繫方式

- **項目負責人**: Daniel Chung
- **郵箱**: daniel@ifoxconn.com

---

**最後更新**: 2025-10-25
