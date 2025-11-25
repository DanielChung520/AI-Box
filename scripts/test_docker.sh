#!/bin/bash
# 代碼功能說明: Docker 環境測試腳本，驗證 Docker 安裝、構建和運行
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

set -e

echo "=========================================="
echo "Docker 環境測試腳本"
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

# 1. Docker 安裝檢查
echo "=== 1. Docker 安裝檢查 ==="
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "  ${GREEN}✓ Docker 已安裝: $DOCKER_VERSION${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${RED}✗ Docker 未安裝${NC}"
    FAILED=$((FAILED + 1))
    exit 1
fi

echo ""

# 2. Docker 守護進程檢查
echo "=== 2. Docker 守護進程檢查 ==="
test_check "Docker 守護進程運行中" "docker ps"

if docker ps &> /dev/null; then
    CONTAINER_COUNT=$(docker ps -q | wc -l | tr -d ' ')
    echo "  運行中的容器數: $CONTAINER_COUNT"
fi

echo ""

# 3. Docker 基本功能測試
echo "=== 3. Docker 基本功能測試 ==="
test_check "可以運行 hello-world 容器" "docker run --rm hello-world"

echo ""

# 4. Dockerfile 檢查
echo "=== 4. Dockerfile 檢查 ==="
if [ -f "Dockerfile" ] || find . -name "Dockerfile" -type f | grep -q .; then
    echo -e "  ${GREEN}✓ Dockerfile 存在${NC}"
    PASSED=$((PASSED + 1))
    
    # 檢查 Dockerfile 語法（簡單檢查）
    if find . -name "Dockerfile" -type f -exec grep -q "FROM" {} \; 2>/dev/null; then
        echo -e "  ${GREEN}✓ Dockerfile 格式正確${NC}"
        PASSED=$((PASSED + 1))
    fi
else
    echo -e "  ${YELLOW}⚠ Dockerfile 不存在（可選）${NC}"
fi

echo ""

# 5. docker-compose 檢查
echo "=== 5. docker-compose 檢查 ==="
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version)
        echo -e "  ${GREEN}✓ Docker Compose 已安裝: $COMPOSE_VERSION${NC}"
    else
        COMPOSE_VERSION=$(docker-compose --version)
        echo -e "  ${GREEN}✓ Docker Compose 已安裝: $COMPOSE_VERSION${NC}"
    fi
    PASSED=$((PASSED + 1))
    
    # 檢查 docker-compose.yml
    if [ -f "docker-compose.yml" ] || [ -f "docker-compose.yaml" ]; then
        echo -e "  ${GREEN}✓ docker-compose.yml 存在${NC}"
        PASSED=$((PASSED + 1))
        
        # 驗證 docker-compose.yml 語法
        if docker compose config &> /dev/null || docker-compose config &> /dev/null; then
            echo -e "  ${GREEN}✓ docker-compose.yml 語法正確${NC}"
            PASSED=$((PASSED + 1))
        else
            echo -e "  ${YELLOW}⚠ docker-compose.yml 語法可能有問題${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠ docker-compose.yml 不存在（可選）${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠ Docker Compose 未安裝${NC}"
fi

echo ""

# 6. Docker 網路測試
echo "=== 6. Docker 網路測試 ==="
if docker network ls &> /dev/null; then
    NETWORK_COUNT=$(docker network ls -q | wc -l | tr -d ' ')
    echo "  Docker 網路數: $NETWORK_COUNT"
    echo -e "  ${GREEN}✓ Docker 網路功能正常${NC}"
    PASSED=$((PASSED + 1))
fi

echo ""

# 7. Docker 資源檢查
echo "=== 7. Docker 資源檢查 ==="
if docker info &> /dev/null; then
    echo "  Docker 系統信息:"
    docker info 2>/dev/null | grep -E "CPUs|Total Memory|Operating System" | sed 's/^/    /' || true
    echo -e "  ${GREEN}✓ Docker 資源信息可獲取${NC}"
    PASSED=$((PASSED + 1))
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
    exit 1
fi

