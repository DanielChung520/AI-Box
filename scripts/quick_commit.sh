#!/bin/bash
# 快速提交腳本
# 功能說明：提供快速提交選項，可選擇性跳過某些檢查以節省時間
# 創建日期：2025-12-12
# 創建人：Daniel Chung
# 最後修改日期：2025-12-12

set -e

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 顯示使用說明
show_usage() {
    echo "用法: $0 [選項] <提交訊息>"
    echo ""
    echo "選項:"
    echo "  -f, --format-only    只運行格式化（black, ruff），跳過 mypy"
    echo "  -s, --skip-checks    跳過所有 pre-commit 檢查（緊急情況使用）"
    echo "  -a, --all-checks     運行所有檢查（默認）"
    echo "  -h, --help           顯示此幫助訊息"
    echo ""
    echo "示例:"
    echo "  $0 -f \"修復 bug\"          # 只格式化，不檢查類型"
    echo "  $0 -s \"緊急修復\"          # 跳過所有檢查（不推薦）"
    echo "  $0 \"正常提交\"             # 運行所有檢查"
}

# 解析參數
SKIP_MYPY=false
SKIP_ALL=false
COMMIT_MSG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--format-only)
            SKIP_MYPY=true
            shift
            ;;
        -s|--skip-checks)
            SKIP_ALL=true
            shift
            ;;
        -a|--all-checks)
            SKIP_MYPY=false
            SKIP_ALL=false
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            if [ -z "$COMMIT_MSG" ]; then
                COMMIT_MSG="$1"
            else
                COMMIT_MSG="$COMMIT_MSG $1"
            fi
            shift
            ;;
    esac
done

# 檢查提交訊息
if [ -z "$COMMIT_MSG" ]; then
    echo -e "${RED}錯誤：請提供提交訊息${NC}"
    show_usage
    exit 1
fi

# 檢查是否有修改
if [ -z "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}警告：沒有需要提交的修改${NC}"
    exit 0
fi

echo -e "${GREEN}開始快速提交流程...${NC}"

# 如果跳過所有檢查
if [ "$SKIP_ALL" = true ]; then
    echo -e "${YELLOW}警告：跳過所有 pre-commit 檢查${NC}"
    echo -e "${YELLOW}這可能會導致代碼質量問題，請謹慎使用${NC}"
    read -p "確認繼續？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 1
    fi
    git add .
    git commit --no-verify -m "$COMMIT_MSG"
    echo -e "${GREEN}提交完成（已跳過檢查）${NC}"
    exit 0
fi

# 只格式化，跳過 mypy
if [ "$SKIP_MYPY" = true ]; then
    echo -e "${GREEN}運行格式化檢查（跳過 mypy）...${NC}"
    
    # 只運行 black 和 ruff
    echo "1. 運行 black 格式化..."
    black . || true
    
    echo "2. 運行 ruff 檢查和修復..."
    ruff check --fix . || true
    
    echo "3. 添加修改的文件..."
    git add .
    
    echo "4. 提交（跳過 mypy）..."
    git commit --no-verify -m "$COMMIT_MSG"
    
    echo -e "${GREEN}提交完成（已跳過 mypy）${NC}"
    exit 0
fi

# 運行所有檢查（默認）
echo -e "${GREEN}運行所有檢查...${NC}"

# 先手動運行格式化，避免 pre-commit 重複運行
echo "1. 運行 black 格式化..."
black . || true

echo "2. 運行 ruff 檢查和修復..."
ruff check --fix . || true

echo "3. 添加修改的文件..."
git add .

echo "4. 提交（運行所有檢查，包括 mypy）..."
git commit -m "$COMMIT_MSG"

echo -e "${GREEN}提交完成！${NC}"
