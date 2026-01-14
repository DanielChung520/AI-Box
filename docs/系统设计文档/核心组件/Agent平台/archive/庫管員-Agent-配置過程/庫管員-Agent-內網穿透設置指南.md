# 庫管員 Agent 內網穿透設置指南

**創建日期**: 2026-01-14
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-14

---

## 概述

由於 Cloudflare Gateway 運行在邊緣網絡，無法直接訪問本地 `localhost:8003`，需要使用內網穿透工具將本地服務暴露到公網。

本指南提供兩種方案：

1. **Cloudflare Tunnel**（推薦，已安裝）✅
2. **ngrok**（備選方案）

---

## 方案 1: Cloudflare Tunnel（推薦）

### 優點

- ✅ 已安裝（`cloudflared` 已在系統中）
- ✅ 免費且穩定
- ✅ 由 Cloudflare 提供，與 Gateway 同源
- ✅ 支持持久化配置

### 步驟

#### 1. 啟動 Cloudflare Tunnel

在終端中運行：

```bash
cloudflared tunnel --url http://localhost:8003
```

**輸出示例**:

```
2026-01-14T10:00:00Z INF +--------------------------------------------------------------------------------------------+
2026-01-14T10:00:00Z INF |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):
2026-01-14T10:00:00Z INF |  https://xxxx-xxxx-xxxx.trycloudflare.com
2026-01-14T10:00:00Z INF +--------------------------------------------------------------------------------------------+
2026-01-14T10:00:00Z INF  Starting metrics server
2026-01-14T10:00:00Z INF  Starting tunnel
```

**重要**: 記下 `https://xxxx-xxxx-xxxx.trycloudflare.com` 這個 URL！

#### 2. 更新 Gateway 路由配置

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
    "target": "https://xxxx-xxxx-xxxx.trycloudflare.com/mcp"
  }
]
'''
```

**注意**:

- 將 `xxxx-xxxx-xxxx` 替換為實際的 Cloudflare Tunnel URL
- 確保 URL 末尾包含 `/mcp` 路徑

#### 3. 部署 Gateway 更新

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
wrangler deploy
```

#### 4. 測試

```bash
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: test-tenant" \
  -H "X-Tool-Name: warehouse_execute_task" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

**預期結果**: 應該返回工具列表，而不是 522 錯誤。

---

## 方案 2: ngrok（備選）

### 優點

- ✅ 簡單易用
- ✅ 提供固定域名（付費版）

### 缺點

- ❌ 需要安裝
- ❌ 免費版每次啟動 URL 會變化

### 安裝步驟

#### 1. 安裝 ngrok

使用 Homebrew 安裝：

```bash
brew install ngrok/ngrok/ngrok
```

或從官網下載：

- 訪問 <https://ngrok.com/download>
- 下載 macOS 版本
- 解壓並移動到 `/usr/local/bin/` 或添加到 PATH

#### 2. 註冊並獲取 Authtoken（可選）

```bash
# 訪問 https://dashboard.ngrok.com/get-started/your-authtoken
# 複製 Authtoken，然後運行：
ngrok config add-authtoken YOUR_AUTHTOKEN
```

**注意**: 如果不註冊，也可以直接使用，但每次啟動 URL 會變化。

#### 3. 啟動 ngrok

在終端中運行：

```bash
ngrok http 8003
```

**輸出示例**:

```
Session Status                online
Account                       Your Account (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       45ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://xxxx-xxxx-xxxx.ngrok.io -> http://localhost:8003

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**重要**: 記下 `https://xxxx-xxxx-xxxx.ngrok.io` 這個 URL！

#### 4. 更新 Gateway 路由配置

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
    "target": "https://xxxx-xxxx-xxxx.ngrok.io/mcp"
  }
]
'''
```

#### 5. 部署和測試（同方案 1 的步驟 3-4）

---

## 注意事項

### 1. URL 會變化

**Cloudflare Tunnel（免費版）**:

- 每次啟動 URL 會變化
- 需要每次更新 Gateway 配置

**ngrok（免費版）**:

- 每次啟動 URL 會變化
- 需要每次更新 Gateway 配置

**解決方案**:

- 使用付費版獲得固定域名
- 或使用腳本自動更新配置

### 2. 保持 Tunnel 運行

- **必須保持 Cloudflare Tunnel 或 ngrok 運行**
- 如果關閉終端或停止 Tunnel，Gateway 將無法訪問服務
- 建議使用 `nohup` 或 `screen`/`tmux` 在後台運行

**示例（後台運行）**:

```bash
# Cloudflare Tunnel
nohup cloudflared tunnel --url http://localhost:8003 > cloudflared.log 2>&1 &

# ngrok
nohup ngrok http 8003 > ngrok.log 2>&1 &
```

### 3. 生產環境建議

對於生產環境，建議：

1. 使用 Cloudflare Tunnel 的持久化配置
2. 或將 Agent 部署到公網可訪問的服務器
3. 或使用固定的公網 IP 和域名

---

## 快速開始（推薦使用 Cloudflare Tunnel）

### 步驟 1: 啟動 Tunnel

```bash
cloudflared tunnel --url http://localhost:8003
```

### 步驟 2: 複製 URL

從輸出中複製 `https://xxxx-xxxx-xxxx.trycloudflare.com`

### 步驟 3: 更新配置

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 編輯 wrangler.toml，更新 warehouse_* 的 target
# 然後部署
wrangler deploy
```

### 步驟 4: 測試

```bash
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -H "X-Tool-Name: warehouse_execute_task" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

---

## 故障排除

### 問題 1: Tunnel 無法啟動

**檢查**:

```bash
# 確認服務正在運行
curl http://localhost:8003/health

# 確認端口未被佔用
lsof -i :8003
```

### 問題 2: Gateway 仍然返回 522

**檢查**:

1. Tunnel URL 是否正確（包含 `/mcp` 路徑）
2. Gateway 配置是否已部署
3. Tunnel 是否正在運行

**測試 Tunnel 直接訪問**:

```bash
curl -X POST https://xxxx-xxxx-xxxx.trycloudflare.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

如果直接訪問成功，但通過 Gateway 失敗，檢查 Gateway 配置。

---

## 相關文檔

- [庫管員-Agent-服務啟動診斷報告](./庫管員-Agent-服務啟動診斷報告.md) - 服務啟動問題診斷
- [庫管員-Agent-522錯誤排查指南](./庫管員-Agent-522錯誤排查指南.md) - 522 錯誤詳細說明
- [Cloudflare Tunnel 官方文檔](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

---

**版本**: 1.0
**最後更新日期**: 2026-01-14
**維護人**: Daniel Chung
