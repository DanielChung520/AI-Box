# Tiptop 模擬系統 Dashboard

**版本**：1.0  
**創建日期**：2026-01-29  
**端口**：8502

## 概述

Streamlit 儀表板，展現 Data-Agent 自然語言查詢與 Tiptop 數據湖分析能力。

## 目錄結構

```
dashboard/
├── app.py              # Streamlit 主程式
├── config.py           # 配置（路徑、URL、端口）
├── services/
│   ├── data_access.py  # DataLakeClient
│   └── data_agent_client.py  # Data-Agent HTTP 調用
├── start.sh            # 啟動腳本
└── README.md
```

## 獨立部署說明

**datalake-system 為獨立示範系統**。Data-Agent、Dashboard、Datalake、Warehouse Manager Agent 均使用 `datalake-system/venv`。可部署於虛擬機或獨立主機。

### 執行環境

| 方式 | 說明 |
|------|------|
| **datalake-system/venv** | 若有 `datalake-system/venv/`，start.sh 會自動啟用 |
| **全局 Python** | 若無 venv，直接使用系統 `python3` / `streamlit` |

### 首次安裝（建立 venv）

```bash
cd datalake-system
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 啟動

```bash
# 從 datalake-system 目錄
./dashboard/start.sh

# 或直接（需已安裝 streamlit）
streamlit run dashboard/app.py --server.port=8502
```

## 依賴

- SeaweedFS S3 (端口 8334)
- Data-Agent (端口 8004)
- streamlit, pandas, plotly, httpx, boto3

## 規格

詳見 [Tiptop模擬系統Dashboard規格書](../.ds-docs/TipTop模擬系統Dashboard/Tiptop模擬系統Dashboard規格書.md)
