# MasterRAG 文檔

## 概述

MasterRAG 是 AI-Box 系統中的主檔語意檢索組件，負責將 ERP 主檔資料（料號、倉庫，工作站）向量化後存入 Qdrant 向量資料庫，實現語意化的實體驗證和搜索功能。

## 架構

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Master Data   │────▶│  qwen3-embed    │────▶│    Qdrant      │
│ (JSON 檔案)     │     │  (生成向量)      │     │  (向量儲存)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ EntityExtractor │────▶│ MMMasterRAGClient│◀────│  語意搜索      │
│ (實體提取)      │     │  (檢索客戶端)    │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 資料來源

| 類型 | 來源檔案 | 數量 |
|------|----------|------|
| 料號 | `metadata/systems/tiptop_jp/item_master.json` | 91,228 筆 |
| 倉庫 | `metadata/systems/tiptop_jp/warehouse_master.json` | 307 筆 |
| 工作站 | `metadata/systems/tiptop_jp/workstation_master.json` | 122 筆 |

## 配置參數

| 參數 | 值 | 說明 |
|------|-----|------|
| COLLECTION_NAME | `mmMasterRAG` | Qdrant collection 名稱 |
| VECTOR_SIZE | `4096` | qwen3-embedding 向量維度 |
| DISTANCE | `COSINE` | 向量距離計算方式 |
| EMBEDDING_MODEL | `qwen3-embedding:latest` | 向量化模型 |

## API 接口

### MMMasterRAGClient

位置：`database/qdrant/mm_master_rag_client.py`

#### 方法

##### search(query_vector, query_type, limit, score_threshold)
語意搜尋

```python
from database.qdrant.mm_master_rag_client import get_mm_master_rag_client

client = get_mm_master_rag_client()

# 搜尋料號
results = client.search_items(
    query_vector=embedding,
    limit=10
)

# 搜尋倉庫
results = client.search_warehouses(
    query_vector=embedding,
    limit=10
)

# 搜尋工作站
results = client.search_workstations(
    query_vector=embedding,
    limit=10
)
```

##### hybrid_search(text, embedding_model, limit)
混合搜尋（關鍵詞 + 語意）

```python
results = client.hybrid_search(
    text="W0001 倉庫",
    embedding_model=embedding_model,
    limit=10
)
```

### REST API

| Method | Endpoint | 功能 |
|--------|----------|------|
| POST | `/api/v1/mm-master/rag/search` | 語意搜尋 |
| POST | `/api/v1/mm-master/rag/semantic-search` | 混合檢索 |
| GET | `/api/v1/mm-master/rag/stats` | 取得統計資訊 |

## 使用場景

### 1. 實體驗證

在 Entity Extraction 過程中，使用 MasterRAG 驗證提取的實體是否存在于主檔：

```python
from data_agent.services.schema_driven_query.entity_extractor import EntityExtractor

extractor = EntityExtractor()

# 驗證料號
result = extractor.validate_with_master_rag("A01396000", "ITEM_NO")
# result.status: VALID / INVALID / NOT_FOUND
```

### 2. 相似實體推薦

當用戶輸入的實體不存在時，推薦相似的實體：

```python
result = extractor.validate_with_master_rag("A99999999", "ITEM_NO")
# 如果 NOT_FOUND，suggestions 中會包含推薦的料號
```

## 重建向量索引

當主檔資料更新時，使用 `sync_mmMaster.py` 腳本進行同步：

```bash
# 進入虛擬環境
cd /home/daniel/ai-box/datalake-system
source venv/bin/activate

# 同步到 Qdrant (使用 qwen3-embedding)
python data_agent/RAG/sync/sync_mmMaster.py --qdrant --recreate

# 同步到 ArangoDB
python data_agent/RAG/sync/sync_mmMaster.py --arangodb

# 全部同步
python data_agent/RAG/sync/sync_mmMaster.py --full
```

### 參數說明

| 參數 | 說明 |
|------|------|
| `--qdrant` | 只同步到 Qdrant |
| `--arangodb` | 只同步到 ArangoDB |
| `--recreate` | 重新建立 Collection（刪除現有） |
| `--full` | 全部同步 |
| `--embedding-model` | 指定 embedding 模型（可選，預設使用 qwen3-embedding） |

## 已知限制

1. **向量維度**：目前使用 qwen3-embedding (4096維)，與其他系統可能存在兼容性問題
2. **數據量**：目前僅入庫 500 筆料號作為測試，完整入庫需要處理大量數據
3. **更新機制**：目前為全量重建，未來需要增量更新機制

## 更新日誌

| 日期 | 內容 |
|------|------|
| 2026-02-24 | 重建 Collection，使用 qwen3-embedding (4096維)；更新 sync_mmMaster.py 使用 qwen3-embedding API |
| 2026-02-10 | 初始版本，使用 nomic-embed-text (384維) |
