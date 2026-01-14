# Cloudflare 第三方 MCP 服務落地計劃

**創建日期**: 2026-01-14
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-14

---

## 📋 當前狀態評估

### ✅ 已完成項目

根據 [開發環境部署狀態報告](./參考&歸檔文件/開發環境部署狀態報告.md)：

1. **Cloudflare 基礎設置**
   - ✅ Cloudflare 賬戶已登錄 (Daniels89)
   - ✅ Wrangler CLI 已安裝並登錄 (v4.54.0)
   - ✅ Worker 項目已創建

2. **KV 命名空間**
   - ✅ AUTH_STORE: `5b6e229c21f649269e93db9dcb8a7e16`
   - ✅ PERMISSIONS_STORE: `75e2e224e5844e1ea7639094b87d1001`
   - ✅ RATE_LIMIT_STORE: `e5b99f78db7c452aa70a080b662e0530`

3. **Gateway 配置**
   - ✅ Gateway Secret 已生成並設置: `0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e`
   - ✅ Worker 已部署: `mcp-gateway`
   - ✅ Workers.dev URL: `https://mcp-gateway.896445070.workers.dev`
   - ✅ DNS 配置已完成: `mcp.k84.org`

### ⏸️ 待完成項目

1. **AI-Box 環境變量配置**（必須）
   - ⏸️ 在 `.env` 文件中添加 `MCP_GATEWAY_SECRET`
   - ⏸️ 在 `.env` 文件中添加 `MCP_GATEWAY_ENDPOINT`

2. **MCP 路由配置**（必須）
   - ⏸️ 在 `wrangler.toml` 中配置 `MCP_ROUTES`（目前為空數組 `[]`）
   - ⏸️ 選擇並配置第一個第三方 MCP 服務（建議：Yahoo Finance）

3. **ArangoDB 配置**（必須）
   - ⏸️ 初始化 `mcp.external_services` 配置（系統啟動時自動完成）
   - ⏸️ 添加外部服務配置到 ArangoDB

4. **Gateway 認證配置**（按需）
   - ⏸️ 在 Gateway KV 中配置外部 MCP 服務認證信息

5. **R2 存儲桶**（可選）
   - ⏸️ 創建 R2 存儲桶用於審計日誌

---

## 🎯 落地計劃

### 階段一：基礎配置（必須完成）

#### 任務 1.1: 配置 AI-Box 環境變量

**目標**：在 AI-Box 的 `.env` 文件中添加 Gateway 配置

**操作步驟**：

```bash
# 在 AI-Box 項目根目錄
cd /Users/daniel/GitHub/AI-Box

# 檢查 .env 文件是否存在
if [ -f .env ]; then
  echo ".env 文件存在"
else
  echo ".env 文件不存在，需要創建"
fi

# 添加 MCP Gateway 配置
echo "" >> .env
echo "# ============================================" >> .env
echo "# MCP Gateway 配置（系統初始化）" >> .env
echo "# ============================================" >> .env
echo "MCP_GATEWAY_ENDPOINT=https://mcp.k84.org" >> .env
echo "MCP_GATEWAY_SECRET=0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e" >> .env
echo "MCP_GATEWAY_TIMEOUT=30" >> .env
echo "MCP_GATEWAY_MAX_RETRIES=3" >> .env
```

**驗證方法**：

```bash
# 檢查配置是否已添加
grep -i "MCP_GATEWAY" .env
```

**預期結果**：

```
MCP_GATEWAY_ENDPOINT=https://mcp.k84.org
MCP_GATEWAY_SECRET=0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e
MCP_GATEWAY_TIMEOUT=30
MCP_GATEWAY_MAX_RETRIES=3
```

#### 任務 1.2: 選擇並配置第一個第三方 MCP 服務

**目標**：選擇一個簡單的第三方 MCP 服務進行測試

**建議選擇**：Yahoo Finance MCP Server（公開服務，無需認證）

**服務信息**：

- **名稱**: `yahoo_finance`
- **描述**: Yahoo Finance MCP Server - 股票數據查詢工具
- **端點**: `https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp`
- **認證**: 無（公開服務）
- **工具示例**: `yahoo_finance_quote`, `yahoo_finance_history`

#### 任務 1.3: 配置 Cloudflare Gateway 路由

**目標**：在 `wrangler.toml` 中配置 MCP 路由規則

**操作步驟**：

1. 編輯 `mcp/gateway/wrangler.toml`
2. 更新 `MCP_ROUTES` 配置：

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

3. 部署更新：

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway
wrangler deploy
```

**驗證方法**：

```bash
# 檢查 wrangler.toml 配置
grep -A 10 "MCP_ROUTES" mcp/gateway/wrangler.toml
```

#### 任務 1.4: 配置 Gateway 認證（無認證服務）

**目標**：在 Gateway KV 中配置 Yahoo Finance 的認證信息（無認證）

**操作步驟**：

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 配置無認證的 MCP Server
wrangler kv key put "auth:yahoo_finance_quote" \
  '{"type":"none"}' \
  --namespace-id=5b6e229c21f649269e93db9dcb8a7e16 \
  --remote

# 驗證配置
wrangler kv key get "auth:yahoo_finance_quote" \
  --namespace-id=5b6e229c21f649269e93db9dcb8a7e16 \
  --remote
```

**預期結果**：

```json
{"type":"none"}
```

#### 任務 1.5: 在 ArangoDB 中配置外部服務

**目標**：通過 API 或直接寫入 ArangoDB 添加外部服務配置

**方法一：通過 API（推薦）**

**操作步驟**：

```bash
# 啟動 API 服務（如果未啟動）
cd /Users/daniel/GitHub/AI-Box
python -m uvicorn api.main:app --reload

# 在另一個終端執行 API 調用
curl -X PUT http://localhost:8000/api/config/system/mcp.external_services \
  -H "Content-Type: application/json" \
  -d '{
    "config_data": {
      "gateway": {
        "endpoint": "https://mcp.k84.org",
        "timeout": 30,
        "max_retries": 3
      },
      "external_services": [
        {
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
      ]
    }
  }'
```

**方法二：通過 Python 腳本直接寫入**

創建腳本 `scripts/migration/add_yahoo_finance_mcp.py`：

```python
#!/usr/bin/env python3
"""添加 Yahoo Finance MCP 服務配置到 ArangoDB"""

import sys
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from services.api.services.config_store_service import ConfigStoreService
from services.api.models.config import ConfigCreate, ConfigUpdate

# 加載環境變量
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

def add_yahoo_finance_service():
    """添加 Yahoo Finance MCP 服務配置"""
    config_service = ConfigStoreService()

    # 檢查配置是否存在
    existing_config = config_service.get_config("mcp.external_services", tenant_id=None)

    if existing_config:
        # 更新現有配置
        external_services = existing_config.config_data.get("external_services", [])

        # 檢查是否已存在
        if any(s.get("name") == "yahoo_finance" for s in external_services):
            print("Yahoo Finance 服務已存在，跳過添加")
            return

        # 添加新服務
        external_services.append({
            "name": "yahoo_finance",
            "description": "Yahoo Finance MCP Server - 股票數據查詢工具",
            "mcp_endpoint": "https://smithery.ai/server/@tsmdev-ux/yahoo-finance-mcp",
            "proxy_endpoint": "https://mcp.k84.org",
            "proxy_config": {
                "enabled": True,
                "audit_enabled": True,
                "hide_ip": True
            },
            "network_type": "third_party",
            "auth_type": "none",
            "auth_config": {
                "type": "none"
            },
            "enabled": True,
            "auto_discover": True
        })

        # 更新配置
        update = ConfigUpdate(
            config_data={
                "gateway": existing_config.config_data.get("gateway", {}),
                "external_services": external_services
            }
        )

        config_service.update_config(
            scope="mcp.external_services",
            config=update,
            tenant_id=None,
            changed_by="system"
        )

        print("✅ Yahoo Finance 服務已添加到配置")
    else:
        print("❌ MCP 外部服務配置不存在，請先初始化")
        print("   系統啟動時會自動初始化，或手動運行配置初始化")

if __name__ == "__main__":
    add_yahoo_finance_service()
```

**執行腳本**：

```bash
cd /Users/daniel/GitHub/AI-Box
python scripts/migration/add_yahoo_finance_mcp.py
```

### 階段二：測試驗證（必須完成）

#### 任務 2.1: 測試 Gateway 路由

**目標**：驗證 Gateway 路由配置是否正確

**測試步驟**：

```bash
# 測試 Gateway 路由（通過 Gateway 調用外部 MCP Server）
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

**預期結果**：

- ✅ 返回工具列表（如果外部 MCP Server 正常）
- ✅ 或返回 JSON-RPC 錯誤（如果路由配置有問題，需要檢查）

#### 任務 2.2: 測試 AI-Box 工具註冊

**目標**：驗證 AI-Box 能否從 ArangoDB 讀取配置並註冊工具

**測試步驟**：

1. 重啟 AI-Box MCP Server（如果正在運行）

```bash
# 檢查 MCP Server 是否運行
ps aux | grep "mcp.server"

# 重啟 MCP Server（讓它重新讀取配置）
# 根據實際啟動方式重啟
```

2. 檢查工具是否已註冊

```bash
# 通過 API 檢查工具列表
curl http://localhost:8002/mcp/tools
```

**預期結果**：

- ✅ 返回工具列表，包含 `yahoo_finance_quote` 等工具
- ✅ 工具類型為 `external`
- ✅ 工具端點指向 Gateway

#### 任務 2.3: 測試工具調用

**目標**：驗證工具調用流程是否正常

**測試步驟**：

```bash
# 調用 Yahoo Finance 工具
curl -X POST http://localhost:8002/api/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "yahoo_finance_quote",
    "arguments": {
      "symbol": "AAPL"
    }
  }'
```

**預期結果**：

- ✅ 返回股票報價數據
- ✅ 或返回錯誤信息（需要根據錯誤信息調試）

### 階段三：優化和完善（可選）

#### 任務 3.1: 配置 R2 存儲桶（可選）

**目標**：啟用審計日誌存儲

**操作步驟**：

1. 在 Cloudflare Dashboard → R2 中啟用 R2
2. 創建存儲桶：
   - 生產環境: `mcp-gateway-audit-logs`
   - 預覽環境: `mcp-gateway-audit-logs-preview`
3. 更新 `wrangler.toml`，取消註釋 R2 配置

#### 任務 3.2: 配置用戶權限（按需）

**目標**：為特定用戶配置工具訪問權限

**操作步驟**：

```bash
cd /Users/daniel/GitHub/AI-Box/mcp/gateway

# 配置用戶權限
wrangler kv key put "permissions:tenant-456:user-123" \
  '{"tools":["yahoo_finance_*"],"rate_limits":{"default":100}}' \
  --namespace-id=75e2e224e5844e1ea7639094b87d1001 \
  --remote
```

---

## 📊 執行進度追蹤

| 任務 | 狀態 | 完成時間 | 備註 |
|------|------|---------|------|
| 1.1 配置 AI-Box 環境變量 | ⏸️ 待執行 | - | - |
| 1.2 選擇第三方 MCP 服務 | ✅ 已完成 | - | 選擇 Yahoo Finance |
| 1.3 配置 Gateway 路由 | ⏸️ 待執行 | - | - |
| 1.4 配置 Gateway 認證 | ⏸️ 待執行 | - | - |
| 1.5 配置 ArangoDB | ⏸️ 待執行 | - | - |
| 2.1 測試 Gateway 路由 | ⏸️ 待執行 | - | - |
| 2.2 測試工具註冊 | ⏸️ 待執行 | - | - |
| 2.3 測試工具調用 | ⏸️ 待執行 | - | - |
| 3.1 配置 R2 存儲桶 | ⏸️ 可選 | - | - |
| 3.2 配置用戶權限 | ⏸️ 按需 | - | - |

---

## 🔍 問題排查指南

### 問題 1: Gateway 路由不匹配

**症狀**：返回 `Method not found: No route for tool`

**排查步驟**：

1. 檢查 `wrangler.toml` 中的 `MCP_ROUTES` 配置
2. 確認 pattern 是否正確匹配工具名稱
3. 檢查工具名稱是否與 pattern 匹配（如 `yahoo_finance_quote` 匹配 `yahoo_finance_*`）

### 問題 2: 認證失敗

**症狀**：返回 `Unauthorized: Invalid Gateway Secret`

**排查步驟**：

1. 檢查 AI-Box `.env` 文件中的 `MCP_GATEWAY_SECRET` 是否正確
2. 確認請求頭 `X-Gateway-Secret` 是否設置
3. 驗證 Cloudflare Worker 中的 `GATEWAY_SECRET` 是否匹配

### 問題 3: 工具未註冊

**症狀**：工具列表中沒有外部工具

**排查步驟**：

1. 檢查 ArangoDB 中是否有 `mcp.external_services` 配置
2. 確認配置中的 `enabled` 為 `true`
3. 檢查 MCP Server 日誌，查看是否有錯誤信息
4. 確認 `ExternalToolManager` 是否正確讀取配置

---

## 📚 相關文檔

- [開發環境部署狀態報告](./參考&歸檔文件/開發環境部署狀態報告.md) - 當前部署狀態
- [第三方 MCP 服务配置指南](./第三方MCP服务配置指南.md) - 配置主指南
- [Cloudflare MCP Gateway 设置指南](./Cloudflare-MCP-Gateway-设置指南.md) - Gateway 詳細設置
- [MCP第三方服務配置管理](../系統管理/MCP第三方服務配置管理.md) - 配置管理規範

---

**版本**: 1.0
**最後更新日期**: 2026-01-14
**維護人**: Daniel Chung
