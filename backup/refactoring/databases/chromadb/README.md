# ChromaDB SDK 封裝

**創建日期**: 2025-10-25
**創建人**: Daniel Chung
**最後修改日期**: 2025-11-25 21:25 (UTC+8)

---

## 概述

本模組提供 ChromaDB 向量資料庫的 Python SDK 封裝，簡化向量存儲和檢索操作。

## 功能特性

- 連接管理（HTTP 模式和持久化模式）
- 集合管理（創建、刪除、列出）
- CRUD 操作（添加、獲取、更新、刪除文檔）
- 向量檢索（相似度搜索）
- 批量操作支持
- 元數據過濾

## 安裝依賴

```bash
pip install chromadb
```

## 使用方法

### 1. 初始化客戶端

```python
from databases.chromadb import ChromaDBClient

# HTTP 模式（連接到 Docker 容器）
client = ChromaDBClient(
    host="localhost",
    port=8001,
    mode="http"
)

# 持久化模式（本地存儲）
client = ChromaDBClient(
    persist_directory="./chroma_data",
    mode="persistent"
)
```

### 2. 創建或獲取集合

```python
from databases.chromadb import ChromaCollection

collection = client.get_or_create_collection(
    name="my_collection",
    metadata={"description": "My first collection"}
)
chroma_collection = ChromaCollection(collection)
```

### 3. 添加文檔

```python
# 添加單個文檔（使用嵌入函數自動生成向量）
chroma_collection.add(
    ids="doc1",
    documents="This is a sample document",
    metadatas={"source": "test", "type": "example"}
)

# 添加多個文檔
chroma_collection.add(
    ids=["doc2", "doc3"],
    documents=["Document 2", "Document 3"],
    metadatas=[
        {"source": "test", "type": "example"},
        {"source": "test", "type": "example"}
    ]
)

# 添加預先計算的向量
chroma_collection.add(
    ids="doc4",
    embeddings=[[0.1, 0.2, 0.3, ...]],
    documents="Document with pre-computed embedding",
    metadatas={"source": "test"}
)
```

### 4. 查詢相似文檔

```python
# 使用文本查詢（自動生成向量）
results = chroma_collection.query(
    query_texts="sample query",
    n_results=5
)

# 使用預先計算的向量查詢
results = chroma_collection.query(
    query_embeddings=[[0.1, 0.2, 0.3, ...]],
    n_results=5
)

# 帶元數據過濾的查詢
results = chroma_collection.query(
    query_texts="sample query",
    n_results=5,
    where={"source": "test"}
)
```

### 5. 獲取文檔

```python
# 根據 ID 獲取
documents = chroma_collection.get(ids=["doc1", "doc2"])

# 根據條件獲取
documents = chroma_collection.get(
    where={"source": "test"},
    limit=10
)
```

### 6. 更新文檔

```python
chroma_collection.update(
    ids="doc1",
    documents="Updated document text",
    metadatas={"source": "updated"}
)
```

### 7. 刪除文檔

```python
# 根據 ID 刪除
chroma_collection.delete(ids=["doc1", "doc2"])

# 根據條件刪除
chroma_collection.delete(where={"source": "test"})
```

## 環境變數

- `CHROMADB_HOST`: ChromaDB 服務器地址（默認: localhost）
- `CHROMADB_PORT`: ChromaDB 服務器端口（默認: 8001）
- `CHROMADB_PERSIST_DIR`: 持久化目錄（持久化模式，默認: ./chroma_data）

## Docker 部署

ChromaDB 已配置在 `docker-compose.yml` 中：

```yaml
chromadb:
  image: chromadb/chroma:latest
  ports:
    - "8001:8000"
  environment:
    - IS_PERSISTENT=TRUE
    - PERSIST_DIRECTORY=/chroma/chroma
```

啟動服務：

```bash
docker-compose up -d chromadb
```

## Kubernetes 部署

> 參考檔案：`k8s/base/chromadb-*.yaml`、`k8s/monitoring/chromadb-*.yaml`

1. **建立命名空間與基礎資源**
   ```bash
   kubectl apply -f k8s/base/namespaces.yaml
   kubectl apply -f k8s/base/chromadb-configmap.yaml
   kubectl apply -f k8s/base/chromadb-pvc.yaml
   ```
2. **部署服務**
   ```bash
   kubectl apply -f k8s/base/chromadb-deployment.yaml
   kubectl apply -f k8s/base/service.yaml   # 內含 chromadb-service
   ```
3. **啟用監控**
   ```bash
   kubectl apply -f k8s/monitoring/prometheus-config.yaml
   kubectl apply -f k8s/monitoring/chromadb-metrics.yaml
   kubectl apply -f k8s/monitoring/chromadb-dashboard.yaml
   ```
4. **驗證**
   ```bash
   kubectl -n ai-box get pods -l app=chromadb
   kubectl -n ai-box-monitoring get servicemonitors chromadb
   ```

## 測試

```python
# 健康檢查
status = client.heartbeat()
print(status)  # {'status': 'healthy'}

# 查看集合信息
collections = client.list_collections()
print(collections)  # ['my_collection', ...]

# 查看集合統計
count = chroma_collection.count()
print(f"Collection contains {count} documents")
```

## 注意事項

1. HTTP 模式需要 ChromaDB 服務器運行
2. 持久化模式會在本地創建數據目錄
3. 集合名稱必須唯一
4. 文檔 ID 在集合內必須唯一
5. 使用文本查詢時需要集合配置了嵌入函數

---

**最後更新**: 2025-10-25
