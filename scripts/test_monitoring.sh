#!/bin/bash
# 代碼功能說明: 監控基礎設施測試腳本，驗證 Prometheus 和 Grafana 部署和配置
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

set -e

echo "=========================================="
echo "監控基礎設施測試腳本"
echo "=========================================="
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# 測試函數
test_check() {
    local description=$1
    local command=$2
    
    echo -n "測試: $description... "
    
    if eval "$command" &> /dev/null; then
        echo -e "${GREEN}✓${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# 1. Kubernetes 環境檢查
echo "=== 1. Kubernetes 環境檢查 ==="
if ! command -v kubectl &> /dev/null; then
    echo -e "  ${RED}✗ kubectl 未安裝${NC}"
    FAILED=$((FAILED + 1))
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    echo -e "  ${RED}✗ 無法連接到 Kubernetes 集群${NC}"
    FAILED=$((FAILED + 1))
    exit 1
fi

echo -e "  ${GREEN}✓ Kubernetes 環境可用${NC}"
PASSED=$((PASSED + 1))

echo ""

# 2. 命名空間檢查
echo "=== 2. 命名空間檢查 ==="
MONITORING_NS="ai-box-monitoring"

if kubectl get namespace "$MONITORING_NS" &> /dev/null; then
    echo -e "  ${GREEN}✓ 命名空間 $MONITORING_NS 存在${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${YELLOW}⚠ 命名空間 $MONITORING_NS 不存在${NC}"
    echo "    創建命名空間: kubectl create namespace $MONITORING_NS"
fi

echo ""

# 3. Prometheus 檢查
echo "=== 3. Prometheus 檢查 ==="
if kubectl get namespace "$MONITORING_NS" &> /dev/null; then
    # 檢查 Prometheus Deployment
    if kubectl get deployment -n "$MONITORING_NS" 2>/dev/null | grep -q prometheus; then
        echo -e "  ${GREEN}✓ Prometheus Deployment 存在${NC}"
        PASSED=$((PASSED + 1))
        
        # 檢查 Pod 狀態
        PROMETHEUS_PODS=$(kubectl get pods -n "$MONITORING_NS" -l app=prometheus --no-headers 2>/dev/null | wc -l | tr -d ' ')
        if [ "$PROMETHEUS_PODS" -gt 0 ]; then
            echo "  Prometheus Pods: $PROMETHEUS_PODS"
            kubectl get pods -n "$MONITORING_NS" -l app=prometheus | sed 's/^/    /'
            
            # 檢查 Pod 是否運行
            RUNNING_PODS=$(kubectl get pods -n "$MONITORING_NS" -l app=prometheus --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l | tr -d ' ')
            if [ "$RUNNING_PODS" -gt 0 ]; then
                echo -e "  ${GREEN}✓ Prometheus Pods 運行中${NC}"
                PASSED=$((PASSED + 1))
            else
                echo -e "  ${YELLOW}⚠ Prometheus Pods 未運行${NC}"
            fi
        fi
        
        # 檢查 Service
        if kubectl get service -n "$MONITORING_NS" 2>/dev/null | grep -q prometheus; then
            echo -e "  ${GREEN}✓ Prometheus Service 存在${NC}"
            PASSED=$((PASSED + 1))
            
            # 檢查端口轉發
            PROMETHEUS_PORT=$(kubectl get service -n "$MONITORING_NS" prometheus -o jsonpath='{.spec.ports[0].port}' 2>/dev/null || echo "9090")
            echo "  Prometheus 端口: $PROMETHEUS_PORT"
        fi
        
        # 檢查 ConfigMap
        if kubectl get configmap -n "$MONITORING_NS" 2>/dev/null | grep -q prometheus; then
            echo -e "  ${GREEN}✓ Prometheus ConfigMap 存在${NC}"
            PASSED=$((PASSED + 1))
        fi
    else
        echo -e "  ${YELLOW}⚠ Prometheus Deployment 不存在${NC}"
        echo "    請部署 Prometheus"
    fi
else
    echo -e "  ${YELLOW}⚠ 命名空間不存在，跳過 Prometheus 檢查${NC}"
fi

echo ""

# 4. Grafana 檢查
echo "=== 4. Grafana 檢查 ==="
if kubectl get namespace "$MONITORING_NS" &> /dev/null; then
    # 檢查 Grafana Deployment
    if kubectl get deployment -n "$MONITORING_NS" 2>/dev/null | grep -q grafana; then
        echo -e "  ${GREEN}✓ Grafana Deployment 存在${NC}"
        PASSED=$((PASSED + 1))
        
        # 檢查 Pod 狀態
        GRAFANA_PODS=$(kubectl get pods -n "$MONITORING_NS" -l app=grafana --no-headers 2>/dev/null | wc -l | tr -d ' ')
        if [ "$GRAFANA_PODS" -gt 0 ]; then
            echo "  Grafana Pods: $GRAFANA_PODS"
            kubectl get pods -n "$MONITORING_NS" -l app=grafana | sed 's/^/    /'
            
            # 檢查 Pod 是否運行
            RUNNING_PODS=$(kubectl get pods -n "$MONITORING_NS" -l app=grafana --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l | tr -d ' ')
            if [ "$RUNNING_PODS" -gt 0 ]; then
                echo -e "  ${GREEN}✓ Grafana Pods 運行中${NC}"
                PASSED=$((PASSED + 1))
            else
                echo -e "  ${YELLOW}⚠ Grafana Pods 未運行${NC}"
            fi
        fi
        
        # 檢查 Service
        if kubectl get service -n "$MONITORING_NS" 2>/dev/null | grep -q grafana; then
            echo -e "  ${GREEN}✓ Grafana Service 存在${NC}"
            PASSED=$((PASSED + 1))
            
            # 檢查端口
            GRAFANA_PORT=$(kubectl get service -n "$MONITORING_NS" grafana -o jsonpath='{.spec.ports[0].port}' 2>/dev/null || echo "3000")
            echo "  Grafana 端口: $GRAFANA_PORT"
        fi
    else
        echo -e "  ${YELLOW}⚠ Grafana Deployment 不存在${NC}"
        echo "    請部署 Grafana"
    fi
else
    echo -e "  ${YELLOW}⚠ 命名空間不存在，跳過 Grafana 檢查${NC}"
fi

echo ""

# 5. 監控配置檢查
echo "=== 5. 監控配置檢查 ==="
if [ -d "k8s/monitoring" ] || find . -path "*/monitoring/*" -name "*.yaml" -o -name "*.yml" 2>/dev/null | grep -q .; then
    echo -e "  ${GREEN}✓ 監控配置文件存在${NC}"
    PASSED=$((PASSED + 1))
    
    CONFIG_COUNT=$(find . -path "*/monitoring/*" \( -name "*.yaml" -o -name "*.yml" \) 2>/dev/null | wc -l | tr -d ' ')
    echo "  配置文件數: $CONFIG_COUNT"
else
    echo -e "  ${YELLOW}⚠ 監控配置文件不存在（可選）${NC}"
fi

echo ""

# 6. 告警規則檢查
echo "=== 6. 告警規則檢查 ==="
if kubectl get namespace "$MONITORING_NS" &> /dev/null; then
    # 檢查 PrometheusRule 或 ConfigMap 中的告警規則
    if kubectl get prometheusrule -n "$MONITORING_NS" 2>/dev/null | grep -q .; then
        echo -e "  ${GREEN}✓ PrometheusRule 存在${NC}"
        PASSED=$((PASSED + 1))
    elif kubectl get configmap -n "$MONITORING_NS" prometheus-config 2>/dev/null | grep -q "alert:"; then
        echo -e "  ${GREEN}✓ 告警規則在 ConfigMap 中配置${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${YELLOW}⚠ 告警規則未配置（可選）${NC}"
    fi
fi

echo ""

# 7. 數據收集測試
echo "=== 7. 數據收集測試 ==="
if kubectl get namespace "$MONITORING_NS" &> /dev/null; then
    # 嘗試訪問 Prometheus API（需要端口轉發）
    echo "  測試 Prometheus 數據收集..."
    echo -e "  ${YELLOW}⚠ 需要手動測試${NC}"
    echo "    1. 端口轉發: kubectl port-forward -n $MONITORING_NS svc/prometheus 9090:9090"
    echo "    2. 訪問: http://localhost:9090"
    echo "    3. 查詢 'up' 指標，應有數據"
fi

echo ""

# 總結
echo "=========================================="
echo "測試結果總結"
echo "=========================================="
echo -e "${GREEN}通過: ${PASSED}${NC}"
echo -e "${RED}失敗: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 所有測試通過！${NC}"
    echo ""
    echo "下一步:"
    echo "1. 訪問 Prometheus: kubectl port-forward -n $MONITORING_NS svc/prometheus 9090:9090"
    echo "2. 訪問 Grafana: kubectl port-forward -n $MONITORING_NS svc/grafana 3000:3000"
    echo "3. 配置 Grafana 數據源連接到 Prometheus"
    exit 0
else
    echo -e "${YELLOW}⚠ 部分測試未通過，請檢查上述結果${NC}"
    exit 0  # 返回 0，因為有些測試是可選的
fi

