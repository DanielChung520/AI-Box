# 第三方 MCP 服务配置指南

**创建日期**: 2025-12-31
**创建人**: Daniel Chung
**最后修改日期**: 2026-01-14

---

## 📋 概述

本指南说明如何在 AI-Box 中配置和使用第三方 MCP (Model Context Protocol) 服务，通过 Gateway 统一管理和代理所有第三方 MCP Server 请求。

AI-Box 支持多种 Gateway 提供商，目前主要使用 **Cloudflare Gateway**，未来可能支持 Google Cloud、AWS 等其他提供商。

---

## 🎯 配置目标

通过 Gateway 统一管理第三方 MCP 服务，实现：

- ✅ 统一认证和授权
- ✅ IP 隐藏和隐私保护
- ✅ 完整的审计日志
- ✅ 速率限制和访问控制
- ✅ 统一的工具发现和注册

---

## 🏗️ Gateway 提供商选择

### 当前支持

#### Cloudflare Gateway（推荐，当前使用）

**特点**：

- ✅ 全球边缘网络，低延迟
- ✅ 商业 SLA 保障
- ✅ 完整的审计和监控功能
- ✅ 易于配置和部署
- ✅ 成本效益高

**设置指南**：请参阅 [Cloudflare MCP Gateway 设置指南](./Cloudflare-MCP-Gateway-设置指南.md)

### 未来计划

#### Google Cloud Gateway（规划中）

**特点**：

- 与 Google Cloud 服务深度集成
- 支持 Google Cloud IAM 认证
- 适用于已使用 Google Cloud 的企业

**状态**：规划中，待实现

#### AWS API Gateway（规划中）

**特点**：

- 与 AWS 服务深度集成
- 支持 AWS IAM 认证
- 适用于已使用 AWS 的企业

**状态**：规划中，待实现

---

## 🔧 配置流程

### 步骤 1: 选择并设置 Gateway

根据您的需求和现有基础设施，选择合适的 Gateway 提供商：

#### 选项 1: Cloudflare Gateway（推荐）

**适用场景**：

- 需要全球低延迟访问
- 需要商业 SLA 保障
- 需要快速部署和配置
- 成本敏感的项目

**设置步骤**：请参阅 [Cloudflare MCP Gateway 设置指南](./Cloudflare-MCP-Gateway-设置指南.md)

#### 选项 2: 其他 Gateway（未来支持）

当其他 Gateway 提供商支持后，将在此处添加相应的设置指南。

### 步骤 2: 在 Gateway 中配置路由

#### 1.1 查找第三方 MCP Server 端点

**查找 MCP Server 的方式**:

1. **smithery.ai 市场**: <https://smithery.ai/>
   - 浏览可用的 MCP Server
   - 查看 Server 详情和端点 URL
   - **注意**: smithery.ai 提供的 URL 可能需要确认是否支持标准的 MCP Protocol

2. **GitHub MCP Server 列表**: <https://github.com/modelcontextprotocol/servers>
   - 查找官方或社区维护的 MCP Server
   - 查看部署说明和端点配置

3. **自行部署 MCP Server**:
   - 使用 MCP SDK 开发自己的 MCP Server
   - 部署到可公开访问的服务器

**端点 URL 格式示例**:

- `https://your-mcp-server.com/mcp`（标准 HTTP MCP Server）
- `https://smithery.ai/server/@username/server-name`（smithery.ai 托管）
- `wss://your-mcp-server.com/mcp`（WebSocket MCP Server，需要适配）

#### 1.2 配置 Gateway 路由（以 Cloudflare Gateway 为例）

**注意**：以下配置示例基于 Cloudflare Gateway。如果您使用其他 Gateway 提供商，请参考相应的设置指南。

**当前实现说明**: Gateway 支持两种路由方式，优先使用方式一（pattern 匹配），如果未匹配则使用方式二（请求头）。

**方式一：通过 wrangler.toml 配置路由规则（推荐，优先使用）**

**文件位置**: `mcp/gateway/wrangler.toml`

**详细设置步骤**：请参阅 [Cloudflare MCP Gateway 设置指南](./Cloudflare-MCP-Gateway-设置指南.md)

```toml
[vars]
# MCP 路由配置（JSON 格式）
MCP_ROUTES = '''
[
  {
    "pattern": "yahoo_finance_*",
    "target": "https://your-yahoo-finance-mcp-server.com/mcp"
  },
  {
    "pattern": "slack_*",
    "target": "https://your-slack-mcp-server.com/mcp"
  },
  {
    "pattern": "notion_*",
    "target": "https://your-notion-mcp-server.com/mcp"
  }
]
'''
```

**路由规则说明**:

- `pattern`: 工具名称匹配模式（支持通配符 `*`）
  - `yahoo_finance_*` 匹配所有以 `yahoo_finance_` 开头的工具（如 `yahoo_finance_quote`, `yahoo_finance_history`）
  - `slack_*` 匹配所有以 `slack_` 开头的工具
  - `*` 匹配所有工具（默认路由）
- `target`: 第三方 MCP Server 的真实端点 URL

**方式二：通过请求头 X-Real-Endpoint 传递端点（备用方案）**

如果 pattern 匹配失败，Gateway 会检查请求头 `X-Real-Endpoint`，如果存在则使用该端点。

AI-Box 的 `ExternalMCPTool` 会自动在请求头中设置 `X-Real-Endpoint`（来自配置文件的 `mcp_endpoint`）。

**方式三：通过 DEFAULT_MCP_ENDPOINT 设置默认端点**

如果以上两种方式都未找到端点，会使用默认端点：

```toml
[vars]
DEFAULT_MCP_ENDPOINT = "https://default-mcp-server.com/mcp"
```

**推荐配置策略**:

- **第三方服务**: 使用方式一（pattern 匹配），在 `wrangler.toml` 中配置路由规则
- **动态端点**: 使用方式二（请求头），在 `external_mcp_tools.yaml` 中配置 `mcp_endpoint`
- **开发测试**: 使用方式三（默认端点），设置 `DEFAULT_MCP_ENDPOINT`

**部署配置**:

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
wrangler deploy
```

**路由工作流程**（当前实现）:

1. AI-Box 发送请求到 Gateway（`proxy_endpoint`），包含请求头 `X-Tool-Name`（工具名称）
2. Gateway Router 从 MCP 请求中提取工具名称（`mcpRequest.params?.name` 或请求头 `X-Tool-Name`）
3. Gateway Router 尝试匹配工具名称到 pattern（如 `yahoo_finance_quote` → `yahoo_finance_*`）
4. 如果匹配成功，使用匹配的 `target` 端点
5. 如果匹配失败，使用 `DEFAULT_MCP_ENDPOINT`（如果配置），否则返回错误
6. Gateway 转发请求到最终确定的端点

**注意**: 当前实现**不支持**从请求头 `X-Real-Endpoint` 获取端点。如果需要此功能，需要修改 `router.ts` 实现。建议使用方式一（pattern 匹配）配置路由。

#### 1.3 配置认证信息（在 Gateway KV 存储中）

**注意**：以下配置示例基于 Cloudflare Gateway。如果您使用其他 Gateway 提供商，请参考相应的设置指南。

**详细设置步骤**：请参阅 [Cloudflare MCP Gateway 设置指南](./Cloudflare-MCP-Gateway-设置指南.md) 中的认证配置部分。

**配置无认证的 MCP Server**（如 Yahoo Finance public demo）:

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# Yahoo Finance MCP Server（无认证）
wrangler kv key put "auth:yahoo_finance_quote" \
  '{"type":"none"}' \
  --namespace-id=5b6e229c21f649269e93db9dcb8a7e16 \
  --remote
```

**配置需要 API Key 的服务**:

```bash
# 首先设置 API Key Secret
wrangler secret put YAHOO_FINANCE_API_KEY
# 然后配置认证
wrangler kv key put "auth:yahoo_finance_quote" \
  '{"type":"api_key","api_key":"${YAHOO_FINANCE_API_KEY}","header_name":"X-API-Key"}' \
  --namespace-id=5b6e229c21f649269e93db9dcb8a7e16 \
  --remote
```

**配置需要 Bearer Token 的服务**:

```bash
# 首先设置 Token Secret
wrangler secret put NOTION_API_KEY
# 然后配置认证
wrangler kv key put "auth:notion_create_page" \
  '{"type":"bearer","token":"${NOTION_API_KEY}"}' \
  --namespace-id=5b6e229c21f649269e93db9dcb8a7e16 \
  --remote
```

**配置需要 OAuth 2.0 的服务**:

```bash
# 首先设置 OAuth 凭证
wrangler secret put SLACK_CLIENT_ID
wrangler secret put SLACK_CLIENT_SECRET
# 然后配置认证
wrangler kv key put "auth:slack_send_message" \
  '{"type":"oauth2","client_id":"${SLACK_CLIENT_ID}","client_secret":"${SLACK_CLIENT_SECRET}","token_url":"https://slack.com/api/oauth.v2.access"}' \
  --namespace-id=5b6e229c21f649269e93db9dcb8a7e16 \
  --remote
```

---

### 步骤 2: 在 AI-Box 中配置外部工具

#### 2.1 创建或更新 `external_mcp_tools.yaml`

**文件位置**: 项目根目录 `external_mcp_tools.yaml`

**配置示例**（Yahoo Finance MCP Server）:

```yaml
# 外部 MCP 工具配置文件
# 配置第三方 MCP Server 通过 Cloudflare Gateway 访问

external_tools:
  # Yahoo Finance MCP Server（通过 smithery.ai）
  - name: "yahoo_finance"
    description: "Yahoo Finance MCP Server - 股票数据查询工具"
    mcp_endpoint: "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp"  # 真实端点
    proxy_endpoint: "https://mcp.k84.org"  # Cloudflare Gateway 端点
    proxy_config:
      enabled: true  # 必须启用 Gateway 代理
      audit_enabled: true  # 启用审计日志
      hide_ip: true  # 隐藏真实 IP
    network_type: "third_party"  # 标记为第三方服务
    # 工具会在注册时自动发现，也可以手动指定
    tool_name_on_server: null  # null 表示使用工具名称（自动发现）
    auth_type: "none"  # 认证类型
    auth_config:
      type: "none"
    # 注意：input_schema 会在工具发现时自动获取，也可以手动指定
    input_schema:
      type: object
      properties: {}
      # 实际的 schema 会在工具发现时自动更新
```

**配置说明**:

| 字段 | 说明 | 必需 |
|------|------|------|
| `name` | 工具名称（本地别名） | ✅ |
| `description` | 工具描述 | ✅ |
| `mcp_endpoint` | 第三方 MCP Server 的真实端点 URL | ✅ |
| `proxy_endpoint` | Cloudflare Gateway 端点 | ✅ |
| `proxy_config` | Gateway 代理配置 | ✅ |
| `network_type` | 网络类型（`third_party` 或 `internal_trusted`） | ✅ |
| `tool_name_on_server` | 外部服务器上的工具名称（可选，支持自动发现） | ❌ |
| `auth_type` | 认证类型（`none` / `api_key` / `bearer` / `oauth2`） | ✅ |
| `auth_config` | 认证配置 | ✅ |
| `input_schema` | 输入 Schema（可选，支持自动发现） | ❌ |

#### 2.2 自动工具发现

AI-Box 的 `ExternalToolManager` 支持自动发现外部 MCP Server 上的工具：

1. **工具注册时自动发现**: 注册外部工具时，会自动调用 `tools/list` 获取可用工具列表
2. **动态刷新**: 支持定期刷新工具列表，获取最新工具
3. **Schema 自动更新**: 工具的 input_schema 会自动从外部服务器获取

**自动发现流程**:

```
1. 加载配置 → 2. 连接到 MCP Server → 3. 调用 tools/list → 4. 注册每个工具
```

---

### 步骤 3: 工具注册和启动

#### 3.1 在 AI-Box 启动时注册外部工具

外部工具会在 AI-Box MCP Server 启动时自动注册（通过 `ExternalToolManager`）。

**注册流程**:

```python
# 在 mcp/server/main.py 的 lifespan 中
from mcp.server.tools.external_manager import ExternalToolManager

async def lifespan(app):
    # 加载并注册外部工具
    external_manager = ExternalToolManager(config_path="external_mcp_tools.yaml")
    await external_manager.register_all_external_tools(server=server)
    yield
    # 清理资源
    for tool in external_manager.registered_tools.values():
        await tool.close()
```

#### 3.2 验证工具注册

**通过 API 检查工具列表**:

```bash
curl http://localhost:8002/mcp/tools
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "tools": [
      {
        "name": "yahoo_finance_quote",
        "description": "Get stock quote from Yahoo Finance",
        "type": "external",
        "mcp_endpoint": "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp",
        "proxy_endpoint": "https://mcp.k84.org"
      }
    ]
  }
}
```

---

### 步骤 4: 前端展示

#### 4.1 工具列表展示

前端可以通过以下 API 获取工具列表：

**API 端点**: `GET /api/mcp/tools`

**响应格式**:

```json
{
  "success": true,
  "data": {
    "tools": [
      {
        "name": "yahoo_finance_quote",
        "description": "Get stock quote from Yahoo Finance",
        "type": "external",
        "category": "finance",
        "mcp_endpoint": "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp",
        "proxy_endpoint": "https://mcp.k84.org",
        "input_schema": {
          "type": "object",
          "properties": {
            "symbol": {
              "type": "string",
              "description": "Stock symbol (e.g., AAPL, TSLA)"
            }
          },
          "required": ["symbol"]
        }
      }
    ]
  }
}
```

#### 4.2 工具调用

**API 端点**: `POST /api/mcp/tools/call`

**请求格式**:

```json
{
  "tool_name": "yahoo_finance_quote",
  "arguments": {
    "symbol": "AAPL"
  }
}
```

**响应格式**:

```json
{
  "success": true,
  "data": {
    "result": {
      "symbol": "AAPL",
      "price": 150.25,
      "change": 1.23,
      "changePercent": 0.82
    }
  }
}
```

#### 4.3 前端组件示例

**React 组件示例**:

```typescript
// components/MCPToolList.tsx
import { useEffect, useState } from 'react';

interface MCPTool {
  name: string;
  description: string;
  type: 'internal' | 'external';
  category?: string;
  input_schema?: any;
}

export function MCPToolList() {
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/mcp/tools')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setTools(data.data.tools);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Loading tools...</div>;

  return (
    <div className="tool-list">
      <h2>Available MCP Tools</h2>
      <div className="tools-grid">
        {tools.map(tool => (
          <div key={tool.name} className="tool-card">
            <h3>{tool.name}</h3>
            <p>{tool.description}</p>
            <span className={`badge ${tool.type}`}>
              {tool.type === 'external' ? 'External' : 'Internal'}
            </span>
            {tool.category && (
              <span className="badge category">{tool.category}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 📝 完整配置示例

### Yahoo Finance MCP Server 完整配置

#### Gateway 配置 (`wrangler.toml`)

```toml
MCP_ROUTES = '''
[
  {
    "pattern": "yahoo_finance_*",
    "target": "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp"
  }
]
'''
```

#### Gateway 认证配置

```bash
# 配置认证（无认证）
wrangler kv key put "auth:yahoo_finance_quote" \
  '{"type":"none"}' \
  --namespace-id=5b6e229c21f649269e93db9dcb8a7e16 \
  --remote
```

#### AI-Box 配置 (`external_mcp_tools.yaml`)

```yaml
external_tools:
  - name: "yahoo_finance"
    description: "Yahoo Finance MCP Server - 股票数据查询工具"
    mcp_endpoint: "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp"
    proxy_endpoint: "https://mcp.k84.org"
    proxy_config:
      enabled: true
      audit_enabled: true
      hide_ip: true
    network_type: "third_party"
    auth_type: "none"
    auth_config:
      type: "none"
```

---

## 🔍 工具发现机制

### 自动发现流程

1. **初始发现**: 注册工具时，自动调用外部 MCP Server 的 `tools/list` 方法
2. **工具注册**: 为每个发现的工具创建 `ExternalMCPTool` 实例
3. **Schema 获取**: 自动获取每个工具的 input_schema
4. **健康检查**: 验证工具是否可用

### 手动指定工具

如果不想使用自动发现，可以手动指定工具：

```yaml
external_tools:
  - name: "yahoo_finance_quote"  # 本地工具名称
    description: "Get stock quote"
    mcp_endpoint: "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp"
    tool_name_on_server: "get_quote"  # 外部服务器上的工具名称
    input_schema:
      type: object
      properties:
        symbol:
          type: string
      required: ["symbol"]
```

---

## 🧪 测试和验证

### 1. 测试 Gateway 路由

```bash
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -H "X-Tool-Name: yahoo_finance_quote" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

### 2. 测试工具调用

```bash
curl -X POST http://localhost:8002/api/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "yahoo_finance_quote",
    "arguments": {
      "symbol": "AAPL"
    }
  }'
```

---

## 📊 工具状态管理

### 工具健康检查

**API 端点**: `GET /api/mcp/tools/{tool_name}/health`

**响应格式**:

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "type": "external",
    "latency_ms": 150.5,
    "endpoint": "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp",
    "proxy_endpoint": "https://mcp.k84.org"
  }
}
```

### 工具统计

**API 端点**: `GET /api/mcp/tools/{tool_name}/stats`

**响应格式**:

```json
{
  "success": true,
  "data": {
    "total_calls": 1250,
    "success_rate": 0.98,
    "average_latency_ms": 145.3,
    "error_types": {
      "TimeoutError": 5,
      "ConnectionError": 2
    }
  }
}
```

---

## 🔄 工具刷新和更新

### 手动刷新工具列表

**API 端点**: `POST /api/mcp/tools/refresh`

```bash
curl -X POST http://localhost:8002/api/mcp/tools/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_endpoint": "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp"
  }'
```

### 自动刷新配置

在 `ExternalToolManager` 中配置自动刷新间隔：

```python
external_manager = ExternalToolManager(
    config_path="external_mcp_tools.yaml",
    refresh_interval=3600  # 1 小时
)
```

---

## 🎨 前端展示建议

### 工具分类展示

建议按以下分类组织工具：

1. **内部工具** (Internal Tools)
   - 任务分析工具
   - 文件操作工具
   - 系统工具

2. **第三方工具** (Third-Party Tools)
   - 金融数据 (Finance)
     - Yahoo Finance
     - Alpha Vantage
   - 协作工具 (Collaboration)
     - Slack
     - Notion
   - 文档处理 (Document)
     - Office MCP
     - PDF Processing

### UI 组件建议

1. **工具卡片**: 显示工具名称、描述、类型、状态
2. **工具详情**: 显示 input_schema、使用示例、统计数据
3. **工具搜索**: 支持按名称、描述、分类搜索
4. **工具状态**: 显示健康状态、调用统计

---

## ⚠️ 注意事项

### 1. 端点 URL 格式

- smithery.ai 提供的 URL 格式: `https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp`
- 需要确认该端点是否支持标准的 MCP Protocol (JSON-RPC 2.0)
- 如果端点格式不同，可能需要适配

### 2. 认证配置

- 公开服务（如 Yahoo Finance public demo）使用 `auth_type: "none"`
- 需要 API Key 的服务使用 `auth_type: "api_key"`
- 需要 Token 的服务使用 `auth_type: "bearer"`
- OAuth 服务使用 `auth_type: "oauth2"`

### 3. 工具名称映射

- 本地工具名称 (`name`) 可以与外部服务器上的工具名称不同
- 使用 `tool_name_on_server` 指定外部服务器上的实际工具名称
- 如果未指定，使用 `name` 作为工具名称

### 4. Schema 自动获取

- 工具的 `input_schema` 会在工具发现时自动获取
- 也可以手动指定 `input_schema` 覆盖自动获取的值
- 建议使用自动获取，确保 Schema 最新

---

## 📚 相关文档

### 核心文档

- [MCP 工具系统规格](./MCP工具.md) - MCP 工具系统完整规格，包含其他 MCP 工具记录
- [Cloudflare MCP Gateway 设置指南](./Cloudflare-MCP-Gateway-设置指南.md) - Cloudflare Gateway 详细设置指南（当前使用）

### 参考文档

- [參考&歸檔文件](./參考&歸檔文件/) - 历史文档和参考材料

---

## 🔗 相关资源

- [MCP Protocol 官方文档](https://modelcontextprotocol.io/)
- [smithery.ai MCP Server 市场](https://smithery.ai/)
- [Cloudflare Workers 文档](https://developers.cloudflare.com/workers/)

---

**最后更新日期**: 2025-12-31
**维护人**: Daniel Chung
