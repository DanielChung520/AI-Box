# 貢獻指南

**創建日期**: 2025-10-25
**創建人**: Daniel Chung
**最後修改日期**: 2025-10-25

---

## 如何貢獻

感謝您對 AI-Box 項目的關注！我們歡迎各種形式的貢獻。

## 開發流程

### 1. Fork 和克隆

1. Fork 本倉庫
2. 克隆您的 Fork：
   ```bash
   git clone https://github.com/[your-username]/AI-Box.git
   cd AI-Box
   ```

### 2. 創建分支

```bash
git checkout -b feature/your-feature-name
```

### 3. 開發

- 遵循代碼規範（見 `.cursor/rules/develop-rule.mdc`）
- 編寫測試
- 更新文檔

### 4. 提交

```bash
git add .
git commit -m "feat: 添加新功能"
```

**提交信息規範**:
- `feat`: 新功能
- `fix`: 修復 bug
- `docs`: 文檔更新
- `style`: 代碼格式調整
- `refactor`: 代碼重構
- `test`: 測試相關
- `chore`: 構建/工具相關

### 5. 推送和創建 PR

```bash
git push origin feature/your-feature-name
```

然後在 GitHub 上創建 Pull Request。

## 代碼規範

- 使用 Python 3.11+
- 遵循 PEP 8 規範
- 使用類型提示
- 編寫文檔字符串

## 測試

在提交 PR 前，請確保：
- 所有測試通過
- 代碼通過 lint 檢查
- 文檔已更新

## 問題報告

如發現問題，請在 GitHub Issues 中報告。

---

**最後更新**: 2025-10-25
