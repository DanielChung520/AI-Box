# JP TiTop ERP Schema 配置說明

## 1. 系統概述

| 項目 | 說明 |
|------|------|
| **系統 ID** | `jp_tiptop_erp` |
| **名稱** | 日本 TiTop 基幹業務システム |
| **資料庫類型** | Oracle |
| **Bucket** | `jp-tiptop-raw` |
| **語言** | 日本語 |

## 2. 資料庫連接配置

### 2.1 連接參數

```yaml
主機: 192.168.5.16
端口: 1521
Service Name: ORCL
帳號: appuser
密碼: app123
Schema: APPUSER
```

### 2.2 Oracle Instant Client 安裝

**注意**：連接 Oracle 資料庫需要安裝 Oracle Instant Client。

#### 2.2.1 下載連結

> **注意**：下載需要 Oracle 帳號（免費註冊）

| 平台 | 下載連結 |
|------|----------|
| **Linux ARM (aarch64)** | [instantclient-basic-linuxArm64-19.21.0.0.0dbru.zip](https://download.oracle.com/otn_software/linux/arm/19.21/instantclient-basic-linuxArm64-19.21.0.0.0dbru.zip) |
| **Linux x86-64** | [instantclient-basic-linux.x64-19.21.0.0.0dbru.zip](https://download.oracle.com/otn_software/linux64/instantclient/19.21/instantclient-basic-linux.x64-19.21.0.0.0dbru.zip) |
| **macOS (Intel)** | [instantclient-basic-macos.x64-19.21.0.0.0dbru.zip](https://download.oracle.com/otn_software/mac/instantclient/19.21/instantclient-basic-macos.x64-19.21.0.0.0dbru.zip) |
| **macOS (Apple Silicon)** | [instantclient-basic-macos.arm64-19.21.0.0.0dbru.zip](https://download.oracle.com/otn_software/mac/instantclient/19.21/instantclient-basic-macos.arm64-19.21.0.0.0dbru.zip) |
| **Windows** | [instantclient-basic-windows.x64-19.21.0.0.0dbru.zip](https://download.oracle.com/otn_software/Windows/InstantClient/instantclient-basic-windows.x64-19.21.0.0.0dbru.zip) |

#### 2.2.2 安裝步驟（Linux）

```bash
# 1. 下載 Instant Client
wget https://download.oracle.com/otn_software/linux64/instantclient/19.21/instantclient-basic-linux.x64-19.21.0.0.0dbru.zip

# 2. 解壓到指定目錄
sudo unzip instantclient-basic-linux.x64-19.21.0.0.0dbru.zip -d /opt/oracle/

# 3. 設定環境變數
export ORACLE_HOME="/opt/oracle/instantclient_19_21"
export LD_LIBRARY_PATH="$ORACLE_HOME:$LD_LIBRARY_PATH"
export PATH="$ORACLE_HOME:$PATH"

# 4. 安裝依賴（Ubuntu/Debian）
sudo apt-get install -y libaio1

# 5. 驗證
sqlplus -V
```

#### 2.2.3 安裝步驟（macOS）

```bash
# 1. 使用 Homebrew 安裝
brew tap oracle/instantclient
brew install instantclient-basic

# 或手動安裝
# 解壓到 /opt/oracle/instantclient_19_21
export ORACLE_HOME="/opt/oracle/instantclient_19_21"
export DYLD_LIBRARY_PATH="$ORACLE_HOME:$DYLD_LIBRARY_PATH"
```

#### 2.2.4 安裝步驟（Windows）

1. 下載 `instantclient-basic-windows.x64-19.21.0.0.0dbru.zip`
2. 解壓到 `C:\oracle\instantclient_19_21`
3. 設定環境變數：
   ```
   ORACLE_HOME=C:\oracle\instantclient_19_21
   PATH=%ORACLE_HOME%;%PATH%
   ```

### 2.3 環境變數配置

```bash
# Oracle 連接資訊
export JP_TIPTOP_HOST="192.168.5.16"
export JP_TIPTOP_PORT="1521"
export JP_TIPTOP_SERVICE="ORCL"
export JP_TIPTOP_USER="appuser"
export JP_TIPTOP_PASSWORD="app123"

# Instant Client 路徑
export ORACLE_HOME="/opt/oracle/instantclient_19_21"
export LD_LIBRARY_PATH="$ORACLE_HOME:$LD_LIBRARY_PATH"
```

### 2.4 Python 連接範例

```python
import oracledb

# Oracle Instant Client 初始化
import oracledb
oracledb.init_oracle_client()

connection = oracledb.connect(
    user="appuser",
    password="app123",
    dsn="192.168.5.16:1521/ORCL"
)
```

## 3. 表格結構

### 3.1 表格清單

| Table | 名稱 | 類型 | 說明 |
|-------|------|------|------|
| **INAG_T** | 在庫明細 | Fact | Inventory Details |
| **SFAA_T** | 工單頭檔 | Fact | WO Header |
| **SFCA_T** | 工單製造頭檔 | Fact | WO Manufacturing Header |
| **SFCB_T** | 工單製造明细檔 | Fact | WO Manufacturing Details |
| **XMDG_T** | 出貨通知頭檔 | Fact | Expenditure List Header |
| **XMDH_T** | 出貨通知明细檔 | Fact | Quotation Details |
| **XMDT_T** | 售價審核頭檔 | Fact | Sales Price Approval Header |
| **XMDU_T** | 售價審核明细檔 | Fact | Sales Price Approval Details |

### 3.2 主要欄位說明

#### INAG_T（在庫明細）
| 欄位 | 類型 | 說明 |
|------|------|------|
| INAGENT | NUMBER | 企業編號 |
| INAGSITE | VARCHAR2 | 營運據點 |
| INAG001 | VARCHAR2 | 料件編號 |
| INAG004 | VARCHAR2 | 倉庫編號 |
| INAG005 | VARCHAR2 | 儲位編號 |
| INAG007 | VARCHAR2 | 單位 |
| INAG008 | NUMBER(15,3) | 現有庫存 |

#### SFAA_T（工單頭檔）
| 欄位 | 類型 | 說明 |
|------|------|------|
| SFAAENT | NUMBER | 企業編號 |
| SFAASITE | VARCHAR2 | 營運據點 |
| SFAA010 | VARCHAR2 | 料件編號 |
| SFAA056 | NUMBER(15,3) | 報廢數量 |
| SFAA022 | VARCHAR2 | 訂單編號 |
| SFAA023 | VARCHAR2 | 訂單項次 |
| SFAA009 | VARCHAR2 | 客戶編號 |
| SFAASTUS | VARCHAR2 | 狀態 |

### 3.3 表格關聯

```
INAG_T (item_no) ────▶ ITEM_MASTER
INAG_T (warehouse_no) ────▶ WAREHOUSE_MASTER
INAG_T (location_no) ────▶ STORAGE_LOCATION

SFAA_T (customer_no) ────▶ CUSTOMER

XMDG_T (customer_no) ────▶ CUSTOMER
XMDH_T (doc_no) ────▶ XMDG_T (doc_no)
XMDH_T (order_no) ────▶ SALES_HEADER

XMDT_T (customer_no) ────▶ CUSTOMER
XMUD_T (doc_no) ────▶ XMDT_T (doc_no)
```

## 4. Schema-Driven Query 架構

### 4.1 檔案結構

```
systems/tiptop_jp/
├── README.md                    # 本說明文件
├── original_schema.md           # 原始 DDL 定義
├── jp_tiptop_erp.yml            # 主 Schema 定義
├── concepts.json                # 業務概念層
├── intents.json                 # 查詢意圖層
└── bindings.json                # 綁定層（概念→實體）
```

### 4.2 Concepts（概念層）

定義業務語義，與資料庫無關：

```json
{
  "ITEM_NO": {
    "description": "料件編號",
    "type": "CODE"
  },
  "EXISTING_STOCKS": {
    "description": "現有庫存",
    "type": "METRIC",
    "aggregation": "SUM"
  },
  "WAREHOUSE_NO": {
    "description": "倉庫編號",
    "type": "CODE"
  }
}
```

### 4.3 Intents（意圖層）

定義查詢意圖與模式：

```json
{
  "QUERY_INVENTORY": {
    "description": "在庫照会",
    "patterns": ["在庫", "手持", "庫存"],
    "input": {
      "filters": ["ITEM_NO", "WAREHOUSE_NO"]
    },
    "output": {
      "metrics": ["EXISTING_STOCKS"],
      "dimensions": ["ITEM_NO", "WAREHOUSE_NO"]
    }
  }
}
```

### 4.4 Bindings（綁定層）

將概念映射到實際資料庫欄位：

```json
{
  "ITEM_NO": {
    "JP_TIPTOP_ERP": {
      "table": "INAG_T",
      "column": "INAG001",
      "type": "string"
    }
  },
  "EXISTING_STOCKS": {
    "JP_TIPTOP_ERP": {
      "table": "INAG_T",
      "column": "INAG008",
      "aggregation": "SUM"
    }
  }
}
```

## 5. 查詢範例

### 5.1 自然語言查詢

```
查詢料件的所有在庫
→ 對應 Intent: QUERY_INVENTORY
→ 生成的 SQL:
SELECT INAG001, INAG004, SUM(INAG008)
FROM APPUSER.INAG_T
GROUP BY INAG001, INAG004
```

### 5.2 結構化查詢

```json
{
  "action": "execute_structured_query",
  "structured_query": {
    "table": "inag_file",
    "columns": ["item_no", "warehouse_no", "existing_stocks"],
    "filters": {
      "warehouse_no": "W01"
    },
    "aggregation": "SUM"
  }
}
```

### 5.3 直接 SQL 查詢

```python
# 查詢所有在庫
SELECT INAG001, INAG004, SUM(INAG008) as total_stocks
FROM APPUSER.INAG_T
WHERE INAG004 = 'W01'
GROUP BY INAG001, INAG004
ORDER BY total_stocks DESC;

# 查詢工單狀態
SELECT SFAA022, SFAA010, SFAA056, SFAASTUS
FROM APPUSER.SFAA_T
WHERE SFAASTUS = '3';

# 查詢出貨通知
SELECT XMDGDOCNO, XMDGDOCDT, XMDG005, SUM(XMDH016) as total_qty
FROM APPUSER.XMDG_T
JOIN APPUSER.XMDH_T ON XMDGDOCNO = XMDHDOCNO
GROUP BY XMDGDOCNO, XMDGDOCDT, XMDG005;
```

## 6. 在 schema_registry.json 中註冊

```json
{
  "systems": {
    "jp_tiptop_erp": {
      "path": "systems/tiptop_jp/jp_tiptop_erp.yml",
      "version": "1.0.0",
      "tables_count": 8,
      "dialect": "oracle",
      "language": "ja",
      "description": "日本 TiTop ERP 系統",
      "schema_driven_query": {
        "concepts": "systems/tiptop_jp/concepts.json",
        "intents": "systems/tiptop_jp/intents.json",
        "bindings": "systems/tiptop_jp/bindings.json"
      }
    }
  }
}
```

## 7. 資料匯入到 S3

將 Oracle 資料匯出為 Parquet 存儲到 SeaweedFS：

```python
import oracledb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# 連接 Oracle
connection = oracledb.connect(
    user="appuser",
    password="app123",
    dsn="192.168.5.16:1521/ORCL"
)

# 匯出表格
tables = ['INAG_T', 'SFAA_T', 'SFCA_T', 'SFCB_T', 
          'XMDG_T', 'XMDH_T', 'XMDT_T', 'XMDU_T']

for table in tables:
    df = pd.read_sql(f"SELECT * FROM APPUSER.{table}", connection)
    parquet_file = f"/tmp/{table}.parquet"
    pq.write_table(pa.Table.from_pandas(df), parquet_file)
    print(f"✅ {table} → {parquet_file}")

# 上傳到 SeaweedFS S3
# aws s3 cp /tmp/*.parquet s3://jp-tiptop-raw/raw/v1/{table}/
```

## 8. 常見問題

### Q1: 連接 Oracle 失敗？

**問題**: `DPY-3010: connections to this database server version are not supported`
**問題**: `DPI-1047: Cannot locate a 64-bit Oracle Client library`

**解決**: 需要安裝 Oracle Instant Client

1. 下載 Instant Client（參考 2.2.1 節）
2. 解壓並設定環境變數：
```bash
export ORACLE_HOME="/opt/oracle/instantclient_19_21"
export LD_LIBRARY_PATH="$ORACLE_HOME:$LD_LIBRARY_PATH"
```

### Q2: 如何新增表格？

1. 在 `jp_tiptop_erp.yml` 中添加 table 定義
2. 在 `concepts.json` 中添加對應概念
3. 在 `intents.json` 中添加查詢意圖（如需要）
4. 在 `bindings.json` 中添加綁定
5. 更新 `schema_registry.json`

### Q3: 如何添加新欄位？

在對應表格的 `columns` 陣列中添加：
```yaml
- id: "new_field"
  names:
    tiptop_jp: "NEWFIELD"
  type: "string"
  description: "新欄位說明"
```

## 9. 相關文件

- [Data-Agent 規格書](../../../../.ds-docs/Data-Agent/Data-Agent-規格書.md)
- [Schema Driven Query](../tiptop_erp/SchemDruvebQuery.md)
- [TiTop ERP Schema](../tiptop_erp/tiptop_erp.yml)
