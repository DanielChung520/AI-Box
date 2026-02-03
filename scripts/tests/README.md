# Test Scripts

本目錄包含 AI-Box 測試相關的清理腳本，用於清理測試數據、重置測試環境。

## 腳本列表

### 1. cleanup_arangodb_test_data.py
**用途**: 清理 ArangoDB 測試數據

**功能**:
- 清理知識圖譜數據（entities、relations）
- 清理文件元數據（file_metadata）
- 清理處理狀態（upload_status）

**使用方式**:

```bash
# 從測試結果文件中清理
python scripts/tests/cleanup_arangodb_test_data.py --test-result phase2_batch_test_results.json

# 指定 file_id 清理
python scripts/tests/cleanup_arangodb_test_data.py --file-ids file1 file2 file3

# 強制刪除文件元數據
python scripts/tests/cleanup_arangodb_test_data.py --file-ids file1 --force-metadata

# 清理所有測試數據（危險）
python scripts/tests/cleanup_arangodb_test_data.py --all
```

**參數**:
- `--test-result`: 測試結果文件路徑
- `--file-ids`: 直接指定要清理的文件 ID 列表
- `--force-metadata`: 強制刪除文件元數據（默認只清理 KG 和狀態）
- `--all`: 清理所有測試數據（危險操作）

---

### 2. cleanup_test_data.py
**用途**: 清理測試環境數據

**功能**:
- 清理測試文件
- 清理測試任務
- 清理測試狀態

**使用方式**:

```bash
# 清理所有測試數據
python scripts/tests/cleanup_test_data.py
```

---

### 3. cleanup_test_file.py
**用途**: 清理單個測試文件

**功能**:
- 按文件 ID 清理單個測試文件及其相關數據

**使用方式**:

```bash
# 清理單個測試文件
python scripts/tests/cleanup_test_file.py --file-id <file_id>
```

**參數**:
- `--file-id`: 要清理的文件 ID

---

### 4. cleanup_test_environment.py
**用途**: 清理整個測試環境

**功能**:
- 重置測試環境到初始狀態
- 清理所有測試數據和配置

**使用方式**:

```bash
# 清理整個測試環境
python scripts/tests/cleanup_test_environment.py
```

---

### 5. cleanup_all.py (舊版腳本)
**用途**: 完整清理腳本（舊版，使用 httpx API 請求）

**功能**:
- 清理 ArangoDB（舊 task_id）
- 清理 Qdrant（指定 file_id pattern）
- 清理 SeaweedFS（tasks 目錄）

**使用方式**:

```bash
# 清理所有舊測試數據
python scripts/tests/cleanup_all.py
```

**注意**:
- ⚠️ 此腳本為舊版，建議使用 `../system-mgt/cleanup_test_data.py`

---

## 測試數據清理流程

### 1. 單文件測試清理

```bash
# 清理單個測試文件
python scripts/tests/cleanup_test_file.py --file-id <file_id>
```

### 2. 批量測試清理（從測試結果）

```bash
# 從測試結果文件中清理
python scripts/tests/cleanup_arangodb_test_data.py --test-result test_results.json
```

### 3. 按任務清理（推薦）

```bash
# 清理特定任務的所有測試數據
python scripts/system-mgt/cleanup_test_data.py --task-ids task1 task2
```

### 4. 完整測試環境重置

```bash
# 重置整個測試環境
python scripts/tests/cleanup_test_environment.py

# 或使用系統管理腳本
python scripts/system-mgt/cleanup_test_data.py --force
```

---

## 測試數據結構

### ArangoDB

```
user_tasks
├── task_id
│   ├── file_ids
│   ├── status
│   └── metadata

file_metadata
├── file_id
│   ├── task_id (關聯到 user_tasks)
│   ├── file_name
│   ├── file_type
│   └── ...

entities
├── entity_id
├── entity_type
└── ...

relations
├── relation_id
├── source_entity
├── target_entity
└── ...
```

### SeaweedFS

```
bucket-ai-box-assets/
└── tasks/
    └── task_id/
        ├── file1
        ├── file2
        └── ...
```

### Qdrant

```
collections/
└── <collection_name>
    └── points
        ├── id
        ├── vector
        └── payload
            └── file_id (關聯到 file_metadata)
```

---

## 測試清理最佳實踐

### 1. 按任務清理（推薦）

```bash
# 每次測試使用唯一的 task_id
# 測試完成後清理該 task_id

# 清理
python scripts/system-mgt/cleanup_test_data.py --task-ids test_task_123
```

### 2. 使用測試結果文件

```bash
# 保存測試結果到 JSON 文件
{
  "results": [
    {"file_id": "file1", "status": "success"},
    {"file_id": "file2", "status": "success"}
  ]
}

# 從測試結果清理
python scripts/tests/cleanup_arangodb_test_data.py --test-result test_results.json
```

### 3. 備份測試數據

```bash
# 在清理前備份（如果需要）
# ...
```

---

## 注意事項

### ⚠️ 清理前確認

1. **確認數據類型**:
   - 是測試數據還是生產數據？
   - 是否需要保留部分數據？

2. **確認清理範圍**:
   - 是清理單個文件還是整個任務？
   - 是否需要清理相關的知識圖譜數據？

3. **確認依賴關係**:
   - 是否有其他進程正在使用這些數據？
   - 是否需要停止相關服務？

### ⚠️ 清理順序

建議按以下順序清理：

1. 停止相關服務
2. 清理 Qdrant（向量數據）
3. 清理 ArangoDB（元數據、知識圖譜）
4. 清理 SeaweedFS（文件）
5. 清理本地文件

### ⚠️ 清理驗證

清理後建議驗證：

```bash
# 檢查 ArangoDB
# ...

# 檢查 Qdrant
# ...

# 檢查 SeaweedFS
# ...
```

---

**文檔維護者**: AI-Box System Agent  
**最後更新**: 2026-01-27
