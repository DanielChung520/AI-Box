# Secret ID/Key 獲取方式完整指南

## 更新日期：2025-01-27

## ✅ 確認：沒有 Secret ID/Key 則退出註冊

**外部 Agent 如果無法提供 Secret ID/Key，註冊程序會被阻止並退出。**

### 驗證機制

1. **前端驗證**：未驗證 Secret 無法提交註冊表單
2. **後端驗證**：沒有 Secret ID 返回 HTTP 400 錯誤

---

## Secret ID/Key 獲取方式建議

### 方案一：Phase 1 - 當前可用方式

#### 1. API 生成（測試/開發環境）

**端點**：`POST /api/v1/agents/secrets/generate`

**使用方式**：

**方式 A：通過 Swagger 文檔**

1. 訪問 `http://localhost:8000/docs`
2. 找到 `POST /api/v1/agents/secrets/generate` 端點
3. 點擊 "Try it out"
4. 輸入組織名稱（可選）：`{"organization": "Your Org"}`
5. 執行請求
6. 複製返回的 `secret_id` 和 `secret_key`

**方式 B：通過 curl 命令**

```bash
curl -X POST "http://localhost:8000/api/v1/agents/secrets/generate" \
  -H "Content-Type: application/json" \
  -d '{"organization": "Your Organization"}'
```

**方式 C：通過 Python 腳本**

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/agents/secrets/generate",
    json={"organization": "Your Organization"}
)
result = response.json()
print(f"Secret ID: {result['data']['secret_id']}")
print(f"Secret Key: {result['data']['secret_key']}")
```

**注意事項**：

- ⚠️ 僅用於測試和開發環境
- ⚠️ Secret Key 只在生成時返回一次，請妥善保管
- ⚠️ 生產環境應使用審批流程

#### 2. 聯繫管理員（生產環境）

- 直接聯繫 AI-Box 管理員
- 說明申請原因、組織信息、使用場景
- 管理員手動生成並通過安全渠道發送 Secret ID/Key

---

### 方案二：Phase 2 - 完整申請審批流程（推薦）

#### 申請流程設計

```
┌─────────────────────────────────────────┐
│  步驟 1：外部 Agent 提供者提交申請      │
│  - 填寫申請表單                         │
│  - 組織/公司名稱                        │
│  - 聯繫人信息和郵箱                     │
│  - Agent 服務描述                       │
│  - 預期使用場景                         │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  步驟 2：AI-Box 管理員審核申請          │
│  - 查看申請詳情                         │
│  - 驗證組織合法性                       │
│  - 批准或拒絕                           │
│  - 填寫審核備註                         │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  步驟 3：審核通過後自動處理             │
│  - AI-Box 自動生成 Secret ID/Key        │
│  - 通過郵件發送給申請者                 │
│  - 更新申請狀態為「已簽發」             │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  步驟 4：申請者使用 Secret 註冊 Agent   │
│  - 收到郵件通知                         │
│  - 在註冊頁面輸入 Secret ID/Key         │
│  - 驗證並完成註冊                       │
└─────────────────────────────────────────┘
```

#### 實施內容

1. **申請表單頁面**
   - 組織/公司名稱（必填）
   - 聯繫人姓名（必填）
   - 聯繫郵箱（必填，驗證格式）
   - Agent 服務描述（必填）
   - 預期使用場景（可選）

2. **管理員審批界面**
   - 申請列表（支持篩選：待審核/已批准/已拒絕）
   - 申請詳情查看
   - 批准/拒絕操作
   - 審核備註輸入

3. **郵件通知系統**
   - 申請提交通知（給管理員）
   - 審批結果通知（給申請者）
   - Secret 簽發通知（包含 Secret ID/Key）

4. **申請狀態查詢**
   - 申請者可以查詢申請狀態
   - 查看審核結果和備註

---

## 推薦實施方案

### 方案 A：快速申請 Modal（Phase 1.5 - 可立即實現）

在註冊頁面中，點擊「點擊這裡申請」時，彈出申請 Modal。

#### 開發環境模式

```typescript
// 快速生成 Secret（僅開發環境）
const handleQuickGenerate = async () => {
  const orgName = prompt('請輸入組織名稱:');
  if (orgName) {
    const response = await generateSecret(orgName);
    setSecretId(response.data.secret_id);
    setSecretKey(response.data.secret_key);
    // 自動驗證
    await handleVerifySecret();
  }
};
```

#### 生產環境模式

```typescript
// 提交申請（生產環境）
const handleSubmitApplication = async (formData) => {
  // 提交申請到後端
  await applyForSecret(formData);
  // 顯示提示：已提交申請，等待審批
};
```

**優點**：

- ✅ 快速實現
- ✅ 用戶體驗好
- ✅ 無需跳轉頁面
- ✅ 支持開發和生產兩種模式

### 方案 B：獨立申請頁面（Phase 2 - 完整流程）

創建專門的 Secret 申請頁面（`/secret-application`），包含：

- 完整的申請表單
- 申請狀態查詢
- 歷史申請記錄
- 申請詳情查看

---

## 前端 UI 改進建議

### 當前狀態

在註冊頁面的 Secret 驗證區塊：

```
還沒有 Secret ID？[點擊這裡申請]
```

目前點擊後顯示 alert 提示。

### 建議改進：添加申請 Modal

#### 開發環境：快速生成

```typescript
// 彈出快速生成 Modal
<SecretQuickGenerateModal
  isOpen={showQuickGenerate}
  onClose={() => setShowQuickGenerate(false)}
  onSuccess={(secretId, secretKey) => {
    setSecretId(secretId);
    setSecretKey(secretKey);
    // 可選：自動驗證
  }}
/>
```

#### 生產環境：申請表單

```typescript
// 彈出申請 Modal
<SecretApplicationModal
  isOpen={showApplication}
  onClose={() => setShowApplication(false)}
  onSuccess={() => {
    // 顯示提示：申請已提交，請等待審批通知
  }}
/>
```

---

## 實施建議總結

### Phase 1.5：快速實現（推薦立即實施）

**目標**：讓用戶可以在註冊頁面直接獲取 Secret

**實現內容**：

1. 創建 `SecretQuickGenerateModal` 組件
2. 開發環境：直接調用 `generateSecret` API
3. 生產環境：顯示申請表單或提示聯繫管理員
4. 成功後自動填入 Secret ID/Key

**時間**：1-2 小時

### Phase 2：完整流程（後續實現）

**目標**：完整的申請審批流程

**實現內容**：

1. 申請表單和提交功能
2. 管理員審批界面
3. 郵件通知系統
4. 申請狀態查詢

**時間**：1-2 天

---

## 獲取方式對比

| 方式 | 適用環境 | 優點 | 缺點 | 狀態 |
|------|---------|------|------|------|
| API 生成 | 測試/開發 | 快速、便捷 | 無審批，不安全 | ✅ 已實現 |
| 聯繫管理員 | 生產環境 | 人工審核 | 效率低，流程不規範 | ✅ 當前可用 |
| 申請審批流程 | 生產環境 | 規範、可追溯、自動化 | 需要開發時間 | 🔄 Phase 2 |

---

## 總結

### Secret 獲取方式建議

1. **開發/測試環境**：
   - 使用 `POST /api/v1/agents/secrets/generate` API
   - 或通過 Swagger 文檔生成

2. **生產環境（當前）**：
   - 聯繫 AI-Box 管理員
   - 管理員手動生成並發送

3. **生產環境（未來 Phase 2）**：
   - 通過申請審批流程
   - 自動化生成和分發

### 註冊要求確認

- ✅ **外部 Agent 必須提供 Secret ID/Key**
- ✅ **沒有 Secret → 無法註冊，程序退出**
- ✅ **必須先驗證 Secret 才能提交註冊**
