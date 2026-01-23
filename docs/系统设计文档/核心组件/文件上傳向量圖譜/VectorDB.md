# VectorDB 向量數據庫架構文檔

## 文檔信息

- **版本**: 1.0
- **創建日期**: 2026-01-20
- **創建人**: Daniel Chung
- **最後修改日期**: 2026-01-20

---

## 目錄

1. [概述](#概述)
2. [架構總覽](#架構總覽)
3. [Qdrant 配置](#qdrant-配置)
4. [核心服務](#核心服務)
5. [代碼調用關係](#代碼調用關係)
6. [數據結構](#數據結構)
7. [API 接口](#api-接口)
8. [遷移歷史](#遷移歷史)
9. [已知問題](#已知問題)

---

## 概述

AI-Box 系統使用 **Qdrant** 作為向量數據庫（VectorDB），用於存儲和檢索文檔的向量化表示。Qdrant 取代了原有的 ChromaDB，提供了更好的性能、可擴展性和管理界面。

### 主要功能

- 文檔向量的存儲和檢索
- 基於文件 ID 的向量隔離
- 語義搜索和相似度匹配
- 權限過濾（ACL）
- 批量操作支持

---

## 架構總覽

### 系統架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI-Box 系統                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ File Upload │  │  RAG 檢索  │  │  Agent Capability      │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                      │               │
│         ▼                ▼                      ▼               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │           QdrantVectorStoreService                      │  │
│  │  (services/api/services/qdrant_vector_store_service.py)│  │
│  └────────────────────────┬────────────────────────────────┘  │
│                           │                                    │
│                           ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    Qdrant Client                        │  │
│  │                   (qdrant-client)                       │  │
│  └────────────────────────┬────────────────────────────────┘  │
│                           │                                    │
│         ┌─────────────────┼─────────────────┐                  │
│         ▼                 ▼                 ▼                  │
│  ┌────────────┐   ┌────────────┐   ┌──────────────────┐      │
│  │ REST API   │   │ gRPC API   │   │   Dashboard      │      │
│  │ :6333      │   │ :6334      │   │   :6333/dashboard│      │
│  └────────────┘   └────────────┘   └──────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### 與其他組件的關係

```
文件上傳流程
  │
  ├───► 文件解析 ──► ChunkProcessor ──► 分塊
  │                                         │
  │                                         ▼
  │                              EmbeddingService ──► 生成向量
  │                                         │
  │                                         ▼
  └────────────────────────────────► QdrantVectorStoreService ──► 存儲到 Qdrant
                                                                           │
                                                                           ▼
RAG 檢索流程                                                    ArangoDB
  │                                                            (元數據)
  ├───► Query Embedding ──► QdrantVectorStoreService.query_vectors()
  │                                         │
  │                                         ▼
  │                              返回相似向量 ──► 格式化結果
  │
  ▼
知識圖譜整合
```

---

## Qdrant 配置

### Docker 部署

**啟動命令**：

```bash
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v /Users/daniel/GitHub/AI-Box/data/qdrant:/qdrant/storage \
  qdrant/qdrant:latest
```

**端口說明**：

| 端口 | 協議 | 用途 |
|------|------|------|
| 6333 | REST API | 主要 API 接口 |
| 6334 | gRPC | 高性能 gRPC 接口 |
| 6333/dashboard | Web UI | 管理界面 |

### 配置文件

**位置**: `config/config.json`

```json
{
  "datastores": {
    "qdrant": {
      "host": "127.0.0.1",
      "port": 6333,
      "grpc_port": 6334,
      "protocol": "http",
      "mode": "local",
      "data_path": "./data/qdrant",
      "api_key": null,
      "timeout": 30,
      "hnsw": {
        "m": 16,
        "ef_construct": 100,
        "full_scan_threshold": 10000
      },
      "optimizers": {
        "default_segment_number": 2,
        "max_optimization_threads": 1
      }
    }
  }
}
```

**環境變數**：

| 環境變數 | 說明 | 默認值 |
|----------|------|--------|
| `QDRANT_HOST` | Qdrant 主機地址 | localhost |
| `QDRANT_PORT` | REST API 端口 | 6333 |
| `QDRANT_GRPC_PORT` | gRPC 端口 | 6334 |
| `QDRANT_API_KEY` | API 密鑰（可選） | null |

### Docker Compose

**位置**: `docker-compose.qdrant.yml`

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - "6333:6333"  # REST API
      - "6334:6334"  # gRPC API
    environment:
      - QDRANT__SERVICE__API_TOKEN_ENABLED=false
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  qdrant_data:
    driver: local
```

---

## 核心服務

### QdrantVectorStoreService

**文件**: `services/api/services/qdrant_vector_store_service.py`

#### 主要方法

| 方法 | 功能 | 返回類型 |
|------|------|----------|
| `store_vectors()` | 存儲向量 | `bool` |
| `query_vectors()` | 查詢相似向量 | `List[Dict]` |
| `query_vectors_with_acl()` | 帶權限查詢 | `List[Dict]` |
| `delete_vectors_by_file_id()` | 刪除文件向量 | `bool` |
| `get_vectors_by_file_id()` | 獲取文件向量 | `List[Dict]` |
| `get_collection_stats()` | 獲取統計信息 | `Dict` |

#### 使用示例

```python
from services.api.services.qdrant_vector_store_service import get_qdrant_vector_store_service

# 獲取服務實例
service = get_qdrant_vector_store_service()

# 存儲向量
success = service.store_vectors(
    file_id="cc3d7aee-b5b3-4e11-9458-784575c1dba6",
    chunks=[chunk1, chunk2, ...],
    embeddings=[[0.1, 0.2, ...], ...],
    user_id="user123"
)

# 查詢向量
results = service.query_vectors(
    query_embedding=[0.1, 0.2, ...],
    file_id="cc3d7aee-b5b3-4e11-9458-784575c1dba6",
    limit=5,
    score_threshold=0.7
)

# 獲取統計信息
stats = service.get_collection_stats(file_id)
```

#### Collection 命名策略

系統支持兩種 Collection 命名策略：

| 策略 | 格式 | 說明 |
|------|------|------|
| file_based | `file_{file_id}` | 每個文件一個 Collection |
| user_based | `user_{user_id}` | 每個用戶一個 Collection |

**默認配置**: `file_based`（每個文件一個 Collection）

### 單例模式

```python
# 獲取服務實例
def get_qdrant_vector_store_service() -> QdrantVectorStoreService:
    """獲取 QdrantVectorStoreService 實例（單例模式）"""
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = QdrantVectorStoreService()
    return _vector_store_service

# 重置服務實例（用於測試）
def reset_qdrant_vector_store_service() -> None:
    """重置 QdrantVectorStoreService 實例"""
    global _vector_store_service
    _vector_store_service = None
```

---

## 代碼調用關係

### 調用方總覽

```
QdrantVectorStoreService 被以下模組調用：

api/routers/file_upload.py
    │
    ├── store_vectors()       ← 存儲文件向量
    ├── query_vectors()       ← 查詢相似向量
    └── get_collection_stats() ← 獲取統計信息

api/routers/file_management.py
    │
    ├── delete_vectors_by_file_id() ← 刪除文件向量
    └── get_vectors_by_file_id()   ← 獲取文件向量

api/routers/user_tasks.py
    │
    └── delete_vectors_by_file_id() ← 刪除任務相關向量

agents/task_analyzer/rag_service.py
    │
    ├── _ensure_collection()  ← 確保 Collection 存在
    ├── store_capability()    ← 存儲 Capability 向量
    ├── retrieve_capabilities() ← 檢索 Capability
    ├── store_policy_chunk()  ← 存儲 Policy 向量
    └── retrieve_policies()   ← 檢索 Policy
```

### 詳細調用關係

#### 1. 文件上傳流程

**文件**: `api/routers/file_upload.py`

```python
# 行 907: 存儲向量
vector_store_service = get_qdrant_vector_store_service()
vector_store_service.store_vectors(
    file_id=file_id,
    chunks=chunks,
    embeddings=embeddings,
    user_id=user_id,
)

# 行 915: 獲取統計信息
stats = vector_store_service.get_collection_stats(file_id, user_id)
```

#### 2. 文件刪除流程

**文件**: `api/routers/file_management.py`

```python
# 行 1572: 刪除文件向量
vector_store_service = get_qdrant_vector_store_service()
vector_store_service.delete_vectors_by_file_id(
    file_id=file_id,
    user_id=user_id,
)
```

#### 3. 文件查詢流程

**文件**: `api/routers/file_management.py`

```python
# 行 2776: 獲取文件向量
vector_store_service = get_qdrant_vector_store_service()
all_vectors = vector_store_service.get_vectors_by_file_id(
    file_id=file_id,
    user_id=user_id,
)
```

#### 4. RAG 服務

**文件**: `agents/task_analyzer/rag_service.py`

```python
# 存儲 Capability 向量
self._qdrant_client.upsert(
    collection_name=self._rag2_collection_name,
    points=[PointStruct(...)],
)

# 檢索 Capability
results = self._qdrant_client.query_points(
    collection_name=self._rag2_collection_name,
    query=query_embedding,
    limit=top_k * 2,
    query_filter=filter_model,
    with_payload=True,
).points
```

### 依賴關係

```
qdrant-client
├── services/api/services/qdrant_vector_store_service.py
├── agents/task_analyzer/rag_service.py
└── config/config.json

chromadb（已廢棄，僅保留向後兼容）
├── services/api/services/vector_store_service.py（已標記廢棄）
├── api/routers/chromadb.py（已標記廢棄）
└── genai/workflows/rag/manager.py（已標記廢棄）
```

---

## 數據結構

### 向量存儲格式

```python
{
    "id": "chunk_0",                           # 向量 ID
    "vector": [0.1, 0.2, ..., 0.768],         # 768 維向量
    "payload": {
        "file_id": "cc3d7aee-b5b3-4e11-9458-784575c1dba6",
        "chunk_index": 0,
        "chunk_text": "文檔內容...",
        "start_position": 0,
        "end_position": 500,
        "chunk_size": 500,
        "strategy": "semantic",
        "encoding": "utf-8",
        "line_count": 10,
        "char_count": 10415,
        "sections": [...],  # 文件結構
        "headers": [...],   # 標題層次
        "has_code_blocks": True,
        "quality": "{\"size\": 500, ...}",
        "task_id": "systemAdmin_SystemDocs",
        "user_id": "unauthenticated"
    }
}
```

### Collection 配置

```python
VectorParams(
    size=768,              # 向量維度
    distance=Distance.COSINE,  # 距離度量
    on_disk=True,          # 存儲在磁盤
)
```

### 查詢結果格式

```python
{
    "id": "chunk_3",
    "score": 0.0098,
    "payload": {
        "file_id": "...",
        "chunk_index": 3,
        "chunk_text": "...",
        # ... 其他元數據
    }
}
```

---

## API 接口

### Qdrant REST API

| 端點 | 方法 | 功能 |
|------|------|------|
| `/collections` | GET | 列出所有 Collections |
| `/collections/{name}` | GET | 獲取 Collection 信息 |
| `/collections/{name}/points` | POST |  upsert 點 |
| `/collections/{name}/points/search` | POST | 搜索點 |
| `/collections/{name}/points/{id}` | DELETE | 刪除點 |
| `/collections/{name}/points/delete` | POST | 批量刪除 |
| `/health` | GET | 健康檢查 |

### 健康檢查

```bash
curl http://localhost:6333/health
```

### 列出所有 Collections

```bash
curl http://localhost:6333/collections
```

### 搜索向量

```bash
curl -X POST http://localhost:6333/collections/file_{file_id}/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": [0.1, 0.2, ...],
    "limit": 5,
    "score_threshold": 0.7
  }'
```

### Dashboard

訪問 `http://localhost:6333/dashboard` 查看 Qdrant Web UI。

---

## 遷移歷史

### ChromaDB → Qdrant 遷移

| 日期 | 版本 | 變更 |
|------|------|------|
| 2025-12-06 | v1.0 | 初始版本，使用 ChromaDB |
| 2026-01-20 | v2.0 | 遷移到 Qdrant |

### 遷移內容

1. **新建文件**:
   - `services/api/services/qdrant_vector_store_service.py`
   - `docker-compose.qdrant.yml`
   - `docs/.../CHROMADB_TO_QDRANT_MIGRATION.md`

2. **修改文件**:
   - `config/config.json` - 添加 `datastores.qdrant` 配置
   - `api/routers/file_upload.py` - 改用 Qdrant
   - `api/routers/file_management.py` - 改用 Qdrant
   - `api/routers/user_tasks.py` - 改用 Qdrant
   - `agents/task_analyzer/rag_service.py` - 改用 Qdrant
   - `scripts/start_services.sh` - 添加 Qdrant 啟動

3. **標記廢棄**:
   - `services/api/services/vector_store_service.py`
   - `api/routers/chromadb.py`
   - `genai/workflows/rag/manager.py`

### 回滾計畫

如需回滾到 ChromaDB，請參考：

- `docs/系统设计文档/核心组件/文件上傳向量圖譜/ROLLBACK_PLAN.md`

---

## 已知問題

### 1. Gemini 模型版本問題

**問題**: `gemini-pro` 已棄用，需要更新為新模型

**狀態**: ⚠️ 已知方案**: 問題
**解決優先使用本地 Ollama 模型

### 2. 依賴版本

| 依賴 | 版本 | 說明 |
|------|------|------|
| `qdrant-client` | 1.16.2+ | 向量數據庫客戶端 |
| `chromadb` | 最新 | 已廢棄，保留向後兼容 |

### 3. Collection 命名衝突

**問題**: 不同的文件可能使用相同的 Collection 名稱

**解決方案**: 使用 `file_{file_id}` 格式確保唯一性

---

## 相關文檔

- [上傳的功能架構說明-v4.0.md](./上傳的功能架構說明-v4.0.md)
- [CHROMADB_TO_QDRANT_MIGRATION.md](./CHROMADB_TO_QDRANT_MIGRATION.md)
- [ROLLBACK_PLAN.md](./ROLLBACK_PLAN.md)
- [Qdrant 官方文檔](https://qdrant.tech/documentation/)
