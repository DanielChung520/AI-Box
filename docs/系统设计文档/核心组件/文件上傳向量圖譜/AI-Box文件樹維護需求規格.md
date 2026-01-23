# 代碼功能說明: AI-Box 文件樹維護需求規格

# 創建日期: 2026-01-21

# 創建人: Daniel Chung

# 最後修改日期: 2026-01-21

# AI-Box 文件樹維護需求規格

## 📋 版本歷史

| 版本 | 日期 | 更新內容 | 更新人 |
|------|------|----------|--------|
| v1.0 | 2026-01-21 | 初始版本 | Daniel Chung |

---

## 1. 概述

### 1.1 文檔目的

本文檔定義前端任務文件區的文件樹顯示邏輯，以及子目錄（資料夾）的增刪改操作規格。

### 1.2 數據源

文件樹的**唯一數據源**：

- **file_metadata**: 檔案元數據
- **folder_metadata**: 資料夾元數據

**廢除**: `user_tasks.fileTree` 欄位

---

## 2. 文件樹顯示規格

### 2.1 API 端點

**端點**: `GET /api/v1/files/tree`

**請求參數**:
| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `task_id` | string | ✅ | 任務 ID |
| `user_id` | string | ❌ | 用戶 ID（驗證用） |

**響應格式**:

```json
{
  "code": 200,
  "data": {
    "tree": {
      "{folder_id}": [
        {
          "file_id": "uuid",
          "filename": "檔案名稱.md",
          "file_type": "markdown",
          "file_size": 12345,
          "upload_time": "2026-01-21T12:00:00Z",
          "updated_at": "2026-01-21T12:00:00Z",
          "status": "uploaded",
          "processing_status": {
            "vectorized": true,
            "kg_extracted": false
          }
        }
      ],
      "{folder_id}_workspace": [ /* 默認工作區 */ ]
    },
    "folders": {
      "{folder_id}": {
        "folder_id": "folder_id",
        "folder_name": "目錄名稱",
        "folder_type": "workspace" | "scheduled" | "custom",
        "parent_folder_id": null | "parent_folder_id",
        "task_id": "task_id",
        "created_at": "2026-01-21T12:00:00Z"
      },
      "{task_id}_workspace": {
        "folder_id": "{task_id}_workspace",
        "folder_name": "任務工作區",
        "folder_type": "workspace",
        "parent_folder_id": null,
        "task_id": "task_id",
        "created_at": "2026-01-21T00:00:00Z"
      }
    },
    "metadata": {
      "total_folders": 3,
      "total_files": 5
    }
  }
}
```

### 2.2 文件樹結構

```
任務文件區
└── 任務工作區 (workspace) ← 默認目錄
    ├── 子目錄 A
    │   ├── 子目錄 A1
    │   │   └── 檔案 1.md
    │   └── 檔案 2.md
    ├── 子目錄 B
    │   └── 檔案 3.md
    └── 檔案 4.md
```

### 2.3 前端顯示邏輯

```typescript
// 假設 API 返回的數據結構
interface FileTreeResponse {
  tree: {
    [folderId: string]: FileNode[]
  };
  folders: {
    [folderId: string]: FolderNode
  };
}

// 前端遞歸渲染
function renderFolder(folderId: string) {
  const folder = folders[folderId];
  const files = tree[folderId] || [];

  return `
    <div class="folder">
      <div class="folder-header">${folder.folder_name}</div>
      <div class="folder-content">
        ${files.map(file => renderFile(file)).join('')}
        ${Object.values(folders)
          .filter(f => f.parent_folder_id === folderId)
          .map(f => renderFolder(f.folder_id))
          .join('')}
      </div>
    </div>
  `;
}
```

---

## 3. 資料夾管理規格

### 3.1 創建資料夾

**端點**: `POST /api/v1/folders`

**請求**:

```json
{
  "task_id": "task_id",
  "folder_name": "新目錄名稱",
  "parent_folder_id": null | "parent_folder_id"  // 可選
}
```

**響應**:

```json
{
  "code": 201,
  "data": {
    "folder_id": "uuid",
    "folder_name": "新目錄名稱",
    "task_id": "task_id",
    "parent_folder_id": null | "parent_folder_id",
    "folder_type": "custom",
    "created_at": "2026-01-21T12:00:00Z"
  },
  "message": "資料夾創建成功"
}
```

**驗證規則**:
| 規則 | 說明 |
|------|------|
| 名稱唯一性 | 同一父目錄下名稱不能重複 |
| 長度限制 | 1-100 字元 |
| 特殊字符 | 不允許 `/ \ : * ? " < >` |

### 3.2 查詢資料夾

**端點**: `GET /api/v1/folders/{folder_id}`

**響應**:

```json
{
  "code": 200,
  "data": {
    "folder_id": "uuid",
    "folder_name": "目錄名稱",
    "task_id": "task_id",
    "parent_folder_id": null | "parent_folder_id",
    "folder_type": "workspace" | "scheduled" | "custom",
    "created_at": "2026-01-21T12:00:00Z",
    "updated_at": "2026-01-21T12:00:00Z"
  }
}
```

### 3.3 更新資料夾

**端點**: `PUT /api/v1/folders/{folder_id}`

**請求**:

```json
{
  "folder_name": "新名稱",           // 可選
  "parent_folder_id": "new_parent"   // 可選（移動）
}
```

**響應**:

```json
{
  "code": 200,
  "message": "資料夾更新成功"
}
```

**限制**:

- 系統資料夾 (`_workspace`, `_scheduled`) 不可移動或刪除
- 移動後需更新所有子目錄的 `parent_folder_id`

### 3.4 刪除資料夾

**端點**: `DELETE /api/v1/folders/{folder_id}`

**請求**:

```json
{
  "recursive": false  // 是否遞歸刪除（包含內容）
}
```

**響應**:

```json
{
  "code": 200,
  "message": "資料夾刪除成功",
  "data": {
    "deleted_folders": 3,
    "deleted_files": 5
  }
}
```

**限制**:
| 情況 | 處理方式 |
|------|----------|
| 資料夾為空 | 直接刪除 |
| 資料夾非空且 `recursive=false` | 返回錯誤 |
| 資料夾非空且 `recursive=true` | 刪除資料夾及所有內容 |

---

## 4. 檔案管理規格

### 4.1 上傳檔案（指定資料夾）

**端點**: `POST /api/v1/files/upload`

**請求**: `multipart/form-data`

| 字段 | 類型 | 說明 |
|------|------|------|
| `files` | File[] | 檔案列表 |
| `task_id` | string | 任務 ID |
| `folder_id` | string | 目標資料夾 ID（可選） |

**響應**:

```json
{
  "code": 201,
  "data": {
    "uploaded": [
      {
        "file_id": "uuid",
        "filename": "檔案名稱.md",
        "folder_id": "folder_id",
        "upload_time": "2026-01-21T12:00:00Z"
      }
    ],
    "failed": []
  }
}
```

### 4.2 移動檔案

**端點**: `PUT /api/v1/files/{file_id}/move`

**請求**:

```json
{
  "target_folder_id": "new_folder_id"
}
```

**響應**:

```json
{
  "code": 200,
  "message": "檔案移動成功",
  "data": {
    "file_id": "uuid",
    "source_folder_id": "old_folder_id",
    "target_folder_id": "new_folder_id"
  }
}
```

### 4.3 刪除檔案

**端點**: `DELETE /api/v1/files/{file_id}`

**響應**:

```json
{
  "code": 200,
  "message": "檔案刪除成功",
  "data": {
    "file_id": "uuid",
    "deleted_from": "folder_id"
  }
}
```

**注意**: 刪除檔案會同時：

1. 從 S3 刪除檔案
2. 從 `file_metadata` 刪除記錄
3. 從 Qdrant 刪除向量
4. 從 ArangoDB 刪除知識圖譜

---

## 5. 特殊資料夾

### 5.1 系統資料夾

每個任務自動創建以下系統資料夾：

| 資料夾 ID | 名稱 | 類型 | 說明 |
|-----------|------|------|------|
| `{task_id}_workspace` | 任務工作區 | workspace | 默認存放位置 |
| `{task_id}_scheduled` | 排程任務 | scheduled | 系統預留 |

**規則**:

- 系統資料夾不可刪除
- 系統資料夾不可移動
- 系統資料夾的 `folder_type` 不可更改

### 5.2 自訂資料夾

用戶創建的資料夾為 `custom` 類型。

---

## 6. API 端點總表

### 6.1 文件樹

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | `/api/v1/files/tree` | 查詢任務文件樹 |
| GET | `/api/v1/files/{file_id}` | 查詢檔案資訊 |

### 6.2 檔案操作

| Method | Endpoint | 說明 |
|--------|----------|------|
| POST | `/api/v1/files/upload` | 上傳檔案 |
| PUT | `/api/v1/files/{file_id}/move` | 移動檔案 |
| DELETE | `/api/v1/files/{file_id}` | 刪除檔案 |

### 6.3 資料夾操作

| Method | Endpoint | 說明 |
|--------|----------|------|
| POST | `/api/v1/folders` | 創建資料夾 |
| GET | `/api/v1/folders/{folder_id}` | 查詢資料夾 |
| PUT | `/api/v1/folders/{folder_id}` | 更新資料夾 |
| DELETE | `/api/v1/folders/{folder_id}` | 刪除資料夾 |

---

## 7. 數據關係

### 7.1 ER 圖

```
┌─────────────────┐       ┌─────────────────┐
│   user_tasks    │       │  folder_metadata│
├─────────────────┤       ├─────────────────┤
│ task_id (PK)    │◄──────┤ task_id (FK)    │
│ user_id         │       │ folder_id (PK)  │
│ title           │       │ folder_name     │
│ ...             │       │ parent_folder_id│
└─────────────────┘       │ folder_type     │
         │                └────────┬────────┘
         │                         │
         │                         │ 1:N
         │                         ▼
         │                ┌─────────────────┐
         └───────────────►│  file_metadata  │
                          ├─────────────────┤
                          │ file_id (PK)    │
                          │ task_id (FK)    │
                          │ folder_id (FK)  │
                          │ filename        │
                          │ storage_path    │
                          │ access_control  │
                          │ ...             │
                          └─────────────────┘
```

### 7.2 查詢邏輯

```python
# 查詢任務文件樹的邏輯
def get_file_tree(task_id: str) -> dict:
    # 1. 查詢所有資料夾
    folders = folder_metadata_service.list(task_id=task_id)

    # 2. 查詢所有檔案
    files = file_metadata_service.list(task_id=task_id)

    # 3. 按 folder_id 分組
    tree = {}
    for folder in folders:
        tree[folder.folder_id] = []
        for file in files:
            if file.folder_id == folder.folder_id:
                tree[folder.folder_id].append(file)

    # 4. 處理沒有 folder_id 的檔案（默認工作區）
    if "{task_id}_workspace" not in tree:
        tree["{task_id}_workspace"] = []
    for file in files:
        if file.folder_id is None:
            tree["{task_id}_workspace"].append(file)

    return {"tree": tree, "folders": folders}
```

---

## 8. 權限控制

### 8.1 資料夾權限

資料夾繼承任務的權限：

- `task.user_id` 為所有者
- `access_control` 為任務級別

### 8.2 檔案權限

檔案權限存儲在 `file_metadata.access_control`：

- 可獨立設置
- 預設繼承所屬資料夾/任務的權限

---

## 9. 實現狀態

| 功能 | 狀態 | 說明 |
|------|------|------|
| 文件樹查詢 | ✅ | `/api/v1/files/tree` |
| 創建資料夾 | ⚠️ | 部分完成 |
| 更新資料夾 | ❌ | 待實現 |
| 刪除資料夾 | ❌ | 待實現 |
| 移動檔案 | ❌ | 待實現 |
| 移動資料夾 | ❌ | 待實現 |

---

## 10. 前端 UI 規格

### 10.1 文件樹組件結構

```
FileTree/
├── Toolbar/
│   ├── UploadButton
│   ├── NewFolderButton
│   └── RefreshButton
├── FolderNode/
│   ├── FolderHeader (可展開/折疊)
│   └── FolderChildren (遞歸渲染)
├── FileNode/
│   ├── FileIcon
│   ├── FileName
│   └── FileActions (右鍵選單)
└── ContextMenu/
    ├── Open
    ├── Download
    ├── Move
    ├── Rename
    └── Delete
```

### 10.2 操作流程

```
用戶點擊「新增資料夾」
    │
    ▼
┌─────────────────────┐
│ 顯示對話框          │
│ - 輸入名稱          │
│ - 選擇父目錄        │
└─────────────────────┘
    │
    ▼
POST /api/v1/folders
    │
    ▼
┌─────────────────────┐
│ 成功: 刷新文件樹    │
│ 失敗: 顯示錯誤      │
└─────────────────────┘
```

---

## 11. 待討論事項

- [ ] 是否支援拖曳移動檔案/資料夾？
- [ ] 是否支援批量操作？
- [ ] 資料夾是否支援重命名？
- [ ] 刪除資料夾時是否需要二次確認？

---

**文件版本**: v1.0
**最後更新日期**: 2026-01-21
**維護人**: Daniel Chung
