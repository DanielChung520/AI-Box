# DevSecOps 開發指南（WBS-2）

## 概述

本文檔說明 AI-Box 項目的 DevSecOps 實踐，包括代碼質量檢查、安全掃描、CI/CD 流程等。

## 代碼質量檢查

### Pre-commit Hooks

在提交代碼前，pre-commit hooks 會自動運行以下檢查：

```bash
# 安裝 pre-commit hooks
pip install pre-commit
pre-commit install

# 手動運行所有 hooks
pre-commit run --all-files
```

### 代碼格式化

- **Black**: 自動格式化 Python 代碼

  ```bash
  black .
  ```

- **isort**: 自動排序 import 語句

  ```bash
  isort .
  ```

### 代碼檢查

- **Ruff**: 快速代碼檢查和修復

  ```bash
  ruff check . --fix
  ```

- **Pylint**: 代碼品質檢查

  ```bash
  pylint services/api/
  ```

- **mypy**: 類型檢查

  ```bash
  mypy . --ignore-missing-imports
  ```

## 安全掃描

### Bandit（Python 安全掃描）

```bash
bandit -r . -ll
```

### Safety（依賴項漏洞檢查）

```bash
safety check
```

### Trivy（容器安全掃描）

在 CI/CD 流程中自動運行，也可手動執行：

```bash
trivy image ai-box:latest
```

## CI/CD 流程

### GitHub Actions

項目使用 GitHub Actions 進行 CI/CD，工作流包括：

1. **代碼質量檢查** (lint job)
   - Black 格式化檢查
   - isort import 排序檢查
   - Ruff 代碼檢查
   - Pylint 代碼品質檢查
   - mypy 類型檢查

2. **安全掃描** (security-scan job)
   - Bandit Python 安全掃描
   - Safety 依賴項漏洞檢查

3. **容器安全掃描** (container-scan job)
   - Trivy 容器漏洞掃描

4. **測試** (test job)
   - 單元測試
   - 整合測試
   - 端到端測試（v4.0 新增）
   - 性能測試（v4.0 新增）
   - 回歸測試（v4.0 新增）
   - 壓力測試（v4.0 新增）
   - 代碼覆蓋率檢查（≥ 80%）

5. **構建** (build job)
   - Docker 映像構建
   - 推送到容器註冊表

6. **部署** (deploy job)
   - 自動部署到 staging/production 環境

### 本地測試

在提交前，建議在本地運行所有檢查：

```bash
# 運行所有檢查
black --check . && \
isort --check-only . && \
ruff check . && \
mypy . --ignore-missing-imports && \
pytest --cov=. --cov-fail-under=80
```

## 依賴管理

### 更新依賴

開發依賴定義在 `requirements-dev.txt` 和 `services/api/pyproject.toml` 中。

```bash
# 安裝開發依賴
pip install -r requirements-dev.txt

# 或使用 pyproject.toml
pip install -e services/api/.[dev]
```

### 安全更新

定期檢查依賴項安全漏洞：

```bash
safety check
```

## 監控與日誌

詳見 [監控文檔](monitoring/README.md)

## v4.0 開發規範

### Task Analyzer v4.0 開發規範

**5層處理流程開發規範**：

1. **L1 語義理解層**：
   - 只輸出純語義理解（`SemanticUnderstandingOutput`）
   - 不產生 intent，不指定 agent
   - 不使用 RAG
   - 響應時間目標：≤5秒（P95）

2. **L2 意圖抽象層**：
   - 基於 Intent DSL 的固定意圖集合
   - 使用 Intent Registry 進行版本化管理
   - 支持 Fallback Intent 機制
   - 響應時間目標：≤100ms（P95）

3. **L3 能力映射層**：
   - 基於 Capability Registry 的能力發現
   - 使用 RAG 進行能力約束和系統感知
   - 生成 Task DAG 進行任務規劃
   - 響應時間目標：≤10秒（P95）

4. **L4 策略檢查層**：
   - 執行前的權限、風險、策略檢查
   - 使用 Policy Service 進行策略驗證
   - 響應時間目標：≤100ms（P95）

5. **L5 執行觀察層**：
   - 任務執行和結果觀察
   - 記錄執行指標和性能數據
   - 支持回放和重試
   - 響應時間目標：根據任務複雜度而定

### 測試規範

**v4.0 測試要求**：

1. **端到端測試**：測試 L1-L5 完整流程
2. **性能測試**：測試各層級性能指標
3. **回歸測試**：確保 v3 功能兼容性
4. **壓力測試**：測試高並發場景

**測試文件位置**：

- `tests/integration/e2e/test_task_analyzer_v4_e2e.py`
- `tests/performance/test_task_analyzer_v4_performance.py`
- `tests/regression/test_task_analyzer_v3_compatibility.py`
- `tests/performance/test_task_analyzer_v4_stress.py`

**測試運行**：

```bash
# 運行端到端測試
./tests/run_e2e_tests.sh

# 運行性能測試
./tests/run_performance_tests.sh

# 運行回歸測試
./tests/run_regression_tests.sh

# 運行壓力測試
./tests/run_stress_tests.sh
```

## 最佳實踐

1. **提交前檢查**: 始終運行 pre-commit hooks
2. **類型注解**: 為所有函數和類添加類型注解
3. **文檔字符串**: 為所有公共 API 添加文檔字符串
4. **測試覆蓋率**: 確保測試覆蓋率 ≥ 80%
5. **安全掃描**: 定期運行安全掃描工具
6. **依賴更新**: 定期更新依賴項以修復安全漏洞
7. **v4.0 架構遵循**: 開發新功能時遵循 v4.0 5層處理流程架構
8. **性能監控**: 監控各層級性能指標，確保符合性能目標

創建日期: 2025-12-18
創建人: Daniel Chung
最後修改日期: 2026-01-13
**版本**: v4.0
