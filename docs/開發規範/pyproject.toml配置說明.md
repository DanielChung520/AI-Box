# pyproject.toml 配置說明

**版本**: 1.0
**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**最後修改日期**: 2025-01-27

---

## 概述

`pyproject.toml` 是 AI-Box 項目的統一配置文件，包含 Ruff、Mypy 和 Black 的配置。本文檔說明配置的詳細內容和使用方法。

---

## Ruff 配置

### 基本設置

```toml
[tool.ruff]
line-length = 100          # 行長度（與 black 保持一致）
target-version = "py311"   # 目標 Python 版本
```

### 啟用的規則類別

```toml
[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors (基本錯誤)
    "F",      # pyflakes (未定義變量、未使用導入等)
    "W",      # pycodestyle warnings (基本警告)
    "I",      # isort (導入排序)
    "UP",     # pyupgrade (Python 版本升級建議)
    "B",      # flake8-bugbear (常見 bug 模式)
    "SIM",    # flake8-simplify (簡化建議)
    "RET",    # flake8-return (返回值檢查)
    "RUF",    # ruff-specific rules (ruff 特定規則)
]
```

**說明**：

- 只啟用核心規則，避免過於嚴格
- 逐步啟用更多規則，而不是一次性啟用所有規則
- 暫時不啟用的規則：`PIE`（flake8-pie）、`PT`（flake8-pytest-style）

### 全局忽略規則

```toml
ignore = [
    "E501",   # line too long (handled by black)
]
```

### 每個文件的忽略規則

```toml
[tool.ruff.lint.per-file-ignores]
"scripts/**/*.py" = ["F841", "E402"]      # scripts 目錄忽略未使用變量和導入位置
"mcp/**/*.py" = ["E402"]                  # mcp 目錄忽略導入位置
"scripts/migration/**/*.py" = ["E402"]    # migration 腳本忽略導入位置
```

**說明**：

- `scripts/` 目錄中的文件可能包含調試代碼或未來使用的變量
- `mcp/` 和 `scripts/migration/` 中的腳本需要在 `sys.path` 修改之後才能導入

### isort 配置（導入排序）

```toml
[tool.ruff.lint.isort]
known-first-party = [
    "api",
    "agents",
    "database",
    "genai",
    "llm",
    "mcp",
    "services",
    "storage",
    "system",
    "workers",
    "kag",
]
```

**說明**：定義項目的第一方包，isort 會將這些包的導入放在第三方庫之後、標準庫之前。

---

## Mypy 配置

### 基本設置

```toml
[tool.mypy]
python_version = "3.11"
strict = false  # 不啟用嚴格模式，逐步改進類型注解
```

### 警告設置

```toml
warn_return_any = true              # 警告返回 Any 類型的函數
warn_unused_configs = true           # 警告未使用的配置選項
warn_redundant_casts = true          # 警告冗餘的類型轉換
warn_unused_ignores = true           # 警告未使用的 type: ignore 註釋
warn_no_return = true                # 警告沒有返回值的函數
warn_unreachable = true              # 警告不可達的代碼
```

### 類型檢查設置

```toml
disallow_untyped_defs = false        # 不要求所有函數都有類型注解（逐步改進）
disallow_incomplete_defs = false     # 不要求完整的類型注解（逐步改進）
check_untyped_defs = true            # 檢查未類型化的函數定義
disallow_untyped_decorators = false  # 不要求裝飾器有類型注解
no_implicit_optional = true          # 不允許隱式的 Optional
strict_optional = true               # 嚴格檢查 Optional 類型
strict_equality = false              # 不嚴格檢查相等性
```

**說明**：

- 不啟用 `strict = true`，因為項目中有大量未類型化的代碼
- 採用逐步改進的策略，而不是一次性啟用所有嚴格檢查
- `no_implicit_optional = true` 和 `strict_optional = true` 確保 Optional 類型的使用正確

### 模塊和導入設置

```toml
ignore_missing_imports = false       # 不忽略缺失的導入
follow_imports = "normal"            # 正常跟隨導入
explicit_package_bases = true        # 使用明確的包基礎路徑，避免模塊重複問題
```

### 排除規則

```toml
exclude = [
    "rag-file-upload/.*",            # 包含連字符的目錄（不是有效的 Python 包名）
    "tests/.*/rag-file-upload/.*",
    "docs/.*/rag-file-upload/.*",
    "backup/.*",                     # 備份目錄
    "venv/.*",                       # 虛擬環境（專案統一使用 venv）
    "build/.*",                      # 構建目錄
    "dist/.*",                       # 分發目錄
    "__pycache__/.*",                # Python 緩存
    ".*\\.pyc$",                     # 編譯的 Python 文件
]
```

### 每個模塊的配置

```toml
[tool.mypy-overrides]
"pydantic.*" = { ignore_missing_imports = false }
"fastapi.*" = { ignore_missing_imports = false }
"structlog.*" = { ignore_missing_imports = false }
"redis.*" = { ignore_missing_imports = false }
"rq.*" = { ignore_missing_imports = false }
"chromadb.*" = { ignore_missing_imports = false }
"arango.*" = { ignore_missing_imports = false }
```

**說明**：這些第三方庫通常有類型存根，不需要忽略缺失的導入。

---

## Black 配置

```toml
[tool.black]
line-length = 100                    # 行長度（與 ruff 保持一致）
target-version = ['py311']          # 目標 Python 版本
include = '\.pyi?$'                 # 包含 .py 和 .pyi 文件
```

**說明**：Black 的配置與 Ruff 保持一致，確保格式化結果一致。

---

## 使用建議

### 1. 開發時檢查

```bash
# 檢查所有文件
ruff check .

# 只檢查高優先級錯誤
ruff check --select F821,E722 .

# 自動修復可修復的問題
ruff check --fix .

# 類型檢查
mypy .
```

### 2. 提交前檢查

```bash
# 運行所有檢查
ruff check .
mypy .

# 或使用 pre-commit hooks（自動運行）
git commit -m "your message"
```

### 3. IDE 配置

**VS Code** (`settings.json`):

```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.analysis.typeCheckingMode": "basic",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

**PyCharm**:

- Settings → Tools → Ruff → Enable Ruff
- Settings → Tools → mypy → Enable mypy

### 4. 逐步改進策略

1. **第一階段**（當前）：
   - 修復所有 F821（未定義名稱）和 E722（裸 except）錯誤
   - 配置忽略 scripts 目錄中的非關鍵錯誤

2. **第二階段**（未來）：
   - 逐步修復 F841（未使用變量）錯誤
   - 改進類型注解，減少 mypy 錯誤

3. **第三階段**（長期）：
   - 啟用更多 ruff 規則（如 PIE、PT）
   - 考慮啟用 mypy 的嚴格模式

---

## 配置驗證

### 檢查配置是否正確

```bash
# 驗證 TOML 語法
python3 -c "import tomllib; f=open('pyproject.toml'); tomllib.loads(f.read()); print('TOML valid')"

# 驗證 ruff 配置
ruff check --config pyproject.toml .

# 驗證 mypy 配置
mypy --config-file pyproject.toml --show-config
```

### 當前狀態

- ✅ **高優先級錯誤**（F821, E722）：0 個
- ✅ **配置正確**：ruff 和 mypy 都能正確讀取配置
- ⚠️ **中優先級錯誤**：已配置忽略 scripts 目錄

---

## 常見問題

### Q1: 為什麼啟用了這麼多規則，但還有很多錯誤？

**A**: 這是正常的。配置啟用了核心規則來幫助發現問題，但不會一次性修復所有問題。優先修復高優先級錯誤（F821, E722），其他錯誤可以逐步修復。

### Q2: 如何只檢查特定類型的錯誤？

**A**: 使用 `--select` 選項：

```bash
ruff check --select F821,E722 .  # 只檢查未定義名稱和裸 except
```

### Q3: 如何忽略特定文件的錯誤？

**A**: 在文件頂部添加註釋：

```python
# ruff: noqa: F841  # 忽略未使用變量
# mypy: ignore-errors  # 忽略所有 mypy 錯誤
```

或在 `pyproject.toml` 中配置 `per-file-ignores`。

### Q4: 如何啟用更多規則？

**A**: 在 `[tool.ruff.lint]` 的 `select` 列表中添加規則類別，例如：

```toml
select = [
    "E", "F", "W", "I", "UP", "B", "SIM", "RET", "RUF",
    "PIE",  # 添加 flake8-pie
    "PT",   # 添加 flake8-pytest-style
]
```

---

## 參考資源

- [Ruff 文檔](https://docs.astral.sh/ruff/)
- [Mypy 文檔](https://mypy.readthedocs.io/)
- [Black 文檔](https://black.readthedocs.io/)
- [項目開發規範](./代碼質量問題分析與解決方案.md)
- [錯誤報告](./ruff-mypy錯誤報告.md)

---

**文檔版本**: 1.0
**最後更新**: 2025-01-27
**維護者**: Daniel Chung
