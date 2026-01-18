# Agent/工具 - Cloudflare MCP Gateway 註冊指南

**創建日期**: 2026-01-14
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-15 09:16 UTC+8

---

## 📋 概述

本文檔提供**通用指南**，說明如何將新的 **Agent** 或 **MCP 工具**註冊到 **Cloudflare MCP Gateway**，使其能夠通過 Gateway 與 AI-Box 系統通信。

### 重要更新（2026-01-15）

✅ **Cloudflare MCP Gateway 已正式上線並完成配置**

**正確的 Gateway 端點**：

- ⭐ **Workers.dev URL**（推薦）: `https://mcp-gateway.896445070.workers.dev`
- 自定義域名: `https://mcp.k84.org`

**認證配置**：

- **Gateway Secret**: `0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e`
- Header: `X-Gateway-Secret`
- 環境變數: `MCP_GATEWAY_SECRET`（AI-Box 後端）

**協議要求**：

- ✅ 使用 JSON-RPC 2.0 協議
- ✅ 調用根路徑 `/`（不是 `/execute` 或其他路徑）
- ✅ 方法: `tools/list`（列出工具）、`tools/call`（調用工具）

### 適用對象

- ✅ 新開發的 Agent（如庫管員 Agent、財務 Agent 等）
- ✅ 新集成的第三方 MCP 工具（如 Office 365、Slack 等）
- ✅ 需要通過 Gateway 進行安全隔離的外部服務

### 為什麼需要通過 Cloudflare Gateway？

1. **統一入口**: 所有外部 MCP 服務通過單一 Gateway 訪問
2. **安全隔離**: Gateway 作為安全層，保護內部服務和 Agent
3. **認證管理**: 集中管理 Gateway 認證（X-Gateway-Secret）
4. **權限控制**: 基於租戶和用戶的細粒度權限管理
5. **審計日誌**: 統一記錄所有 MCP 調用日誌
6. **速率限制**: 防止 API 濫用
7. **故障隔離**: Agent 故障不會直接影響 AI-Box 核心系統
8. **動態路由**: 根據工具名稱前綴自動路由到對應的 Agent

### 架構說明

```
┌─────────────────────────────────────────────────────────────────┐
│  AI-Box（AI 操作系統）                                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Chat API (api/routers/chat.py)                           │   │
│  │  - 接收前端聊天請求                                        │   │
│  │  - 調用 Task Analyzer 進行意圖分析                         │   │
│  │  - 從 Agent Registry 獲取 Agent 端點配置                  │   │
│  │  - 構建 JSON-RPC 2.0 請求                                  │   │
│  │  - 添加認證 Headers (X-Gateway-Secret, X-User-ID 等)     │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Agent Registry                                            │   │
│  │  - agent_display_configs (ArangoDB): 外部 Agent 配置      │   │
│  │  - system_agent_registry (ArangoDB): 內部 Agent 配置      │   │
│  │  - system_configs (ArangoDB): 系統參數                    │   │
│  │    → scope: mcp_gateway                                   │   │
│  │    → default_endpoint: https://mcp-gateway...workers.dev  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                        ↓ JSON-RPC 2.0 over HTTPS
                        ↓ Headers: X-Gateway-Secret, X-User-ID,
                        ↓          X-Tenant-ID, X-Tool-Name
┌─────────────────────────────────────────────────────────────────┐
│  Cloudflare MCP Gateway (Workers)                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  1. Gateway Secret 驗證 (X-Gateway-Secret)               │   │
│  │  2. 權限檢查 (KV Store: PERMISSIONS_STORE)               │   │
│  │     - Key: permissions:{tenant_id}:{user_id}             │   │
│  │     - 檢查用戶是否有權訪問 {tool_name}                   │   │
│  │  3. 速率限制 (Rate Limiting)                              │   │
│  │  4. 路由規則匹配 (wrangler.toml: MCP_ROUTES)             │   │
│  │     - Pattern: {tool_prefix}_* → Target URL              │   │
│  │  5. 請求轉發到目標 Agent                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                        ↓ HTTP/HTTPS
┌─────────────────────────────────────────────────────────────────┐
│  外部 Agent/MCP Server                                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  MCP Server (例如：Warehouse Manager Agent)              │   │
│  │  - 端點: http://localhost:8003 或 https://ngrok-url      │   │
│  │  - 接收來自 Cloudflare Gateway 的 JSON-RPC 請求          │   │
│  │  - 方法: tools/list, tools/call                           │   │
│  │  - 處理業務邏輯並返回結果                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 關鍵認證流程

1. **AI-Box → Gateway**：
   - Header: `X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e`
   - Header: `X-User-ID: {user_id}`
   - Header: `X-Tenant-ID: {tenant_id}`
   - Header: `X-Tool-Name: {tool_name}`

2. **Gateway 驗證**：
   - 檢查 `X-Gateway-Secret` 是否正確
   - 查詢 `PERMISSIONS_STORE` 檢查權限
   - 如果驗證失敗，返回 `401 Unauthorized` 或 `403 Forbidden`

3. **Gateway → Agent**：
   - 轉發 JSON-RPC 請求到 Agent
   - 可能添加額外的認證信息（如 API Key）

---

## 🚀 快速開始

### 註冊流程概覽

1. **準備 Agent/MCP 服務** - 確保服務正常運行並提供 MCP 端點
2. **配置內網穿透**（如需要）- 使用 ngrok 或 Cloudflare Tunnel 暴露本地服務
3. **配置 Cloudflare Gateway 路由** - 添加路由規則
4. **配置 Gateway 認證**（如需要）- 設置 API Key 或其他認證方式
5. **配置 Gateway 權限** - 設置用戶/租戶權限
6. **在 AI-Box 中註冊 Agent** - 端點指向 Cloudflare Gateway
7. **管理員核准** - 將 Agent 狀態從 `registering` 轉為 `online`
8. **驗證配置** - 測試 Agent 調用

---

## 📝 步驟 1: 準備 Agent/MCP 服務

### 1.1 確認服務運行狀態

**檢查清單**:

- [ ] Agent/MCP 服務已啟動並正常運行
- [ ] MCP 端點可訪問（如 `http://localhost:PORT/mcp`）
- [ ] 工具已正確註冊（使用 `tools/list` 方法驗證）
- [ ] 健康檢查端點正常（如 `/health`）

**測試命令**:

```bash
# 健康檢查
curl http://localhost:PORT/health

# 測試 MCP 端點
curl -X POST http://localhost:PORT/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### 1.2 工具命名規範

**重要**: 工具名稱必須遵循命名規範，以便 Gateway 路由匹配。

**命名規則**:

- ✅ **使用前綴**: 工具名稱應以 `{agent_name}_` 或 `{tool_category}_` 開頭
- ✅ **使用下劃線**: 使用下劃線分隔單詞（如 `warehouse_query_part`）
- ✅ **小寫字母**: 全部使用小寫字母
- ✅ **描述性**: 名稱應清晰描述工具功能

**範例**:

| Agent/工具 | 工具名稱前綴 | 範例工具名稱 |
|-----------|------------|------------|
| 庫管員 Agent | `warehouse_` | `warehouse_execute_task`, `warehouse_query_part` |
| 財務 Agent | `finance_` | `finance_get_quote`, `finance_get_balance` |
| Office 365 | `office_` | `office_create_document`, `office_send_email` |
| Slack | `slack_` | `slack_send_message`, `slack_list_channels` |

**❌ 錯誤範例**:

- `QueryPart` - 缺少前綴，不符合規範
- `warehouse-query-part` - 使用連字符而非下劃線
- `Warehouse_Query_Part` - 使用大寫字母

---

## 🌐 步驟 2: 配置內網穿透（如需要）

### 2.1 判斷是否需要內網穿透

**需要內網穿透的情況**:

- ✅ Agent 部署在本地開發環境（`localhost`）
- ✅ Agent 部署在內網（私有 IP，如 `192.168.x.x`）
- ✅ Agent 沒有公網 IP 或域名

**不需要內網穿透的情況**:

- ✅ Agent 已部署在公網（有公網域名，如 `https://agent.example.com`）
- ✅ Agent 已部署在雲服務（AWS、Azure、GCP 等，有公網端點）

### 2.2 使用 ngrok（推薦用於開發/測試）

**步驟 1: 註冊 ngrok 帳號**

1. 訪問: <https://dashboard.ngrok.com/signup>
2. 註冊免費帳號（使用 GitHub、Google 或 Email）

**步驟 2: 獲取 Authtoken**

1. 登錄後訪問: <https://dashboard.ngrok.com/get-started/your-authtoken>
2. 複製 authtoken

**步驟 3: 配置 Authtoken**

```bash
ngrok config add-authtoken YOUR_AUTHTOKEN
```

**步驟 4: 啟動 ngrok**

```bash
# 暴露本地服務端口
ngrok http 8003

# 或指定域名（付費版）
ngrok http 8003 --domain=your-fixed-domain.ngrok.io
```

**步驟 5: 獲取 ngrok URL**

ngrok 會顯示類似以下的 URL：

```
Forwarding  https://xxxxx.ngrok-free.app -> http://localhost:8003
```

**⚠️ 注意事項**:

- 免費版每次重啟會生成新的 URL，需要更新 Gateway 配置
- 建議生產環境使用 ngrok 付費版獲得固定域名
- 可以使用 `nohup` 後台運行: `nohup ngrok http 8003 > ngrok.log 2>&1 &`

### 2.3 使用 Cloudflare Tunnel（推薦用於生產環境）

**步驟 1: 安裝 cloudflared**

```bash
# macOS
brew install cloudflared

# Linux
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
```

**步驟 2: 登錄 Cloudflare**

```bash
cloudflared tunnel login
```

**步驟 3: 創建 Tunnel**

```bash
cloudflared tunnel create agent-tunnel
```

**步驟 4: 配置路由**

編輯配置文件（通常在 `~/.cloudflared/config.yml`）:

```yaml
tunnel: agent-tunnel-id
credentials-file: /path/to/credentials.json

ingress:
  - hostname: agent.yourdomain.com
    service: http://localhost:8003
  - service: http_status:404
```

**步驟 5: 運行 Tunnel**

```bash
cloudflared tunnel run agent-tunnel
```

---

## 🔧 步驟 3: 配置 Cloudflare Gateway 路由

### 3.1 更新 wrangler.toml

**文件位置**: `mcp/gateway/wrangler.toml`

**操作步驟**:

1. 編輯 `wrangler.toml` 文件
2. 在 `MCP_ROUTES` 中添加新的路由規則

**配置範例**:

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
  },
  {
    "pattern": "finance_*",
    "target": "https://finance-agent.example.com/mcp"
  },
  {
    "pattern": "office_*",
    "target": "https://office-mcp.example.com/mcp"
  }
]
'''
```

**配置說明**:

- **Pattern**: 工具名稱匹配模式，使用通配符 `*` 匹配所有以該前綴開頭的工具
- **Target**: Agent/MCP Server 的實際端點 URL
  - 本地開發（通過 ngrok）: `https://xxxxx.ngrok-free.app`
  - 內網部署（通過 Tunnel）: `https://agent.yourdomain.com`
  - 公網部署: `https://agent.example.com/mcp`

**⚠️ 重要注意事項**:

1. **Pattern 必須唯一**: 確保不同 Agent 的工具前綴不重疊
2. **Target 必須可訪問**: 確保 Cloudflare Gateway 能夠訪問該 URL
3. **使用 HTTPS**: 生產環境建議使用 HTTPS
4. **端點路徑**: 確認 MCP 端點路徑（通常是 `/mcp` 或 `/`）

### 3.2 部署更新

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
wrangler deploy
```

**驗證部署**:

```bash
# 檢查部署狀態
wrangler deployments list

# 查看日誌
wrangler tail mcp-gateway
```

---

## 🔐 步驟 4: 配置 Cloudflare Gateway 認證（可選）

### 4.1 認證類型選擇

根據 Agent/MCP Server 的認證需求，選擇合適的認證類型：

| 認證類型 | 適用場景 | 配置複雜度 |
|---------|---------|-----------|
| **無認證** | 開發/測試環境，公開服務 | ⭐ 簡單 |
| **API Key** | 簡單的 API 認證 | ⭐⭐ 中等 |
| **Bearer Token** | OAuth 2.0 或 JWT Token | ⭐⭐⭐ 複雜 |
| **OAuth 2.0** | 需要動態獲取 Token | ⭐⭐⭐⭐ 很複雜 |

### 4.2 無認證配置（開發/測試環境）

**適用場景**: Agent 不需要認證，或僅在開發/測試環境使用

**配置命令**:

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 為每個工具配置無認證
wrangler kv key put "auth:{tool_name}" \
  '{"type":"none"}' \
  --binding=AUTH_STORE --preview=false --remote
```

**範例**:

```bash
# 配置 warehouse_execute_task 無認證
wrangler kv key put "auth:warehouse_execute_task" \
  '{"type":"none"}' \
  --binding=AUTH_STORE --preview=false --remote

# 配置 finance_get_quote 無認證
wrangler kv key put "auth:finance_get_quote" \
  '{"type":"none"}' \
  --binding=AUTH_STORE --preview=false --remote
```

### 4.3 API Key 認證配置

**適用場景**: Agent 使用簡單的 API Key 認證

**步驟 1: 設置 API Key Secret**

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 設置 API Key（會提示輸入值）
wrangler secret put {AGENT_NAME}_API_KEY
# 輸入 API Key 值
```

**步驟 2: 配置認證**

```bash
# 配置 API Key 認證
wrangler kv key put "auth:{tool_name}" \
  '{"type":"api_key","api_key":"${AGENT_NAME}_API_KEY","header_name":"X-API-Key"}' \
  --binding=AUTH_STORE --preview=false --remote
```

**範例**:

```bash
# 1. 設置 Secret
wrangler secret put FINANCE_AGENT_API_KEY
# 輸入: your-api-key-here

# 2. 配置認證
wrangler kv key put "auth:finance_get_quote" \
  '{"type":"api_key","api_key":"${FINANCE_AGENT_API_KEY}","header_name":"X-API-Key"}' \
  --binding=AUTH_STORE --preview=false --remote
```

### 4.4 Bearer Token 認證配置

**適用場景**: Agent 使用 Bearer Token 認證（OAuth 2.0 或 JWT）

**步驟 1: 設置 Token Secret**

```bash
wrangler secret put {AGENT_NAME}_TOKEN
# 輸入 Token 值
```

**步驟 2: 配置認證**

```bash
wrangler kv key put "auth:{tool_name}" \
  '{"type":"bearer","token":"${AGENT_NAME}_TOKEN"}' \
  --binding=AUTH_STORE --preview=false --remote
```

**範例**:

```bash
# 1. 設置 Secret
wrangler secret put OFFICE_365_TOKEN
# 輸入: your-bearer-token-here

# 2. 配置認證
wrangler kv key put "auth:office_create_document" \
  '{"type":"bearer","token":"${OFFICE_365_TOKEN}"}' \
  --binding=AUTH_STORE --preview=false --remote
```

### 4.5 OAuth 2.0 認證配置（高級）

**適用場景**: Agent 需要動態獲取 OAuth 2.0 Access Token

**配置範例**:

```bash
wrangler kv key put "auth:slack_send_message" \
  '{
    "type":"oauth2",
    "client_id":"${SLACK_CLIENT_ID}",
    "client_secret":"${SLACK_CLIENT_SECRET}",
    "token_url":"https://slack.com/api/oauth.v2.access",
    "scope":"chat:write"
  }' \
  --binding=AUTH_STORE --preview=false --remote
```

**注意**: OAuth 2.0 配置需要 Gateway 代碼支持動態 Token 獲取和刷新。

### 4.6 驗證認證配置

```bash
# 檢查認證配置
wrangler kv key get "auth:{tool_name}" \
  --binding=AUTH_STORE --preview=false --remote
```

---

## 🔒 步驟 5: 配置 Gateway 權限

### 5.1 權限配置說明

Gateway 支持基於租戶和用戶的權限控制，可以限制哪些用戶/租戶可以訪問哪些工具。

### 5.2 配置租戶默認權限

**配置命令**:

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 配置租戶默認權限（允許所有用戶訪問）
wrangler kv key put "permissions:{tenant_id}:default" \
  '{"tools":["{tool_prefix}_*"]}' \
  --binding=PERMISSIONS_STORE --preview=false --remote
```

**範例**:

```bash
# 允許 test-tenant 租戶的所有用戶訪問 warehouse_* 工具
wrangler kv key put "permissions:test-tenant:default" \
  '{"tools":["warehouse_*"]}' \
  --binding=PERMISSIONS_STORE --preview=false --remote

# 允許 finance-tenant 租戶的所有用戶訪問 finance_* 工具
wrangler kv key put "permissions:finance-tenant:default" \
  '{"tools":["finance_*"]}' \
  --binding=PERMISSIONS_STORE --preview=false --remote
```

### 5.3 配置用戶特定權限

**配置命令**:

```bash
# 配置特定用戶的權限
wrangler kv key put "permissions:{tenant_id}:{user_id}" \
  '{"tools":["{tool_prefix}_*"],"rate_limits":{"default":100}}' \
  --binding=PERMISSIONS_STORE --preview=false --remote
```

**範例**:

```bash
# 允許 user-123 訪問 warehouse_* 和 finance_* 工具，速率限制 100 次/分鐘
wrangler kv key put "permissions:test-tenant:user-123" \
  '{"tools":["warehouse_*","finance_*"],"rate_limits":{"default":100}}' \
  --binding=PERMISSIONS_STORE --preview=false --remote
```

### 5.4 驗證權限配置

```bash
# 檢查權限配置
wrangler kv key get "permissions:{tenant_id}:default" \
  --binding=PERMISSIONS_STORE --preview=false --remote
```

---

## 📝 步驟 6: 在 AI-Box 中註冊 Agent

### 6.1 獲取 Secret ID 和 Secret Key

**操作步驟**:

```bash
# 生成新的 Secret ID/Key 對
curl -X POST http://localhost:8000/api/v1/agents/secrets/generate \
  -H "Content-Type: application/json"
```

**響應範例**:

```json
{
  "success": true,
  "data": {
    "secret_id": "aibox-{agent-name}-1234567890-abc123",
    "secret_key": "sk_live_<YOUR_SECRET_KEY_HERE>",
    "expires_at": null
  },
  "message": "Secret generated successfully"
}
```

**⚠️ 重要**: 保存 `secret_id` 和 `secret_key`，後續註冊需要使用。

### 6.2 驗證 Secret

```bash
curl -X POST http://localhost:8000/api/v1/agents/secrets/verify \
  -H "Content-Type: application/json" \
  -d '{
    "secret_id": "aibox-{agent-name}-1234567890-abc123",
    "secret_key": "sk_live_<YOUR_SECRET_KEY_HERE>"
  }'
```

**預期響應**:

```json
{
  "success": true,
  "data": {
    "valid": true,
    "is_bound": false,
    "status": "active"
  },
  "message": "Secret verified successfully"
}
```

### 6.3 註冊 Agent（端點指向 Cloudflare Gateway）

**關鍵配置**: MCP 端點指向 Cloudflare Gateway，而不是直接指向 Agent。

**方式一：通過前端界面註冊（推薦）**

1. **打開 Agent 註冊界面**
   - 在 AI-Box 前端界面點擊「註冊新 Agent」按鈕

2. **填寫基本資訊**
   - **Agent 名稱**: `{Agent 名稱}`（如 `財務 Agent`、`Office 365 Agent`）
   - **Agent 類型**: 選擇 `Execution (執行)`
   - **描述**: 描述 Agent 的功能和用途
   - **能力列表**: 列出 Agent 提供的工具（如 `finance_get_quote`, `office_create_document`）
   - **圖標**: 選擇合適的圖標

3. **配置端點（關鍵步驟）**
   - **取消勾選**「內部 Agent」
   - **協議類型**: 選擇 `MCP (Model Context Protocol)`
   - **MCP 端點 URL**: ⭐ **指向 Cloudflare Gateway**
     - **推薦**: `https://mcp-gateway.896445070.workers.dev`
     - 或使用自定義域名: `https://mcp.k84.org`
   - **⚠️ 重要**:
     - 不要直接指向 Agent 的實際端點（如 `http://localhost:8003`）
     - 必須指向 Cloudflare Gateway
     - Gateway 會根據工具名稱前綴自動路由到對應的 Agent

4. **Secret 身份驗證**
   - 輸入從 AI-Box 獲取的 `Secret ID`
   - 輸入對應的 `Secret Key`
   - 點擊「驗證 Secret」按鈕

5. **提交註冊**
   - 檢查所有必填項是否已填寫
   - 點擊「註冊 Agent」按鈕

**方式二：通過 API 註冊**

```bash
curl -X POST http://localhost:8000/api/v1/agent-display-configs/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {your_token}" \
  -d '{
    "id": "{agent-id}",
    "names": {
      "en": "{Agent Name}",
      "zh_CN": "{Agent 名称}",
      "zh_TW": "{Agent 名稱}"
    },
    "description": {
      "en": "{Agent Description}",
      "zh_CN": "{Agent 描述}",
      "zh_TW": "{Agent 描述}"
    },
    "icon": "{icon_name}",
    "agent_type": "execution",
    "protocol": "mcp",
    "endpoint_url": "https://mcp-gateway.896445070.workers.dev",
    "secret_id": "{secret_id}",
    "secret_key": "{secret_key}",
    "capabilities": [
      "{tool_name_1}",
      "{tool_name_2}"
    ],
    "is_enabled": true,
    "display_order": 1
  }'
```

**關鍵配置說明**:

- **`endpoint_url`**: `https://mcp-gateway.896445070.workers.dev` - **必須**指向 Cloudflare Gateway
- **`protocol`**: `mcp` - 使用 MCP 協議
- **`agent_type`**: `execution` - Agent 類型（execution/planning/review）
- **`secret_id`** 和 **`secret_key`**: 用於外部 Agent 身份驗證（從 AI-Box 獲取）
- **`capabilities`**: 列出所有工具名稱（必須以配置的前綴開頭，如 `warehouse_*`）

**雙存儲機制**：

API 會自動將配置同時保存到：

1. **agent_display_configs** (ArangoDB) - 用於前端展示
2. **Agent Registry** (In-Memory + ArangoDB) - 用於後端調用

---

## ✅ 步驟 7: 管理員核准

### 7.1 檢查 Agent 註冊狀態

```bash
curl http://localhost:8000/api/v1/agents/{agent-id}
```

**預期響應**:

```json
{
  "success": true,
  "data": {
    "agent_id": "{agent-id}",
    "name": "{Agent 名稱}",
    "status": "registering",
    "is_internal": false,
    "protocol": "mcp",
    "endpoints": {
      "mcp": "https://mcp.k84.org",
      "protocol": "mcp",
      "is_internal": false
    }
  }
}
```

### 7.2 管理員核准

```bash
curl -X POST "http://localhost:8000/api/v1/agents/{agent-id}/approve?approved=true" \
  -H "Content-Type: application/json"
```

### 7.3 驗證 Agent 可用性

核准後，Agent 狀態應為 `online`：

```bash
curl http://localhost:8000/api/v1/agents/{agent-id}
```

**期望響應**:

```json
{
  "success": true,
  "data": {
    "agent_id": "{agent-id}",
    "status": "online",
    ...
  }
}
```

---

## 🧪 步驟 8: 驗證配置

### 8.1 測試 Cloudflare Gateway 連接

**測試命令**:

```bash
curl -X POST https://mcp-gateway.896445070.workers.dev \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: default" \
  -H "X-Tool-Name: warehouse_execute_task" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

**預期結果**:

- ✅ **成功**: 返回 JSON-RPC 響應，包含工具列表

  ```json
  {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
      "tools": [
        {
          "name": "warehouse_execute_task",
          "description": "...",
          "inputSchema": {...}
        }
      ]
    }
  }
  ```

- ❌ **失敗**: 返回錯誤信息
  - `401 Unauthorized`: Gateway Secret 錯誤
  - `403 Forbidden` / `Unauthorized: No permission`: 權限不足
  - `404 Not Found` / `Method not found`: 路由配置錯誤

### 8.2 測試工具調用

**測試命令**:

```bash
curl -X POST https://mcp-gateway.896445070.workers.dev \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: 0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" \
  -H "X-User-ID: test-user" \
  -H "X-Tenant-ID: default" \
  -H "X-Tool-Name: warehouse_execute_task" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "warehouse_execute_task",
      "arguments": {
        "task_data": {
          "instruction": "列出所有庫存料號"
        },
        "metadata": {
          "user_id": "test-user",
          "tenant_id": "default"
        }
      }
    }
  }'
```

**預期結果**:

- ✅ **成功**: 返回 Agent 執行結果

  ```json
  {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
      "content": [
        {
          "type": "text",
          "text": "{\"task_id\":\"...\",\"status\":\"success\",\"result\":{...}}"
        }
      ]
    }
  }
  ```

- ❌ **失敗**: 返回錯誤信息
  - Agent 執行失敗: `result.content[0].text` 中包含 `"status": "failed"`
  - 參數錯誤: 檢查 `arguments` 格式是否符合 Agent 的 `inputSchema`

### 8.3 通過 AI-Box 測試

在 AI-Box 前端界面中：

1. 選擇已註冊的 Agent
2. 嘗試調用 Agent 提供的工具
3. 檢查響應是否正常

---

## 📊 配置檢查清單

### Cloudflare Gateway 配置

- [ ] `wrangler.toml` 中已添加 `{tool_prefix}_*` 路由規則
- [ ] Gateway 已部署更新
- [ ] 認證配置已設置（如需要）
- [ ] 權限配置已設置（如需要）
- [ ] 路由測試通過

### 內網穿透配置（如需要）

- [ ] ngrok/Cloudflare Tunnel 已配置並運行
- [ ] 公網 URL 可訪問
- [ ] Gateway 路由已更新為公網 URL

### Agent/MCP Server 配置

- [ ] Agent 服務已啟動並正常運行
- [ ] MCP 端點已配置
- [ ] 工具已註冊（工具名稱符合命名規範）
- [ ] 健康檢查通過

### AI-Box Agent 註冊

- [ ] Secret ID/Key 已生成並驗證
- [ ] Agent 已註冊（端點指向 Cloudflare Gateway）
- [ ] Agent 狀態為 `online`
- [ ] 工具調用測試通過

---

## ⚠️ 注意事項

### 1. 工具命名規範

**必須遵循**:

- ✅ 工具名稱必須以 `{prefix}_` 開頭
- ✅ 使用下劃線分隔單詞
- ✅ 全部使用小寫字母
- ✅ 前綴必須唯一，不與其他 Agent 重疊

**範例**:

```python
# ✅ 正確
warehouse_execute_task
finance_get_quote
office_create_document

# ❌ 錯誤
execute_task  # 缺少前綴
warehouse-execute-task  # 使用連字符
Warehouse_Execute_Task  # 使用大寫字母
```

### 2. 路由配置注意事項

- ⚠️ **Pattern 必須唯一**: 確保不同 Agent 的工具前綴不重疊
- ⚠️ **Target 必須可訪問**: 確保 Cloudflare Gateway 能夠訪問該 URL
- ⚠️ **使用 HTTPS**: 生產環境建議使用 HTTPS
- ⚠️ **端點路徑**: 確認 MCP 端點路徑（通常是 `/mcp` 或 `/`）

### 3. 認證配置注意事項

- ⚠️ **生產環境必須配置認證**: 不要使用無認證配置
- ⚠️ **Secret 安全**: 不要將 Secret 提交到代碼倉庫
- ⚠️ **Token 過期**: 如果使用 Bearer Token，注意 Token 過期時間

### 4. ngrok 注意事項

- ⚠️ **免費版 URL 會變化**: 每次重啟會生成新的 URL，需要更新 Gateway 配置
- ⚠️ **建議使用付費版**: 生產環境建議使用 ngrok 付費版獲得固定域名
- ⚠️ **連接限制**: 免費版可能有連接限制

### 5. AI-Box 註冊注意事項

- ⚠️ **端點指向 Gateway**: 不要直接指向 Agent 端點，而是指向 Cloudflare Gateway
- ⚠️ **工具名稱匹配**: 確保註冊的工具名稱與 Gateway 路由規則匹配
- ⚠️ **Secret 驗證**: 必須先驗證 Secret 才能註冊

---

## 🔍 疑難排除

### 問題 1: Gateway 路由不匹配

**症狀**: 請求返回 `Method not found` 或 `404`

**可能原因**:

1. 工具名稱前綴與路由規則不匹配
2. 路由規則未正確配置
3. Gateway 未部署更新

**解決方法**:

1. **檢查工具名稱前綴**:

   ```bash
   # 確認工具名稱
   curl -X POST http://localhost:PORT/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
   ```

2. **檢查路由配置**:

   ```bash
   # 查看 wrangler.toml
   cat mcp/gateway/wrangler.toml | grep -A 10 "MCP_ROUTES"
   ```

3. **重新部署 Gateway**:

   ```bash
   cd mcp/gateway
   wrangler deploy
   ```

### 問題 2: 認證失敗

**症狀**: 請求返回 `401 Unauthorized`

**可能原因**:

1. 認證配置不正確
2. API Key/Token 錯誤
3. Secret 未正確設置

**解決方法**:

1. **檢查認證配置**:

   ```bash
   wrangler kv key get "auth:{tool_name}" \
     --binding=AUTH_STORE --preview=false --remote
   ```

2. **檢查 Secret 設置**:

   ```bash
   # 注意：無法直接查看 Secret 值，只能確認是否設置
   wrangler secret list
   ```

3. **重新配置認證**:

   ```bash
   # 重新設置 Secret
   wrangler secret put {AGENT_NAME}_API_KEY

   # 重新配置認證
   wrangler kv key put "auth:{tool_name}" \
     '{"type":"api_key","api_key":"${AGENT_NAME}_API_KEY","header_name":"X-API-Key"}' \
     --binding=AUTH_STORE --preview=false --remote
   ```

### 問題 3: 權限被拒絕

**症狀**: 請求返回 `403 Forbidden` 或 `Unauthorized: No permission`

**可能原因**:

1. 用戶/租戶沒有訪問權限
2. 權限配置不正確

**解決方法**:

1. **檢查權限配置**:

   ```bash
   wrangler kv key get "permissions:{tenant_id}:{user_id}" \
     --binding=PERMISSIONS_STORE --preview=false --remote
   ```

2. **配置權限**:

   ```bash
   wrangler kv key put "permissions:{tenant_id}:default" \
     '{"tools":["{tool_prefix}_*"]}' \
     --binding=PERMISSIONS_STORE --preview=false --remote
   ```

### 問題 4: ngrok URL 變化

**症狀**: Gateway 無法連接到 Agent（502 Bad Gateway）

**可能原因**:

1. ngrok 重啟後 URL 變化
2. Gateway 配置未更新

**解決方法**:

1. **獲取新的 ngrok URL**:

   ```bash
   # 查看 ngrok Web UI
   open http://localhost:4040
   # 或查看 ngrok 終端輸出
   ```

2. **更新 Gateway 配置**:

   ```bash
   # 編輯 wrangler.toml
   # 更新 MCP_ROUTES 中的 target URL

   # 重新部署
   cd mcp/gateway
   wrangler deploy
   ```

3. **使用固定域名**（推薦）:
   - 使用 ngrok 付費版獲得固定域名
   - 或使用 Cloudflare Tunnel

### 問題 5: Agent 無法連接

**症狀**: Gateway 返回 `502 Bad Gateway` 或超時

**可能原因**:

1. Agent 服務未運行
2. Agent 端點不可訪問
3. 網絡連接問題

**解決方法**:

1. **檢查 Agent 服務狀態**:

   ```bash
   # 健康檢查
   curl http://localhost:PORT/health

   # 檢查進程
   ps aux | grep {agent_process}
   ```

2. **測試 Agent 端點**:

   ```bash
   # 直接測試 Agent 端點
   curl -X POST http://localhost:PORT/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
   ```

3. **檢查網絡連接**:

   ```bash
   # 測試 Gateway 到 Agent 的連接
   curl -X POST https://agent-url.com/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
   ```

### 問題 6: AI-Box 註冊失敗

**症狀**: Agent 註冊後狀態為 `registering`，無法轉為 `online`

**可能原因**:

1. Secret 驗證失敗
2. Gateway 端點不可訪問
3. 工具名稱不匹配

**解決方法**:

1. **檢查 Secret 驗證**:

   ```bash
   curl -X POST http://localhost:8000/api/v1/agents/secrets/verify \
     -H "Content-Type: application/json" \
     -d '{
       "secret_id": "{secret_id}",
       "secret_key": "{secret_key}"
     }'
   ```

2. **檢查 Gateway 端點**:

   ```bash
   # 測試 Gateway 端點
   curl -X POST https://mcp.k84.org \
     -H "Content-Type: application/json" \
     -H "X-Gateway-Secret: {gateway_secret}" \
     -H "X-Tool-Name: {tool_name}" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
   ```

3. **檢查工具名稱匹配**:
   - 確保註冊的工具名稱與 Gateway 路由規則匹配
   - 確保工具名稱以正確的前綴開頭

---

## 📚 相關文檔

### 主要文檔

- [Cloudflare MCP Gateway 设置指南](./Cloudflare-MCP-Gateway-设置指南.md) - Gateway 詳細設置和完整配置
- [庫管員-Agent-Cloudflare-註冊配置指南](../Agent平台/庫管員-Agent-Cloudflare-註冊配置指南.md) - 實際案例參考
- [第三方 MCP 服务配置指南](./第三方MCP服务配置指南.md) - 第三方服務配置主指南

### 參考文檔

- [Cloudflare第三方MCP服務最終部署狀態](./Cloudflare第三方MCP服務最終部署狀態.md) - Gateway 當前部署狀態
- [MCP工具.md](./MCP工具.md) - MCP 工具系統概述

---

## 🎯 快速參考

### 常用命令

```bash
# 1. 部署 Gateway
cd mcp/gateway
wrangler deploy

# 2. 配置認證
wrangler kv key put "auth:{tool_name}" \
  '{"type":"none"}' \
  --binding=AUTH_STORE --preview=false --remote

# 3. 配置權限
wrangler kv key put "permissions:{tenant_id}:default" \
  '{"tools":["{tool_prefix}_*"]}' \
  --binding=PERMISSIONS_STORE --preview=false --remote

# 4. 測試 Gateway
curl -X POST https://mcp.k84.org \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: {gateway_secret}" \
  -H "X-Tool-Name: {tool_name}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### 配置範例

**wrangler.toml 路由配置**:

```toml
MCP_ROUTES = '''
[
  {
    "pattern": "{tool_prefix}_*",
    "target": "https://agent-url.com/mcp"
  }
]
'''
```

**認證配置**:

```bash
# 無認證
wrangler kv key put "auth:{tool_name}" \
  '{"type":"none"}' \
  --binding=AUTH_STORE --preview=false --remote

# API Key
wrangler kv key put "auth:{tool_name}" \
  '{"type":"api_key","api_key":"${AGENT_API_KEY}","header_name":"X-API-Key"}' \
  --binding=AUTH_STORE --preview=false --remote
```

**權限配置**:

```bash
wrangler kv key put "permissions:{tenant_id}:default" \
  '{"tools":["{tool_prefix}_*"]}' \
  --binding=PERMISSIONS_STORE --preview=false --remote
```

---

## 📝 更新日誌

### 版本 1.1（2026-01-15 09:16 UTC+8）

**重大更新**：

- ✅ 更新 Gateway 端點為正式 URL: `https://mcp-gateway.896445070.workers.dev`
- ✅ 添加完整的認證流程說明（X-Gateway-Secret, X-User-ID 等）
- ✅ 添加 JSON-RPC 2.0 協議要求
- ✅ 更新架構圖，包含詳細的認證流程
- ✅ 更新測試命令，使用實際的 Gateway 端點和正確的請求格式
- ✅ 添加雙存儲機制說明（agent_display_configs + Agent Registry）
- ✅ 更新 API 註冊示例為實際的 AI-Box API

**修正**：

- ❌ 移除錯誤的域名 `https://mcp.k84.com`（應為 `.org` 或 Workers.dev URL）
- ❌ 修正 Agent 註冊 API 端點路徑
- ❌ 修正測試命令中的參數格式

### 版本 1.0（2026-01-14）

- 初始版本
- 提供通用 Agent/工具註冊指南

---

**版本**: 1.1
**最後更新日期**: 2026-01-15 09:16 UTC+8
**維護人**: Daniel Chung
