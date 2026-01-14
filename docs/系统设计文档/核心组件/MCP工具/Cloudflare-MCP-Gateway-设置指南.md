# Cloudflare MCP Gateway 设置指南

**创建日期**: 2025-12-31
**创建人**: Daniel Chung
**最后修改日期**: 2026-01-14

---

## 📋 概述

本指南详细说明如何在 Cloudflare 上设置 MCP Gateway，作为 AI-Box 与外部 MCP Server 之间的隔离层。

---

## 📊 设置状态追踪

### 当前部署状态

**最后更新**: 2026-01-14

| 项目 | 状态 | 详情 | 备注 |
|------|------|------|------|
| **Cloudflare 账户** | ✅ 已完成 | 账户: Daniels89 (<896445070@qq.com>) | 已登录 wrangler |
| **Wrangler CLI** | ✅ 已完成 | 版本: 4.54.0 | 已安装并登录 |
| **KV 命名空间** | ✅ 已完成 | 3 个生产 + 3 个预览 | 见下方详情 |
| **R2 存储桶** | ⏸️ 待手动 | 需要在 Dashboard 启用 R2 | 见下方说明 |
| **Gateway Secret** | ✅ 已完成 | 已生成并设置 | 见下方详情 |
| **Worker 部署** | ✅ 已完成 | 已部署到生产环境 | 见下方详情 |
| **域名路由** | ✅ 已完成 | mcp.k84.org | 已在 Dashboard 配置路由 |
| **ngrok 配置** | ✅ 已完成 | 已配置并运行 | 见下方详情 |
| **庫管員 Agent** | ✅ 已完成 | 已注册并配置 | 见下方详情 |

### 详细配置信息

#### KV 命名空间

| 命名空间 | 生产环境 ID | 预览环境 ID | 状态 |
|---------|------------|------------|------|
| AUTH_STORE | `5b6e229c21f649269e93db9dcb8a7e16` | `b1295b79c8f64b879d5d7a3fd8c65400` | ✅ 已创建 |
| PERMISSIONS_STORE | `75e2e224e5844e1ea7639094b87d1001` | `89d30fa67fc944e0a5bce820c2b6b4b3` | ✅ 已创建 |
| RATE_LIMIT_STORE | `e5b99f78db7c452aa70a080b662e0530` | `437f52b27010407ab1730f85d89d835a` | ✅ 已创建 |

#### Gateway Secret

- **Secret 值**: `0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e`
- **设置位置**: Cloudflare Worker Secrets
- **AI-Box 配置**: ⚠️ **需要在 AI-Box 的 .env 文件中添加**:

  ```bash
  MCP_GATEWAY_SECRET=0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e
  ```

#### Worker 部署信息

- **Worker 名称**: `mcp-gateway`
- **Workers.dev URL**: `https://mcp-gateway.896445070.workers.dev` ✅ 正常工作
- **自定义域名**: `mcp.k84.org` ✅ 已配置（在 Dashboard 中设置路由）
- **部署状态**: ✅ 已部署
- **当前版本 ID**: `ff825e48-8a80-477d-b6d4-61acd3e79304` (2026-01-14)

#### 实际配置详情

**1. DNS 配置** ✅ 已完成

- **域名**: `k84.org`
- **记录类型**: CNAME
- **名称**: `mcp`
- **目标**: `mcp-gateway.896445070.workers.dev`
- **代理状态**: ✅ 已启用（橙色云朵）

**2. Cloudflare Dashboard 路由配置** ✅ 已完成

**重要**: 除了在 `wrangler.toml` 中配置路由外，还需要在 Cloudflare Dashboard 中手动绑定路由。

**配置步骤**:

1. 登录 Cloudflare Dashboard: <https://dash.cloudflare.com>
2. 选择域名 `k84.org`
3. 进入 **Workers & Pages** → 选择 `mcp-gateway` Worker
4. 点击 **Triggers** 标签
5. 在 **Routes** 部分，添加路由:
   - **Route**: `mcp.k84.org/*`
   - **Zone**: `k84.org`
   - 点击 **Save**

**当前路由状态**: ✅ `mcp.k84.org/*` 已绑定到 `mcp-gateway` Worker

**3. ngrok 配置** ✅ 已完成

**ngrok URL**: `https://182740a0a99a.ngrok-free.app`

**配置步骤**:

1. **注册 ngrok 账号**:
   - 访问: <https://dashboard.ngrok.com/signup>
   - 注册免费账号

2. **获取 Authtoken**:
   - 登录后访问: <https://dashboard.ngrok.com/get-started/your-authtoken>
   - 复制 authtoken

3. **配置 Authtoken**:

   ```bash
   ngrok config add-authtoken YOUR_AUTHTOKEN
   ```

4. **启动 ngrok**:

   ```bash
   ngrok http 8003
   ```

5. **更新 Gateway 配置**:
   - 复制 ngrok 提供的 URL（例如: `https://182740a0a99a.ngrok-free.app`）
   - 更新 `wrangler.toml` 中的 `MCP_ROUTES` 配置

**注意**:

- ngrok 免费版每次重启会生成新的 URL，需要更新 Gateway 配置
- 建议使用 ngrok 付费版获得固定域名（生产环境）

**4. 庫管員 Agent 配置** ✅ 已完成

**Agent 服务信息**:

- **本地服务**: `http://localhost:8003`
- **MCP 端点**: `http://localhost:8003/mcp` 和 `http://localhost:8003/`
- **工具名称**: `warehouse_execute_task`
- **路由模式**: `warehouse_*`

**Gateway 路由配置** (`wrangler.toml`):

```toml
MCP_ROUTES = '''
[
  {
    "pattern": "yahoo_finance_*",
    "target": "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp"
  },
  {
    "pattern": "warehouse_*",
    "target": "https://182740a0a99a.ngrok-free.app"
  }
]
'''
```

**认证配置** (KV Store):

```bash
# 配置工具认证（无认证）
wrangler kv key put "auth:warehouse_execute_task" \
  '{"type":"none"}' \
  --binding=AUTH_STORE --preview=false --remote
```

**权限配置** (KV Store):

```bash
# 配置租户默认权限
wrangler kv key put "permissions:test-tenant:default" \
  '{"tools":["warehouse_*"]}' \
  --binding=PERMISSIONS_STORE --preview=false --remote
```

**5. 待完成操作** (可选)

1. **启用 R2** (可选，用于审计日志)
   - 在 Cloudflare Dashboard → R2 中启用 R2
   - 然后创建存储桶: `mcp-gateway-audit-logs`
   - 更新 `wrangler.toml` 取消注释 R2 配置

2. **配置其他外部 MCP 认证** (按需)
   - 使用 `wrangler kv key put` 命令导入认证配置
   - 设置外部 MCP API Keys (Worker Secrets)

3. **配置其他用户权限** (按需)
   - 使用 `wrangler kv key put` 命令导入用户权限配置

### 配置检查清单

- [x] Cloudflare 账户已创建并登录
- [x] Wrangler CLI 已安装并登录
- [x] 所有 KV 命名空间已创建
- [x] Gateway Secret 已生成并设置
- [ ] Gateway Secret 已在 AI-Box 服务器上配置
- [ ] DNS 记录已配置 (mcp.k84.org)
- [ ] R2 存储桶已创建（如需要）
- [ ] 外部 MCP 认证配置已导入
- [ ] 用户权限已配置
- [x] Worker 已成功部署

---

---

## 🔐 认证机制说明

### Cloudflare 账户 vs 认证机制

**重要澄清**：Cloudflare 账户和认证机制是两个不同的概念：

1. **Cloudflare 账户**（用于部署和管理）
   - 用途：登录 Cloudflare Dashboard，部署和管理 Workers
   - 方式：通过 `wrangler login` 进行 OAuth 认证
   - 作用：管理 Cloudflare 资源（Workers、KV、域名等）
   - 不用于：AI-Box 和 Gateway 之间的业务认证

2. **Gateway Secret 认证**（用于业务层认证）
   - 用途：验证 AI-Box 发送的请求是否来自合法来源
   - 方式：自定义密钥（Gateway Secret）
   - 作用：保护 Gateway 不被未授权访问
   - 独立于：Cloudflare 账户认证

3. **外部 MCP Server 认证**（用于第三方服务认证）
   - 用途：Gateway 调用外部 MCP Server 时的认证
   - 方式：API Key、OAuth 2.0、Bearer Token 等
   - 作用：访问外部服务
   - 独立于：Cloudflare 账户和 Gateway Secret

### 认证流程总结

```
┌─────────────────────────────────────────────────────────┐
│ 1. Cloudflare 账户认证（部署时）                          │
│    - wrangler login                                     │
│    - 用于部署和管理 Worker                               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Gateway Secret 认证（运行时）                         │
│    - AI-Box → Gateway: X-Gateway-Secret 头              │
│    - 验证请求来源的合法性                                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. 外部 MCP Server 认证（运行时）                         │
│    - Gateway → 外部 MCP: API Key / OAuth Token          │
│    - 访问第三方服务                                      │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 前置要求

1. **Cloudflare 账户**（仅用于部署）
   - 免费账户即可使用 Workers（10 万请求/天）
   - 付费账户（$5/月起）提供更多功能和配额
   - **注意**：Cloudflare 账户只用于部署 Worker，不用于业务认证

2. **Node.js 环境**
   - Node.js 18+
   - npm 或 pnpm

3. **Wrangler CLI**
   - Cloudflare Workers 命令行工具

---

## 📦 步骤 1: 安装和初始化

### 1.1 安装 Wrangler CLI

```bash
# 使用 npm
npm install -g wrangler

# 或使用 pnpm
pnpm add -g wrangler

# 验证安装
wrangler --version
```

### 1.2 登录 Cloudflare

```bash
# 登录 Cloudflare（会打开浏览器进行认证）
wrangler login
```

### 1.3 创建 Worker 项目

```bash
# 在 AI-Box 项目下创建 Gateway 目录
cd /Users/daniel/GitHub/AI-Box
mkdir -p mcp/gateway
cd mcp/gateway

# 初始化 Worker 项目
wrangler init mcp-gateway

# 选择配置：
# - Would you like to use TypeScript? Yes
# - Would you like to create a Worker at src/index.ts? Yes
# - Would you like to use git for version control? Yes
```

---

## 💻 步骤 2: 实现 Gateway Worker

### 2.1 项目结构

```
AI-Box/
└── mcp/
    └── gateway/
        ├── src/
        │   ├── index.ts          # Worker 主入口
        │   ├── gateway.ts        # Gateway 核心逻辑
        │   ├── router.ts         # 路由引擎
        │   ├── auth.ts           # 认证授权
        │   ├── filter.ts         # 请求过滤
        │   └── audit.ts          # 审计日志
        ├── wrangler.toml         # Worker 配置
        ├── package.json
        └── tsconfig.json
```

### 2.2 核心实现代码

#### src/index.ts

```typescript
/**
 * Cloudflare MCP Gateway Worker
 * 作为 AI-Box 与外部 MCP Server 之间的隔离层
 */

import { MCPGateway } from './gateway';

export interface Env {
  // MCP Server 路由配置
  MCP_ROUTES: string;  // JSON 格式的路由配置

  // 认证配置（KV 存储）
  AUTH_STORE: KVNamespace;

  // 审计日志（Durable Object 或 R2）
  AUDIT_LOG: DurableObjectNamespace;

  // 环境变量
  GATEWAY_SECRET: string;  // Gateway 密钥（用于验证请求来源）

  // 可选：外部日志服务
  LOG_ENDPOINT?: string;
  LOG_API_KEY?: string;
}

export default {
  async fetch(
    request: Request,
    env: Env,
    ctx: ExecutionContext
  ): Promise<Response> {
    try {
      const gateway = new MCPGateway(env);
      return await gateway.handle(request);
    } catch (error) {
      console.error('Gateway error:', error);
      return new Response(
        JSON.stringify({
          error: {
            code: -32603,
            message: 'Internal error',
            data: { error: String(error) }
          }
        }),
        {
          status: 500,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }
  }
};
```

#### src/gateway.ts

```typescript
/**
 * MCP Gateway 核心实现
 */

import { Router } from './router';
import { AuthManager } from './auth';
import { RequestFilter } from './filter';
import { AuditLogger } from './audit';

export class MCPGateway {
  private router: Router;
  private authManager: AuthManager;
  private requestFilter: RequestFilter;
  private auditLogger: AuditLogger;

  constructor(private env: any) {
    this.router = new Router(env);
    this.authManager = new AuthManager(env);
    this.requestFilter = new RequestFilter(env);
    this.auditLogger = new AuditLogger(env);
  }

  async handle(request: Request): Promise<Response> {
    const startTime = Date.now();
    const requestId = crypto.randomUUID();

    try {
      // 1. 解析请求
      const body = await request.json();
      const mcpRequest = body;

      // 2. 验证请求来源（可选，如果配置了 GATEWAY_SECRET）
      if (this.env.GATEWAY_SECRET) {
        const authHeader = request.headers.get('X-Gateway-Secret');
        if (authHeader !== this.env.GATEWAY_SECRET) {
          return this.errorResponse(mcpRequest.id, -32001, 'Unauthorized');
        }
      }

      // 3. 路由到目标 MCP Server
      const targetEndpoint = await this.router.route(mcpRequest);
      if (!targetEndpoint) {
        return this.errorResponse(mcpRequest.id, -32601, 'Method not found');
      }

      // 4. 认证授权
      const authResult = await this.authManager.authenticate(
        request,
        targetEndpoint
      );
      if (!authResult.authorized) {
        return this.errorResponse(mcpRequest.id, -32001, 'Unauthorized');
      }

      // 5. 请求过滤（移除敏感信息）
      const filteredRequest = await this.requestFilter.filter(
        request,
        mcpRequest
      );

      // 6. 转发请求到外部 MCP Server
      const response = await this.forwardRequest(
        targetEndpoint,
        filteredRequest,
        authResult.headers
      );

      // 7. 响应过滤
      const filteredResponse = await this.requestFilter.filterResponse(
        response
      );

      // 8. 审计日志（异步，不阻塞响应）
      ctx.waitUntil(
        this.auditLogger.log({
          requestId,
          timestamp: new Date().toISOString(),
          method: mcpRequest.method,
          toolName: mcpRequest.params?.name,
          targetEndpoint,
          request: filteredRequest,
          response: filteredResponse,
          latency: Date.now() - startTime,
        })
      );

      return new Response(JSON.stringify(filteredResponse), {
        headers: { 'Content-Type': 'application/json' }
      });

    } catch (error) {
      // 记录错误
      ctx.waitUntil(
        this.auditLogger.logError({
          requestId,
          error: String(error),
          timestamp: new Date().toISOString(),
        })
      );

      return this.errorResponse(
        body?.id,
        -32603,
        'Internal error',
        { error: String(error) }
      );
    }
  }

  private async forwardRequest(
    endpoint: string,
    request: any,
    authHeaders: Record<string, string>
  ): Promise<any> {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
        // 移除追踪信息
        'X-Forwarded-For': 'Cloudflare-IP',
        'X-Request-Source': 'AI-Box-Gateway',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  }

  private errorResponse(
    id: any,
    code: number,
    message: string,
    data?: any
  ): Response {
    return new Response(
      JSON.stringify({
        jsonrpc: '2.0',
        id,
        error: { code, message, data }
      }),
      {
        status: 200,  // JSON-RPC 错误仍返回 200
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}
```

#### src/router.ts

```typescript
/**
 * 路由引擎
 */

export class Router {
  private routes: Map<string, string> = new Map();

  constructor(private env: any) {
    this.loadRoutes();
  }

  private loadRoutes() {
    // 从环境变量加载路由配置
    if (this.env.MCP_ROUTES) {
      const routesConfig = JSON.parse(this.env.MCP_ROUTES);
      for (const route of routesConfig) {
        this.routes.set(route.pattern, route.target);
      }
    }
  }

  async route(mcpRequest: any): Promise<string | null> {
    // 从请求中提取工具名称
    const toolName = mcpRequest.params?.name;
    if (!toolName) {
      return null;
    }

    // 匹配路由规则
    for (const [pattern, target] of this.routes.entries()) {
      if (this.matchPattern(pattern, toolName)) {
        return target;
      }
    }

    // 默认路由（如果配置了）
    return this.env.DEFAULT_MCP_ENDPOINT || null;
  }

  private matchPattern(pattern: string, toolName: string): boolean {
    // 支持通配符匹配
    const regex = new RegExp('^' + pattern.replace(/\*/g, '.*') + '$');
    return regex.test(toolName);
  }
}
```

#### src/auth.ts

```typescript
/**
 * 认证授权管理器
 */

export class AuthManager {
  constructor(private env: any) {}

  async authenticate(
    request: Request,
    targetEndpoint: string
  ): Promise<{ authorized: boolean; headers: Record<string, string> }> {
    // 1. 从请求头获取工具名称
    const toolName = request.headers.get('X-Tool-Name');
    if (!toolName) {
      return { authorized: false, headers: {} };
    }

    // 2. 从 KV 存储获取认证配置
    const authConfig = await this.env.AUTH_STORE.get(
      `auth:${toolName}`,
      'json'
    );

    if (!authConfig) {
      return { authorized: false, headers: {} };
    }

    // 3. 根据认证类型构建请求头
    const headers: Record<string, string> = {};

    if (authConfig.type === 'api_key') {
      const apiKey = this.resolveEnvVar(authConfig.api_key);
      const headerName = authConfig.header_name || 'Authorization';
      headers[headerName] = authConfig.header_name === 'Authorization'
        ? `Bearer ${apiKey}`
        : apiKey;
    } else if (authConfig.type === 'bearer') {
      const token = this.resolveEnvVar(authConfig.token);
      headers['Authorization'] = `Bearer ${token}`;
    } else if (authConfig.type === 'oauth2') {
      // OAuth 2.0 需要获取 access token
      const token = await this.getOAuthToken(authConfig);
      headers['Authorization'] = `Bearer ${token}`;
    }

    return { authorized: true, headers };
  }

  private resolveEnvVar(value: string): string {
    if (value.startsWith('${') && value.endsWith('}')) {
      const envVar = value.slice(2, -1);
      // 在 Cloudflare Workers 中，环境变量通过 env 对象访问
      return this.env[envVar] || value;
    }
    return value;
  }

  private async getOAuthToken(config: any): Promise<string> {
    // 实现 OAuth 2.0 Token 获取逻辑
    // 可以使用 Durable Objects 缓存 token
    // ...
    return '';
  }
}
```

#### src/filter.ts

```typescript
/**
 * 请求/响应过滤器
 */

export class RequestFilter {
  constructor(private env: any) {}

  async filter(request: Request, mcpRequest: any): Promise<any> {
    // 1. 移除敏感信息
    const filtered = { ...mcpRequest };

    // 2. 数据脱敏（如果需要）
    if (this.env.ENABLE_DATA_MASKING) {
      filtered.params = this.maskSensitiveData(filtered.params);
    }

    return filtered;
  }

  async filterResponse(response: any): Promise<any> {
    // 响应过滤逻辑
    return response;
  }

  private maskSensitiveData(data: any): any {
    // 实现数据脱敏逻辑
    // 例如：移除 PII、敏感字段等
    return data;
  }
}
```

#### src/audit.ts

```typescript
/**
 * 审计日志记录器
 */

export class AuditLogger {
  constructor(private env: any) {}

  async log(auditData: any): Promise<void> {
    try {
      // 1. 记录到 Cloudflare Logpush（如果配置）
      if (this.env.LOG_ENDPOINT) {
        await fetch(this.env.LOG_ENDPOINT, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.env.LOG_API_KEY}`,
          },
          body: JSON.stringify(auditData),
        });
      }

      // 2. 记录到 Durable Object（如果配置）
      if (this.env.AUDIT_LOG) {
        const id = this.env.AUDIT_LOG.idFromName('audit-log');
        const stub = this.env.AUDIT_LOG.get(id);
        await stub.fetch('http://internal/log', {
          method: 'POST',
          body: JSON.stringify(auditData),
        });
      }

      // 3. 记录到控制台（开发环境）
      console.log('Audit log:', JSON.stringify(auditData));
    } catch (error) {
      console.error('Failed to log audit:', error);
    }
  }

  async logError(errorData: any): Promise<void> {
    await this.log({
      ...errorData,
      type: 'error',
    });
  }
}
```

---

## 📝 实际配置详情（2026-01-14 更新）

本章节记录所有实际部署的配置信息，包括 Cloudflare、ngrok、mcp_gateway 等所有相关设置。

### 1. Cloudflare Worker 配置

#### 1.1 wrangler.toml 完整配置

**文件位置**: `/Users/daniel/GitHub/AI-Box/mcp/gateway/wrangler.toml`

```toml
name = "mcp-gateway"
main = "src/index.ts"
compatibility_date = "2024-12-31"

# 环境变量
[vars]
DEFAULT_MCP_ENDPOINT = ""
ENABLE_DATA_MASKING = "true"
ENABLE_RESPONSE_FILTERING = "false"
DEFAULT_RATE_LIMIT = "100"

# MCP 路由配置
MCP_ROUTES = '''
[
  {
    "pattern": "yahoo_finance_*",
    "target": "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp"
  },
  {
    "pattern": "warehouse_*",
    "target": "https://182740a0a99a.ngrok-free.app"
  }
]
'''

# KV 存储
[[kv_namespaces]]
binding = "AUTH_STORE"
id = "5b6e229c21f649269e93db9dcb8a7e16"
preview_id = "b1295b79c8f64b879d5d7a3fd8c65400"

[[kv_namespaces]]
binding = "PERMISSIONS_STORE"
id = "75e2e224e5844e1ea7639094b87d1001"
preview_id = "89d30fa67fc944e0a5bce820c2b6b4b3"

[[kv_namespaces]]
binding = "RATE_LIMIT_STORE"
id = "e5b99f78db7c452aa70a080b662e0530"
preview_id = "437f52b27010407ab1730f85d89d835a"

# 路由配置（自定义域名）
routes = [
  { pattern = "mcp.k84.org/*", zone_name = "k84.org" }
]
```

#### 1.2 Gateway Secret 配置

**Secret 值**: `0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e`

**设置方式**:

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
wrangler secret put GATEWAY_SECRET
# 输入: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e
```

**AI-Box 环境变量** (`.env`):

```bash
MCP_GATEWAY_SECRET=0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e
```

#### 1.3 部署信息

**部署命令**:

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
wrangler deploy
```

**当前部署状态**:

- ✅ **Workers.dev URL**: `https://mcp-gateway.896445070.workers.dev` (正常工作)
- ✅ **自定义域名**: `https://mcp.k84.org` (已配置路由)
- ✅ **版本 ID**: `ff825e48-8a80-477d-b6d4-61acd3e79304` (2026-01-14)

### 2. DNS 和路由配置

#### 2.1 DNS 记录配置

**Cloudflare Dashboard → DNS → Records**:

| 类型 | 名称 | 目标 | 代理状态 |
|------|------|------|----------|
| CNAME | `mcp` | `mcp-gateway.896445070.workers.dev` | ✅ 已启用（橙色云朵） |

#### 2.2 Worker 路由配置（重要）

**⚠️ 重要**: 除了在 `wrangler.toml` 中配置路由外，**必须在 Cloudflare Dashboard 中手动绑定路由**。

**配置步骤**:

1. **登录 Cloudflare Dashboard**
   - 访问: <https://dash.cloudflare.com>
   - 选择域名: `k84.org`

2. **进入 Workers & Pages**
   - 左侧菜单 → **Workers & Pages**
   - 选择 Worker: `mcp-gateway`

3. **配置 Triggers**
   - 点击 **Triggers** 标签
   - 在 **Routes** 部分，检查是否有 `mcp.k84.org/*` 路由

4. **添加路由**（如果不存在）
   - 点击 **Add route**
   - **Route**: `mcp.k84.org/*`
   - **Zone**: `k84.org`
   - 点击 **Save**

**当前路由状态**: ✅ `mcp.k84.org/*` 已绑定到 `mcp-gateway` Worker

**验证路由**:

```bash
# 测试自定义域名
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -H "X-Tool-Name: warehouse_execute_task" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### 3. ngrok 配置

#### 3.1 ngrok 基本信息

**当前 ngrok URL**: `https://182740a0a99a.ngrok-free.app`

**ngrok Authtoken**: `2ezS4bIh0BK7iIRd2l5jxSYmUkk_3hecAfh6scnJrGVQ7Urco`

#### 3.2 ngrok 配置步骤

**1. 注册 ngrok 账号**:

- 访问: <https://dashboard.ngrok.com/signup>
- 注册免费账号（使用 GitHub、Google 或 Email）

**2. 获取 Authtoken**:

- 登录后访问: <https://dashboard.ngrok.com/get-started/your-authtoken>
- 复制 authtoken

**3. 配置 Authtoken**:

```bash
ngrok config add-authtoken 2ezS4bIh0BK7iIRd2l5jxSYmUkk_3hecAfh6scnJrGVQ7Urco
```

**4. 启动 ngrok**:

```bash
# 暴露本地 8003 端口（庫管員 Agent）
ngrok http 8003
```

**5. 更新 Gateway 配置**:

- 复制 ngrok 提供的 URL（例如: `https://182740a0a99a.ngrok-free.app`）
- 更新 `wrangler.toml` 中的 `MCP_ROUTES` 配置:

  ```toml
  {
    "pattern": "warehouse_*",
    "target": "https://182740a0a99a.ngrok-free.app"
  }
  ```

- 重新部署: `wrangler deploy`

#### 3.3 ngrok 注意事项

**免费版限制**:

- ⚠️ 每次重启 ngrok 会生成新的 URL，需要更新 Gateway 配置
- ⚠️ 免费版可能有连接限制
- ⚠️ 建议生产环境使用 ngrok 付费版获得固定域名

**后台运行**:

```bash
# 使用 nohup 后台运行
nohup ngrok http 8003 > ngrok.log 2>&1 &
```

**查看 ngrok Web UI**:

- 访问: `http://localhost:4040`
- 可以查看请求日志和统计信息

### 4. 庫管員 Agent 配置

#### 4.1 Agent 服务信息

**本地服务**:

- **端口**: `8003`
- **本地 URL**: `http://localhost:8003`
- **MCP 端点**:
  - `http://localhost:8003/mcp`
  - `http://localhost:8003/` (根路径，用于 Tunnel/ngrok)

**工具信息**:

- **工具名称**: `warehouse_execute_task`
- **路由模式**: `warehouse_*`
- **描述**: 执行库存管理任务（查询料号、查询库存、缺料分析、生成采购单等）

#### 4.2 Gateway 路由配置

**wrangler.toml**:

```toml
MCP_ROUTES = '''
[
  {
    "pattern": "warehouse_*",
    "target": "https://182740a0a99a.ngrok-free.app"
  }
]
'''
```

#### 4.3 Gateway 认证配置

**配置工具认证** (无认证):

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 配置工具认证（无认证）
wrangler kv key put "auth:warehouse_execute_task" \
  '{"type":"none"}' \
  --binding=AUTH_STORE --preview=false --remote
```

**配置权限**:

```bash
# 配置租户默认权限（允许 warehouse_* 工具）
wrangler kv key put "permissions:test-tenant:default" \
  '{"tools":["warehouse_*"]}' \
  --binding=PERMISSIONS_STORE --preview=false --remote
```

#### 4.4 测试配置

**测试本地服务**:

```bash
# 健康检查
curl http://localhost:8003/health

# MCP 端点测试
curl -X POST http://localhost:8003/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

**测试 ngrok**:

```bash
curl -X POST https://182740a0a99a.ngrok-free.app/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

**测试 Gateway (workers.dev)**:

```bash
curl -X POST https://mcp-gateway.896445070.workers.dev \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -H "X-Tool-Name: warehouse_execute_task" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

**测试 Gateway (自定义域名)**:

```bash
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -H "X-Tool-Name: warehouse_execute_task" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### 5. 完整配置检查清单

#### 5.1 Cloudflare 配置

- [x] Cloudflare 账户已创建并登录
- [x] Wrangler CLI 已安装并登录
- [x] 所有 KV 命名空间已创建
- [x] Gateway Secret 已生成并设置
- [x] Worker 已成功部署
- [x] DNS 记录已配置 (mcp.k84.org)
- [x] Worker 路由已在 Dashboard 中绑定

#### 5.2 ngrok 配置

- [x] ngrok 账号已注册
- [x] Authtoken 已配置
- [x] ngrok 已启动并运行
- [x] Gateway 路由已更新为 ngrok URL

#### 5.3 庫管員 Agent 配置

- [x] Agent 服务已启动 (localhost:8003)
- [x] MCP 端点已配置 (`/mcp` 和 `/`)
- [x] 工具已注册 (`warehouse_execute_task`)
- [x] Gateway 路由已配置 (`warehouse_*`)
- [x] Gateway 认证已配置 (无认证)
- [x] Gateway 权限已配置 (允许 `warehouse_*`)

#### 5.4 测试验证

- [x] 本地服务测试通过
- [x] ngrok 直接访问测试通过
- [x] Gateway (workers.dev) 测试通过
- [x] Gateway (自定义域名) 测试通过

### 6. 当前可用端点

| 端点 | URL | 状态 | 说明 |
|------|-----|------|------|
| **本地服务** | `http://localhost:8003` | ✅ | 本地开发 |
| **ngrok** | `https://182740a0a99a.ngrok-free.app` | ✅ | 内网穿透 |
| **Gateway (workers.dev)** | `https://mcp-gateway.896445070.workers.dev` | ✅ | 生产环境 |
| **Gateway (自定义域名)** | `https://mcp.k84.org` | ✅ | 生产环境（推荐） |

### 7. 配置更新流程

#### 7.1 更新 ngrok URL

如果 ngrok 重启并生成新 URL:

1. **获取新 URL**:

   ```bash
   # 查看 ngrok Web UI
   open http://localhost:4040
   # 或查看 ngrok 终端输出
   ```

2. **更新 wrangler.toml**:

   ```toml
   {
     "pattern": "warehouse_*",
     "target": "https://NEW_NGROK_URL.ngrok-free.app"
   }
   ```

3. **重新部署**:

   ```bash
   cd /Users/daniel/GitHub/AI-Box/mcp/gateway
   wrangler deploy
   ```

#### 7.2 添加新的 MCP 工具

1. **更新 wrangler.toml**:

   ```toml
   {
     "pattern": "new_tool_*",
     "target": "https://new-mcp-server.example.com/mcp"
   }
   ```

2. **配置认证** (如果需要):

   ```bash
   wrangler kv key put "auth:new_tool_name" \
     '{"type":"api_key","api_key":"YOUR_API_KEY"}' \
     --binding=AUTH_STORE --preview=false --remote
   ```

3. **配置权限**:

   ```bash
   wrangler kv key put "permissions:tenant-id:default" \
     '{"tools":["new_tool_*"]}' \
     --binding=PERMISSIONS_STORE --preview=false --remote
   ```

4. **重新部署**:

   ```bash
   wrangler deploy
   ```

---

## ⚙️ 步骤 3: 配置 Worker

### 3.1 wrangler.toml 配置

```toml
name = "mcp-gateway"
main = "src/index.ts"
compatibility_date = "2024-12-31"

# 环境变量
[vars]
GATEWAY_SECRET = "your-gateway-secret-key"
DEFAULT_MCP_ENDPOINT = "https://default-mcp.example.com/mcp"
ENABLE_DATA_MASKING = "true"

# MCP 路由配置（JSON 格式）
MCP_ROUTES = '''
[
  {
    "pattern": "office_*",
    "target": "https://office-mcp.example.com/mcp"
  },
  {
    "pattern": "finance_*",
    "target": "https://finance-mcp.example.com/mcp"
  },
  {
    "pattern": "bi_*",
    "target": "https://bi-mcp.example.com/mcp"
  }
]
'''

# KV 存储（用于认证配置）
[[kv_namespaces]]
binding = "AUTH_STORE"
id = "your-kv-namespace-id"
preview_id = "your-preview-kv-namespace-id"

# Durable Objects（用于审计日志，可选）
[[durable_objects.bindings]]
name = "AUDIT_LOG"
class_name = "AuditLogDO"
script_name = "mcp-gateway"

# R2 存储（用于日志存储，可选）
[[r2_buckets]]
binding = "AUDIT_BUCKET"
bucket_name = "mcp-gateway-audit-logs"
preview_bucket_name = "mcp-gateway-audit-logs-preview"

# 路由配置（自定义域名）
routes = [
  { pattern = "mcp-gateway.your-domain.com/*", zone_name = "your-domain.com" }
]

# 限制配置
[limits]
cpu_ms = 50  # CPU 时间限制（毫秒）
```

### 3.2 创建 KV 存储

```bash
# 进入 Gateway 目录
cd mcp/gateway

# 创建 KV 命名空间
wrangler kv:namespace create "AUTH_STORE"

# 创建预览环境 KV 命名空间
wrangler kv:namespace create "AUTH_STORE" --preview

# 将返回的 ID 添加到 wrangler.toml
```

### 3.3 配置认证信息

```bash
# 进入 Gateway 目录
cd mcp/gateway

# 存储 Office MCP 认证配置
wrangler kv:key put "auth:office_word" \
  '{"type":"api_key","api_key":"${OFFICE_API_KEY}","header_name":"X-API-Key"}' \
  --namespace-id=YOUR_KV_NAMESPACE_ID

# 存储 Finance MCP 认证配置
wrangler kv:key put "auth:yahoo_finance_quote" \
  '{"type":"none"}' \
  --namespace-id=YOUR_KV_NAMESPACE_ID
```

---

## 🌐 步骤 4: 配置域名和路由

### 4.1 自定义域名（可选）

1. **在 Cloudflare Dashboard 中添加域名**
   - 登录 Cloudflare Dashboard
   - 添加你的域名（如果还没有）
   - 配置 DNS 记录

2. **配置 Worker 路由**
   - 进入 Workers & Pages
   - 选择你的 Worker
   - 添加自定义路由：`mcp-gateway.your-domain.com/*`

### 4.2 使用 workers.dev 子域名（默认）

Worker 会自动获得一个 `your-worker.your-subdomain.workers.dev` 的 URL，可以直接使用。

---

## 🔒 步骤 5: 安全配置

### 5.1 设置 Gateway Secret

**重要**：Gateway Secret 是**自定义密钥**，与 Cloudflare 账户无关。它用于 AI-Box 和 Gateway 之间的业务认证。

```bash
# 生成随机密钥（32 字节，64 个十六进制字符）
openssl rand -hex 32

# 进入 Gateway 目录
cd mcp/gateway

# 添加到 Cloudflare Worker 环境变量（使用 wrangler，需要 Cloudflare 账户登录）
# 注意：wrangler 需要 Cloudflare 账户来部署，但 Gateway Secret 本身是独立的
wrangler secret put GATEWAY_SECRET
# 输入密钥值（刚才生成的密钥）

# 同时在 AI-Box 服务器上设置相同的密钥
export MCP_GATEWAY_SECRET="your-generated-secret"
# 或添加到 .env 文件
echo "MCP_GATEWAY_SECRET=your-generated-secret" >> .env
```

**认证流程**：

1. **部署阶段**：使用 Cloudflare 账户登录（`wrangler login`），用于部署 Worker
2. **运行时**：AI-Box 使用 Gateway Secret 认证，与 Cloudflare 账户无关

### 5.2 配置 WAF 规则（Cloudflare Pro+）

1. 进入 Cloudflare Dashboard
2. 选择你的域名
3. 进入 Security → WAF
4. 创建自定义规则：
   - 规则名称：`MCP Gateway Protection`
   - 表达式：`(http.request.uri.path contains "/mcp")`
   - 操作：`Challenge` 或 `Block`（根据需求）

### 5.3 配置速率限制

1. 进入 Security → Rate Limiting
2. 创建规则：
   - 匹配：`http.request.uri.path eq "/mcp"`
   - 限制：100 请求/分钟
   - 操作：`Block`

---

## 📊 步骤 6: 配置日志和监控

### 6.1 启用 Cloudflare Logpush

1. 进入 Analytics & Logs → Logpush
2. 创建新的 Logpush 任务
3. 选择日志类型：`HTTP Requests`
4. 配置目标（S3、GCS、Datadog 等）

### 6.2 配置 Workers Analytics

Worker 自动记录以下指标：

- 请求数
- 错误数
- CPU 时间
- 响应时间

在 Workers Dashboard 中查看。

### 6.3 集成外部监控（可选）

```typescript
// 在 gateway.ts 中添加
async logToExternalService(data: any) {
  if (this.env.MONITORING_ENDPOINT) {
    await fetch(this.env.MONITORING_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.env.MONITORING_API_KEY}`,
      },
      body: JSON.stringify(data),
    });
  }
}
```

---

## 🧪 步骤 7: 测试和部署

### 7.1 本地测试

```bash
# 进入 Gateway 目录
cd mcp/gateway

# 启动本地开发服务器
wrangler dev

# 测试请求（在另一个终端）
curl -X POST http://localhost:8787/mcp \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: your-gateway-secret" \
  -H "X-User-ID: user-123" \
  -H "X-Tenant-ID: tenant-456" \
  -H "X-Tool-Name: yahoo_finance_quote" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "yahoo_finance_quote",
      "arguments": {"symbol": "AAPL"}
    }
  }'
```

### 7.2 部署到生产环境

```bash
# 进入 Gateway 目录
cd mcp/gateway

# 部署 Worker
wrangler deploy

# 部署到预览环境
wrangler deploy --env preview
```

### 7.3 验证部署

```bash
# 测试生产环境
curl -X POST https://mcp-gateway.your-domain.workers.dev/mcp \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: your-gateway-secret" \
  -H "X-User-ID: user-123" \
  -H "X-Tenant-ID: tenant-456" \
  -H "X-Tool-Name: yahoo_finance_quote" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

---

## 📝 步骤 8: 更新 AI-Box 配置

### 8.1 更新 external_mcp_tools.yaml

```yaml
external_tools:
  - name: "yahoo_finance_quote"
    mcp_endpoint: "https://finance.yahoo.com/mcp"  # 真实端点
    proxy_endpoint: "https://mcp-gateway.your-domain.workers.dev"  # Gateway
    proxy_config:
      enabled: true
      audit_enabled: true
      hide_ip: true
    # ... 其他配置
```

### 8.2 设置环境变量

```bash
# 在 AI-Box 服务器上设置 Gateway Secret
export MCP_GATEWAY_SECRET="your-gateway-secret"
```

---

## 🔧 高级配置

### 缓存配置

```typescript
// 在 gateway.ts 中添加缓存逻辑
async getCachedResponse(cacheKey: string): Promise<Response | null> {
  const cache = caches.default;
  return await cache.match(cacheKey);
}

async setCachedResponse(cacheKey: string, response: Response, ttl: number) {
  const cache = caches.default;
  const cachedResponse = response.clone();
  cachedResponse.headers.set('Cache-Control', `max-age=${ttl}`);
  await cache.put(cacheKey, cachedResponse);
}
```

### 负载均衡

```typescript
// 支持多个后端
const backends = [
  'https://mcp-server-1.example.com/mcp',
  'https://mcp-server-2.example.com/mcp',
];

const backend = backends[Math.floor(Math.random() * backends.length)];
```

### 故障转移

```typescript
async forwardWithFallback(endpoint: string, request: any): Promise<Response> {
  try {
    return await this.forwardRequest(endpoint, request);
  } catch (error) {
    // 尝试备用端点
    const fallback = this.getFallbackEndpoint(endpoint);
    if (fallback) {
      return await this.forwardRequest(fallback, request);
    }
    throw error;
  }
}
```

---

## 📊 监控和告警

### Cloudflare Analytics

在 Workers Dashboard 中查看：

- 请求量
- 错误率
- 响应时间
- CPU 使用率

### 自定义监控

```typescript
// 发送指标到外部监控服务
async sendMetrics(metrics: any) {
  await fetch('https://your-monitoring-service.com/metrics', {
    method: 'POST',
    body: JSON.stringify(metrics),
  });
}
```

---

## 🐛 故障排查

### 常见问题

1. **401 Unauthorized**
   - 检查 `GATEWAY_SECRET` 是否正确
   - 检查请求头 `X-Gateway-Secret` 是否设置

2. **502 Bad Gateway**
   - 检查目标 MCP Server 是否可达
   - 检查认证配置是否正确

3. **超时错误**
   - 增加 Worker CPU 时间限制
   - 检查目标服务器响应时间

### 调试技巧

```typescript
// 启用详细日志
if (this.env.DEBUG_MODE === 'true') {
  console.log('Request:', JSON.stringify(request, null, 2));
  console.log('Response:', JSON.stringify(response, null, 2));
}
```

---

---

## 🔐 产品化认证方案

### 三层认证架构

```
Layer 1: AI-Box → Gateway 认证
  ├─ Gateway Secret 验证
  ├─ JWT Token 认证（可选，更安全）
  └─ IP 白名单（可选）

Layer 2: Gateway 内部认证
  ├─ 用户身份验证
  ├─ 工具权限检查
  └─ 速率限制检查

Layer 3: Gateway → 外部 MCP Server 认证
  ├─ API Key / OAuth 2.0
  ├─ Bearer Token
  └─ 动态 Token 刷新
```

### 启动流程

#### 阶段 1: 初始化配置

**1.1 设置 Gateway Secret**

**说明**：Gateway Secret 是自定义密钥，用于 AI-Box 和 Gateway 之间的认证。它与 Cloudflare 账户认证是独立的。

```bash
# 生成随机密钥（32 字节）
openssl rand -hex 32
# 输出示例：a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2

# 在 AI-Box 服务器上设置（业务认证）
export MCP_GATEWAY_SECRET="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"
# 或添加到 .env 文件

# 在 Cloudflare Worker 中设置（需要先登录 Cloudflare 账户）
cd mcp/gateway
wrangler secret put GATEWAY_SECRET
# 输入相同的密钥值

# 注意：
# - wrangler 命令需要 Cloudflare 账户登录（用于部署）
# - 但 Gateway Secret 本身是独立的业务认证密钥
# - 运行时认证不依赖 Cloudflare 账户
```

**1.2 创建 KV 存储**

```bash
# 创建认证配置存储
wrangler kv:namespace create "AUTH_STORE"
wrangler kv:namespace create "AUTH_STORE" --preview

# 创建权限存储
wrangler kv:namespace create "PERMISSIONS_STORE"
wrangler kv:namespace create "PERMISSIONS_STORE" --preview

# 创建速率限制存储
wrangler kv:namespace create "RATE_LIMIT_STORE"
wrangler kv:namespace create "RATE_LIMIT_STORE" --preview
```

**1.3 配置外部 MCP 认证信息**

```bash
# 存储 Office MCP 认证配置
wrangler kv:key put "auth:office_word" \
  '{"type":"api_key","api_key":"${OFFICE_API_KEY}","header_name":"X-API-Key"}' \
  --namespace-id=YOUR_KV_NAMESPACE_ID

# 存储 Finance MCP 认证配置
wrangler kv:key put "auth:yahoo_finance_quote" \
  '{"type":"none"}' \
  --namespace-id=YOUR_KV_NAMESPACE_ID

# 存储 OAuth 2.0 配置
wrangler kv:key put "auth:slack_send_message" \
  '{"type":"oauth2","client_id":"${SLACK_CLIENT_ID}","client_secret":"${SLACK_CLIENT_SECRET}","token_url":"https://slack.com/api/oauth.v2.access"}' \
  --namespace-id=YOUR_KV_NAMESPACE_ID
```

#### 阶段 2: 配置用户权限

**2.1 创建权限配置**

```json
{
  "user_id": "user-123",
  "tenant_id": "tenant-456",
  "tools": [
    "finance_*",
    "office_readonly_*",
    "bi_query_*"
  ],
  "rate_limits": {
    "default": 100,
    "finance_*": 50
  }
}
```

**2.2 导入权限到 KV**

```bash
# 存储用户权限
wrangler kv:key put "permissions:tenant-456:user-123" \
  '{"tools":["finance_*","office_readonly_*"],"rate_limits":{"default":100}}' \
  --namespace-id=YOUR_PERMISSIONS_KV_NAMESPACE_ID
```

#### 阶段 3: 更新 Gateway Worker 代码

**3.1 增强认证功能**

更新 `src/gateway.ts` 以支持三层认证：

```typescript
// src/gateway.ts

async handle(request: Request): Promise<Response> {
  // Layer 1: 验证 Gateway Secret
  const gatewaySecret = request.headers.get('X-Gateway-Secret');
  if (gatewaySecret !== this.env.GATEWAY_SECRET) {
    return this.errorResponse(null, -32001, 'Unauthorized: Invalid Gateway Secret');
  }

  // 提取用户信息
  const userId = request.headers.get('X-User-ID');
  const tenantId = request.headers.get('X-Tenant-ID');
  const toolName = request.headers.get('X-Tool-Name');

  // Layer 2: 检查用户权限
  const permissionManager = new PermissionManager(this.env);
  const hasPermission = await permissionManager.checkPermission(
    userId,
    tenantId,
    toolName
  );
  if (!hasPermission) {
    return this.errorResponse(null, -32001, 'Unauthorized: No permission');
  }

  // Layer 2: 检查速率限制
  const rateLimiter = new RateLimiter(this.env);
  const rateLimitResult = await rateLimiter.checkRateLimit(userId, toolName);
  if (!rateLimitResult.allowed) {
    return this.errorResponse(null, -32002, 'Rate limit exceeded');
  }

  // Layer 3: 获取外部 MCP 认证信息
  const authResult = await this.authManager.authenticate(toolName);

  // 继续处理请求...
}
```

**3.2 添加权限管理模块**

创建 `src/auth/permissions.ts`：

```typescript
export class PermissionManager {
  async checkPermission(
    userId: string,
    tenantId: string,
    toolName: string
  ): Promise<boolean> {
    const userPermissions = await this.env.PERMISSIONS_STORE.get(
      `permissions:${tenantId}:${userId}`,
      'json'
    );

    if (!userPermissions) {
      return false;
    }

    const toolPatterns = userPermissions.tools || [];
    return toolPatterns.some(pattern => this.matchPattern(pattern, toolName));
  }

  private matchPattern(pattern: string, toolName: string): boolean {
    const regex = new RegExp('^' + pattern.replace(/\*/g, '.*') + '$');
    return regex.test(toolName);
  }
}
```

**3.3 添加速率限制模块**

创建 `src/auth/ratelimit.ts`：

```typescript
export class RateLimiter {
  async checkRateLimit(
    userId: string,
    toolName: string
  ): Promise<{ allowed: boolean; remaining: number }> {
    const key = `ratelimit:${userId}:${toolName}`;
    const count = await this.env.RATE_LIMIT_STORE.get(key, 'number') || 0;
    const limit = await this.getRateLimit(userId, toolName);

    if (count >= limit) {
      return { allowed: false, remaining: 0 };
    }

    await this.env.RATE_LIMIT_STORE.put(key, count + 1, {
      expirationTtl: 60
    });

    return { allowed: true, remaining: limit - count - 1 };
  }

  private async getRateLimit(userId: string, toolName: string): Promise<number> {
    // 从权限配置获取速率限制
    const permissions = await this.env.PERMISSIONS_STORE.get(
      `permissions:${userId}`,
      'json'
    );

    if (permissions?.rate_limits) {
      for (const [pattern, limit] of Object.entries(permissions.rate_limits)) {
        if (this.matchPattern(pattern, toolName)) {
          return limit as number;
        }
      }
    }

    return permissions?.rate_limits?.default || 100;
  }

  private matchPattern(pattern: string, toolName: string): boolean {
    const regex = new RegExp('^' + pattern.replace(/\*/g, '.*') + '$');
    return regex.test(toolName);
  }
}
```

#### 阶段 4: 更新 AI-Box 配置

**4.1 更新 ExternalMCPTool 代码**

确保 `mcp/server/tools/external_tool.py` 中的 `_get_proxy_headers()` 方法包含用户信息：

```python
def _get_proxy_headers(self) -> Dict[str, str]:
    """获取代理相关的请求头"""
    headers: Dict[str, str] = {}

    # 添加 Gateway Secret
    gateway_secret = os.getenv("MCP_GATEWAY_SECRET")
    if gateway_secret:
        headers["X-Gateway-Secret"] = gateway_secret

    # 添加用户信息（从请求上下文获取）
    # 注意：需要从当前请求上下文中获取 user_id 和 tenant_id
    user_id = self._get_current_user_id()  # 需要实现此方法
    if user_id:
        headers["X-User-ID"] = user_id
        headers["X-Tenant-ID"] = self._get_tenant_id(user_id)

    # 添加工具信息
    headers["X-Tool-Name"] = self.name
    headers["X-Real-Endpoint"] = self.mcp_endpoint

    return headers
```

**4.2 设置环境变量**

```bash
# .env 文件
MCP_GATEWAY_SECRET=your-gateway-secret
MCP_GATEWAY_ENDPOINT=https://mcp-gateway.your-domain.workers.dev
```

#### 阶段 5: 部署和验证

**5.1 部署 Gateway**

```bash
cd mcp/gateway
wrangler deploy --env production
```

**5.2 验证认证**

```bash
# 测试认证流程
curl -X POST https://mcp-gateway.your-domain.workers.dev/mcp \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: your-gateway-secret" \
  -H "X-User-ID: user-123" \
  -H "X-Tenant-ID: tenant-456" \
  -H "X-Tool-Name: yahoo_finance_quote" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "yahoo_finance_quote",
      "arguments": {"symbol": "AAPL"}
    }
  }'
```

### 启动检查清单

**部署前检查**:

- [ ] Gateway Secret 已设置并同步
- [ ] KV 命名空间已创建
- [ ] 外部 MCP 认证配置已导入
- [ ] 用户权限已配置
- [ ] 速率限制已设置

**部署后验证**:

- [ ] Gateway 可以正常访问
- [ ] Layer 1 认证正常工作
- [ ] Layer 2 权限检查正常工作
- [ ] Layer 3 外部认证正常工作
- [ ] 审计日志正常记录

### 高级认证选项

#### JWT Token 认证（替代 Gateway Secret）

**AI-Box 端生成 JWT**:

```python
# services/auth/jwt_service.py
import jwt
from datetime import datetime, timedelta

def generate_gateway_token(user_id: str, tenant_id: str) -> str:
    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
        "aud": "mcp-gateway",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
```

**Gateway 端验证 JWT**:

```typescript
// src/auth/jwt.ts
import jwt from '@tsndr/cloudflare-worker-jwt';

async verifyJWT(token: string): Promise<any> {
  const isValid = await jwt.verify(token, this.env.JWT_SECRET);
  if (!isValid) {
    throw new Error('Invalid token');
  }
  return await jwt.decode(token);
}
```

### 维护和更新

**定期任务**:

1. **每周**: 审查认证失败日志
2. **每月**: 审查用户权限
3. **每季度**: 轮换密钥
4. **每半年**: 安全审计

**更新认证配置**:

```bash
# 更新单个工具的认证配置
cd mcp/gateway
wrangler kv:key put "auth:tool_name" \
  '{"type":"api_key","api_key":"new-key"}' \
  --namespace-id=YOUR_KV_NAMESPACE_ID
```

---

## 📚 参考资源

- [Cloudflare Workers 文档](https://developers.cloudflare.com/workers/)
- [Wrangler CLI 文档](https://developers.cloudflare.com/workers/wrangler/)
- [Workers KV 文档](https://developers.cloudflare.com/workers/runtime-apis/kv/)
- [Workers Durable Objects 文档](https://developers.cloudflare.com/workers/runtime-apis/durable-objects/)

### 相关文档

- [開發環境部署狀態報告](./開發環境部署狀態報告.md) - 当前开发环境部署状态和配置信息
- [Cloudflare 手动操作清单](./Cloudflare-手动操作清单.md) - 必须手动执行的操作清单
- [Cloudflare 生产环境迁移指南](./Cloudflare-生产环境迁移指南.md) - 从开发环境迁移到生产环境的完整指南

---

**最后更新日期**: 2026-01-14
**维护人**: Daniel Chung

---

## 📝 更新日志

### 2026-01-14 更新

**重要更新**:

- ✅ 添加了完整的"实际配置详情"章节，包含所有 Cloudflare、ngrok、mcp_gateway 配置
- ✅ 记录了自定义域名 `mcp.k84.org` 的完整配置步骤（包括 Dashboard 路由设置）
- ✅ 添加了 ngrok 配置详情（包括 authtoken 和启动步骤）
- ✅ 添加了庫管員 Agent 完整配置流程（包括路由、认证、权限配置）
- ✅ 更新了所有实际配置值（Gateway Secret、KV 命名空间 ID、ngrok URL 等）
- ✅ 添加了完整的测试命令和验证步骤
- ✅ 添加了配置更新流程和维护指南
- ✅ 更新了部署状态追踪表（所有配置标记为已完成）

**配置状态**:

- ✅ Cloudflare Worker 已部署并正常工作
- ✅ 自定义域名 `mcp.k84.org` 已配置并正常工作
- ✅ ngrok 已配置并运行（`https://182740a0a99a.ngrok-free.app`）
- ✅ 庫管員 Agent 已注册并配置（`warehouse_execute_task`）
- ✅ 所有路由、认证、权限配置已完成

### 2025-12-31 初始版本

- ✅ 创建了 Cloudflare MCP Gateway 设置指南
- ✅ 记录了基本配置步骤和架构说明
