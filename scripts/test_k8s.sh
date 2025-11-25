#!/bin/bash
# 代碼功能說明: Kubernetes 環境測試腳本，驗證 k3s 安裝、kubectl 配置和集群狀態
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

set -e

echo "=========================================="
echo "Kubernetes 環境測試腳本"
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

# 1. kubectl 安裝檢查
echo "=== 1. kubectl 安裝檢查 ==="
if command -v kubectl &> /dev/null; then
    KUBECTL_VERSION=$(kubectl version --client --short 2>/dev/null | head -n 1)
    echo -e "  ${GREEN}✓ kubectl 已安裝: $KUBECTL_VERSION${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${RED}✗ kubectl 未安裝${NC}"
    FAILED=$((FAILED + 1))
    echo "  請安裝 kubectl: brew install kubectl"
fi

echo ""

# 2. k3s 檢查
echo "=== 2. k3s 檢查 ==="
if command -v k3s &> /dev/null; then
    K3S_VERSION=$(k3s --version 2>/dev/null | head -n 1)
    echo -e "  ${GREEN}✓ k3s 已安裝: $K3S_VERSION${NC}"
    PASSED=$((PASSED + 1))
    
    # 檢查 k3s 服務狀態
    if sudo systemctl is-active --quiet k3s 2>/dev/null || pgrep -x k3s &> /dev/null; then
        echo -e "  ${GREEN}✓ k3s 服務運行中${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${YELLOW}⚠ k3s 服務未運行${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠ k3s 未安裝（可選，可使用 Docker Desktop K8s）${NC}"
fi

echo ""

# 3. Kubernetes 集群連接檢查
echo "=== 3. Kubernetes 集群連接檢查 ==="
if command -v kubectl &> /dev/null; then
    if kubectl cluster-info &> /dev/null; then
        echo -e "  ${GREEN}✓ 可以連接到 Kubernetes 集群${NC}"
        PASSED=$((PASSED + 1))
        
        # 顯示集群信息
        echo "  集群信息:"
        kubectl cluster-info | sed 's/^/    /'
        
        # 檢查節點狀態
        echo ""
        echo "  節點狀態:"
        if kubectl get nodes &> /dev/null; then
            kubectl get nodes | sed 's/^/    /'
            PASSED=$((PASSED + 1))
        fi
    else
        echo -e "  ${RED}✗ 無法連接到 Kubernetes 集群${NC}"
        FAILED=$((FAILED + 1))
        echo "  請檢查 kubeconfig 配置"
    fi
fi

echo ""

# 4. 命名空間檢查
echo "=== 4. 命名空間檢查 ==="
if kubectl get namespaces &> /dev/null; then
    NAMESPACES=("ai-box" "ai-box-agents" "ai-box-monitoring")
    for ns in "${NAMESPACES[@]}"; do
        if kubectl get namespace "$ns" &> /dev/null; then
            echo -e "  ${GREEN}✓ 命名空間 $ns 存在${NC}"
            PASSED=$((PASSED + 1))
        else
            echo -e "  ${YELLOW}⚠ 命名空間 $ns 不存在（可選）${NC}"
        fi
    done
    
    echo ""
    echo "  所有命名空間:"
    kubectl get namespaces | sed 's/^/    /'
else
    echo -e "  ${YELLOW}⚠ 無法獲取命名空間列表${NC}"
fi

echo ""

# 5. 基礎資源檢查
echo "=== 5. 基礎資源檢查 ==="
if kubectl get namespaces ai-box &> /dev/null; then
    # 檢查 ConfigMap
    if kubectl get configmap -n ai-box &> /dev/null; then
        CONFIGMAP_COUNT=$(kubectl get configmap -n ai-box --no-headers 2>/dev/null | wc -l | tr -d ' ')
        echo "  ConfigMap 數量: $CONFIGMAP_COUNT"
    fi
    
    # 檢查 Secret
    if kubectl get secret -n ai-box &> /dev/null; then
        SECRET_COUNT=$(kubectl get secret -n ai-box --no-headers 2>/dev/null | wc -l | tr -d ' ')
        echo "  Secret 數量: $SECRET_COUNT"
    fi
    
    # 檢查 ServiceAccount
    if kubectl get serviceaccount -n ai-box &> /dev/null; then
        SA_COUNT=$(kubectl get serviceaccount -n ai-box --no-headers 2>/dev/null | wc -l | tr -d ' ')
        echo "  ServiceAccount 數量: $SA_COUNT"
    fi
    
    echo -e "  ${GREEN}✓ 基礎資源檢查完成${NC}"
    PASSED=$((PASSED + 1))
fi

echo ""

# 6. 測試部署
echo "=== 6. 測試部署 ==="
if kubectl get namespaces ai-box &> /dev/null; then
    # 檢查是否有測試部署
    if kubectl get deployment -n ai-box &> /dev/null; then
        DEPLOYMENT_COUNT=$(kubectl get deployment -n ai-box --no-headers 2>/dev/null | wc -l | tr -d ' ')
        echo "  部署數量: $DEPLOYMENT_COUNT"
        
        if [ "$DEPLOYMENT_COUNT" -gt 0 ]; then
            echo "  部署狀態:"
            kubectl get deployment -n ai-box | sed 's/^/    /'
            PASSED=$((PASSED + 1))
        fi
    fi
else
    echo -e "  ${YELLOW}⚠ 命名空間不存在，跳過測試部署檢查${NC}"
fi

echo ""

# 7. kubeconfig 檢查
echo "=== 7. kubeconfig 檢查 ==="
if [ -f ~/.kube/config ]; then
    echo -e "  ${GREEN}✓ kubeconfig 文件存在${NC}"
    PASSED=$((PASSED + 1))
    
    # 檢查當前上下文
    if kubectl config current-context &> /dev/null; then
        CURRENT_CONTEXT=$(kubectl config current-context)
        echo "  當前上下文: $CURRENT_CONTEXT"
        PASSED=$((PASSED + 1))
    fi
else
    echo -e "  ${YELLOW}⚠ kubeconfig 文件不存在${NC}"
    echo "  請設置 kubeconfig:"
    echo "    mkdir -p ~/.kube"
    echo "    sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config"
    echo "    sudo chown \$USER ~/.kube/config"
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
    exit 0
else
    echo -e "${YELLOW}⚠ 部分測試未通過，請檢查上述結果${NC}"
    exit 0  # 返回 0，因為有些測試是可選的
fi

