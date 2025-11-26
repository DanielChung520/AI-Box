# 代碼功能說明: ArangoDB 運維腳本說明
# 創建日期: 2025-11-25 22:25 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 22:25 (UTC+8)

本目錄提供 WBS 1.4.1 所需的輔助腳本，協助在 Docker 或 Kubernetes 環境中初始化與檢查 ArangoDB。

## 檔案列表

| 檔案 | 說明 |
|------|------|
| `bootstrap.sh` | 建立資料庫、集合、預設使用者並可設定 Active Failover 標籤 |
| `healthcheck.sh` | 針對 Docker 與 K8s 服務執行 HTTP 健康檢查與版本確認 |

## 使用方式

```bash
# 初始化資料庫
./infra/arangodb/bootstrap.sh

# 健康檢查
./infra/arangodb/healthcheck.sh
```

請依 `docs/deployment/arangodb-deployment.md` 指南將腳本納入 CI/CD 或日常維運流程。
