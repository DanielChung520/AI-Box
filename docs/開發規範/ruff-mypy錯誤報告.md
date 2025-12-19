# Ruff 和 Mypy 錯誤報告

**版本**: 1.0
**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**最後修改日期**: 2025-01-27

---

## 執行結果摘要

### Ruff 檢查結果

**總錯誤數**: 50 個錯誤（無法自動修復）

**錯誤分類統計**：

- **F841 (未使用的變量)**: 28 個
- **E402 (導入不在文件頂部)**: 15 個
- **F821 (未定義的名稱)**: 5 個
- **E722 (裸 except)**: 2 個

### Mypy 檢查結果

**錯誤**: 1 個配置問題

```
rag-file-upload is not a valid Python package name
```

---

## 詳細錯誤列表

### 1. F841: 未使用的變量 (28 個)

#### 問題描述

變量被賦值但從未使用，這會導致代碼冗餘和潛在的邏輯錯誤。

#### 錯誤位置

**agents/builtin/orchestrator_manager/agent.py:546**

```python
agents = self._registry.list_agents()  # 未使用
return AgentServiceStatus.AVAILABLE
```

**agents/builtin/registry_manager/agent.py:495**

```python
agents = self._registry.list_agents()  # 未使用
return AgentServiceStatus.AVAILABLE
```

**agents/builtin/security_manager/agent.py:517**

```python
agents = self._registry.list_agents()  # 未使用
return AgentServiceStatus.AVAILABLE
```

**agents/services/registry/discovery.py:128**

```python
user_roles_set = set(user_roles or [])  # 未使用
```

**api/routers/auth.py:70**

```python
settings = get_security_settings()  # 未使用
```

**kag/kag_schema_manager_v2.py:121**

```python
template = self.load_prompt_template()  # 未使用
```

**scripts/restore_tasks_db.py:72-74**

```python
task_id = task.get("task_id")  # 未使用
doc_key = task.get("_key")  # 未使用
```

**scripts/update_phase5_and_it15_test_scenarios.py:176**

```python
it15_total = it15_data.get("total", 0)  # 未使用
```

**scripts/update_phase5_test_scenarios.py:38-39, 86, 95, 151-155, 158**

```python
pass_rate = results.get("pass_rate", 0)  # 未使用
skipped_rate = ...  # 未使用
phase1_pattern = ...  # 未使用
total_tests = ...  # 未使用
total_passed = ...  # 未使用
total_skipped = ...  # 未使用
total_failed = ...  # 未使用
total_pass_rate = ...  # 未使用
pattern = ...  # 未使用
```

#### 修復建議

**方法 1: 如果變量不需要，直接調用函數**

```python
# ❌ 錯誤
agents = self._registry.list_agents()
return AgentServiceStatus.AVAILABLE

# ✅ 正確
self._registry.list_agents()  # 只調用，不賦值
return AgentServiceStatus.AVAILABLE
```

**方法 2: 如果變量需要但未使用，使用下劃線前綴**

```python
# ❌ 錯誤
agents = self._registry.list_agents()

# ✅ 正確（如果確實需要調用但不需要返回值）
_ = self._registry.list_agents()
```

**方法 3: 如果變量應該被使用，添加使用邏輯**

```python
# ❌ 錯誤
template = self.load_prompt_template()

# ✅ 正確
template = self.load_prompt_template()
prompt = template.format(...)  # 使用 template
```

---

### 2. E402: 導入不在文件頂部 (15 個)

#### 問題描述

模塊級導入應該在文件頂部，在 `sys.path` 修改之後的導入會被標記為錯誤。

#### 錯誤位置

**mcp/server/main.py:30**

```python
sys.path.insert(0, str(project_root))
from system.logging_config import setup_mcp_server_logging  # E402
```

**scripts/clear_user_data.py:32**

```python
import shutil  # E402 (在 sys.exit 之後)
```

**scripts/fix_dev_user_tasks.py:25-26**

```python
sys.path.insert(0, str(project_root))
from arango import ArangoClient  # E402
from dotenv import load_dotenv  # E402
```

**scripts/migration/create_schema.py:18, 20**

```python
sys.path.insert(0, str(project_root))
import structlog  # E402
from database.arangodb import ArangoDBClient  # E402
```

**scripts/migration/migrate_configs.py:15, 17-19**

```python
sys.path.insert(0, str(project_root))
import structlog  # E402
from database.arangodb import ArangoDBClient  # E402
from services.api.models.config import ConfigCreate  # E402
from services.api.services.config_store_service import get_config_store_service  # E402
```

**scripts/migration/migrate_ontologies.py:15, 17-19**

```python
sys.path.insert(0, str(project_root))
import structlog  # E402
from database.arangodb import ArangoDBClient  # E402
from services.api.models.ontology import OntologyCreate  # E402
from services.api.services.ontology_store_service import get_ontology_store_service  # E402
```

#### 修復建議

**方法 1: 使用類型忽略註釋（如果必須動態導入）**

```python
sys.path.insert(0, str(project_root))
from system.logging_config import setup_mcp_server_logging  # type: ignore[E402]
```

**方法 2: 重構代碼結構（推薦）**

```python
# 將 sys.path 修改放在最前面，然後所有導入
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 現在可以正常導入
from system.logging_config import setup_mcp_server_logging
```

**方法 3: 使用 ruff 配置忽略特定文件**
在 `pyproject.toml` 或 `.ruff.toml` 中：

```toml
[tool.ruff.lint]
ignore = ["E402"]  # 全局忽略

# 或針對特定文件
[tool.ruff.lint.per-file-ignores]
"scripts/**/*.py" = ["E402"]
"mcp/**/*.py" = ["E402"]
```

---

### 3. F821: 未定義的名稱 (5 個)

#### 問題描述

使用了未定義的變量或函數，這會導致運行時錯誤。

#### 錯誤位置

**llm/moe/moe_manager.py:470, 471, 493, 494**

```python
# 函數參數中沒有 context 參數
def some_function(provider, ...):
    api_key = None
    if isinstance(context, dict):  # F821: context 未定義
        keys = context.get("llm_api_keys")  # F821
        ...
    ...
    if isinstance(context, dict):  # F821
        keys = context.get("llm_api_keys")  # F821
```

#### 修復建議

**方法 1: 添加缺失的參數**

```python
# ❌ 錯誤
def some_function(provider, ...):
    if isinstance(context, dict):  # context 未定義
        ...

# ✅ 正確
def some_function(provider, context: Optional[Dict[str, Any]] = None, ...):
    if isinstance(context, dict):
        ...
```

**方法 2: 從其他地方獲取 context**

```python
# 如果 context 應該從某個地方獲取
def some_function(provider, ...):
    context = get_context()  # 從某處獲取
    if isinstance(context, dict):
        ...
```

---

### 4. E722: 裸 except (2 個)

#### 問題描述

使用 `except:` 會捕獲所有異常，包括 `SystemExit` 和 `KeyboardInterrupt`，這不是好的實踐。

#### 錯誤位置

**api/routers/user_tasks.py:386, 398**

```python
try:
    task_created_at = datetime.fromisoformat(
        task.created_at.replace("Z", "+00:00")
    )
except:  # E722: 裸 except
    task_created_at = None

try:
    task_updated_at = datetime.fromisoformat(
        task.updated_at.replace("Z", "+00:00")
    )
except:  # E722: 裸 except
    task_updated_at = None
```

#### 修復建議

**使用具體的異常類型**

```python
# ❌ 錯誤
try:
    task_created_at = datetime.fromisoformat(
        task.created_at.replace("Z", "+00:00")
    )
except:  # 會捕獲所有異常
    task_created_at = None

# ✅ 正確
try:
    task_created_at = datetime.fromisoformat(
        task.created_at.replace("Z", "+00:00")
    )
except (ValueError, TypeError) as e:  # 只捕獲預期的異常
    logger.warning(f"無法解析日期: {e}")
    task_created_at = None
```

---

### 5. Mypy 配置問題

#### 問題描述

```
rag-file-upload is not a valid Python package name
```

#### 可能原因

1. 目錄名稱包含連字符（`-`），Python 包名不能包含連字符
2. mypy 配置中引用了無效的包名

#### 修復建議

**方法 1: 重命名目錄（推薦）**

```bash
# 將 rag-file-upload 重命名為 rag_file_upload
mv rag-file-upload rag_file_upload
```

**方法 2: 在 mypy 配置中排除該目錄**
在 `pyproject.toml` 或 `mypy.ini` 中：

```toml
[tool.mypy]
exclude = [
    "rag-file-upload/.*",
]
```

**方法 3: 檢查 mypy 配置文件**

```bash
# 查找 mypy 配置文件
find . -name "mypy.ini" -o -name ".mypy.ini" -o -name "pyproject.toml"
```

---

## 修復優先級

### 高優先級（必須修復）

1. **F821: 未定義的名稱** (5 個)
   - 會導致運行時錯誤
   - 必須立即修復

2. **E722: 裸 except** (2 個)
   - 可能隱藏重要異常
   - 應該修復

### 中優先級（建議修復）

3. **F841: 未使用的變量** (28 個)
   - 代碼冗餘，影響可讀性
   - 建議修復

4. **E402: 導入不在文件頂部** (15 個)
   - 代碼風格問題
   - 可以使用類型忽略或配置忽略

### 低優先級（可選修復）

5. **Mypy 配置問題**
   - 配置問題，不影響代碼運行
   - 可以通過配置解決

---

## 批量修復建議

### 1. 自動修復未使用的變量

對於簡單的未使用變量，可以使用 ruff 的 `--unsafe-fixes` 選項：

```bash
ruff check --fix --unsafe-fixes .
```

**注意**: 使用 `--unsafe-fixes` 前請先提交代碼，因為可能會修改代碼邏輯。

### 2. 配置 ruff 忽略特定錯誤

在 `pyproject.toml` 中：

```toml
[tool.ruff.lint]
# 全局忽略某些錯誤
ignore = ["E402"]  # 忽略導入不在頂部的錯誤

# 或針對特定目錄
[tool.ruff.lint.per-file-ignores]
"scripts/**/*.py" = ["E402", "F841"]  # scripts 目錄忽略這些錯誤
"mcp/**/*.py" = ["E402"]
```

### 3. 修復未定義的名稱

需要手動檢查每個 F821 錯誤，確定：

- 變量應該從哪裡來
- 是否需要添加參數
- 是否需要初始化變量

---

## 修復檢查清單

- [ ] 修復所有 F821 錯誤（未定義的名稱）
- [ ] 修復所有 E722 錯誤（裸 except）
- [ ] 修復或忽略 F841 錯誤（未使用的變量）
- [ ] 修復或配置忽略 E402 錯誤（導入不在頂部）
- [ ] 解決 mypy 配置問題
- [ ] 運行 `ruff check .` 確認無錯誤
- [ ] 運行 `mypy .` 確認無錯誤
- [ ] 提交修復後的代碼

---

## 參考資源

- [Ruff 文檔](https://docs.astral.sh/ruff/)
- [Mypy 文檔](https://mypy.readthedocs.io/)
- [項目開發規範](../.cursor/rules/develop-rule.mdc)
- [代碼質量問題分析與解決方案](./代碼質量問題分析與解決方案.md)

---

**文檔版本**: 1.0
**最後更新**: 2025-01-27
**維護者**: Daniel Chung
