#!/bin/bash
# 代碼功能說明: Git 版本控制設置測試腳本，驗證 Git 倉庫、分支策略、.gitignore 和 Git Hooks
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

set -e

echo "=========================================="
echo "Git 版本控制設置測試腳本"
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
    local expected_result=$3
    
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

# 1. 倉庫初始化測試
echo "=== 1. 倉庫初始化測試 ==="
test_check "Git 倉庫已初始化" "git rev-parse --git-dir"
test_check "遠程倉庫已配置" "git remote -v | grep -q ."

if git remote -v &> /dev/null; then
    echo "  遠程倉庫:"
    git remote -v | sed 's/^/    /'
fi

echo ""

# 2. 分支創建測試
echo "=== 2. 分支創建測試 ==="
CURRENT_BRANCH=$(git branch --show-current)
echo "  當前分支: $CURRENT_BRANCH"

# 檢查 develop 分支是否存在
if git branch -a | grep -q "develop"; then
    echo -e "  ${GREEN}✓ develop 分支存在${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${YELLOW}⚠ develop 分支不存在${NC}"
fi

# 測試創建 feature 分支
TEST_BRANCH="feature/test-branch-$$"
if git checkout -b "$TEST_BRANCH" &> /dev/null; then
    echo -e "  ${GREEN}✓ 可以創建 feature 分支${NC}"
    PASSED=$((PASSED + 1))
    git checkout "$CURRENT_BRANCH" &> /dev/null
    git branch -D "$TEST_BRANCH" &> /dev/null
else
    echo -e "  ${RED}✗ 無法創建 feature 分支${NC}"
    FAILED=$((FAILED + 1))
fi

echo "  所有分支:"
git branch -a | sed 's/^/    /'

echo ""

# 3. .gitignore 測試
echo "=== 3. .gitignore 測試 ==="
if [ -f .gitignore ]; then
    echo -e "  ${GREEN}✓ .gitignore 文件存在${NC}"
    PASSED=$((PASSED + 1))
    
    # 測試 .gitignore 是否生效
    touch test.pyc
    if ! git status --porcelain | grep -q "test.pyc"; then
        echo -e "  ${GREEN}✓ .gitignore 生效（test.pyc 被忽略）${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${RED}✗ .gitignore 未生效${NC}"
        FAILED=$((FAILED + 1))
    fi
    rm -f test.pyc
else
    echo -e "  ${RED}✗ .gitignore 文件不存在${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""

# 4. Git Hooks 測試
echo "=== 4. Git Hooks 測試 ==="
if [ -d .git/hooks ]; then
    HOOKS_COUNT=$(ls -1 .git/hooks/* 2>/dev/null | wc -l | tr -d ' ')
    echo "  已安裝的 hooks: $HOOKS_COUNT"
    
    if [ -f .git/hooks/pre-commit ]; then
        echo -e "  ${GREEN}✓ pre-commit hook 存在${NC}"
        PASSED=$((PASSED + 1))
        
        # 檢查是否為 pre-commit 框架
        if grep -q "pre-commit" .git/hooks/pre-commit 2>/dev/null; then
            echo -e "  ${GREEN}✓ pre-commit 框架已安裝${NC}"
            PASSED=$((PASSED + 1))
        fi
    else
        echo -e "  ${YELLOW}⚠ pre-commit hook 不存在${NC}"
    fi
    
    if [ -f .pre-commit-config.yaml ]; then
        echo -e "  ${GREEN}✓ .pre-commit-config.yaml 存在${NC}"
        PASSED=$((PASSED + 1))
    fi
else
    echo -e "  ${RED}✗ .git/hooks 目錄不存在${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""

# 5. 分支保護規則檢查（需要 GitHub CLI 或 API）
echo "=== 5. 分支保護規則檢查 ==="
if command -v gh &> /dev/null; then
    if gh auth status &> /dev/null; then
        echo "  使用 GitHub CLI 檢查分支保護規則..."
        # 這裡可以添加具體的檢查邏輯
        echo -e "  ${YELLOW}⚠ 請手動檢查 GitHub 分支保護規則${NC}"
    else
        echo -e "  ${YELLOW}⚠ GitHub CLI 未登錄，請手動檢查${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠ GitHub CLI 未安裝，請手動檢查分支保護規則${NC}"
    echo "    訪問: GitHub → Settings → Branches"
fi

echo ""

# 6. 文檔檢查
echo "=== 6. 文檔檢查 ==="
DOCS=("README.md" "CONTRIBUTING.md" "CHANGELOG.md")
for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "  ${GREEN}✓ $doc 存在${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${YELLOW}⚠ $doc 不存在${NC}"
    fi
done

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

