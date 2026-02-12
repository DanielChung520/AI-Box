# TipTop ERP Schema Registry Metadata

## 概述

本目錄存放 TipTop ERP 系統的 Schema Registry 定義，用於支援 **HybridRRAG**（混合檢索增強生成）架構，將自然語言查詢轉換為精確的 SQL 語句。

---

## 架構演進

### 問題背景

```
傳統 Text-to-SQL 的痛點：
┌─────────────────────────────────────────────────────────┐
│  • LLM 無法準確理解 Schema 結構                          │
│  • Prompt 過長導致關鍵資訊遺漏                           │
│  • 表格選擇錯誤（如：查料號卻選到 pmn_file）              │
│  • 缺少領域概念映射（如：鋁合金 → MATERIAL_CATEGORY）    │
│  • 資料庫綁定（硬編碼 DuckDB 路徑，難以遷移）            │
└─────────────────────────────────────────────────────────┘
```

### 解決方案：HybridRRAG + SQL Adapter 雙層架構

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Data-Agent 完整架構                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   User Query ──┬──► HybridRRAG ──► LLM Prompt                        │
│                │           │              │                            │
│                │           ▼              ▼                            │
│                │    ┌─────────┐    ┌─────────┐                       │
│                │    │  Qdrant │    │ArangoDB │                       │
│                │    │ (語義)  │    │ (圖譜)  │                       │
│                │    └─────────┘    └─────────┘                       │
│                │                                                 │
│                ▼                                                   │
│   ┌─────────────────────────────────────────────────────────┐       │
│   │              Text-to-SQL 轉換層                          │       │
│   │  Query → RAG → LLM → SQL → SQLAdapter.execute()        │       │
│   │                            │                            │       │
│   │                            ▼                            │       │
│   │              ┌─────────────────────────┐               │       │
│   │              │   SQLAdapter 介面       │               │       │
│   │              ├─────────────────────────┤               │       │
│   │              │ DuckDBAdapter           │               │       │
│   │              │ OracleAdapter (未來)    │               │       │
│   │              │ MySQLAdapter (未來)     │               │       │
│   │              └─────────────────────────┘               │       │
│   └─────────────────────────────────────────────────────────┘       │
│                            │                                          │
│                            ▼                                          │
│   ┌─────────────────────────────────────────────────────────┐       │
│   │                    資料庫執行層                          │       │
│   │  ┌───────────┐  ┌───────────┐  ┌───────────┐          │       │
│   │  │  DuckDB   │  │  Oracle   │  │  MySQL    │          │       │
│   │  │ (S3 Parquet)│  │  (未來)   │  │  (未來)    │          │       │
│   │  └───────────┘  └───────────┘  └───────────┘          │       │
│   └─────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**核心原則**：
1. **RAG 層**：只負責 Schema 檢索（表格、欄位、概念）
2. **Adapter 層**：隔離資料庫差異，未來替換資料庫只需新增 Adapter
3. **職責分離**：Data-Agent 無需知道底層資料庫

---

## Schema Registry 結構

### 檔案組織

```
metadata/
├── tiptop_schema_registry.json   # TipTop ERP Schema 定義
├── README.md                     # 本文件
└── config/
    └── schema_rag_config.yaml    # RAG 服務配置
```

### JSON 結構

```json
{
  "system": {
    "system_id": "tiptop01",
    "system_name": "鼎捷 TipTop ERP",
    "description": "進銷存與財務管理系統"
  },
  "tables": { ... },
  "concepts": { ... },
  "intent_templates": { ... },
  "validation_rules": { ... },
  "table_relationships": { ... }
}
```

---

## System 區塊

每個 Schema Registry 必須包含 system 區塊，用於區分不同系統：

```json
{
  "system": {
    "system_id": "tiptop01",
    "system_name": "鼎捷 TipTop ERP",
    "description": "進銷存與財務管理系統"
  }
}
```

**用途**：
- 查詢時根據用戶上下文自動過濾
- 跨系統查詢時區分資料來源
- 版本控制與權限管理

---

## Tables 區塊

定義資料表結構，供 Qdrant 向量化檢索：

```json
{
  "tables": {
    "ima_file": {
      "canonical_name": "ima_file",
      "tiptop_name": "料件主檔",
      "columns": [
        {"id": "ima01", "name": "料號", "type": "V", "description": "PK"},
        {"id": "ima02", "name": "品名", "type": "V", "description": "Item Name"},
        {"id": "ima08", "name": "來源碼", "type": "V", "description": "M:成品, P:原料"}
      ]
    }
  }
}
```

---

## Concepts 區塊（核心創新）

領域概念映射，解決「語義模糊」問題：

### MATERIAL_CATEGORY（物料類別）

```json
{
  "concepts": {
    "MATERIAL_CATEGORY": {
      "description": "物料類別，用於過濾特定類型的物料",
      "mappings": {
        "plastic": {
          "keywords": ["塑料件", "塑膠件", "塑膠", "塑料"],
          "target_field": "ima02",
          "operator": "LIKE",
          "pattern": "%{value}%"
        },
        "metal": {
          "keywords": ["金屬件", "金屬", "鐵件", "鋁件", "鋁", "鋁合金", "鋁合金錠"],
          "target_field": "ima02",
          "operator": "LIKE",
          "pattern": "%{value}%"
        }
      }
    }
  }
}
```

### 其他 Concepts

| Concept | 用途 | 範例關鍵字 |
|---------|------|-----------|
| **INVENTORY_LOCATION** | 倉庫位置 | 原料倉、成品倉、W01 |
| **TRANSACTION_TYPE** | 交易類型 | 採購、入庫、出庫、報廢 |
| **TIME_EXPRESSION** | 時間表達 | 本月、上月、今年、去年 |
| **ORDER_STATUS** | 訂單狀態 | 已確認、已出貨、已結案 |

---

## Intent Templates 區塊

查詢意圖模板，指導 LLM 生成正確的 SQL：

```json
{
  "intent_templates": {
    "QUERY_STOCK": {
      "description": "庫存查詢",
      "intent_type": "QUERY",
      "primary_table": "img_file",
      "joins": [
        { "table": "ima_file", "on": "img01 = ima01", "type": "LEFT" }
      ],
      "output_fields": ["img01", "ima02", "img02", "SUM(img10) as qty"],
      "examples": [
        "RM05-008 庫存還有多少",
        "查詢 W01 倉庫的庫存"
      ]
    }
  }
}
```

---

## SQL Adapter 資料庫抽象化層

### 架構原則

```
┌─────────────────────────────────────────────────┐
│              Data-Agent (抽象化層)               │
├─────────────────────────────────────────────────┤
│  Query → RAG → LLM → SQL → Adapter.execute()   │
│                              │                  │
│                              ▼                  │
│              ┌─────────────────────────┐       │
│              │   SQLAdapter 介面      │       │
│              ├─────────────────────────┤       │
│              │ DuckDBAdapter │ OracleAdapter │ │
│              │ MySQLAdapter           │       │
│              └─────────────────────────┘       │
└─────────────────────────────────────────────────┘
```

**職責**：
- 隔離資料庫差異
- 未來替換資料庫只需新增 Adapter
- Data-Agent 無需知道底層資料庫

### 介面定義

```python
class SQLAdapter(ABC):
    """SQL Adapter 介面 - 所有資料庫適配器必須實作此介面"""

    @property
    @abstractmethod
    def dialect_name(self) -> str:
        """資料庫名稱（如 'duckdb', 'oracle', 'mysql'）"""

    @abstractmethod
    def table_source(self, table: str, schema: str = None) -> str:
        """生成表格來源語法"""

    @abstractmethod
    def cast(self, expr: str, type: str) -> str:
        """生成 CAST 表達式"""

    @abstractmethod
    def concat(self, *args: str) -> str:
        """生成字串拼接"""

    @abstractmethod
    def like(self, field: str, pattern: str) -> str:
        """生成 LIKE 條件"""

    @abstractmethod
    def sum(self, field: str, alias: str = None) -> str:
        """生成 SUM 聚合"""

    @abstractmethod
    def count(self, field: str = "*", alias: str = None) -> str:
        """生成 COUNT 聚合"""

    @abstractmethod
    def join(self, left_table, right_table, left_field, right_field, join_type="LEFT") -> str:
        """生成 JOIN 語法"""

    @abstractmethod
    def limit(self, count: int) -> str:
        """生成 LIMIT 子句"""

    @abstractmethod
    def execute(self, sql_query: str) -> SQLResult:
        """執行 SQL 查詢"""
```

### 已實作 Adapter

#### DuckDBAdapter

| 方法 | 輸出範例 |
|------|---------|
| `table_source("ima_file")` | `read_parquet('s3://tiptop-raw/raw/v1/ima_file/year=*/month=*/data.parquet', hive_partitioning=true)` |
| `cast("img10", "N")` | `CAST(img10 AS DOUBLE)` |
| `concat("ima01", "ima02")` | `CONCAT(ima01, ima02)` |
| `limit(100)` | `LIMIT 100` |

#### OracleAdapter（預留）

| 方法 | 輸出範例 |
|------|---------|
| `table_source("ima_file")` | `IMA_FILE` |
| `table_source("ima_file", "TIPTOP")` | `TIPTOP.IMA_FILE` |
| `limit(100)` | `ROWNUM <= 100` |

#### MySQLAdapter（預留）

| 方法 | 輸出範例 |
|------|---------|
| `table_source("ima_file")` | `` `ima_file` `` |
| `concat("ima01", "ima02")` | `CONCAT(ima01, ima02)` |

### 工廠模式

```python
from data_agent.sql_adapter import SQLAdapterFactory

# 建立 DuckDB Adapter
duckdb_adapter = SQLAdapterFactory.create("duckdb")

# 建立 Oracle Adapter（未來）
oracle_adapter = SQLAdapterFactory.create("oracle")

# 支援的資料庫類型
print(SQLAdapterFactory.supported_dialects())
# ['duckdb', 'oracle', 'mysql']
```

### 新增 Adapter 步驟

1. 繼承 `SQLAdapter` 抽象類別
2. 實作所有抽象方法
3. 在工廠中註冊

```python
class PostgreSQLAdapter(SQLAdapter):
    """PostgreSQL 適配器 - 新增範例"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @property
    def dialect_name(self) -> str:
        return "postgresql"

    def table_source(self, table: str, schema: str = None) -> str:
        schema_prefix = f"{schema}." if schema else ""
        return f'{schema_prefix}"{table}"'

    # ... 實作其他方法

# 註冊新 Adapter
SQLAdapterFactory.register("postgresql", PostgreSQLAdapter)
```

---

## Workflow 流程

### 1. Schema 上傳（schemaUpload.py）

```
┌─────────────────────────────────────────────────────────┐
│  schemaUpload.py                                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  輸入: tiptop_schema_registry.json                       │
│       │                                                 │
│       ▼                                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  1. 解析 JSON                                    │   │
│  │  2. 向量化 → Qdrant (tables + concepts)         │   │
│  │  3. 圖譜化 → ArangoDB (relationships)          │   │
│  │  4. 建立 HybridRRAG 索引                        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  時機: 首次部署 / 重大 Schema 變更                       │
│  耗時: ~5 秒 (15 表格)                                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2. Schema 查詢（schemaRAG.py）

```
┌─────────────────────────────────────────────────────────┐
│  schemaRAG.py                                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  用戶查詢: 「鋁合金錠系列的料號」                         │
│       │                                                 │
│       ▼                                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  1. 取得當前系統上下文                          │   │
│  │     → system_id = "tiptop"                    │   │
│  │                                                 │   │
│  │  2. HybridRRAG 檢索                             │   │
│  │     → Qdrant: 語義搜索相關 schema               │   │
│  │     → ArangoDB: 表格關係                        │   │
│  │                                                 │   │
│  │  3. Filter 自動附加                             │   │
│  │     → {"must": [{"key": "system_id", "eq": ...}]}│
│  │                                                 │   │
│  │  4. 生成 Prompt                                 │   │
│  │     → 「使用 ima_file，WHERE ima02 LIKE '%鋁合金%'」│
│  └─────────────────────────────────────────────────┘   │
│       │                                                 │
│       ▼                                                 │
│  LLM 生成 SQL + SQL Adapter 執行                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 3. SQL 執行（sqlAdapter.py）

```
┌─────────────────────────────────────────────────────────┐
│  sqlAdapter.py                                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  LLM 生成的 SQL（資料庫無關）                            │
│       │                                                 │
│       ▼                                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  1. 根據 sql_dialect 選擇 Adapter               │   │
│  │     → SQLAdapterFactory.create("duckdb")        │   │
│  │                                                 │   │
│  │  2. Adapter 轉換為資料庫特定語法                 │   │
│  │     → table_source()                           │   │
│  │     → cast(), concat(), like(), join()          │   │
│  │                                                 │   │
│  │  3. 執行 SQL                                     │   │
│  │     → adapter.execute(sql)                      │   │
│  └─────────────────────────────────────────────────┘   │
│       │                                                 │
│       ▼                                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  執行結果                                        │   │
│  │  { success: true, rows: [...], row_count: 10 }  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 多系統資料庫設計

### 設計原則

| 維度 | ArangoDB | Qdrant |
|------|----------|--------|
| **Collections** | 2 個：`schema_entities` + `schema_relationships` | 1 個：`schema_registry` |
| **System 區分** | `_key` 尾碼（如 `ima_file_tiptop`） | `payload.system_id` |
| **查詢語法** | AQL | Qdrant Filter API |
| **跨系統** | `FILTER system_id IN [...]` | `should` clause |

---

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `tiptop_schema_registry.json` | TipTop ERP Schema 定義 |
| `README.md` | 本說明文件 |
| `config/schema_rag_config.yaml` | RAG 服務配置 |

### 相關程式碼

| 檔案 | 目錄 | 說明 |
|------|------|------|
| `schemaUpload.py` | `datalake-system/scripts/` | Schema 上傳至 Qdrant/ArangoDB |
| `schemaRAG.py` | `datalake-system/data_agent/` | HybridRRAG 查詢接口 |
| `sqlAdapter.py` | `datalake-system/data_agent/` | SQL 資料庫抽象化層 |
| `textToSQL.py` | `datalake-system/data_agent/` | Text-to-SQL 轉換服務 |

---

## 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.0.0 | 2026-02-09 | 初始版本，新增 system 區塊，新增鋁合金概念 |
| 1.1.0 | 2026-02-10 | 新增 SQL Adapter 資料庫抽象化層 |

---

## 未來擴展方向

1. **SQL Adapter**：PostgreSQL、SQL Server、BigQuery
2. **更多 Concepts**：SUPPLIER_TYPE、ORDER_STATUS、PRICING_TYPE
3. **跨系統查詢**：Federated Search 一次查多個系統
4. **語義優化**：HyDE、Cross-Encoder Reranking
5. **版本控制**：Schema 版本歷史追蹤
