# 代碼功能說明: ArangoDB 部署指南
# 創建日期: 2025-11-25 22:25 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 22:58 (UTC+8)

# ArangoDB 部署指南

## 1. 前置需求
- Docker Desktop / containerd 環境
- Kubernetes 1.28+（含 `kubectl` 權限）
- Prometheus + Grafana 監控命名空間 `ai-box-monitoring`
- 本地 SSD 掛載路徑 `datasets/arangodb`（對應 docker-compose volume）
- 取得管理密碼（預設 `ARANGO_ROOT_PASSWORD=ai_box_arangodb_password`，請於生產環境改用 Secret 管理）
- 已建立 `config/config.json` 並設定 `datastores.arangodb.*`、`kubernetes.storage_class` 等非敏感參數，結構如下：

```json
{
  "datastores": {
    "arangodb": {
      "host": "127.0.0.1",
      "port": 8529,
      "protocol": "http",
      "database": "ai_box_kg",
      "credentials": {
        "username": "ARANGODB_USERNAME",
        "password": "ARANGODB_PASSWORD"
      },
      "request_timeout": 30,
      "pool": {
        "connections": 10,
        "max_size": 10,
        "timeout": 5
      },
      "retry": {
        "enabled": true,
        "max_attempts": 3,
        "backoff_factor": 1.5,
        "max_backoff_seconds": 10
      },
      "tls": {
        "enabled": false,
        "verify": true
      }
    }
  }
}
```
- `jq` 1.6+（供 `infra/arangodb/*.sh` 腳本輸出格式化結果）

## 2. Docker Compose 流程
1. 建立持久化資料夾：
   ```bash
   mkdir -p datasets/arangodb/data datasets/arangodb/apps
   ```
2. 啟動服務：
   ```bash
   docker-compose up -d arangodb
   ```
3. 建立初始資料庫與帳號（可選）：
   ```bash
   ./infra/arangodb/bootstrap.sh
   ```
4. 健康檢查：
   ```bash
   ./infra/arangodb/healthcheck.sh
   ```

## 3. Kubernetes 部署流程
1. 套用命名空間與基礎資源：
   ```bash
   kubectl apply -f k8s/base/namespaces.yaml
   kubectl apply -f k8s/base/arangodb-configmap.yaml
   kubectl apply -f k8s/base/arangodb-pvc.yaml
   kubectl apply -f k8s/base/arangodb-secret.yaml
   ```
2. 部署 StatefulSet 與 Service：
   ```bash
   kubectl apply -f k8s/base/arangodb-statefulset.yaml
   kubectl apply -f k8s/base/service.yaml   # 內含 arangodb-service
   ```
3. 監控與儀表板（可選）：
   ```bash
   kubectl apply -f k8s/monitoring/prometheus-config.yaml
   kubectl apply -f k8s/monitoring/chromadb-metrics.yaml   # 共用 Prometheus 設定
   kubectl apply -f k8s/monitoring/chromadb-dashboard.yaml # 可另複製製作 ArangoDB 版
   ```

## 4. Failover 與擴充建議
- 預設 StatefulSet 以單節點(Replica=1)運行。若需 Active Failover：
  1. 將 `arangodb-statefulset.yaml` 的 `replicas` 調整為 3。
  2. 設定 `ARANGO_NO_AUTH=false` 並使用 Operator 或 Starter 模式（可透過 `ARANGO_STARTER_MODE=activefailover`）。
  3. 為每個 Pod 配置獨立 PVC，並在 Service 中啟用 `clusterIP: None`。
- 建議為備援節點開啟 `readOnly` 模式，由應用端根據 `/ _admin/server/role` 決定寫入節點。
- 若要為每個 Pod 提供獨立儲存，可將目前的 PVC 綁定改為 `volumeClaimTemplates`，使 `arangodb-statefulset.yaml` 自動建立 `arangodb-data-${pod}`。

## 5. 驗證與維運
- 檢查 Pod：
  ```bash
  kubectl -n ai-box get pods -l app=arangodb
  ```
- 查看服務：
  ```bash
  kubectl -n ai-box get svc arangodb-service
  ```
- 執行 AQL 健康查詢：
  ```bash
  kubectl -n ai-box exec -it statefulset/arangodb -- \
    arangosh --server.username root --server.password $ARANGO_ROOT_PASSWORD \
    --javascript.execute-string "db._databases()"
  ```
- 監控驗證：確認 Prometheus 能抓取 `/ _admin/metrics`，Grafana 面板中 CPU / 記憶體 / 查詢速度曲線正常。

## 6. 故障排查
- PVC 卡在 `Pending`：確認 `storageClassName=fast-ssd` 是否存在或依環境調整。
- Pod CrashLoop：檢查 Secret 是否存在、root 密碼是否正確。
- 連線逾時：確認 Service / NetworkPolicy 開放 8529 連接埠，或使用 `kubectl port-forward`.
- Failover 未生效：請確保 `ARANGO_STARTER_MODE` 設為 `activefailover` 並提供 3 個 Pod。

## 7. 資料匯入與查詢驗證
1. 根據 `docs/datasets/arangodb-kg-schema.md` 規劃資料模型，確認 `datasets/arangodb/schema.yml` 與 `seed_data.json` 已符合需求。
2. 執行資料匯入：
   ```bash
   poetry run python scripts/arangodb_seed.py --reset
   ```
   - 使用 `--dry-run` 可先檢視操作內容。
   - `--config` 可覆寫預設的 `config/config.json` 路徑。
3. Run-time 驗證：
   ```bash
   poetry run python scripts/arangodb_query_demo.py \
     --vertex entities/agent_planning \
     --relation-types handles requires \
     --limit 5
   ```
   - `neighbors` 區塊應顯示 Agent 與任務/資源的關聯。
   - `subgraph` 應輸出最短路徑資訊。
   - `entity_scan` 可確認 `filter_entities` 的分頁與條件。
4. API/Agent 集成前，可於 `tests/databases/arangodb` 目錄執行 `pytest` 驗證 SDK 行為。

## 7. 相關腳本
- `infra/arangodb/bootstrap.sh`：建立資料庫、使用者與預設集合。
- `infra/arangodb/healthcheck.sh`：檢查 Docker 及 K8s 執行個體的版本與健康狀態。
- `scripts/arangodb_seed.py`：知識圖譜資料匯入/重置。
- `scripts/arangodb_query_demo.py`：查詢封裝驗證。
- 以上腳本皆可在 CI/CD 中呼叫，確保 1.4.1/1.4.2/1.4.4 部署步驟寫入自動化流程。
