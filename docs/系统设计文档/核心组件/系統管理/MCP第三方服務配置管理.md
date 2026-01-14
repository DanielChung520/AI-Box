# MCP 第三方服務配置管理

**創建日期**: 2026-01-13
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-13

---

## 📋 概述

本文檔說明如何管理 MCP 第三方服務配置，採用雙層配置策略：

- **`.env` 文件**：系統初始化配置（基礎服務連接參數）
- **ArangoDB `system_configs`**：可調整的運行時配置（可通過管理界面動態修改）

---

## 🏗️ 配置架構

### 雙層配置策略

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: .env 文件（系統初始化）                        │
│  - MCP Gateway 連接參數                                  │
│  - Gateway Secret（敏感信息）                            │
│  - 基礎服務端點                                          │
│  - 系統啟動必需參數                                      │
└─────────────────────────────────────────────────────────┘
                        ↓ 初始化時讀取
┌─────────────────────────────────────────────────────────┐
│  Layer 2: ArangoDB system_configs（可調整配置）         │
│  - 第三方 MCP Server 列表                                │
│  - 路由配置                                              │
│  - 認證配置（非敏感部分）                                │
│  - 代理配置                                              │
│  - 工具配置                                              │
└─────────────────────────────────────────────────────────┘
                        ↓ 運行時讀取
┌─────────────────────────────────────────────────────────┐
│  ExternalToolManager（工具管理器）                        │
│  - 從 ArangoDB 讀取配置                                  │
│  - 註冊外部工具                                          │
│  - 動態刷新工具列表                                      │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 .env 文件配置（系統初始化）

### 配置類別

#### 1. MCP Gateway 基礎配置

**用途**：系統啟動時連接 Gateway 的必需參數

```bash
# ============================================
# MCP Gateway 配置（系統初始化）
# ============================================

# Gateway 端點 URL
MCP_GATEWAY_ENDPOINT=https://mcp.k84.org
# 或使用 workers.dev URL（如果 DNS 未配置）:
# MCP_GATEWAY_ENDPOINT=https://mcp-gateway.896445070.workers.dev

# Gateway Secret（用於 AI-Box 與 Gateway 之間的認證）
# 注意：這是敏感信息，必須與 Cloudflare Worker 中的 GATEWAY_SECRET 一致
MCP_GATEWAY_SECRET=0d28bdb881c5aeea501bf535b45c153ea78bf6f28b4856a41e36068dfbf7410e

# Gateway 連接超時（秒）
MCP_GATEWAY_TIMEOUT=30

# Gateway 重試次數
MCP_GATEWAY_MAX_RETRIES=3
```

#### 2. 第三方 MCP Server API Keys（敏感信息）

**用途**：存儲第三方服務的 API Keys（敏感信息，不應存儲在 ArangoDB）

```bash
# ============================================
# 第三方 MCP Server API Keys（敏感信息）
# ============================================

# Yahoo Finance API Key（如果服務需要）
# YAHOO_FINANCE_API_KEY=your-api-key-here

# Glama Office API Key
# GLAMA_OFFICE_API_KEY=your-api-key-here

# Slack Bot Token
# SLACK_BOT_TOKEN=xoxb-your-token-here

# Notion API Key
# NOTION_API_KEY=secret-your-key-here

# Confluence API Token
# CONFLUENCE_API_TOKEN=your-token-here
```

**注意**：

- ✅ 這些是敏感信息，只存儲在 `.env` 文件中
- ✅ 不會同步到 ArangoDB
- ✅ 在 ArangoDB 配置中，使用環境變量引用（如 `${GLAMA_OFFICE_API_KEY}`）

---

## 🗄️ ArangoDB 配置（可調整參數）

### 配置 Scope

**Scope 名稱**：`mcp.external_services`

**配置結構**：

```json
{
  "_key": "mcp.external_services",
  "scope": "mcp.external_services",
  "tenant_id": null,
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
      },
      {
        "name": "glama_office_word",
        "description": "Glama Office Word 操作工具",
        "mcp_endpoint": "https://api.glama.office/mcp",
        "proxy_endpoint": "https://mcp.k84.org",
        "proxy_config": {
          "enabled": true,
          "audit_enabled": true,
          "hide_ip": true
        },
        "network_type": "third_party",
        "auth_type": "api_key",
        "auth_config": {
          "type": "api_key",
          "api_key": "${GLAMA_OFFICE_API_KEY}",
          "header_name": "X-API-Key"
        },
        "enabled": true,
        "auto_discover": true
      }
    ]
  },
  "is_active": true,
  "created_at": "2026-01-13T00:00:00Z",
  "updated_at": "2026-01-13T00:00:00Z"
}
```

### 配置字段說明

#### Gateway 配置

| 字段 | 類型 | 說明 | 來源 |
|------|------|------|------|
| `gateway.endpoint` | string | Gateway 端點 URL | `.env` → ArangoDB |
| `gateway.timeout` | number | 連接超時（秒） | `.env` → ArangoDB |
| `gateway.max_retries` | number | 最大重試次數 | `.env` → ArangoDB |

#### 外部服務配置

| 字段 | 類型 | 說明 | 可調整 |
|------|------|------|--------|
| `name` | string | 服務名稱（唯一標識） | ❌ |
| `description` | string | 服務描述 | ✅ |
| `mcp_endpoint` | string | 真實 MCP Server 端點 | ✅ |
| `proxy_endpoint` | string | Gateway 代理端點 | ✅ |
| `proxy_config.enabled` | boolean | 是否啟用代理 | ✅ |
| `proxy_config.audit_enabled` | boolean | 是否啟用審計 | ✅ |
| `proxy_config.hide_ip` | boolean | 是否隱藏 IP | ✅ |
| `network_type` | string | 網絡類型（`third_party` / `internal_trusted`） | ✅ |
| `auth_type` | string | 認證類型（`none` / `api_key` / `bearer` / `oauth2`） | ✅ |
| `auth_config` | object | 認證配置（API Key 使用環境變量引用） | ✅ |
| `enabled` | boolean | 是否啟用此服務 | ✅ |
| `auto_discover` | boolean | 是否自動發現工具 | ✅ |

---

## 🔧 配置初始化流程

### 1. 系統啟動時初始化

**位置**：`api/main.py` 的 `startup_event`

**流程**：

```python
# 1. 從 .env 讀取基礎配置
gateway_endpoint = os.getenv("MCP_GATEWAY_ENDPOINT")
gateway_secret = os.getenv("MCP_GATEWAY_SECRET")

# 2. 檢查 ArangoDB 中是否已有配置
config_service = ConfigStoreService()
existing_config = config_service.get_config("mcp.external_services", tenant_id=None)

# 3. 如果不存在，從 .env 初始化配置到 ArangoDB
if not existing_config:
    initialize_mcp_external_services_config()
```

### 2. 配置初始化服務

**文件**：`services/api/services/config_initializer.py`

**新增函數**：

```python
def initialize_mcp_external_services_config(force: bool = False) -> bool:
    """
    初始化 MCP 第三方服務配置到 ArangoDB

    Args:
        force: 如果為 True，強制覆蓋現有配置

    Returns:
        是否成功初始化
    """
    config_service = ConfigStoreService()

    # 檢查配置是否已存在
    existing_config = config_service.get_config("mcp.external_services", tenant_id=None)

    if existing_config and not force:
        logger.debug("MCP external services config already exists, skipping initialization")
        return False

    # 從 .env 讀取基礎配置
    gateway_endpoint = os.getenv("MCP_GATEWAY_ENDPOINT", "https://mcp.k84.org")
    gateway_timeout = int(os.getenv("MCP_GATEWAY_TIMEOUT", "30"))
    gateway_max_retries = int(os.getenv("MCP_GATEWAY_MAX_RETRIES", "3"))

    # 構建配置數據
    config_data = {
        "gateway": {
            "endpoint": gateway_endpoint,
            "timeout": gateway_timeout,
            "max_retries": gateway_max_retries
        },
        "external_services": []  # 初始為空，後續通過管理界面添加
    }

    # 創建配置
    config_create = ConfigCreate(
        scope="mcp.external_services",
        config_data=config_data,
        metadata={
            "initialized": True,
            "source": "env_file",
            "description": "MCP 第三方服務配置"
        },
        tenant_id=None,  # 系統級配置
        data_classification="internal"  # 內部配置
    )

    config_service.save_config(config_create, tenant_id=None, changed_by="system")
    logger.info("MCP external services config initialized")

    return True
```

---

## 📊 配置讀取流程

### 1. ExternalToolManager 讀取配置

**文件**：`mcp/server/tools/external_manager.py`

**修改**：從 ArangoDB 讀取配置，而不是從 YAML 文件

```python
class ExternalToolManager:
    """外部 MCP 工具管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化外部工具管理器

        Args:
            config_path: YAML 配置文件路徑（可選，用於向後兼容）
        """
        self.config_path = config_path or "external_mcp_tools.yaml"
        self.external_tool_configs: List[Dict[str, Any]] = []
        self.registered_tools: Dict[str, ExternalMCPTool] = {}

    def load_config(self) -> List[Dict[str, Any]]:
        """
        加載外部工具配置（優先從 ArangoDB 讀取）

        Returns:
            List[Dict[str, Any]]: 工具配置列表
        """
        # 優先從 ArangoDB 讀取配置
        try:
            from services.api.services.config_store_service import ConfigStoreService

            config_service = ConfigStoreService()
            config = config_service.get_config("mcp.external_services", tenant_id=None)

            if config and config.config_data:
                # 從 ArangoDB 讀取配置
                gateway_config = config.config_data.get("gateway", {})
                external_services = config.config_data.get("external_services", [])

                # 過濾啟用的服務
                enabled_services = [
                    service for service in external_services
                    if service.get("enabled", True)
                ]

                self.external_tool_configs = enabled_services
                logger.info(
                    f"Loaded {len(enabled_services)} external service configurations from ArangoDB"
                )
                return enabled_services
        except Exception as e:
            logger.warning(f"Failed to load config from ArangoDB: {e}, falling back to YAML file")

        # 回退到 YAML 文件（向後兼容）
        return self._load_config_from_yaml()

    def _load_config_from_yaml(self) -> List[Dict[str, Any]]:
        """從 YAML 文件加載配置（向後兼容）"""
        config_file = Path(self.config_path)

        if not config_file.exists():
            logger.warning(f"External tools config file not found: {self.config_path}")
            return []

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                self.external_tool_configs = config.get("external_tools", [])
                logger.info(
                    f"Loaded {len(self.external_tool_configs)} external tool configurations from YAML"
                )
                return self.external_tool_configs
        except Exception as e:
            logger.error(f"Failed to load external tools config: {e}")
            return []
```

### 2. 環境變量解析

**功能**：解析認證配置中的環境變量引用（如 `${GLAMA_OFFICE_API_KEY}`）

```python
def resolve_env_variables(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析配置中的環境變量引用

    Args:
        config: 配置字典

    Returns:
        解析後的配置字典
    """
    import os
    import re

    def resolve_value(value: Any) -> Any:
        if isinstance(value, str):
            # 匹配 ${VAR_NAME} 格式
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)

            for var_name in matches:
                env_value = os.getenv(var_name)
                if env_value:
                    value = value.replace(f"${{{var_name}}}", env_value)
                else:
                    logger.warning(f"Environment variable {var_name} not found")

            return value
        elif isinstance(value, dict):
            return {k: resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [resolve_value(item) for item in value]
        else:
            return value

    return resolve_value(config)
```

---

## 🔄 配置更新流程

### 1. 通過 API 更新配置

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

### 2. 配置生效

**立即生效**：

- 配置更新後，`ExternalToolManager` 會在下一次工具刷新時讀取新配置
- 可以手動觸發刷新：`POST /api/mcp/tools/refresh`

**自動刷新**：

- `ExternalToolManager` 每小時自動刷新一次（可配置）

---

## 📝 配置管理 API

### 1. 獲取配置

**端點**：`GET /api/config/system/mcp.external_services`

**響應**：

```json
{
  "success": true,
  "data": {
    "id": "mcp.external_services",
    "scope": "mcp.external_services",
    "config_data": {
      "gateway": {
        "endpoint": "https://mcp.k84.org",
        "timeout": 30,
        "max_retries": 3
      },
      "external_services": [...]
    }
  }
}
```

### 2. 更新配置

**端點**：`PUT /api/config/system/mcp.external_services`

**請求**：見上方示例

### 3. 添加外部服務

**端點**：`POST /api/config/system/mcp.external_services/services`

**請求**：

```json
{
  "service": {
    "name": "new_service",
    "description": "新服務描述",
    "mcp_endpoint": "https://new-service.com/mcp",
    "proxy_endpoint": "https://mcp.k84.org",
    "proxy_config": {
      "enabled": true,
      "audit_enabled": true,
      "hide_ip": true
    },
    "network_type": "third_party",
    "auth_type": "api_key",
    "auth_config": {
      "type": "api_key",
      "api_key": "${NEW_SERVICE_API_KEY}",
      "header_name": "X-API-Key"
    },
    "enabled": true,
    "auto_discover": true
  }
}
```

### 4. 更新外部服務

**端點**：`PUT /api/config/system/mcp.external_services/services/{service_name}`

### 5. 刪除外部服務

**端點**：`DELETE /api/config/system/mcp.external_services/services/{service_name}`

### 6. 啟用/禁用外部服務

**端點**：`PATCH /api/config/system/mcp.external_services/services/{service_name}/toggle`

**請求**：

```json
{
  "enabled": true
}
```

---

## 🔐 安全考慮

### 1. 敏感信息處理

**原則**：

- ✅ 敏感信息（API Keys、Tokens）只存儲在 `.env` 文件中
- ✅ ArangoDB 配置中使用環境變量引用（如 `${GLAMA_OFFICE_API_KEY}`）
- ✅ 運行時解析環境變量引用

**示例**：

```json
{
  "auth_config": {
    "type": "api_key",
    "api_key": "${GLAMA_OFFICE_API_KEY}",  // 環境變量引用，不存儲實際值
    "header_name": "X-API-Key"
  }
}
```

### 2. 配置驗證

**驗證規則**：

- ✅ 服務名稱必須唯一
- ✅ MCP 端點必須是有效的 URL
- ✅ 認證類型必須是支持的类型
- ✅ 環境變量引用必須存在（運行時檢查）

---

## 📋 配置遷移

### 從 YAML 文件遷移到 ArangoDB

**遷移腳本**：`scripts/migration/migrate_mcp_external_services.py`

**功能**：

1. 讀取 `external_mcp_tools.yaml` 文件
2. 轉換為 ArangoDB 配置格式
3. 寫入 `system_configs` Collection
4. 保留原始 YAML 文件作為備份

**執行**：

```bash
python scripts/migration/migrate_mcp_external_services.py
```

---

## 🧪 測試

### 1. 配置初始化測試

```python
from services.api.services.config_initializer import initialize_mcp_external_services_config

# 初始化配置
result = initialize_mcp_external_services_config(force=False)
assert result == True

# 驗證配置已寫入 ArangoDB
from services.api.services.config_store_service import ConfigStoreService

config_service = ConfigStoreService()
config = config_service.get_config("mcp.external_services", tenant_id=None)
assert config is not None
assert "gateway" in config.config_data
assert "external_services" in config.config_data
```

### 2. 配置讀取測試

```python
from mcp.server.tools.external_manager import ExternalToolManager

manager = ExternalToolManager()
configs = manager.load_config()

# 驗證從 ArangoDB 讀取配置
assert len(configs) >= 0  # 可能為空（初始狀態）
```

### 3. 環境變量解析測試

```python
import os
from services.api.services.mcp_config_service import resolve_env_variables

# 設置環境變數
os.environ["TEST_API_KEY"] = "test-key-123"

# 測試解析
config = {
    "auth_config": {
        "api_key": "${TEST_API_KEY}"
    }
}

resolved = resolve_env_variables(config)
assert resolved["auth_config"]["api_key"] == "test-key-123"
```

---

## 📚 相關文檔

- [部署架構](./部署架構.md) - 系統參數配置策略
- [配置初始化測試指南](./配置初始化测试指南.md) - 配置初始化測試
- [MCP工具系統規格](../MCP工具/MCP工具.md) - MCP 工具系統完整規格
- [第三方MCP服務配置指南](../MCP工具/第三方MCP服务配置指南.md) - 第三方 MCP 配置指南

---

**版本**: 1.0
**最後更新日期**: 2026-01-14
**維護人**: Daniel Chung
