# 庫管員 Agent - Cloudflare Tunnel 配置問題排查

**創建日期**: 2026-01-14
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-14

---

## 問題描述

通過 Cloudflare Gateway 調用庫管員 Agent 時返回 **522 錯誤**（Connection timed out）。

### 當前配置

- **Gateway URL**: `https://mcp.k84.org` → `https://mcp-gateway.896445070.workers.dev`
- **Gateway 路由**: `warehouse_*` → `https://owns-towers-arbitrary-classic.trycloudflare.com/mcp`
- **Cloudflare Tunnel**: `cloudflared tunnel --url http://localhost:8003`
- **本地服務**: `http://localhost:8003` ✅ 正常運行

---

## 診斷結果

### ✅ 正常的部分

1. **本地服務正常**:

   ```bash
   $ curl http://localhost:8003/health
   {"status":"healthy","agent_status":"available"}

   $ curl -X POST http://localhost:8003/mcp -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
   {"jsonrpc":"2.0","id":1,"result":{"tools":[...]}}
   ```

2. **Cloudflare Tunnel 進程運行中**:

   ```bash
   $ ps aux | grep "cloudflared tunnel"
   daniel  19795  ... cloudflared tunnel --url http://localhost:8003
   ```

3. **Gateway 配置已部署**:
   - 路由規則：`warehouse_*` → `https://owns-towers-arbitrary-classic.trycloudflare.com/mcp`
   - Gateway Secret 配置正確

### ❌ 問題部分

1. **Cloudflare Tunnel 返回 404**:

   ```bash
   $ curl -X POST https://owns-towers-arbitrary-classic.trycloudflare.com/mcp
   HTTP Status: 404
   ```

2. **Gateway 返回 522**:

   ```bash
   $ curl -X POST https://mcp.k84.org -H "X-Tool-Name: warehouse_execute_task" ...
   error code: 522
   ```

---

## 根本原因分析

### 問題 1: Cloudflare Tunnel 路徑轉發

**現象**: Tunnel URL 的 `/mcp` 路徑返回 404

**可能原因**:

1. Cloudflare Tunnel 的 quick tunnel 可能不支持路徑轉發
2. 或者需要配置路徑轉發規則

**驗證步驟**:

```bash
# 測試根路徑
curl https://owns-towers-arbitrary-classic.trycloudflare.com/

# 測試健康檢查端點
curl https://owns-towers-arbitrary-classic.trycloudflare.com/health

# 測試 MCP 端點
curl -X POST https://owns-towers-arbitrary-classic.trycloudflare.com/mcp ...
```

### 問題 2: Gateway 轉發邏輯

根據 Gateway 代碼，`forwardRequest` 方法直接將請求發送到 `targetEndpoint`：

```typescript
const response = await fetch(endpoint, {
  method: 'POST',
  headers: {...},
  body: JSON.stringify(request),
});
```

這意味著：

- 如果 `targetEndpoint = "https://owns-towers-arbitrary-classic.trycloudflare.com/mcp"`
- Gateway 會發送到：`https://owns-towers-arbitrary-classic.trycloudflare.com/mcp`
- 但如果 Tunnel 不支持路徑轉發，會返回 404

---

## 解決方案

### 方案 1: 使用根路徑（如果 Tunnel 支持）

如果 Cloudflare Tunnel 可以轉發到根路徑，可以：

1. **修改 Gateway 配置**，使用根路徑：

   ```toml
   {
     "pattern": "warehouse_*",
     "target": "https://owns-towers-arbitrary-classic.trycloudflare.com"
   }
   ```

2. **修改 Gateway 代碼**，自動附加 `/mcp` 路徑：

   ```typescript
   // 在 forwardRequest 中
   const endpointWithPath = endpoint.endsWith('/mcp')
     ? endpoint
     : `${endpoint}/mcp`;
   ```

### 方案 2: 使用命名 Tunnel（推薦）

使用 Cloudflare Tunnel 的命名配置，支持路徑轉發：

1. **創建命名 Tunnel**:

   ```bash
   cloudflared tunnel create warehouse-agent
   ```

2. **配置路由**:

   ```bash
   cloudflared tunnel route dns warehouse-agent warehouse-agent.yourdomain.com
   ```

3. **配置 config.yml**:

   ```yaml
   tunnel: warehouse-agent
   credentials-file: /path/to/credentials.json

   ingress:
     - hostname: warehouse-agent.yourdomain.com
       service: http://localhost:8003
   ```

4. **運行 Tunnel**:

   ```bash
   cloudflared tunnel run warehouse-agent
   ```

### 方案 3: 修改服務端點（臨時解決）

如果 Tunnel 只支持根路徑轉發，可以：

1. **在 FastAPI 中添加根路徑處理**:

   ```python
   @app.post("/")
   async def handle_mcp_root(request: Request):
       # 轉發到 /mcp
       return await handle_mcp_request(request)
   ```

2. **更新 Gateway 配置**:

   ```toml
   {
     "pattern": "warehouse_*",
     "target": "https://owns-towers-arbitrary-classic.trycloudflare.com"
   }
   ```

---

## 測試步驟

### 步驟 1: 測試 Tunnel 根路徑

```bash
curl -X POST https://owns-towers-arbitrary-classic.trycloudflare.com/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### 步驟 2: 測試健康檢查

```bash
curl https://owns-towers-arbitrary-classic.trycloudflare.com/health
```

### 步驟 3: 測試 Gateway

```bash
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: ..." \
  -H "X-Tool-Name: warehouse_execute_task" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

---

## 當前狀態

| 項目 | 狀態 | 詳情 |
|------|------|------|
| **本地服務** | ✅ 正常 | 端口 8003，`/mcp` 端點正常 |
| **Cloudflare Tunnel** | ⚠️ 部分正常 | 進程運行，但 `/mcp` 路徑返回 404 |
| **Gateway 配置** | ✅ 已部署 | 路由規則已更新 |
| **Gateway 連接** | ❌ 失敗 | 522 錯誤（Tunnel 無法訪問） |

---

## 下一步操作

1. **測試 Tunnel 根路徑** - 確認是否支持根路徑轉發
2. **如果根路徑可用** - 修改 Gateway 配置和代碼，使用根路徑並自動附加 `/mcp`
3. **如果根路徑不可用** - 使用命名 Tunnel 配置，支持路徑轉發
4. **或使用替代方案** - 考慮使用 ngrok 或其他內網穿透工具

---

## 相關文檔

- [庫管員-Agent-服務啟動診斷報告](./庫管員-Agent-服務啟動診斷報告.md)
- [庫管員-Agent-內網穿透設置指南](./庫管員-Agent-內網穿透設置指南.md)
- [Cloudflare Tunnel 官方文檔](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

---

**版本**: 1.0
**最後更新日期**: 2026-01-14
**維護人**: Daniel Chung
