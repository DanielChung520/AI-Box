# AI-Box v2 部署指南

**代碼功能說明**: AI-Box v2 完整部署指南
**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-29

---

## 概述

本文檔提供 AI-Box v2 平台的完整部署指南，包括環境要求、依賴服務、配置說明、部署步驟與驗證。適用於新環境部署、專案遷移或重裝。

**關聯文檔**:

- [重裝計劃](../重裝計劃.md) - 新環境完整重裝步驟與檢查清單
- [文件編輯-Agent-v2-故障排查](./文件編輯-Agent-v2-故障排查.md) - 故障排查與錯誤碼對照
- [專案端口清單](../系统设计文档/核心组件/系統管理/專案端口清單.md) - 完整端口總覽、配置來源、服務依賴
- [部署架構](../系统设计文档/核心组件/系統管理/部署架构.md) - 架構設計、配置策略（.env 與 system_configs）
- [Docker 管理說明](../系统设计文档/核心组件/系統管理/Docker管理說明.md) - 容器詳情、啟動停止、維護操作

---

## 1. 環境要求

### 1.1 系統要求

- **操作系統**: Linux, macOS, Windows
- **Python 版本**: Python 3.11+（建議 3.12）
- **Node.js**: 前端與部分工具需 Node.js
- **內存**: 至少 4GB RAM（建議 8GB+）
- **存儲**: 至少 10GB 可用空間

### 1.2 前置條件

- 已安裝 **Docker**（含 Docker Compose：`docker-compose` 或 `docker compose`）
- 已安裝 **Python 3.11+**（建議使用 venv）
- 已安裝 **Node.js**（前端與部分工具）
- 專案路徑：`/home/daniel/ai-box`（依實際路徑替換）

---

## 2. 服務與端口清單

> **完整端口清單**：詳見 [專案端口清單](../系统设计文档/核心组件/系統管理/專案端口清單.md)，含配置來源、環境變數、服務依賴與端口衝突檢查腳本。

### 2.1 端口總覽表

| 端口 | 服務 | 所屬系統 | 說明 |
|------|------|----------|------|
| **3000** | AI-Bot 前端 | AI-Box | Vite 開發服務器 |
| **3001** | Grafana | AI-Box 監控 | 監控可視化平台 |
| **5432** | PostgreSQL | AI-Box | 資料庫（docker-compose.qdrant.yml） |
| **6333** | Qdrant REST API | AI-Box | 向量資料庫 REST |
| **6334** | Qdrant gRPC | AI-Box | 向量資料庫 gRPC |
| **6379** | Redis | AI-Box | 快取與 RQ 任務隊列 |
| **8000** | FastAPI API | AI-Box | 後端 API 主服務 |
| **8002** | MCP Server | AI-Box | MCP 協議服務 |
| **8003** | Warehouse Manager Agent | Data-Agent | 庫管員 Agent |
| **8004** | Data Agent | Data-Agent | 數據查詢 Agent |
| **8333** | SeaweedFS AI-Box S3 | AI-Box | AI-Box 文件存儲 S3 |
| **8334** | SeaweedFS Datalake S3 | Datalake | Datalake 文件存儲 S3 |
| **8529** | ArangoDB | AI-Box | 圖資料庫 |
| **8888** | SeaweedFS AI-Box Filer | AI-Box | AI-Box Filer API |
| **8889** | SeaweedFS Datalake Filer | Datalake | Datalake Filer API |
| **9090** | Prometheus | AI-Box 監控 | 監控指標收集 |
| **9093** | Alertmanager | AI-Box 監控 | 告警管理 |
| **9100** | Node Exporter | AI-Box 監控 | 主機資源監控 |
| **9121** | Redis Exporter | AI-Box 監控 | Redis 指標 |
| **9181** | RQ Dashboard | AI-Box | 任務隊列監控介面 |
| **9333** | SeaweedFS AI-Box Master | AI-Box | AI-Box Master API |
| **9334** | SeaweedFS Datalake Master | Datalake | Datalake Master API |
| **11434** | Ollama | AI-Box | 本機 LLM 服務 |
| **8501** | Tiptop Data-Agent Dashboard | Data-Agent | Streamlit 儀表板 |

### 2.2 Docker 容器服務

> **容器詳情**：詳見 [Docker 管理說明](../系统设计文档/核心组件/系統管理/Docker管理說明.md)，含 14 個容器配置、Volume、啟動命令與維護操作。

| 服務                 | 容器名稱        | 端口             | 說明           |
| -------------------- | --------------- | ---------------- | -------------- |
| ArangoDB             | `arangodb`      | 8529             | 圖資料庫       |
| Qdrant               | `qdrant`        | 6333, 6334       | 向量資料庫     |
| Redis                | 依 compose/腳本 | 6379             | 快取與 RQ      |
| SeaweedFS (AI-Box)   | 見下表          | 9333, 8888, 8333 | 文件存儲 S3    |
| SeaweedFS (DataLake) | 見下表          | 9334, 8889, 8334 | DataLake 存儲  |
| 監控（可選）         | 見下表          | 見下表           | Prometheus/Grafana |

**SeaweedFS AI-Box**（`docker-compose.seaweedfs.yml`）:

- `seaweedfs-ai-box-master` — 9333
- `seaweedfs-ai-box-filer` — 8888（Filer）, 8333（S3）

**SeaweedFS DataLake**（`docker-compose.seaweedfs-datalake.yml`）:

- `seaweedfs-datalake-master` — 9334
- `seaweedfs-datalake-filer` — 8889（Filer）, 8334（S3）

**監控**（`docker-compose.monitoring.yml`）:

- `aibox-prometheus` — 9090
- `aibox-grafana` — 3001
- `aibox-alertmanager` — 9093
- `aibox-node-exporter` — 9100
- `aibox-redis-exporter` — 9121

### 2.3 本機進程服務

| 服務         | 端口 | 說明              |
| ------------ | ---- | ----------------- |
| FastAPI      | 8000 | 後端 API          |
| MCP Server   | 8002 | MCP 服務          |
| Frontend     | 3000 | 前端（ai-bot）    |
| RQ Worker    | -    | 任務隊列 Worker   |
| RQ Dashboard | 9181 | RQ 監控介面       |

### 2.4 Docker Compose 配置檔案

| 檔案 | 用途 | 服務 |
|------|------|------|
| `docker-compose.yml` | 主配置 | Redis、ArangoDB、Qdrant |
| `docker-compose.qdrant.yml` | Qdrant 與基礎設施 | Redis、Qdrant、SeaweedFS、API、MCP |
| `docker-compose.seaweedfs.yml` | AI-Box SeaweedFS | Master、Volume、Filer |
| `docker-compose.seaweedfs-datalake.yml` | DataLake SeaweedFS | Master、Volume、Filer |
| `docker-compose.monitoring.yml` | 監控系統 | Prometheus、Grafana、Alertmanager、Exporters |

### 2.5 端口佔用檢查

```bash
# 檢查常用端口（來源：專案端口清單）
for port in 3000 6333 6379 8000 8002 8003 8004 8333 8334 8529 8888 8889 9181 9333 9334 8501; do
  lsof -i :$port 2>/dev/null && echo "端口 $port 已佔用" || echo "端口 $port 可用"
done

# 單一端口檢查
lsof -i :8000
nc -z 127.0.0.1 8000
```

---

## 3. 配置說明

> **配置策略詳解**：詳見 [部署架構](../系统设计文档/核心组件/系統管理/部署架构.md)，含 `.env` 與 ArangoDB `system_configs` 雙層配置、參數詳表與最佳實踐。

### 3.1 環境變量

複製 `env.example` 為 `.env` 並依新環境修改：

```bash
cp env.example .env
```

**關鍵配置項**:

```bash
# 專案配置路徑（必須與實際路徑一致）
AI_BOX_CONFIG_PATH=/home/daniel/ai-box/config/config.json

# 數據庫配置
ARANGO_HOST=localhost
ARANGO_PORT=8529
ARANGO_USER=root
ARANGO_PASSWORD=changeme
ARANGO_DB=ai_box

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379

# systemAdmin 密碼（用於登入與上架腳本）
SYSTEM_ADMIN_PASSWORD=systemAdmin@2026
# 或
SYSTEADMIN_PASSWORD=systemAdmin@2026

# SeaweedFS（若使用 Docker 網路，主機名為容器名）
AI_BOX_SEAWEEDFS_S3_ENDPOINT=http://localhost:8333
AI_BOX_SEAWEEDFS_S3_ACCESS_KEY=admin
AI_BOX_SEAWEEDFS_S3_SECRET_KEY=admin123

# 前端 API 基礎 URL
VITE_API_BASE_URL=http://localhost:8000
```

### 3.2 應用配置

配置文件位置：`config/config.json`。專案已提供預設配置，新環境通常無需修改。

### 3.3 SeaweedFS S3 配置

SeaweedFS Filer 需讀取 S3 設定。專案已提供 `config/seaweedfs/s3.json`（identities: admin / admin123）。若 Filer 啟動失敗，請確認該檔案存在且 compose 已掛載 `./config/seaweedfs:/etc/seaweedfs:ro`。

---

## 4. 部署步驟

### 4.1 階段一：環境與配置

```bash
# 1. 進入專案目錄
cd /home/daniel/ai-box

# 2. 配置 .env
cp env.example .env
# 編輯 .env，確認 AI_BOX_CONFIG_PATH 為正確路徑

# 3. 創建 Python 虛擬環境
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 4. 安裝依賴
pip install -r requirements.txt
# 可選：pip install -r requirements-dev.txt

# 5. 創建 Qdrant 資料目錄
mkdir -p data/qdrant
```

### 4.2 階段二：Docker 基礎設施

**方式一：使用 start_services.sh（推薦）**

```bash
./scripts/start_services.sh redis
./scripts/start_services.sh arangodb
./scripts/start_services.sh qdrant
```

**方式二：使用 Docker Compose**

```bash
# 啟動 Redis、Qdrant、SeaweedFS、API、MCP
docker compose -f docker-compose.qdrant.yml up -d

# 若需 ArangoDB（預設為可選 profile）
docker compose -f docker-compose.qdrant.yml --profile with-arangodb up -d

# 若需 DataLake SeaweedFS
docker compose -f docker-compose.seaweedfs-datalake.yml up -d

# 若需監控
docker compose -f docker-compose.monitoring.yml up -d
```

**若出現「container name already in use」**:

```bash
# 先停止並移除衝突容器（不刪 volume，資料保留）
docker stop qdrant redis seaweedfs-ai-box-master seaweedfs-ai-box-volume seaweedfs-ai-box-filer 2>/dev/null
docker rm qdrant redis seaweedfs-ai-box-master seaweedfs-ai-box-volume seaweedfs-ai-box-filer 2>/dev/null
# 再執行 compose
```

### 4.3 階段三：ArangoDB Schema 與 systemAdmin

```bash
# 1. 運行 Schema 腳本（若專案有提供）
python scripts/migration/create_schema.py

# 2. 初始化 systemAdmin 帳號（新環境必做）
source venv/bin/activate
SYSTEM_ADMIN_PASSWORD="systemAdmin@2026" python scripts/init_system_admin.py
```

**systemAdmin 登入資訊**:

- **用戶名**: `systemAdmin`
- **密碼**: `systemAdmin@2026`（或 `.env` 中 `SYSTEM_ADMIN_PASSWORD`）

### 4.4 階段四：應用服務

```bash
source venv/bin/activate

# 1. 啟動 FastAPI
./scripts/start_services.sh fastapi

# 2. 啟動 MCP Server
./scripts/start_services.sh mcp

# 3. 啟動前端（需先安裝依賴：cd ai-bot && pnpm install）
./scripts/start_services.sh frontend

# 4. 啟動 RQ Worker
./scripts/start_services.sh worker

# 5. 啟動 RQ Dashboard
./scripts/start_services.sh dashboard
```

**一鍵啟動（可選）**:

```bash
./scripts/start_services.sh all
```

### 4.5 啟動服務（開發環境）

```bash
# 開發環境 - FastAPI 熱重載
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 生產環境 - 使用 Gunicorn
gunicorn api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

---

## 5. 驗證部署

### 5.1 狀態檢查

```bash
./scripts/start_services.sh status
```

### 5.2 手動驗證

| 服務     | 驗證方式                                              |
| -------- | ----------------------------------------------------- |
| ArangoDB | 瀏覽 `http://localhost:8529`，使用 root 密碼登入      |
| Qdrant   | 瀏覽 `http://localhost:6333/dashboard`                |
| Redis    | `redis-cli -p 6379 ping` 應回傳 `PONG`                |
| FastAPI  | `curl http://localhost:8000/health` 應回傳 200        |
| 前端     | 瀏覽 `http://localhost:3000`                          |
| 登入     | 使用 systemAdmin / systemAdmin@2026 登入前端          |

### 5.3 健康檢查 API

```bash
# 後端健康檢查
curl http://localhost:8000/health

# API 文檔
# 瀏覽 http://localhost:8000/docs
```

---

## 6. 每日／開機後啟動

**做法一：Docker 為主**

```bash
cd /home/daniel/ai-box

# 1. 啟動 Docker 服務
docker compose -f docker-compose.qdrant.yml up -d
docker compose -f docker-compose.seaweedfs-datalake.yml up -d  # 若需 DataLake

# 2. 啟動本機進程
source venv/bin/activate
./scripts/start_services.sh fastapi
./scripts/start_services.sh frontend
./scripts/start_services.sh worker
./scripts/start_services.sh dashboard
```

**做法二：腳本一鍵**

```bash
cd /home/daniel/ai-box
source venv/bin/activate
./scripts/start_services.sh all
```

---

## 7. 停止服務

> **Docker 維護操作**：詳見 [Docker 管理說明](../系统设计文档/核心组件/系統管理/Docker管理說明.md)，含備份、更新、日誌管理與故障排除。

```bash
# 停止腳本管理的本機進程
./scripts/start_services.sh stop

# 停止 Docker 堆疊（依實際啟動的 compose 執行）
docker compose -f docker-compose.qdrant.yml down
docker compose -f docker-compose.seaweedfs-datalake.yml down
docker compose -f docker-compose.monitoring.yml down
```

`down` 只會停止並移除該 compose 定義的容器，**不刪除 volume**，資料會保留。

---

## 8. 故障排查

### 8.1 登入失敗 ERR_CONNECTION_REFUSED

**症狀**: 前端登入時 `POST http://localhost:8000/api/v1/auth/login net::ERR_CONNECTION_REFUSED`

**原因**: FastAPI 後端未啟動

**解決**:

```bash
source venv/bin/activate
./scripts/start_services.sh fastapi
```

### 8.2 systemAdmin 登入失敗

**症狀**: 用戶名或密碼錯誤

**解決**:

```bash
# 重新初始化 systemAdmin
SYSTEM_ADMIN_PASSWORD="systemAdmin@2026" python scripts/init_system_admin.py
```

若用戶已存在，腳本會跳過建立。需重置密碼時，可透過 API 或直接操作 ArangoDB `system_users` collection。

### 8.3 SeaweedFS Filer 啟動失敗

**症狀**: Filer 容器不斷重啟（Restarting 255）

**原因**: 缺少 S3 設定檔

**解決**: 確認 `config/seaweedfs/s3.json` 存在，且 compose 已掛載 `./config/seaweedfs:/etc/seaweedfs:ro`。

### 8.4 端口衝突

**症狀**: 服務啟動失敗，端口已被佔用

**解決**:

```bash
# 檢查佔用進程
lsof -i :8000

# 腳本會嘗試釋放被佔用端口，但會跳過 Docker 容器佔用的端口
./scripts/start_services.sh fastapi
```

### 8.5 容器故障排除

**Docker 相關問題**：詳見 [Docker 管理說明](../系统设计文档/核心组件/系統管理/Docker管理說明.md) 的「故障排除」章節，含：

- 容器無法啟動
- 端口被佔用
- 磁盤空間不足
- 網絡連接問題
- Grafana 無法連接 Prometheus
- 告警未發送

### 8.6 文件上傳 504 超時

**症狀**: `POST /api/v1/files/v2/upload` 或 `/api/v1/ontologies/import` 返回 504 Gateway Timeout

**解決**: 詳見 [文件上傳_504_超時設定](./文件上傳_504_超時設定.md) — 調整 Nginx `proxy_read_timeout` 或檢查 Cloudflare 限制。

### 8.7 更多故障排查

詳見 [文件編輯-Agent-v2-故障排查](./文件編輯-Agent-v2-故障排查.md) 與 [重裝計劃](../重裝計劃.md)。

---

## 9. 服務依賴關係

```
AI-Box 主系統
├── FastAPI (8000) ← 前端 (3000) 代理 /api 到此
├── MCP Server (8002)
├── Redis (6379)
├── Qdrant (6333, 6334)
├── ArangoDB (8529)
├── SeaweedFS AI-Box (9333, 8333, 8888)
└── Ollama (11434)

模擬 Datalake
└── SeaweedFS Datalake (9334, 8334, 8889)

Data-Agent 體系（可選）
├── Data Agent (8004) ← 依賴 Datalake SeaweedFS
├── Warehouse Manager Agent (8003) ← 依賴 Data Agent (8004)
└── Tiptop Data-Agent Dashboard (8501) ← 依賴 Datalake SeaweedFS
```

> **完整依賴與監控架構**：詳見 [專案端口清單](../系统设计文档/核心组件/系統管理/專案端口清單.md) 第五、六節。

---

## 10. 部署檢查清單

| 步驟 | 項目              | 指令/動作                                      | 完成 |
| ---- | ----------------- | ---------------------------------------------- | ---- |
| 1    | 專案目錄與 .env   | `cd` 專案目錄，配置 `.env`                     | ☐    |
| 2    | Python venv       | `venv` + `pip install -r requirements.txt`     | ☐    |
| 3    | data/qdrant       | `mkdir -p data/qdrant`                         | ☐    |
| 4    | Redis             | `./scripts/start_services.sh redis`            | ☐    |
| 5    | ArangoDB          | `./scripts/start_services.sh arangodb`         | ☐    |
| 6    | Qdrant            | `./scripts/start_services.sh qdrant`           | ☐    |
| 7    | SeaweedFS         | `./scripts/start_services.sh seaweedfs`        | ☐    |
| 8    | ArangoDB Schema   | `python scripts/migration/create_schema.py`    | ☐    |
| 9    | systemAdmin       | `python scripts/init_system_admin.py`           | ☐    |
| 10   | FastAPI           | `./scripts/start_services.sh fastapi`           | ☐    |
| 11   | Frontend          | `./scripts/start_services.sh frontend`         | ☐    |
| 12   | RQ Worker         | `./scripts/start_services.sh worker`           | ☐    |
| 13   | 狀態檢查          | `./scripts/start_services.sh status`           | ☐    |
| 14   | 登入驗證          | systemAdmin / systemAdmin@2026 登入前端         | ☐    |

---

## 11. 參考資料

### 核心文檔

- [重裝計劃](../重裝計劃.md) - 新環境完整重裝步驟
- [專案端口清單](../系统设计文档/核心组件/系統管理/專案端口清單.md) - 完整端口總覽、配置來源、服務依賴
- [部署架構](../系统设计文档/核心组件/系統管理/部署架构.md) - 架構設計、配置策略（.env 與 system_configs）
- [Docker 管理說明](../系统设计文档/核心组件/系統管理/Docker管理說明.md) - 14 個容器詳情、啟動停止、維護操作

### 其他參考

- [Datalake-System 服務部署說明](../../datalake-system/.ds-docs/Datalake-System-服務部署說明.md) - Datalake、Data-Agent、Tiptop、Streamlit Dashboard
- [文件編輯-Agent-v2-故障排查](./文件編輯-Agent-v2-故障排查.md) - 故障排查與錯誤碼
- [開發環境設置指南](../系统设计文档/开发环境设置指南.md) - 開發環境配置
- [SeaweedFS 使用指南](../系统设计文档/核心组件/系統管理/SeaweedFS使用指南.md) - SeaweedFS 配置

---

**最後更新日期**: 2026-01-29
**維護人**: Daniel Chung
