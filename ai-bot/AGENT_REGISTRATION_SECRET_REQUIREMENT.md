# Agent 註冊 Secret 驗證要求說明

## 更新日期：2025-01-27

## 核心問題回答

**問：在 Agent 註冊時，是否要提供 Secret ID/Key，若沒有才進行註冊程序？**

**答：是的，外部 Agent 必須提供並驗證 Secret ID/Key 後，才能進行註冊程序。如果沒有 Secret ID/Key，註冊會被阻止。**

---

## 當前實現邏輯

### 1. 前端驗證（必須通過）

**位置**：`ai-bot/src/components/AgentRegistrationModal.tsx`

```typescript
// 外部 Agent 驗證
if (!isInternal) {
  // 優先檢查 Secret 驗證
  if (!secretVerified) {
    setError('請先驗證 Secret ID 和 Secret Key');
    setActiveTab('endpoints'); // 切換到端點配置標籤頁
    return false; // ❌ 阻止提交
  }
  // ... 其他驗證
}
```

**要求**：
- ✅ 外部 Agent **必須**先驗證 Secret（`secretVerified` 必須為 `true`）
- ✅ 未驗證 Secret 無法提交註冊表單
- ✅ 驗證通過後才能繼續填寫其他信息

### 2. 後端驗證（必須通過）

**位置**：`api/routers/agent_registry.py`

```python
# 對於外部 Agent，驗證認證配置
if not request.endpoints.is_internal:
    permissions = request.permissions or AgentPermissionConfig()

    # Phase 1: 外部 Agent 必須提供 Secret ID（強制要求）
    if not permissions.secret_id:
        raise HTTPException(
            status_code=400,
            detail="External agent must provide Secret ID for authentication...",
        )

    # 驗證 Secret ID 是否存在和有效
    secret_info = secret_manager.get_secret_info(permissions.secret_id)
    if not secret_info:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Secret ID: '{permissions.secret_id}'...",
        )

    # 驗證 Secret ID 是否已綁定
    if secret_manager.is_secret_bound(permissions.secret_id):
        raise HTTPException(
            status_code=400,
            detail=f"Secret ID '{permissions.secret_id}' is already bound...",
        )
```

**要求**：
- ✅ 外部 Agent **必須**提供 `permissions.secret_id`
- ✅ Secret ID 必須存在且有效
- ✅ Secret ID 必須未綁定到其他 Agent
- ❌ 沒有 Secret ID → 註冊失敗（HTTP 400）

---

## 完整註冊流程

### 外部 Agent 註冊流程

```
1. 打開註冊頁面
   ↓
2. 填寫基本資訊
   ↓
3. 切換到「端點配置」標籤頁
   ↓
4. 取消勾選「內部 Agent」
   ↓
5. ⭐ Secret 驗證（必須通過）
   - 輸入 Secret ID
   - 輸入 Secret Key
   - 點擊「驗證 Secret」
   - 等待驗證結果
   ↓
6. 驗證成功後，繼續配置
   - 協議類型
   - 端點 URL
   ↓
7. 配置權限（可選）
   ↓
8. 提交註冊
   - 前端檢查：secretVerified 必須為 true
   - 後端檢查：permissions.secret_id 必須存在
   ↓
9. 註冊成功，Secret ID 綁定到 Agent ID
```

### 如果沒有 Secret ID/Key？

**無法註冊外部 Agent**。必須：

1. **獲取 Secret ID/Key**
   - 開發/測試：`POST /api/v1/agents/secrets/generate`
   - 生產環境：向 AI-Box 管理員申請（Phase 2）

2. **驗證 Secret**
   - 在註冊頁面驗證

3. **然後才能註冊**

---

## 驗證層級

### 第一層：前端 UI 驗證

- **位置**：註冊表單提交前
- **檢查項**：`secretVerified` 狀態
- **結果**：未驗證 → 阻止提交，顯示錯誤提示

### 第二層：前端 API 驗證

- **位置**：`verifySecret()` 函數
- **檢查項**：Secret ID/Key 是否正確
- **結果**：驗證失敗 → 顯示錯誤，不允許繼續

### 第三層：後端註冊驗證

- **位置**：`register_agent()` API
- **檢查項**：
  1. 是否有 `permissions.secret_id`
  2. Secret ID 是否存在
  3. Secret ID 是否已綁定
- **結果**：任何檢查失敗 → 返回 HTTP 400 錯誤

---

## 設計原則

### 為什麼必須提供 Secret ID？

1. ✅ **安全第一**：確保只有授權的組織才能註冊
2. ✅ **身份驗證**：通過 AI-Box 簽發的憑證驗證身份
3. ✅ **可追溯性**：每個 Agent 都與申請記錄關聯
4. ✅ **集中管理**：AI-Box 完全控制憑證的生成和分發

### 雙重驗證機制

- **前端驗證**：提前攔截，提供友好的錯誤提示
- **後端驗證**：最後防線，確保安全性

---

## 錯誤情況處理

### 情況 1：沒有 Secret ID/Key

**前端**：
- 用戶無法驗證 Secret
- 無法通過表單驗證
- 無法提交註冊

**後端**：
- 如果直接調用 API（繞過前端），會返回：
  ```
  HTTP 400: "External agent must provide Secret ID for authentication..."
  ```

**解決方法**：
- 獲取 Secret ID/Key（申請或生成）
- 先驗證 Secret
- 再進行註冊

### 情況 2：Secret ID/Key 錯誤

**前端**：
- 驗證時顯示錯誤提示
- `secretVerified` 保持為 `false`
- 無法提交註冊

**後端**：
- 驗證端點返回驗證失敗
- 註冊端點會檢查 Secret ID 是否存在

---

## 總結

### 關鍵點

1. ✅ **外部 Agent 必須提供 Secret ID/Key**（強制要求）
2. ✅ **沒有 Secret ID/Key → 無法註冊**
3. ✅ **驗證通過 → 才能進行註冊程序**
4. ✅ **前後端雙重驗證**（確保安全）

### 當前實現狀態

- ✅ 前端已強制要求 Secret 驗證
- ✅ 後端已強制要求 Secret ID
- ✅ 驗證流程完整
- ✅ 錯誤處理完善

**結論**：外部 Agent 註冊必須提供並驗證 Secret ID/Key，這是硬性要求，沒有例外。

---

**最後更新**：2025-01-27
