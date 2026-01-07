# Cloudflare MCP Gateway

**创建日期**: 2025-12-31
**创建人**: Daniel Chung
**最后修改日期**: 2025-12-31

---

## 📋 概述

Cloudflare MCP Gateway 是 AI-Box 与外部 MCP Server 之间的隔离层，提供统一的路由、认证、审计和监控功能。

---

## 🚀 快速开始

### 1. 安装依赖

```bash
npm install
# 或
pnpm install
```

### 2. 配置 wrangler.toml

1. 创建 KV 命名空间（参考手动操作清单）
2. 更新 `wrangler.toml` 中的 KV 命名空间 ID
3. 配置 MCP 路由规则

### 3. 设置 Secrets

```bash
# 设置 Gateway Secret
wrangler secret put GATEWAY_SECRET

# 设置外部 MCP API Keys
wrangler secret put OFFICE_API_KEY
wrangler secret put SLACK_CLIENT_ID
# ... 其他 API Keys
```

### 4. 本地开发

```bash
npm run dev
```

### 5. 部署

```bash
# 部署到生产环境
npm run deploy

# 部署到预览环境
npm run deploy:preview
```

---

## 📁 项目结构

```
mcp/gateway/
├── src/
│   ├── index.ts              # Worker 主入口
│   ├── gateway.ts            # Gateway 核心逻辑
│   ├── router.ts             # 路由引擎
│   ├── auth.ts               # 认证授权
│   ├── filter.ts             # 请求过滤
│   ├── audit.ts              # 审计日志
│   └── auth/
│       ├── permissions.ts    # 权限管理
│       └── ratelimit.ts      # 速率限制
├── wrangler.toml             # Worker 配置
├── package.json
├── tsconfig.json
└── README.md
```

---

## ⚙️ 配置说明

### MCP 路由配置

在 `wrangler.toml` 中配置 `MCP_ROUTES` 环境变量：

```json
[
  {
    "pattern": "office_*",
    "target": "https://office-mcp.example.com/mcp"
  },
  {
    "pattern": "finance_*",
    "target": "https://finance-mcp.example.com/mcp"
  }
]
```

### 认证配置

使用 KV 存储配置外部 MCP 认证信息：

```bash
wrangler kv:key put "auth:office_word" \
  '{"type":"api_key","api_key":"${OFFICE_API_KEY}","header_name":"X-API-Key"}' \
  --namespace-id=YOUR_KV_NAMESPACE_ID
```

### 权限配置

使用 KV 存储配置用户权限：

```bash
wrangler kv:key put "permissions:tenant-456:user-123" \
  '{"tools":["finance_*","office_readonly_*"],"rate_limits":{"default":100}}' \
  --namespace-id=YOUR_PERMISSIONS_KV_NAMESPACE_ID
```

---

## 🔐 认证流程

### 三层认证架构

1. **Layer 1: Gateway Secret 验证**
   - AI-Box 请求必须包含 `X-Gateway-Secret` 头
   - Gateway 验证 Secret 是否匹配

2. **Layer 2: 用户权限和速率限制**
   - 检查用户是否有权限使用该工具
   - 检查是否超过速率限制

3. **Layer 3: 外部 MCP Server 认证**
   - 从 KV 获取认证配置
   - 构建认证请求头（API Key、Bearer Token、OAuth 2.0）

---

## 📊 监控和日志

### Workers Analytics

在 Cloudflare Dashboard 中查看：

- 请求量
- 错误率
- 响应时间
- CPU 使用率

### 审计日志

审计日志记录到：

- R2 存储（如果配置）
- 外部日志服务（如果配置）
- 控制台（开发环境）

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

---

## 📚 相关文档

- [Cloudflare MCP Gateway 设置指南](../../../docs/系统设计文档/核心组件/MCP工具/Cloudflare-MCP-Gateway-设置指南.md)
- [Cloudflare 手动操作清单](../../../docs/系统设计文档/核心组件/MCP工具/Cloudflare-手动操作清单.md)
- [MCP 工具系统规格](../../../docs/系统设计文档/核心组件/MCP工具/MCP工具.md)

---

**最后更新日期**: 2025-12-31
**维护人**: Daniel Chung
