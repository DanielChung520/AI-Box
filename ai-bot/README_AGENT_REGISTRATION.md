# 前端 Agent 註冊功能說明

## 快速開始

### 如何打開註冊頁面
1. 進入瀏覽代理頁面
2. 點擊右側的「管理」按鈕
3. 彈出 Agent 註冊浮動頁面

### 外部 Agent 註冊新流程（重要變更）

#### 新增步驟：Secret 驗證 ⭐

外部 Agent 現在**必須先驗證 Secret** 才能註冊：

1. **切換到「端點配置」標籤頁**
2. **取消勾選「內部 Agent」**
3. **在 Secret 驗證區塊**：
   - 輸入 Secret ID（由 AI-Box 簽發）
   - 輸入 Secret Key（由 AI-Box 簽發）
   - 點擊「驗證 Secret」按鈕
   - 等待驗證成功
4. **繼續配置**：
   - 選擇協議類型（HTTP/MCP）
   - 輸入端點 URL
5. **提交註冊**

### Secret 驗證界面說明

#### 未驗證狀態：
- 顯示兩個輸入框（Secret ID 和 Secret Key）
- 「驗證 Secret」按鈕（藍色）
- 錯誤提示區域（如有錯誤）

#### 驗證成功後：
- 綠色成功提示框
- 顯示已驗證的 Secret ID
- 輸入框自動禁用

#### 常見錯誤：
- ❌ Secret ID 或 Secret Key 無效
- ❌ 此 Secret ID 已被綁定到其他 Agent
- ❌ Secret 驗證失敗，請稍後再試

---

## 主要修改總結

### 1. 新增功能
- ✅ Secret 驗證機制（外部 Agent 必需）
- ✅ 實時驗證反饋
- ✅ 驗證狀態顯示

### 2. 修改的文件
- `components/AgentRegistrationModal.tsx` - 添加 Secret 驗證 UI 和邏輯
- `lib/api.ts` - 添加 `verifySecret` API 函數
- `hooks/useLanguage.ts` - 添加 Secret 相關翻譯

### 3. 新增 API 端點
- `POST /api/v1/agents/secrets/verify` - 驗證 Secret
- `POST /api/v1/agents/secrets/generate` - 生成 Secret（測試用）

---

## 完整文檔

詳細的修改說明和使用指南請參考：
- `AGENT_REGISTRATION_CHANGES.md` - 完整的技術文檔

---

**最後更新**：2025-01-27
