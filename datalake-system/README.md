# Datalake System

**datalake-system 為獨立示範系統**，不依賴 AI-Box 專案。可部署於虛擬機或獨立主機。

## 執行環境

**所有組件統一使用 `datalake-system/venv`**：

| 組件 | 說明 | 端口 |
|------|------|------|
| **Data-Agent** | 自然語言轉 SQL、Datalake 查詢 | 8004 |
| **Dashboard** | Tiptop 模擬系統 Streamlit 儀表板 | 8502 |
| **Datalake** | SeaweedFS S3 數據存儲 | 8334 |
| **MM-Agent** | 庫管員 Agent | 8003 |

### 首次安裝

```bash
cd datalake-system
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 啟動服務（推薦：統一腳本）

使用 `scripts/start_services.sh` 統一管理所有組件：

```bash
cd datalake-system

# 檢查所有服務狀態（預設）
./scripts/start_services.sh
./scripts/start_services.sh status

# 啟動全部服務
./scripts/start_services.sh start

# 個別啟動
./scripts/start_services.sh start data_agent      # Data-Agent
./scripts/start_services.sh start dashboard        # Dashboard
./scripts/start_services.sh start mm_agent # MM-Agent
./scripts/start_services.sh start datalake        # SeaweedFS (Docker)

# 停止服務
./scripts/start_services.sh stop                  # 停止全部
./scripts/start_services.sh stop dashboard        # 僅停止 Dashboard

# 重啟服務
./scripts/start_services.sh restart all
./scripts/start_services.sh restart data_agent
```

**注意**：Datalake (SeaweedFS) 為 Docker 服務，`stop datalake` 不會自動停止，需手動執行 `docker-compose down`。

### 個別組件啟動（進階）

各組件亦可單獨啟動，腳本會自動啟用 `datalake-system/venv`（若存在）：

| 組件 | 啟動腳本 | 狀態檢查 |
|------|----------|----------|
| Data-Agent | `./scripts/data_agent/start.sh` | `./scripts/data_agent/status.sh` |
| Dashboard | `./scripts/start_services.sh start dashboard` | `./scripts/start_services.sh status` |
| MM-Agent | `./scripts/mm_agent/start.sh` | `./scripts/mm_agent/status.sh` |

---

## 目錄結構

```
datalake-system/
├── venv/                    # 統一虛擬環境（所有組件共用）
├── data_agent/              # Data Agent 服務
├── dashboard/               # Tiptop Dashboard
├── mm_agent/                # MM-Agent（庫管員 Agent）
├── scripts/                 # 啟動腳本
│   ├── start_services.sh    # 統一服務管理（推薦）
│   ├── data_agent/          # Data-Agent 啟動腳本
│   └── mm_agent/            # MM-Agent 啟動腳本
├── logs/                    # 日誌（運行時創建）
├── metadata/                # Schema 等
└── .ds-docs/                # 文檔
```

---

**詳細文檔**：`.ds-docs/Datalake/README.md`
