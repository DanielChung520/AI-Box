#!/bin/bash
# 代碼功能說明: 開發環境驗證腳本，用於驗證 Python、Node.js、Docker、Git 等開發工具的安裝和配置
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

set -e

echo "=========================================="
echo "開發環境驗證腳本"
echo "=========================================="
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 驗證結果計數
PASSED=0
FAILED=0

# 驗證函數
check_command() {
    local cmd=$1
    local expected_version=$2
    local description=$3
    
    echo -n "檢查 $description... "
    
    if command -v $cmd &> /dev/null; then
        local version=$($cmd --version 2>&1 | head -n 1)
        echo -e "${GREEN}✓${NC} $version"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} 未安裝"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Python 環境驗證
echo "=== Python 環境驗證 ==="
check_command "python3" "3.11+" "Python 3"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo "  Python 版本: $PYTHON_VERSION"
    
    # 測試虛擬環境創建
    echo -n "  測試虛擬環境創建... "
    if python3 -m venv /tmp/test_venv_$$ &> /dev/null; then
        echo -e "${GREEN}✓${NC}"
        source /tmp/test_venv_$$/bin/activate
        PYTHON_VENV_VERSION=$(python --version 2>&1)
        echo "  虛擬環境 Python 版本: $PYTHON_VENV_VERSION"
        deactivate
        rm -rf /tmp/test_venv_$$
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
    fi
fi

echo ""

# Node.js 環境驗證
echo "=== Node.js 環境驗證 ==="
check_command "node" "18+" "Node.js"
check_command "npm" "" "npm"
check_command "yarn" "" "yarn (可選)"

if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "  Node.js 版本: $NODE_VERSION"
fi

if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "  npm 版本: $NPM_VERSION"
fi

echo ""

# Docker 環境驗證
echo "=== Docker 環境驗證 ==="
check_command "docker" "" "Docker"

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "  Docker 版本: $DOCKER_VERSION"
    
    # 測試 Docker 守護進程
    echo -n "  檢查 Docker 守護進程... "
    if docker ps &> /dev/null; then
        echo -e "${GREEN}✓${NC}"
        PASSED=$((PASSED + 1))
        
        # 測試 hello-world 容器
        echo -n "  測試 hello-world 容器... "
        if docker run --rm hello-world &> /dev/null; then
            echo -e "${GREEN}✓${NC}"
            PASSED=$((PASSED + 1))
        else
            echo -e "${YELLOW}⚠${NC} 無法運行容器（可能需要權限）"
        fi
    else
        echo -e "${RED}✗${NC} Docker 守護進程未運行"
        FAILED=$((FAILED + 1))
    fi
fi

echo ""

# Git 環境驗證
echo "=== Git 環境驗證 ==="
check_command "git" "2.40+" "Git"

if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version)
    echo "  Git 版本: $GIT_VERSION"
    
    # 檢查 Git 配置
    echo -n "  檢查 Git 用戶配置... "
    if git config --global user.name &> /dev/null && git config --global user.email &> /dev/null; then
        echo -e "${GREEN}✓${NC}"
        echo "    用戶名: $(git config --global user.name)"
        echo "    郵箱: $(git config --global user.email)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${YELLOW}⚠${NC} Git 用戶配置未設置"
    fi
fi

echo ""

# 其他工具驗證
echo "=== 其他開發工具驗證 ==="
check_command "curl" "" "curl"
check_command "jq" "" "jq (可選)"
check_command "kubectl" "" "kubectl (可選)"

echo ""

# 總結
echo "=========================================="
echo "驗證結果總結"
echo "=========================================="
echo -e "${GREEN}通過: ${PASSED}${NC}"
echo -e "${RED}失敗: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 所有檢查通過！${NC}"
    exit 0
else
    echo -e "${RED}✗ 部分檢查失敗，請檢查上述錯誤${NC}"
    exit 1
fi

