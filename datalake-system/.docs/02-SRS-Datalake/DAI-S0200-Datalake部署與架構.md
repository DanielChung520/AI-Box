# DAI-S0200 Datalake 部署與架構規格書

**文件編號**: DAI-S0200  
**版本**: 1.0  
**日期**: 2026-01-29  
**依據代碼**: `datalake-system/datalake/`

---

# Datalake System 服務部署說明

**代碼功能說明**: Datalake System 獨立與模擬環境的完整服務部署指南
**創建日期**: 2026-01-29
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-29

---

## 概述

本文檔說明 Datalake System 的服務部署，包含：

1. **Datalake（SeaweedFS）**：獨立部署與模擬環境
2. **Data-Agent**：數據查詢服務（端口 8004）
3. **Tiptop 庫管員 Agent**：業務 Agent（端口 8003）
4. **Tiptop 資料初始化**：測試數據與 Buckets
5. **Tiptop Dashboard**：Streamlit 儀表板（端口 8501）

**架構關係**：

```
AI-Box (8000) ← 前端、Orchestrator
    ↓
Tiptop 庫管員 Agent (8003) ← 依賴 Data Agent、AI-Box Orchestrator
    ↓
Data-Agent (8004) ← 依賴 Datalake SeaweedFS
    ↓
SeaweedFS Datalake (9334, 8889, 8334)
```

---

## 1. Datalake（SeaweedFS）部署

### 1.1 獨立 vs 模擬

| 模式 | 說明 | 適用場景 |
|------|------|----------|
| **模擬** | 與 AI-Box 同機部署，使用 Docker Compose | 開發、測試、演示 |
| **獨立** | 獨立機器或 K8s 集群部署 | 生產環境、企業數據隔離 |

### 1.2 模擬環境部署（Docker Compose）

**前置條件**：AI-Box 專案根目錄、Docker 已安裝。

```bash
# 進入 AI-Box 專案根目錄
cd /home/daniel/ai-box

# 啟動 Datalake SeaweedFS（3 個容器）
docker compose -f docker-compose.seaweedfs-datalake.yml up -d
```

**容器與端口**：

| 容器名稱 | 端口 | 說明 |
|----------|------|------|
| `seaweedfs-datalake-master` | 9334 | Master API |
| `seaweedfs-datalake-volume` | - | 存儲節點 |
| `seaweedfs-datalake-filer` | 8889（Filer）, 8334（S3） | Filer API、S3 API |

**驗證**：

```bash
# 檢查容器狀態
docker ps | grep seaweedfs-datalake

# 檢查 Master
curl http://localhost:9334/cluster/status

# 檢查 Filer
curl http://localhost:8889
```

### 1.3 環境變數配置

在 AI-Box 專案根目錄的 `.env` 中配置：

```bash
# Datalake SeaweedFS 配置
DATALAKE_SEAWEEDFS_S3_ENDPOINT=http://localhost:8334
DATALAKE_SEAWEEDFS_S3_ACCESS_KEY=admin
DATALAKE_SEAWEEDFS_S3_SECRET_KEY=admin123
DATALAKE_SEAWEEDFS_USE_SSL=false
DATALAKE_SEAWEEDFS_FILER_ENDPOINT=http://localhost:8889

# Data Agent 預設 Bucket（新架構 Parquet 用）
DATALAKE_DEFAULT_BUCKET=tiptop-raw
```

**注意**：S3 API 使用 8334，Filer API 使用 8889。部分腳本可能使用 Filer 端點，請依實際腳本說明調整。

### 1.4 S3 配置檔

SeaweedFS Filer 需讀取 S3 設定。專案已提供 `config/seaweedfs/s3.json`（identities: admin / admin123）。若 Filer 啟動失敗，請確認：

- `config/seaweedfs/s3.json` 存在
- `docker-compose.seaweedfs-datalake.yml` 已掛載 `./config/seaweedfs:/etc/seaweedfs:ro`

---

## 2. Buckets 與資料初始化

### 2.1 創建 Buckets

**方式一：使用遷移腳本（推薦）**

```bash
cd /home/daniel/ai-box
source venv/bin/activate

# 創建 Datalake 相關 Buckets
python scripts/migration/create_seaweedfs_buckets.py --service datalake

# 或創建所有 Buckets（含 AI-Box）
python scripts/migration/create_seaweedfs_buckets.py --service all
```

**方式二：手動創建**

```bash
# 使用 Filer API 創建
curl -X PUT "http://localhost:8889/bucket-datalake-assets"
curl -X PUT "http://localhost:8889/bucket-datalake-dictionary"
curl -X PUT "http://localhost:8889/bucket-datalake-schema"

# 若使用新架構（Parquet），需創建 tiptop-raw
curl -X PUT "http://localhost:8889/tiptop-raw"
```

**Datalake Buckets 清單**：

| Bucket | 用途 |
|--------|------|
| `bucket-datalake-assets` | 物料、庫存等業務數據（JSON/JSONL） |
| `bucket-datalake-dictionary` | 數據字典定義 |
| `bucket-datalake-schema` | Schema 定義 |
| `tiptop-raw` | 新架構 Parquet 數據（可選） |

### 2.2 檢查 Datalake 環境

```bash
cd /home/daniel/ai-box
source venv/bin/activate

# 檢查 SeaweedFS 服務與 Buckets
python scripts/check_datalake_setup.py
```

### 2.3 初始化測試數據（523 筆）

```bash
cd /home/daniel/ai-box
source venv/bin/activate

# 初始化 500+ 筆測試數據（物料、庫存、歷史、字典、Schema）
python scripts/init_datalake_test_data.py
```

**創建內容**：

- 10 個料號的物料數據
- 10 個料號的庫存數據
- 每個料號 50 筆庫存歷史（共 500 筆）
- 數據字典、Schema 定義

**或使用上傳腳本**（若本地有 `scripts/datalake_test_data/` 目錄）：

```bash
python scripts/upload_datalake_test_data.py
# 或
python scripts/upload_datalake_test_data_filer.py
```

### 2.4 Tiptop 新架構數據（Parquet）

若使用 Parquet 新架構，需執行 `master_data_gen.py` 與 `transactional_data_gen.py`：

```bash
cd /home/daniel/ai-box/datalake-system
source ../venv/bin/activate  # 或專案 venv

# 生成主數據
python scripts/master_data_gen.py

# 生成交易數據
python scripts/transactional_data_gen.py
```

詳見 [Data-Agent-測試計劃.md](./Data-Agent-測試計劃.md)。

---

## 3. Data-Agent 部署

### 3.1 依賴安裝

```bash
cd /home/daniel/ai-box/datalake-system

# 安裝 Datalake System 專用依賴
pip install -r requirements.txt

# 或使用安裝腳本
./scripts/data_agent/install_dependencies.sh
```

### 3.2 環境檢查

```bash
cd /home/daniel/ai-box/datalake-system
python scripts/check_environment.py
```

**預期**：Datalake SeaweedFS 可連、Data Agent 配置已設、Python 依賴已安裝。

### 3.3 啟動 Data-Agent

```bash
cd /home/daniel/ai-box/datalake-system

# 方式一：使用腳本
./scripts/data_agent/start.sh

# 方式二：使用專案根目錄腳本
cd /home/daniel/ai-box
python scripts/start_data_agent_service.py
```

### 3.4 服務管理

| 腳本 | 用途 |
|------|------|
| `./scripts/data_agent/start.sh` | 啟動 |
| `./scripts/data_agent/stop.sh` | 停止 |
| `./scripts/data_agent/restart.sh` | 重啟 |
| `./scripts/data_agent/status.sh` | 狀態 |
| `./scripts/data_agent/view_logs.sh` | 日誌 |
| `./scripts/data_agent/quick_start.sh` | 快速啟動並觀察 |

### 3.5 驗證

```bash
# 健康檢查
curl http://localhost:8004/health

# 或
./scripts/data_agent/status.sh
```

---

## 4. Tiptop 庫管員 Agent 部署

### 4.1 前置條件

- Data-Agent 已啟動（8004）
- AI-Box FastAPI 已啟動（8000，Orchestrator）
- Datalake 測試數據已初始化

### 4.2 啟動庫管員 Agent

```bash
cd /home/daniel/ai-box/datalake-system

# 使用腳本
./scripts/warehouse_manager_agent/start.sh
```

### 4.3 服務管理

| 腳本 | 用途 |
|------|------|
| `./scripts/warehouse_manager_agent/start.sh` | 啟動 |
| `./scripts/warehouse_manager_agent/stop.sh` | 停止 |
| `./scripts/warehouse_manager_agent/restart.sh` | 重啟 |
| `./scripts/warehouse_manager_agent/status.sh` | 狀態 |
| `./scripts/warehouse_manager_agent/view_logs.sh` | 日誌 |

### 4.4 驗證

```bash
curl http://localhost:8003/health
```

---

## 5. Tiptop Dashboard（Streamlit）安裝與啟動

### 5.1 安裝 Streamlit

```bash
cd /home/daniel/ai-box/datalake-system
pip install streamlit pandas plotly httpx
```

或確認 `requirements.txt` 已含上述依賴後執行：

```bash
pip install -r requirements.txt
```

### 5.2 啟動 Dashboard

```bash
cd /home/daniel/ai-box/datalake-system
source ../venv/bin/activate  # 或專案 venv

# 從 scripts 目錄執行（tiptop_dashboard.py 會 import data_access）
cd scripts
streamlit run tiptop_dashboard.py --server.port=8501
```

**或從專案根目錄**：

```bash
cd /home/daniel/ai-box
source venv/bin/activate
cd datalake-system/scripts
streamlit run tiptop_dashboard.py --server.port=8501
```

### 5.3 訪問

瀏覽 `http://localhost:8501`。

### 5.4 依賴說明

- **DataLakeClient**：`scripts/data_access.py`，需能連接 Datalake SeaweedFS
- **Data-Agent**：Dashboard 會呼叫 Data-Agent API（8004）進行自然語言查詢
- **環境變數**：從 AI-Box 根目錄 `.env` 載入（`DATA_AGENT_SERVICE_PORT`、`DATALAKE_SEAWEEDFS_*`）

---

## 6. 部署檢查清單

| 步驟 | 項目 | 指令/動作 | 完成 |
|------|------|-----------|------|
| 1 | SeaweedFS Datalake | `docker compose -f docker-compose.seaweedfs-datalake.yml up -d` | ☐ |
| 2 | .env 配置 | 設定 `DATALAKE_SEAWEEDFS_*`、`DATA_AGENT_SERVICE_*` | ☐ |
| 3 | Buckets | `python scripts/migration/create_seaweedfs_buckets.py --service datalake` | ☐ |
| 4 | 檢查環境 | `python scripts/check_datalake_setup.py` | ☐ |
| 5 | 測試數據 | `python scripts/init_datalake_test_data.py` | ☐ |
| 6 | Data-Agent 依賴 | `cd datalake-system && pip install -r requirements.txt` | ☐ |
| 7 | Data-Agent | `./scripts/data_agent/start.sh` | ☐ |
| 8 | 庫管員 Agent | `./scripts/warehouse_manager_agent/start.sh` | ☐ |
| 9 | Streamlit | `pip install streamlit pandas plotly httpx` | ☐ |
| 10 | Tiptop Dashboard | `cd scripts && streamlit run tiptop_dashboard.py --server.port=8501` | ☐ |
| 11 | 驗證 | `curl localhost:8004/health`、`curl localhost:8003/health`、訪問 8501 | ☐ |

---

## 7. 端口總覽

| 端口 | 服務 | 說明 |
|------|------|------|
| 8003 | Warehouse Manager Agent | 庫管員 Agent |
| 8004 | Data-Agent | 數據查詢服務 |
| 8334 | SeaweedFS Datalake S3 | S3 API |
| 8501 | Tiptop Dashboard | Streamlit 儀表板 |
| 8889 | SeaweedFS Datalake Filer | Filer API |
| 9334 | SeaweedFS Datalake Master | Master API |

---

## 8. 故障排除

### 8.1 SeaweedFS Filer 啟動失敗

**症狀**：Filer 容器不斷重啟（Restarting 255）

**解決**：確認 `config/seaweedfs/s3.json` 存在，且 compose 已掛載 `./config/seaweedfs:/etc/seaweedfs:ro`。

### 8.2 Data-Agent 無法連接 Datalake

**檢查**：

```bash
python scripts/check_environment.py
cat ../.env | grep DATALAKE_SEAWEEDFS
```

確認 `DATALAKE_SEAWEEDFS_S3_ENDPOINT` 為 `http://localhost:8334`（S3）或依腳本使用 Filer `http://localhost:8889`。

### 8.3 庫管員 Agent 查詢失敗

**原因**：Data-Agent 未啟動或 Datalake 無測試數據。

**解決**：先啟動 Data-Agent，再執行 `init_datalake_test_data.py`。

### 8.4 Streamlit 無法 import data_access

**原因**：工作目錄錯誤，`data_access.py` 在 `scripts/` 下。

**解決**：從 `datalake-system/scripts/` 目錄執行 `streamlit run tiptop_dashboard.py`。

---

## 9. 相關文檔

- [Datalake-測試數據初始化指南](./Datalake-測試數據初始化指南.md)
- [Data-Agent 規格書](./Data-Agent-規格書.md)
- [Data-Agent 測試計劃](./Data-Agent-測試計劃.md)
- [ENVIRONMENT.md](./ENVIRONMENT.md) - 環境配置
- [README.md](./README.md) - Datalake System 概述
- [QUICK_START.md](./QUICK_START.md) - 快速開始
- [模擬-Datalake-規劃書](../../../docs/系统设计文档/核心组件/Agent平台/模擬-Datalake-規劃書.md)
- [SeaweedFS 使用指南](../../../docs/系统设计文档/核心组件/系統管理/SeaweedFS使用指南.md)

---

**最後更新日期**: 2026-01-29
**維護人**: Daniel Chung
