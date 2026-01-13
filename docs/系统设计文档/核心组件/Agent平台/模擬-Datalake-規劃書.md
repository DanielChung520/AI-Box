# 模擬 Datalake 規劃書

**版本**：1.0
**創建日期**：2026-01-13
**創建人**：Daniel Chung
**最後修改日期**：2026-01-13

> **📋 相關文檔**：
>
> - [SeaweedFS使用指南](../系統管理/SeaweedFS使用指南.md) - SeaweedFS 使用指南
> - [庫管員-Agent-規劃書.md](./庫管員-Agent-規劃書.md) - 庫管員 Agent 規劃書（**必讀**：了解業務需求）
> - [AI-Box-Agent-架構規格書.md](./AI-Box-Agent-架構規格書.md) - Agent 架構總體設計

---

## 目錄

1. [概述](#1-概述)
2. [架構設計](#2-架構設計)
3. [SeaweedFS 配置](#3-seaweedfs-配置)
4. [Data Agent 設計](#4-data-agent-設計)
5. [數據模型](#5-數據模型)
6. [數據字典與 Schema](#6-數據字典與-schema)
7. [API 設計](#7-api-設計)
8. [實現計劃](#8-實現計劃)
9. [測試計劃](#9-測試計劃)
10. [配合條件](#10-配合條件)

---

## 1. 概述

### 1.1 定位

**模擬 Datalake**是一個**外部數據湖**，用於模擬真實的企業數據環境，支持：

- **物料數據存儲**：存儲物料基本信息（料號、名稱、規格等）
- **庫存數據存儲**：存儲庫存數量、位置、狀態等信息
- **數據查詢服務**：通過 Data Agent 提供數據查詢服務
- **數據字典管理**：管理數據字典和 Schema 定義

### 1.2 設計目標

1. **真實環境模擬**：模擬真實的企業數據環境
2. **獨立部署**：作為外部系統獨立部署
3. **標準化接口**：提供標準化的數據訪問接口
4. **可擴展性**：易於擴展更多數據類型和功能

### 1.3 技術選型

**存儲系統**：SeaweedFS（分布式文件系統）

**原因**：

- ✅ 已部署並運行（Master: 9334, Filer API: 8889）
- ✅ 支持 S3 API，易於集成
- ✅ 高性能、可擴展
- ✅ 支持多租戶和數據隔離

**服務架構**：

- **Master 節點**：管理元數據（端口 9334）
- **Volume 節點**：存儲實際數據
- **Filer API**：提供文件系統接口和 S3 API（端口 8889）

---

## 2. 架構設計

### 2.1 整體架構

```
┌─────────────────────────────────────────────────────────┐
│  外部系統：模擬 Datalake                                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │  SeaweedFS 服務                                   │   │
│  │  - Master (9334)                                  │   │
│  │  - Volume (存儲節點)                              │   │
│  │  - Filer API (8889)                               │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  數據存儲                                          │   │
│  │  - 物料數據 (JSON)                                 │   │
│  │  - 庫存數據 (JSON)                                 │   │
│  │  - 數據字典 (JSON)                                  │   │
│  │  - Schema 定義 (JSON)                              │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        ↓ S3 API / Filer API
┌─────────────────────────────────────────────────────────┐
│  AI-Box 系統：Data Agent                                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Data Agent Service                               │   │
│  │  - 數據查詢服務                                    │   │
│  │  - 數據字典管理                                    │   │
│  │  - Schema 管理                                     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        ↓ Agent Service Protocol
┌─────────────────────────────────────────────────────────┐
│  AI-Box 系統：業務 Agent                                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │  庫管員 Agent                                     │   │
│  │  - 料號查詢                                       │   │
│  │  - 庫存查詢                                       │   │
│  │  - 缺料分析                                       │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 數據流向

```
用戶查詢請求
    ↓
Orchestrator
    ↓
庫管員 Agent
    ↓ (請求數據)
Orchestrator
    ↓ (調用 Data Agent)
Data Agent
    ↓ (S3 API / Filer API)
SeaweedFS Datalake
    ↓ (返回數據)
Data Agent
    ↓ (處理和格式化)
Orchestrator
    ↓ (傳遞數據)
庫管員 Agent
    ↓ (業務邏輯處理)
返回結果給用戶
```

### 2.3 數據存儲結構

**SeaweedFS Bucket 結構**：

```
bucket-datalake-assets/
├── parts/                    # 物料數據
│   ├── ABC-123.json         # 料號 ABC-123 的數據
│   ├── ABC-124.json         # 料號 ABC-124 的數據
│   └── ...
├── stock/                    # 庫存數據
│   ├── ABC-123.json         # 料號 ABC-123 的庫存
│   ├── ABC-124.json         # 料號 ABC-124 的庫存
│   └── ...
├── dictionary/               # 數據字典
│   └── warehouse.json       # 倉庫數據字典
└── schema/                   # Schema 定義
    ├── part_schema.json     # 物料 Schema
    └── stock_schema.json    # 庫存 Schema
```

---

## 3. SeaweedFS 配置

### 3.1 服務配置

**當前運行狀態**：

- ✅ Master - 運行中（端口 9334）
- ✅ Volume - 運行中（Up 5 minutes）
- ✅ Filer API - 運行中（端口 8889）

**配置信息**：

```bash
# Master 配置
MASTER_PORT=9334
MASTER_HOST=localhost

# Filer API 配置
FILER_PORT=8889
FILER_HOST=localhost

# S3 API 配置（通過 Filer）
S3_ENDPOINT=http://localhost:8889
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
```

### 3.2 Bucket 配置

**需要創建的 Buckets**：

| Bucket 名稱 | 用途 | 說明 |
|------------|------|------|
| `bucket-datalake-assets` | 主要數據存儲 | 存儲物料、庫存等業務數據 |
| `bucket-datalake-dictionary` | 數據字典 | 存儲數據字典定義（Data Agent 管理） |
| `bucket-datalake-schema` | Schema 定義 | 存儲 Schema 定義（Data Agent 管理） |

**創建命令**：

```bash
# 使用 SeaweedFS Filer API 創建 Bucket
curl -X PUT "http://localhost:8889/bucket-datalake-assets"
curl -X PUT "http://localhost:8889/bucket-datalake-dictionary"
curl -X PUT "http://localhost:8889/bucket-datalake-schema"
```

### 3.3 環境變數配置

**Data Agent 環境變數**：

```bash
# Datalake SeaweedFS 配置
DATALAKE_SEAWEEDFS_S3_ENDPOINT=http://localhost:8889
DATALAKE_SEAWEEDFS_S3_ACCESS_KEY=your-access-key
DATALAKE_SEAWEEDFS_S3_SECRET_KEY=your-secret-key
DATALAKE_SEAWEEDFS_USE_SSL=false
DATALAKE_SEAWEEDFS_FILER_ENDPOINT=http://localhost:8889

# Data Agent 配置
DATA_AGENT_ENABLED=true
DATA_AGENT_DATALAKE_BUCKET=bucket-datalake-assets
DATA_AGENT_DICTIONARY_BUCKET=bucket-datalake-dictionary
DATA_AGENT_SCHEMA_BUCKET=bucket-datalake-schema
```

---

## 4. Data Agent 設計

### 4.1 職責擴展

**原有職責**（已實現）：

- Text-to-SQL 轉換
- 安全查詢閘道
- 查詢驗證

**新增職責**（本次擴展）：

- **Datalake 數據查詢**：查詢外部 Datalake（SeaweedFS）數據
- **數據字典管理**：管理 Datalake 的數據字典
- **Schema 管理**：管理 Datalake 的 Schema 定義

### 4.2 核心功能

#### 4.2.1 Datalake 數據查詢

**功能描述**：查詢外部 Datalake 中的數據

**支持的操作**：

- 查詢單個數據文件（如：`parts/ABC-123.json`）
- 查詢多個數據文件（批量查詢）
- 模糊查詢（根據條件查詢）

**接口設計**：

```python
async def query_datalake(
    self,
    bucket: str,
    key: str,
    query_type: str = "exact"  # exact/fuzzy
) -> Dict[str, Any]:
    """查詢 Datalake 數據"""
    pass
```

#### 4.2.2 數據字典管理

**功能描述**：管理 Datalake 的數據字典

**支持的操作**：

- 創建數據字典
- 更新數據字典
- 查詢數據字典
- 刪除數據字典

**數據字典結構**：

```json
{
  "dictionary_id": "warehouse",
  "name": "倉庫數據字典",
  "version": "1.0.0",
  "tables": {
    "parts": {
      "description": "物料表",
      "fields": {
        "part_number": {"type": "string", "description": "料號"},
        "name": {"type": "string", "description": "名稱"},
        "specification": {"type": "string", "description": "規格"}
      }
    },
    "stock": {
      "description": "庫存表",
      "fields": {
        "part_number": {"type": "string", "description": "料號"},
        "current_stock": {"type": "integer", "description": "當前庫存"},
        "location": {"type": "string", "description": "庫存位置"}
      }
    }
  },
  "created_at": "2026-01-13T00:00:00Z",
  "updated_at": "2026-01-13T13:45:27Z"
}
```

#### 4.2.3 Schema 管理

**功能描述**：管理 Datalake 的 Schema 定義

**支持的操作**：

- 創建 Schema
- 更新 Schema
- 查詢 Schema
- 驗證數據是否符合 Schema

**Schema 結構**（JSON Schema 格式）：

```json
{
  "schema_id": "part_schema",
  "name": "物料 Schema",
  "version": "1.0.0",
  "json_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "part_number": {"type": "string", "required": true},
      "name": {"type": "string", "required": true},
      "specification": {"type": "string"},
      "unit": {"type": "string"},
      "supplier": {"type": "string"},
      "category": {"type": "string"},
      "safety_stock": {"type": "integer"}
    },
    "required": ["part_number", "name"]
  },
  "created_at": "2026-01-13T00:00:00Z",
  "updated_at": "2026-01-13T13:45:27Z"
}
```

### 4.3 接口擴展

**新增任務類型**：

```python
class DataAgentTaskType(str, Enum):
    """Data Agent 任務類型（擴展）"""
    # 原有任務類型
    TEXT_TO_SQL = "text_to_sql"
    EXECUTE_QUERY = "execute_query"
    VALIDATE_QUERY = "validate_query"
    GET_SCHEMA = "get_schema"

    # 新增任務類型
    QUERY_DATALAKE = "query_datalake"  # 查詢 Datalake
    CREATE_DICTIONARY = "create_dictionary"  # 創建數據字典
    UPDATE_DICTIONARY = "update_dictionary"  # 更新數據字典
    GET_DICTIONARY = "get_dictionary"  # 查詢數據字典
    CREATE_SCHEMA = "create_schema"  # 創建 Schema
    UPDATE_SCHEMA = "update_schema"  # 更新 Schema
    GET_SCHEMA = "get_schema"  # 查詢 Schema
    VALIDATE_DATA = "validate_data"  # 驗證數據
```

**新增請求模型**：

```python
class QueryDatalakeRequest(BaseModel):
    """查詢 Datalake 請求"""
    bucket: str
    key: str  # 文件路徑，如 "parts/ABC-123.json"
    query_type: str = "exact"  # exact/fuzzy
    filters: Optional[Dict[str, Any]] = None  # 查詢過濾條件

class DictionaryRequest(BaseModel):
    """數據字典請求"""
    dictionary_id: str
    action: str  # create/update/get/delete
    data: Optional[Dict[str, Any]] = None

class SchemaRequest(BaseModel):
    """Schema 請求"""
    schema_id: str
    action: str  # create/update/get/delete
    data: Optional[Dict[str, Any]] = None
```

---

## 5. 數據模型

### 5.1 物料數據模型

**文件路徑**：`bucket-datalake-assets/parts/{part_number}.json`

**數據結構**：

```json
{
  "part_number": "ABC-123",
  "name": "電子元件 A",
  "specification": "10x10x5mm",
  "unit": "PCS",
  "supplier": "供應商 A",
  "category": "電子元件",
  "safety_stock": 100,
  "unit_price": 10.5,
  "currency": "TWD",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-13T13:45:27Z"
}
```

### 5.2 庫存數據模型

**文件路徑**：`bucket-datalake-assets/stock/{part_number}.json`

**數據結構**：

```json
{
  "part_number": "ABC-123",
  "current_stock": 50,
  "location": "倉庫 A-01",
  "status": "shortage",  # normal/low/shortage
  "last_updated": "2026-01-13T10:00:00Z",
  "last_counted": "2026-01-10T08:00:00Z"
}
```

### 5.3 數據字典模型

**文件路徑**：`bucket-datalake-dictionary/warehouse.json`

**數據結構**：見 [4.2.2 數據字典管理](#422-數據字典管理)

### 5.4 Schema 模型

**文件路徑**：`bucket-datalake-schema/{schema_id}.json`

**數據結構**：見 [4.2.3 Schema 管理](#423-schema-管理)

---

## 6. 數據字典與 Schema

### 6.1 數據字典設計

**目的**：

- 提供數據結構的文檔說明
- 支持數據發現和查詢
- 幫助 Data Agent 理解數據結構

**管理方式**：

- 由 Data Agent 管理
- 存儲在 `bucket-datalake-dictionary` Bucket
- 支持版本控制

### 6.2 Schema 設計

**目的**：

- 定義數據的結構和驗證規則
- 支持數據驗證
- 確保數據一致性

**管理方式**：

- 由 Data Agent 管理
- 存儲在 `bucket-datalake-schema` Bucket
- 使用 JSON Schema 格式
- 支持版本控制

### 6.3 初始化數據

**初始化腳本**：

```python
# scripts/init_datalake.py

# 1. 創建數據字典
dictionary = {
    "dictionary_id": "warehouse",
    "name": "倉庫數據字典",
    "version": "1.0.0",
    "tables": {
        "parts": {...},
        "stock": {...}
    }
}

# 2. 創建 Schema
part_schema = {
    "schema_id": "part_schema",
    "name": "物料 Schema",
    "version": "1.0.0",
    "json_schema": {...}
}

# 3. 創建測試數據
test_parts = [
    {"part_number": "ABC-123", ...},
    {"part_number": "ABC-124", ...}
]
```

---

## 7. API 設計

### 7.1 Data Agent API 擴展

**新增端點**：

```python
# 查詢 Datalake
POST /api/v1/data-agent/query-datalake
{
    "bucket": "bucket-datalake-assets",
    "key": "parts/ABC-123.json",
    "query_type": "exact"
}

# 數據字典管理
POST /api/v1/data-agent/dictionary
{
    "dictionary_id": "warehouse",
    "action": "get"  # create/update/get/delete
}

# Schema 管理
POST /api/v1/data-agent/schema
{
    "schema_id": "part_schema",
    "action": "get"  # create/update/get/delete
}
```

### 7.2 SeaweedFS API 使用

**S3 API 使用**：

```python
from storage.s3_storage import S3FileStorage, SeaweedFSService

# 創建存儲實例
storage = S3FileStorage(
    endpoint=os.getenv("DATALAKE_SEAWEEDFS_S3_ENDPOINT"),
    access_key=os.getenv("DATALAKE_SEAWEEDFS_S3_ACCESS_KEY"),
    secret_key=os.getenv("DATALAKE_SEAWEEDFS_S3_SECRET_KEY"),
    use_ssl=False,
    service_type=SeaweedFSService.DATALAKE,
)

# 讀取數據
data = storage.read_file("bucket-datalake-assets", "parts/ABC-123.json")

# 寫入數據
storage.write_file("bucket-datalake-assets", "parts/ABC-123.json", data)
```

**Filer API 使用**：

```python
import httpx

# 查詢文件
response = httpx.get("http://localhost:8889/bucket-datalake-assets/parts/ABC-123.json")

# 上傳文件
with open("data.json", "rb") as f:
    response = httpx.put(
        "http://localhost:8889/bucket-datalake-assets/parts/ABC-123.json",
        content=f.read()
    )
```

---

## 8. 實現計劃

### 8.1 開發階段

#### 階段一：SeaweedFS 配置與初始化（0.5 天）

**任務**：

1. 確認 SeaweedFS 服務運行狀態
2. 創建必要的 Buckets
3. 配置環境變數
4. 測試連接

**交付物**：

- Buckets 創建完成
- 環境變數配置完成
- 連接測試通過

#### 階段二：Data Agent 擴展（2-3 天）

**任務**：

1. 擴展 Data Agent 支持 Datalake 查詢
2. 實現數據字典管理功能
3. 實現 Schema 管理功能
4. 實現數據驗證功能

**交付物**：

- Data Agent 擴展代碼
- 單元測試
- API 文檔

#### 階段三：測試數據準備（0.5 天）

**任務**：

1. 創建測試物料數據
2. 創建測試庫存數據
3. 創建數據字典
4. 創建 Schema 定義

**交付物**：

- 測試數據文件
- 數據字典文件
- Schema 定義文件

#### 階段四：集成測試（1 天）

**任務**：

1. Data Agent 與 Datalake 集成測試
2. 庫管員 Agent 與 Data Agent 集成測試
3. 端到端測試

**交付物**：

- 集成測試用例
- 測試報告

### 8.2 技術實現

**Data Agent 擴展位置**：

- 文件：`agents/builtin/data_agent/agent.py`
- 新增方法：`query_datalake()`, `manage_dictionary()`, `manage_schema()`

**新增服務類**：

```python
# agents/builtin/data_agent/datalake_service.py
class DatalakeService:
    """Datalake 數據服務"""
    pass

# agents/builtin/data_agent/dictionary_service.py
class DictionaryService:
    """數據字典服務"""
    pass

# agents/builtin/data_agent/schema_service.py
class SchemaService:
    """Schema 服務"""
    pass
```

---

## 9. 測試計劃

### 9.1 單元測試

**測試範圍**：

- Datalake 查詢功能
- 數據字典管理功能
- Schema 管理功能
- 數據驗證功能

**測試用例**：

1. 查詢存在的數據文件
2. 查詢不存在的數據文件
3. 創建數據字典
4. 更新數據字典
5. 查詢數據字典
6. 創建 Schema
7. 驗證數據是否符合 Schema

### 9.2 集成測試

**測試範圍**：

- Data Agent 與 SeaweedFS 集成
- Data Agent 與庫管員 Agent 集成
- 端到端流程測試

**測試場景**：

1. 庫管員 Agent 查詢料號 → Data Agent 查詢 Datalake → 返回結果
2. 庫管員 Agent 查詢庫存 → Data Agent 查詢 Datalake → 返回結果
3. Data Agent 管理數據字典 → 存儲到 SeaweedFS → 查詢驗證

### 9.3 性能測試

**測試指標**：

- 查詢響應時間：< 1 秒
- 並發查詢：支持 20+ 並發請求
- 數據寫入：支持批量寫入

---

## 10. 配合條件

### 10.1 前置條件

1. **SeaweedFS 服務運行**：
   - ✅ Master 運行中（端口 9334）
   - ✅ Volume 運行中
   - ✅ Filer API 運行中（端口 8889）

2. **Data Agent 基礎功能**：
   - ✅ Text-to-SQL 功能已實現
   - ✅ 安全查詢閘道已實現
   - 🔄 需要擴展 Datalake 查詢功能

3. **環境配置**：
   - ✅ 環境變數配置完成
   - ✅ Buckets 創建完成

### 10.2 環境要求

**SeaweedFS 服務**：

- Master 節點運行正常
- Volume 節點運行正常
- Filer API 可訪問

**AI-Box 系統**：

- Data Agent 服務運行正常
- 能夠訪問 SeaweedFS Datalake
- 支持外部 Agent 調用

### 10.3 數據準備

**測試數據**：

- 10+ 測試料號數據
- 10+ 測試庫存數據
- 數據字典定義
- Schema 定義

**初始化腳本**：

- ✅ **檢查腳本**：`scripts/check_datalake_setup.py` - 檢查 SeaweedFS 服務和 Buckets 狀態
- ✅ **初始化腳本**：`scripts/init_datalake_test_data.py` - 自動創建 523 筆測試數據
  - 10 個料號的物料數據（10 筆）
  - 10 個料號的庫存數據（10 筆）
  - 每個料號的庫存歷史記錄（50 筆 × 10 = 500 筆）
  - 數據字典（1 筆）
  - Schema 定義（2 筆）

**使用步驟**：

```bash
# 1. 檢查 SeaweedFS 服務和 Buckets
python scripts/check_datalake_setup.py

# 2. 初始化測試數據（523 筆）
python scripts/init_datalake_test_data.py
```

### 10.4 文檔要求

**需要創建的文檔**：

1. Datalake 數據結構文檔
2. Data Agent API 文檔（擴展部分）
3. 數據字典使用指南
4. Schema 使用指南

---

## 11. 後續擴展

### 11.1 功能擴展

1. **數據同步**：支持從其他系統同步數據
2. **數據備份**：支持數據備份和恢復
3. **數據版本控制**：支持數據版本管理
4. **數據分析**：支持數據分析和報表生成

### 11.2 集成擴展

1. **多數據源支持**：支持多個 Datalake 數據源
2. **實時數據同步**：支持實時數據同步
3. **數據質量監控**：支持數據質量監控和告警

---

**文檔版本**：1.0
**最後更新**：2026-01-13
**維護者**：Daniel Chung
