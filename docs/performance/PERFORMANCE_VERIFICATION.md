# ChromaDB 性能驗證指南

**創建日期**: 2025-10-25
**創建人**: Daniel Chung
**最後修改日期**: 2025-10-25

## 概述

本文檔說明如何執行 ChromaDB 性能驗證，確保滿足 1k 筆嵌入寫入和 <200ms 檢索延遲的要求。

## 驗證目標

- ✅ 成功寫入 1,000 筆嵌入向量
- ✅ P95 檢索延遲 < 200ms
- ✅ 批量寫入吞吐量 > 100 文檔/秒
- ✅ 查詢 QPS > 50

## 前置要求

1. **環境準備**:
   - Python 3.11+
   - ChromaDB 已安裝（`pip install chromadb`）
   - 足夠的磁盤空間（至少 500MB）

2. **啟動 ChromaDB**:
   ```bash
   # 方式 1: 使用 Docker Compose
   docker-compose up chromadb

   # 方式 2: 使用持久化模式（無需額外服務）
   # 直接運行測試腳本即可
   ```

## 執行性能驗證

### 方法 1: 使用性能測試腳本（推薦）

```bash
# 基本性能測試（1k 文檔，100 次查詢）
python scripts/performance/chromadb_benchmark.py \
    --mode persistent \
    --num-docs 1000 \
    --num-queries 100 \
    --target-latency 200 \
    --output benchmark_report.json

# 使用 HTTP 模式（需要先啟動 ChromaDB 服務）
python scripts/performance/chromadb_benchmark.py \
    --mode http \
    --host localhost \
    --port 8001 \
    --num-docs 1000 \
    --num-queries 100 \
    --target-latency 200 \
    --output benchmark_report.json

# 並發測試
python scripts/performance/chromadb_benchmark.py \
    --mode persistent \
    --num-docs 1000 \
    --num-queries 100 \
    --concurrent \
    --num-threads 10 \
    --target-latency 200 \
    --output benchmark_report.json
```

### 方法 2: 手動驗證

```python
from databases.chromadb import ChromaDBClient, ChromaCollection
import time
import random

# 初始化客戶端
client = ChromaDBClient(mode="persistent", persist_directory="./test_chroma_data")
collection_obj = client.get_or_create_collection("perf_test")
collection = ChromaCollection(collection_obj, expected_embedding_dim=384)

# 1. 生成 1k 筆嵌入向量
print("生成 1,000 筆嵌入向量...")
embeddings = [[random.random() for _ in range(384)] for _ in range(1000)]
items = [
    {
        "id": f"doc_{i}",
        "embedding": embeddings[i],
        "metadata": {"index": i},
        "document": f"Document {i}: This is a test document for performance verification."
    }
    for i in range(1000)
]

# 2. 批量寫入測試
print("\n開始批量寫入...")
start_time = time.time()
result = collection.batch_add(items, batch_size=100)
end_time = time.time()

elapsed = end_time - start_time
print(f"寫入完成: {result['success']}/{result['total']} 文檔")
print(f"耗時: {elapsed:.2f} 秒")
print(f"吞吐量: {result['success']/elapsed:.2f} 文檔/秒")

# 3. 等待索引建立
print("\n等待索引建立...")
time.sleep(2)

# 4. 檢索性能測試
print("\n開始檢索性能測試...")
query_embeddings = [[random.random() for _ in range(384)] for _ in range(100)]
latencies = []

for i, query_emb in enumerate(query_embeddings):
    query_start = time.time()
    result = collection.query(query_embeddings=query_emb, n_results=10)
    query_end = time.time()
    latency = (query_end - query_start) * 1000  # 轉換為毫秒
    latencies.append(latency)

    if (i + 1) % 10 == 0:
        print(f"已完成 {i + 1}/100 次查詢")

# 5. 計算統計數據
import statistics
avg_latency = statistics.mean(latencies)
p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else latencies[-1]

print(f"\n檢索性能統計:")
print(f"平均延遲: {avg_latency:.2f} 毫秒")
print(f"P95 延遲: {p95_latency:.2f} 毫秒")
print(f"最小延遲: {min(latencies):.2f} 毫秒")
print(f"最大延遲: {max(latencies):.2f} 毫秒")

# 6. 驗證結果
target_latency = 200.0
if p95_latency < target_latency:
    print(f"\n✅ 性能驗證通過!")
    print(f"   P95 延遲: {p95_latency:.2f}ms < {target_latency}ms")
else:
    print(f"\n❌ 性能驗證失敗!")
    print(f"   P95 延遲: {p95_latency:.2f}ms >= {target_latency}ms")

# 清理
client.delete_collection("perf_test")
client.close()
```

## 驗證結果解讀

### 成功標準

性能測試腳本會輸出以下結果：

1. **批量寫入統計**:
   - `elapsed_time`: 總耗時（秒）
   - `throughput`: 吞吐量（文檔/秒）
   - `success_count`: 成功寫入的文檔數

2. **檢索性能統計**:
   - `avg_latency_ms`: 平均延遲（毫秒）
   - `p95_latency_ms`: P95 延遲（毫秒）**← 關鍵指標**
   - `p99_latency_ms`: P99 延遲（毫秒）
   - `qps`: 每秒查詢數

3. **驗證結果**:
   - `passed`: 是否通過驗證
   - `meets_requirement`: 是否滿足要求

### 示例輸出

```
=== 批量寫入測試: 1000 文檔, 批次大小: 100 ===
完成時間: 8.45 秒
吞吐量: 118.34 文檔/秒
平均每文檔: 8.45 毫秒
成功: 1000, 失敗: 0

=== 檢索性能測試: 100 次查詢, 每次返回 10 結果 ===
檢索性能統計:
總查詢數: 100
成功: 100, 失敗: 0
平均延遲: 45.23 毫秒
P50 延遲: 42.15 毫秒
P95 延遲: 78.90 毫秒
P99 延遲: 95.12 毫秒
QPS: 22.13

=== 性能驗證 (目標: <200.0ms) ===
✅ 性能驗證通過!
   P95 延遲: 78.90ms < 200.0ms
```

## 性能調優建議

如果性能驗證失敗，請參考以下優化建議：

1. **檢索延遲過高**:
   - 減少 `n_results` 參數
   - 使用 SSD 存儲
   - 增加內存配置
   - 參考 [性能優化文檔](chromadb-optimization.md)

2. **寫入速度慢**:
   - 增加 `batch_size`（建議 100-500）
   - 使用 SSD 存儲
   - 檢查磁盤 I/O 性能

3. **內存不足**:
   - 減少 `batch_size`
   - 增加系統內存
   - 限制並發查詢數

## 持續驗證

建議在以下場景執行性能驗證：

1. **開發階段**: 每次重大更新後
2. **CI/CD**: 在自動化測試中集成性能測試
3. **部署前**: 在 staging 環境驗證
4. **定期檢查**: 每月執行一次性能回歸測試

## 相關文檔

- [ChromaDB 性能優化指南](chromadb-optimization.md)
- [ChromaDB 部署指南](../deployment/chromadb-deployment.md)
- [ChromaDB SDK 文檔](../../databases/chromadb/README.md)
