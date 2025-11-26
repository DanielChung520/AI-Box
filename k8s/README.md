# Kubernetes 配置說明

**創建日期**: 2025-10-25
**創建人**: Daniel Chung
**最後修改日期**: 2025-10-25

---

## 目錄結構

```
k8s/
├── base/                    # 基礎配置
│   ├── namespaces.yaml     # 命名空間
│   ├── configmap.yaml      # ConfigMap
│   ├── secret.yaml         # Secret
│   └── service.yaml        # Service
└── monitoring/              # 監控配置
    ├── prometheus-config.yaml
    ├── prometheus-deployment.yaml
    └── grafana-deployment.yaml
```

## 使用說明

### 1. 創建命名空間

```bash
kubectl apply -f k8s/base/namespaces.yaml
```

### 2. 部署基礎資源

```bash
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/secret.yaml
kubectl apply -f k8s/base/service.yaml
```

### 3. 部署監控組件

```bash
# 部署 Prometheus
kubectl apply -f k8s/monitoring/prometheus-config.yaml
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml

# 部署 Grafana
kubectl apply -f k8s/monitoring/grafana-deployment.yaml
```

### 4. 訪問服務

```bash
# Prometheus
kubectl port-forward -n ai-box-monitoring svc/prometheus 9090:9090

# Grafana
kubectl port-forward -n ai-box-monitoring svc/grafana 3000:3000
```

## 注意事項

- Secret 文件中的密碼僅為示例，生產環境請使用安全的密碼管理方案
- 資源限制根據實際需求調整
- 監控組件的持久化存儲需要根據實際情況配置

---

**最後更新**: 2025-10-25
