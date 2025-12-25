# GitHub 遠程倉庫設置指南

**創建日期**: 2025-10-25
**創建人**: Daniel Chung
**最後修改日期**: 2025-10-25

---

## 設置步驟

### 1. 在 GitHub 創建倉庫

1. 登錄 GitHub
2. 點擊右上角的 "+" → "New repository"
3. 倉庫名稱：`AI-Box`
4. 描述：`Agent AI Box 系統 - 基於 GenAI 的智能代理系統`
5. 選擇：Private（私有）或 Public（公開）
6. **不要**初始化 README、.gitignore 或 license（我們已經有了）
7. 點擊 "Create repository"

### 2. 設置本地 Git 遠程倉庫

#### 方法 1：使用 HTTPS（推薦）

```bash
# 替換 USERNAME 為您的 GitHub 用戶名
git remote add origin https://github.com/USERNAME/AI-Box.git

# 驗證遠程倉庫配置
git remote -v
```

#### 方法 2：使用 SSH

```bash
# 替換 USERNAME 為您的 GitHub 用戶名
git remote add origin git@github.com:USERNAME/AI-Box.git

# 驗證遠程倉庫配置
git remote -v
```

### 3. 推送代碼到 GitHub

```bash
# 確保在 develop 分支
git checkout develop

# 推送 develop 分支
git push -u origin develop

# 創建並推送 main 分支
git checkout -b main
git push -u origin main
```

### 4. 設置分支保護規則

1. 訪問 GitHub 倉庫頁面
2. 點擊 Settings → Branches
3. 點擊 "Add rule"
4. 分支名稱模式：`main`
5. 啟用以下選項：
   - ✅ Require a pull request before merging
   - ✅ Require approvals: 1
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
6. 點擊 "Create"

---

## 快速設置腳本

如果您已經知道 GitHub 用戶名，可以使用以下命令：

```bash
# 設置變數（替換為您的用戶名）
GITHUB_USERNAME="your-username"

# 添加遠程倉庫
git remote add origin https://github.com/${GITHUB_USERNAME}/AI-Box.git

# 驗證
git remote -v

# 推送代碼
git push -u origin develop
```

---

## 驗證設置

```bash
# 檢查遠程倉庫
git remote -v

# 應該顯示：
# origin  https://github.com/USERNAME/AI-Box.git (fetch)
# origin  https://github.com/USERNAME/AI-Box.git (push)
```

---

## 常見問題

### 問題 1：遠程倉庫已存在

如果出現 "remote origin already exists" 錯誤：

```bash
# 移除現有遠程倉庫
git remote remove origin

# 重新添加
git remote add origin https://github.com/USERNAME/AI-Box.git
```

### 問題 2：認證失敗

如果推送時需要認證：

**HTTPS 方式**：

- 使用 Personal Access Token（PAT）作為密碼
- 創建 PAT：Settings → Developer settings → Personal access tokens → Tokens (classic)

**SSH 方式**：

- 確保 SSH 密鑰已添加到 GitHub
- 測試連接：`ssh -T git@github.com`

### 問題 3：分支保護規則設置

如果無法直接推送到 main 分支：

- 這是正常的，因為我們設置了分支保護
- 應該通過 Pull Request 合併到 main 分支

---

## 下一步

設置完成後：

1. ✅ 推送代碼到 GitHub
2. ✅ 設置分支保護規則
3. ✅ 測試 CI/CD 工作流
4. ✅ 邀請團隊成員協作

---

**最後更新**: 2025-10-25
