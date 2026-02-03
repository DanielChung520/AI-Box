# Docker 清理報告

**清理日期**: 2026-01-27  
**執行人**: AI-Box System Agent

---

## 📋 清理概述

本次清理了 Docker 容器、Images 和 Volumes，移除了已廢棄的 ChromaDB，並優化了 `start_services.sh` 啟動腳本。

---

## 🗑️ 已刪除資源

### 容器（6 個）

| 容器名稱 | 刪除原因 |
|---------|---------|
| **chromadb** | 已被 Qdrant 替代，狀態 unhealthy |
| **aibox-oauth2-proxy** | 已停止 8 天，不再需要 |
| **bcd8d823ea58_ai-box-redis-prod** | 未啟動，與 `redis` 重複 |
| **ai-box-seaweedfs-prod** | 未啟動，與 `seaweedfs-ai-box-*` 重複 |
| **3f7766aec947_ai-box-chromadb-prod** | 未啟動，ChromaDB 已廢棄 |
| **sad_wozniak** | 測試用 Redis 實例 |

### Volumes（11 個）

| Volume 名稱 | 刪除原因 |
|------------|---------|
| **ai-box_chromadb_data** | ChromaDB 已廢棄 |
| **dcf939...c070** | 測試用 Redis volume |
| **5c34d5...b9b6** | 孤立的 SeaweedFS volume |
| **95155d...c282** | 孤立的 SeaweedFS volume |
| **b962f8...e017** | 孤立的 SeaweedFS volume |
| **d96879...d257** | 孤立的 SeaweedFS volume |
| **da6023...dce8** | 孤立的 SeaweedFS volume |
| **fc3c44...f6e** | 孤立的 SeaweedFS volume |
| **fe5769e...c842** | 孤立的 SeaweedFS volume |
| **seaweedfs-ai-box-s3-config** | 舊命名（已替換為 ai-box_seaweedfs-ai-box-s3-config） |
| **seaweedfs-datalake-s3-config** | 舊命名（已替換為 ai-box_seaweedfs-datalake-s3-config） |
| **ai-box_seaweedfs_data** | 舊命名 |

### Images（5 個）

| Image | 刪除原因 | 大小 |
|-------|---------|------|
| **chromadb/chroma:latest** | ChromaDB 已廢棄 | 789 MB |
| **quay.io/oauth2-proxy/oauth2-proxy:v7.5.1** | OAuth2 已停止 | 50.7 MB |
| **arangodb/arangodb:latest** | 舊版本，已被 arangodb:3.12 替代 | 685 MB |
| **alpine:latest** | 未使用 | 13.6 MB |
| **hello-world:latest** | 測試用 | 16.9 kB |

---

## 📊 清理效果

### 容器統計

| 項目 | 清理前 | 清理後 | 變化 |
|------|--------|--------|------|
| 總容器數 | 20 | 14 | -6 |
| 運行中容器 | 16 | 14 | -2 |
| 已停止容器 | 1 | 0 | -1 |
| 未啟動容器 | 3 | 0 | -3 |

### Image 統計

| 項目 | 清理前 | 清理後 | 變化 |
|------|--------|--------|------|
| 總 Image 數 | 14 | 10 | -4 |
| 總大小 | ~4.2 GB | ~3.1 GB | -1.1 GB |

### Volume 統計

| 項目 | 清理前 | 清理後 | 變化 |
|------|--------|--------|------|
| 總 Volume 數 | 28 | 15 | -13 |
| 已使用 Volume | 18 | 15 | -3 |
| 孤立 Volume | 10 | 0 | -10 |
| 釋放空間 | - | 288 KB | - |

---

## 🔧 腳本修改

### `scripts/start_services.sh` 修改內容

#### 1. 移除 ChromaDB 相關配置
- 移除 `CHROMADB_PORT` 變數定義
- 移除 `start_chromadb()` 函數（120 行）
- 移除 `start_all` 中的 `start_chromadb` 調用

#### 2. 新增監控系統啟動功能
- 新增 `start_monitoring()` 函數（約 60 行）
- 啟動監控系統：Prometheus、Grafana、Alertmanager、Node Exporter、Redis Exporter
- 使用 `docker-compose.monitoring.yml` 配置文件
- 支援檢查啟動狀態和等待服務就緒

#### 3. 優化啟動順序
調整 `start_all` 的啟動順序，分為三個階段：

```
[1/3] 基礎設施服務
  └─ Redis（RQ Worker、Dashboard 依賴）
  └─ ArangoDB（數據庫）
  └─ Qdrant（向量數據庫）

[2/3] 存儲和監控服務
  └─ SeaweedFS（AI-Box 和 DataLake）
  └─ SeaweedFS Buckets
  └─ 監控系統（Prometheus、Grafana、Alertmanager）

[3/3] 應用服務
  └─ FastAPI（需要基礎設施和存儲服務）
  └─ MCP Server
  └─ Frontend
  └─ RQ Worker（需要 Redis 和 FastAPI）
  └─ RQ Dashboard（需要 Redis）
```

#### 4. 更新 help 文檔
- 移除 `chromadb` 選項
- 新增 `monitoring` 選項
- 重新組織選項分類（基礎設施、存儲和監控、應用服務、其他）

#### 5. 更新 `check_status()` 函數
- 移除 ChromaDB 狀態檢查
- 新增監控系統狀態檢查：
  - Grafana (端口 3001)
  - Prometheus (端口 9090)
  - Alertmanager (端口 9093)
  - Node Exporter (端口 9100)
  - Redis Exporter (端口 9121)

---

## 📁 備份資訊

### 備份位置
`docs/備份與歸檔/Docker狀態備份/`

### 備份文件
- `containers_20260127_YYYYMMSS.txt` - 清理前的容器狀態
- `volumes_20260127_YYYYMMSS.txt` - 清理前的 Volume 列表
- `images_20260127_YYYYMMSS.txt` - 清理前的 Image 列表

---

## ✅ 清理後狀態

### 運行中的容器（14 個）

| 容器名稱 | Image | 端口 | 狀態 |
|---------|-------|------|------|
| **arangodb** | arangodb:3.12 | 8529 | ✅ Up 18h (healthy) |
| **redis** | redis:7-alpine | 6379 | ✅ Up 18h (healthy) |
| **qdrant** | qdrant/qdrant | 6333-6334 | ✅ Up 18h |
| **seaweedfs-ai-box-master** | chrislusf/seaweedfs | 9333 | ✅ Up 18h |
| **seaweedfs-ai-box-volume** | chrislusf/seaweedfs | 內部 | ✅ Up 18h |
| **seaweedfs-ai-box-filer** | chrislusf/seaweedfs | 8333, 8888 | ✅ Up 18h |
| **seaweedfs-datalake-master** | chrislusf/seaweedfs | 9334 | ✅ Up 18h |
| **seaweedfs-datalake-volume** | chrislusf/seaweedfs | 內部 | ✅ Up 18h |
| **seaweedfs-datalake-filer** | chrislusf/seaweedfs | 8334, 8889 | ✅ Up 18h |
| **aibox-grafana** | grafana/grafana | 3001 | ✅ Up 18h |
| **aibox-prometheus** | prom/prometheus | 9090 | ✅ Up 18h |
| **aibox-alertmanager** | prom/alertmanager | 9093 | ✅ Up 18h |
| **aibox-redis-exporter** | redis_exporter | 9121 | ✅ Up 18h |
| **aibox-node-exporter** | prom/node-exporter | 9100 | ✅ Up 18h |

### 保留的 Volumes（15 個）

| Volume 名稱 | 用途 |
|------------|------|
| ai-box_arangodb_data | ArangoDB 數據 |
| ai-box_arangodb_apps_data | ArangoDB Apps 數據 |
| ai-box_redis_data | Redis 數據 |
| ai-box_grafana_data | Grafana 數據 |
| ai-box_prometheus_data | Prometheus 數據 |
| ai-box_alertmanager_data | Alertmanager 數據 |
| ai-box_seaweedfs-master-data | AI-Box SeaweedFS Master 數據 |
| ai-box_seaweedfs-volume-data | AI-Box SeaweedFS Volume 數據 |
| ai-box_seaweedfs-ai-box-s3-config | AI-Box SeaweedFS S3 配置 |
| ai-box_seaweedfs-datalake-master-data | DataLake SeaweedFS Master 數據 |
| ai-box_seaweedfs-datalake-volume-data | DataLake SeaweedFS Volume 數據 |
| ai-box_seaweedfs-datalake-s3-config | DataLake SeaweedFS S3 配置 |
| 1f08d27...735e | AI-Box SeaweedFS Filer 數據 |
| e3c923...dfa9f | DataLake SeaweedFS Filer 數據 |

---

## 🎯 清理效果總結

### 優化成果
1. ✅ 移除已廢棄的 ChromaDB 及其相關資源
2. ✅ 清理 6 個未使用的容器
3. ✅ 清理 13 個孤立的 Volumes
4. ✅ 清理 5 個未使用的 Images（釋放 1.1 GB）
5. ✅ 新增監控系統啟動功能
6. ✅ 優化服務啟動順序，避免依賴問題
7. ✅ 移除已廢棄的 ChromaDB 相關代碼
8. ✅ 更新文檔和狀態檢查功能

### 系統改進
- 啟動順序更合理，避免依賴問題
- 監控系統可獨立啟動和管理
- 移除過時服務，降低維護複雜度
- 釋放磁盤空間約 1.1 GB
- 提高系統整潔度和可維護性

---

**報告生成時間**: 2026-01-27  
**下次檢查建議**: 2026-02-03
