# MCP 第三方服務配置管理 - 快速參考

**創建日期**: 2026-01-14
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-14

---

## 📋 快速配置指南

### 1. .env 文件配置（系統初始化）

在項目根目錄的 `.env` 文件中添加：

```bash
# ============================================
# MCP Gateway 配置（系統初始化）
# ============================================

# Gateway 端點 URL
MCP_GATEWAY_ENDPOINT=https://mcp.k84.org

# Gateway Secret（用於 AI-Box 與 Gateway 之間的認證）
# 注意：必須與 Cloudflare Worker 中的 GATEWAY_SECRET 一致
MCP_GATEWAY_SECRET=0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e

# Gateway 連接超時（秒）
MCP_GATEWAY_TIMEOUT=30

# Gateway 重試次數
MCP_GATEWAY_MAX_RETRIES=3

# ============================================
# 第三方 MCP Server API Keys（敏感信息）
# ============================================

# Glama Office API Key（示例）
# GLAMA_OFFICE_API_KEY=your-api-key-here

# Slack Bot Token（示例）
# SLACK_BOT_TOKEN=xoxb-your-token-here

# Notion API Key（示例）
# NOTION_API_KEY=secret-your-key-here
```

### 2. 系統啟動時自動初始化

配置會在系統啟動時自動從 `.env` 讀取並寫入 ArangoDB。

**檢查初始化狀態**：

```python
from services.api.services.config_store_service import ConfigStoreService

config_service = ConfigStoreService()
config = config_service.get_config("mcp.external_services", tenant_id=None)

if config:
    print("✅ MCP 配置已初始化")
    print(f"Gateway 端點: {config.config_data['gateway']['endpoint']}")
else:
    print("❌ MCP 配置未初始化")
```

### 3. 通過 API 添加外部服務

**API 端點**：`POST /api/config/system/mcp.external_services/services`

**請求示例**：

```json
{
  "service": {
    "name": "yahoo_finance",
    "description": "Yahoo Finance MCP Server - 股票數據查詢工具",
    "mcp_endpoint": "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp",
    "proxy_endpoint": "https://mcp.k84.org",
    "proxy_config": {
      "enabled": true,
      "audit_enabled": true,
      "hide_ip": true
    },
    "network_type": "third_party",
    "auth_type": "none",
    "auth_config": {
      "type": "none"
    },
    "enabled": true,
    "auto_discover": true
  }
}
```

### 4. 通過 API 更新配置

**API 端點**：`PUT /api/config/system/mcp.external_services`

**請求示例**：

```json
{
  "config_data": {
    "gateway": {
      "endpoint": "https://mcp.k84.org",
      "timeout": 30,
      "max_retries": 3
    },
    "external_services": [
      {
        "name": "yahoo_finance",
        "description": "Yahoo Finance MCP Server",
        "mcp_endpoint": "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp",
        "proxy_endpoint": "https://mcp.k84.org",
        "proxy_config": {
          "enabled": true,
          "audit_enabled": true,
          "hide_ip": true
        },
        "network_type": "third_party",
        "auth_type": "none",
        "auth_config": {
          "type": "none"
        },
        "enabled": true,
        "auto_discover": true
      }
    ]
  }
}
```

---

## 🔄 配置流程圖

```
系統啟動
    ↓
讀取 .env 文件
    ↓
檢查 ArangoDB 中是否有 mcp.external_services 配置
    ↓
如果不存在 → 從 .env 初始化配置到 ArangoDB
    ↓
ExternalToolManager 啟動
    ↓
從 ArangoDB 讀取配置
    ↓
解析環境變量引用（如 ${GLAMA_OFFICE_API_KEY}）
    ↓
註冊外部工具
    ↓
工具可用
```

---

## 📝 配置字段說明

### Gateway 配置

| 字段 | 來源 | 說明 |
|------|------|------|
| `gateway.endpoint` | `.env` → ArangoDB | Gateway 端點 URL |
| `gateway.timeout` | `.env` → ArangoDB | 連接超時（秒） |
| `gateway.max_retries` | `.env` → ArangoDB | 最大重試次數 |

### 外部服務配置

| 字段 | 類型 | 說明 | 可調整 |
|------|------|------|--------|
| `name` | string | 服務名稱（唯一標識） | ❌ |
| `mcp_endpoint` | string | 真實 MCP Server 端點 | ✅ |
| `proxy_endpoint` | string | Gateway 代理端點 | ✅ |
| `auth_type` | string | 認證類型 | ✅ |
| `auth_config.api_key` | string | API Key（使用 `${VAR_NAME}` 引用環境變量） | ✅ |
| `enabled` | boolean | 是否啟用 | ✅ |

---

## 🔐 環境變量引用

在 ArangoDB 配置中使用環境變量引用：

```json
{
  "auth_config": {
    "type": "api_key",
    "api_key": "${GLAMA_OFFICE_API_KEY}",
    "header_name": "X-API-Key"
  }
}
```

系統會在運行時自動解析 `${GLAMA_OFFICE_API_KEY}` 為實際的環境變量值。

---

## 📚 相關文檔

詳細說明請參閱：[MCP第三方服務配置管理](./MCP第三方服務配置管理.md)

---

**版本**: 1.0
**最後更新日期**: 2026-01-14
**維護人**: Daniel Chung
