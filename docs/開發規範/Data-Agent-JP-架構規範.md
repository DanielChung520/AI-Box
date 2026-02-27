# Data-Agent-JP 架構規範

## 版本
1.0.0

## 建立日期
2026-02-19

## 背景

本次規範是為了解決「清理舊程式碼後仍然使用舊模式」的問題。問題根源：

1. **只清理了模板文件，沒有更換調用方**
2. **依賴鏈沒有斷開**：MM-Agent → StructuredQueryHandler → 舊 schema

---

## 正確架構

```
MM-Agent (port 8003)
    ↓
    ┌─────────────────────────────────────────┐
    │  正確：使用 /jp/execute 端點           │
    │  URL: http://localhost:8004/api/v1/data-agent/jp/execute
    │  payload: { task_type: "schema_driven_query", task_data: { nlq: "..." } }
    └─────────────────────────────────────────┘
    ↓
Data-Agent-JP (port 8004)
    ↓
    ┌─────────────────────────────────────────┐
    │  schema_driven_query 模組               │
    │  - resolver.py (意圖解析)                │
    │  - sql_generator.py (SQL生成)           │
    │  - duckdb_executor.py (執行)            │
    └─────────────────────────────────────────┘
    ↓
DuckDB (tiptop_jp.duckdb)
    ↓
    mart_inventory_wide (item_no, warehouse_no, existing_stocks, ...)
    mart_work_order_wide (item_no, customer_no, status, ...)
    mart_shipping_wide (doc_no, doc_date, customer_no, ...)
```

---

## 嚴禁事項

### ❌ 禁止使用舊模組

以下模組**已棄用**，嚴禁在 MM-Agent 中調用：

| 模組 | 棄用原因 |
|------|----------|
| `data_agent.structured_query_handler.StructuredQueryHandler` | 使用舊 schema |
| `data_agent.structured_query_builder` | 使用舊 SQL 模板 |
| `data_agent.code_dictionary` | 使用舊欄位名稱 |
| `data_agent.semantic_scenarios` | 使用舊表名 |
| `data_agent.data_agent_intent_rag` | 使用舊 SQL 模板 |

### ❌ 禁止使用舊欄位名稱

| 舊欄位名稱 | 新欄位名稱 |
|-----------|-----------|
| `img01`, `ima01` | `item_no` |
| `img02`, `mb002` | `warehouse_no` |
| `img03` | `location_no` |
| `img04`, `mb010` | `existing_stocks` |
| `tlf06` | (無對應) |

### ❌ 禁止使用舊表名

| 舊表名 | 新表名 |
|--------|--------|
| `img_file` | `mart_inventory_wide` |
| `tlf_file` | `mart_work_order_wide` |
| `ima_file` | `mart_inventory_wide` |

### ❌ 禁止使用舊倉庫編號

| 舊編號 | 新編號 |
|--------|--------|
| W01, W02, W03 | 2101, 2205, 2700, 3000 等 |
| R01 | (需查詢實際編號) |

---

## 正確做法

### 1. MM-Agent 調用 Data-Agent

```python
# ✅ 正確：使用 /jp/execute 端點
import httpx

payload = {
    "task_id": "mm-agent-xxx",
    "task_type": "schema_driven_query",
    "task_data": {
        "nlq": "查詢 2101 倉庫的庫存"
    }
}

with httpx.Client(timeout=60.0) as client:
    resp = client.post(
        "http://localhost:8004/api/v1/data-agent/jp/execute",
        json=payload
    )
    result = resp.json()

# 處理回應
data = result.get("result", {}).get("data", [])
for row in data:
    item_no = row.get("item_no")      # ✅ 新欄位
    warehouse_no = row.get("warehouse_no")  # ✅ 新欄位
    existing_stocks = row.get("existing_stocks")  # ✅ 新欄位
```

### 2. Data-Agent 直接調用

```python
# ✅ 正確：使用 schema_driven_query 模組
from data_agent.services.schema_driven_query.resolver import Resolver
from data_agent.services.schema_driven_query.executor import ExecutorFactory

resolver = Resolver()
resolver.load_schemas()

# 執行查詢
factory = ExecutorFactory(config)
executor = factory.get_executor()
result = executor.execute(sql)
```

---

## 驗證清單

每次修改 Data-Agent 相關代碼後，必須驗證：

- [ ] SQL 使用 `mart_inventory_wide` 而非 `img_file`
- [ ] SQL 使用 `mart_work_order_wide` 而非 `tlf_file`
- [ ] SQL 使用 `mart_shipping_wide`
- [ ] 欄位使用 `item_no`, `warehouse_no`, `existing_stocks` 等新名稱
- [ ] 倉庫編號使用數字（如 2101, 2700）而非 W01, W03

---

## 違反處理

若發現違反規範：

1. **立即停止**該功能
2. **回滾**到上一個正確版本
3. **報告**給架構負責人
4. **修復**後重新驗證

---

## 參考文檔

- [Data-Agent-JP 規格書](../.ds-docs/Data-Agent/Data-Agent-JP規格書.md)
- [測試報告](./經寶物料管理代理_50測試場景_JPV3_報告.md)
