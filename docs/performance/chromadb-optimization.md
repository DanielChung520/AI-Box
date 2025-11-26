# ChromaDB 性能優化指南

**創建日期**: 2025-10-25
**創建人**: Daniel Chung
**最後修改日期**: 2025-10-25

## 概述

本文檔提供 ChromaDB 性能優化的最佳實踐和建議，包括批量寫入、索引調整、資源配置等方面的優化策略。

## 性能目標

- **批量寫入**: 支持 1k-100k 文檔的高效寫入
- **檢索延遲**: P95 延遲 < 200ms（1k 文檔規模）
- **並發查詢**: 支持 10-100 並發查詢
- **吞吐量**: 單機 QPS > 50

## 批量寫入優化

### 1. 批次大小配置

**建議配置**:
- 小批量（< 1k 文檔）: `batch_size = 50-100`
- 中批量（1k-10k 文檔）: `batch_size = 100-200`
- 大批量（> 10k 文檔）: `batch_size = 200-500`

**原因**:
- 批次太小會增加網絡開銷和事務成本
- 批次太大會導致內存壓力並增加失敗風險
- 需要根據文檔大小和系統資源調整

**示例**:
```python
from databases.chromadb import ChromaDBClient, ChromaCollection

client = ChromaDBClient(mode="persistent")
collection_obj = client.get_or_create_collection("my_collection")
collection = ChromaCollection(
    collection_obj,
    batch_size=200  # 根據數據量調整
)

# 批量添加
items = [...]  # 大量文檔
result = collection.batch_add(items, batch_size=200)
```

### 2. 並發寫入

對於超大規模數據（> 100k），可以考慮並發寫入：

```python
from concurrent.futures import ThreadPoolExecutor

def write_batch(batch_items):
    collection.batch_add(batch_items, batch_size=100)
    return len(batch_items)

# 將數據分片
batches = [items[i:i+1000] for i in range(0, len(items), 1000)]

# 並發寫入（注意：需要確保 ChromaDB 支持並發寫入）
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(write_batch, batch) for batch in batches]
    results = [f.get() for f in futures]
```

**注意事項**:
- 並發寫入可能導致索引競爭，需要測試驗證
- 建議並發數不超過 CPU 核心數
- 監控內存和 I/O 使用情況

### 3. 嵌入向量預處理

在寫入前預處理嵌入向量可以減少寫入時間：

```python
# 標準化嵌入向量格式
from databases.chromadb.utils import normalize_embeddings, validate_embedding_dimension

embeddings = normalize_embeddings(raw_embeddings)
validate_embedding_dimension(embeddings, expected_dim=384)
```

## 檢索性能優化

### 1. 索引配置

ChromaDB 使用 HNSW (Hierarchical Navigable Small World) 索引，可以通過以下方式優化：

**索引參數**（如果 ChromaDB 支持）:
- `ef_construction`: 構建時的搜索範圍（越大越準確，但構建時間更長）
- `M`: 每個節點的連接數（越大索引越大，但查詢更快）

**建議**:
- 對於讀多寫少的場景，增加 `ef_construction` 和 `M`
- 對於寫多讀少的場景，使用較小的參數以加快寫入速度

### 2. 查詢參數優化

**n_results 限制**:
- 只返回需要的結果數量，避免不必要的計算
- 建議 `n_results <= 100`

**where 過濾優化**:
- 使用索引字段進行過濾（如果 ChromaDB 支持）
- 避免複雜的嵌套查詢

```python
# 好的做法：使用簡單的過濾條件
result = collection.query(
    query_embeddings=query_emb,
    n_results=10,
    where={"category": "A", "status": "active"}  # 簡單的等值過濾
)

# 避免：複雜的過濾條件
# where={"$and": [{"category": "A"}, {"$or": [...]}]}  # 可能較慢
```

### 3. 連線池配置

使用連線池可以減少連接開銷：

```python
from databases.chromadb import ChromaDBClient

client = ChromaDBClient(
    mode="http",
    host="localhost",
    port=8001,
    pool_size=8,  # 根據並發需求調整
    connection_timeout=5.0,
)
```

**建議配置**:
- 低並發（< 10）: `pool_size = 4`
- 中並發（10-50）: `pool_size = 8-16`
- 高並發（> 50）: `pool_size = 16-32`

## 資源配置建議

### 1. 內存配置

**最小配置**:
- 1k 文檔: 512MB RAM
- 10k 文檔: 2GB RAM
- 100k 文檔: 8GB RAM

**建議配置**:
- 1k 文檔: 1GB RAM
- 10k 文檔: 4GB RAM
- 100k 文檔: 16GB RAM

### 2. CPU 配置

- **寫入密集型**: 4-8 核心
- **查詢密集型**: 8-16 核心
- **混合負載**: 8-12 核心

### 3. 存儲配置

**持久化模式**:
- 使用 SSD 存儲以獲得最佳 I/O 性能
- 確保有足夠的磁盤空間（至少是數據大小的 2-3 倍）
- 考慮使用 NVMe SSD 以獲得最佳性能

**Docker 配置示例**:
```yaml
services:
  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - ./chroma_data:/chroma/chroma  # 使用本地 SSD
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '2'
          memory: 2G
```

### 4. Kubernetes 配置

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chromadb
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: chromadb
        resources:
          requests:
            memory: "2Gi"
            cpu: "2"
          limits:
            memory: "4Gi"
            cpu: "4"
        volumeMounts:
        - name: chroma-data
          mountPath: /chroma/chroma
      volumes:
      - name: chroma-data
        persistentVolumeClaim:
          claimName: chromadb-pvc
```

## 監控與調優

### 1. 關鍵指標

- **寫入吞吐量**: 文檔/秒
- **查詢延遲**: P50, P95, P99 延遲
- **QPS**: 每秒查詢數
- **內存使用**: 峰值和平均值
- **CPU 使用率**: 平均值和峰值
- **I/O 使用**: 讀寫 IOPS

### 2. 性能測試

使用提供的性能測試腳本：

```bash
# 基本測試
python scripts/performance/chromadb_benchmark.py \
    --num-docs 1000 \
    --num-queries 100 \
    --target-latency 200

# 並發測試
python scripts/performance/chromadb_benchmark.py \
    --num-docs 1000 \
    --num-queries 100 \
    --concurrent \
    --num-threads 10 \
    --output benchmark_report.json
```

### 3. 性能調優流程

1. **基準測試**: 記錄當前性能指標
2. **識別瓶頸**: 分析 CPU、內存、I/O 使用情況
3. **調整參數**: 根據瓶頸調整配置
4. **驗證改進**: 重新測試並對比結果
5. **文檔記錄**: 記錄最佳配置

## 常見問題與解決方案

### 1. 寫入速度慢

**可能原因**:
- 批次大小太小
- 磁盤 I/O 瓶頸
- 內存不足

**解決方案**:
- 增加 `batch_size`（建議 100-500）
- 使用 SSD 存儲
- 增加內存配置

### 2. 查詢延遲高

**可能原因**:
- 索引未優化
- 查詢結果數過多
- 並發過高導致資源競爭

**解決方案**:
- 減少 `n_results` 參數
- 使用過濾條件縮小搜索範圍
- 增加連線池大小
- 考慮增加 CPU 和內存

### 3. 內存使用過高

**可能原因**:
- 批次大小過大
- 並發查詢過多
- 索引參數過大

**解決方案**:
- 減少 `batch_size`
- 限制並發查詢數
- 調整索引參數（如果支持）

### 4. 連接超時

**可能原因**:
- 連線池大小不足
- 網絡延遲
- 服務器負載過高

**解決方案**:
- 增加 `pool_size`
- 增加 `connection_timeout`
- 檢查服務器資源使用情況

## 最佳實踐總結

1. **批量寫入**:
   - 使用 `batch_add` 方法進行批量寫入
   - 根據數據規模調整 `batch_size`（建議 100-500）
   - 監控寫入進度和錯誤率

2. **查詢優化**:
   - 限制 `n_results` 數量
   - 使用簡單的 `where` 過濾條件
   - 合理配置連線池大小

3. **資源配置**:
   - 使用 SSD 存儲
   - 確保足夠的內存（至少數據大小的 2-3 倍）
   - 根據負載類型配置 CPU

4. **監控與調優**:
   - 定期執行性能測試
   - 監控關鍵指標
   - 根據實際負載調整配置

5. **錯誤處理**:
   - 實現重試機制
   - 記錄失敗的批次以便重試
   - 監控錯誤率並設置告警

## 參考資料

- [ChromaDB 官方文檔](https://docs.trychroma.com/)
- [HNSW 算法論文](https://arxiv.org/abs/1603.09320)
- [向量數據庫性能優化](https://www.pinecone.io/learn/vector-database-performance/)
