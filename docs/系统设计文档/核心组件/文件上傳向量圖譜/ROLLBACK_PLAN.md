# ROLLBACK_PLAN.md

**創建日期**: 2026-01-20
**創建人**: Daniel Chung
**版本**: 1.0

---

## 概述

本文檔提供從 Qdrant 回滾到 ChromaDB 的詳細計劃。

---

## 回滾觸發條件

以下情況應考慮回滾：

| 條件 | 嚴重程度 | 說明 |
|------|----------|------|
| Qdrant 服務不可用 > 30 分鐘 | 高 | 無法提供向量檢索服務 |
| 數據丟失或損壞 | 高 | 向量數據丟失 |
| 性能下降 > 50% | 中 | 查詢延遲顯著增加 |
| 兼容性問題 | 中 | 與現有系統不兼容 |

---

## 回滾步驟

### 步驟 1: 評估影響範圍

```bash
# 檢查有多少文件使用 Qdrant 存儲
curl -s http://localhost:6333/collections | python3 -c "
import sys, json
data = json.load(sys.stdin)
total = sum(c.vectors_count for c in data.get('collections', []))
print(f'Total vectors in Qdrant: {total}')
"
```

### 步驟 2: 停止 Qdrant 服務

```bash
# 停止 Qdrant 容器
docker-compose -f docker-compose.qdrant.yml stop qdrant

# 或獨立停止
docker stop qdrant && docker rm qdrant
```

### 步驟 3: 啟動 ChromaDB 服務

```bash
# 確保 ChromaDB 運行
docker-compose up -d chromadb
```

### 步驟 4: 更新配置

修改 `config/config.json`，禁用 Qdrant：

```json
{
  "datastores": {
    "qdrant": {
      "_disabled": true
    }
  }
}
```

### 步驟 5: 恢復向量存儲服務

在代碼中切換回 ChromaDB：

```python
# 從
from services.api.services.qdrant_vector_store_service import get_qdrant_vector_store_service

# 改為
from services.api.services.vector_store_service import get_vector_store_service
```

### 步驟 6: 重新處理文件（可選）

如果需要從頭重建向量：

1. 清理 ChromaDB 數據
2. 重新上傳所有文件
3. 自動觸發向量化

```bash
# 清理 ChromaDB
python3 << 'EOF'
import chromadb
client = chromadb.HttpClient(host='localhost', port=8001)
for coll in client.list_collections():
    try:
        client.delete_collection(coll.name)
    except:
        pass
print('ChromaDB cleaned')
EOF

# 重新處理文件
# 通過文件上傳界面重新上傳文件
```

### 步驟 7: 驗證服務

```bash
# 測試 ChromaDB
curl -s http://localhost:8001/api/v1/heartbeat

# 測試 API
curl -s http://localhost:8000/health
```

---

## 快速回滾命令

```bash
#!/bin/bash
# rollback_to_chromadb.sh

echo "Starting rollback to ChromaDB..."

# 1. 停止 Qdrant
echo "Stopping Qdrant..."
docker stop qdrant 2>/dev/null || true
docker rm qdrant 2>/dev/null || true

# 2. 啟動 ChromaDB
echo "Starting ChromaDB..."
docker-compose up -d chromadb

# 3. 等待 ChromaDB 啟動
echo "Waiting for ChromaDB..."
sleep 10

# 4. 驗證
if curl -s http://localhost:8001/api/v1/heartbeat > /dev/null; then
    echo "✅ ChromaDB is running"
else
    echo "❌ ChromaDB health check failed"
fi

echo "Rollback complete!"
echo "Note: Remember to update your code to use get_vector_store_service() instead of get_qdrant_vector_store_service()"
```

---

## 回滾後檢查清單

- [ ] Qdrant 容器已停止
- [ ] ChromaDB 服務運行正常
- [ ] API 健康檢查通過
- [ ] 文件上傳功能正常
- [ ] 向量查詢功能正常
- [ ] 監控指標正常

---

## 數據恢復

### 從 Qdrant 導出

```python
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)

collections = client.get_collections()
for coll in collections.collections:
    print(f"Collection: {coll.name}")
    points = client.scroll(
        collection_name=coll.name,
        limit=1000
    )[0]
    print(f"  Points: {len(points)}")
```

### 數據格式

導出的數據格式：

```json
{
  "collection": "file_xxx",
  "vectors": [
    {
      "id": "file_xxx_0",
      "vector": [0.1, 0.2, ...],
      "payload": {
        "file_id": "xxx",
        "chunk_index": 0,
        "chunk_text": "..."
      }
    }
  ]
}
```

---

## 聯繫方式

回滾過程中如有問題，請聯繫：

- 系統管理員
- 值班工程師

---

## 更新記錄

| 日期 | 版本 | 變更 |
|------|------|------|
| 2026-01-20 | 1.0 | 初始版本 |

---

## 相關文檔

- [遷移說明](./CHROMADB_TO_QDRANT_MIGRATION.md)
