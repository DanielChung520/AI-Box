# 文件編輯 API 文檔

**版本**: 1.0
**創建日期**: 2026-01-06
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-06

---

## 📋 概述

文件編輯 API 提供基於 Agent 系統的智能文件編輯功能，支持流式編輯和實時預覽。本文檔描述所有相關的 API 端點、請求/響應格式和使用示例。

---

## 🔗 API 端點

### 1. 創建編輯 Session

**端點**: `POST /api/v1/editing/session/start`

**描述**: 創建一個新的編輯 Session，用於管理文件編輯會話。

**請求體**:

```json
{
  "doc_id": "file-123",
  "ttl_seconds": 3600
}
```

**參數說明**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `doc_id` | string | ✅ | 文件 ID |
| `ttl_seconds` | integer | ❌ | Session 過期時間（秒），默認 3600（1小時） |

**響應**:

```json
{
  "success": true,
  "data": {
    "session_id": "session-123",
    "ws_url": null
  }
}
```

**錯誤響應**:

```json
{
  "success": false,
  "error": "File not found",
  "error_code": "FILE_NOT_FOUND",
  "status_code": 404
}
```

---

### 2. 提交編輯指令

**端點**: `POST /api/v1/editing/command`

**描述**: 提交編輯指令到 Agent 系統，觸發文件編輯。

**請求體**:

```json
{
  "session_id": "session-123",
  "command": "在開頭添加一個標題",
  "cursor_context": {
    "position": 0,
    "line": 1,
    "column": 0
  }
}
```

**參數說明**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `session_id` | string | ✅ | 編輯 Session ID |
| `command` | string | ✅ | 編輯指令（自然語言） |
| `cursor_context` | object | ❌ | 游標上下文信息 |

**cursor_context 字段**:

| 字段 | 類型 | 說明 |
|------|------|------|
| `position` | integer | 字符位置 |
| `line` | integer | 行號 |
| `column` | integer | 列號 |
| `selection` | string | 選中的文本 |

**響應**:

```json
{
  "success": true,
  "data": {
    "request_id": "request-123",
    "status": "queued"
  }
}
```

**錯誤響應**:

```json
{
  "success": false,
  "error": "Session not found",
  "error_code": "SESSION_NOT_FOUND",
  "status_code": 404
}
```

---

### 3. 流式編輯輸出

**端點**: `GET /api/v1/streaming/editing/{session_id}/stream`

**描述**: 通過 Server-Sent Events (SSE) 流式接收編輯 patches。

**路徑參數**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `session_id` | string | ✅ | 編輯 Session ID |

**查詢參數**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `request_id` | string | ❌ | 編輯請求 ID（可選） |

**響應格式**: `text/event-stream`

**事件類型**:

1. **patch_start**: 開始新的 patch 流

```
data: {"type":"patch_start","data":{}}

```

2. **patch_chunk**: patch 數據塊

```
data: {"type":"patch_chunk","data":{"chunk":"{\"patches\":[{\"search_block\":\""}}

```

3. **patch_end**: patch 結束

```
data: {"type":"patch_end","data":{"request_id":"request-123"}}

```

4. **error**: 錯誤信息

```
data: {"type":"error","data":{"error":"Error message"}}

```

**完整示例**:

```javascript
const eventSource = new EventSource('/api/v1/streaming/editing/session-123/stream?request_id=request-123');

eventSource.addEventListener('patch_start', (event) => {
  console.log('Patch stream started');
});

eventSource.addEventListener('patch_chunk', (event) => {
  const data = JSON.parse(event.data);
  console.log('Received chunk:', data.data.chunk);
});

eventSource.addEventListener('patch_end', (event) => {
  const data = JSON.parse(event.data);
  console.log('Patch stream completed:', data.data.request_id);
  eventSource.close();
});

eventSource.addEventListener('error', (event) => {
  const data = JSON.parse(event.data);
  console.error('Stream error:', data.data.error);
  eventSource.close();
});
```

---

### 4. 應用編輯修改

**端點**: `POST /api/v1/docs/{request_id}/apply`

**描述**: 將編輯修改應用到文件，保存到後端存儲。

**路徑參數**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `request_id` | string | ✅ | 編輯請求 ID |

**請求體**:

```json
{
  "summary": "添加了標題並優化了內容"
}
```

**參數說明**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `summary` | string | ❌ | 變更摘要（可選） |

**響應**:

```json
{
  "success": true,
  "data": {
    "new_version": 2,
    "file_id": "file-123",
    "timestamp": "2026-01-06T15:30:00Z"
  }
}
```

**錯誤響應**:

```json
{
  "success": false,
  "error": "Base version mismatch",
  "error_code": "BASE_VERSION_MISMATCH",
  "status_code": 409,
  "details": {
    "current_version": 2,
    "base_version": 1
  }
}
```

---

## 📝 數據格式

### Search-and-Replace Patch 格式

```json
{
  "patches": [
    {
      "search_block": "原始文本內容",
      "replace_block": "修改後的文本內容"
    }
  ],
  "thought_chain": "思考過程說明（可選）"
}
```

**字段說明**:

| 字段 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `patches` | array | ✅ | Patch 數組 |
| `patches[].search_block` | string | ✅ | 需要被替換的原始文本 |
| `patches[].replace_block` | string | ✅ | 修改後的新文本 |
| `thought_chain` | string | ❌ | AI 思考過程說明 |

---

## 🔢 錯誤碼

| 錯誤碼 | HTTP 狀態碼 | 說明 |
|--------|------------|------|
| `FILE_NOT_FOUND` | 404 | 文件不存在 |
| `SESSION_NOT_FOUND` | 404 | Session 不存在 |
| `SESSION_ACCESS_DENIED` | 403 | Session 訪問被拒絕 |
| `BASE_VERSION_MISMATCH` | 409 | 文件版本衝突 |
| `INVALID_FILE_TYPE` | 400 | 無效的文件類型（僅支持 Markdown） |
| `INVALID_PATCH_FORMAT` | 400 | 無效的 Patch 格式 |

---

## 💡 使用示例

### 完整編輯流程

```javascript
// 1. 創建編輯 Session
const sessionResponse = await fetch('/api/v1/editing/session/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ doc_id: 'file-123' })
});
const { session_id } = await sessionResponse.json();

// 2. 提交編輯指令
const commandResponse = await fetch('/api/v1/editing/command', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id,
    command: '在開頭添加一個標題',
    cursor_context: { position: 0 }
  })
});
const { request_id } = await commandResponse.json();

// 3. 連接流式輸出
const eventSource = new EventSource(
  `/api/v1/streaming/editing/${session_id}/stream?request_id=${request_id}`
);

let patches = [];
eventSource.addEventListener('patch_chunk', (event) => {
  const data = JSON.parse(event.data);
  // 累積和解析 patches
  // ...
});

eventSource.addEventListener('patch_end', async () => {
  // 4. 應用編輯修改
  await fetch(`/api/v1/docs/${request_id}/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ summary: '添加了標題' })
  });

  eventSource.close();
});
```

---

## 🔒 認證與權限

所有 API 端點都需要：

- **認證**: JWT Token（通過 `Authorization: Bearer <token>` header）
- **租戶隔離**: 自動從 Token 中提取 `tenant_id`
- **權限檢查**: 用戶必須有文件編輯權限

---

## 📊 性能優化

### 大文件處理

- 文件大小 > 10MB 時，只傳遞游標附近的上下文窗口（前後各 2000 字符）
- 自動檢測並記錄大文件警告日誌

### 流式傳輸優化

- 根據數據大小動態調整 chunk_size 和延遲
- 小數據（< 10KB）使用較短延遲（10ms）
- 大數據使用標準延遲（50ms）

---

## 🔗 相關文檔

- [文件編輯 Agent 開發規劃書](../核心组件/IEE對話式開發文件編輯/文件編輯Agent開發規劃書.md)
- [IEE 編輯器操作說明](../核心组件/IEE對話式開發文件編輯/IEE編輯器操作說明.md)

---

**最後更新日期**: 2026-01-06
**文檔版本**: 1.0
**維護人**: Daniel Chung
