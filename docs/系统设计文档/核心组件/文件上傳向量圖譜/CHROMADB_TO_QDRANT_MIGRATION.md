# CHROMADB_TO_QDRANT_MIGRATION.md

**創建日期**: 2026-01-20
**創建人**: Daniel Chung
**版本**: 1.0

---

## 概述

本文檔記錄從 ChromaDB 遷移到 Qdrant 向量數據庫的架構變更。

---

## 變更原因

### ChromaDB 持久化模式的問題

| 問題 | 說明 | 影響 |
|------|------|------|
| 目錄碎片化 | 每個文件創建一個 UUID 目錄 | 1000 個文件 = 1000 個目錄 |
| 難以管理 | 難以備份、清理、監控 | 運維成本增加 |
| 擴展性差 | 不適合大規模部署 | 無法支撐未來增長 |

### Qdrant 的優勢

| 特性 | ChromaDB | Qdrant |
|------|----------|--------|
| 數據管理 | 分散 UUID 目錄 | 集中式存儲 |
| 擴展性 | 單機 | 水平擴展 |
| Dashboard | 無 | 內建 Web UI |
| 開源授權 | Apache 2.0 | Apache 2.0 |
| 性能 | 一般 | 高性能 Rust 實現 |

---

## 架構變更

### 變更前架構

```
┌─────────────────────────────────────────────────────────┐
│                    AI-Box 系統                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐    │
│  │ SeaWeedFS   │   │  ArangoDB   │   │  ChromaDB   │    │
│  │ (文件存儲)  │   │ (知識圖譜)  │   │ (向量存儲)  │    │
│  │             │   │             │   │ UUID 目錄   │    │
│  └─────────────┘   └─────────────┘   └─────────────┘    │
│        ↓                  ↓                  ↓           │
│    S3 兼容             圖數據庫         分散管理         │
└─────────────────────────────────────────────────────────┘
```

### 變更後架構

```
┌─────────────────────────────────────────────────────────┐
│                    AI-Box 系統                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐    │
│  │ SeaWeedFS   │   │  ArangoDB   │   │   Qdrant    │    │
│  │ (文件存儲)  │   │ (知識圖譜)  │   │ (向量存儲)  │    │
│  │             │   │             │   │ + Dashboard │    │
│  └─────────────┘   └─────────────┘   └─────────────┘    │
│        ↓                  ↓                  ↓           │
│    S3 兼容             圖數據庫        集中管理          │
└─────────────────────────────────────────────────────────┘
```

---

## 文件變更

### 新增文件

| 文件 | 說明 |
|------|------|
| `docker-compose.qdrant.yml` | Qdrant 整合的 Docker Compose 配置 |
| `services/api/services/qdrant_vector_store_service.py` | Qdrant 向量存儲服務 |

### 修改文件

| 文件 | 變更 |
|------|------|
| `config/config.json` | 添加 `datastores.qdrant` 配置 |

### 標記過時

| 文件 | 狀態 |
|------|------|
| `docker-compose.yml` 中的 chromadb 部分 | 保留但標記過時 |
| `services/api/services/vector_store_service.py` | 保留，回滾時使用 |

---

## 配置變更

### config/config.json

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
      "hnsw": {
        "m": 16,
        "ef_construct": 100,
        "full_scan_threshold": 10000
      }
    },
    "chromadb": {
      "_deprecated": true,
      "_deprecated_reason": "已遷移到 Qdrant"
    }
  }
}
```

---

## API 接口

### 現有接口（保持兼容）

| 接口 | 服務 | 說明 |
|------|------|------|
| `get_vector_store_service()` | ChromaDB | 原服務 |
| `get_qdrant_vector_store_service()` | Qdrant | 新服務 |

### 遷移後使用

```python
# 切換到 Qdrant
from services.api.services.qdrant_vector_store_service import get_qdrant_vector_store_service

service = get_qdrant_vector_store_service()
service.store_vectors(file_id, chunks, embeddings)
```

---

## 管理界面

### Qdrant Dashboard

Qdrant 1.6+ 內建 Web UI，可通過 iframe 嵌入系統管理界面：

```
URL: http://localhost:6333/dashboard
```

### 嵌入方式

```tsx
function QdrantDashboard() {
  return (
    <iframe
      src="http://localhost:6333/dashboard"
      style={{
        width: '100%',
        height: 'calc(100vh - 64px)',
        border: 'none'
      }}
      title="Qdrant Dashboard"
    />
  );
}
```

---

## 部署步驟

### 1. 啟動 Qdrant

```bash
# 使用 Docker Compose
docker-compose -f docker-compose.qdrant.yml up -d

# 或獨立啟動
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v /path/to/data/qdrant:/qdrant/storage \
  qdrant/qdrant
```

### 2. 安裝依賴

```bash
pip install qdrant-client
```

### 3. 更新配置

確保 `config/config.json` 中有正確的 `datastores.qdrant` 配置。

### 4. 更新代碼

將向量存儲服務從 ChromaDB 切換到 Qdrant。

---

## 回滾計劃

如需回滾到 ChromaDB，請參見 [ROLLBACK_PLAN.md](./ROLLBACK_PLAN.md)。

---

## 測試

### 單一文件測試

```bash
python3 scripts/test_file_upload_phase2.py
```

### 向量查詢測試

```python
from services.api.services.qdrant_vector_store_service import get_qdrant_vector_store_service

service = get_qdrant_vector_store_service()
results = service.query_vectors(
    query_embedding=[0.1, 0.2, ...],
    limit=10
)
```

---

## 監控

### 健康檢查

```bash
curl http://localhost:6333/health
```

### 監控指標

- `http://localhost:6333/metrics` (如果啟用)

---

## 常見問題

### Q1: Qdrant 和 ChromaDB 可以同時運行嗎？

可以。ChromaDB 保留用於回滾，Qdrant 作為主要向量存儲。

### Q2: 數據如何遷移？

目前不支持自動遷移。需要：

1. 從 ChromaDB 導出向量
2. 重新處理文件上傳
3. 自動存入 Qdrant

### Q3: 如果 Qdrant 不可用怎麼辦？

系統應記錄錯誤日誌，並返回空結果。建議部署高可用 Qdrant 集群。

---

## 更新記錄

| 日期 | 版本 | 變更 |
|------|------|------|
| 2026-01-20 | 1.0 | 初始版本 |

---

## 相關文檔

- [Qdrant 官方文檔](https://qdrant.tech/documentation/)
- [Qdrant Web UI](https://github.com/qdrant/qdrant-web-ui)
- [回滾計劃](./ROLLBACK_PLAN.md)
