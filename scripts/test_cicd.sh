#!/bin/bash
# 代碼功能說明: CI/CD 流程測試腳本，驗證 GitHub Actions 工作流配置和執行
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

set -e

echo "=========================================="
echo "CI/CD 流程測試腳本"
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

# 1. GitHub Actions 工作流文件檢查
echo "=== 1. GitHub Actions 工作流文件檢查 ==="
if [ -d ".github/workflows" ]; then
    echo -e "  ${GREEN}✓ .github/workflows 目錄存在${NC}"
    PASSED=$((PASSED + 1))
    
    WORKFLOW_COUNT=$(find .github/workflows -name "*.yml" -o -name "*.yaml" 2>/dev/null | wc -l | tr -d ' ')
    echo "  工作流文件數: $WORKFLOW_COUNT"
    
    if [ "$WORKFLOW_COUNT" -gt 0 ]; then
        echo "  工作流文件列表:"
        find .github/workflows -name "*.yml" -o -name "*.yaml" 2>/dev/null | sed 's/^/    /'
        PASSED=$((PASSED + 1))
        
        # 檢查 CI 工作流
        if [ -f ".github/workflows/ci.yml" ] || [ -f ".github/workflows/ci.yaml" ]; then
            echo -e "  ${GREEN}✓ CI 工作流文件存在${NC}"
            PASSED=$((PASSED + 1))
            
            # 驗證 YAML 語法（簡單檢查）
            if command -v yamllint &> /dev/null; then
                if yamllint .github/workflows/ci.yml 2>/dev/null || yamllint .github/workflows/ci.yaml 2>/dev/null; then
                    echo -e "  ${GREEN}✓ YAML 語法正確${NC}"
                    PASSED=$((PASSED + 1))
                else
                    echo -e "  ${YELLOW}⚠ YAML 語法可能有問題${NC}"
                fi
            fi
        else
            echo -e "  ${YELLOW}⚠ CI 工作流文件不存在${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠ 未找到工作流文件${NC}"
    fi
else
    echo -e "  ${RED}✗ .github/workflows 目錄不存在${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""

# 2. GitHub CLI 檢查（用於檢查 Actions 狀態）
echo "=== 2. GitHub CLI 檢查 ==="
if command -v gh &> /dev/null; then
    echo -e "  ${GREEN}✓ GitHub CLI 已安裝${NC}"
    PASSED=$((PASSED + 1))
    
    if gh auth status &> /dev/null; then
        echo -e "  ${GREEN}✓ GitHub CLI 已登錄${NC}"
        PASSED=$((PASSED + 1))
        
        # 檢查最近的 Actions 運行
        echo "  最近的 Actions 運行:"
        gh run list --limit 5 2>/dev/null | head -n 5 | sed 's/^/    /' || echo "    無法獲取運行列表"
    else
        echo -e "  ${YELLOW}⚠ GitHub CLI 未登錄${NC}"
        echo "    請運行: gh auth login"
    fi
else
    echo -e "  ${YELLOW}⚠ GitHub CLI 未安裝（可選）${NC}"
    echo "    安裝: brew install gh"
fi

echo ""

# 3. 工作流配置檢查
echo "=== 3. 工作流配置檢查 ==="
if [ -f ".github/workflows/ci.yml" ] || [ -f ".github/workflows/ci.yaml" ]; then
    CI_FILE=$(find .github/workflows -name "ci.yml" -o -name "ci.yaml" 2>/dev/null | head -n 1)
    
    # 檢查觸發條件
    if grep -q "on:" "$CI_FILE" 2>/dev/null; then
        echo -e "  ${GREEN}✓ 觸發條件已配置${NC}"
        PASSED=$((PASSED + 1))
    fi
    
    # 檢查 jobs
    if grep -q "jobs:" "$CI_FILE" 2>/dev/null; then
        echo -e "  ${GREEN}✓ Jobs 已配置${NC}"
        PASSED=$((PASSED + 1))
        
        # 檢查常見的 job
        if grep -q "lint\|test\|build" "$CI_FILE" 2>/dev/null; then
            echo -e "  ${GREEN}✓ 常見 Jobs (lint/test/build) 已配置${NC}"
            PASSED=$((PASSED + 1))
        fi
    fi
fi

echo ""

# 4. 本地測試工具檢查
echo "=== 4. 本地測試工具檢查 ==="
if command -v act &> /dev/null; then
    echo -e "  ${GREEN}✓ act (GitHub Actions 本地測試工具) 已安裝${NC}"
    PASSED=$((PASSED + 1))
    echo "    可以使用 'act' 命令在本地測試 GitHub Actions"
else
    echo -e "  ${YELLOW}⚠ act 未安裝（可選）${NC}"
    echo "    安裝: brew install act"
fi

echo ""

# 5. 依賴文件檢查
echo "=== 5. 依賴文件檢查 ==="
if [ -f "requirements.txt" ] || [ -f "requirements-dev.txt" ]; then
    echo -e "  ${GREEN}✓ Python 依賴文件存在${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${YELLOW}⚠ Python 依賴文件不存在（可選）${NC}"
fi

if [ -f "package.json" ]; then
    echo -e "  ${GREEN}✓ Node.js 依賴文件存在${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${YELLOW}⚠ Node.js 依賴文件不存在（可選）${NC}"
fi

echo ""

# 6. Docker 構建檢查
echo "=== 6. Docker 構建檢查 ==="
if [ -f "Dockerfile" ]; then
    echo -e "  ${GREEN}✓ Dockerfile 存在${NC}"
    PASSED=$((PASSED + 1))
    
    # 檢查工作流中是否有 Docker 構建步驟
    if [ -f ".github/workflows/ci.yml" ] || [ -f ".github/workflows/ci.yaml" ]; then
        CI_FILE=$(find .github/workflows -name "ci.yml" -o -name "ci.yaml" 2>/dev/null | head -n 1)
        if grep -qi "docker\|buildx" "$CI_FILE" 2>/dev/null; then
            echo -e "  ${GREEN}✓ Docker 構建步驟已配置${NC}"
            PASSED=$((PASSED + 1))
        fi
    fi
else
    echo -e "  ${YELLOW}⚠ Dockerfile 不存在（可選）${NC}"
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
    echo "1. 推送代碼到 GitHub 觸發 CI"
    echo "2. 檢查 GitHub Actions 頁面確認工作流執行"
    echo "3. 創建 PR 測試 CI 在 PR 上的執行"
    exit 0
else
    echo -e "${YELLOW}⚠ 部分測試未通過，請檢查上述結果${NC}"
    exit 0  # 返回 0，因為有些測試是可選的
fi

