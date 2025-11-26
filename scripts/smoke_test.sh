#!/bin/bash
# 代碼功能說明: API 服務 Smoke Test 腳本
# 創建日期: 2025-11-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

set -e

# 配置
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
TEST_REPORT_FILE="${TEST_REPORT_FILE:-smoke_test_report.txt}"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 測試計數器
PASSED=0
FAILED=0

# 測試函數
test_endpoint() {
    local method=$1
    local endpoint=$2
    local expected_status=${3:-200}
    local description=$4

    echo -n "Testing $description... "

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE_URL}${endpoint}")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -d "$5")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $http_code)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (Expected HTTP $expected_status, got HTTP $http_code)"
        echo "Response: $body" | head -c 200
        echo ""
        ((FAILED++))
        return 1
    fi
}

# 開始測試
echo "=========================================="
echo "API Smoke Test"
echo "=========================================="
echo "API Base URL: $API_BASE_URL"
echo "Test Report: $TEST_REPORT_FILE"
echo ""

# 測試健康檢查端點
test_endpoint "GET" "/health" 200 "Health Check"
test_endpoint "GET" "/ready" 200 "Readiness Check"
test_endpoint "GET" "/metrics" 200 "Metrics Endpoint"

# 測試版本信息端點
test_endpoint "GET" "/version" 200 "Version Info"

# 測試 OpenAPI 文檔
test_endpoint "GET" "/docs" 200 "OpenAPI Docs (Swagger UI)"
test_endpoint "GET" "/redoc" 200 "OpenAPI Docs (ReDoc)"
test_endpoint "GET" "/openapi.json" 200 "OpenAPI JSON Schema"

# 測試 API 端點（基本檢查）
test_endpoint "GET" "/api/v1/agents/discover" 200 "Agents Discover"

# 生成報告
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Total:  $((PASSED + FAILED))"
echo ""

# 保存報告
{
    echo "API Smoke Test Report"
    echo "===================="
    echo "Date: $(date)"
    echo "API Base URL: $API_BASE_URL"
    echo ""
    echo "Results:"
    echo "  Passed: $PASSED"
    echo "  Failed: $FAILED"
    echo "  Total:  $((PASSED + FAILED))"
} > "$TEST_REPORT_FILE"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    exit 1
fi
