# AI-Box Docker 管理說明

**文檔版本**: 1.0  
**最後更新**: 2026-01-27  
**適用範圍**: AI-Box 生產環境

---

## 📋 目錄

- [容器總覽](#容器總覽)
- [基礎設施服務](#基礎設施服務)
- [存儲服務](#存儲服務)
- [監控系統](#監控系統)
- [相關檔案](#相關檔案)
- [啟動和停止](#啟動和停止)
- [維護操作](#維護操作)
- [故障排除](#故障排除)

---

## 📊 容器總覽

### 運行中的容器（14 個）

| 類別 | 容器數 | 狀態 |
|------|--------|------|
| 基礎設施 | 4 | ✅ 運行中 |
| 存儲服務 | 6 | ✅ 運行中 |
| 監控系統 | 4 | ✅ 運行中 |
| **總計** | **14** | **✅ 全部運行** |

---

## 🗄️ 基礎設施服務

### 1. ArangoDB（圖資料庫）

| 項目 | 配置 |
|------|------|
| **容器名稱** | `arangodb` |
| **Image** | `arangodb:3.12` (823 MB) |
| **端口** | 8529 |
| **啟動命令** | `./scripts/start_services.sh arangodb` |
| **Docker Volume** | `ai-box_arangodb_data`<br>`ai-box_arangodb_apps_data` |
| **用途** | 存儲知識圖譜、Agent 註冊資料、系統配置 |
| **Web UI** | http://localhost:8529 |
| **健康檢查** | `docker ps --filter name=arangodb` |

**相關檔案**：
- 數據目錄：`/var/lib/docker/volumes/ai-box_arangodb_data/_data`
- Apps 目錄：`/var/lib/docker/volumes/ai-box_arangodb_apps_data/_data`
- 環境變數：`.env` 中的 `ARANGO_ROOT_PASSWORD`

**依賴關係**：
- 無依賴（基礎服務）
- 被依賴：FastAPI、RQ Worker

---

### 2. Redis（任務隊列、快取）

| 項目 | 配置 |
|------|------|
| **容器名稱** | `redis` |
| **Image** | `redis:7-alpine` (61.4 MB) |
| **端口** | 6379 |
| **啟動命令** | `./scripts/start_services.sh redis` |
| **Docker Volume** | `ai-box_redis_data` |
| **用途** | RQ 任務隊列、Session 存儲、快取 |
| **CLI 工具** | `redis-cli -h localhost -p 6379` |
| **健康檢查** | `docker ps --filter name=redis` |

**相關檔案**：
- 數據目錄：`/var/lib/docker/volumes/ai-box_redis_data/_data`
- 環境變數：`.env` 中的 `REDIS_URL`

**依賴關係**：
- 無依賴（基礎服務）
- 被依賴：RQ Worker、RQ Dashboard

---

### 3. Qdrant（向量數據庫）

| 項目 | 配置 |
|------|------|
| **容器名稱** | `qdrant` |
| **Image** | `qdrant/qdrant:latest` (284 MB) |
| **端口** | 6333 (REST), 6334 (gRPC) |
| **啟動命令** | `./scripts/start_services.sh qdrant` |
| **Bind Mount** | `./data/qdrant → /qdrant/storage` |
| **用途** | 向量數據庫 - 替代 ChromaDB |
| **Web Dashboard** | http://localhost:6333/dashboard |
| **API 文檔** | http://localhost:6333/docs |
| **健康檢查** | `docker ps --filter name=qdrant` |

**相關檔案**：
- 數據目錄：`./data/qdrant/`
- 環境變數：`.env` 中的 `QDRANT_HOST`、`QDRANT_PORT`

**依賴關係**：
- 無依賴（基礎服務）
- 被依賴：FastAPI、RQ Worker

**備註**：
- ✅ 已完全替代 ChromaDB
- ✅ 支援 gRPC 和 REST API
- ✅ 自動備份到本地目錄

---

## 📁 存儲服務

### AI-Box SeaweedFS（3 個容器）

#### 4. AI-Box SeaweedFS Master

| 項目 | 配置 |
|------|------|
| **容器名稱** | `seaweedfs-ai-box-master` |
| **Image** | `chrislusf/seaweedfs:latest` (267 MB) |
| **端口** | 9333 |
| **啟動命令** | `./scripts/start_services.sh seaweedfs-ai-box` |
| **Docker Volume** | `ai-box_seaweedfs-master-data` |
| **用途** | AI-Box SeaweedFS Master 節點 - 管理元數據 |
| **配置檔案** | `docker-compose.seaweedfs.yml` |

#### 5. AI-Box SeaweedFS Volume

| 項目 | 配置 |
|------|------|
| **容器名稱** | `seaweedfs-ai-box-volume` |
| **Image** | `chrislusf/seaweedfs:latest` |
| **端口** | 內部（無對外暴露） |
| **啟動命令** | `./scripts/start_services.sh seaweedfs-ai-box` |
| **Docker Volume** | `ai-box_seaweedfs-volume-data` |
| **用途** | AI-Box SeaweedFS 存儲節點 - 實際存儲文件 |
| **配置檔案** | `docker-compose.seaweedfs.yml` |

#### 6. AI-Box SeaweedFS Filer

| 項目 | 配置 |
|------|------|
| **容器名稱** | `seaweedfs-ai-box-filer` |
| **Image** | `chrislusf/seaweedfs:latest` |
| **端口** | 8333 (S3 API), 8888 (HTTP API) |
| **啟動命令** | `./scripts/start_services.sh seaweedfs-ai-box` |
| **Docker Volumes** | `1f08d27...735e` (數據)<br>`ai-box_seaweedfs-ai-box-s3-config` (配置) |
| **用途** | AI-Box SeaweedFS Filer - 提供 S3 相容 API |
| **S3 Endpoint** | http://localhost:8333 |
| **配置檔案** | `docker-compose.seaweedfs.yml` |

---

### DataLake SeaweedFS（3 個容器）

#### 7. DataLake SeaweedFS Master

| 項目 | 配置 |
|------|------|
| **容器名稱** | `seaweedfs-datalake-master` |
| **Image** | `chrislusf/seaweedfs:latest` |
| **端口** | 9334 |
| **啟動命令** | `./scripts/start_services.sh seaweedfs-datalake` |
| **Docker Volume** | `ai-box_seaweedfs-datalake-master-data` |
| **用途** | DataLake SeaweedFS Master 節點 |
| **配置檔案** | `docker-compose.seaweedfs-datalake.yml` |

#### 8. DataLake SeaweedFS Volume

| 項目 | 配置 |
|------|------|
| **容器名稱** | `seaweedfs-datalake-volume` |
| **Image** | `chrislusf/seaweedfs:latest` |
| **端口** | 內部（無對外暴露） |
| **啟動命令** | `./scripts/start_services.sh seaweedfs-datalake` |
| **Docker Volume** | `ai-box_seaweedfs-datalake-volume-data` |
| **用途** | DataLake SeaweedFS 存儲節點 |
| **配置檔案** | `docker-compose.seaweedfs-datalake.yml` |

#### 9. DataLake SeaweedFS Filer

| 項目 | 配置 |
|------|------|
| **容器名稱** | `seaweedfs-datalake-filer` |
| **Image** | `chrislusf/seaweedfs:latest` |
| **端口** | 8334 (S3 API), 8889 (HTTP API) |
| **啟動命令** | `./scripts/start_services.sh seaweedfs-datalake` |
| **Docker Volumes** | `e3c923...dfa9f` (數據)<br>`ai-box_seaweedfs-datalake-s3-config` (配置) |
| **用途** | DataLake SeaweedFS Filer - 提供 S3 API |
| **S3 Endpoint** | http://localhost:8334 |
| **配置檔案** | `docker-compose.seaweedfs-datalake.yml` |

---

## 📊 監控系統

### 10. Prometheus（時序數據庫）

| 項目 | 配置 |
|------|------|
| **容器名稱** | `aibox-prometheus` |
| **Image** | `prom/prometheus:latest` (465 MB) |
| **端口** | 9090 |
| **啟動命令** | `./scripts/start_services.sh monitoring` |
| **Docker Volume** | `ai-box_prometheus_data` |
| **Bind Mounts** | `./monitoring/prometheus/prometheus.yml → /etc/prometheus/prometheus.yml`<br>`./monitoring/prometheus/alerts.yml → /etc/prometheus/alerts.yml` |
| **用途** | 時序數據庫 - 收集和存儲指標 |
| **Web UI** | http://localhost:9090 |
| **配置檔案** | `docker-compose.monitoring.yml` |

**相關檔案**：
- 數據目錄：`/var/lib/docker/volumes/ai-box_prometheus_data/_data`
- 配置檔案：`./monitoring/prometheus/prometheus.yml`
- 告警配置：`./monitoring/prometheus/alerts.yml`
- 保留時間：30 天

**依賴關係**：
- 被依賴：Grafana、Alertmanager

---

### 11. Grafana（可視化平台）

| 項目 | 配置 |
|------|------|
| **容器名稱** | `aibox-grafana` |
| **Image** | `grafana/grafana:latest` (932 MB) |
| **端口** | 3001 (對外 3001 → 內部 3000) |
| **啟動命令** | `./scripts/start_services.sh monitoring` |
| **Docker Volume** | `ai-box_grafana_data` |
| **Bind Mounts** | `./monitoring/grafana/grafana.ini → /etc/grafana/grafana.ini`<br>`./monitoring/grafana/provisioning → /etc/grafana/provisioning`<br>`./monitoring/grafana/dashboards → /var/lib/grafana/dashboards` |
| **用途** | 監控視覺化平台 - 顯示系統指標 Dashboard |
| **Web UI** | http://localhost:3001 |
| **默認賬號** | admin / admin |
| **配置檔案** | `docker-compose.monitoring.yml` |

**相關檔案**：
- 數據目錄：`/var/lib/docker/volumes/ai-box_grafana_data/_data`
- 配置檔案：`./monitoring/grafana/grafana.ini`
- Provisioning：`./monitoring/grafana/provisioning/`
- Dashboards：`./monitoring/grafana/dashboards/`

**依賴關係**：
- 依賴：Prometheus

---

### 12. Alertmanager（告警管理）

| 項目 | 配置 |
|------|------|
| **容器名稱** | `aibox-alertmanager` |
| **Image** | `prom/alertmanager:latest` (111 MB) |
| **端口** | 9093 |
| **啟動命令** | `./scripts/start_services.sh monitoring` |
| **Docker Volume** | `ai-box_alertmanager_data` |
| **Bind Mounts** | `./monitoring/alertmanager/alertmanager.yml → /etc/alertmanager/alertmanager.yml` |
| **用途** | 告警管理 - 接收和發送告警通知 |
| **Web UI** | http://localhost:9093 |
| **配置檔案** | `docker-compose.monitoring.yml` |

**相關檔案**：
- 數據目錄：`/var/lib/docker/volumes/ai-box_alertmanager_data/_data`
- 配置檔案：`./monitoring/alertmanager/alertmanager.yml`

**依賴關係**：
- 依賴：Prometheus

---

### 13. Node Exporter（系統指標導出）

| 項目 | 配置 |
|------|------|
| **容器名稱** | `aibox-node-exporter` |
| **Image** | `prom/node-exporter:latest` (39.5 MB) |
| **端口** | 9100 |
| **啟動命令** | `./scripts/start_services.sh monitoring` |
| **Bind Mounts** | `/proc → /host/proc` (ro)<br>`/sys → /host/sys` (ro)<br>`/ → /rootfs` (ro) |
| **用途** | 節點指標導出 - 導出系統指標給 Prometheus |
| **指標端點** | http://localhost:9100/metrics |
| **配置檔案** | `docker-compose.monitoring.yml` |

**依賴關係**：
- 被依賴：Prometheus

---

### 14. Redis Exporter（Redis 指標導出）

| 項目 | 配置 |
|------|------|
| **容器名稱** | `aibox-redis-exporter` |
| **Image** | `oliver006/redis_exporter:latest` (13.6 MB) |
| **端口** | 9121 |
| **啟動命令** | `./scripts/start_services.sh monitoring` |
| **環境變數** | `REDIS_ADDR=host.docker.internal:6379` |
| **用途** | Redis 指標導出 - 監控 Redis 性能 |
| **指標端點** | http://localhost:9121/metrics |
| **配置檔案** | `docker-compose.monitoring.yml` |

**依賴關係**：
- 依賴：Redis（host.docker.internal:6379）
- 被依賴：Prometheus

---

## 📁 相關檔案

### Docker Compose 配置檔案

| 檔案 | 用途 | 服務 |
|------|------|------|
| `docker-compose.yml` | 主配置檔案 | Redis、ArangoDB、Qdrant、SeaweedFS、Grafana、Prometheus、Alertmanager |
| `docker-compose.seaweedfs.yml` | AI-Box SeaweedFS 配置 | seaweedfs-ai-box-master/volume/filer |
| `docker-compose.seaweedfs-datalake.yml` | DataLake SeaweedFS 配置 | seaweedfs-datalake-master/volume/filer |
| `docker-compose.monitoring.yml` | 監控系統配置 | Prometheus、Grafana、Alertmanager、Node Exporter、Redis Exporter |
| `docker-compose.prod.yml` | 生產環境配置 | - |

### 監控配置檔案

| 檔案 | 用途 |
|------|------|
| `monitoring/prometheus/prometheus.yml` | Prometheus 配置 |
| `monitoring/prometheus/alerts.yml` | Prometheus 告警規則 |
| `monitoring/alertmanager/alertmanager.yml` | Alertmanager 配置 |
| `monitoring/grafana/grafana.ini` | Grafana 配置 |
| `monitoring/grafana/provisioning/` | Grafana Provisioning 配置 |
| `monitoring/grafana/dashboards/` | Grafana Dashboard 配置 |

### 數據目錄

| 目錄/Volume | 用途 | 容器 |
|------------|------|------|
| `./data/qdrant/` | Qdrant 向量數據 | qdrant |
| `ai-box_arangodb_data` | ArangoDB 數據 | arangodb |
| `ai-box_arangodb_apps_data` | ArangoDB Apps | arangodb |
| `ai-box_redis_data` | Redis 數據 | redis |
| `ai-box_seaweedfs-master-data` | AI-Box SeaweedFS Master | seaweedfs-ai-box-master |
| `ai-box_seaweedfs-volume-data` | AI-Box SeaweedFS Volume | seaweedfs-ai-box-volume |
| `ai-box_seaweedfs-ai-box-s3-config` | AI-Box SeaweedFS S3 配置 | seaweedfs-ai-box-filer |
| `ai-box_seaweedfs-datalake-master-data` | DataLake SeaweedFS Master | seaweedfs-datalake-master |
| `ai-box_seaweedfs-datalake-volume-data` | DataLake SeaweedFS Volume | seaweedfs-datalake-volume |
| `ai-box_seaweedfs-datalake-s3-config` | DataLake SeaweedFS S3 配置 | seaweedfs-datalake-filer |
| `ai-box_prometheus_data` | Prometheus 數據 | aibox-prometheus |
| `ai-box_grafana_data` | Grafana 數據 | aibox-grafana |
| `ai-box_alertmanager_data` | Alertmanager 數據 | aibox-alertmanager |

### 腳本和文檔

| 檔案 | 用途 |
|------|------|
| `scripts/start_services.sh` | 服務啟動腳本 |
| `docs/系统设计文档/核心组件/系統管理/Docker容器整理報告.md` | Docker 容器整理報告 |
| `docs/系统设计文档/核心组件/系統管理/Docker管理說明.md` | 本文檔 |

---

## 🚀 啟動和停止

### 啟動服務

#### 啟動所有服務（依賴順序自動處理）
```bash
./scripts/start_services.sh all
```

啟動順序：
1. **基礎設施**：Redis → ArangoDB → Qdrant
2. **存儲和監控**：SeaweedFS → Buckets → 監控系統
3. **應用服務**：FastAPI → MCP → Frontend → Worker → Dashboard

#### 分類啟動

**基礎設施**：
```bash
./scripts/start_services.sh redis arangodb qdrant
```

**存儲和監控**：
```bash
./scripts/start_services.sh seaweedfs monitoring
```

**單一服務**：
```bash
./scripts/start_services.sh arangodb    # ArangoDB
./scripts/start_services.sh redis       # Redis
./scripts/start_services.sh qdrant      # Qdrant
./scripts/start_services.sh monitoring  # 監控系統
./scripts/start_services.sh seaweedfs   # SeaweedFS (AI-Box + DataLake)
```

### 停止服務

#### 停止所有服務
```bash
./scripts/start_services.sh stop
```

#### 使用 Docker Compose 停止特定服務
```bash
# 停止監控系統
docker-compose -f docker-compose.monitoring.yml down

# 停止 SeaweedFS
docker-compose -f docker-compose.seaweedfs.yml down
docker-compose -f docker-compose.seaweedfs-datalake.yml down
```

### 檢查服務狀態
```bash
./scripts/start_services.sh status
```

---

## 🔧 維護操作

### 備份

#### 數據庫備份
```bash
# ArangoDB 備份
./scripts/backup_arangodb.sh

# Redis 備份
docker exec redis redis-cli BGSAVE

# Qdrant 備份
./scripts/backup_qdrant.sh
```

#### SeaweedFS 備份
```bash
# 創建 SeaweedFS 備份快照
./scripts/backup_seaweedfs.sh
```

#### 監控數據備份
```bash
# 備份 Prometheus 數據
docker cp aibox-prometheus:/prometheus ./backup/prometheus/

# 備份 Grafana 配置
docker cp aibox-grafana:/var/lib/grafana ./backup/grafana/
```

### 更新

#### 更新 Docker Images
```bash
# 拉取最新 Image
docker-compose -f docker-compose.monitoring.yml pull
docker-compose -f docker-compose.seaweedfs.yml pull
docker-compose -f docker-compose.seaweedfs-datalake.yml pull

# 重啟服務
docker-compose -f docker-compose.monitoring.yml up -d
docker-compose -f docker-compose.seaweedfs.yml up -d
docker-compose -f docker-compose.seaweedfs-datalake.yml up -d
```

### 清理

#### 清理未使用的資源
```bash
# 清理已停止的容器
docker container prune -f

# 清理未使用的 Images
docker image prune -a -f

# 清理未使用的 Volumes
docker volume prune -f

# 清理未使用的網絡
docker network prune -f
```

### 日誌管理

#### 查看容器日誌
```bash
# 查看所有容器日誌
docker logs -f arangodb
docker logs -f redis
docker logs -f qdrant
docker logs -f aibox-prometheus
docker logs -f aibox-grafana
docker logs -f aibox-alertmanager

# 查看特定行數
docker logs --tail 100 arangodb

# 查看最近的日誌
docker logs --since 1h arangodb
```

#### 配置日誌輪轉
在 `docker-compose.yml` 中添加：
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## 🔍 故障排除

### 常見問題

#### 1. 容器無法啟動
```bash
# 檢查容器狀態
docker ps -a

# 查看容器日誌
docker logs <container-name>

# 檢查資源使用
docker stats
```

#### 2. 端口被占用
```bash
# 查看端口占用
lsof -i :<port>

# 殺死占用端口的進程
kill -9 <pid>
```

#### 3. 磁盤空間不足
```bash
# 查看 Docker 磁盤使用
docker system df

# 清理未使用的資源
docker system prune -a --volumes
```

#### 4. 網絡連接問題
```bash
# 檢查 Docker 網絡
docker network ls

# 檢查容器網絡
docker inspect <container-name> | grep -A 10 NetworkSettings
```

### 監控系統故障排除

#### Grafana 無法連接 Prometheus
```bash
# 檢查 Prometheus 是否運行
docker ps | grep prometheus

# 檢查 Prometheus 日誌
docker logs aibox-prometheus

# 檢查 Grafana 數據源配置
# 訪問：http://localhost:3001/datasources
```

#### 告警未發送
```bash
# 檢查 Alertmanager 是否運行
docker ps | grep alertmanager

# 檢查 Alertmanager 日誌
docker logs aibox-alertmanager

# 檢查告警規則
# 訪問：http://localhost:9090/alerts
```

---

## 📚 參考文檔

### 內部文檔
- [Docker 容器整理報告](./Docker容器整理報告.md)
- [系統 AI 治理規劃](./AI-Box-系統AI治理規劃.md)
- [數據備份規範](./數據備份規範.md)

### 外部文檔
- [Docker 官方文檔](https://docs.docker.com/)
- [Prometheus 文檔](https://prometheus.io/docs/)
- [Grafana 文檔](https://grafana.com/docs/)
- [ArangoDB 文檔](https://www.arangodb.com/docs/)
- [Qdrant 文檔](https://qdrant.tech/documentation/)
- [SeaweedFS 文檔](https://github.com/chrislusf/seaweedfs)

---

## 📝 更新日誌

| 日期 | 版本 | 變更內容 |
|------|------|----------|
| 2026-01-27 | 1.0 | 初始版本 - 完整記錄所有 14 個容器及相關配置 |

---

**文檔維護者**: AI-Box System Agent  
**下次審查日期**: 2026-02-03
