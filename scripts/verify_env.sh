# 代碼功能說明: 開發環境驗證腳本，用於驗證 Python、Node.js、Docker、Git 等工具並生成 Ollama 節點硬體報告
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 23:33 (UTC+8)
#!/bin/bash

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

# Ollama 報告輸出位置
OLLAMA_REPORT_PATH="${OLLAMA_REPORT_PATH:-docs/deployment/ollama-health-report.md}"
OLLAMA_TARGET_HOST="${OLLAMA_TARGET_HOST:-localhost}"
OLLAMA_TARGET_PORT="${OLLAMA_TARGET_PORT:-11434}"
OLLAMA_DATA_DIR="${OLLAMA_DATA_DIR:-/}"

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

# 其他工具驗證與系統觀測
echo "=== 其他工具與系統觀測 ==="
check_command "curl" "" "curl"
check_command "jq" "" "jq (可選)"
check_command "kubectl" "" "kubectl (可選)"
echo ""

collect_cpu_info() {
    if [[ "$(uname -s)" == "Darwin" ]]; then
        sysctl -n machdep.cpu.brand_string
    elif command -v lscpu >/dev/null 2>&1; then
        lscpu | awk -F': +' '/Model name/ {print $2; exit}'
    else
        echo "Unknown CPU"
    fi
}

collect_mem_info() {
    if [[ "$(uname -s)" == "Darwin" ]]; then
        local bytes
        bytes=$(sysctl -n hw.memsize)
        awk -v b="${bytes}" 'BEGIN { printf "%.2f GiB", b/1024/1024/1024 }'
    elif [[ -r /proc/meminfo ]]; then
        awk '/MemTotal/ { printf "%.2f GiB", $2/1024/1024 }' /proc/meminfo
    else
        echo "Unknown memory"
    fi
}

collect_gpu_info() {
    if command -v nvidia-smi >/dev/null 2>&1; then
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    elif [[ "$(uname -s)" == "Darwin" ]]; then
        system_profiler SPDisplaysDataType | awk -F': ' '/Chipset Model/ {print $2; exit}'
    else
        echo "Unknown GPU"
    fi
}

collect_disk_info() {
    df -h "${OLLAMA_DATA_DIR}" | awk 'NR==1 || NR==2 {print}'
}

collect_ollama_version() {
    if command -v ollama >/dev/null 2>&1; then
        ollama --version
    else
        echo "ollama command not found"
    fi
}

collect_ollama_models() {
    if command -v ollama >/dev/null 2>&1; then
        ollama list || true
    else
        echo "N/A - ollama command not found"
    fi
}

check_ollama_api() {
    if ! command -v curl >/dev/null 2>&1; then
        echo "curl not available"
        return
    fi

    local url="http://${OLLAMA_TARGET_HOST}:${OLLAMA_TARGET_PORT}/api/version"
    if curl -sf --max-time 5 "${url}" >/dev/null 2>&1; then
        echo "OK (${url})"
    else
        echo "UNREACHABLE (${url})"
    fi
}

write_ollama_report() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S %Z')
    mkdir -p "$(dirname "${OLLAMA_REPORT_PATH}")"
    cat > "${OLLAMA_REPORT_PATH}" <<EOF
# Ollama 節點硬體檢查報告

- 報告時間：${timestamp}
- 目標節點：${OLLAMA_TARGET_HOST}:${OLLAMA_TARGET_PORT}
- 生成工具：scripts/verify_env.sh

## 硬體摘要

| 項目 | 數值 |
|------|------|
| CPU | $(collect_cpu_info) |
| 記憶體 | $(collect_mem_info) |
| GPU | $(collect_gpu_info) |
| 儲存（針對 ${OLLAMA_DATA_DIR}） | $(collect_disk_info | tail -n 1) |

## Ollama 狀態

- CLI 版本：$(collect_ollama_version)
- API 健康：$(check_ollama_api)

<details>
<summary>模型清單</summary>

\`\`\`
$(collect_ollama_models)
\`\`\`

</details>
EOF
}

echo "=== Ollama 節點健康檢查 ==="
echo "CPU: $(collect_cpu_info)"
echo "記憶體: $(collect_mem_info)"
echo "GPU: $(collect_gpu_info)"
echo "儲存 (${OLLAMA_DATA_DIR}):"
collect_disk_info
echo "Ollama CLI 版本: $(collect_ollama_version)"
echo "Ollama API 健康: $(check_ollama_api)"
echo "生成報告：${OLLAMA_REPORT_PATH}"
write_ollama_report
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
