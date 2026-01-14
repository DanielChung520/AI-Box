# MCP Gateway 測試指南

**創建日期**: 2026-01-13
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-13

---

## 📋 概述

本文檔說明如何正確測試 MCP Gateway 是否正常運行。

---

## ✅ 配置狀態檢查

### 1. DNS 配置檢查

**測試方法**：訪問 `https://mcp.k84.org`

**預期結果**：

```json
{
  "jsonrpc": "2.0",
  "id": null,
  "error": {
    "code": -32600,
    "message": "Invalid Request: Only POST method is supported",
    "data": {
      "method": "GET"
    }
  }
}
```

**說明**：

- ✅ **這是成功的標誌**！
- ✅ DNS 配置正確（域名指向 Gateway）
- ✅ Gateway 正常運行（能夠接收請求並返回響應）
- ⚠️ 錯誤是因為瀏覽器使用 GET 請求，而 Gateway 只支持 POST 請求

### 2. Gateway 健康檢查

**測試方法**：使用 POST 請求測試

```bash
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -H "X-Tool-Name: test_tool" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

**預期結果**：

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

**說明**：

- ✅ Gateway 正常運行
- ✅ 認證通過（Gateway Secret 正確）
- ⚠️ 錯誤是因為還沒有配置 MCP Server 路由（這是正常的）

---

## 🧪 測試場景

### 場景 1: 測試 GET 請求（瀏覽器訪問）

**操作**：在瀏覽器中訪問 `https://mcp.k84.org`

**預期結果**：

```json
{
  "jsonrpc": "2.0",
  "id": null,
  "error": {
    "code": -32600,
    "message": "Invalid Request: Only POST method is supported",
    "data": {
      "method": "GET"
    }
  }
}
```

**狀態**：✅ **成功** - Gateway 正常運行

### 場景 2: 測試 POST 請求（無認證）

**操作**：

```bash
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

**預期結果**：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32001,
    "message": "Unauthorized: Invalid Gateway Secret"
  }
}
```

**狀態**：✅ **成功** - 認證機制正常工作

### 場景 3: 測試 POST 請求（有認證，無路由）

**操作**：

```bash
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -H "X-Tool-Name: test_tool" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

**預期結果**：

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

**狀態**：✅ **成功** - Gateway 正常運行，認證通過，但沒有配置路由（這是正常的）

### 場景 4: 測試 POST 請求（錯誤的 Gateway Secret）

**操作**：

```bash
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: wrong-secret" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

**預期結果**：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32001,
    "message": "Unauthorized: Invalid Gateway Secret"
  }
}
```

**狀態**：✅ **成功** - 認證機制正常工作，拒絕了錯誤的 Secret

---

## 📊 錯誤代碼說明

### JSON-RPC 錯誤代碼

| 錯誤代碼 | 說明 | 狀態 |
|---------|------|------|
| **-32600** | Invalid Request（無效請求） | ✅ 正常 - 表示 Gateway 正常運行 |
| **-32001** | Unauthorized（未授權） | ✅ 正常 - 認證機制正常工作 |
| **-32601** | Method not found（方法未找到） | ⚠️ 需要配置路由 |
| **-32602** | Invalid params（無效參數） | ✅ 正常 - 參數驗證正常工作 |
| **-32700** | Parse error（解析錯誤） | ✅ 正常 - JSON 解析正常工作 |
| **-32603** | Internal error（內部錯誤） | ❌ 需要檢查 Gateway 日誌 |

### HTTP 狀態碼

| 狀態碼 | 說明 | 狀態 |
|--------|------|------|
| **200** | OK（成功） | ✅ 正常 - JSON-RPC 協議返回 200 |
| **522** | Connection Timeout | ❌ Worker 連接超時（需要檢查 Worker 狀態） |

---

## ✅ 配置成功標誌

### 1. DNS 配置成功

**標誌**：

- ✅ 訪問 `https://mcp.k84.org` 返回 JSON-RPC 錯誤（不是 404 或連接錯誤）
- ✅ 錯誤信息包含 `"Only POST method is supported"`

**測試命令**：

```bash
curl https://mcp.k84.org
# 預期: 返回 JSON-RPC 錯誤（-32600）
```

### 2. Gateway 正常運行

**標誌**：

- ✅ POST 請求返回 JSON-RPC 響應（不是 522 或連接錯誤）
- ✅ 認證機制正常工作（錯誤的 Secret 被拒絕）

**測試命令**：

```bash
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
# 預期: 返回 JSON-RPC 響應（可能是 -32601 路由錯誤，這是正常的）
```

### 3. 認證機制正常

**標誌**：

- ✅ 正確的 Gateway Secret 通過認證
- ✅ 錯誤的 Gateway Secret 被拒絕（返回 -32001）

**測試命令**：

```bash
# 測試錯誤的 Secret
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: wrong-secret" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
# 預期: 返回 -32001 Unauthorized
```

---

## 🔧 下一步配置

### 1. 配置 MCP Server 路由

**操作**：在 `wrangler.toml` 中配置 `MCP_ROUTES`

```toml
MCP_ROUTES = '''
[
  {
    "pattern": "warehouse_*",
    "target": "http://your-warehouse-agent:8003/mcp"
  },
  {
    "pattern": "data_*",
    "target": "http://your-data-agent:8004/mcp"
  }
]
'''
```

**部署**：

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
wrangler deploy
```

### 2. 配置 Agent 認證信息

**操作**：在 KV 中存儲 Agent 認證配置

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 配置 Warehouse Agent 認證
wrangler kv key put "auth:warehouse_query_stock" \
  '{"type":"none"}' \
  --namespace-id=5b6e229c21f649269e93db9dcb8a7e16
```

### 3. 配置用戶權限

**操作**：在 KV 中存儲用戶權限配置

```bash
wrangler kv key put "permissions:tenant-1:user-1" \
  '{"tools":["warehouse_*","data_*"],"rate_limits":{"default":100}}' \
  --namespace-id=75e2e224e5844e1ea7639094b87d1001
```

---

## 📝 測試檢查清單

### 基礎配置檢查

- [x] DNS 配置成功（`mcp.k84.org` 指向 Gateway）
- [x] Gateway Worker 已部署
- [x] Gateway Secret 已設置
- [x] KV 命名空間已創建

### 功能測試

- [x] GET 請求返回正確錯誤（-32600）
- [x] POST 請求無認證被拒絕（-32001）
- [x] POST 請求錯誤 Secret 被拒絕（-32001）
- [x] POST 請求正確 Secret 通過認證
- [ ] MCP Server 路由配置（待配置）
- [ ] Agent 認證配置（待配置）
- [ ] 用戶權限配置（待配置）

---

## 🎯 總結

### 當前狀態

✅ **DNS 配置成功**：

- `mcp.k84.org` 正確指向 `mcp-gateway.896445070.workers.dev`
- 訪問域名返回 JSON-RPC 錯誤（表示 Gateway 正常運行）

✅ **Gateway 正常運行**：

- Worker 已部署並正常運行
- 認證機制正常工作
- 請求處理正常

⚠️ **待配置**：

- MCP Server 路由配置
- Agent 認證配置
- 用戶權限配置

### 重要說明

**瀏覽器訪問返回錯誤是正常的**：

- Gateway 只支持 POST 請求（JSON-RPC 協議）
- 瀏覽器使用 GET 請求，所以返回錯誤
- 這表示 Gateway **正常運行**，不是配置錯誤

**正確的測試方法**：

- 使用 `curl` 或 Postman 發送 POST 請求
- 必須包含 `X-Gateway-Secret` 頭部
- 必須使用 JSON-RPC 格式

---

**版本**: 1.0
**最後更新日期**: 2026-01-13
**維護人**: Daniel Chung
