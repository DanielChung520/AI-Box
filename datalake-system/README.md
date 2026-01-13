# Datalake System

**版本**：1.0
**創建日期**：2026-01-13
**創建人**：Daniel Chung
**最後修改日期**：2026-01-13

## 概述

Datalake System 是獨立的數據湖系統，提供數據存儲、數據字典管理和 Schema 管理功能。

根據 Data-Agent 規格書，**Data Agent 屬於 Datalake 系統（外部系統）**，不屬於 AI-Box。

## 目錄結構

```
datalake-system/
├── data_agent/              # Data Agent 服務代碼
│   ├── __init__.py
│   ├── agent.py             # DataAgent 主類
│   ├── models.py            # 數據模型
│   ├── datalake_service.py  # Datalake 查詢服務
│   ├── dictionary_service.py # 數據字典服務
│   ├── schema_service.py    # Schema 服務
│   ├── text_to_sql.py       # Text-to-SQL 服務
│   ├── query_gateway.py     # 查詢閘道服務
│   └── mcp_server.py        # MCP Server
├── scripts/                 # 服務管理腳本
│   ├── start_data_agent_service.py  # 服務啟動腳本
│   ├── check_environment.py         # 環境配置檢查
│   └── data_agent/          # 啟動和日誌腳本
│       ├── start.sh         # 啟動服務
│       ├── stop.sh          # 停止服務
│       ├── restart.sh       # 重啟服務
│       ├── status.sh        # 查看狀態
│       ├── view_logs.sh     # 查看日誌
│       ├── quick_start.sh   # 快速啟動
│       └── install_dependencies.sh # 安裝依賴
├── tests/                   # 測試文件
│   └── data_agent/
├── logs/                     # 日誌文件（運行時創建）
│   ├── data_agent.log
│   ├── data_agent_error.log
│   └── data_agent.pid
├── requirements.txt          # Python 依賴
├── README.md                 # 本文件
└── QUICK_START.md            # 快速開始指南
```

## 環境配置

### 環境變數位置

環境變數配置在 **AI-Box 項目的 `.env` 文件中**（上層目錄）：

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

### 當前環境狀態

根據您提供的信息：

- ✅ **SeaweedFS Master** - 運行中 (端口 9334)
- ✅ **SeaweedFS Volume** - 運行中
- ✅ **SeaweedFS Filer API** - 運行中 (端口 8889)
- ✅ **SeaweedFS S3 API** - 運行中 (端口 8334)
- ✅ **認證配置** - 在 `.env` 文件中

## 快速開始

### 1. 檢查環境配置

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
python3 scripts/check_environment.py
```

### 2. 安裝依賴

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
./scripts/data_agent/install_dependencies.sh
```

### 3. 啟動服務

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
./scripts/data_agent/start.sh
```

或使用快速啟動腳本：

```bash
./scripts/data_agent/quick_start.sh
```

### 4. 查看日誌

```bash
# 實時查看日誌
./scripts/data_agent/view_logs.sh

# 查看錯誤日誌
./scripts/data_agent/view_logs.sh error
```

## 服務管理

所有腳本位於 `scripts/data_agent/` 目錄：

- `start.sh` - 啟動服務
- `stop.sh` - 停止服務
- `restart.sh` - 重啟服務
- `status.sh` - 查看狀態
- `view_logs.sh` - 查看日誌
- `quick_start.sh` - 快速啟動和觀察
- `install_dependencies.sh` - 安裝依賴

詳細說明請參閱：[QUICK_START.md](./QUICK_START.md)

## 依賴安裝位置

**在 Datalake System 目錄中安裝**：

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
pip install -r requirements.txt
```

或使用安裝腳本：

```bash
./scripts/data_agent/install_dependencies.sh
```

## 架構說明

### 與 AI-Box 的關係

- **Datalake System** 是獨立系統，位於 AI-Box 項目中的 `datalake-system/` 目錄
- **環境變數** 配置在 AI-Box 項目的 `.env` 文件中（共享配置）
- **代碼** 完全獨立，有自己的 `requirements.txt` 和啟動腳本
- **日誌** 存儲在 `datalake-system/logs/` 目錄

### 未來遷移

當 Datalake 項目完全獨立後，可以：

1. 將 `datalake-system/` 目錄遷移到獨立項目
2. 創建獨立的 `.env` 文件
3. 獨立部署和維護

## 相關文檔

- [快速開始指南](./QUICK_START.md)
- [Data-Agent 規格書](../docs/系统设计文档/核心组件/Agent平台/Data-Agent-規格書.md)
- [模擬 Datalake 規劃書](../docs/系统设计文档/核心组件/Agent平台/模擬-Datalake-規劃書.md)
- [SeaweedFS 使用指南](../docs/系统设计文档/核心组件/系統管理/SeaweedFS使用指南.md)
