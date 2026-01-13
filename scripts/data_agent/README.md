# Data Agent 服務管理腳本

## 概述

此目錄包含 Data Agent 獨立服務的管理腳本，用於啟動、停止、重啟服務以及查看日誌。

## 腳本說明

### 1. start.sh - 啟動服務

啟動 Data Agent 服務並在後台運行。

```bash
./scripts/data_agent/start.sh
```

**功能：**

- 檢查服務是否已運行
- 檢查 Python 環境和依賴
- 啟動服務並記錄 PID
- 將日誌輸出到 `logs/data_agent/data_agent.log`

### 2. stop.sh - 停止服務

停止正在運行的 Data Agent 服務。

```bash
./scripts/data_agent/stop.sh
```

**功能：**

- 優雅地停止服務（SIGTERM）
- 如果服務未響應，強制終止（SIGKILL）
- 清理 PID 文件

### 3. restart.sh - 重啟服務

重啟 Data Agent 服務。

```bash
./scripts/data_agent/restart.sh
```

**功能：**

- 先停止服務
- 等待 2 秒
- 重新啟動服務

### 4. status.sh - 查看服務狀態

查看 Data Agent 服務的運行狀態。

```bash
./scripts/data_agent/status.sh
```

**顯示信息：**

- 服務運行狀態
- 進程 ID (PID)
- 進程詳細信息
- 端口監聽狀態
- 健康檢查結果
- 日誌文件信息

### 5. view_logs.sh - 查看日誌

查看 Data Agent 服務的日誌。

```bash
# 實時查看日誌（默認）
./scripts/data_agent/view_logs.sh

# 查看最後 100 行
./scripts/data_agent/view_logs.sh last 100

# 查看錯誤日誌
./scripts/data_agent/view_logs.sh error

# 搜索日誌
./scripts/data_agent/view_logs.sh search "query_datalake" 50

# 查看日誌統計
./scripts/data_agent/view_logs.sh stats
```

**模式說明：**

- `tail` / `follow` / `f` - 實時查看日誌（默認）
- `last` / `l [行數]` - 查看最後 N 行（默認 50 行）
- `all` / `a` - 查看完整日誌
- `error` / `e [行數]` - 查看錯誤日誌（默認 50 行）
- `search` / `s <關鍵字> [行數]` - 搜索日誌
- `stats` / `stat` - 顯示日誌統計信息

## 使用示例

### 啟動服務

```bash
cd /Users/daniel/GitHub/AI-Box
./scripts/data_agent/start.sh
```

### 查看服務狀態

```bash
./scripts/data_agent/status.sh
```

### 實時查看日誌

```bash
./scripts/data_agent/view_logs.sh
```

### 查看錯誤日誌

```bash
./scripts/data_agent/view_logs.sh error
```

### 重啟服務

```bash
./scripts/data_agent/restart.sh
```

### 停止服務

```bash
./scripts/data_agent/stop.sh
```

## 日誌文件位置

- **日誌文件**: `logs/data_agent/data_agent.log`
- **PID 文件**: `logs/data_agent/data_agent.pid`

## 環境變數

服務使用以下環境變數（可在 `.env` 文件中配置）：

- `DATA_AGENT_SERVICE_HOST` - 服務主機地址（默認: localhost）
- `DATA_AGENT_SERVICE_PORT` - 服務端口（默認: 8004）
- `DATALAKE_SEAWEEDFS_S3_ENDPOINT` - SeaweedFS S3 端點
- `DATALAKE_SEAWEEDFS_S3_ACCESS_KEY` - SeaweedFS S3 Access Key
- `DATALAKE_SEAWEEDFS_S3_SECRET_KEY` - SeaweedFS S3 Secret Key

## 健康檢查

服務啟動後，可以通過以下方式檢查服務健康狀態：

```bash
# 使用 curl
curl http://localhost:8004/health

# 使用 status.sh 腳本
./scripts/data_agent/status.sh
```

## 故障排除

### 服務無法啟動

1. 檢查 Python 環境：

   ```bash
   python3 --version
   ```

2. 檢查依賴：

   ```bash
   python3 -c "import fastapi, uvicorn"
   ```

3. 查看日誌：

   ```bash
   ./scripts/data_agent/view_logs.sh error
   ```

### 端口被占用

如果端口 8004 已被占用，可以：

1. 修改 `.env` 文件中的 `DATA_AGENT_SERVICE_PORT`
2. 或停止占用端口的進程

### 服務無響應

1. 檢查服務狀態：

   ```bash
   ./scripts/data_agent/status.sh
   ```

2. 重啟服務：

   ```bash
   ./scripts/data_agent/restart.sh
   ```

3. 查看錯誤日誌：

   ```bash
   ./scripts/data_agent/view_logs.sh error
   ```

## 注意事項

1. 確保 SeaweedFS Datalake 服務已啟動
2. 確保環境變數已正確配置
3. 日誌文件會持續增長，建議定期清理或使用日誌輪轉
4. 生產環境建議使用 systemd 或 supervisor 管理服務

## 相關文檔

- [Data-Agent 規格書](../../../docs/系统设计文档/核心组件/Agent平台/Data-Agent-規格書.md)
- [SeaweedFS 使用指南](../../../docs/系统设计文档/核心组件/系統管理/SeaweedFS使用指南.md)

### 6. quick_start.sh - 快速啟動和觀察

快速啟動服務並顯示狀態和日誌（適合初次使用）。

```bash
./scripts/data_agent/quick_start.sh
```

**功能：**

- 檢查服務狀態
- 如果服務未運行，自動啟動
- 顯示服務狀態
- 顯示最後 20 行日誌
- 提供使用提示

## 快速開始

### 第一次使用

```bash
cd /Users/daniel/GitHub/AI-Box
./scripts/data_agent/quick_start.sh
```

這會自動啟動服務並顯示狀態和日誌。

### 日常使用

```bash
# 啟動服務
./scripts/data_agent/start.sh

# 實時查看日誌（在另一個終端）
./scripts/data_agent/view_logs.sh

# 查看服務狀態
./scripts/data_agent/status.sh

# 停止服務
./scripts/data_agent/stop.sh
```

## 日誌文件

- **標準日誌**: `logs/data_agent/data_agent.log` - 服務標準輸出
- **錯誤日誌**: `logs/data_agent/data_agent_error.log` - 服務錯誤輸出
- **PID 文件**: `logs/data_agent/data_agent.pid` - 進程 ID 記錄

## 依賴安裝

### 自動安裝（推薦）

```bash
./scripts/data_agent/install_dependencies.sh
```

此腳本會自動安裝：

- FastAPI 和 uvicorn（HTTP 服務）
- boto3（SeaweedFS S3 API）
- jsonschema（Schema 驗證）

### 手動安裝

```bash
# 安裝核心依賴
pip install fastapi uvicorn boto3 jsonschema

# 或安裝所有項目依賴
pip install -r requirements.txt
```

## 常見問題

### 1. ModuleNotFoundError: No module named 'botocore'

**原因**: 缺少 boto3 依賴

**解決方法**:

```bash
pip install boto3
# 或運行
./scripts/data_agent/install_dependencies.sh
```

### 2. ModuleNotFoundError: No module named 'fastapi'

**原因**: 缺少 FastAPI 依賴

**解決方法**:

```bash
pip install fastapi uvicorn
# 或運行
./scripts/data_agent/install_dependencies.sh
```

## 重要說明：部署位置

### 架構定位

根據 Data-Agent 規格書，**Data Agent 屬於 Datalake 系統（外部系統）**，不屬於 AI-Box。

### 當前狀態

目前 Data Agent 代碼位於 AI-Box 項目中，這是**臨時位置**。未來應該遷移到獨立的 Datalake 項目。

### 依賴安裝位置

**當前方案**：在 AI-Box 項目中安裝（因為代碼目前在 AI-Box 中）

```bash
cd /Users/daniel/GitHub/AI-Box
./scripts/data_agent/install_dependencies.sh
```

**未來方案**：在獨立的 Datalake 項目中安裝

```bash
cd /path/to/datalake-system
pip install -r requirements.txt
```

詳細說明請參閱：[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
