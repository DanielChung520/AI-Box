# Datalake 測試數據初始化指南

**創建日期**：2026-01-13
**創建人**：Daniel Chung
**最後修改日期**：2026-01-13

## 📋 概述

本指南說明如何初始化 Datalake 測試數據，包括：

1. 檢查 SeaweedFS 服務狀態
2. 確認 Buckets 存在
3. 創建 500+ 筆測試數據

## 🚀 快速開始

### 步驟 1：檢查服務和 Buckets

```bash
# 運行檢查腳本
python scripts/check_datalake_setup.py
```

**檢查內容**：

- ✅ SeaweedFS Master 服務（端口 9334）
- ✅ SeaweedFS Filer API 服務（端口 8889）
- ✅ 必要的 Buckets 是否存在

**預期輸出**：

```
============================================================
🔍 檢查 Datalake SeaweedFS 服務和 Buckets 狀態
============================================================

📋 環境變數配置:
  S3 Endpoint: http://localhost:8889
  Filer Endpoint: http://localhost:8889

🔧 檢查服務狀態:
✅ SeaweedFS Master 服務運行正常: http://localhost:9334/cluster/status
✅ SeaweedFS Filer API 服務運行正常: http://localhost:8889

📦 檢查 Buckets (Filer: http://localhost:8889)...
  ✅ Bucket 'bucket-datalake-assets' 已存在或已創建
  ✅ Bucket 'bucket-datalake-dictionary' 已存在或已創建
  ✅ Bucket 'bucket-datalake-schema' 已存在或已創建

============================================================
✅ 所有檢查通過，可以開始初始化測試數據
============================================================
```

### 步驟 2：初始化測試數據

```bash
# 運行初始化腳本
python scripts/init_datalake_test_data.py
```

**創建內容**：

- 📦 10 個料號的物料數據（10 筆）
- 📊 10 個料號的庫存數據（10 筆）
- 📜 每個料號的庫存歷史記錄（50 筆 × 10 = 500 筆）
- 📚 數據字典（1 筆）
- 📋 Schema 定義（2 筆）

**總計：523 筆數據**

**預期輸出**：

```
🚀 開始初始化 Datalake 測試數據（500+ 筆）...
============================================================
✅ 成功連接到 SeaweedFS Datalake: http://localhost:8889

📦 創建物料數據（10 個料號）...
  ✅ ABC-123: 電子元件 A
  ✅ ABC-124: 電子元件 B
  ...

📊 創建庫存數據（10 個料號）...
  ✅ ABC-123: 庫存 50 (shortage)
  ⚠️  ABC-124: 庫存 30 (low)
  ...

📜 創建庫存歷史記錄（每個料號 50 筆，共 500 筆）...
  ✅ ABC-123: 50 筆歷史記錄
  ✅ ABC-124: 50 筆歷史記錄
  ...

📚 創建數據字典...
  ✅ 數據字典: warehouse.json

📋 創建 Schema 定義...
  ✅ Schema: part_schema.json
  ✅ Schema: stock_schema.json

============================================================
✅ 成功創建: 523 筆數據
📊 數據分布:
   - 物料數據: 10 筆
   - 庫存數據: 10 筆
   - 庫存歷史: 500 筆
   - 數據字典: 1 筆
   - Schema 定義: 2 筆
   - 總計: 523 筆
============================================================
```

## 📊 測試數據結構

### 料號列表

| 料號 | 名稱 | 類別 | 單位 |
|------|------|------|------|
| ABC-123 | 電子元件 A | 電子元件 | PCS |
| ABC-124 | 電子元件 B | 電子元件 | PCS |
| ABC-125 | 機械零件 C | 機械零件 | PCS |
| ABC-126 | 包裝材料 D | 包裝材料 | BOX |
| ABC-127 | 電子元件 E | 電子元件 | PCS |
| ABC-128 | 化學原料 F | 化學原料 | KG |
| ABC-129 | 金屬材料 G | 金屬材料 | KG |
| ABC-130 | 電子元件 H | 電子元件 | PCS |
| ABC-131 | 機械零件 I | 機械零件 | PCS |
| ABC-132 | 包裝材料 J | 包裝材料 | BOX |

### 數據文件結構

```
bucket-datalake-assets/
├── parts/
│   ├── ABC-123.json
│   ├── ABC-124.json
│   └── ... (共 10 個)
├── stock/
│   ├── ABC-123.json
│   ├── ABC-124.json
│   └── ... (共 10 個)
└── stock_history/
    ├── ABC-123.jsonl  (50 筆記錄)
    ├── ABC-124.jsonl  (50 筆記錄)
    └── ... (共 10 個文件，500 筆記錄)

bucket-datalake-dictionary/
└── warehouse.json

bucket-datalake-schema/
├── part_schema.json
└── stock_schema.json
```

## ⚙️ 環境變數配置

確保以下環境變數已設置：

```bash
# Datalake SeaweedFS 配置
export DATALAKE_SEAWEEDFS_S3_ENDPOINT=http://localhost:8889
export DATALAKE_SEAWEEDFS_S3_ACCESS_KEY=your-access-key
export DATALAKE_SEAWEEDFS_S3_SECRET_KEY=your-secret-key
export DATALAKE_SEAWEEDFS_USE_SSL=false
export DATALAKE_SEAWEEDFS_FILER_ENDPOINT=http://localhost:8889
```

或在 `.env` 文件中設置：

```env
DATALAKE_SEAWEEDFS_S3_ENDPOINT=http://localhost:8889
DATALAKE_SEAWEEDFS_S3_ACCESS_KEY=your-access-key
DATALAKE_SEAWEEDFS_S3_SECRET_KEY=your-secret-key
DATALAKE_SEAWEEDFS_USE_SSL=false
DATALAKE_SEAWEEDFS_FILER_ENDPOINT=http://localhost:8889
```

## 🔧 故障排除

### 問題 1：SeaweedFS 服務未運行

**錯誤信息**：

```
❌ SeaweedFS Master 服務無法連接: http://localhost:9334/cluster/status
```

**解決方案**：

1. 確認 SeaweedFS 服務正在運行
2. 檢查端口是否正確（Master: 9334, Filer: 8889）
3. 檢查防火牆設置

### 問題 2：無法創建 Buckets

**錯誤信息**：

```
❌ 無法檢查 Bucket 'bucket-datalake-assets': ...
```

**解決方案**：

1. 確認 Filer API 服務運行正常
2. 檢查訪問權限
3. 手動創建 Buckets：

   ```bash
   curl -X PUT "http://localhost:8889/bucket-datalake-assets"
   curl -X PUT "http://localhost:8889/bucket-datalake-dictionary"
   curl -X PUT "http://localhost:8889/bucket-datalake-schema"
   ```

### 問題 3：無法導入 boto3

**錯誤信息**：

```
❌ 無法導入 S3FileStorage: No module named 'boto3'
```

**解決方案**：

```bash
pip install boto3
```

## 📝 相關文檔

- [模擬-Datalake-規劃書.md](./模擬-Datalake-規劃書.md) - 完整的 Datalake 規劃書
- [庫管員-Agent-規劃書.md](./庫管員-Agent-規劃書.md) - 庫管員 Agent 規劃書
- [SeaweedFS使用指南](../系統管理/SeaweedFS使用指南.md) - SeaweedFS 使用指南

---

**文檔版本**：1.0
**最後更新**：2026-01-13
**維護者**：Daniel Chung
