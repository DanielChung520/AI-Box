# 代碼功能說明: AI-Box 檔案任務架構檢討報告

# 創建日期: 2026-01-21

# 創建人: Daniel Chung

# 最後修改日期: 2026-01-21

# AI-Box 檔案任務架構檢討報告

## 📋 概述

本文檔全面檢討 AI-Box 系統中檔案和任務的數據存儲架構，識別數據冗餘和不一致的問題，並提出改進建議。

---

## 🔍 數據源清查

### 1. ArangoDB Collections

#### 1.1 `file_metadata` 集合

**用途**: 存儲檔案的元數據，是檔案管理的主數據源

**字段結構**:

```json
{
  "_key": "file_id",
  "file_id": "唯一檔案 ID",
  "filename": "檔案名稱",
  "file_type": "檔案類型",
  "file_size": "檔案大小",
  "user_id": "所屬用戶 ID",
  "task_id": "所屬任務 ID",
  "folder_id": "所屬資料夾 ID",
  "storage_path": "存儲路徑",
  "tags": ["標籤列表"],
  "description": "描述",
  "status": "狀態",
  "processing_status": "處理狀態",
  "chunk_count": "分塊數量",
  "vector_count": "向量數量",
  "kg_status": "知識圖譜狀態",
  "access_control": { /* 權限控制 */ },
  "upload_time": "上傳時間",
  "created_at": "創建時間",
  "updated_at": "更新時間"
}
```

**主要用途**:

- 檔案管理（增刪改查）
- 文件樹構建 (`/api/v1/files/tree`)
- 權限檢查
- 狀態追蹤（向量化、知識圖譜提取等）

**使用位置**:

- `services/api/services/file_metadata_service.py`
- `api/routers/file_management.py`
- `api/routers/file_upload.py`

#### 1.2 `folder_metadata` 集合

**用途**: 存儲資料夾的元數據

**字段結構**:

```json
{
  "_key": "folder_id",
  "folder_name": "資料夾名稱",
  "user_id": "所屬用戶 ID",
  "task_id": "所屬任務 ID",
  "folder_type": "資料夾類型 (workspace/scheduled)",
  "parent_task_id": "父任務 ID (用於嵌套結構)",
  "created_at": "創建時間"
}
```

**主要用途**:

- 資料夾管理
- 文件樹構建（嵌套資料夾結構）

**使用位置**:

- `services/api/services/task_workspace_service.py`
- `api/routers/file_management.py`

#### 1.3 `user_tasks` 集合

**用途**: 存儲任務信息

**字段結構**:

```json
{
  "_key": "task_id 或 user_id_task_id",
  "task_id": "任務 ID",
  "user_id": "所屬用戶 ID",
  "title": "任務標題",
  "status": "狀態",
  "task_status": "任務狀態 (activate/archived)",
  "fileTree": [ /* 檔案樹結構 */ ],
  "messages": [],
  "executionConfig": {},
  "created_at": "創建時間",
  "updated_at": "更新時間"
}
```

**重要問題**: `fileTree` 欄位是冗餘數據！

**使用位置**:

- `services/api/services/user_task_service.py`
- `api/routers/user_tasks.py`

---

### 2. 文件存儲

#### 2.1 S3/SeaweedFS 存儲

**配置**: `storage_backend = "s3"`

**存儲路徑格式**:

- 一般檔案: `tasks/{task_id}/{file_id}.{ext}`
- 默認 Bucket: `bucket-ai-box-assets`

**使用位置**:

- `storage/s3_storage.py`

#### 2.2 本地文件系統（備用）

**配置**: `storage_backend = "local"`

**存儲路徑格式**:

- 本地路徑: `data/tasks/{task_id}/workspace/{file_id}.{ext}`

**使用位置**:

- `storage/file_storage.py`

**注意**: `data/tasks/` 目錄僅用於本地存儲，實際生產環境使用 S3

---

## 📊 數據流向分析

### 檔案上傳流程

```
前端上傳檔案
    ↓
POST /api/v1/files/upload
    ↓
1. 存儲檔案到 S3/本地
2. metadata_service.create() → file_metadata
3. 更新任務的 fileTree ← 問題點！
```

**問題**: 有兩處更新 fileTree，可能導致不一致：

1. `file_upload.py:2568` - 調用 `task_service.get(build_file_tree=True)`
2. `file_upload.py:2590` - 直接更新任務文檔的 `fileTree` 欄位

### 文件樹查詢流程

**正確方式**（從 `file_metadata` 查詢）:

```
GET /api/v1/files/tree?task_id=xxx
    ↓
file_metadata_service.list() → file_metadata
folder_metadata_service.list() → folder_metadata
組裝成樹狀結構
    ↓
返回 tree, folders
```

**舊方式**（從任務的 `fileTree` 欄位讀取）:

```
GET /api/v1/user-tasks/{task_id}?build_file_tree=true
    ↓
task_service.get(build_file_tree=True)
    ↓
調用 _build_file_tree_for_task() 或直接返回 fileTree
    ↓
返回任務的 fileTree 欄位
```

---

## ❌ 問題診斷

### 問題 1: 數據冗餘

| 數據源 | fileTree | file_metadata | 狀態 |
|--------|----------|---------------|------|
| 任務的 fileTree 欄位 | ✅ 有 | ❌ 沒有 | 不一致 |
| `/api/v1/files/tree` API | N/A | ✅ 有 | 正確 |

**原因**:

- 上傳時 `metadata_service.create()` 可能失敗
- 但任務的 `fileTree` 已更新
- 導致 `file_metadata` 缺少記錄

### 問題 2: fileTree 欄位職責不清

`fileTree` 欄位有兩種來源：

1. 從 `file_metadata` + `folder_metadata` 動態構建
2. 手動更新（繞過 metadata）

**代碼證據**:

```python
# file_upload.py:2568
task = task_service.get(user_id=user_id, task_id=task_id, build_file_tree=True)
if task and task.fileTree:
    # 使用任務的 fileTree
    file_tree_data = []
    for node in task.fileTree:
        ...

# file_upload.py:2590
task_collection.update(task_doc)  # 直接更新 fileTree
```

### 問題 3: 雙重數據源

前端有兩個 API 獲取 fileTree：

1. `/api/v1/files/tree` - 從 `file_metadata` 查詢（正確）
2. `/api/v1/user-tasks/{task_id}` - 從任務的 `fileTree` 欄位讀取（可能有問題）

---

## 🎯 改進建議

### 建議 1: 移除任務的 fileTree 欄位

**目標**: `file_metadata` 為檔案管理的唯一數據源

**實施步驟**:

1. 修改前端，只使用 `/api/v1/files/tree` API
2. 移除 `user_tasks` 的 `fileTree` 欄位
3. 刪除 `_build_file_tree_for_task()` 方法
4. 確保上傳流程一定創建 `file_metadata`

### 建議 2: 修復數據不一致

**短期修復**（已執行）:

```bash
# 為現有任務補建 file_metadata
curl -X POST "http://localhost:8529/_db/ai_box_kg/_api/document/file_metadata" \
  -H "Content-Type: application/json" \
  -d '{
    "_key": "file_id",
    "file_id": "file_id",
    "filename": "filename.md",
    "task_id": "task_id",
    "user_id": "user_id",
    ...
  }'
```

**長期方案**:

1. 確保 `metadata_service.create()` 在上傳時一定成功
2. 添加事務保證：file_metadata 和 fileTree 要麼都成功，要麼都失敗

### 建議 3: 統一文件樹 API

**目標**: 移除從任務獲取 fileTree 的能力

**修改**:

```python
# user_tasks.py
# 移除 build_file_tree 參數或始終返回 False
async def get_user_task(
    task_id: str,
    build_file_tree: bool = Query(False),  # 廢棄參數
    ...
):
    # 忽略 build_file_tree，前端應使用 /api/v1/files/tree
```

---

## 📁 目錄結構整理

### 當前結構

```
AI-Box/
├── data/
│   ├── tasks/                    # 本地存儲（備用）
│   │   ├── {task_id}/
│   │   │   ├── workspace/        # 任務工作區
│   │   │   └── scheduled/        # 排程任務
│   │   └── ...
│   ├── datasets/                 # 數據集
│   ├── ontology/                 # 本體論
│   ├── intents/                  # 意圖
│   └── qdrant/                   # 向量數據庫
│
├── storage/
│   ├── s3_storage.py             # S3/SeaweedFS 存儲
│   └── file_storage.py           # 本地文件存儲
│
└── api/routers/
    ├── file_upload.py            # 檔案上傳
    ├── file_management.py        # 檔案管理
    └── user_tasks.py             # 任務管理
```

### 建議結構

```
AI-Box/
├── data/
│   ├── tasks/                    # 本地存儲（僅開發環境）
│   │   └── {task_id}/
│   ├── datasets/
│   ├── ontology/
│   ├── intents/
│   └── qdrant/
│
├── storage/                      # 存儲抽象層
│   ├── base.py                   # 存儲接口
│   ├── s3_storage.py             # S3/SeaweedFS
│   └── local_storage.py          # 本地存儲
│
└── api/
    ├── routers/
    │   ├── file_upload.py        # 檔案上傳
    │   ├── file_management.py    # 檔案管理（單一數據源）
    │   └── task.py               # 任務管理（無 fileTree）
```

---

## 🔧 實施計劃

### Phase 1: 數據修復（已完成）

- [x] 為缺失的 `file_metadata` 補建記錄
- [ ] 運行數據一致性檢查腳本

### Phase 2: 代碼修復

- [ ] 確保 `metadata_service.create()` 在上傳時一定成功
- [ ] 添加事務保證
- [ ] 移除重複的 fileTree 更新邏輯

### Phase 3: 前端遷移

- [ ] 修改前端只使用 `/api/v1/files/tree`
- [ ] 移除從 `/api/v1/user-tasks/{id}` 獲取 fileTree 的邏輯

### Phase 4: 數據庫遷移

- [ ] 從 `user_tasks` 移除 `fileTree` 欄位
- [ ] 刪除 `_build_file_tree_for_task()` 方法

---

## 📝 總結

### 當前狀態

| 項目 | 狀態 | 說明 |
|------|------|------|
| file_metadata | ✅ 主數據源 | 檔案管理的正確數據源 |
| folder_metadata | ✅ 輔助數據源 | 資料夾結構管理 |
| user_tasks.fileTree | ❌ 冗餘/過時 | 導致數據不一致 |
| S3 存儲 | ✅ 正確 | 實際檔案存儲位置 |
| data/tasks/ | ⚠️ 備用 | 本地存儲（開發環境） |

### 行動項目

1. **立即**: 修復 `file_metadata` 缺失問題（已完成）
2. **短期**: 統一文件樹 API，移除 `fileTree` 冗餘
3. **長期**: 從架構上移除 `fileTree` 欄位

---

**文件版本**: v1.0
**創建日期**: 2026-01-21
**維護人**: Daniel Chung
