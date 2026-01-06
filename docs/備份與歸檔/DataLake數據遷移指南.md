# DataLake 數據遷移指南

**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**最後修改日期**: 2025-12-29

**更新記錄**：

- 2025-12-29：驗證遷移腳本可用性，更新遷移步驟說明，添加遷移驗證檢查清單

---

## 📋 概述

本文檔說明如何將 DataLake dictionary 和 schema 定義從 ArangoDB 遷移到 SeaweedFS。

## 🎯 遷移目標

- 將 DataLake dictionary 定義從 ArangoDB 遷移到 SeaweedFS
- 將 DataLake schema 定義從 ArangoDB 遷移到 SeaweedFS
- 更新相關服務的讀取和寫入邏輯（從 ArangoDB 改為 SeaweedFS）
- 確保數據完整性和一致性

## 📋 遷移前準備

### 1. 確認數據位置

**重要**：DataLake dictionary 和 schema 定義的具體存儲位置需要進一步確認。可能的位置包括：

- 獨立的 Collection：`datalake_dictionary`、`datalake_schema`
- 配置 Collection：`system_configs`、`tenant_configs`（scope 包含 "datalake"）

### 2. 環境檢查

確保以下環境已配置：

- ✅ SeaweedFS 服務已部署並運行
- ✅ S3 API 端點可訪問
- ✅ 環境變數已配置
- ✅ Buckets 已創建（`bucket-datalake-dictionary`、`bucket-datalake-schema`）

### 3. 備份

**重要**：遷移前必須備份 ArangoDB 數據：

```bash
# 使用 ArangoDB 備份工具
arangodump --server.endpoint tcp://localhost:8529 \
  --server.database _system \
  --collection datalake_dictionary \
  --collection datalake_schema \
  --output-directory backup_datalake_$(date +%Y%m%d)
```

## 🚀 遷移步驟

### 步驟 1：查找數據位置

首先確認數據在 ArangoDB 中的存儲位置：

```python
from database.arangodb import ArangoDBClient

client = ArangoDBClient()
# 檢查可能的 Collection
for collection_name in ["datalake_dictionary", "datalake_schema", "system_configs", "tenant_configs"]:
    if client.db.has_collection(collection_name):
        print(f"Found collection: {collection_name}")
```

### 步驟 2：乾運行測試

執行乾運行，檢查將要遷移的數據：

```bash
python scripts/migration/migrate_datalake_data_to_seaweedfs.py --dry-run
```

### 步驟 3：執行遷移

執行實際遷移：

```bash
python scripts/migration/migrate_datalake_data_to_seaweedfs.py
```

### 步驟 4：驗證遷移結果

檢查遷移狀態：

```bash
# 檢查遷移狀態
cat data/datalake_migration_state.json

# 檢查遷移日誌
tail -20 data/datalake_migration_log.jsonl
```

## 📊 數據結構

### Dictionary 定義

存儲路徑：`dictionary/{tenant_id}/{dictionary_id}.json`

文件格式：JSON

```json
{
  "_key": "dictionary_id",
  "tenant_id": "tenant_123",
  "name": "dictionary_name",
  "definition": {...},
  "created_at": "2025-01-27T00:00:00Z",
  "updated_at": "2025-01-27T00:00:00Z"
}
```

### Schema 定義

存儲路徑：`schema/{tenant_id}/{schema_id}.json`

文件格式：JSON

```json
{
  "_key": "schema_id",
  "tenant_id": "tenant_123",
  "name": "schema_name",
  "definition": {...},
  "created_at": "2025-01-27T00:00:00Z",
  "updated_at": "2025-01-27T00:00:00Z"
}
```

## 🔄 服務更新

遷移完成後，需要更新 Data Agent 相關服務：

1. **讀取邏輯**：從 SeaweedFS 讀取 dictionary 和 schema 定義
2. **寫入邏輯**：寫入到 SeaweedFS 而非 ArangoDB
3. **向後兼容**：如果 ArangoDB 中還有數據，支持從 ArangoDB 讀取（過渡期）

## ⚠️ 注意事項

1. **數據位置不確定**：DataLake dictionary 和 schema 的具體存儲位置需要進一步確認
2. **服務更新**：遷移後需要更新 Data Agent 相關服務的讀寫邏輯
3. **向後兼容**：過渡期需要支持從 ArangoDB 和 SeaweedFS 兩處讀取

## 🔗 相關文檔

- [資料存儲架構重構分析與計劃](../資料存儲架構重構分析與計劃.md)
- [資料架構建議報告](../資料架构建议报告.md)
- [文件遷移指南](./文件遷移指南.md)

---

**最後更新**: 2025-01-27
**維護者**: Daniel Chung
