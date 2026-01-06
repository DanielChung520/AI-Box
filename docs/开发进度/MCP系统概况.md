# MCP 系统概况

**创建日期**: 2025-12-30
**创建人**: Daniel Chung
**最后修改日期**: 2025-12-30

---

## 📋 概述

MCP (Model Context Protocol) 是 AI-Box 系统中用于 Agent 和工具调用的统一协议层。系统实现了完整的 MCP Server 和 MCP Client 架构，支持工具注册、调用、负载均衡和健康检查等功能。

---

## 🏗️ 架构概览

### 目录结构

```
mcp/
├── server/                          # MCP Server 实现
│   ├── __init__.py
│   ├── config.py                    # 服务器配置管理
│   ├── main.py                      # 启动入口
│   ├── server.py                    # 核心服务器实现
│   ├── monitoring.py                # 监控和指标收集
│   ├── protocol/                    # MCP 协议定义
│   │   ├── __init__.py
│   │   └── models.py                # 协议数据模型
│   └── tools/                       # MCP 工具
│       ├── __init__.py
│       ├── base.py                  # 工具基类
│       ├── registry.py             # 工具注册表（扩展版）
│       ├── task_analyzer.py         # Task Analyzer 工具
│       ├── file_tool.py             # 文件操作工具
│       ├── external_tool.py         # 外部 MCP 工具代理类
│       ├── external_manager.py      # 外部工具管理器
│       └── config.yaml              # 工具配置文件
└── client/                          # MCP Client 实现
    ├── __init__.py
    ├── client.py                    # 客户端核心实现
    └── connection/                  # 连接管理
        ├── __init__.py
        ├── manager.py               # 连接管理器
        └── pool.py                  # 连接池实现
```

---

## 🔧 MCP Server 配置

### 基本配置

**配置文件**: `mcp/server/config.py`

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `server_name` | `ai-box-mcp-server` | 服务器名称 |
| `server_version` | `1.0.0` | 服务器版本 |
| `protocol_version` | `2024-11-05` | MCP 协议版本 |
| `host` | `0.0.0.0` | 服务器主机地址 |
| `port` | `8002` | 服务器端口（注意：env.example 中为 8001） |
| `log_level` | `INFO` | 日志级别 |
| `enable_monitoring` | `True` | 是否启用监控 |
| `metrics_endpoint` | `/metrics` | 指标端点 |
| `shutdown_timeout` | `30` | 关闭超时时间（秒） |

### 环境变量配置

**文件**: `env.example`

```bash
# MCP Server 配置
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8001  # 注意：与代码默认值 8002 不一致
```

**注意**: 环境变量 `MCP_SERVER_PORT=8001` 与代码默认值 `8002` 不一致，需要统一。

### 启动方式

```bash
# 直接启动
python -m mcp.server.main

# 指定参数
python -m mcp.server.main --host 0.0.0.0 --port 8002

# 开发模式（自动重载）
python -m mcp.server.main --reload
```

---

## 🛠️ 已注册工具

### 1. Task Analyzer Tool

**文件**: `mcp/server/tools/task_analyzer.py`

**功能**: 任务分析和分类（Mock 实现）

**输入 Schema**:

```json
{
  "type": "object",
  "properties": {
    "task": {
      "type": "string",
      "description": "要分析的任务描述"
    },
    "context": {
      "type": "object",
      "description": "任务上下文信息",
      "additionalProperties": true
    }
  },
  "required": ["task"]
}
```

**输出示例**:

```json
{
  "task_id": "task_1234",
  "task_type": "planning",
  "workflow": "planning_workflow",
  "complexity": "medium",
  "estimated_time": "30 minutes",
  "required_agents": ["planning"],
  "confidence": 0.85,
  "analysis": {
    "keywords": ["plan", "任务"],
    "intent": "User wants to planning",
    "suggestions": [
      "Use planning_workflow for this task",
      "Consider breaking down into smaller steps"
    ]
  }
}
```

**分类逻辑**:

- 包含 "plan"/"计划"/"规划" → `planning`
- 包含 "execute"/"执行"/"运行" → `execution`
- 包含 "review"/"审查"/"检查" → `review`
- 其他 → `general`

### 2. File Tool

**文件**: `mcp/server/tools/file_tool.py`

**功能**: 文件读写操作工具

**输入 Schema**:

```json
{
  "type": "object",
  "properties": {
    "operation": {
      "type": "string",
      "enum": ["read", "write", "list", "delete"],
      "description": "操作类型"
    },
    "path": {
      "type": "string",
      "description": "文件路径（相对于 base_path）"
    },
    "content": {
      "type": "string",
      "description": "文件内容（仅用于 write 操作）"
    }
  },
  "required": ["operation", "path"]
}
```

**安全限制**:

- 基础路径: `/tmp`（可配置）
- 路径验证: 确保所有操作都在基础路径内
- 防止路径遍历攻击

**支持操作**:

- `read`: 读取文件内容
- `write`: 写入文件内容
- `list`: 列出目录内容
- `delete`: 删除文件或目录

---

## 🔌 MCP Client 架构

### 连接管理器

**文件**: `mcp/client/connection/manager.py`

**功能**:

- 管理多个 MCP Server 端点
- 负载均衡（轮询策略）
- 健康检查（默认 30 秒间隔）
- 自动重试（默认最多 3 次）
- 连接池管理

**配置参数**:

```python
MCPConnectionManager(
    endpoints=["http://mcp-server:8002/mcp"],  # 端点列表
    load_balance_strategy=LoadBalanceStrategy.ROUND_ROBIN,
    health_check_interval=30,  # 健康检查间隔（秒）
    max_retries=3,  # 最大重试次数
    retry_delay=1.0,  # 重试延迟（秒）
)
```

### 客户端实现

**文件**: `mcp/client/client.py`

**功能**:

- 初始化连接
- 列出可用工具
- 调用工具
- 错误处理和重试
- 自动重连

**主要方法**:

- `initialize()`: 初始化连接
- `list_tools()`: 列出可用工具
- `call_tool(name, arguments)`: 调用工具
- `close()`: 关闭连接

---

## 🌐 API 路由集成

### FastAPI 路由

**文件**: `api/routers/mcp.py`

**路由端点**:

1. **GET `/mcp/status`**
   - 获取 MCP 连接状态
   - 返回连接统计信息

2. **GET `/mcp/tools`**
   - 列出 MCP Server 可用工具
   - 返回工具列表和 Schema

3. **POST `/mcp/tools/call`**
   - 调用 MCP 工具
   - 请求体: `{ "tool_name": "...", "arguments": {...} }`

### 环境变量配置

**MCP Server 端点配置**:

```bash
MCP_SERVER_ENDPOINTS=http://mcp-server:8002/mcp
# 支持多个端点（逗号分隔）
MCP_SERVER_ENDPOINTS=http://mcp-server1:8002/mcp,http://mcp-server2:8002/mcp
```

---

## 📊 协议模型

### 核心消息类型

**文件**: `mcp/server/protocol/models.py`

1. **MCPRequest**: 请求消息
   - `method`: 方法名称
   - `params`: 请求参数

2. **MCPResponse**: 响应消息
   - `result`: 响应结果

3. **MCPError**: 错误信息
   - `code`: 错误代码
   - `message`: 错误消息
   - `data`: 错误详情

4. **MCPTool**: 工具定义
   - `name`: 工具名称
   - `description`: 工具描述
   - `inputSchema`: 输入 Schema

### 协议版本

- **当前版本**: `2024-11-05`
- **JSON-RPC 版本**: `2.0`

---

## 🔍 监控和指标

### 监控配置

**文件**: `mcp/server/monitoring.py`

**功能**:

- 请求计数
- 响应时间统计
- 错误率统计
- 工具调用统计

**指标端点**: `/metrics`

**指标数据**:

```json
{
  "total_requests": 1000,
  "successful_requests": 950,
  "failed_requests": 50,
  "average_response_time_ms": 120.5,
  "tool_calls": {
    "task_analyzer": 500,
    "file_tool": 450
  }
}
```

---

## 🔗 Agent 集成

### Agent MCP Server 实现

以下 Agent 实现了 MCP Server 接口：

1. **Planning Agent**
   - 文件: `agents/planning/mcp_server.py`
   - 文件: `agents/core/planning/handlers.py`

2. **Execution Agent**
   - 文件: `agents/execution/mcp_server.py`
   - 文件: `agents/core/execution/handlers.py`

3. **Review Agent**
   - 文件: `agents/review/mcp_server.py`
   - 文件: `agents/core/review/handlers.py`

### Agent Registry 集成

**文件**: `agents/services/registry/models.py`

**Agent 端点配置**:

```python
class AgentEndpoints(BaseModel):
    mcp_endpoint: Optional[str]  # MCP 端点 URL
    health_endpoint: Optional[str]  # 健康检查端点
```

---

## 📝 工具注册机制

### 工具注册表

**文件**: `mcp/server/tools/registry.py`

**功能**:

- 工具注册和注销
- 工具查询
- 工具列表管理

**使用示例**:

```python
from mcp.server.tools.registry import get_registry
from mcp.server.tools.base import BaseTool

# 获取注册表
registry = get_registry()

# 注册工具
tool = MyCustomTool()
registry.register(tool)

# 查询工具
tool = registry.get("tool_name")

# 列出所有工具
tools = registry.list_all()
```

### 工具基类

**文件**: `mcp/server/tools/base.py`

**BaseTool 接口**:

- `name`: 工具名称
- `description`: 工具描述
- `input_schema`: 输入 Schema（JSON Schema）
- `execute(arguments)`: 执行工具（异步方法）
- `validate_input(arguments)`: 验证输入参数

---

## 🌐 外部 MCP 工具支持

### 外部工具集成机制

系统支持通过 `ExternalMCPTool` 代理类集成外部 MCP Server 提供的工具。

**核心组件**:

- `ExternalMCPTool`: 外部工具代理类
- `ExternalToolManager`: 外部工具管理器
- `external_mcp_tools.yaml`: 外部工具配置文件

**功能特性**:

- ✅ 动态工具发现和注册
- ✅ 支持多种认证方式（API Key、OAuth、Bearer Token）
- ✅ 自动健康检查和连接验证
- ✅ 定期刷新工具列表
- ✅ 工具调用统计和监控

**详细文档**: 请参阅 [MCP 工具系统规格](../核心组件/MCP工具/MCP工具.md)

---

## ⚠️ 已知问题

### 1. 端口配置不一致（已修复）

- ✅ **已统一**: 代码和环境变量默认值均为 `8002`
- ✅ **已更新**: `env.example` 已更新为 `8002`

### 2. Task Analyzer 为 Mock 实现

当前 `task_analyzer.py` 是 Mock 实现，使用简单的关键词匹配进行分类。

**建议**: 集成真实的 Task Analyzer 服务。

---

## 🚀 使用示例

### 1. 启动 MCP Server

```bash
# 使用默认配置
python -m mcp.server.main

# 指定端口
python -m mcp.server.main --port 8002

# 开发模式
python -m mcp.server.main --reload
```

### 2. 通过 API 调用工具

```bash
# 列出工具
curl http://localhost:8000/mcp/tools

# 调用 Task Analyzer
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "task_analyzer",
    "arguments": {
      "task": "帮我制定一个项目计划",
      "context": {}
    }
  }'

# 调用 File Tool
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "file_tool",
    "arguments": {
      "operation": "read",
      "path": "test.txt"
    }
  }'
```

### 3. 在代码中使用 MCP Client

```python
from mcp.client.connection.manager import MCPConnectionManager
from mcp.client.connection.pool import LoadBalanceStrategy

# 创建连接管理器
manager = MCPConnectionManager(
    endpoints=["http://localhost:8002/mcp"],
    load_balance_strategy=LoadBalanceStrategy.ROUND_ROBIN,
)

# 初始化
await manager.initialize()

# 列出工具
tools = await manager.list_tools()

# 调用工具
result = await manager.call_tool(
    name="task_analyzer",
    arguments={"task": "分析任务", "context": {}}
)

# 关闭连接
await manager.close()
```

---

## 📚 相关文档

- [MCP 工具系统规格](../核心组件/MCP工具/MCP工具.md) - **新增**: 详细的工具系统规格文档
- [MCP 平台开发计划](../開發過程文件/plans/phase1/wbs-1.2-mcp-platform.md)
- [工具组开发规格](../tools/工具組開發規格.md)
- [代码管制表](../代碼管制表.md)

## 🔄 更新记录

### 2025-12-30: 外部 MCP 工具支持

**新增功能**:

- ✅ 外部 MCP 工具代理类 (`ExternalMCPTool`)
- ✅ 外部工具管理器 (`ExternalToolManager`)
- ✅ 工具注册表扩展（支持工具类型和元数据）
- ✅ 外部工具配置文件示例 (`external_mcp_tools.yaml.example`)
- ✅ 自动工具发现和刷新机制
- ✅ 工具健康检查和统计

**修复问题**:

- ✅ 统一端口配置为 `8002`
- ✅ 更新 `env.example` 配置

**新增文档**:

- ✅ [MCP 工具系统规格](../核心组件/MCP工具/MCP工具.md)

---

## 📊 统计信息

### 代码文件统计

| 类型 | 文件数 | 说明 |
|------|--------|------|
| Server 核心 | 5 | config, main, server, monitoring, protocol |
| Tools | 4 | base, registry, task_analyzer, file_tool |
| Client 核心 | 3 | client, manager, pool |
| **总计** | **12** | 核心实现文件 |

### 已注册工具

#### 内部工具

| 工具名称 | 状态 | 说明 |
|----------|------|------|
| `task_analyzer` | ✅ | Mock 实现，需要集成真实服务 |
| `file_tool` | ✅ | 完整实现，支持文件操作 |

#### 外部工具

外部工具通过 `external_mcp_tools.yaml` 配置文件动态注册。支持的第三方 MCP Server 包括：

- **Office 文档处理**: Glama Office、Microsoft Graph API、Gamma
- **金融数据**: Yahoo Finance、Alpha Vantage、IEX Cloud
- **协作工具**: Slack、Teams、Email (Gmail/Outlook)、Jira、Trello、Asana
- **数据可视化**: Power BI、Tableau、Google Looker、Metabase

**详细列表**: 请参阅 [MCP 工具系统规格](../核心组件/MCP工具/MCP工具.md#外部-mcp-工具列表)

---

**最后更新日期**: 2025-12-30
**维护人**: Daniel Chung
