# System Config 存儲位置說明

**創建日期**: 2025-12-30
**創建人**: Daniel Chung
**最後修改日期**: 2025-12-30

**關聯文檔**: [工具組開發規格](./工具組開發規格.md)

---

## 📋 存儲位置確認

### 1. 存儲位置

**System Configs 存儲在 ArangoDB 中**，**不存儲在 `config.json` 文件中**。

- **數據庫**: ArangoDB
- **Collection 名稱**: `system_configs`
- **服務**: `ConfigStoreService` (`services/api/services/config_store_service.py`)

### 2. 存儲結構

#### Collection: `system_configs`

**Document 結構**:

```json
{
  "_key": "scope_key",                 // 主鍵，格式：{scope} 或 {scope}_{sub_scope}
  "_id": "system_configs/scope_key",
  "tenant_id": null,                   // 始終為 null（系統層）
  "scope": "genai.policy",             // 配置範圍（如 genai.policy, genai.model_registry）
  "sub_scope": "model_registry",       // 子範圍（可選）
  "is_active": true,                   // 是否啟用
  "config_data": {                     // 配置數據（JSON 對象）
    "allowed_providers": [...],
    "allowed_models": {...},
    "default_fallback": {...},
    "models": [...]                    // model_registry 使用
  },
  "metadata": {
    "description": "...",
    "version": "1.0"
  },
  "created_at": "2025-12-18T10:00:00Z",
  "updated_at": "2025-12-18T10:00:00Z",
  "created_by": "system",
  "updated_by": "user_id"
}
```

### 3. 常見 Scope 列表

根據代碼分析，系統中常見的 scope 包括：

- `genai.policy`: GenAI 策略配置
- `genai.model_registry`: 模型註冊表配置
- `genai.tenant_secrets`: GenAI 租戶密鑰配置
- `llm.provider_config`: LLM 提供商配置
- `llm.moe_routing`: MoE 路由配置
- `ontology.base`: Base Ontology 配置
- `ontology.domain`: Domain Ontology 配置
- `ontology.major`: Major Ontology 配置
- `system.security`: 安全配置
- `system.storage`: 存儲配置
- `system.logging`: 日誌配置
- `tools.datetime`: 日期時間工具配置（新增，用於工具組）

---

## 🔍 查詢方法

### 方法 1: 使用 API 查詢

```bash
# 查詢特定 scope 的 system config
curl -X GET "http://localhost:8000/api/configs/system?scope=genai.policy"

# 查詢有效配置（自動合併 system > tenant > user）
curl -X GET "http://localhost:8000/api/configs/effective?scope=genai.policy&tenant_id=tenant_123"
```

### 方法 2: 使用 Python 腳本查詢

```python
from services.api.services.config_store_service import get_config_store_service

# 獲取服務
service = get_config_store_service()

# 查詢特定 scope 的 system config
config = service.get_config(scope="genai.policy", tenant_id=None, user_id=None)
if config:
    print(f"Scope: {config.scope}")
    print(f"Config Data: {config.config_data}")
else:
    print("Config not found")
```

### 方法 3: 直接查詢 ArangoDB

```python
from database.arangodb import ArangoDBClient

client = ArangoDBClient()
cursor = client.db.aql.execute("""
    FOR doc IN system_configs
        FILTER doc.is_active == true
        SORT doc.scope ASC
        RETURN doc
""")

for config in cursor:
    print(f"Scope: {config['scope']}")
    print(f"Config Data: {config['config_data']}")
```

### 方法 4: 使用 ArangoDB Web UI

1. 訪問 ArangoDB Web UI（通常是 `http://localhost:8529`）
2. 登錄後選擇數據庫（通常是 `ai_box_kg`）
3. 進入 `system_configs` collection
4. 查看所有文檔

**注意**: 需要正確的 ArangoDB 認證信息（用戶名和密碼）

---

## 📝 當前配置查詢方法

### 方法 1: 使用 API 查詢（推薦）

如果 API 服務正在運行，可以使用 API 查詢：

```bash
# 查詢所有 system configs（需要實現 list 端點）
curl -X GET "http://localhost:8000/api/configs/system?scope=genai.policy"

# 或使用 Python requests
python3 -c "
import requests
response = requests.get('http://localhost:8000/api/configs/system?scope=genai.policy')
print(response.json())
"
```

### 方法 2: 使用 Python 腳本查詢

**注意**: 需要正確配置 ArangoDB 連接信息（環境變數）

```python
# 查詢腳本示例
from services.api.services.config_store_service import get_config_store_service

service = get_config_store_service()

# 查詢特定 scope
scopes = [
    "genai.policy",
    "genai.model_registry",
    "llm.provider_config",
    "tools.datetime"  # 新增的日期時間配置
]

for scope in scopes:
    config = service.get_config(scope=scope, tenant_id=None, user_id=None)
    if config:
        print(f"\n✅ Scope: {scope}")
        print(f"Config Data: {config.config_data}")
    else:
        print(f"\n⚠️  Scope '{scope}' 未找到")
```

### 方法 3: 直接查詢 ArangoDB（需要認證）

```python
from database.arangodb import ArangoDBClient
from services.api.services.config_store_service import SYSTEM_CONFIGS_COLLECTION
import json

# 需要正確的環境變數配置（ARANGO_USER, ARANGO_PASSWORD, ARANGO_DB）
client = ArangoDBClient()
if client.db is None:
    print("❌ ArangoDB 未連接，請檢查環境變數配置")
    exit(1)

cursor = client.db.aql.execute(f"""
    FOR doc IN {SYSTEM_CONFIGS_COLLECTION}
        FILTER doc.is_active == true
        SORT doc.scope ASC
        RETURN doc
""")

configs = list(cursor)
print(f"✅ 找到 {len(configs)} 個 system configs\n")

for config in configs:
    print(f"Scope: {config['scope']}")
    print(f"Key: {config['_key']}")
    print(f"Config Data:")
    print(json.dumps(config['config_data'], indent=2, ensure_ascii=False))
    print("-" * 60)
```

---

## 🔧 配置管理方式

### 創建 System Config

```python
from services.api.services.config_store_service import get_config_store_service
from services.api.models.config import ConfigCreate

service = get_config_store_service()

config = ConfigCreate(
    scope="tools.datetime",
    config_data={
        "default_format": "%Y-%m-%d %H:%M:%S",
        "default_timezone": "UTC",
        "default_locale": "en_US"
    },
    metadata={
        "description": "日期時間工具默認配置",
        "version": "1.0"
    }
)

config_id = service.save_config(config)
print(f"Config created: {config_id}")
```

### 更新 System Config

```python
from services.api.services.config_store_service import get_config_store_service
from services.api.models.config import ConfigUpdate

service = get_config_store_service()

updates = ConfigUpdate(
    config_data={
        "default_format": "%Y年%m月%d日 %H:%M:%S"
    }
)

updated_config = service.update_config(
    config_id="tools.datetime",
    updates=updates
)
```

### 讀取 System Config

```python
from services.api.services.config_store_service import get_config_store_service

service = get_config_store_service()

config = service.get_config(scope="tools.datetime")
if config:
    default_format = config.config_data.get("default_format")
    print(f"Default format: {default_format}")
```

---

## ⚠️ 重要說明

### 為什麼不使用 `config.json`？

1. **多租戶支持**: 不同租戶需要不同的配置
2. **動態配置**: 可以在運行時修改配置，無需重啟服務
3. **配置層級**: 支持 System > Tenant > User 三層配置合併
4. **版本歷史**: 配置變更有版本歷史記錄（存儲在 SeaweedFS）
5. **統一管理**: 與系統其他配置使用相同的架構

### 配置優先級

當讀取配置時，系統會自動合併三層配置：

1. **System Config**（`system_configs`）: 基礎配置，所有用戶共享
2. **Tenant Config**（`tenant_configs`）: 租戶特定配置，覆蓋 system config
3. **User Config**（`user_configs`）: 用戶個性化配置，優先級最高

**合併邏輯**: User > Tenant > System

---

## 📊 配置示例

### 示例 1: GenAI Policy Config

根據測試代碼中的示例，`genai.policy` scope 的配置結構如下：

```json
{
  "_key": "genai.policy",
  "_id": "system_configs/genai.policy",
  "scope": "genai.policy",
  "tenant_id": null,
  "is_active": true,
  "config_data": {
    "allowed_providers": ["openai", "anthropic"],
    "allowed_models": {
      "openai": ["gpt-4o", "gpt-3.5-turbo"],
      "anthropic": ["claude-3-opus", "claude-3-sonnet"]
    },
    "rate_limit": 1000
  },
  "metadata": {
    "description": "GenAI 策略配置",
    "version": "1.0"
  },
  "created_at": "2025-12-18T10:00:00Z",
  "updated_at": "2025-12-18T10:00:00Z",
  "created_by": "system",
  "updated_by": null
}
```

### 示例 2: Tools DateTime Config（新增）

```json
{
  "_key": "tools.datetime",
  "scope": "tools.datetime",
  "tenant_id": null,
  "is_active": true,
  "config_data": {
    "default_format": "%Y-%m-%d %H:%M:%S",
    "default_timezone": "UTC",
    "default_locale": "en_US",
    "iso_format": "%Y-%m-%dT%H:%M:%S%z",
    "date_only_format": "%Y-%m-%d",
    "time_only_format": "%H:%M:%S",
    "localized_formats": {
      "zh_TW": "%Y年%m月%d日 %H:%M:%S",
      "en_US": "%B %d, %Y %I:%M:%S %p"
    }
  },
  "metadata": {
    "description": "日期時間工具默認配置",
    "version": "1.0"
  }
}
```

---

## 🔗 相關文檔

- [Config Store Service](../../../services/api/services/config_store_service.py) - 配置存儲服務實現
- [Config API 路由](../../../services/api/routers/config.py) - 配置 API 端點
- [Config 數據模型](../../../services/api/models/config.py) - 配置數據模型定義
- [ArangoDB 數據存儲規範](../../../.cursor/rules/develop-rule.mdc#arangodb-數據存儲規範) - ArangoDB 存儲規範

---

**最後更新**: 2025-12-30
**維護人**: Daniel Chung
