# 文件編輯 Agent v2.0 API 文檔

**代碼功能說明**: 文件編輯 Agent v2.0 API 文檔
**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-11

---

## 概述

文件編輯 Agent v2.0 提供 REST API 接口，支持文件創建、編輯、刪除、Draft State 管理和版本控制（Commit & Rollback）等功能。

**Base URL**: `/api/v1/document-editing-agent/v2`

---

## 認證

所有 API 端點都需要認證：

- **認證方式**: 通過 `get_current_user` 和 `get_current_tenant_id` 依賴注入
- **用戶信息**: 從認證 Token 中提取
- **租戶信息**: 從認證 Token 或請求頭中提取

---

## API 端點

### 1. 創建文件

**端點**: `POST /files`

**描述**: 在指定的任務工作區中創建新文件。

**請求體**:

```json
{
  "file_name": "example.md",
  "task_id": "task-123",
  "content": "# 標題\n\n內容",
  "format": "markdown"
}
```

**參數說明**:

| 參數 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `file_name` | string | 是 | 文件名 |
| `task_id` | string | 是 | 任務 ID |
| `content` | string | 是 | 文件內容 |
| `format` | string | 否 | 文件格式（markdown, excel, pdf），默認 "markdown" |

**響應** (201 Created):

```json
{
  "success": true,
  "data": {
    "file_id": "file-123",
    "file_path": "data/tasks/task-123/workspace/file-123.md",
    "task_id": "task-123",
    "folder_id": "task-123_workspace"
  }
}
```

**錯誤響應**:

- `500 Internal Server Error`: 創建文件失敗

---

### 2. 編輯文件

**端點**: `POST /edit`

**描述**: 使用 Intent DSL 對文件進行結構化編輯。

**請求體**:

```json
{
  "document_context": {
    "doc_id": "doc-123",
    "version_id": "v1",
    "file_path": "data/tasks/task-123/workspace/file-123.md",
    "task_id": "task-123",
    "user_id": "user-456",
    "tenant_id": "tenant-789"
  },
  "edit_intent": {
    "intent_id": "intent-123",
    "intent_type": "update",
    "target_selector": {
      "type": "heading",
      "selector": {
        "text": "標題",
        "level": 1,
        "occurrence": 1
      }
    },
    "action": {
      "mode": "update",
      "content": "新標題",
      "position": "inside"
    },
    "constraints": {
      "max_tokens": 500,
      "style_guide": "enterprise-tech-v1",
      "no_external_reference": true
    }
  }
}
```

**參數說明**:

| 參數 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `document_context` | object | 是 | 文檔上下文（見 DocumentContext 說明） |
| `edit_intent` | object | 是 | 編輯意圖 DSL（見 Edit Intent DSL 說明） |

**響應** (200 OK):

```json
{
  "success": true,
  "data": {
    "patch_id": "patch-123",
    "patch": {
      "patch_id": "patch-123",
      "intent_id": "intent-123",
      "block_patch": {
        "operations": []
      },
      "text_patch": "--- a/file.md\n+++ b/file.md\n",
      "preview": "新標題內容",
      "audit_info": {
        "model_version": "gpt-4-turbo-preview-2026-01-09",
        "context_digest": "sha256...",
        "generated_at": "2026-01-11T10:00:00Z",
        "generated_by": "md-editor-v2.0"
      }
    },
    "preview": "新標題內容"
  }
}
```

**錯誤響應**:

- `400 Bad Request`: 編輯失敗（如目標未找到、驗證失敗等）
- `500 Internal Server Error`: 服務器錯誤

---

### 3. 刪除文件

**端點**: `DELETE /files/{file_id}`

**描述**: 刪除指定的文件。

**路徑參數**:

| 參數 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `file_id` | string | 是 | 文件 ID |

**響應** (200 OK):

```json
{
  "success": true,
  "data": {
    "deleted": true,
    "file_id": "file-123"
  }
}
```

**錯誤響應**:

- `404 Not Found`: 文件不存在
- `403 Forbidden`: 沒有權限刪除文件
- `500 Internal Server Error`: 刪除失敗

---

### 4. 保存 Draft State

**端點**: `POST /draft`

**描述**: 保存文件的草稿狀態。

**請求體**:

```json
{
  "doc_id": "doc-123",
  "content": "草稿內容",
  "patches": []
}
```

**參數說明**:

| 參數 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `doc_id` | string | 是 | 文檔 ID |
| `content` | string | 是 | 草稿內容 |
| `patches` | array | 否 | 已應用的 Patches |

**響應** (200 OK):

```json
{
  "success": true,
  "data": {
    "doc_id": "doc-123"
  }
}
```

---

### 5. 讀取 Draft State

**端點**: `GET /draft/{doc_id}`

**描述**: 讀取文件的草稿狀態。

**路徑參數**:

| 參數 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `doc_id` | string | 是 | 文檔 ID |

**響應** (200 OK):

```json
{
  "success": true,
  "data": {
    "doc_id": "doc-123",
    "content": "草稿內容",
    "patches": []
  }
}
```

**錯誤響應**:

- `404 Not Found`: Draft State 不存在

---

### 6. Commit（提交變更）

**端點**: `POST /commit`

**描述**: 提交草稿狀態為正式版本。

**請求體**:

```json
{
  "doc_id": "doc-123",
  "base_version_id": "v3",
  "summary": "AI 生成並經用戶確認的變更摘要",
  "content": "最終合併後的完整 Markdown 內容"
}
```

**參數說明**:

| 參數 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `doc_id` | string | 是 | 文檔 ID |
| `base_version_id` | string | 否 | 基礎版本 ID |
| `summary` | string | 否 | 變更摘要 |
| `content` | string | 是 | 最終合併後的完整內容 |

**響應** (200 OK):

```json
{
  "success": true,
  "data": {
    "new_version_id": "v4",
    "timestamp": "2026-01-11T10:00:00Z"
  }
}
```

---

### 7. Rollback（回滾版本）

**端點**: `POST /rollback`

**描述**: 回滾到指定的版本。

**請求體**:

```json
{
  "doc_id": "doc-123",
  "target_version_id": "v2"
}
```

**參數說明**:

| 參數 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `doc_id` | string | 是 | 文檔 ID |
| `target_version_id` | string | 是 | 目標版本 ID |

**響應** (200 OK):

```json
{
  "success": true,
  "data": {
    "rolled_back_to_version_id": "v2",
    "timestamp": "2026-01-11T10:00:00Z"
  }
}
```

---

## Intent DSL 語法說明

### DocumentContext

文檔上下文，包含文檔的基本信息。

```json
{
  "doc_id": "uuid",
  "version_id": "uuid",
  "file_path": "data/tasks/{task_id}/workspace/{file_id}.md",
  "task_id": "uuid",
  "user_id": "uuid",
  "tenant_id": "uuid"
}
```

**字段說明**:

| 字段 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `doc_id` | string | 是 | 文檔 ID |
| `version_id` | string | 否 | 版本 ID |
| `file_path` | string | 是 | 文件路徑 |
| `task_id` | string | 是 | 任務 ID |
| `user_id` | string | 是 | 用戶 ID |
| `tenant_id` | string | 是 | 租戶 ID |

---

### Edit Intent DSL

編輯意圖領域特定語言，定義編輯操作。

```json
{
  "intent_id": "uuid",
  "intent_type": "insert|update|delete|move|replace",
  "target_selector": {
    "type": "heading|anchor|block",
    "selector": {
      // 選擇器特定字段
    }
  },
  "action": {
    "mode": "insert|update|delete|move|replace",
    "content": "markdown content or null",
    "position": "before|after|inside|start|end"
  },
  "constraints": {
    "max_tokens": 300,
    "style_guide": "enterprise-tech-v1",
    "no_external_reference": true
  }
}
```

**字段說明**:

| 字段 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `intent_id` | string | 是 | Intent ID（UUID） |
| `intent_type` | string | 是 | Intent 類型（insert, update, delete, move, replace） |
| `target_selector` | object | 是 | 目標選擇器（見 Target Selector 說明） |
| `action` | object | 是 | 操作定義（見 Action 說明） |
| `constraints` | object | 否 | 約束條件（見 Constraints 說明） |

---

### Target Selector

目標選擇器，用於定位要編輯的目標。

#### Heading Selector

```json
{
  "type": "heading",
  "selector": {
    "text": "標題文本",
    "level": 1,
    "occurrence": 1
  }
}
```

**字段說明**:

| 字段 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `text` | string | 是 | 標題文本（支持模糊匹配） |
| `level` | integer | 否 | 標題級別（1-6） |
| `occurrence` | integer | 否 | 出現次數（從 1 開始），默認 1 |

#### Anchor Selector

```json
{
  "type": "anchor",
  "selector": {
    "anchor_id": "anchor-id"
  }
}
```

**字段說明**:

| 字段 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `anchor_id` | string | 是 | Anchor ID（支持模糊匹配） |

#### Block Selector

```json
{
  "type": "block",
  "selector": {
    "block_id": "block-id"
  }
}
```

**字段說明**:

| 字段 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `block_id` | string | 是 | Block ID |

---

### Action

操作定義，描述要執行的編輯操作。

```json
{
  "mode": "update",
  "content": "新內容",
  "position": "inside"
}
```

**字段說明**:

| 字段 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `mode` | string | 是 | 操作模式（insert, update, delete, move, replace） |
| `content` | string | 否 | 新內容（insert/update/replace 時需要） |
| `position` | string | 否 | 位置（before, after, inside, start, end） |

---

### Constraints

約束條件，用於驗證生成內容。

```json
{
  "max_tokens": 500,
  "style_guide": "enterprise-tech-v1",
  "no_external_reference": true
}
```

**字段說明**:

| 字段 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `max_tokens` | integer | 否 | 最大 Token 數 |
| `style_guide` | string | 否 | 樣式指南名稱（如 "enterprise-tech-v1"） |
| `no_external_reference` | boolean | 否 | 是否禁止外部參照（默認 false） |

**進階驗證選項**（通過 `style_guide` 啟用）:

- **語氣檢查**: 禁止第一人稱、禁止命令式
- **術語檢查**: 必須使用標準術語
- **格式檢查**: 表格標頭、列表格式
- **語義漂移檢查**: NER 變更率、關鍵詞交集比例
- **外部參照檢查**: 外部 URL 檢測

---

## 錯誤碼

| 錯誤碼 | HTTP 狀態碼 | 說明 |
|--------|------------|------|
| `DOCUMENT_NOT_FOUND` | 404 | 文檔不存在 |
| `VERSION_NOT_FOUND` | 404 | 版本不存在 |
| `PERMISSION_DENIED` | 403 | 權限不足 |
| `INVALID_FORMAT` | 400 | 格式無效 |
| `VALIDATION_FAILED` | 400 | 驗證失敗 |
| `TARGET_NOT_FOUND` | 400 | 目標未找到 |
| `TARGET_AMBIGUOUS` | 400 | 目標模糊（多個匹配） |
| `CONSTRAINT_VIOLATION` | 400 | 約束違規 |
| `INVALID_INTENT` | 400 | Intent 無效 |
| `INVALID_SELECTOR` | 400 | 選擇器無效 |

**錯誤響應格式**:

```json
{
  "success": false,
  "error": {
    "code": "TARGET_NOT_FOUND",
    "message": "未找到目標: heading=標題",
    "details": {
      "selector_type": "heading",
      "selector_value": "標題"
    },
    "suggestions": [
      {
        "action": "檢查選擇器值",
        "example": "確保目標存在於文檔中"
      }
    ]
  }
}
```

---

## 示例

### 示例 1: 創建並編輯文件

```bash
# 1. 創建文件
curl -X POST "http://localhost:8000/api/v1/document-editing-agent/v2/files" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "example.md",
    "task_id": "task-123",
    "content": "# 標題\n\n內容",
    "format": "markdown"
  }'

# 2. 編輯文件（更新標題）
curl -X POST "http://localhost:8000/api/v1/document-editing-agent/v2/edit" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "document_context": {
      "doc_id": "doc-123",
      "file_path": "data/tasks/task-123/workspace/file-123.md",
      "task_id": "task-123",
      "user_id": "user-456",
      "tenant_id": "tenant-789"
    },
    "edit_intent": {
      "intent_id": "intent-123",
      "intent_type": "update",
      "target_selector": {
        "type": "heading",
        "selector": {
          "text": "標題",
          "level": 1,
          "occurrence": 1
        }
      },
      "action": {
        "mode": "update",
        "content": "新標題",
        "position": "inside"
      }
    }
  }'
```

### 示例 2: 使用模糊匹配

```bash
# 如果標題文本有拼寫錯誤，系統會自動嘗試模糊匹配
curl -X POST "http://localhost:8000/api/v1/document-editing-agent/v2/edit" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "document_context": {
      "doc_id": "doc-123",
      "file_path": "data/tasks/task-123/workspace/file-123.md",
      "task_id": "task-123",
      "user_id": "user-456",
      "tenant_id": "tenant-789"
    },
    "edit_intent": {
      "intent_id": "intent-123",
      "intent_type": "update",
      "target_selector": {
        "type": "heading",
        "selector": {
          "text": "標題",  // 拼寫錯誤，系統會自動嘗試模糊匹配
          "level": 1,
          "occurrence": 1
        }
      },
      "action": {
        "mode": "update",
        "content": "新標題",
        "position": "inside"
      }
    }
  }'
```

### 示例 3: 使用進階驗證

```bash
# 啟用樣式檢查和外部參照檢查
curl -X POST "http://localhost:8000/api/v1/document-editing-agent/v2/edit" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "document_context": {
      "doc_id": "doc-123",
      "file_path": "data/tasks/task-123/workspace/file-123.md",
      "task_id": "task-123",
      "user_id": "user-456",
      "tenant_id": "tenant-789"
    },
    "edit_intent": {
      "intent_id": "intent-123",
      "intent_type": "update",
      "target_selector": {
        "type": "heading",
        "selector": {
          "text": "標題",
          "level": 1,
          "occurrence": 1
        }
      },
      "action": {
        "mode": "update",
        "content": "新標題",
        "position": "inside"
      },
      "constraints": {
        "max_tokens": 500,
        "style_guide": "enterprise-tech-v1",
        "no_external_reference": true
      }
    }
  }'
```

---

## 性能指標

- **單次編輯延遲**: < 30 秒（P95）
- **Intent 驗證延遲**: < 100ms
- **目標定位延遲**: < 200ms（包含模糊匹配）
- **上下文裝配延遲**: < 300ms
- **審計日誌寫入**: 不影響主流程性能（增加 < 50ms）

---

## 審計日誌

所有編輯操作都會記錄審計日誌，包括：

- Intent 接收和驗證
- 目標定位
- 上下文裝配
- 內容生成
- Patch 生成
- 驗證通過/失敗
- Patch 應用

審計日誌可以通過審計日誌服務查詢（需要相應的權限）。

---

## 版本信息

- **API 版本**: v2.0
- **Agent 版本**: md-editor-v2.0
- **最後更新**: 2026-01-11
