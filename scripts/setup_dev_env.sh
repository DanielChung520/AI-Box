#!/bin/bash
# 代碼功能說明: 開發環境自動化設置腳本，自動安裝和配置開發環境所需的工具
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

set -e

echo "=========================================="
echo "開發環境自動化設置腳本"
echo "=========================================="
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 檢查是否為 macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}錯誤: 此腳本僅適用於 macOS${NC}"
    exit 1
fi

# 檢查 Homebrew 是否安裝
check_homebrew() {
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}Homebrew 未安裝，正在安裝...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo -e "${GREEN}✓ Homebrew 已安裝${NC}"
    fi
}

# 安裝 Python 3.11+
install_python() {
    echo -e "${BLUE}安裝 Python 3.11+...${NC}"

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}' | cut -d. -f1,2)
        if [[ $(echo "$PYTHON_VERSION >= 3.11" | bc -l 2>/dev/null || echo "0") == "1" ]]; then
            echo -e "${GREEN}✓ Python $PYTHON_VERSION 已安裝${NC}"
            return 0
        fi
    fi

    brew install python@3.11
    echo -e "${GREEN}✓ Python 3.11+ 安裝完成${NC}"
}

# 安裝 Node.js 18+
install_nodejs() {
    echo -e "${BLUE}安裝 Node.js 18+...${NC}"

    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version | cut -d. -f1 | sed 's/v//')
        if [[ $NODE_VERSION -ge 18 ]]; then
            echo -e "${GREEN}✓ Node.js $(node --version) 已安裝${NC}"
            return 0
        fi
    fi

    brew install node@18
    echo -e "${GREEN}✓ Node.js 18+ 安裝完成${NC}"
}

# 配置 npm 全局包路徑
setup_npm() {
    echo -e "${BLUE}配置 npm...${NC}"

    mkdir -p ~/.npm-global
    npm config set prefix '~/.npm-global'

    # 添加到 PATH（如果尚未添加）
    if ! grep -q '~/.npm-global/bin' ~/.zshrc 2>/dev/null; then
        echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.zshrc
    fi

    # 安裝全局工具
    npm install -g yarn typescript ts-node 2>/dev/null || true

    echo -e "${GREEN}✓ npm 配置完成${NC}"
}

# 安裝 Docker Desktop（需要手動下載）
install_docker() {
    echo -e "${BLUE}檢查 Docker...${NC}"

    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓ Docker 已安裝${NC}"
        return 0
    fi

    echo -e "${YELLOW}Docker Desktop 需要手動安裝${NC}"
    echo "請訪問: https://www.docker.com/products/docker-desktop"
    echo "下載適用於 Apple Silicon 的版本並安裝"
    echo ""
    read -p "安裝完成後按 Enter 繼續..."

    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓ Docker 安裝完成${NC}"
    else
        echo -e "${RED}✗ Docker 仍未安裝，請稍後手動安裝${NC}"
    fi
}

# 安裝 VS Code
install_vscode() {
    echo -e "${BLUE}檢查 VS Code...${NC}"

    if command -v code &> /dev/null; then
        echo -e "${GREEN}✓ VS Code 已安裝${NC}"
        return 0
    fi

    brew install --cask visual-studio-code
    echo -e "${GREEN}✓ VS Code 安裝完成${NC}"
    echo -e "${YELLOW}請手動安裝以下 VS Code 插件:${NC}"
    echo "  - Python"
    echo "  - Docker"
    echo "  - Kubernetes"
    echo "  - GitLens"
    echo "  - YAML"
    echo "  - Markdown All in One"
}

# 安裝其他開發工具
install_dev_tools() {
    echo -e "${BLUE}安裝其他開發工具...${NC}"

    brew install git curl jq kubectl helm || true

    # 配置 Git（如果尚未配置）
    if ! git config --global user.name &> /dev/null; then
        echo -e "${YELLOW}請配置 Git 用戶信息:${NC}"
        read -p "Git 用戶名: " git_name
        read -p "Git 郵箱: " git_email
        git config --global user.name "$git_name"
        git config --global user.email "$git_email"
    fi

    git config --global init.defaultBranch main

    echo -e "${GREEN}✓ 開發工具安裝完成${NC}"
}

# 創建項目虛擬環境
setup_venv() {
    echo -e "${BLUE}設置項目虛擬環境...${NC}"

    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    cd "$PROJECT_DIR"

    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo -e "${GREEN}✓ 虛擬環境創建完成${NC}"
    else
        echo -e "${GREEN}✓ 虛擬環境已存在${NC}"
    fi

    source venv/bin/activate
    pip install --upgrade pip
    pip install pytest black ruff mypy pre-commit || true

    echo -e "${GREEN}✓ Python 依賴安裝完成${NC}"
}

# 主函數
main() {
    echo "開始設置開發環境..."
    echo ""

    check_homebrew
    echo ""

    install_python
    echo ""

    install_nodejs
    echo ""

    setup_npm
    echo ""

    install_docker
    echo ""

    install_vscode
    echo ""

    install_dev_tools
    echo ""

    setup_venv
    echo ""

    echo "=========================================="
    echo -e "${GREEN}開發環境設置完成！${NC}"
    echo "=========================================="
    echo ""
    echo "下一步:"
    echo "1. 運行 ./scripts/verify_env.sh 驗證環境"
    echo "2. 激活虛擬環境: source venv/bin/activate"
    echo "3. 安裝 VS Code 插件（如未安裝）"
}

# 執行主函數
main
