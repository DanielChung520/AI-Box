# Agent 生命週期管理文檔

## 更新日期：2025-01-27

## 創建人：Daniel Chung

## 最後修改日期：2025-01-27

---

## 概述

本文檔說明 Agent 在 AI-Box 平台中的完整生命週期流程，包括狀態定義、狀態轉換規則、權限控制和操作流程。

---

## Agent 狀態定義

Agent 在系統中可以處於以下四種狀態之一：

### 1. 註冊中 (REGISTERING)

- **狀態值**：`registering`
- **描述**：Agent 開發者已提交註冊申請，等待 AI-Box 管理單位核准
- **特點**：
  - 剛註冊的 Agent 默認處於此狀態
  - 無法被其他系統調用
  - 可以查看但無法執行任務

### 2. 在線 (ONLINE)

- **狀態值**：`online`
- **描述**：Agent 已通過管理單位核准，可以正常使用
- **特點**：
  - 可以接受任務請求
  - 可以執行任務
  - 可以接收心跳更新
  - 可以被其他系統調用

### 3. 維修中 (MAINTENANCE)

- **狀態值**：`maintenance`
- **描述**：Agent 正在進行維護或更新
- **特點**：
  - 暫時無法接受新任務
  - 正在執行的任務可以繼續完成
  - 可以查看狀態和配置

### 4. 已作廢 (DEPRECATED)

- **狀態值**：`deprecated`
- **描述**：Agent 已被標記為作廢，不再使用
- **特點**：
  - 無法接受新任務
  - 無法執行任務
  - 保留歷史記錄
  - 需要重新註冊才能恢復使用

---

## 狀態轉換流程圖

```
┌─────────────┐
│  註冊中      │
│ REGISTERING │
└──────┬──────┘
       │
       │ [管理單位核准]
       ▼
┌─────────────┐
│   在線       │◄────┐
│   ONLINE    │     │
└──────┬──────┘     │
       │            │
       │ [開發者操作]│
       │            │
       ├────────────┘
       │
       ├─────► ┌─────────────┐
       │       │  維修中      │
       │       │ MAINTENANCE │
       │       └─────────────┘
       │
       └─────► ┌─────────────┐
               │  已作廢      │
               │ DEPRECATED  │
               └─────────────┘
```

---

## 狀態轉換規則

### 1. 註冊流程

**觸發者**：Agent 開發者
**操作**：提交 Agent 註冊申請
**結果**：Agent 狀態自動設為 `REGISTERING`

**規則**：
- 註冊時必須提供完整的 Agent 信息（ID、名稱、類型、端點等）
- 外部 Agent 必須提供有效的 Secret ID 和 Secret Key
- 註冊後立即進入「註冊中」狀態

### 2. 核准流程

**觸發者**：AI-Box 管理單位（管理員權限）
**操作**：核准註冊申請
**結果**：Agent 狀態從 `REGISTERING` 轉為 `ONLINE`

**權限要求**：
- 必須擁有管理員權限（`admin` 或 `agent:approve`）
- 只有管理員可以將 Agent 從「註冊中」轉為「在線」

**規則**：
- 管理員可以核准或拒絕註冊申請
- 核准後 Agent 立即變為「在線」狀態，可以開始接受任務
- 拒絕後 Agent 可以重新提交註冊申請

### 3. 設置維修狀態

**觸發者**：Agent 開發者
**操作**：將「在線」的 Agent 設置為「維修中」
**結果**：Agent 狀態從 `ONLINE` 轉為 `MAINTENANCE`

**權限要求**：
- Agent 開發者（Agent 的擁有者）
- 管理員權限

**規則**：
- 只有「在線」狀態的 Agent 可以被設置為「維修中」
- 設置為「維修中」後，Agent 不再接受新任務
- 正在執行的任務可以繼續完成

### 4. 設置作廢狀態

**觸發者**：Agent 開發者
**操作**：將 Agent 標記為「已作廢」
**結果**：Agent 狀態從 `ONLINE` 或 `MAINTENANCE` 轉為 `DEPRECATED`

**權限要求**：
- Agent 開發者（Agent 的擁有者）
- 管理員權限

**規則**：
- 可以從「在線」或「維修中」狀態轉為「已作廢」
- 作廢後 Agent 完全停止服務
- 保留所有歷史記錄和配置信息

### 5. 恢復服務（重新註冊）

**觸發者**：Agent 開發者
**操作**：重新提交註冊申請
**結果**：Agent 狀態從 `MAINTENANCE` 或 `DEPRECATED` 轉為 `REGISTERING`

**規則**：
- 「維修中」或「已作廢」的 Agent 無法直接恢復服務
- 必須重新提交註冊申請，進入「註冊中」狀態
- 重新註冊後需要管理員再次核准才能轉為「在線」

---

## 權限控制

### 管理單位（管理員）權限

- ✅ 核准 Agent 註冊申請（`REGISTERING` → `ONLINE`）
- ✅ 拒絕 Agent 註冊申請（`REGISTERING` → `DEPRECATED`）
- ✅ 查看所有 Agent 的狀態和配置
- ✅ 將任何 Agent 設置為「維修中」或「已作廢」
- ✅ 管理 Agent 權限配置

### Agent 開發者權限

- ✅ 註冊新的 Agent（創建 `REGISTERING` 狀態的 Agent）
- ✅ 查看自己開發的 Agent 信息
- ✅ 將「在線」的 Agent 設置為「維修中」
- ✅ 將「在線」或「維修中」的 Agent 設置為「已作廢」
- ✅ 重新註冊「維修中」或「已作廢」的 Agent
- ❌ 無法直接將「註冊中」的 Agent 轉為「在線」（需要管理員核准）
- ❌ 無法直接恢復「維修中」或「已作廢」的 Agent（需要重新註冊）

---

## API 端點

### 1. 註冊 Agent

**端點**：`POST /api/agents/register`
**描述**：註冊新的 Agent，狀態自動設為「註冊中」
**權限**：已認證用戶

**請求示例**：
```json
{
  "agent_id": "my-agent-001",
  "agent_type": "execution",
  "name": "My Agent",
  "endpoints": {
    "http": "https://example.com/agent",
    "is_internal": false
  },
  "capabilities": ["tool_execution"],
  "permissions": {
    "secret_id": "secret-123",
    "allowed_tools": ["tool1", "tool2"]
  }
}
```

**響應**：
```json
{
  "success": true,
  "data": {
    "agent_id": "my-agent-001",
    "status": "registering"
  },
  "message": "Agent registered successfully. Waiting for admin approval."
}
```

### 2. 核准 Agent 註冊

**端點**：`POST /api/agents/{agent_id}/approve`
**描述**：管理員核准 Agent 註冊申請
**權限**：管理員（`admin` 或 `agent:approve`）

**請求示例**：
```json
{
  "approved": true,
  "comment": "Approved after security review"
}
```

**響應**：
```json
{
  "success": true,
  "data": {
    "agent_id": "my-agent-001",
    "status": "online"
  },
  "message": "Agent approved successfully"
}
```

### 3. 更新 Agent 狀態（開發者）

**端點**：`PUT /api/agents/{agent_id}/status`
**描述**：Agent 開發者更新 Agent 狀態
**權限**：Agent 開發者或管理員

**狀態轉換規則**：
- `ONLINE` → `MAINTENANCE`：允許
- `ONLINE` → `DEPRECATED`：允許
- `MAINTENANCE` → `DEPRECATED`：允許
- 其他轉換：需要管理員權限

**請求示例**：
```json
{
  "status": "maintenance"
}
```

**響應**：
```json
{
  "success": true,
  "data": {
    "agent_id": "my-agent-001",
    "status": "maintenance"
  },
  "message": "Agent status updated successfully"
}
```

### 4. 查詢 Agent 狀態

**端點**：`GET /api/agents/{agent_id}`
**描述**：查詢 Agent 的詳細信息，包括當前狀態
**權限**：已認證用戶

---

## 狀態顯示

### 前端狀態標籤

- **註冊中**：灰色標籤（`bg-gray-500`），文字：「註冊中」或「等待核准」
- **在線**：綠色標籤（`bg-green-500`），文字：「在線」
- **維修中**：黃色標籤（`bg-yellow-500`），文字：「維修中」
- **已作廢**：紅色標籤（`bg-red-500`），文字：「已作廢」

### 狀態過濾

在 Agent 列表中，可以根據狀態進行過濾：
- 顯示所有狀態
- 只顯示「在線」的 Agent（用於任務執行）
- 只顯示「註冊中」的 Agent（用於管理員審核）

---

## 使用場景示例

### 場景 1：新 Agent 註冊

1. 開發者提交 Agent 註冊申請
2. Agent 自動進入「註冊中」狀態
3. 管理員收到通知，審核註冊申請
4. 管理員核准後，Agent 轉為「在線」狀態
5. Agent 可以開始接受任務請求

### 場景 2：Agent 維護

1. 開發者發現 Agent 需要更新
2. 開發者將 Agent 狀態從「在線」改為「維修中」
3. Agent 停止接受新任務
4. 正在執行的任務繼續完成
5. 開發者完成維護後，重新提交註冊申請
6. 管理員核准後，Agent 重新上線

### 場景 3：Agent 作廢

1. 開發者決定停止使用某個 Agent
2. 開發者將 Agent 狀態從「在線」改為「已作廢」
3. Agent 完全停止服務
4. 保留所有歷史記錄
5. 若需要恢復，開發者需要重新註冊

---

## 注意事項

1. **狀態持久化**：Agent 狀態會持久化到數據庫，系統重啟後狀態保持不變

2. **權限驗證**：所有狀態轉換操作都會進行權限驗證，確保只有授權用戶可以執行

3. **審計日誌**：所有狀態變更都會記錄審計日誌，包括：
   - 操作時間
   - 操作者
   - 狀態變更（從 → 到）
   - 操作原因（如果有）

4. **任務處理**：
   - 「註冊中」狀態的 Agent 不會被分配到任務
   - 「維修中」狀態的 Agent 不會接受新任務
   - 「已作廢」狀態的 Agent 不會被分配到任務

5. **重新註冊**：
   - 重新註冊時可以保留原 Agent ID 或使用新 ID
   - 歷史記錄和配置信息會保留
   - 需要重新通過管理員核准

---

## 相關文檔

- [Agent 註冊指南](./AGENT_REGISTRATION_GUIDE.md)
- [Agent 權限管理](./AGENT_PERMISSIONS.md)
- [API 參考文檔](./API_REFERENCE.md)

---

**最後更新**：2025-01-27
