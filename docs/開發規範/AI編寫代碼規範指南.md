# AI 編寫代碼規範指南

**版本**: 1.0
**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**最後修改日期**: 2025-01-27

---

## 概述

本文檔說明如何讓 AI 在編寫代碼時自動參考 `pyproject.toml` 中的配置，確保生成的代碼符合項目規範。

---

## pyproject.toml 的作用範圍

### ✅ 工具會自動使用

`pyproject.toml` 中的配置會被以下工具自動讀取和使用：

1. **Ruff**: 運行 `ruff check .` 時自動讀取配置
2. **Mypy**: 運行 `mypy .` 時自動讀取配置
3. **Black**: 運行 `black .` 時自動讀取配置
4. **Pre-commit hooks**: 提交時自動使用配置

### ❌ AI 不會自動讀取

**重要**：AI（如 Cursor 的 AI 助手）**不會自動讀取** `pyproject.toml` 配置。需要通過以下方式讓 AI 遵循這些規範：

1. **更新 Cursor 規則文件**（`.cursor/rules/develop-rule.mdc`）
2. **在提示詞中明確要求**
3. **生成後立即執行檢查工具**

---

## 解決方案

### 方案 1: 更新 Cursor 規則文件（推薦）

在 `.cursor/rules/develop-rule.mdc` 中添加對 `pyproject.toml` 的引用和具體規範。

#### 添加的內容

```markdown
## pyproject.toml 配置規範（2025-01-27 UTC+8）

### Ruff 配置要求

生成代碼時必須遵循 `pyproject.toml` 中的 Ruff 配置：

1. **行長度**: 最大 100 字符（與 black 保持一致）
2. **Python 版本**: 目標 Python 3.11
3. **啟用的規則**:
   - E: pycodestyle errors（基本錯誤）
   - F: pyflakes（未定義變量、未使用導入等）
   - W: pycodestyle warnings（基本警告）
   - I: isort（導入排序）
   - UP: pyupgrade（Python 版本升級建議）
   - B: flake8-bugbear（常見 bug 模式）
   - SIM: flake8-simplify（簡化建議）
   - RET: flake8-return（返回值檢查）
   - RUF: ruff-specific rules（ruff 特定規則）

4. **必須避免的錯誤**:
   - ❌ F821: 未定義的名稱（會導致運行時錯誤）
   - ❌ E722: 裸 except（必須使用 `except Exception`）
   - ❌ F841: 未使用的變量（除非在 scripts 目錄中）
   - ❌ E402: 導入不在文件頂部（除非在 scripts/mcp 目錄中）

5. **導入排序**:
   - 標準庫 → 第三方庫 → 第一方包（api, agents, database, genai, llm, mcp, services, storage, system, workers, kag）

### Mypy 配置要求

生成代碼時必須遵循 `pyproject.toml` 中的 Mypy 配置：

1. **類型注解要求**:
   - ✅ 所有函數參數必須有類型注解
   - ✅ 所有返回值必須有類型注解
   - ✅ 可能為 None 的變量使用 `Optional[T]` 而不是 `T = None`
   - ✅ 不允許隱式的 Optional（必須明確使用 `Optional[T]`）

2. **類型檢查要求**:
   - ✅ 使用 `strict_optional = true`（嚴格檢查 Optional 類型）
   - ✅ 使用 `no_implicit_optional = true`（不允許隱式 Optional）

3. **必須避免的類型錯誤**:
   - ❌ 未定義的變量或函數
   - ❌ 類型不匹配
   - ❌ 隱式的 Optional（如 `def func(param: str = None)` 應為 `def func(param: Optional[str] = None)`）

### 生成代碼後的檢查流程

AI 生成代碼後，必須執行以下檢查：

1. **立即運行 Ruff 檢查**:
   ```bash
   ruff check --fix path/to/new_file.py
   ```

2. **立即運行 Mypy 檢查**:

   ```bash
   mypy path/to/new_file.py
   ```

3. **如果檢查失敗，修復錯誤後重新檢查**，直到通過為止。

```

### 方案 2: 在提示詞中明確要求

每次讓 AI 生成代碼時，在提示詞中添加：

```

請遵循項目的 pyproject.toml 配置：

- 行長度：100 字符
- Python 版本：3.11
- 必須包含完整的類型注解
- 使用 Optional[T] 而不是 T = None
- 所有 import 必須在文件頂部
- 使用 except Exception 而不是裸 except
- 不要創建未使用的變量

生成代碼後，請執行：

1. ruff check --fix <文件路徑>
2. mypy <文件路徑>
3. 如果檢查失敗，修復錯誤

```

### 方案 3: 自動化檢查（最佳實踐）

在生成代碼後，自動執行檢查工具：

```python
# AI 生成代碼後的檢查流程
1. 保存文件
2. 運行: ruff check --fix <文件>
3. 運行: mypy <文件>
4. 如果失敗，修復錯誤並重複步驟 2-3
5. 確認通過後，繼續下一步
```

---

## 實際應用範例

### 範例 1: 生成新函數

**AI 提示詞**：

```
請生成一個處理文件上傳的函數，遵循 pyproject.toml 配置：
- 包含完整的類型注解
- 使用 Optional[T] 而不是 T = None
- 行長度不超過 100 字符
- 所有 import 在文件頂部
```

**AI 應該生成的代碼**：

```python
from typing import Optional, Dict, Any
from fastapi import UploadFile

async def process_file_upload(
    file: UploadFile,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    處理文件上傳

    Args:
        file: 上傳的文件
        user_id: 用戶 ID（可選）
        metadata: 文件元數據（可選）

    Returns:
        處理結果字典
    """
    # 實現邏輯
    pass
```

**生成後檢查**：

```bash
ruff check --fix path/to/file.py
mypy path/to/file.py
```

### 範例 2: 修復現有代碼

**AI 提示詞**：

```
請修復這個函數，確保通過 ruff 和 mypy 檢查：
- 添加缺失的類型注解
- 修復未定義的變量
- 使用 Optional[T] 而不是 T = None
```

**AI 應該執行的步驟**：

1. 修復代碼
2. 運行 `ruff check --fix <文件>`
3. 運行 `mypy <文件>`
4. 如果失敗，繼續修復直到通過

---

## 配置檢查清單

在讓 AI 生成代碼前，確保：

- [ ] `.cursor/rules/develop-rule.mdc` 已更新，包含 pyproject.toml 規範
- [ ] 提示詞中明確要求遵循 pyproject.toml 配置
- [ ] 生成後立即執行 `ruff check --fix`
- [ ] 生成後立即執行 `mypy` 檢查
- [ ] 如果檢查失敗，修復錯誤後重新檢查

---

## 最佳實踐

### 1. 在 Cursor 規則中引用配置

在 `.cursor/rules/develop-rule.mdc` 中添加：

```markdown
## 代碼生成規範（2025-01-27 UTC+8）

生成 Python 代碼時，必須嚴格遵循 `pyproject.toml` 中的配置：

### Ruff 配置
- 行長度：100 字符
- 目標版本：Python 3.11
- 必須避免：F821（未定義名稱）、E722（裸 except）
- 導入排序：標準庫 → 第三方庫 → 第一方包

### Mypy 配置
- 所有函數參數和返回值必須有類型注解
- 使用 `Optional[T]` 而不是 `T = None`
- 不允許隱式的 Optional

### 生成後檢查
生成代碼後，必須執行：
1. `ruff check --fix <文件>`
2. `mypy <文件>`
3. 如果失敗，修復錯誤後重新檢查
```

### 2. 使用工具驗證

創建一個檢查腳本，AI 生成代碼後自動運行：

```bash
#!/bin/bash
# check_code.sh
FILE=$1
echo "檢查 $FILE..."
ruff check --fix "$FILE" && mypy "$FILE" && echo "✅ 檢查通過" || echo "❌ 檢查失敗"
```

### 3. 配置 IDE 自動檢查

在 VS Code 中配置保存時自動檢查：

```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.fixAll": true
    }
  }
}
```

---

## 總結

### pyproject.toml 的作用

- ✅ **工具會自動使用**：ruff、mypy、black 會自動讀取配置
- ❌ **AI 不會自動讀取**：需要通過規則文件或提示詞讓 AI 遵循

### 讓 AI 遵循配置的方法

1. **更新 Cursor 規則文件**（`.cursor/rules/develop-rule.mdc`）- 推薦
2. **在提示詞中明確要求**
3. **生成後立即執行檢查工具**

### 檢查流程

```
AI 生成代碼
    ↓
保存文件
    ↓
ruff check --fix <文件>  ← 自動修復可修復的問題
    ↓
mypy <文件>  ← 檢查類型
    ↓
如果失敗 → 修復錯誤 → 重新檢查
    ↓
通過 ✅
```

---

**文檔版本**: 1.0
**最後更新**: 2025-01-27
**維護者**: Daniel Chung
