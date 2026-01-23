#!/bin/bash
# 测试系统管理 API 端点

# 获取测试 token（假设有登录凭证）
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"systemAdmin","password":"Admin@2026"}' \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get token"
  exit 1
fi

echo "✓ Got authentication token"

# 测试各个端点
echo ""
echo "Testing API endpoints..."
echo "========================"

# 1. 测试服务状态
echo -n "1. /api/v1/admin/services: "
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "http://localhost:8000/api/v1/admin/services" \
  -H "Authorization: Bearer $TOKEN" --max-time 5)
STATUS=$(echo "$RESPONSE" | tail -1)
if [ "$STATUS" = "200" ]; then
  echo "✓ OK (Status: $STATUS)"
else
  echo "❌ Failed (Status: $STATUS)"
fi

# 2. 测试用户列表
echo -n "2. /api/v1/admin/users: "
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "http://localhost:8000/api/v1/admin/users?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN" --max-time 5)
STATUS=$(echo "$RESPONSE" | tail -1)
if [ "$STATUS" = "200" ]; then
  echo "✓ OK (Status: $STATUS)"
else
  echo "❌ Failed (Status: $STATUS)"
fi

# 3. 测试 Agent 请求列表
echo -n "3. /api/v1/admin/agent-requests: "
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "http://localhost:8000/api/v1/admin/agent-requests?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN" --max-time 5)
STATUS=$(echo "$RESPONSE" | tail -1)
if [ "$STATUS" = "200" ]; then
  echo "✓ OK (Status: $STATUS)"
else
  echo "❌ Failed (Status: $STATUS)"
fi

echo ""
echo "========================"
echo "All tests completed!"
