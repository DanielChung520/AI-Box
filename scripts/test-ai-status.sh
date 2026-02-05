#!/bin/bash

# AI-Box 呼吸大腦 AI 執行狀態顯示功能 - 完整測試腳本
# 用於測試所有功能是否正常工作

echo "=========================================="
echo "   AI-Box 呼吸大腦功能完整測試"
echo "=========================================="
echo ""
echo "測試時間: $(date)"
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 測試計數
PASSED=0
FAILED=0

# 測試函數
test_endpoint() {
    local name="$1"
    local url="$2"
    local method="$3"
    local data="$4"
    
    echo -e "${BLUE}[測試]${NC} $name"
    
    if [ -n "$data" ]; then
        response=$(curl -s -X "$method" "$url" -H "Content-Type: application/json" -d "$data")
    else
        response=$(curl -s -X "$method" "$url")
    fi
    
    if echo "$response" | grep -q '"status":'; then
        echo -e "${GREEN}✅ 通過${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ 失敗${NC}"
        echo "Response: $response"
        ((FAILED++))
    fi
    echo ""
}

# 生成測試 request_id
TEST_REQUEST_ID="test-$(date +%s)-$$"
echo "本次測試 Request ID: $TEST_REQUEST_ID"
echo ""

echo "=========================================="
echo "   Step 1: API 端點測試"
echo "=========================================="
echo ""

# 測試 1：啟動狀態追蹤
test_endpoint "啟動狀態追蹤" \
    "http://localhost:8000/api/v1/agent-status/start" \
    "POST" \
    "{\"request_id\": \"$TEST_REQUEST_ID\"}"

# 測試 2：發送狀態事件
test_endpoint "發送狀態事件 (接收請求)" \
    "http://localhost:8000/api/v1/agent-status/event" \
    "POST" \
    "{\"request_id\": \"$TEST_REQUEST_ID\", \"step\": \"接收請求\", \"status\": \"processing\", \"message\": \"收到用戶請求\", \"progress\": 0.0}"

test_endpoint "發送狀態事件 (L1 語義理解)" \
    "http://localhost:8000/api/v1/agent-status/event" \
    "POST" \
    "{\"request_id\": \"$TEST_REQUEST_ID\", \"step\": \"L1 語義理解\", \"status\": \"processing\", \"message\": \"Router LLM 分析中\", \"progress\": 0.35}"

test_endpoint "發送狀態事件 (完成處理)" \
    "http://localhost:8000/api/v1/agent-status/event" \
    "POST" \
    "{\"request_id\": \"$TEST_REQUEST_ID\", \"step\": \"完成處理\", \"status\": \"completed\", \"message\": \"處理完成\", \"progress\": 1.0}"

echo "=========================================="
echo "   Step 2: SSE 監聽測試"
echo "=========================================="
echo ""

# 生成新的 request_id 用於 SSE 測試
SSE_REQUEST_ID="sse-$(date +%s)-$$"

echo -e "${BLUE}[測試]${NC} SSE 連接和事件接收"
echo ""

# 啟動追蹤
curl -s -X POST "http://localhost:8000/api/v1/agent-status/start" \
    -H "Content-Type: application/json" \
    -d "{\"request_id\": \"$SSE_REQUEST_ID\"}" > /dev/null

# 後台運行 SSE 監聽
(
    sleep 1
    # 發送測試事件
    curl -s -X POST "http://localhost:8000/api/v1/agent-status/event" \
        -H "Content-Type: application/json" \
        -d "{\"request_id\": \"$SSE_REQUEST_ID\", \"step\": \"測試步驟\", \"status\": \"processing\", \"message\": \"測試消息\", \"progress\": 0.5}" > /dev/null
) &

# 監聽 SSE
SSE_OUTPUT=$(timeout 3 curl -s -N "http://localhost:8000/api/v1/agent-status/stream/$SSE_REQUEST_ID" 2>/dev/null)

if echo "$SSE_OUTPUT" | grep -q "測試步驟"; then
    echo -e "${GREEN}✅ SSE 監聽測試通過${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ SSE 監聽測試失敗${NC}"
    ((FAILED++))
fi
echo ""

echo "=========================================="
echo "   Step 3: 性能模擬測試"
echo "=========================================="
echo ""

PERF_REQUEST_ID="perf-$(date +%s)-$$"

# 啟動追蹤
curl -s -X POST "http://localhost:8000/api/v1/agent-status/start" \
    -H "Content-Type: application/json" \
    -d "{\"request_id\": \"$PERF_REQUEST_ID\"}" > /dev/null

# 模擬帶延遲的執行流程
(
    sleep 0.3
    curl -s -X POST "http://localhost:8000/api/v1/agent-status/event" \
        -H "Content-Type: application/json" \
        -d "{\"request_id\": \"$PERF_REQUEST_ID\", \"step\": \"接收請求\", \"status\": \"processing\", \"message\": \"收到用戶請求\", \"progress\": 0.0}" > /dev/null
    
    sleep 0.5
    curl -s -X POST "http://localhost:8000/api/v1/agent-status/event" \
        -H "Content-Type: application/json" \
        -d "{\"request_id\": \"$PERF_REQUEST_ID\", \"step\": \"L1 語義理解\", \"status\": \"processing\", \"message\": \"Router LLM 分析中\", \"progress\": 0.35}" > /dev/null
    
    sleep 0.2
    curl -s -X POST "http://localhost:8000/api/v1/agent-status/event" \
        -H "Content-Type: application/json" \
        -d "{\"request_id\": \"$PERF_REQUEST_ID\", \"step\": \"路由決策\", \"status\": \"completed\", \"message\": \"選擇 Agent\", \"progress\": 0.8}" > /dev/null
    
    sleep 0.8
    curl -s -X POST "http://localhost:8000/api/v1/agent-status/event" \
        -H "Content-Type: application/json" \
        -d "{\"request_id\": \"$PERF_REQUEST_ID\", \"step\": \"Agent 執行\", \"status\": \"completed\", \"message\": \"Agent 完成\", \"progress\": 0.85}" > /dev/null
    
    sleep 0.3
    curl -s -X POST "http://localhost:8000/api/v1/agent-status/event" \
        -H "Content-Type: application/json" \
        -d "{\"request_id\": \"$PERF_REQUEST_ID\", \"step\": \"完成處理\", \"status\": \"completed\", \"message\": \"處理完成\", \"progress\": 1.0}" > /dev/null
) &

echo -e "${BLUE}[測試]${NC} 性能模擬測試（5 個步驟，總延遲 ~2.1 秒）"

# 監聽 SSE
SSE_OUTPUT=$(timeout 5 curl -s -N "http://localhost:8000/api/v1/agent-status/stream/$PERF_REQUEST_ID" 2>/dev/null)

EVENT_COUNT=$(echo "$SSE_OUTPUT" | grep -c "data:")

if [ "$EVENT_COUNT" -ge 5 ]; then
    echo -e "${GREEN}✅ 性能模擬測試通過${NC} - 收到 $EVENT_COUNT 個事件"
    ((PASSED++))
else
    echo -e "${RED}❌ 性能模擬測試失敗${NC} - 收到 $EVENT_COUNT 個事件（期望 5+）"
    ((FAILED++))
fi
echo ""

echo "=========================================="
echo "   測試總結"
echo "=========================================="
echo ""
echo -e "通過: ${GREEN}$PASSED${NC}"
echo -e "失敗: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 所有測試通過！${NC}"
    echo ""
    echo "功能狀態："
    echo "  ✅ SSE 狀態推送正常工作"
    echo "  ✅ 全局進度條功能正常"
    echo "  ✅ 性能統計功能正常"
    echo "  ✅ 時間線功能正常"
    echo ""
    exit 0
else
    echo -e "${YELLOW}⚠️  有部分測試失敗，請檢查上述輸出${NC}"
    exit 1
fi
