# Cloudflare MCP Gateway 生产环境迁移指南

**创建日期**: 2025-12-31
**创建人**: Daniel Chung
**最后修改日期**: 2025-12-31

---

## 📋 概述

将 MCP Gateway 从开发环境 Cloudflare 账户迁移到生产环境 Cloudflare 账户。

**迁移资源**:

- Worker 代码
- KV 命名空间数据
- Secrets（需重新设置）
- 路由配置
- 安全规则

---

## 🎯 迁移配置

### 环境变量

```yaml
# 开发环境
DEV_ACCOUNT: "dev@example.com"
DEV_WORKER_NAME: "mcp-gateway-dev"
DEV_DOMAIN: "mcp-gateway-dev.your-subdomain.workers.dev"
DEV_AUTH_STORE_ID: "dev_auth_store_id"
DEV_PERMISSIONS_STORE_ID: "dev_permissions_store_id"
DEV_RATE_LIMIT_STORE_ID: "dev_rate_limit_store_id"

# 生产环境
PROD_ACCOUNT: "prod@example.com"
PROD_WORKER_NAME: "mcp-gateway-prod"
PROD_DOMAIN: "mcp-gateway.your-domain.com"
PROD_AUTH_STORE_ID: ""  # 需要创建后填入
PROD_PERMISSIONS_STORE_ID: ""  # 需要创建后填入
PROD_RATE_LIMIT_STORE_ID: ""  # 需要创建后填入
```

---

## 🔄 迁移步骤

### STEP 1: 备份开发环境

**ACTION**: 备份所有开发环境数据

```bash
cd mcp/gateway
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"

# 导出 KV 数据
wrangler kv:key list --namespace-id=${DEV_AUTH_STORE_ID} > ${BACKUP_DIR}/dev_auth_store.json
wrangler kv:key list --namespace-id=${DEV_PERMISSIONS_STORE_ID} > ${BACKUP_DIR}/dev_permissions_store.json
wrangler kv:key list --namespace-id=${DEV_RATE_LIMIT_STORE_ID} > ${BACKUP_DIR}/dev_rate_limit_store.json

# 备份配置文件
cp wrangler.toml ${BACKUP_DIR}/wrangler.dev.toml

# 记录 Secrets 名称（不记录值）
cat > ${BACKUP_DIR}/secrets_list.txt << EOF
GATEWAY_SECRET
OFFICE_API_KEY
SLACK_CLIENT_SECRET
EOF
```

**CHECK**: 验证备份文件存在

```bash
ls -la ${BACKUP_DIR}/
```

---

### STEP 2: 切换 Cloudflare 账户

**ACTION**: 登录生产环境账户

```bash
# 登出开发账户
wrangler logout

# 登录生产账户
wrangler login

# 验证账户
wrangler whoami
```

**CHECK**: 确认当前账户为生产账户

```bash
# 输出应显示生产账户邮箱
wrangler whoami | grep -i "email"
```

---

### STEP 3: 创建生产环境 KV 命名空间

**ACTION**: 创建所有必需的 KV 命名空间

```bash
# 创建 AUTH_STORE
AUTH_OUTPUT=$(wrangler kv:namespace create "AUTH_STORE")
PROD_AUTH_STORE_ID=$(echo $AUTH_OUTPUT | jq -r '.id')
echo "PROD_AUTH_STORE_ID=${PROD_AUTH_STORE_ID}"

AUTH_PREVIEW_OUTPUT=$(wrangler kv:namespace create "AUTH_STORE" --preview)
PROD_AUTH_STORE_PREVIEW_ID=$(echo $AUTH_PREVIEW_OUTPUT | jq -r '.id')
echo "PROD_AUTH_STORE_PREVIEW_ID=${PROD_AUTH_STORE_PREVIEW_ID}"

# 创建 PERMISSIONS_STORE
PERM_OUTPUT=$(wrangler kv:namespace create "PERMISSIONS_STORE")
PROD_PERMISSIONS_STORE_ID=$(echo $PERM_OUTPUT | jq -r '.id')
echo "PROD_PERMISSIONS_STORE_ID=${PROD_PERMISSIONS_STORE_ID}"

PERM_PREVIEW_OUTPUT=$(wrangler kv:namespace create "PERMISSIONS_STORE" --preview)
PROD_PERMISSIONS_STORE_PREVIEW_ID=$(echo $PERM_PREVIEW_OUTPUT | jq -r '.id')
echo "PROD_PERMISSIONS_STORE_PREVIEW_ID=${PROD_PERMISSIONS_STORE_PREVIEW_ID}"

# 创建 RATE_LIMIT_STORE
RATE_OUTPUT=$(wrangler kv:namespace create "RATE_LIMIT_STORE")
PROD_RATE_LIMIT_STORE_ID=$(echo $RATE_OUTPUT | jq -r '.id')
echo "PROD_RATE_LIMIT_STORE_ID=${PROD_RATE_LIMIT_STORE_ID}"

RATE_PREVIEW_OUTPUT=$(wrangler kv:namespace create "RATE_LIMIT_STORE" --preview)
PROD_RATE_LIMIT_STORE_PREVIEW_ID=$(echo $RATE_PREVIEW_OUTPUT | jq -r '.id')
echo "PROD_RATE_LIMIT_STORE_PREVIEW_ID=${PROD_RATE_LIMIT_STORE_PREVIEW_ID}"
```

**CHECK**: 验证所有命名空间已创建

```bash
wrangler kv:namespace list | grep -E "(AUTH_STORE|PERMISSIONS_STORE|RATE_LIMIT_STORE)"
```

---

### STEP 4: 创建生产环境配置

**ACTION**: 创建 `wrangler.prod.toml`

```toml
# wrangler.prod.toml
name = "mcp-gateway-prod"
main = "src/index.ts"
compatibility_date = "2024-12-31"

[[kv_namespaces]]
binding = "AUTH_STORE"
id = "${PROD_AUTH_STORE_ID}"
preview_id = "${PROD_AUTH_STORE_PREVIEW_ID}"

[[kv_namespaces]]
binding = "PERMISSIONS_STORE"
id = "${PROD_PERMISSIONS_STORE_ID}"
preview_id = "${PROD_PERMISSIONS_STORE_PREVIEW_ID}"

[[kv_namespaces]]
binding = "RATE_LIMIT_STORE"
id = "${PROD_RATE_LIMIT_STORE_ID}"
preview_id = "${PROD_RATE_LIMIT_STORE_PREVIEW_ID}"

routes = [
  { pattern = "mcp-gateway.your-domain.com/*", zone_name = "your-domain.com" }
]
```

**CHECK**: 验证配置文件格式

```bash
cat wrangler.prod.toml | grep -E "(name|id =)"
```

---

### STEP 5: 迁移 KV 数据

**ACTION**: 批量迁移 KV 数据

```bash
# 迁移脚本
cat > migrate_kv.sh << 'SCRIPT_EOF'
#!/bin/bash
set -e

DEV_NS_ID=$1
PROD_NS_ID=$2
NS_NAME=$3

echo "Migrating ${NS_NAME} from ${DEV_NS_ID} to ${PROD_NS_ID}"

# 获取所有键
KEYS=$(wrangler kv:key list --namespace-id=${DEV_NS_ID} | jq -r '.[].name')

for KEY in $KEYS; do
  echo "Migrating key: ${KEY}"

  # 获取值
  VALUE=$(wrangler kv:key get "${KEY}" --namespace-id=${DEV_NS_ID})

  # 写入生产环境
  echo "${VALUE}" | wrangler kv:key put "${KEY}" --namespace-id=${PROD_NS_ID} --path -

  echo "✓ Migrated: ${KEY}"
done

echo "Migration completed for ${NS_NAME}"
SCRIPT_EOF

chmod +x migrate_kv.sh

# 执行迁移
./migrate_kv.sh ${DEV_AUTH_STORE_ID} ${PROD_AUTH_STORE_ID} "AUTH_STORE"
./migrate_kv.sh ${DEV_PERMISSIONS_STORE_ID} ${PROD_PERMISSIONS_STORE_ID} "PERMISSIONS_STORE"
./migrate_kv.sh ${DEV_RATE_LIMIT_STORE_ID} ${PROD_RATE_LIMIT_STORE_ID} "RATE_LIMIT_STORE"
```

**CHECK**: 验证数据迁移成功

```bash
# 比较键数量
DEV_COUNT=$(wrangler kv:key list --namespace-id=${DEV_AUTH_STORE_ID} | jq '. | length')
PROD_COUNT=$(wrangler kv:key list --namespace-id=${PROD_AUTH_STORE_ID} | jq '. | length')

if [ "$DEV_COUNT" -eq "$PROD_COUNT" ]; then
  echo "✓ KV data migration verified"
else
  echo "✗ KV data count mismatch: DEV=${DEV_COUNT}, PROD=${PROD_COUNT}"
  exit 1
fi
```

---

### STEP 6: 设置生产环境 Secrets

**ACTION**: 设置所有必需的 Secrets

```bash
# 生成新的 Gateway Secret
PROD_GATEWAY_SECRET=$(openssl rand -hex 32)
echo "Generated Gateway Secret: ${PROD_GATEWAY_SECRET}"

# 设置 Secrets（需要交互式输入）
wrangler secret put GATEWAY_SECRET << EOF
${PROD_GATEWAY_SECRET}
EOF

# 设置其他 Secrets（根据实际需要）
# wrangler secret put OFFICE_API_KEY
# wrangler secret put SLACK_CLIENT_SECRET
```

**CHECK**: 验证 Secrets 已设置

```bash
# 注意：无法直接列出 Secrets，只能通过部署测试验证
echo "Secrets configured. Will verify during deployment."
```

---

### STEP 7: 部署生产环境 Worker

**ACTION**: 部署 Worker

```bash
# 确保在生产账户
wrangler whoami

# 部署
wrangler deploy --config wrangler.prod.toml
```

**CHECK**: 验证部署成功

```bash
# 检查 Worker 状态
wrangler deployments list --name mcp-gateway-prod

# 测试端点
curl -X POST https://mcp-gateway.your-domain.com/mcp \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: ${PROD_GATEWAY_SECRET}" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

---

### STEP 8: 更新 AI-Box 配置

**ACTION**: 更新环境变量

```bash
# 更新 .env 文件
cat >> .env << EOF
# MCP Gateway Production
MCP_GATEWAY_ENDPOINT=https://mcp-gateway.your-domain.com
MCP_GATEWAY_SECRET=${PROD_GATEWAY_SECRET}
EOF
```

**CHECK**: 验证配置更新

```bash
grep -E "MCP_GATEWAY" .env
```

---

### STEP 9: 配置域名和 DNS

**ACTION**: 在 Cloudflare Dashboard 配置

```yaml
# 配置步骤（需在 Dashboard 中操作）
steps:
  - action: "add_route"
    worker: "mcp-gateway-prod"
    route: "mcp-gateway.your-domain.com/*"
    zone: "your-domain.com"

  - action: "configure_dns"
    type: "CNAME"
    name: "mcp-gateway"
    target: "your-domain.com"

  - action: "configure_ssl"
    mode: "Full"
```

**CHECK**: 验证域名配置

```bash
# 检查 DNS 解析
dig mcp-gateway.your-domain.com

# 检查 SSL 证书
curl -I https://mcp-gateway.your-domain.com/mcp
```

---

### STEP 10: 配置安全规则

**ACTION**: 配置 WAF 和速率限制

```yaml
# WAF 规则配置
waf_rules:
  - name: "MCP Gateway Protection"
    expression: "(http.request.uri.path contains \"/mcp\")"
    action: "Challenge"

# 速率限制配置
rate_limits:
  - match: "http.request.uri.path eq \"/mcp\""
    limit: 100
    period: 60
    action: "Block"
```

**CHECK**: 验证安全规则

```bash
# 在 Cloudflare Dashboard 中验证规则已创建
echo "Verify WAF and Rate Limiting rules in Dashboard"
```

---

### STEP 11: 配置监控和日志

**ACTION**: 启用 Logpush 和告警

```yaml
# Logpush 配置
logpush:
  enabled: true
  destination: "s3://your-bucket/logs"
  log_type: "HTTP Requests"

# 告警配置
alerts:
  - name: "Worker Error Rate"
    condition: "worker.errors > 10"
    action: "notify"

  - name: "Worker Response Time"
    condition: "worker.response_time > 1000"
    action: "notify"
```

**CHECK**: 验证监控配置

```bash
# 检查 Logpush 任务
# 在 Dashboard 中验证告警规则
```

---

### STEP 12: 完整验证

**ACTION**: 执行完整功能测试

```bash
# 测试脚本
cat > test_production.sh << 'TEST_EOF'
#!/bin/bash
set -e

GATEWAY_URL="https://mcp-gateway.your-domain.com"
GATEWAY_SECRET="${PROD_GATEWAY_SECRET}"

echo "Testing Production Gateway..."

# 1. 测试认证
echo "1. Testing authentication..."
RESPONSE=$(curl -s -X POST ${GATEWAY_URL}/mcp \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: ${GATEWAY_SECRET}" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}')

if echo "$RESPONSE" | jq -e '.result' > /dev/null; then
  echo "✓ Authentication test passed"
else
  echo "✗ Authentication test failed"
  exit 1
fi

# 2. 测试工具调用
echo "2. Testing tool call..."
TOOL_RESPONSE=$(curl -s -X POST ${GATEWAY_URL}/mcp \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: ${GATEWAY_SECRET}" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -H "X-Tool-Name: yahoo_finance_quote" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"yahoo_finance_quote","arguments":{"symbol":"AAPL"}}}')

if echo "$TOOL_RESPONSE" | jq -e '.result' > /dev/null; then
  echo "✓ Tool call test passed"
else
  echo "✗ Tool call test failed"
  exit 1
fi

echo "All tests passed!"
TEST_EOF

chmod +x test_production.sh
./test_production.sh
```

**CHECK**: 验证所有测试通过

```bash
# 检查测试输出
./test_production.sh | grep -E "(✓|✗)"
```

---

## 🔄 回滚方案

### 快速回滚

**ACTION**: 切换回开发环境

```bash
# 更新 AI-Box 配置
export MCP_GATEWAY_ENDPOINT=https://mcp-gateway-dev.workers.dev
export MCP_GATEWAY_SECRET=${DEV_GATEWAY_SECRET}

# 重启服务
# systemctl restart ai-box  # 根据实际部署方式调整
```

---

## 📋 迁移检查清单

### 迁移前检查

```yaml
pre_migration:
  - [ ] 备份开发环境 KV 数据
  - [ ] 备份配置文件
  - [ ] 记录 Secrets 名称
  - [ ] 准备生产环境账户
  - [ ] 验证生产环境配额
```

### 迁移中检查

```yaml
migration:
  - [ ] 切换 Cloudflare 账户
  - [ ] 创建生产环境 KV 命名空间
  - [ ] 迁移 KV 数据
  - [ ] 设置生产环境 Secrets
  - [ ] 部署生产环境 Worker
  - [ ] 配置域名和 DNS
  - [ ] 配置安全规则
```

### 迁移后检查

```yaml
post_migration:
  - [ ] 功能验证通过
  - [ ] 性能指标正常
  - [ ] 安全配置生效
  - [ ] 监控和告警正常
  - [ ] AI-Box 配置已更新
```

---

## 🔧 自动化迁移脚本

### 完整迁移脚本

```bash
#!/bin/bash
# migrate_to_production.sh

set -e

# 配置
source migration_config.env  # 包含所有环境变量

echo "=== Starting Migration ==="

# STEP 1: 备份
echo "STEP 1: Backing up development environment..."
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
# ... 备份逻辑 ...

# STEP 2: 切换账户
echo "STEP 2: Switching Cloudflare account..."
wrangler logout
wrangler login
wrangler whoami

# STEP 3: 创建 KV 命名空间
echo "STEP 3: Creating production KV namespaces..."
# ... 创建逻辑 ...

# STEP 4: 迁移数据
echo "STEP 4: Migrating KV data..."
# ... 迁移逻辑 ...

# STEP 5: 设置 Secrets
echo "STEP 5: Setting production secrets..."
# ... Secrets 设置逻辑 ...

# STEP 6: 部署
echo "STEP 6: Deploying production Worker..."
wrangler deploy --config wrangler.prod.toml

# STEP 7: 验证
echo "STEP 7: Verifying deployment..."
./test_production.sh

echo "=== Migration Completed ==="
```

---

## 🛡️ 安全注意事项

### Secrets 管理

```yaml
secrets_management:
  rules:
    - "never_hardcode_in_code"
    - "never_commit_to_git"
    - "use_wrangler_secret_put"
    - "regenerate_for_production"
    - "rotate_quarterly"
```

### 数据迁移安全

```yaml
data_migration:
  rules:
    - "use_https_only"
    - "verify_data_integrity"
    - "delete_temp_files_after_migration"
    - "use_minimum_privileges"
```

### 访问控制

```yaml
access_control:
  rules:
    - "separate_prod_account"
    - "limit_prod_access"
    - "enable_2fa"
    - "review_logs_regularly"
```

---

## 📊 验证检查点

### 功能验证

```bash
# 检查点列表
checkpoints:
  - name: "authentication"
    command: "curl -X POST ${GATEWAY_URL}/mcp -H 'X-Gateway-Secret: ${SECRET}' -d '{\"method\":\"tools/list\"}'"
    expected: "200 OK with result"

  - name: "tool_call"
    command: "curl -X POST ${GATEWAY_URL}/mcp -H 'X-Gateway-Secret: ${SECRET}' -d '{\"method\":\"tools/call\",\"params\":{...}}'"
    expected: "200 OK with result"

  - name: "error_handling"
    command: "curl -X POST ${GATEWAY_URL}/mcp -d '{\"method\":\"invalid\"}'"
    expected: "400/500 with error"
```

### 性能验证

```yaml
performance_checks:
  - metric: "response_time"
    threshold: 1000  # ms
    action: "alert_if_exceeded"

  - metric: "error_rate"
    threshold: 0.01  # 1%
    action: "alert_if_exceeded"

  - metric: "throughput"
    threshold: 100  # requests/min
    action: "monitor"
```

---

## 🆘 故障处理

### 常见问题

```yaml
troubleshooting:
  - issue: "migration_failed_access"
    checks:
      - "verify_dns_config"
      - "verify_worker_route"
      - "verify_ssl_tls"
    solution: "check_dashboard_configuration"

  - issue: "authentication_failed"
    checks:
      - "verify_gateway_secret"
      - "verify_request_headers"
      - "check_worker_logs"
    solution: "verify_secrets_and_headers"

  - issue: "kv_data_missing"
    checks:
      - "verify_backup_exists"
      - "verify_namespace_ids"
    solution: "restore_from_backup"
```

---

## 📚 相关文档

- [Cloudflare MCP Gateway 设置指南](./Cloudflare-MCP-Gateway-设置指南.md)
- [MCP 工具系统规格](./MCP工具.md)

---

**最后更新日期**: 2025-12-31
**维护人**: Daniel Chung
