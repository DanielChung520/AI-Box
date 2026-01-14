# 庫管員 Agent - 522 錯誤排查指南

**創建日期**: 2026-01-14
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-14

---

## 🔍 522 錯誤說明

### 錯誤信息

```bash
curl -X POST https://mcp.k84.org \
  -H "X-Gateway-Secret: ..." \
  -H "X-Tool-Name: warehouse_query_part" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

error code: 522
```

### 錯誤含義

**522 錯誤**是 Cloudflare 的特定錯誤碼，表示 **"Connection timed out"（連接超時）**。

**這意味著**：

- ✅ Cloudflare Gateway 能夠接收請求
- ✅ 路由匹配成功（Gateway 識別了 `warehouse_*` 工具）
- ✅ Gateway 嘗試轉發請求到目標端點
- ❌ **無法連接到目標服務**（`http://localhost:8003/mcp`）

---

## 🎯 根本原因分析

### 問題 1: Cloudflare Workers 無法訪問 localhost

**核心問題**：Cloudflare Workers 運行在 Cloudflare 的**邊緣網絡**（全球分佈的服務器），無法訪問您本地機器上的 `localhost:8003`。

**為什麼會這樣**：

- Cloudflare Workers 不在您的本地網絡中
- `localhost` 或 `127.0.0.1` 在 Workers 環境中指向 Workers 服務器本身，而不是您的機器
- 即使您的機器有公網 IP，`localhost` 也不會被解析為您的機器

### 問題 2: 庫管員 Agent 未運行

即使解決了網絡問題，如果庫管員 Agent 服務沒有運行，也會出現連接錯誤。

---

## ✅ 解決方案

### 方案 1: 使用公網可訪問的端點（推薦）

**適用場景**：庫管員 Agent 部署在公網可訪問的服務器上

**操作步驟**：

1. **確保庫管員 Agent 部署在公網可訪問的服務器**
   - 使用公網 IP 或域名
   - 確保防火牆允許端口 8003 的訪問

2. **更新 Gateway 路由配置**

編輯 `mcp/gateway/wrangler.toml`：

```toml
MCP_ROUTES = '''
[
  {
    "pattern": "yahoo_finance_*",
    "target": "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp"
  },
  {
    "pattern": "warehouse_*",
    "target": "http://YOUR_PUBLIC_IP:8003/mcp"
    # 或使用域名：
    # "target": "https://warehouse-agent.example.com/mcp"
  }
]
'''
```

3. **部署更新**

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
wrangler deploy
```

### 方案 2: 使用內網穿透（開發/測試環境）

**適用場景**：庫管員 Agent 部署在本地或內網，需要臨時暴露到公網

**推薦工具**：

- **Cloudflare Tunnel**（推薦，與 Cloudflare Gateway 集成良好）
- **ngrok**
- **localtunnel**

#### 使用 Cloudflare Tunnel

1. **安裝 Cloudflare Tunnel**

```bash
# macOS
brew install cloudflare/cloudflare/cloudflared

# 或下載二進制文件
# https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
```

2. **創建 Tunnel**

```bash
# 登錄 Cloudflare
cloudflared tunnel login

# 創建 Tunnel
cloudflared tunnel create warehouse-agent-tunnel

# 運行 Tunnel（將本地 8003 端口暴露到公網）
cloudflared tunnel --url http://localhost:8003
```

3. **獲取公網 URL**

Tunnel 會提供一個公網 URL，例如：

```
https://xxxx-xxxx-xxxx.trycloudflare.com
```

4. **更新 Gateway 路由配置**

```toml
{
  "pattern": "warehouse_*",
  "target": "https://xxxx-xxxx-xxxx.trycloudflare.com/mcp"
}
```

5. **部署更新**

```bash
wrangler deploy
```

#### 使用 ngrok

1. **安裝 ngrok**

```bash
# macOS
brew install ngrok/ngrok/ngrok

# 或下載：https://ngrok.com/download
```

2. **啟動 ngrok**

```bash
ngrok http 8003
```

3. **獲取公網 URL**

ngrok 會顯示：

```
Forwarding  https://xxxx-xxxx-xxxx.ngrok.io -> http://localhost:8003
```

4. **更新 Gateway 路由配置**

```toml
{
  "pattern": "warehouse_*",
  "target": "https://xxxx-xxxx-xxxx.ngrok.io/mcp"
}
```

5. **部署更新**

```bash
wrangler deploy
```

### 方案 3: 使用 Cloudflare Tunnel（生產環境推薦）

**適用場景**：生產環境，需要穩定的內網連接

**優勢**：

- 不需要公網 IP
- 不需要開放防火牆端口
- 與 Cloudflare Gateway 集成良好
- 免費且穩定

**操作步驟**：

1. **安裝並配置 Cloudflare Tunnel**

```bash
# 安裝
brew install cloudflare/cloudflare/cloudflared

# 登錄
cloudflared tunnel login

# 創建 Tunnel
cloudflared tunnel create warehouse-agent-tunnel

# 配置 Tunnel（創建配置文件）
cloudflared tunnel route dns warehouse-agent-tunnel warehouse-agent.yourdomain.com
```

2. **創建配置文件** `~/.cloudflared/config.yml`:

```yaml
tunnel: warehouse-agent-tunnel
credentials-file: /Users/daniel/.cloudflared/xxxx-xxxx-xxxx.json

ingress:
  - hostname: warehouse-agent.yourdomain.com
    service: http://localhost:8003
  - service: http_status:404
```

3. **運行 Tunnel**

```bash
cloudflared tunnel run warehouse-agent-tunnel
```

4. **更新 Gateway 路由配置**

```toml
{
  "pattern": "warehouse_*",
  "target": "https://warehouse-agent.yourdomain.com/mcp"
}
```

5. **部署更新**

```bash
wrangler deploy
```

### 方案 4: 直接連接（不通過 Gateway）

**適用場景**：AI-Box 和庫管員 Agent 在同一內網

如果 AI-Box 和庫管員 Agent 都在同一內網，可以不使用 Gateway，直接在 AI-Box 中註冊 Agent 的內網端點。

**操作步驟**：

1. **在 AI-Box 中註冊 Agent**（不使用 Gateway）

```bash
curl -X POST http://localhost:8000/api/v1/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "warehouse-manager-agent",
    "endpoints": {
      "mcp": "http://localhost:8003/mcp",  # 直接使用內網端點
      "protocol": "mcp",
      "is_internal": false
    },
    ...
  }'
```

**注意**：這種方式不經過 Cloudflare Gateway，無法享受 Gateway 的安全、審計等功能。

---

## 🔍 診斷步驟

### 步驟 1: 檢查庫管員 Agent 是否運行

```bash
# 檢查端口是否被占用
lsof -i :8003

# 或檢查進程
ps aux | grep warehouse

# 測試本地連接
curl http://localhost:8003/mcp
```

### 步驟 2: 檢查 Gateway 路由配置

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
cat wrangler.toml | grep -A 10 "warehouse_*"
```

**確認**：

- Pattern 是否正確：`warehouse_*`
- Target 是否可訪問（不是 `localhost`，除非使用內網穿透）

### 步驟 3: 測試目標端點可訪問性

**如果使用公網端點**：

```bash
# 測試公網端點是否可訪問
curl http://YOUR_PUBLIC_IP:8003/mcp

# 或使用域名
curl https://warehouse-agent.example.com/mcp
```

**如果使用內網穿透**：

```bash
# 測試 ngrok URL
curl https://xxxx-xxxx-xxxx.ngrok.io/mcp

# 測試 Cloudflare Tunnel URL
curl https://warehouse-agent.yourdomain.com/mcp
```

### 步驟 4: 檢查 Gateway 日誌

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
wrangler tail mcp-gateway
```

查看日誌中的錯誤信息，可能有更詳細的連接失敗原因。

---

## 📊 錯誤對照表

| 錯誤碼 | 含義 | 可能原因 | 解決方案 |
|--------|------|---------|---------|
| **522** | Connection timed out | Cloudflare 無法連接到目標服務 | 使用公網端點或內網穿透 |
| **521** | Web server is down | 目標服務未運行 | 啟動庫管員 Agent 服務 |
| **526** | Invalid SSL certificate | SSL 證書問題 | 檢查 HTTPS 配置 |
| **404** | Not found | 路由不匹配 | 檢查路由配置 |
| **-32601** | Method not found | 路由匹配失敗 | 檢查工具名稱前綴 |

---

## 🎯 推薦配置（根據環境）

### 開發環境

**推薦**：使用 ngrok 或 Cloudflare Tunnel（臨時）

```toml
{
  "pattern": "warehouse_*",
  "target": "https://xxxx-xxxx-xxxx.ngrok.io/mcp"
}
```

### 測試環境

**推薦**：使用 Cloudflare Tunnel（穩定）

```toml
{
  "pattern": "warehouse_*",
  "target": "https://warehouse-agent-test.yourdomain.com/mcp"
}
```

### 生產環境

**推薦**：使用公網域名 + HTTPS

```toml
{
  "pattern": "warehouse_*",
  "target": "https://warehouse-agent.yourdomain.com/mcp"
}
```

---

## ✅ 快速檢查清單

- [ ] 庫管員 Agent 服務正在運行（端口 8003）
- [ ] Gateway 路由配置中的 `target` 不是 `localhost` 或 `127.0.0.1`
- [ ] 目標端點可以從公網訪問（或使用內網穿透）
- [ ] 如果使用 HTTPS，SSL 證書有效
- [ ] 防火牆允許端口 8003 的訪問（如果使用公網 IP）

---

## 📚 相關文檔

- [庫管員-Agent-Cloudflare-註冊配置指南](./庫管員-Agent-Cloudflare-註冊配置指南.md) - 完整配置指南
- [庫管員-Agent-Cloudflare-測試指南](./庫管員-Agent-Cloudflare-測試指南.md) - 測試方法
- [Cloudflare Tunnel 文檔](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/) - Cloudflare Tunnel 官方文檔

---

**版本**: 1.0
**最後更新日期**: 2026-01-14
**維護人**: Daniel Chung
