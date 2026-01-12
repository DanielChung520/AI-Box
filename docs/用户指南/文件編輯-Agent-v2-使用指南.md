# 文件編輯 Agent v2.0 使用指南

**代碼功能說明**: 文件編輯 Agent v2.0 使用指南
**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-11

---

## 概述

文件編輯 Agent v2.0 是一個基於 Intent DSL 和 Block Patch 的結構化文件編輯服務，支持 Markdown 文件的精準編輯，提供模糊匹配、進階驗證和完整的審計日誌功能。

---

## 快速開始

### 1. 創建文件

```bash
POST /api/v1/document-editing-agent/v2/files
Content-Type: application/json
Authorization: Bearer <token>

{
  "file_name": "example.md",
  "task_id": "task-123",
  "content": "# 標題\n\n內容",
  "format": "markdown"
}
```

### 2. 編輯文件

```bash
POST /api/v1/document-editing-agent/v2/edit
Content-Type: application/json
Authorization: Bearer <token>

{
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
}
```

---

## Intent DSL 使用說明

### Target Selector（目標選擇器）

#### Heading Selector（標題選擇器）

用於定位標題 Block。

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

**參數說明**:

- `text`: 標題文本（支持模糊匹配）
- `level`: 標題級別（1-6，可選）
- `occurrence`: 出現次數（從 1 開始，可選，默認 1）

**模糊匹配**:

如果精確匹配失敗，系統會自動嘗試模糊匹配。例如：

- 查詢文本：`"系統概述"`
- 實際標題：`"系統概述"`
- 系統會自動找到最相似的標題（相似度 > 0.7）

**示例**:

```json
// 精確匹配第一個 h1 標題 "系統概述"
{
  "type": "heading",
  "selector": {
    "text": "系統概述",
    "level": 1,
    "occurrence": 1
  }
}

// 模糊匹配（如果精確匹配失敗）
{
  "type": "heading",
  "selector": {
    "text": "系統概述",  // 拼寫錯誤，系統會自動嘗試模糊匹配
    "level": 1,
    "occurrence": 1
  }
}
```

#### Anchor Selector（錨點選擇器）

用於定位具有 HTML id 屬性或註解標記的 Block。

```json
{
  "type": "anchor",
  "selector": {
    "anchor_id": "anchor-id"
  }
}
```

#### Block Selector（Block ID 選擇器）

用於通過 Block ID 定位 Block。

```json
{
  "type": "block",
  "selector": {
    "block_id": "block-id"
  }
}
```

---

### Action（操作）

定義要執行的編輯操作。

```json
{
  "mode": "update",
  "content": "新內容",
  "position": "inside"
}
```

**操作模式**:

- `insert`: 插入新內容
- `update`: 更新現有內容
- `delete`: 刪除內容
- `replace`: 替換內容
- `move`: 移動內容（後續迭代）

**位置選項**:

- `before`: 在目標之前
- `after`: 在目標之後
- `inside`: 在目標內部
- `start`: 在目標開始位置
- `end`: 在目標結束位置

---

### Constraints（約束條件）

用於驗證生成內容。

```json
{
  "max_tokens": 500,
  "style_guide": "enterprise-tech-v1",
  "no_external_reference": true
}
```

**約束選項**:

- `max_tokens`: 最大 Token 數（用於長度檢查）
- `style_guide`: 樣式指南名稱（啟用樣式檢查）
- `no_external_reference`: 是否禁止外部參照（啟用外部參照檢查）

---

## 進階驗證

### 樣式檢查

通過 `style_guide` 參數啟用樣式檢查。

**支持的樣式指南**:

- `enterprise-tech-v1`: 企業技術文檔樣式指南

**檢查內容**:

- **語氣檢查**: 禁止第一人稱（我、我們）、禁止命令式語氣
- **術語檢查**: 必須使用標準術語（如果配置了術語表）
- **格式檢查**: 表格標頭、列表格式等

**示例**:

```json
{
  "constraints": {
    "style_guide": "enterprise-tech-v1"
  }
}
```

### 語義漂移檢查

比較原始內容和新內容的語義差異。

**檢查內容**:

- **NER 變更率**: 命名實體的變更率（默認最大 30%）
- **關鍵詞交集比例**: 關鍵詞的重疊比例（默認最小 50%）

**示例**:

語義漂移檢查會在驗證時自動進行（如果提供了原始內容）。

### 外部參照檢查

檢測外部 URL 和未在上下文中的事實。

**示例**:

```json
{
  "constraints": {
    "no_external_reference": true
  }
}
```

---

## 錯誤處理

### 常見錯誤

#### TARGET_NOT_FOUND

目標未找到。

**可能原因**:

- 選擇器值不正確
- 目標不存在於文檔中

**解決方案**:

- 檢查選擇器值
- 使用模糊匹配（系統會自動嘗試）
- 檢查文檔內容

**錯誤響應示例**:

```json
{
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
```

#### VALIDATION_FAILED

驗證失敗。

**可能原因**:

- 樣式違規
- 語義漂移過大
- 外部參照違規
- 長度超標

**解決方案**:

- 檢查錯誤詳情
- 根據建議修正內容
- 調整約束條件

---

## 最佳實踐

### 1. 使用精確的選擇器

優先使用精確的選擇器值，減少模糊匹配的使用：

```json
// ✅ 推薦：使用精確的標題文本和級別
{
  "type": "heading",
  "selector": {
    "text": "系統概述",
    "level": 1,
    "occurrence": 1
  }
}
```

### 2. 合理設置約束條件

根據實際需求設置約束條件：

```json
{
  "constraints": {
    "max_tokens": 500,  // 根據實際需要設置
    "style_guide": "enterprise-tech-v1",  // 只在需要時啟用
    "no_external_reference": true  // 只在需要時啟用
  }
}
```

### 3. 使用 Draft State

對於複雜的編輯操作，建議使用 Draft State：

```bash
# 1. 保存 Draft State
POST /api/v1/document-editing-agent/v2/draft
{
  "doc_id": "doc-123",
  "content": "草稿內容",
  "patches": []
}

# 2. 多次編輯（使用 Draft State）

# 3. Commit 提交
POST /api/v1/document-editing-agent/v2/commit
{
  "doc_id": "doc-123",
  "content": "最終內容"
}
```

### 4. 查看審計日誌

所有編輯操作都會記錄審計日誌，可以用於追蹤和調試：

- 查看編輯歷史
- 調試編輯問題
- 審計和合規

---

## 常見問題

### Q1: 如何處理目標模糊的情況？

如果有多個匹配的目標，系統會返回 `TARGET_AMBIGUOUS` 錯誤，並提供候選列表。可以使用以下方法解決：

1. 使用 `level` 參數限制標題級別
2. 使用 `occurrence` 參數指定第幾個匹配
3. 使用更精確的文本

### Q2: 模糊匹配的相似度閾值是多少？

默認相似度閾值是 0.7（70%）。如果有多個匹配，系統會返回相似度最高的候選列表。

### Q3: 如何啟用進階驗證？

在 `constraints` 中設置 `style_guide` 和 `no_external_reference` 參數：

```json
{
  "constraints": {
    "style_guide": "enterprise-tech-v1",
    "no_external_reference": true
  }
}
```

### Q4: 審計日誌如何查詢？

審計日誌通過審計日誌服務查詢（需要相應的權限）。可以按以下條件查詢：

- `intent_id`: Intent ID
- `patch_id`: Patch ID
- `doc_id`: 文檔 ID
- `event_type`: 事件類型

---

## 參考資料

- API 文檔：`docs/api/document-editing-agent-v2-api.md`
- 模組設計：`docs/系统设计文档/核心组件/IEE對話式開發文件編輯/文件編輯-Agent-模組設計-v2.md`
- 系統規格書：`docs/系统设计文档/核心组件/IEE對話式開發文件編輯/文件編輯-Agent-系統規格書-v2.0.md`
