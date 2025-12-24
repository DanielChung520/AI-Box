# 監控與日誌文檔（WBS-2.4）

## 概述

本文檔說明 AI-Box API 的監控與日誌配置，使用 Prometheus 收集指標，Grafana 進行可視化。

## 架構

- **Prometheus**: 時間序列數據庫，用於收集和存儲指標
- **Grafana**: 可視化儀表板，用於展示監控數據
- **Prometheus Client**: Python 客戶端庫，用於在應用中暴露指標

## 指標說明

### HTTP 指標

- `http_requests_total`: HTTP 請求總數（按方法、端點、狀態碼分類）
- `http_request_duration_seconds`: HTTP 請求處理時間（直方圖）
- `http_requests_in_progress`: 正在處理中的請求數
- `active_connections`: 當前活躍連接數

### 業務指標

- `file_uploads_total`: 文件上傳總數（按狀態分類）
- `file_upload_size_bytes`: 文件上傳大小（直方圖）

## 安裝與配置

### 1. 安裝依賴

```bash
pip install prometheus-client>=0.19.0
```

### 2. Prometheus 配置

複製 `prometheus.yml` 到 Prometheus 配置目錄，並根據實際部署情況修改 `targets`。

### 3. Grafana 配置

1. 在 Grafana 中添加 Prometheus 數據源
2. 導入 `grafana-dashboard.json` 創建儀表板

### 4. 啟動服務

```bash
# 啟動 AI-Box API（已自動暴露 /metrics 端點）
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 啟動 Prometheus（如果未使用容器化部署）
prometheus --config.file=docs/monitoring/prometheus.yml
```

## 訪問端點

- **Metrics**: `http://localhost:8000/metrics`
- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3000`

## 告警規則

可以根據需要在 Prometheus 中配置告警規則，例如：

- 錯誤率 > 5%
- 請求延遲 P95 > 1s
- 活躍連接數 > 1000

## 日誌管理

應用使用 `structlog` 進行結構化日誌記錄，日誌格式為 JSON，便於日誌聚合系統（如 ELK、Loki）處理。

創建日期: 2025-12-18
創建人: Daniel Chung
最後修改日期: 2025-12-18
