# 庫管員 Agent - Cloudflare Gateway 測試指南

**創建日期**: 2026-01-14
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-14

---

## 📋 概述

本文檔說明如何測試通過 Cloudflare Gateway 註冊的庫管員 Agent。

---

## ✅ 配置狀態檢查

### 1. 檢查 Gateway 路由配置

**檢查方法**:

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
cat wrangler.toml | grep -A 10 "MCP_ROUTES"
```

**預期結果**:

```toml
MCP_ROUTES = '''
[
  {
    "pattern": "yahoo_finance_*",
    "target": "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp"
  },
  {
    "pattern": "warehouse_*",
    "target": "http://localhost:8003/mcp"
  }
]
'''
```

### 2. 檢查認證配置

**檢查方法**:

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
wrangler kv key get "auth:warehouse_query_part" \
  --namespace-id=5b6e229c21f649269e93db9dcb8a7e16 \
  --remote
```

**預期結果**:

```json
{"type":"none"}
```

### 3. 檢查 Gateway 部署狀態

**檢查方法**:

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
wrangler deployments list
```

**預期結果**: 顯示最新的部署版本

---

## 🧪 測試方法

### 測試 1: 測試 Gateway 路由匹配

**目標**: 驗證 Gateway 能夠正確匹配 `warehouse_*` 路由規則

**測試命令**:

```bash
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -H "X-Tool-Name: warehouse_query_part" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

**預期結果**:

**情況 A: 庫管員 Agent 正在運行**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "warehouse_query_part",
        "description": "查詢料號信息",
        ...
      },
      {
        "name": "warehouse_query_stock",
        "description": "查詢庫存信息",
        ...
      }
    ]
  }
}
```

**情況 B: 庫管員 Agent 未運行或無法連接**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": {
      "error": "Error: connect ECONNREFUSED 127.0.0.1:8003"
    }
  }
}
```

**情況 C: 路由匹配失敗**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32601,
    "message": "Method not found: No route for tool"
  }
}
```

**分析**:

- ✅ **情況 A**: 路由配置正確，庫管員 Agent 正常運行
- ⚠️ **情況 B**: 路由配置正確，但庫管員 Agent 未運行或無法連接（需要啟動 Agent）
- ❌ **情況 C**: 路由配置有問題，需要檢查 `wrangler.toml` 配置

### 測試 2: 測試工具調用

**目標**: 驗證能夠通過 Gateway 調用庫管員 Agent 的工具

**測試命令**:

```bash
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -H "X-Tool-Name: warehouse_query_part" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "warehouse_query_part",
      "arguments": {
        "part_number": "ABC-123"
      }
    }
  }'
```

**預期結果**:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "料號 ABC-123 的信息：..."
      }
    ]
  }
}
```

### 測試 3: 測試從 AI-Box 調用（完整流程）

**前提條件**:

1. 庫管員 Agent 已在 AI-Box 中註冊（端點指向 `https://mcp.k84.org`）
2. Agent 狀態為 `online`
3. 庫管員 Agent 服務正在運行

**測試步驟**:

1. **檢查 Agent 註冊狀態**

```bash
curl http://localhost:8000/api/v1/agents/warehouse-manager-agent
```

**預期響應**:

```json
{
  "success": true,
  "data": {
    "agent_id": "warehouse-manager-agent",
    "name": "庫管員 Agent",
    "status": "online",
    "endpoints": {
      "mcp": "https://mcp.k84.org",
      "protocol": "mcp"
    }
  }
}
```

2. **通過 AI-Box 調用 Agent**

```bash
curl -X POST http://localhost:8000/api/v1/agents/warehouse-manager-agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task_data": {
      "instruction": "查詢料號 ABC-123 的庫存"
    },
    "metadata": {
      "user_id": "test-user",
      "tenant_id": "test-tenant"
    }
  }'
```

**預期響應**:

```json
{
  "success": true,
  "data": {
    "task_id": "...",
    "status": "completed",
    "result": {
      "part_number": "ABC-123",
      "stock_quantity": 100,
      ...
    }
  }
}
```

---

## 🔍 故障排查

### 問題 1: 路由匹配失敗

**症狀**: 返回 `{"code":-32601,"message":"Method not found: No route for tool"}`

**排查步驟**:

1. **檢查路由配置**

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
cat wrangler.toml | grep -A 10 "MCP_ROUTES"
```

2. **確認工具名稱前綴**

工具名稱必須以 `warehouse_` 開頭，例如：

- ✅ `warehouse_query_part`
- ✅ `warehouse_query_stock`
- ❌ `query_part`（不匹配）

3. **重新部署 Gateway**

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
wrangler deploy
```

### 問題 2: 連接被拒絕

**症狀**: 返回 `{"error":"Error: connect ECONNREFUSED 127.0.0.1:8003"}`

**排查步驟**:

1. **檢查庫管員 Agent 是否運行**

```bash
# 檢查端口是否被占用
lsof -i :8003

# 或檢查進程
ps aux | grep warehouse
```

2. **檢查 Agent 端點配置**

確認 `wrangler.toml` 中的 `target` 是否正確：

```toml
{
  "pattern": "warehouse_*",
  "target": "http://localhost:8003/mcp"  # 確認這個端點正確
}
```

3. **如果 Agent 部署在其他主機**

更新 `target` 為實際的 IP 地址或域名：

```toml
{
  "pattern": "warehouse_*",
  "target": "http://192.168.1.100:8003/mcp"  # 使用實際 IP
}
```

### 問題 3: 認證失敗

**症狀**: 返回 `{"code":-32001,"message":"Unauthorized"}`

**排查步驟**:

1. **檢查認證配置**

```bash
wrangler kv key get "auth:warehouse_query_part" \
  --namespace-id=5b6e229c21f649269e93db9dcb8a7e16 \
  --remote
```

2. **如果使用 API Key 認證**

確認 Secret 已設置：

```bash
wrangler secret list
```

### 問題 4: Agent 未註冊或狀態不對

**症狀**: AI-Box 無法找到 Agent 或 Agent 狀態不是 `online`

**排查步驟**:

1. **檢查 Agent 註冊狀態**

```bash
curl http://localhost:8000/api/v1/agents/warehouse-manager-agent
```

2. **確認端點配置**

Agent 的 MCP 端點應該指向 Cloudflare Gateway：

```json
{
  "endpoints": {
    "mcp": "https://mcp.k84.org",  // ✅ 正確：指向 Gateway
    // "mcp": "http://localhost:8003/mcp"  // ❌ 錯誤：直接指向 Agent
  }
}
```

3. **管理員核准**

如果 Agent 狀態為 `registering`，需要管理員核准：

```bash
curl -X POST "http://localhost:8000/api/v1/agents/warehouse-manager-agent/approve?approved=true" \
  -H "Content-Type: application/json"
```

---

## 📊 測試檢查清單

### Gateway 配置檢查

- [ ] `wrangler.toml` 中已添加 `warehouse_*` 路由規則
- [ ] Gateway 已部署更新
- [ ] 認證配置已設置（如需要）
- [ ] 路由測試通過（測試 1）

### Agent 配置檢查

- [ ] 庫管員 Agent 服務正在運行（端口 8003）
- [ ] Agent 提供的工具名稱以 `warehouse_` 開頭
- [ ] Agent 端點可訪問（`http://localhost:8003/mcp`）

### AI-Box 註冊檢查

- [ ] Agent 已在 AI-Box 中註冊
- [ ] Agent 端點指向 Cloudflare Gateway（`https://mcp.k84.org`）
- [ ] Agent 狀態為 `online`
- [ ] 工具調用測試通過（測試 3）

---

## 🚀 快速測試腳本

### 測試腳本 1: Gateway 路由測試

```bash
#!/bin/bash

GATEWAY_URL="https://mcp.k84.org"
GATEWAY_SECRET="0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e"

echo "測試 Gateway 路由匹配..."
curl -X POST "$GATEWAY_URL" \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: $GATEWAY_SECRET" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -H "X-Tool-Name: warehouse_query_part" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }' | jq .
```

### 測試腳本 2: 完整流程測試

```bash
#!/bin/bash

AI_BOX_URL="http://localhost:8000"
AGENT_ID="warehouse-manager-agent"

echo "1. 檢查 Agent 註冊狀態..."
curl "$AI_BOX_URL/api/v1/agents/$AGENT_ID" | jq .

echo -e "\n2. 測試 Agent 調用..."
curl -X POST "$AI_BOX_URL/api/v1/agents/$AGENT_ID/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_data": {
      "instruction": "查詢料號 ABC-123 的庫存"
    },
    "metadata": {
      "user_id": "test-user",
      "tenant_id": "test-tenant"
    }
  }' | jq .
```

---

## 📚 相關文檔

- [庫管員-Agent-Cloudflare-註冊配置指南](./庫管員-Agent-Cloudflare-註冊配置指南.md) - 完整配置指南
- [庫管員-Agent-規格書](./庫管員-Agent-規格書.md) - Agent 規格說明
- [Cloudflare MCP Gateway 设置指南](../MCP工具/Cloudflare-MCP-Gateway-设置指南.md) - Gateway 詳細設置

---

**版本**: 1.0
**最後更新日期**: 2026-01-14
**維護人**: Daniel Chung
