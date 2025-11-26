# Git 分支策略

**創建日期**: 2025-10-25
**創建人**: Daniel Chung
**最後修改日期**: 2025-10-25

---

## 分支結構

```
main (生產分支)
  ├── develop (開發分支)
  │     ├── feature/xxx (功能分支)
  │     ├── feature/yyy
  │     └── hotfix/zzz (緊急修復分支)
  └── release/v1.0.0 (發布分支)
```

## 分支說明

### main 分支
- **用途**: 生產環境代碼
- **保護規則**:
  - 僅通過 PR 合併
  - 必須經過代碼審查
  - 必須通過 CI/CD 檢查

### develop 分支
- **用途**: 日常開發分支
- **規則**: 功能完成後合併到此分支

### feature/* 分支
- **用途**: 功能開發分支
- **命名**: `feature/功能名稱`
- **規則**:
  - 從 develop 創建
  - 完成後合併回 develop

### hotfix/* 分支
- **用途**: 緊急修復分支
- **命名**: `hotfix/修復名稱`
- **規則**:
  - 從 main 創建
  - 完成後合併到 main 和 develop

### release/* 分支
- **用途**: 發布準備分支
- **命名**: `release/v版本號`
- **規則**:
  - 從 develop 創建
  - 用於發布前的測試和準備

## 工作流程

1. **創建功能分支**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/new-feature
   ```

2. **開發和提交**
   ```bash
   git add .
   git commit -m "feat: 添加新功能"
   git push origin feature/new-feature
   ```

3. **創建 Pull Request**
   - 在 GitHub 上創建 PR
   - 從 feature 分支合併到 develop
   - 等待代碼審查和 CI 通過

4. **合併**
   - 審查通過後合併
   - 刪除 feature 分支

## 提交信息規範

- `feat`: 新功能
- `fix`: 修復 bug
- `docs`: 文檔更新
- `style`: 代碼格式調整
- `refactor`: 代碼重構
- `test`: 測試相關
- `chore`: 構建/工具相關

---

**最後更新**: 2025-10-25
