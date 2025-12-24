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

## 最佳實踐

1. **提交前檢查**: 始終運行 pre-commit hooks
2. **類型注解**: 為所有函數和類添加類型注解
3. **文檔字符串**: 為所有公共 API 添加文檔字符串
4. **測試覆蓋率**: 確保測試覆蓋率 ≥ 80%
5. **安全掃描**: 定期運行安全掃描工具
6. **依賴更新**: 定期更新依賴項以修復安全漏洞

創建日期: 2025-12-18
創建人: Daniel Chung
最後修改日期: 2025-12-18
