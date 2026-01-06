# Cloudflare MCP Gateway 手动操作清单

**创建日期**: 2025-12-31
**创建人**: Daniel Chung
**最后修改日期**: 2025-12-31

---

## 📋 概述

本文档列出在实施第三方 MCP 管理时，**必须**在 Cloudflare Dashboard 上手动执行的操作。其他操作（如代码编写、配置更新等）可以由 AI 助手完成。

---

## ✅ 必须手动操作清单

### 🔐 阶段 1: 账户和基础设置（必须手动）

#### 1.1 创建/登录 Cloudflare 账户

**操作位置**: <https://dash.cloudflare.com/>

**操作步骤**:

1. 访问 Cloudflare 官网
2. 如果没有账户，点击 "Sign Up" 注册（免费账户即可）
3. 如果已有账户，直接登录

**注意事项**:

- 免费账户可以使用 Workers（10 万请求/天）
- 付费账户（$5/月起）提供更多功能和配额
- **重要**：Cloudflare 账户只用于部署和管理 Worker，不用于业务认证

**完成标志**: ✅ 能够登录 Cloudflare Dashboard

---

#### 1.2 安装 Wrangler CLI（本地操作，但需要手动）

**操作位置**: 本地终端

**操作步骤**:

```bash
# 使用 npm
npm install -g wrangler

# 或使用 pnpm
pnpm add -g wrangler

# 验证安装
wrangler --version
```

**完成标志**: ✅ `wrangler --version` 显示版本号

---

#### 1.3 登录 Wrangler（需要手动授权）

**操作位置**: 本地终端

**操作步骤**:

```bash
wrangler login
```

**操作说明**:

- 命令会打开浏览器
- 在浏览器中授权 Wrangler 访问你的 Cloudflare 账户
- 授权完成后，终端会显示成功信息

**完成标志**: ✅ 终端显示 "Successfully logged in"

---

### 🌐 阶段 2: 域名配置（如果使用自定义域名，必须手动）

#### 2.1 添加域名到 Cloudflare（可选）

**操作位置**: Cloudflare Dashboard → Add a Site

**操作步骤**:

1. 登录 Cloudflare Dashboard
2. 点击右上角 "Add a Site"
3. 输入你的域名（如 `your-domain.com`）
4. 选择计划（免费计划即可）
5. 按照提示更新域名的 Nameservers

**完成标志**: ✅ 域名状态显示为 "Active"

---

#### 2.2 配置 DNS 记录（如果使用自定义域名）

**操作位置**: Cloudflare Dashboard → 你的域名 → DNS → Records

**操作步骤**:

1. 进入你的域名管理页面
2. 点击 "DNS" → "Records"
3. 添加 CNAME 记录：
   - **Type**: CNAME
   - **Name**: `mcp-gateway`（或你想要的子域名）
   - **Target**: `your-worker-name.your-subdomain.workers.dev`
   - **Proxy status**: Proxied（橙色云朵图标）

**完成标志**: ✅ DNS 记录创建成功，状态为 "Active"

---

### 💾 阶段 3: 创建存储资源（必须手动）

#### 3.1 创建 KV 命名空间（方法一：Dashboard）

**操作位置**: Cloudflare Dashboard → Workers & Pages → KV

**操作步骤**:

1. 登录 Cloudflare Dashboard
2. 进入 "Workers & Pages"
3. 点击左侧菜单 "KV"
4. 点击 "Create a namespace"
5. 输入命名空间名称：`AUTH_STORE`
6. 点击 "Add"
7. **重复步骤 4-6**，创建以下命名空间：
   - `AUTH_STORE`（认证配置存储）
   - `PERMISSIONS_STORE`（权限配置存储）
   - `RATE_LIMIT_STORE`（速率限制存储）
8. **为每个命名空间创建预览版本**：
   - 点击命名空间右侧的 "..." 菜单
   - 选择 "Create preview namespace"
   - 输入预览命名空间名称（如 `AUTH_STORE_PREVIEW`）

**记录信息**:

- 记录每个命名空间的 **ID**（用于 `wrangler.toml` 配置）
- 记录每个预览命名空间的 **ID**

**完成标志**: ✅ 所有 KV 命名空间创建成功，并记录 ID

---

#### 3.2 创建 KV 命名空间（方法二：命令行，推荐）

**操作位置**: 本地终端（在 Gateway 项目目录）

**操作步骤**:

```bash
# 进入 Gateway 目录
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 创建生产环境 KV 命名空间
wrangler kv:namespace create "AUTH_STORE"
wrangler kv:namespace create "PERMISSIONS_STORE"
wrangler kv:namespace create "RATE_LIMIT_STORE"

# 创建预览环境 KV 命名空间
wrangler kv:namespace create "AUTH_STORE" --preview
wrangler kv:namespace create "PERMISSIONS_STORE" --preview
wrangler kv:namespace create "RATE_LIMIT_STORE" --preview
```

**操作说明**:

- 每个命令会返回命名空间的 ID
- 需要将这些 ID 添加到 `wrangler.toml` 配置文件中

**完成标志**: ✅ 所有 KV 命名空间创建成功，并记录 ID

---

#### 3.3 创建 R2 存储桶（可选，用于日志存储）

**操作位置**: Cloudflare Dashboard → R2

**操作步骤**:

1. 登录 Cloudflare Dashboard
2. 进入 "R2"
3. 点击 "Create bucket"
4. 输入存储桶名称：`mcp-gateway-audit-logs`
5. 选择位置（推荐选择离你最近的区域）
6. 点击 "Create bucket"
7. **重复步骤 3-6**，创建预览存储桶：`mcp-gateway-audit-logs-preview`

**完成标志**: ✅ R2 存储桶创建成功

---

### 🔒 阶段 4: 安全配置（必须手动）

#### 4.1 设置 Gateway Secret（Worker Secrets）

**操作位置**: 本地终端（在 Gateway 项目目录）

**操作步骤**:

```bash
# 1. 生成随机密钥（32 字节）
openssl rand -hex 32
# 输出示例：a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2

# 2. 进入 Gateway 目录
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 3. 设置 Worker Secret（需要先登录 wrangler）
wrangler secret put GATEWAY_SECRET
# 提示时输入刚才生成的密钥值

# 4. 记录密钥值（需要在 AI-Box 服务器上设置相同的值）
# 将密钥添加到 AI-Box 的 .env 文件：
# MCP_GATEWAY_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

**重要说明**:

- Gateway Secret 是**自定义密钥**，与 Cloudflare 账户无关
- 用于 AI-Box 和 Gateway 之间的业务认证
- 必须在 AI-Box 服务器和 Gateway Worker 中设置**相同的值**

**完成标志**: ✅ Secret 设置成功，并在 AI-Box 服务器上配置相同的值

---

#### 4.2 配置 WAF 规则（Cloudflare Pro+ 账户，可选）

**操作位置**: Cloudflare Dashboard → 你的域名 → Security → WAF

**操作步骤**:

1. 登录 Cloudflare Dashboard
2. 选择你的域名
3. 进入 "Security" → "WAF"
4. 点击 "Create rule"
5. 配置规则：
   - **Rule name**: `MCP Gateway Protection`
   - **Expression**: `(http.request.uri.path contains "/mcp")`
   - **Action**: `Challenge` 或 `Block`（根据需求）
6. 点击 "Deploy"

**注意事项**:

- 此功能需要 Cloudflare Pro 或更高版本账户
- 免费账户无法使用自定义 WAF 规则

**完成标志**: ✅ WAF 规则创建并部署成功

---

#### 4.3 配置速率限制（Cloudflare Pro+ 账户，可选）

**操作位置**: Cloudflare Dashboard → 你的域名 → Security → Rate Limiting

**操作步骤**:

1. 登录 Cloudflare Dashboard
2. 选择你的域名
3. 进入 "Security" → "Rate Limiting"
4. 点击 "Create rule"
5. 配置规则：
   - **Rule name**: `MCP Gateway Rate Limit`
   - **Match**: `http.request.uri.path eq "/mcp"`
   - **Requests**: `100`
   - **Period**: `1 minute`
   - **Action**: `Block`
6. 点击 "Create"

**注意事项**:

- 此功能需要 Cloudflare Pro 或更高版本账户
- 免费账户无法使用速率限制功能

**完成标志**: ✅ 速率限制规则创建成功

---

### 📊 阶段 5: 监控和日志配置（可选，但推荐）

#### 5.1 启用 Cloudflare Logpush（可选）

**操作位置**: Cloudflare Dashboard → Analytics & Logs → Logpush

**操作步骤**:

1. 登录 Cloudflare Dashboard
2. 进入 "Analytics & Logs" → "Logpush"
3. 点击 "Create a job"
4. 选择日志类型：`HTTP Requests`
5. 选择目标服务（S3、GCS、Datadog 等）
6. 配置目标服务连接信息
7. 点击 "Create job"

**注意事项**:

- Logpush 需要付费账户（Pro+）
- 免费账户无法使用 Logpush

**完成标志**: ✅ Logpush 任务创建成功

---

#### 5.2 查看 Workers Analytics（自动启用，无需配置）

**操作位置**: Cloudflare Dashboard → Workers & Pages → 你的 Worker → Analytics

**操作说明**:

- Workers Analytics 自动启用，无需手动配置
- 可以查看以下指标：
  - 请求数
  - 错误数
  - CPU 时间
  - 响应时间

**完成标志**: ✅ 可以正常查看 Analytics 数据

---

### 🚀 阶段 6: 部署和验证（部分手动）

#### 6.1 部署 Worker（可以通过命令行，但需要手动执行）

**操作位置**: 本地终端（在 Gateway 项目目录）

**操作步骤**:

```bash
# 进入 Gateway 目录
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 部署到生产环境
wrangler deploy

# 或部署到预览环境
wrangler deploy --env preview
```

**完成标志**: ✅ 部署成功，显示 Worker URL

---

#### 6.2 配置 Worker 路由（如果使用自定义域名）

**操作位置**: Cloudflare Dashboard → Workers & Pages → 你的 Worker → Settings → Triggers

**操作步骤**:

1. 登录 Cloudflare Dashboard
2. 进入 "Workers & Pages"
3. 选择你的 Worker（`mcp-gateway`）
4. 进入 "Settings" → "Triggers"
5. 在 "Routes" 部分，点击 "Add route"
6. 配置路由：
   - **Route**: `mcp-gateway.your-domain.com/*`
   - **Zone**: 选择你的域名
7. 点击 "Add route"

**完成标志**: ✅ 路由配置成功，可以通过自定义域名访问

---

### 🔧 阶段 7: 配置外部 MCP 认证信息（必须手动）

#### 7.1 导入认证配置到 KV（必须手动执行命令）

**操作位置**: 本地终端（在 Gateway 项目目录）

**操作步骤**:

```bash
# 进入 Gateway 目录
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 存储 Office MCP 认证配置
wrangler kv:key put "auth:office_word" \
  '{"type":"api_key","api_key":"${OFFICE_API_KEY}","header_name":"X-API-Key"}' \
  --namespace-id=YOUR_AUTH_STORE_KV_NAMESPACE_ID

# 存储 Finance MCP 认证配置
wrangler kv:key put "auth:yahoo_finance_quote" \
  '{"type":"none"}' \
  --namespace-id=YOUR_AUTH_STORE_KV_NAMESPACE_ID

# 存储 OAuth 2.0 配置（示例：Slack）
wrangler kv:key put "auth:slack_send_message" \
  '{"type":"oauth2","client_id":"${SLACK_CLIENT_ID}","client_secret":"${SLACK_CLIENT_SECRET}","token_url":"https://slack.com/api/oauth.v2.access"}' \
  --namespace-id=YOUR_AUTH_STORE_KV_NAMESPACE_ID

# 存储 Bearer Token 配置（示例：Confluence）
wrangler kv:key put "auth:confluence_create_page" \
  '{"type":"bearer","token":"${CONFLUENCE_API_TOKEN}"}' \
  --namespace-id=YOUR_AUTH_STORE_KV_NAMESPACE_ID
```

**重要说明**:

- 需要替换 `YOUR_AUTH_STORE_KV_NAMESPACE_ID` 为实际的 KV 命名空间 ID
- 环境变量（如 `${OFFICE_API_KEY}`）需要在 Worker 的 Secrets 中设置
- 每个外部 MCP 工具都需要配置对应的认证信息

**完成标志**: ✅ 所有外部 MCP 工具的认证配置已导入 KV

---

#### 7.2 设置外部 MCP API Keys（Worker Secrets）

**操作位置**: 本地终端（在 Gateway 项目目录）

**操作步骤**:

```bash
# 进入 Gateway 目录
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 设置 Office API Key
wrangler secret put OFFICE_API_KEY
# 提示时输入实际的 API Key 值

# 设置 Slack Client ID
wrangler secret put SLACK_CLIENT_ID
# 提示时输入实际的 Client ID

# 设置 Slack Client Secret
wrangler secret put SLACK_CLIENT_SECRET
# 提示时输入实际的 Client Secret

# 设置 Confluence API Token
wrangler secret put CONFLUENCE_API_TOKEN
# 提示时输入实际的 API Token

# 重复以上步骤，为所有需要的外部 MCP 服务设置 Secrets
```

**重要说明**:

- 这些 Secrets 用于在 Gateway 中访问外部 MCP Server
- 不要在代码中硬编码这些值
- 定期轮换这些密钥

**完成标志**: ✅ 所有外部 MCP 服务的 API Keys 已设置

---

### 👥 阶段 8: 配置用户权限（必须手动）

#### 8.1 导入用户权限到 KV（必须手动执行命令）

**操作位置**: 本地终端（在 Gateway 项目目录）

**操作步骤**:

```bash
# 进入 Gateway 目录
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 存储用户权限配置
wrangler kv:key put "permissions:tenant-456:user-123" \
  '{"tools":["finance_*","office_readonly_*","bi_query_*"],"rate_limits":{"default":100,"finance_*":50}}' \
  --namespace-id=YOUR_PERMISSIONS_STORE_KV_NAMESPACE_ID

# 存储管理员权限（示例）
wrangler kv:key put "permissions:tenant-456:admin" \
  '{"tools":["*"],"rate_limits":{"default":1000}}' \
  --namespace-id=YOUR_PERMISSIONS_STORE_KV_NAMESPACE_ID

# 重复以上步骤，为所有用户配置权限
```

**重要说明**:

- 需要替换 `YOUR_PERMISSIONS_STORE_KV_NAMESPACE_ID` 为实际的 KV 命名空间 ID
- 权限配置格式：`permissions:{tenant_id}:{user_id}`
- 支持通配符匹配（如 `finance_*`）

**完成标志**: ✅ 所有用户权限已配置

---

## 📝 操作检查清单

### 部署前检查

- [ ] Cloudflare 账户已创建并登录
- [ ] Wrangler CLI 已安装并登录
- [ ] 所有 KV 命名空间已创建（AUTH_STORE, PERMISSIONS_STORE, RATE_LIMIT_STORE）
- [ ] 所有 KV 命名空间的 ID 已记录
- [ ] R2 存储桶已创建（如需要）
- [ ] Gateway Secret 已生成并设置
- [ ] Gateway Secret 已在 AI-Box 服务器上配置
- [ ] 外部 MCP API Keys 已设置（Worker Secrets）
- [ ] 外部 MCP 认证配置已导入 KV
- [ ] 用户权限已配置
- [ ] 域名已添加（如使用自定义域名）
- [ ] DNS 记录已配置（如使用自定义域名）
- [ ] WAF 规则已配置（如需要，Pro+）
- [ ] 速率限制已配置（如需要，Pro+）

### 部署后验证

- [ ] Worker 已成功部署
- [ ] Worker URL 可以访问
- [ ] 自定义域名路由已配置（如使用）
- [ ] Gateway Secret 认证正常工作
- [ ] 外部 MCP 认证正常工作
- [ ] 用户权限检查正常工作
- [ ] 审计日志正常记录
- [ ] Workers Analytics 可以查看数据

---

## 🔄 定期维护操作（手动）

### 每周任务

- [ ] 审查认证失败日志
- [ ] 检查 Workers Analytics 中的错误率
- [ ] 审查异常访问模式

### 每月任务

- [ ] 审查用户权限配置
- [ ] 更新外部 MCP API Keys（如需要）
- [ ] 检查 KV 存储使用情况

### 每季度任务

- [ ] 轮换 Gateway Secret
- [ ] 轮换外部 MCP API Keys
- [ ] 安全审计

### 每半年任务

- [ ] 全面安全审计
- [ ] 审查和优化 WAF 规则
- [ ] 审查和优化速率限制规则

---

## 📚 相关文档

- [MCP 工具系统规格](./MCP工具.md)
- [Cloudflare MCP Gateway 设置指南](./Cloudflare-MCP-Gateway-设置指南.md)

---

## ⚠️ 重要提醒

1. **Cloudflare 账户 vs 业务认证**
   - Cloudflare 账户只用于部署和管理 Worker
   - Gateway Secret 是独立的业务认证密钥
   - 运行时认证不依赖 Cloudflare 账户

2. **免费账户限制**
   - Workers: 10 万请求/天
   - KV: 读取 1000 次/天，写入 1000 次/天
   - 无法使用 WAF 自定义规则
   - 无法使用速率限制功能
   - 无法使用 Logpush

3. **安全最佳实践**
   - 定期轮换密钥
   - 不要在代码中硬编码敏感信息
   - 使用 Worker Secrets 存储 API Keys
   - 启用审计日志

4. **成本考虑**
   - 免费账户适合开发和测试
   - 生产环境建议使用付费账户（$5/月起）
   - 监控 Workers 使用量，避免超出配额

---

**最后更新日期**: 2025-12-31
**维护人**: Daniel Chung
