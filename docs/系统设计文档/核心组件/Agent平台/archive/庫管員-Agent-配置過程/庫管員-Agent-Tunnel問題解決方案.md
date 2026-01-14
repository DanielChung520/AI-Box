# 庫管員 Agent - Tunnel 問題解決方案

**創建日期**: 2026-01-14
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-14

---

## 🔍 問題診斷

### 當前狀態

| 項目 | 狀態 | 詳情 |
|------|------|------|
| **本地服務** | ✅ 正常 | `http://localhost:8003` 正常運行 |
| **Tunnel 進程** | ✅ 運行中 | PID 32593，進程正常 |
| **Tunnel URL** | ❌ 404 | `https://bands-ratio-consideration-february.trycloudflare.com` 返回 404 |
| **Gateway** | ❌ 522 | 因為 Tunnel 無法訪問，Gateway 返回 timeout |

### 問題分析

**根本原因**: Cloudflare Tunnel 的 quick tunnel 無法正確轉發請求到本地服務。

**可能原因**:

1. Quick tunnel 的連接不穩定
2. 網絡配置問題
3. Quick tunnel 的臨時性限制

---

## 🔧 解決方案

### 方案 1: 使用 ngrok（推薦，快速解決）

ngrok 通常比 Cloudflare Tunnel 的 quick tunnel 更穩定。

#### 步驟 1: 安裝 ngrok

```bash
brew install ngrok/ngrok/ngrok
```

#### 步驟 2: 啟動 ngrok

```bash
ngrok http 8003
```

**輸出示例**:

```
Session Status                online
Account                       Your Account (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Forwarding                    https://xxxx-xxxx-xxxx.ngrok.io -> http://localhost:8003
```

#### 步驟 3: 更新 Gateway 配置

編輯 `mcp/gateway/wrangler.toml`:

```toml
MCP_ROUTES = '''
[
  {
    "pattern": "yahoo_finance_*",
    "target": "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp"
  },
  {
    "pattern": "warehouse_*",
    "target": "https://xxxx-xxxx-xxxx.ngrok.io"
  }
]
'''
```

**注意**: 使用根路徑，因為服務已支持根路徑 MCP 端點。

#### 步驟 4: 部署並測試

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
wrangler deploy

# 測試
curl -X POST https://mcp.k84.org \
  -H "X-Gateway-Secret: ..." \
  -H "X-Tool-Name: warehouse_execute_task" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

---

### 方案 2: 使用 Cloudflare 命名 Tunnel（生產環境推薦）

如果希望繼續使用 Cloudflare Tunnel，建議使用命名 Tunnel（更穩定）。

#### 步驟 1: 創建命名 Tunnel

```bash
cloudflared tunnel create warehouse-agent
```

#### 步驟 2: 配置路由（需要域名）

```bash
cloudflared tunnel route dns warehouse-agent warehouse-agent.yourdomain.com
```

#### 步驟 3: 創建配置文件

創建 `~/.cloudflared/config.yml`:

```yaml
tunnel: warehouse-agent
credentials-file: /Users/daniel/.cloudflared/xxxxx.json

ingress:
  - hostname: warehouse-agent.yourdomain.com
    service: http://localhost:8003
  - service: http_status:404
```

#### 步驟 4: 運行 Tunnel

```bash
cloudflared tunnel run warehouse-agent
```

#### 步驟 5: 更新 Gateway 配置

```toml
{
  "pattern": "warehouse_*",
  "target": "https://warehouse-agent.yourdomain.com"
}
```

---

### 方案 3: 直接部署到公網服務器（長期方案）

如果服務需要長期運行，建議：

1. **部署到公網可訪問的服務器**
2. **使用固定域名和 HTTPS**
3. **更新 Gateway 配置指向公網端點**

---

## 🚀 快速修復（使用 ngrok）

### 完整步驟

```bash
# 1. 安裝 ngrok
brew install ngrok/ngrok/ngrok

# 2. 啟動 ngrok（在新終端）
ngrok http 8003

# 3. 複製 ngrok URL（例如：https://xxxx-xxxx-xxxx.ngrok.io）

# 4. 更新 Gateway 配置
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
# 編輯 wrangler.toml，更新 warehouse_* 的 target

# 5. 部署
wrangler deploy

# 6. 測試
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -H "X-Tool-Name: warehouse_execute_task" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

---

## 📝 注意事項

### ngrok 免費版限制

- 每次啟動 URL 會變化
- 需要每次更新 Gateway 配置
- 有連接數限制

### 解決方案

1. **使用 ngrok 付費版** - 獲得固定域名
2. **使用腳本自動更新** - 自動獲取 URL 並更新配置
3. **使用命名 Tunnel** - 更穩定的長期方案

---

## 🧪 測試清單

完成配置後，請測試：

- [ ] ngrok/Tunnel URL 可以訪問本地服務
- [ ] Gateway 配置已更新
- [ ] Gateway 可以通過 Tunnel/ngrok 訪問服務
- [ ] 工具調用正常

---

## 📚 相關文檔

- [庫管員-Agent-內網穿透設置指南](./庫管員-Agent-內網穿透設置指南.md)
- [庫管員-Agent-配置完成總結](./庫管員-Agent-配置完成總結.md)

---

**版本**: 1.0
**最後更新日期**: 2026-01-14
**維護人**: Daniel Chung
