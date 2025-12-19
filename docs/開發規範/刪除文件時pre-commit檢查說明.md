# 刪除文件時 Pre-commit 檢查說明

**版本**: 1.0
**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**最後修改日期**: 2025-01-27

---

## 問題說明

### 為什麼刪除文件也會觸發錯誤？

**原因**: Pre-commit hooks **不是只檢查被刪除的文件**，而是會檢查**所有相關文件**（取決於配置）。

---

## Pre-commit Hooks 的檢查範圍

### 1. 默認行為

**Pre-commit hooks 會檢查**:

- ✅ 被修改的文件（`git add` 後的文件）
- ✅ 被刪除的文件（`git rm` 後的文件）
- ⚠️ **所有文件**（如果使用 `--all-files` 參數）
- ⚠️ **特定類型的文件**（如所有 `.yaml` 文件，如果配置了）

### 2. 當前問題

**實際錯誤**: 不是因為刪除文件，而是因為 `prettier` 在檢查 YAML 文件時發現了語法錯誤。

**錯誤位置**: `k8s/base/service.yaml:41` - 重複的 `apiVersion` 鍵

**錯誤信息**:

```
[error] k8s/base/service.yaml: SyntaxError: Map keys must be unique; "apiVersion" is repeated (41:1)
```

---

## 解決方案

### 方案 1: 修復 YAML 文件錯誤（推薦）

修復 `k8s/base/service.yaml` 文件中的重複 `apiVersion` 問題。

### 方案 2: 配置 Prettier 排除 k8s 目錄

在 `.pre-commit-config.yaml` 中配置 prettier 排除 k8s 目錄：

```yaml
- repo: https://github.com/pre-commit/mirrors-prettier
  rev: v4.0.0-alpha.8
  hooks:
    - id: prettier
      types: [yaml]
      exclude: ^(.github/|.pre-commit-config.yaml|k8s/)
```

### 方案 3: 跳過 Prettier 檢查（臨時方案）

如果必須立即提交，可以跳過 prettier 檢查：

```bash
git commit --no-verify -m "your message"
```

**注意**: 不推薦，應該修復錯誤。

---

## Pre-commit Hooks 的工作機制

### 1. 提交時的行為

當執行 `git commit` 時：

1. **Pre-commit hooks 自動運行**
2. **檢查範圍**:
   - 默認：只檢查暫存區的文件（`git add` 後的文件）
   - 使用 `--all-files`：檢查所有文件
3. **如果檢查失敗**:
   - 提交被阻止
   - 需要修復錯誤後重新提交

### 2. 為什麼會檢查未修改的文件？

**原因**: 某些 hooks（如 `prettier`）配置為檢查**特定類型的文件**，而不是只檢查修改的文件。

**示例配置**:

```yaml
- id: prettier
  types: [yaml]  # 會檢查所有 YAML 文件
```

這意味著：

- 即使只刪除了一個 Markdown 文件
- Prettier 仍然會檢查**所有 YAML 文件**
- 如果任何 YAML 文件有錯誤，提交會被阻止

---

## 當前錯誤詳解

### 錯誤文件

`k8s/base/service.yaml` - Kubernetes Service 配置文件

### 錯誤原因

文件中有**重複的 `apiVersion` 鍵**，這違反了 YAML 語法規則。

### 修復方法

檢查文件，確保每個 YAML 文檔只有一個 `apiVersion` 鍵。

**常見情況**:

- 文件中可能有多個 YAML 文檔（用 `---` 分隔）
- 每個文檔應該有獨立的 `apiVersion`
- 但同一個文檔內不能有重複的鍵

---

## 建議的處理流程

### 1. 檢查錯誤

```bash
# 查看 prettier 的具體錯誤
pre-commit run prettier --all-files
```

### 2. 修復錯誤

```bash
# 修復 YAML 文件
vim k8s/base/service.yaml
# 或使用其他編輯器修復
```

### 3. 重新提交

```bash
# 添加修復後的文件
git add k8s/base/service.yaml

# 重新提交
git commit -m "fix: 修復 YAML 文件錯誤並刪除重複文檔"
```

---

## 配置建議

### 1. 限制 Prettier 檢查範圍

如果 k8s 配置文件不需要格式化，可以排除：

```yaml
- id: prettier
  types: [yaml]
  exclude: ^(.github/|.pre-commit-config.yaml|k8s/)
```

### 2. 只檢查修改的文件

某些 hooks 可以配置為只檢查修改的文件，但這取決於 hook 的實現。

### 3. 分離檢查和格式化

- **檢查**: 在 CI/CD 中運行（檢查所有文件）
- **格式化**: 在 pre-commit 中運行（只格式化修改的文件）

---

## 總結

### 為什麼刪除文件也會觸發錯誤？

1. **不是因為刪除文件本身**
2. **而是因為 pre-commit hooks 會檢查所有相關文件**
3. **當前錯誤是 `k8s/base/service.yaml` 的 YAML 語法錯誤**

### 解決方案

1. **修復 YAML 文件錯誤**（推薦）
2. **配置 prettier 排除 k8s 目錄**（如果不需要檢查）
3. **跳過檢查**（不推薦，僅緊急情況）

### 關鍵點

- Pre-commit hooks **不是只檢查被修改的文件**
- 某些 hooks 會檢查**所有特定類型的文件**
- 需要根據項目需求配置檢查範圍

---

**文檔版本**: 1.0
**最後更新**: 2025-01-27
**維護者**: Daniel Chung
