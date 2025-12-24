# 推送代碼到 GitHub 指南

**創建日期**: 2025-10-25
**創建人**: Daniel Chung
**最後修改日期**: 2025-10-25

---

## 推送代碼需要認證

由於 GitHub 需要身份驗證，您需要選擇以下方式之一：

---

## 方法 1：使用 Personal Access Token (PAT) - 推薦

### 步驟 1：創建 Personal Access Token

1. 訪問：<https://github.com/settings/tokens>
2. 點擊 "Generate new token" → "Generate new token (classic)"
3. 設置：
   - Note: `AI-Box 開發`
   - Expiration: 選擇合適的過期時間（建議 90 天或 No expiration）
   - 勾選權限：`repo`（完整倉庫權限）
4. 點擊 "Generate token"
5. **重要**：複製生成的 token（只顯示一次）

### 步驟 2：推送代碼

```bash
# 推送 develop 分支
git push -u origin develop

# 當提示輸入用戶名時：輸入 DanielChung520
# 當提示輸入密碼時：輸入剛才複製的 Personal Access Token（不是 GitHub 密碼）
```

---

## 方法 2：使用 SSH（如果已配置 SSH 密鑰）

### 步驟 1：檢查 SSH 密鑰

```bash
# 檢查是否有 SSH 密鑰
ls -la ~/.ssh/id_*.pub

# 如果沒有，生成新的 SSH 密鑰
ssh-keygen -t ed25519 -C "daniel.chung@example.com"
```

### 步驟 2：添加 SSH 密鑰到 GitHub

1. 複製公鑰內容：

   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```

2. 訪問：<https://github.com/settings/keys>
3. 點擊 "New SSH key"
4. 貼上公鑰內容
5. 點擊 "Add SSH key"

### 步驟 3：更改遠程倉庫 URL 為 SSH

```bash
# 更改為 SSH URL
git remote set-url origin git@github.com:DanielChung520/AI-Box.git

# 驗證
git remote -v

# 推送
git push -u origin develop
```

---

## 方法 3：使用 GitHub CLI（如果已安裝）

```bash
# 登錄 GitHub CLI
gh auth login

# 選擇 GitHub.com
# 選擇 HTTPS
# 選擇瀏覽器登錄或 token

# 推送代碼
git push -u origin develop
```

---

## 完整推送流程

無論使用哪種方法，推送流程如下：

```bash
# 1. 確保在 develop 分支
git checkout develop

# 2. 推送 develop 分支
git push -u origin develop

# 3. 創建並推送 main 分支
git checkout -b main
git push -u origin main

# 4. 切換回 develop 分支繼續開發
git checkout develop
```

---

## 常見問題

### 問題 1：認證失敗

**錯誤**：`fatal: could not read Username for 'https://github.com'`

**解決方案**：

- 使用 Personal Access Token（方法 1）
- 或配置 SSH（方法 2）

### 問題 2：倉庫不存在

**錯誤**：`remote: Repository not found`

**解決方案**：

- 確保已在 GitHub 創建名為 `AI-Box` 的倉庫
- 訪問：<https://github.com/new>

### 問題 3：權限不足

**錯誤**：`remote: Permission denied`

**解決方案**：

- 檢查 Personal Access Token 是否有 `repo` 權限
- 或檢查 SSH 密鑰是否已添加到 GitHub

---

## 推薦流程

1. **先創建 GitHub 倉庫**：
   - 訪問：<https://github.com/new>
   - 倉庫名稱：`AI-Box`
   - 不要初始化任何文件

2. **使用 Personal Access Token 推送**（最簡單）：

   ```bash
   git push -u origin develop
   # 用戶名：DanielChung520
   # 密碼：Personal Access Token
   ```

3. **設置分支保護規則**（可選）

---

**最後更新**: 2025-10-25
