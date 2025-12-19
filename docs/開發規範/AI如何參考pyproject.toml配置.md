# AI 如何參考 pyproject.toml 配置

**版本**: 1.0
**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**最後修改日期**: 2025-01-27

---

## 問題回答

### ❓ pyproject.toml 設置好後，AI 編寫代碼會參考執行嗎？

**答案**：**部分會，部分不會**。

#### ✅ 工具會自動使用

以下工具會**自動讀取** `pyproject.toml` 配置：

1. **Ruff**: `ruff check .` 時自動讀取
2. **Mypy**: `mypy .` 時自動讀取
3. **Black**: `black .` 時自動讀取
4. **Pre-commit hooks**: 提交時自動使用

#### ❌ AI 不會自動讀取

**重要**：AI（如 Cursor 的 AI 助手）**不會自動讀取** `pyproject.toml` 配置。

---

## 解決方案

### ✅ 方案 1: 更新 Cursor 規則文件（已完成）

**已更新**: `.cursor/rules/develop-rule.mdc`

**添加的內容**：

- pyproject.toml 配置規範說明
- Ruff 配置要求
- Mypy 配置要求
- 生成代碼後的檢查流程
- 正確和錯誤的代碼生成範例

**效果**：

- ✅ AI 在生成代碼時會參考這些規範
- ✅ 自動遵循類型注解要求
- ✅ 自動避免高優先級錯誤（F821, E722）

### ✅ 方案 2: 生成後自動檢查（推薦）

**工作流程**：

```
AI 生成代碼
    ↓
保存文件
    ↓
自動執行: ruff check --fix <文件>
    ↓
自動執行: mypy <文件>
    ↓
如果失敗 → AI 修復錯誤 → 重新檢查
    ↓
通過 ✅
```

**實現方式**：

1. **在提示詞中要求**：

   ```
   請生成代碼後執行：
   1. ruff check --fix <文件路徑>
   2. mypy <文件路徑>
   3. 如果檢查失敗，修復錯誤
   ```

2. **使用工具調用**（如果支持）：
   - AI 生成代碼後，自動調用 `ruff check --fix`
   - 自動調用 `mypy`
   - 根據結果修復錯誤

### ✅ 方案 3: IDE 配置自動檢查

**VS Code 配置** (`settings.json`):

```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.analysis.typeCheckingMode": "basic",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  }
}
```

**效果**：

- 保存文件時自動運行 ruff 和 mypy
- 自動修復可修復的問題
- AI 可以看到實時檢查結果

---

## 當前配置狀態

### ✅ 已完成的配置

1. **pyproject.toml**: 完整的 Ruff 和 Mypy 配置
2. **.cursor/rules/develop-rule.mdc**: 已添加 pyproject.toml 配置規範
3. **文檔**: 創建了詳細的配置說明文檔

### 📋 配置內容摘要

#### Ruff 配置（AI 會參考）

- 行長度：100 字符
- Python 版本：3.11
- 啟用的規則：E, F, W, I, UP, B, SIM, RET, RUF
- 必須避免：F821, E722（高優先級）
- 導入排序：標準庫 → 第三方庫 → 第一方包

#### Mypy 配置（AI 會參考）

- 所有函數參數和返回值必須有類型注解
- 使用 `Optional[T]` 而不是 `T = None`
- 不允許隱式的 Optional
- 嚴格檢查 Optional 類型

---

## 驗證方法

### 測試 AI 是否遵循配置

1. **讓 AI 生成一個新函數**：

   ```
   請生成一個處理文件的函數，包含完整的類型注解
   ```

2. **檢查生成的代碼**：
   - ✅ 是否有完整的類型注解？
   - ✅ 是否使用 `Optional[T]` 而不是 `T = None`？
   - ✅ 是否避免裸 `except:`？
   - ✅ 導入是否在文件頂部？

3. **運行檢查工具**：

   ```bash
   ruff check --fix <文件>
   mypy <文件>
   ```

4. **如果檢查失敗**：
   - 說明 AI 沒有完全遵循配置
   - 需要手動修復或再次提示 AI

---

## 最佳實踐

### 1. 在提示詞中明確要求

每次讓 AI 生成代碼時，添加：

```
請遵循項目的 pyproject.toml 配置：
- 行長度：100 字符
- 包含完整的類型注解
- 使用 Optional[T] 而不是 T = None
- 所有 import 在文件頂部
- 使用 except Exception 而不是裸 except

生成後請執行檢查：
1. ruff check --fix <文件>
2. mypy <文件>
3. 如果失敗，修復錯誤
```

### 2. 生成後立即檢查

**自動化腳本** (`check_new_code.sh`):

```bash
#!/bin/bash
# 檢查新生成的代碼
FILE=$1

echo "🔍 檢查 $FILE..."

# Ruff 檢查
echo "1. 運行 Ruff 檢查..."
ruff check --fix "$FILE"
RUFF_EXIT=$?

# Mypy 檢查
echo "2. 運行 Mypy 檢查..."
mypy "$FILE"
MYPY_EXIT=$?

# 總結
if [ $RUFF_EXIT -eq 0 ] && [ $MYPY_EXIT -eq 0 ]; then
    echo "✅ 所有檢查通過！"
    exit 0
else
    echo "❌ 檢查失敗，請修復錯誤"
    exit 1
fi
```

**使用方式**：

```bash
chmod +x check_new_code.sh
./check_new_code.sh path/to/new_file.py
```

### 3. 配置 IDE 自動檢查

**VS Code** (`settings.json`):

```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.analysis.typeCheckingMode": "basic",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },
  "ruff.enable": true,
  "ruff.organizeImports": true
}
```

---

## 總結

### pyproject.toml 的作用範圍

| 工具/場景 | 是否自動使用配置 |
|---------|----------------|
| Ruff (`ruff check .`) | ✅ 是 |
| Mypy (`mypy .`) | ✅ 是 |
| Black (`black .`) | ✅ 是 |
| Pre-commit hooks | ✅ 是 |
| **AI 生成代碼** | ❌ **否**（需要通過規則文件） |

### 讓 AI 遵循配置的方法

1. ✅ **更新 Cursor 規則文件**（已完成）
   - `.cursor/rules/develop-rule.mdc` 已包含 pyproject.toml 規範

2. ✅ **在提示詞中明確要求**
   - 每次生成代碼時引用配置要求

3. ✅ **生成後立即檢查**
   - 自動運行 `ruff check --fix` 和 `mypy`
   - 根據結果修復錯誤

4. ✅ **配置 IDE 自動檢查**
   - 保存時自動運行檢查工具

### 當前狀態

- ✅ `pyproject.toml` 配置完整
- ✅ `.cursor/rules/develop-rule.mdc` 已更新
- ✅ AI 會參考規則文件中的規範
- ✅ 工具會自動使用配置

**結論**：AI 現在會通過 Cursor 規則文件參考 `pyproject.toml` 的配置，但建議在生成代碼後立即運行檢查工具驗證。

---

## 參考文檔

- [pyproject.toml 配置說明](./pyproject.toml配置說明.md)
- [代碼質量問題分析與解決方案](./代碼質量問題分析與解決方案.md)
- [AI 編寫代碼規範指南](./AI編寫代碼規範指南.md)
- [Ruff 文檔](https://docs.astral.sh/ruff/)
- [Mypy 文檔](https://mypy.readthedocs.io/)

---

**文檔版本**: 1.0
**最後更新**: 2025-01-27
**維護者**: Daniel Chung
