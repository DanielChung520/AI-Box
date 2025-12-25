<!--
代碼功能說明: ChromaDB 部署指南
創建日期: 2025-11-25 21:25 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-11-25 21:25 (UTC+8)
-->

# ChromaDB 部署指南

## 1. 前置需求

- Docker Desktop / containerd 環境
- Kubernetes 1.28+（含 `kubectl` 權限）
- Prometheus + Grafana 監控命名空間 `ai-box-monitoring`
- 本地 SSD 掛載路徑 `datasets/chromadb`（對應 docker-compose volume）
- 已建立 `config/config.json`（由 `config/config.example.json` 複製），其中的 `datastores.chromadb` 欄位會提供路徑/埠號等非敏感設定

## 2. Docker Compose 流程

1. 建立持久化資料夾：

   ```bash
   mkdir -p datasets/chromadb
   ```

2. 啟動服務：

   ```bash
   docker-compose up -d chromadb
   ```

3. 健康檢查：

   ```bash
   curl http://localhost:8001/api/v1/heartbeat
   ```

## 3. Kubernetes 部署流程

1. 套用命名空間與基礎資源：

   ```bash
   kubectl apply -f k8s/base/namespaces.yaml
   kubectl apply -f k8s/base/chromadb-configmap.yaml
   kubectl apply -f k8s/base/chromadb-pvc.yaml
   ```

2. 部署工作負載與服務：

   ```bash
   kubectl apply -f k8s/base/chromadb-deployment.yaml
   kubectl apply -f k8s/base/service.yaml
   ```

3. 監控與儀表板：

   ```bash
   kubectl apply -f k8s/monitoring/prometheus-config.yaml
   kubectl apply -f k8s/monitoring/chromadb-metrics.yaml
   kubectl apply -f k8s/monitoring/chromadb-dashboard.yaml
   ```

## 4. 驗證與維運

- 檢查 Pod：

  ```bash
  kubectl -n ai-box get pods -l app=chromadb
  ```

- 查看服務：

  ```bash
  kubectl -n ai-box get svc chromadb-service
  ```

- 監控驗證：

  ```bash
  kubectl -n ai-box-monitoring get servicemonitor chromadb
  ```

- Grafana 匯入 `grafana-dashboard-chromadb` ConfigMap，即可看到延遲、CPU、記憶體三大圖表。

## 5. 故障排查

- 若 PVC 卡在 `Pending`，確認 `storageClassName=fast-ssd` 已存在或改成環境既有 StorageClass。
- 監控無數據時，先檢查 `chromadb` Pod 上的 `prometheus.io` 註解是否存在。
- 若需要水平擴展，調整 `chromadb-deployment.yaml` 的 `replicas` 並確保 Persistent Volume 支援 RWO。
