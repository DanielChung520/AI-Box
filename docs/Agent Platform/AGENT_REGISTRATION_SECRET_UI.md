# Agent 註冊 - Secret 輸入 UI 說明

## 更新日期：2025-01-27

## 確認：前端已提供 Secret ID/Key 輸入

✅ **前端 Agent 註冊頁面已在端點配置標籤頁提供 Secret ID/Key 輸入框。**

---

## UI 位置和結構

### 標籤頁：端點配置（Endpoints Configuration）

當用戶選擇「外部 Agent」時，會在端點配置標籤頁的最上方顯示 Secret 驗證區塊。

### UI 層級結構

```
端點配置標籤頁
├── 內部 Agent 選項（勾選框）
└── 外部 Agent 配置區塊（取消勾選「內部 Agent」後顯示）
    ├── Secret 驗證區塊 ⭐
    │   ├── 標題：「外部 Agent 身份驗證」*
    │   ├── 提示文字
    │   ├── Secret ID 輸入框
    │   ├── Secret Key 輸入框（密碼類型）
    │   ├── 「驗證 Secret」按鈕
    │   ├── 錯誤提示區域
    │   └── 「還沒有 Secret ID？點擊這裡申請」鏈接
    ├── 協議類型選擇（HTTP/MCP）
    └── 端點 URL 輸入框
```

---

## Secret 輸入框詳細說明

### 1. Secret ID 輸入框

**位置**：端點配置標籤頁，Secret 驗證區塊內

**屬性**：

- **類型**：`text`（文本輸入框）
- **標籤**：`Secret ID（由 AI-Box 簽發）`
- **佔位符**：`例如：aibox-example-1234567890-abc123`
- **必填**：是（外部 Agent 必需）
- **禁用條件**：提交中或正在驗證 Secret

**代碼位置**：`ai-bot/src/components/AgentRegistrationModal.tsx` 第 525-536 行

### 2. Secret Key 輸入框

**位置**：端點配置標籤頁，Secret 驗證區塊內

**屬性**：

- **類型**：`password`（密碼輸入框，隱藏輸入）
- **標籤**：`Secret Key（由 AI-Box 簽發）`
- **佔位符**：`輸入 Secret Key`
- **必填**：是（外部 Agent 必需）
- **禁用條件**：提交中或正在驗證 Secret

**代碼位置**：`ai-bot/src/components/AgentRegistrationModal.tsx` 第 542-553 行

### 3. 驗證按鈕

**位置**：Secret Key 輸入框下方

**功能**：

- 調用 `verifySecret` API 驗證 Secret ID/Key
- 驗證中顯示載入狀態
- 驗證成功後顯示綠色成功提示
- 驗證失敗顯示錯誤信息

**代碼位置**：`ai-bot/src/components/AgentRegistrationModal.tsx` 第 561-577 行

---

## 完整 UI 流程

### 步驟 1：打開註冊頁面

用戶點擊「管理」按鈕，打開 Agent 註冊 Modal。

### 步驟 2：填寫基本資訊

在「基本資訊」標籤頁填寫 Agent 信息。

### 步驟 3：切換到端點配置

點擊「端點配置」標籤頁。

### 步驟 4：選擇外部 Agent

取消勾選「內部 Agent（運行在同一系統中）」。

### 步驟 5：輸入 Secret（新增的區塊）

立即顯示 Secret 驗證區塊：

```
┌─────────────────────────────────────────┐
│ 外部 Agent 身份驗證 *                   │
├─────────────────────────────────────────┤
│ ℹ️ 請使用由 AI-Box 簽發的 Secret...     │
│                                         │
│ Secret ID（由 AI-Box 簽發）            │
│ ┌─────────────────────────────────┐   │
│ │                                 │   │
│ └─────────────────────────────────┘   │
│                                         │
│ Secret Key（由 AI-Box 簽發）           │
│ ┌─────────────────────────────────┐   │
│ │ ••••••••••••••••••••••••••••••  │   │
│ └─────────────────────────────────┘   │
│                                         │
│ [ 驗證 Secret ]                        │
│                                         │
│ ℹ️ 還沒有 Secret ID？[點擊這裡申請]    │
└─────────────────────────────────────────┘
```

### 步驟 6：驗證 Secret

1. 輸入 Secret ID
2. 輸入 Secret Key（隱藏顯示）
3. 點擊「驗證 Secret」按鈕
4. 等待驗證結果

### 步驟 7：驗證成功

顯示綠色成功提示框：

```
┌─────────────────────────────────────────┐
│ ✅ Secret 驗證成功                      │
│ Secret ID: aibox-test-...              │
└─────────────────────────────────────────┘
```

### 步驟 8：繼續配置

驗證成功後，繼續配置協議類型和端點 URL。

---

## 代碼實現位置

### 組件文件

- **文件**：`ai-bot/src/components/AgentRegistrationModal.tsx`
- **標籤頁**：`activeTab === 'endpoints'`
- **條件顯示**：`!isInternal`

### Secret 輸入框

- **Secret ID**：第 525-536 行
- **Secret Key**：第 542-553 行
- **驗證按鈕**：第 561-577 行
- **驗證函數**：第 118-148 行（`handleVerifySecret`）

### 狀態管理

- `secretId`：Secret ID 輸入值
- `secretKey`：Secret Key 輸入值
- `secretVerified`：驗證狀態
- `isVerifyingSecret`：正在驗證標誌
- `secretVerificationError`：驗證錯誤信息

---

## 測試用 Secret

可以使用以下測試用 Secret 進行驗證：

**Secret ID**: `aibox-test-1764743150-1fc4e7ed`
**Secret Key**: `JpPMAnB655E9rW50sKW4PaGVciRP4vpvUEzRnJ6i9y0`

（需要先在 `.env` 文件中配置 `AGENT_SECRET_ID` 和 `AGENT_SECRET_KEY`）

---

## 總結

✅ **前端已完整實現 Secret ID/Key 輸入功能**：

1. ✅ 在「端點配置」標籤頁提供 Secret 輸入區塊
2. ✅ Secret ID 文本輸入框
3. ✅ Secret Key 密碼輸入框（隱藏顯示）
4. ✅ 驗證按鈕和狀態顯示
5. ✅ 錯誤提示和成功提示
6. ✅ 驗證通過後才能繼續註冊

**位置**：端點配置標籤頁 → 外部 Agent 配置區塊 → Secret 驗證區塊

**最後更新**：2025-01-27
