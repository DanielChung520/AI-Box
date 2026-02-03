# AI-Box Docker 容器整理報告

**報告日期**: 2026-01-27  
**分析範圍**: 容器、Image、Volume 的完整關係

---

## 📊 容器總覽

### 統計摘要

| 狀態 | 數量 |
|------|------|
| 運行中 | 16 個 |
| 已停止 | 1 個 |
| 未啟動 | 3 個 |
| **總計** | **20 個** |

### Image 使用情況

| Image | 使用次數 | 大小 | 容器 |
|-------|---------|------|------|
| chrislusf/seaweedfs | 9 | 267 MB | 6 個運行中 + 3 個未啟動 |
| redis:7-alpine | 3 | 61 MB | 2 個運行中 + 1 個未啟動 |
| chromadb/chroma | 2 | 789 MB | 1 個運行中（unhealthy）+ 1 個未啟動 |
| arangodb:3.12 | 1 | 823 MB | 運行中 |
| qdrant/qdrant | 1 | 284 MB | 運行中 |
| grafana/grafana | 1 | 932 MB | 運行中 |
| prom/prometheus | 1 | 465 MB | 運行中 |
| prom/alertmanager | 1 | 111 MB | 運行中 |
| prom/node-exporter | 1 | 39 MB | 運行中 |
| redis_exporter | 1 | 13 MB | 運行中 |
| oauth2-proxy | 1 | 50 MB | 已停止 |

**Image 總大小**: ~3.8 GB

### Volume 使用情況

| 類型 | 數量 |
|------|------|
| 已使用（命名） | 15 個 |
| 已使用（未命名） | 3 個 |
| 孤立的 | 10 個 |
| **總計** | **28 個** |

---

## 🗄️ 核心數據庫（4 個）

| 容器名稱 | Image | 狀態 | Volumes | Bind Mounts | 用途 |
|---------|-------|------|---------|-------------|------|
| **arangodb** | arangodb:3.12 (823 MB) | ✅ Up 18h (healthy) | • ai-box_arangodb_data<br>• ai-box_arangodb_apps_data | - | 圖資料庫 - 存儲知識圖譜、Agent 註冊資料 |
| **redis** | redis:7-alpine (61 MB) | ✅ Up 18h (healthy) | • ai-box_redis_data | - | RQ 任務隊列、快取、Session 存儲 |
| **qdrant** | qdrant/qdrant (284 MB) | ✅ Up 18h | - | • data/qdrant → /qdrant/storage | 向量資料庫 - 替代 ChromaDB 的新方案 |
| **chromadb** | chromadb/chroma (789 MB) | ⚠️ Up 18h (unhealthy) | • ai-box_chromadb_data | - | 向量資料庫 - 已被 Qdrant 替代（可能不再使用） |

---

## 📁 SeaweedFS - 文件存儲系統（6 個）

| 容器名稱 | Image | 狀態 | Volumes | Bind Mounts | 用途 |
|---------|-------|------|---------|-------------|------|
| **seaweedfs-ai-box-master** | chrislusf/seaweedfs (267 MB) | ✅ Up 18h | • ai-box_seaweedfs-master-data | - | AI-Box 主伺服器 - 管理 Master 節點 |
| **seaweedfs-ai-box-volume** | chrislusf/seaweedfs | ✅ Up 18h | • ai-box_seaweedfs-volume-data | - | AI-Box 存儲節點 - 存儲文件數據 |
| **seaweedfs-ai-box-filer** | chrislusf/seaweedfs | ✅ Up 18h | • 1f08d27...735e (unnamed)<br>• ai-box_seaweedfs-ai-box-s3-config | - | AI-Box 文件伺服器 - 提供 S3 相容 API |
| **seaweedfs-datalake-master** | chrislusf/seaweedfs | ✅ Up 18h | • ai-box_seaweedfs-datalake-master-data | - | 數據湖主伺服器 - 管理數據湖 Master 節點 |
| **seaweedfs-datalake-volume** | chrislusf/seaweedfs | ✅ Up 18h | • ai-box_seaweedfs-datalake-volume-data | - | 數據湖存儲節點 - 存儲數據湖文件 |
| **seaweedfs-datalake-filer** | chrislusf/seaweedfs | ✅ Up 18h | • e3c923...dfa9f (unnamed)<br>• ai-box_seaweedfs-datalake-s3-config | - | 數據湖文件伺服器 - 提供數據湖 API |

---

## 📊 監控系統（5 個）

| 容器名稱 | Image | 狀態 | Volumes | Bind Mounts | 用途 |
|---------|-------|------|---------|-------------|------|
| **aibox-grafana** | grafana/grafana (932 MB) | ✅ Up 18h | • ai-box_grafana_data | • monitoring/grafana/grafana.ini → /etc/grafana/grafana.ini<br>• monitoring/grafana/provisioning → /etc/grafana/provisioning<br>• monitoring/grafana/dashboards → /var/lib/grafana/dashboards | 監控視覺化平台 - 顯示系統指標 Dashboard |
| **aibox-prometheus** | prom/prometheus (465 MB) | ✅ Up 18h | • ai-box_prometheus_data | • monitoring/prometheus/alerts.yml → /etc/prometheus/alerts.yml<br>• monitoring/prometheus/prometheus.yml → /etc/prometheus/prometheus.yml | 監控數據採集 - 收集各服務指標 |
| **aibox-alertmanager** | prom/alertmanager (111 MB) | ✅ Up 18h | • ai-box_alertmanager_data | • monitoring/alertmanager/alertmanager.yml → /etc/alertmanager/alertmanager.yml | 告警管理 - 發送告警通知 |
| **aibox-node-exporter** | prom/node-exporter (39 MB) | ✅ Up 18h | - | • /proc → /host/proc<br>• /sys → /host/sys<br>• / → /rootfs | 節點指標導出 - 導出系統指標給 Prometheus |
| **aibox-redis-exporter** | redis_exporter (13 MB) | ✅ Up 18h | - | - | Redis 指標導出 - 監控 Redis 性能 |

---

## 🔐 其他容器（1 個）

| 容器名稱 | Image | 狀態 | Volumes | Bind Mounts | 用途 |
|---------|-------|------|---------|-------------|------|
| **aibox-oauth2-proxy** | oauth2-proxy:v7.5.1 (50 MB) | ❌ Exited 8d | - | - | OAuth2 代理服務 - 身份認證（已停止） |

---

## ⚠️ 未使用的容器（4 個 - 可清理）

| 容器名稱 | Image | 狀態 | Volumes | Bind Mounts | 用途 | 建議 |
|---------|-------|------|---------|-------------|------|------|
| **sad_wozniak** | redis:7-alpine | ⚠️ Up 1h | • dcf939...c070 (unnamed) | - | 測試用 Redis 實例 | 可能是測試或調試產生，建議刪除 |
| **bcd8d823ea58_ai-box-redis-prod** | redis:7-alpine | ⏸️ Created | - | - | 生產環境 Redis（未啟動） | 與 `redis` 重複，可刪除 |
| **ai-box-seaweedfs-prod** | chrislusf/seaweedfs | ⏸️ Created | - | - | 生產環境 SeaweedFS（未啟動） | 與 `seaweedfs-ai-box-*` 重複，可刪除 |
| **3f7766aec947_ai-box-chromadb-prod** | chromadb/chroma | ⏸️ Created | - | - | 生產環境 ChromaDB（未啟動） | ChromaDB 已被 Qdrant 替代，可刪除 |

---

## 🗑️ 孤立的 Volumes（10 個）

| Volume 名稱 | 大小 | 創建時間 | 建議操作 |
|------------|------|----------|----------|
| 5c34d5d96666111c9c2f260943f9ffae7c031eac4fd1221fa00f1d8aa63fb9b6 | ? | ? | 可能是舊 SeaweedFS volume，建議檢查後刪除 |
| 95155dd9f2bbe3b6495b281880ea45f3053e3e34d21aed2ce7457bf605d2c282 | ? | ? | 可能是舊 SeaweedFS volume，建議檢查後刪除 |
| b962f8b3675a29842215edbfc68fd1fad942554381193cc1fa06083d083ee017 | ? | ? | 可能是舊 SeaweedFS volume，建議檢查後刪除 |
| d96879b78b6199d01975f596e35b0eff6007653eaf0734e99237b466c675d257 | ? | ? | 可能是舊 SeaweedFS volume，建議檢查後刪除 |
| da6023c8280eaafe9804ae993efdec16189b8aa267f673e4adf573375a7d4ce8 | ? | ? | 可能是舊 SeaweedFS volume，建議檢查後刪除 |
| fc3c4419ade44ef36efbf2d3382729c7f06e3ed04e9799a10f1bec78d76a2f6e | ? | ? | 可能是舊 SeaweedFS volume，建議檢查後刪除 |
| fe5769e17d263f79213dd7665de5857a4424068bb8b17098b997ca6ffb4cc842 | ? | ? | 可能是舊 SeaweedFS volume，建議檢查後刪除 |
| **seaweedfs-ai-box-s3-config** | ? | ? | 舊命名（已替換為 ai-box_seaweedfs-ai-box-s3-config） |
| **seaweedfs-datalake-s3-config** | ? | ? | 舊命名（已替換為 ai-box_seaweedfs-datalake-s3-config） |
| **ai-box_seaweedfs_data** | ? | ? | 可能是舊 SeaweedFS volume，建議檢查後刪除 |

---

## 🚨 需要關注的問題

### 1. ChromaDB 狀態異常
- **容器**: `chromadb` (unhealthy)
- **問題**: 已被 Qdrant 替代，但仍在運行且狀態異常
- **建議**: 
  - 檢查是否有遷移需要的數據
  - 停止並刪除容器及其 volume
  - 刪除對應的 image（chromadb/chroma）

### 2. OAuth2 Proxy 已停止
- **容器**: `aibox-oauth2-proxy` (Exited 8 days ago)
- **問題**: 已停止 8 天
- **建議**: 
  - 確認是否還需要 OAuth2 認證（已有 SSO）
  - 如不需要，刪除容器和 image

### 3. 測試用 Redis 實例
- **容器**: `sad_wozniak` (Up About an hour)
- **問題**: 可能是調試時產生，與正式 `redis` 容器重複
- **建議**: 
  - 確認用途
  - 如不需要，刪除容器及其 volume

### 4. 未啟動的生產環境容器
- **容器**: 3 個 Created 狀態的容器
- **問題**: 與運行中容器重複
- **建議**: 
  - 刪除這些未啟動的容器

### 5. 孤立的 Volumes
- **數量**: 10 個
- **問題**: 不再被任何容器使用，占用磁盤空間
- **建議**: 
  - 檢查是否有需要的數據
  - 清理這些孤立的 volumes

---

## 🧹 清理建議

### 立即可刪除
```bash
# 停止並刪除未啟動的生產環境容器
docker rm bcd8d823ea58_ai-box-redis-prod
docker rm ai-box-seaweedfs-prod
docker rm 3f7766aec947_ai-box-chromadb-prod

# 刪除已停止的 OAuth2 Proxy
docker rm aibox-oauth2-proxy
```

### 需確認後刪除
```bash
# ChromaDB（確認數據遷移後）
docker stop chromadb
docker rm chromadb
docker volume rm ai-box_chromadb_data
docker rmi chromadb/chroma:latest

# 測試用 Redis（確認用途後）
docker stop sad_wozniak
docker rm sad_wozniak
docker volume rm dcf9399343c47efddcbe7a65fae2a3f714c4e776319eb3f2cb60c995f1c2c070
```

### 清理孤立 Volumes
```bash
# 檢查 volume 內容後刪除
docker volume ls -f dangling=true

# 刪除所有孤立的 volumes
docker volume prune

# 或刪除特定 volume
docker volume rm <volume-name>
```

### 清理未使用的 Images
```bash
# 刪除所有未被使用的 images
docker image prune -a
```

---

## 📈 優化後的狀態

清理後預期狀態：

| 項目 | 清理前 | 清理後 | 減少 |
|------|--------|--------|------|
| 容器 | 20 | 13 | -7 |
| 運行中容器 | 16 | 15 | -1 (ChromaDB) |
| Image | 11 | 9 | -2 (ChromaDB, OAuth2) |
| Volume | 28 | 18 | -10 |
| 磁盤空間 | ~3.8 GB | ~2.9 GB | ~900 MB |

---

## 📝 維護建議

1. **定期檢查孤立資源**
   ```bash
   # 每週執行一次
   docker container prune  # 清理已停止的容器
   docker image prune -a     # 清理未使用的鏡像
   docker volume prune       # 清理未使用的 volumes
   ```

2. **監控容器健康狀態**
   ```bash
   # 檢查所有容器健康狀態
   docker ps --format "table {{.Names}}\t{{.Status}}"
   ```

3. **統一命名規範**
   - 運行中的容器應使用一致的命名前綴（如 `ai-box-`）
   - Volumes 應使用描述性名稱，避免使用隨機哈希

4. **文檔化容器用途**
   - 每個容器應有清晰的用途說明
   - 在 `docker-compose.yml` 中添加註釋

5. **使用 Docker Compose 管理**
   - 建議將容器遷移到 Docker Compose 管理
   - 便於版本控制和部署

---

**報告生成時間**: 2026-01-27 10:45  
**下次審查建議**: 2026-02-03
