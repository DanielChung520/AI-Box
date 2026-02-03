# Datalake System 快速開始指南

**版本**：1.0
**創建日期**：2026-01-13
**創建人**：Daniel Chung

## 概述

**datalake-system 為獨立示範系統**。Data-Agent、Dashboard、Datalake、Warehouse Manager Agent 均使用 `datalake-system/venv`。

Datalake System 包含 Data Agent 服務，提供數據查詢、數據字典管理和 Schema 管理功能。

## 環境確認

### 1. 確認 SeaweedFS Datalake 服務運行

```bash
# 檢查 SeaweedFS 服務狀態
docker ps | grep seaweedfs-datalake

# 應該看到：
# - seaweedfs-datalake-master (端口 9334)
# - seaweedfs-datalake-volume
# - seaweedfs-datalake-filer (端口 8889, S3 API: 8334)
```

### 2. 確認環境變數配置

環境變數配置在 AI-Box 項目的 `.env` 文件中：

```bash
# Datalake SeaweedFS 配置
DATALAKE_SEAWEEDFS_S3_ENDPOINT=http://localhost:8334
DATALAKE_SEAWEEDFS_S3_ACCESS_KEY=admin
DATALAKE_SEAWEEDFS_S3_SECRET_KEY=admin123
DATALAKE_SEAWEEDFS_USE_SSL=false
DATALAKE_SEAWEEDFS_FILER_ENDPOINT=http://localhost:8889

# Data Agent Service 配置
DATA_AGENT_SERVICE_HOST=localhost
DATA_AGENT_SERVICE_PORT=8004
AI_BOX_API_URL=http://localhost:8000
```

## 快速開始

### 步驟 1：檢查環境配置

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
python3 scripts/check_environment.py
```

### 步驟 2：安裝依賴

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
./scripts/data_agent/install_dependencies.sh
```

### 步驟 3：啟動服務

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
./scripts/data_agent/start.sh
```

或使用快速啟動腳本（自動檢查並啟動）：

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
./scripts/data_agent/quick_start.sh
```

### 步驟 4：查看日誌

```bash
# 實時查看日誌
./scripts/data_agent/view_logs.sh

# 查看錯誤日誌
./scripts/data_agent/view_logs.sh error
```

## 服務管理

### 啟動服務

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
./scripts/data_agent/start.sh
```

### 停止服務

```bash
./scripts/data_agent/stop.sh
```

### 重啟服務

```bash
./scripts/data_agent/restart.sh
```

### 查看狀態

```bash
./scripts/data_agent/status.sh
```

### 查看日誌

```bash
# 實時查看
./scripts/data_agent/view_logs.sh

# 查看最後 100 行
./scripts/data_agent/view_logs.sh last 100

# 查看錯誤
./scripts/data_agent/view_logs.sh error

# 搜索日誌
./scripts/data_agent/view_logs.sh search "query_datalake" 50
```

## 目錄結構

```
datalake-system/
├── data_agent/              # Data Agent 服務代碼
│   ├── agent.py
│   ├── datalake_service.py
│   ├── dictionary_service.py
│   ├── schema_service.py
│   └── ...
├── scripts/                 # 服務管理腳本
│   ├── start_data_agent_service.py
│   ├── check_environment.py
│   └── data_agent/          # 啟動和日誌腳本
│       ├── start.sh
│       ├── stop.sh
│       ├── status.sh
│       ├── view_logs.sh
│       └── ...
├── logs/                    # 日誌文件（運行時創建）
│   ├── data_agent.log
│   ├── data_agent_error.log
│   └── data_agent.pid
├── requirements.txt         # Python 依賴
└── README.md               # 說明文檔
```

## 環境變數說明

所有環境變數配置在 AI-Box 項目的 `.env` 文件中：

| 變數名 | 說明 | 默認值 | 必需 |
|--------|------|--------|------|
| `DATALAKE_SEAWEEDFS_S3_ENDPOINT` | SeaweedFS S3 API 端點 | `http://localhost:8334` | ✅ |
| `DATALAKE_SEAWEEDFS_S3_ACCESS_KEY` | S3 Access Key | - | ✅ |
| `DATALAKE_SEAWEEDFS_S3_SECRET_KEY` | S3 Secret Key | - | ✅ |
| `DATALAKE_SEAWEEDFS_USE_SSL` | 是否使用 SSL | `false` | ❌ |
| `DATALAKE_SEAWEEDFS_FILER_ENDPOINT` | Filer API 端點 | `http://localhost:8889` | ❌ |
| `DATA_AGENT_SERVICE_HOST` | 服務主機地址 | `localhost` | ❌ |
| `DATA_AGENT_SERVICE_PORT` | 服務端口 | `8004` | ❌ |

## 健康檢查

服務啟動後，可以通過以下方式檢查：

```bash
# 使用 curl
curl http://localhost:8004/health

# 使用 status.sh 腳本
./scripts/data_agent/status.sh
```

## 故障排除

### 環境配置檢查失敗

運行環境檢查腳本查看詳細信息：

```bash
python3 scripts/check_environment.py
```

### 依賴未安裝

```bash
./scripts/data_agent/install_dependencies.sh
```

### 服務無法啟動

1. 檢查日誌：

   ```bash
   ./scripts/data_agent/view_logs.sh error
   ```

2. 檢查 SeaweedFS 服務：

   ```bash
   docker ps | grep seaweedfs-datalake
   ```

3. 檢查環境變數：

   ```bash
   cat ../.env | grep DATALAKE_SEAWEEDFS
   ```

詳細故障排除請參閱：[scripts/data_agent/TROUBLESHOOTING.md](./scripts/data_agent/TROUBLESHOOTING.md)
