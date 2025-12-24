#!/bin/bash
# 代碼功能說明: MCP 自動化測試腳本
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

set -e

echo "=========================================="
echo "MCP Server/Client 自動化測試"
echo "=========================================="

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 測試結果計數
PASSED=0
FAILED=0

# 測試函數
test_health_check() {
    echo -e "\n${YELLOW}測試 1: 健康檢查端點${NC}"
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/health || echo "000")
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ 健康檢查通過${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ 健康檢查失敗 (HTTP $response)${NC}"
        ((FAILED++))
    fi
}

test_ready_check() {
    echo -e "\n${YELLOW}測試 2: 就緒檢查端點${NC}"
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/ready || echo "000")
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ 就緒檢查通過${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ 就緒檢查失敗 (HTTP $response)${NC}"
        ((FAILED++))
    fi
}

test_mcp_initialize() {
    echo -e "\n${YELLOW}測試 3: MCP 初始化請求${NC}"
    response=$(curl -s -X POST http://localhost:8002/mcp \
        -H "Content-Type: application/json" \
        -d '{
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }')

    if echo "$response" | grep -q '"result"'; then
        echo -e "${GREEN}✓ MCP 初始化成功${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ MCP 初始化失敗${NC}"
        echo "Response: $response"
        ((FAILED++))
    fi
}

test_mcp_list_tools() {
    echo -e "\n${YELLOW}測試 4: 列出工具${NC}"
    response=$(curl -s -X POST http://localhost:8002/mcp \
        -H "Content-Type: application/json" \
        -d '{
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }')

    if echo "$response" | grep -q '"tools"'; then
        echo -e "${GREEN}✓ 列出工具成功${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ 列出工具失敗${NC}"
        echo "Response: $response"
        ((FAILED++))
    fi
}

test_mcp_tool_call() {
    echo -e "\n${YELLOW}測試 5: 工具調用${NC}"
    response=$(curl -s -X POST http://localhost:8002/mcp \
        -H "Content-Type: application/json" \
        -d '{
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "task_analyzer",
                "arguments": {
                    "task": "Test task"
                }
            }
        }')

    if echo "$response" | grep -q '"result"'; then
        echo -e "${GREEN}✓ 工具調用成功${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ 工具調用失敗${NC}"
        echo "Response: $response"
        ((FAILED++))
    fi
}

# 檢查服務器是否運行
echo -e "\n${YELLOW}檢查 MCP Server 是否運行...${NC}"
if ! curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo -e "${RED}✗ MCP Server 未運行，請先啟動服務器${NC}"
    echo "啟動命令: python -m services.mcp_server.main"
    exit 1
fi

echo -e "${GREEN}✓ MCP Server 正在運行${NC}"

# 執行測試
test_health_check
test_ready_check
test_mcp_initialize
test_mcp_list_tools
test_mcp_tool_call

# 輸出測試結果
echo -e "\n=========================================="
echo "測試結果"
echo "=========================================="
echo -e "${GREEN}通過: $PASSED${NC}"
echo -e "${RED}失敗: $FAILED${NC}"
echo "總計: $((PASSED + FAILED))"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}所有測試通過！${NC}"
    exit 0
else
    echo -e "\n${RED}部分測試失敗${NC}"
    exit 1
fi
