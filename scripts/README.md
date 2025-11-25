# 階段一：基礎建設階段 - 腳本說明

**創建日期**: 2025-01-27  
**創建人**: Daniel Chung  
**最後修改日期**: 2025-01-27

---

## 腳本列表

### 環境設置腳本

#### `setup_dev_env.sh`

自動化設置開發環境的腳本，包括：
- Python 3.11+ 安裝
- Node.js 18+ 安裝
- Docker Desktop 安裝指引
- VS Code 安裝
- 開發工具安裝（Git, curl, jq, kubectl 等）
- 項目虛擬環境設置

**使用方法**:
```bash
./scripts/setup_dev_env.sh
```

**注意事項**:
- 需要管理員權限（部分操作需要 sudo）
- Docker Desktop 需要手動下載安裝
- VS Code 插件需要手動安裝

---

### 驗證腳本

#### `verify_env.sh`

驗證開發環境是否正確設置，檢查：
- Python 環境
- Node.js 環境
- Docker 環境
- Git 環境
- 其他開發工具

**使用方法**:
```bash
./scripts/verify_env.sh
```

**輸出**:
- 顯示每個工具的版本號
- 標記通過/失敗的檢查項
- 提供測試結果總結

---

### 測試腳本

**注意**: 測試腳本已根據階段一完成確認清除。實際測試將通過以下方式進行：

1. **手動驗證**: 使用 `verify_env.sh` 驗證開發環境
2. **CI/CD 自動測試**: GitHub Actions 工作流自動執行測試
3. **部署後驗證**: 部署後手動驗證各組件功能

---

## 使用流程

### 1. 初始設置

```bash
# 1. 設置開發環境
./scripts/setup_dev_env.sh

# 2. 驗證環境設置
./scripts/verify_env.sh
```

### 2. 工作項驗證

根據工作項進度，執行相應的驗證：

```bash
# 工作項 1.1.1: 開發環境搭建
./scripts/verify_env.sh

# 工作項 1.1.2: 版本控制設置
git status
git branch -a

# 工作項 1.1.3: CI/CD 基礎配置
# 推送代碼後，GitHub Actions 會自動執行

# 工作項 1.2.1: Docker 環境配置
docker-compose config
docker-compose up -d

# 工作項 1.2.2: Kubernetes 環境準備
kubectl apply -f k8s/base/namespaces.yaml
kubectl get namespaces

# 工作項 1.2.3: 監控基礎設施
kubectl apply -f k8s/monitoring/
kubectl get pods -n ai-box-monitoring
```

### 3. 定期驗證

建議在每次重要變更後執行驗證腳本：

```bash
./scripts/verify_env.sh
```

---

## 測試結果解讀

### 通過標準

- ✅ 綠色標記：測試通過
- ❌ 紅色標記：測試失敗
- ⚠ 黃色標記：警告（可選項未配置）

### 測試報告

每個測試腳本都會輸出：
- 測試結果總結（通過/失敗數量）
- 詳細的測試步驟結果
- 下一步行動建議

---

## 故障排除

### 常見問題

1. **權限問題**
   - 某些操作需要 sudo 權限
   - Docker 可能需要用戶加入 docker 組

2. **環境變數未設置**
   - 檢查 PATH 環境變數
   - 重新載入 shell 配置：`source ~/.zshrc`

3. **服務未運行**
   - Docker: 確保 Docker Desktop 正在運行
   - Kubernetes: 確保集群可用

4. **網路問題**
   - 檢查網路連接
   - 檢查防火牆設置

---

## 相關文檔

- [階段一詳細實施計劃](../docs/progress/phase1/)
- [進度報告模板](../docs/progress/phase1/templates/)
- [開發規範](../.cursor/rules/develop-rule.mdc)

---

## 維護

如有問題或建議，請聯繫：
- **創建人**: Daniel Chung
- **最後更新**: 2025-01-27

