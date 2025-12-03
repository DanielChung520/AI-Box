# 前端 Agent 註冊新修改方式

## 更新日期：2025-01-27

## 概述

前端 Agent 註冊功能已更新，添加了 Secret 驗證機制，確保外部 Agent 必須通過 AI-Box 簽發的 Secret ID/Key 進行身份驗證後才能註冊。

---

## 主要修改

### 1. 新增 Secret 驗證功能

#### 修改文件：`ai-bot/src/components/AgentRegistrationModal.tsx`

**新增狀態變量**：
```typescript
// Secret 驗證相關狀態
const [secretId, setSecretId] = useState('');
const [secretKey, setSecretKey] = useState('');
const [secretVerified, setSecretVerified] = useState(false);
const [isVerifyingSecret, setIsVerifyingSecret] = useState(false);
const [secretVerificationError, setSecretVerificationError] = useState<string | null>(null);
```

**新增驗證函數**：
```typescript
const handleVerifySecret = async () => {
  // 1. 檢查輸入
  // 2. 調用驗證 API
  // 3. 處理驗證結果
  // 4. 更新驗證狀態
};
```

**修改表單驗證邏輯**：
- 外部 Agent 必須先驗證 Secret 才能提交
- 如果未驗證，會自動切換到端點配置標籤頁並顯示錯誤

### 2. UI 更新 - Secret 驗證區塊

#### 位置：端點配置標籤頁，外部 Agent 配置的最上方

**UI 結構**：
```
┌─────────────────────────────────────────┐
│ 外部 Agent 身份驗證 *                   │
├─────────────────────────────────────────┤
│ ℹ️ 請使用由 AI-Box 簽發的 Secret...     │
│                                         │
│ Secret ID（由 AI-Box 簽發）*           │
│ ┌─────────────────────────────────┐   │
│ │                                 │   │
│ └─────────────────────────────────┘   │
│                                         │
│ Secret Key（由 AI-Box 簽發）*          │
│ ┌─────────────────────────────────┐   │
│ │ ••••••••••••••••••••••••••••••  │   │
│ └─────────────────────────────────┘   │
│                                         │
│ [ 驗證 Secret ] 或 [ 驗證中... ]       │
│                                         │
│ ℹ️ 還沒有 Secret ID？[點擊申請]        │
└─────────────────────────────────────────┘
```

**驗證成功後顯示**：
```
┌─────────────────────────────────────────┐
│ ✅ Secret 驗證成功                      │
│ Secret ID: aibox-example-123...        │
└─────────────────────────────────────────┘
```

### 3. API 集成

#### 修改文件：`ai-bot/src/lib/api.ts`

**新增 API 函數**：
```typescript
// Secret 驗證
export async function verifySecret(
  request: SecretVerificationRequest
): Promise<SecretVerificationResponse>

// 註冊請求中包含 secret_id
export interface AgentRegistrationRequest {
  // ... 其他字段
  permissions?: {
    secret_id?: string;  // 新增
    // ... 其他權限配置
  };
}
```

### 4. 多語言支持

#### 修改文件：`ai-bot/src/hooks/useLanguage.ts`

**新增翻譯鍵值**：
- `agentRegistration.fields.secretAuth` - 外部 Agent 身份驗證
- `agentRegistration.fields.secretId` - Secret ID
- `agentRegistration.fields.secretKey` - Secret Key
- `agentRegistration.hints.secretAuth` - Secret 驗證提示
- `agentRegistration.secretVerified` - Secret 驗證成功
- `agentRegistration.verifySecret` - 驗證 Secret 按鈕
- `agentRegistration.errors.secretRequired` - Secret 必填錯誤
- `agentRegistration.errors.secretInvalid` - Secret 無效錯誤
- `agentRegistration.errors.secretAlreadyBound` - Secret 已綁定錯誤
- `agentRegistration.errors.secretNotVerified` - Secret 未驗證錯誤

### 5. 註冊流程更新

#### 修改的驗證流程：

**之前**：
1. 填寫基本信息
2. 配置端點
3. 配置權限（可選）
4. 提交註冊

**現在**（外部 Agent）：
1. 填寫基本信息
2. 配置端點
3. **驗證 Secret** ⭐（新增必需步驟）
4. 配置協議和端點 URL
5. 配置權限（可選）
6. 提交註冊（包含 Secret ID）

---

## 使用方式

### 外部 Agent 註冊步驟

1. **打開註冊頁面**
   - 瀏覽代理頁面 → 點擊「管理」按鈕

2. **填寫基本資訊**
   - Agent ID、名稱、類型等

3. **切換到端點配置標籤頁**
   - 取消勾選「內部 Agent」

4. **驗證 Secret** ⭐
   - 輸入 Secret ID
   - 輸入 Secret Key
   - 點擊「驗證 Secret」
   - 等待驗證結果

5. **配置端點**
   - 選擇協議類型
   - 輸入端點 URL

6. **配置權限**（可選）
   - IP 白名單
   - 其他認證方式

7. **提交註冊**
   - 點擊「註冊 Agent」

### 內部 Agent 註冊

內部 Agent 註冊流程保持不變，不需要 Secret 驗證。

---

## 技術細節

### 驗證流程

```typescript
用戶輸入 Secret → 前端驗證（必填檢查）
    ↓
調用 verifySecret API
    ↓
後端驗證 Secret ID/Key
    ↓
返回驗證結果
    ↓
前端更新狀態（verified/error）
    ↓
提交註冊時包含 secret_id
    ↓
後端綁定 Secret 到 Agent ID
```

### 錯誤處理

- **輸入錯誤**：顯示紅色錯誤提示框
- **驗證失敗**：顯示具體錯誤原因
- **已綁定**：提示 Secret 已被使用
- **網絡錯誤**：提示稍後重試

---

## 文件變更清單

### 修改的文件

1. `ai-bot/src/components/AgentRegistrationModal.tsx`
   - 添加 Secret 驗證狀態和邏輯
   - 添加 Secret 驗證 UI 區塊
   - 更新表單驗證邏輯

2. `ai-bot/src/lib/api.ts`
   - 添加 `verifySecret` 函數
   - 更新 `AgentRegistrationRequest` 類型（添加 `secret_id`）

3. `ai-bot/src/hooks/useLanguage.ts`
   - 添加所有 Secret 相關的翻譯鍵值

### 新增的 API 端點

- `POST /api/v1/agents/secrets/verify` - 驗證 Secret
- `POST /api/v1/agents/secrets/generate` - 生成 Secret（測試用）

---

## 向後兼容性

- ✅ 內部 Agent 註冊流程完全兼容
- ✅ 現有的外部 Agent 仍可使用其他認證方式（API Key、mTLS 等）
- ✅ Secret 驗證是可選的，但強烈推薦使用

---

## 後續計劃（Phase 2）

- [ ] Secret 申請頁面
- [ ] 申請狀態查詢
- [ ] 管理員審批界面
- [ ] 郵件通知系統

---

## 總結

這次更新為前端 Agent 註冊添加了：

1. ✅ **Secret 驗證機制** - 確保安全的身份驗證
2. ✅ **友好的 UI 設計** - 清晰的步驟引導
3. ✅ **完善的錯誤處理** - 詳細的錯誤提示
4. ✅ **多語言支持** - 三種語言完整支持

所有修改已完成並通過測試，可以立即使用。
