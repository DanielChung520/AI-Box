# System Management Scripts

本目錄包含 AI-Box 系統管理腳本，用於清理測試數據、管理數據庫和存儲。

## 腳本列表

### 1. cleanup_all_data.py
**用途**: 清理所有數據庫和存儲的測試數據

**功能**:
- 清理 ArangoDB collections: `user_tasks`, `file_metadata`, `entities`, `relations`, `folder_metadata`
- 清理 Qdrant collections（支持按 file_id 清理）
- 清理 SeaweedFS buckets（支持按 task_id 清理）
- 清理本地文件: `data/tasks`, `data/uploads`

**使用方式**:

```bash
# 清空所有數據（危險操作）
python scripts/system-mgt/cleanup_all_data.py --force

# 按任務清理（推薦用於測試清理）
python scripts/system-mgt/cleanup_all_data.py --task-ids task1 task2

# 按文件清理 Qdrant
python scripts/system-mgt/cleanup_all_data.py --file-ids file1 file2 --task-ids task1
```

**參數**:
- `--force`: 跳過確認直接執行（危險！）
- `--task-ids`: 按 task_id 清理（可指定多個）
- `--file-ids`: 按 file_id 清理 Qdrant（可指定多個）

**清理模式**:

1. **清空模式**（默認）:
   - ArangoDB: 清空所有 collections
   - Qdrant: 刪除所有 collections
   - SeaweedFS: 刪除 bucket 中所有文件

2. **按任務清理模式**:
   - ArangoDB: 只刪除指定 task_id 的 user_tasks 和 file_metadata
   - ArangoDB: 始終清空 entities 和 relations（知識圖譜數據）
   - Qdrant: 只刪除指定 file_id 的向量（通過 payload.file_id）
   - SeaweedFS: 只刪除 `tasks/<task_id>/` 目錄下的文件

**依賴**:
- `boto3`: SeaweedFS S3 操作
- `qdrant-client`: Qdrant 操作
- `database.arangodb.ArangoDBClient`: ArangoDB 操作

**注意**:
- ⚠️ 此腳本會刪除數據，請確認後再執行
- ⚠️ 建議先使用 `--task-ids` 模式進行清理，而不是 `--force` 清空模式
- ⚠️ 清空模式會刪除所有數據，包括生產數據

---

## 測試腳本

測試相關的腳本位於 `../tests/` 目錄：

- `cleanup_arangodb_test_data.py`: 清理 ArangoDB 測試數據（按 file_id）
- `cleanup_test_data.py`: 清理測試環境數據
- `cleanup_test_file.py`: 清理單個測試文件
- `cleanup_test_environment.py`: 清理整個測試環境

---

## 數據清理流程

### 按任務清理測試數據

1. **獲取 task_id**:
```bash
# 查詢 ArangoDB 獲取 task_id
# 從測試結果文件中獲取 task_id
```

2. **執行清理**:
```bash
# 清理特定任務的數據
python scripts/system-mgt/cleanup_all_data.py --task-ids <task_id>

# 清理多個任務
python scripts/system-mgt/cleanup_all_data.py --task-ids task1 task2 task3
```

3. **驗證清理**:
```bash
# 檢查 ArangoDB 中是否還有該 task_id 的數據
# 檢查 SeaweedFS 中是否還有 tasks/<task_id>/ 目錄
# 檢查 Qdrant 中是否還有相關的向量數據
```

### 清空所有數據（僅用於測試環境）

```bash
# ⚠️ 危險操作：清空所有數據
python scripts/system-mgt/cleanup_all_data.py --force
```

---

## 數據關係

### ArangoDB Collections

| Collection | 用途 | 清理方式 |
|-----------|------|---------|
| `user_tasks` | 用戶任務記錄 | 按任務清理或清空 |
| `file_metadata` | 文件元數據 | 按任務清理或清空 |
| `entities` | 知識圖譜實體 | 始終清空 |
| `relations` | 知識圖譜關係 | 始終清空 |
| `folder_metadata` | 文件夾元數據 | 清空 |

### Qdrant Collections

- 向量數據通過 `payload.file_id` 關聯到 file_metadata
- 清理時通過 file_id 查找並刪除相關向量

### SeaweedFS Buckets

- 文件存儲在 `tasks/<task_id>/<file_id>` 結構
- 清理時刪除整個 `tasks/<task_id>/` 目錄

---

## 環境變量

清理腳本使用以下環境變量：

```bash
# ArangoDB
ARANGO_DB=ai_box_kg
ARANGO_ROOT_PASSWORD=changeme

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# SeaweedFS
SEAWEEDFS_HOST=localhost
SEAWEEDFS_PORT=8333
SEAWEEDFS_BUCKET=bucket-ai-box-assets
AI_BOX_SEAWEEDFS_S3_ACCESS_KEY=admin
AI_BOX_SEAWEEDFS_S3_SECRET_KEY=admin123
```

---

## 故障排除

### ArangoDB 連接失敗
```bash
# 檢查 ArangoDB 是否運行
docker ps | grep arangodb

# 檢查環境變量
echo $ARANGO_ROOT_PASSWORD
```

### Qdrant 連接失敗
```bash
# 檢查 Qdrant 是否運行
docker ps | grep qdrant

# 檢查端口
curl http://localhost:6333
```

### SeaweedFS 連接失敗
```bash
# 檢查 SeaweedFS 是否運行
docker ps | grep seaweedfs

# 檢查 S3 端口
curl http://localhost:8333
```

---

## 備份建議

在執行清理前，建議先備份重要數據：

```bash
# 備份 ArangoDB
python scripts/system-mgt/backup_arangodb.py

# 備份 Qdrant
python scripts/system-mgt/backup_qdrant.py

# 備份 SeaweedFS
python scripts/system-mgt/backup_seaweedfs.py
```

---

**文檔維護者**: AI-Box System Agent  
**最後更新**: 2026-01-27
