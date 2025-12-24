#!/bin/bash
# 提交前快速檢查腳本
# 功能說明：在提交前快速檢查代碼，發現問題提前修復，避免提交時重試
# 創建日期：2025-12-12
# 創建人：Daniel Chung
# 最後修改日期：2025-12-12

set -e

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  提交前快速檢查工具${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 檢查是否有修改
if [ -z "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}沒有需要檢查的修改${NC}"
    exit 0
fi

ERRORS=0

# 1. 檢查修改的 Python 文件
PYTHON_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)
UNSTAGED_PYTHON_FILES=$(git diff --name-only --diff-filter=ACM | grep '\.py$' || true)

if [ -z "$PYTHON_FILES" ] && [ -z "$UNSTAGED_PYTHON_FILES" ]; then
    echo -e "${GREEN}✓ 沒有修改的 Python 文件${NC}"
else
    ALL_PYTHON_FILES="$PYTHON_FILES $UNSTAGED_PYTHON_FILES"

    echo -e "${BLUE}檢查 Python 文件...${NC}"

    # 2. Black 格式化檢查
    echo -n "  檢查 Black 格式..."
    if black --check $ALL_PYTHON_FILES 2>/dev/null; then
        echo -e " ${GREEN}✓${NC}"
    else
        echo -e " ${RED}✗${NC}"
        echo -e "  ${YELLOW}運行 'black .' 自動修復格式${NC}"
        ERRORS=$((ERRORS + 1))
    fi

    # 3. Ruff 檢查
    echo -n "  檢查 Ruff 代碼風格..."
    if ruff check $ALL_PYTHON_FILES 2>/dev/null; then
        echo -e " ${GREEN}✓${NC}"
    else
        echo -e " ${RED}✗${NC}"
        echo -e "  ${YELLOW}運行 'ruff check --fix .' 自動修復${NC}"
        ERRORS=$((ERRORS + 1))
    fi

    # 4. Mypy 類型檢查（可選，較慢）
    read -p "  是否運行 mypy 類型檢查？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -n "  檢查 Mypy 類型..."
        if mypy $ALL_PYTHON_FILES 2>/dev/null; then
            echo -e " ${GREEN}✓${NC}"
        else
            echo -e " ${RED}✗${NC}"
            echo -e "  ${YELLOW}請修復類型錯誤${NC}"
            ERRORS=$((ERRORS + 1))
        fi
    fi
fi

# 5. 檢查其他文件
echo -e "${BLUE}檢查其他文件...${NC}"

# JSON 文件
JSON_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.json$' || true)
if [ -n "$JSON_FILES" ]; then
    echo -n "  檢查 JSON 格式..."
    JSON_ERROR=false
    for file in $JSON_FILES; do
        if [[ "$file" != *"tsconfig.json"* ]]; then
            if ! python3 -m json.tool "$file" > /dev/null 2>&1; then
                echo -e " ${RED}✗ $file 格式錯誤${NC}"
                JSON_ERROR=true
                ERRORS=$((ERRORS + 1))
            fi
        fi
    done
    if [ "$JSON_ERROR" = false ]; then
        echo -e " ${GREEN}✓${NC}"
    fi
fi

# 總結
echo ""
echo -e "${BLUE}========================================${NC}"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有檢查通過！可以安全提交${NC}"
    echo -e "${BLUE}========================================${NC}"
    exit 0
else
    echo -e "${RED}✗ 發現 $ERRORS 個問題，請修復後再提交${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${YELLOW}快速修復命令：${NC}"
    echo "  black .                    # 格式化代碼"
    echo "  ruff check --fix .         # 修復代碼風格"
    echo "  mypy .                     # 檢查類型（可選）"
    exit 1
fi
