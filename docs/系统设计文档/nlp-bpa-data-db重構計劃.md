# NLP-BPA-Data-DB 重構計劃

**創建日期**: 2026-02-09
**創建人**: Daniel Chung
**版本**: v1.0
**狀態**: 待確認

---

## 零、關鍵教訓（2026-02-09 新增）

### tlf_file_large 欄位問題

**問題描述**：
```
MM-Agent 構造 SQL 時使用了錯誤的欄位名稱：
- ❌ 使用 tlf02（實際不存在於 tlf_file_large）
- ❌ 使用 tlf11（實際應該是 tlf06）
- ✅ 應該由 Data-Agent 根據 schema_registry.json 自動映射
```

**根本原因**：
MM-Agent 直接構造 SQL 時，需要知道具體的欄位名稱。這違反了「職責分離」原則。

**解決方案**：
MM-Agent 只傳遞結構化參數，Data-Agent 根據 schema 自動映射欄位。

### 欄位映射原則

| 場景 | MM-Agent 職責 | Data-Agent 職責 |
|------|--------------|-----------------|
| 料號查詢 | 傳遞 `part_number` | 映射到正確欄位（如 `img01` 或 `tlf01`） |
| 日期範圍 | 傳遞 `start_date`, `end_date` | 映射到正確欄位（如 `tlf06`） |
| 交易類型 | 傳遞 `transaction_type` | 映射到正確欄位（如 `tlf19`） |

### Schema Registry 職責

```json
{
  "tables": {
    "tlf_file_large": {
      "columns": {
        "tlf01": { "alias": "料號", "type": "string" },
        "tlf06": { "alias": "交易日期", "type": "date" },
        "tlf10": { "alias": "數量", "type": "number" },
        "tlf19": { "alias": "交易類型", "type": "string" }
      }
    }
  }
}
```

**Data-Agent 職責**：
- 根據 intent 選擇正確的表
- 根據參數名稱映射到實際欄位
- 處理日期格式轉換

**MM-Agent 職責**：
- 解析用戶意圖
- 產生結構化參數（`part_number`, `start_date`, `end_date`）
- 格式化返回結果

---

## 一、現狀分析

### 1.1 當前問題：重複的 SQL 生成邏輯

**系統中存在 3 套獨立的 SQL 生成邏輯**：

| 服務 | 位置 | SQL 生成方式 | 問題 |
|------|------|-------------|------|
| **MM-Agent** | `stock_service.py` | 直接構造 SQL 模板 | ❌ 重複功能 |
| **MM-Agent** | `sql_generator.py` | 獨立規則引擎 | ❌ 與 Data-Agent 重疊 |
| **MM-Agent** | `mm_agent_chain.py` | LLM 生成 SQL | ❌ 混雜意圖分類 |
| **Data-Agent** | `data_agent/agent.py` | NLP → Text-to-SQL | ✅ 正確位置 |

### 1.2 當前架構（錯誤）

```
User → AI-Box:3000 → MM-Agent:8003
                          │
              ┌───────────┼───────────┐
              ↓           ↓           ↓
      stock_service  sql_generator  mm_agent_chain
              │           │           │
              └───────────┴───────────┘
                          ↓
                   直接執行 SQL
                          ↓
                   DuckDB → Datalake
```

### 1.3 MM-Agent 直接構造 SQL 的函數清單

#### stock_service.py（需刪除）

| 函數 | 行號 | SQL 模板 | 需改造 |
|------|------|---------|--------|
| `query_stock_info()` | 76-82 | `SELECT FROM img_file` | ❌ 刪除 |
| `query_stock_list()` | 145-151 | `SELECT FROM img_file` | ❌ 刪除 |
| `query_transactions()` | 215-223 | `SELECT FROM tlf_file_large` | ❌ 刪除 |
| `query_purchase()` | 271-280 | `SELECT FROM tlf_file_large` | ❌ 刪除 |
| `query_sales()` | 329-338 | `SELECT FROM tlf_file_large` | ❌ 刪除 |

#### sql_generator.py（需評估）

| 函數 | 行號 | 說明 | 需改造 |
|------|------|------|--------|
| `SQLGenerator` | 18-233 | 純規則引擎 | ❌ 移至 Data-Agent |

#### agent.py（需改造）

| 函數 | 行號 | SQL 引用 | 需改造 |
|------|------|---------|--------|
| `_query_stock_info()` | 372-450 | `stock_service.query_stock_list()` | ✅ 改調 Data-Agent |
| `_query_stock_history()` | 459-529 | `stock_service.query_transactions()` | ✅ 改調 Data-Agent |

#### shortage_analyzer.py（需改造）

| 函數 | 行號 | SQL 引用 | 需改造 |
|------|------|---------|--------|
| `analyze_shortage()` | 63 | `stock_service.query_stock_info()` | ✅ 改調 Data-Agent |

---

## 二、目標架構

### 2.1 正確架構

```
User → AI-Box:3000 → MM-Agent:8003 (意圖分類 + 結構化需求)
                          │
                          ↓
                    Data-Agent:8004
                          │
              ┌───────────┴───────────┐
              ↓                       ↓
        比對 schema          Text-to-SQL
              │                       │
              └───────────┬───────────┘
                          ↓
                   DuckDB → Datalake
```

### 2.2 職責分離原則

| 服務 | 職責 | 禁止事項 |
|------|------|----------|
| **MM-Agent** | 意圖分類、產生結構化查詢需求、格式化結果 | ❌ 禁止直接構造 SQL |
| **Data-Agent** | 比對 schema、Text-to-SQL、執行查詢 | ❌ 禁止進行意圖分類 |

### 2.3 數據流向

```
Step 1: User Input
          ↓
Step 2: MM-Agent 意圖分類
          ↓
Step 3: 產生結構化需求 {intent, parameters}
          ↓
Step 4: Data-Agent 比對 schema
          ↓
Step 5: Data-Agent Text-to-SQL
          ↓
Step 6: DuckDB 執行
          ↓
Step 7: MM-Agent 格式化結果
          ↓
Step 8: User Output
```

---

## 三、接口定義

### 3.1 MM-Agent → Data-Agent 接口

#### 原則：MM-Agent 傳遞語義參數，Data-Agent 處理欄位映射

**錯誤做法**（職責不清）：
```json
{
  "parameters": {
    "tlf01": "10-0012",
    "tlf06": "2024-02-09"
  }
}
```

**正確做法**（職責分離）：
```json
{
  "parameters": {
    "part_number": "10-0012",
    "start_date": "2024-02-09",
    "end_date": "2026-02-09"
  }
}
```

#### 接口：execute_structured_query

**請求格式**：
```json
{
  "task_id": "uuid-string",
  "task_type": "structured_query",
  "task_data": {
    "intent": "query_stock_history",
    "parameters": {
      "part_number": "10-0012",
      "start_date": "2024-02-09",
      "end_date": "2026-02-09",
      "warehouse": null,
      "limit": 100
    }
  },
  "metadata": {}
}
```

**響應格式**：
```json
{
  "status": "completed",
  "result": {
    "success": true,
    "rows": [
      {
        "seq": "10-0012",
        "part_number": "10-0012",
        "transaction_type": "102",
        "trans_date": "2025-12-31",
        "quantity": 16,
        "warehouse": "W03"
      }
    ],
    "row_count": 21387,
    "sql_query": "SELECT ...",
    "schema": {...}
  },
  "error": null
}
```

### 3.2 Intent → SQL 映射規則

**原則**：Data-Agent 根據 schema_registry.json 自動映射欄位

| Intent | 目標表 | MM-Agent 傳遞 | Data-Agent 映射 |
|--------|--------|---------------|-----------------|
| `query_stock_info` | img_file | `{part_number, warehouse}` | `img01`=料號, `img02`=倉庫 |
| `query_stock_history` | tlf_file_large | `{part_number, start_date, end_date}` | `tlf01`=料號, `tlf06`=日期 |
| `query_purchase` | tlf_file_large | `{part_number, month}` | `tlf01`=料號, `tlf19`='101' |
| `query_sales` | tlf_file_large | `{part_number, month}` | `tlf01`=料號, `tlf19`='202' |
| `analyze_shortage` | img_file + tlf_file | `{part_number}` | 複雜聚合 |

**SQL 生成（Data-Agent 內部）**：
```python
# Data-Agent 根據 schema 自動生成
def generate_sql(intent: str, parameters: dict) -> str:
    schema = load_schema_registry()
    table = INTENT_TABLE_MAP[intent]
    columns = schema[table]["columns"]
    
    # 映射參數到欄位
    field_map = {
        "part_number": columns["tlf01"].name,  # 映射到 tlf01
        "start_date": columns["tlf06"].name,    # 映射到 tlf06
    }
    
    # 生成 SQL
    return f"SELECT ... FROM {table} WHERE {field_map['part_number']}=..."
```

### 3.3 Schema Registry 映射

**檔案位置**: `datalake-system/metadata/schema_registry.json`

```json
{
  "tables": {
    "img_file": {
      "path": "s3://bucket/raw/v1/img_file/year=*/*/data.parquet",
      "columns": {
        "img01": "料號",
        "img02": "倉庫",
        "img04": "批號",
        "img10": "數量"
      }
    },
    "tlf_file_large": {
      "path": "s3://bucket/raw/v1/tlf_file_large/**/*.parquet",
      "columns": {
        "tlf01": "料號",
        "tlf06": "交易日期",
        "tlf10": "數量(正入負出)",
        "tlf13": "來源單號",
        "tlf19": "交易類型",
        "tlf061": "倉庫",
        "tlf062": "儲位"
      }
    }
  }
}
```

---

## 四、重構步驟

### Step 1: Data-Agent 新增結構化查詢接口

**目標**: Data-Agent 支援接收結構化參數，根據 schema_registry.json 自動映射欄位

**新增檔案**: `datalake-system/data_agent/structured_query_handler.py`

**職責**:
- 接收 `{intent, parameters}`
- 根據 intent 查詢 schema_registry.json
- 自動映射參數到實際欄位（如 `part_number` → `tlf01`）
- 生成並執行 SQL
- 返回結果

**核心原則**：
```python
# ❌ 錯誤：MM-Agent 知道欄位名稱
sql = f"SELECT tlf06 FROM tlf_file_large WHERE tlf01 = '{part_number}'"

# ✅ 正確：Data-Agent 根據 schema 自動映射
def map_parameters_to_columns(parameters: dict, intent: str) -> dict:
    schema = load_schema()
    column_mapping = {
        "part_number": schema.table(intent).column("tlf01"),  # 實際欄位
        "start_date": schema.table(intent).column("tlf06"),  # 實際欄位
    }
    return {
        column_mapping[k].name: v for k, v in parameters.items()
    }
```

**接口**:
```python
class StructuredQueryHandler:
    async def execute(
        self,
        intent: str,
        parameters: Dict[str, Any]
    ) -> QueryResult:
        """執行結構化查詢"""
```

**檢查點**:
- [ ] 接口文檔已定義
- [ ] schema_registry.json 已包含所有欄位映射
- [ ] 日期格式轉換已處理（用戶輸入 → SQL 格式）
- [ ] 單元測試通過
- [ ] 與現有 text_to_sql 共存

#### 日期格式轉換（Data-Agent 職責）

```python
# Data-Agent 處理日期格式轉換
def normalize_date(date_input: str) -> str:
    """
    用戶輸入: "前兩年", "2024年1月", "2024-02-09"
    SQL 格式:   "2024-02-09"
    """
    # 解析自然語言日期
    if "前兩年" in date_input:
        return (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    
    # 處理中文格式
    if "年" in date_input:
        return parse_chinese_date(date_input)  # "2024年1月" → "2024-01-01"
    
    return date_input  # 已是標準格式
```

---

### Step 2: 改造 MM-Agent Agent.py

**目標**: MM-Agent 不再直接構造 SQL，改調 Data-Agent

**核心原則**：
```python
# ❌ 錯誤示範：MM-Agent 知道欄位名稱
sql = f"SELECT tlf06, tlf10 FROM tlf_file_large WHERE tlf01 = '{part_number}'"

# ✅ 正確做法：MM-Agent 只傳語義參數
result = await data_agent_client.execute_structured_query(
    intent="query_stock_history",
    parameters={
        "part_number": part_number,      # 語義參數
        "start_date": start_date,        # 語義參數
        "end_date": end_date             # 語義參數
    }
)
# Data-Agent 知道 tlf01=料號, tlf06=日期
```

**修改檔案**: `datalake-system/mm_agent/agent.py`

**改造函數**:

| 函數 | 原行為 | 新行為 |
|------|-------|-------|
| `_query_stock_info()` | 調 `stock_service` | 調 `data_agent_client.structured_query()` |
| `_query_stock_history()` | 調 `stock_service` | 調 `data_agent_client.structured_query()` |

**改造後流程**:
```python
async def _query_stock_history(self, part_number, request, semantic_result):
    # Step 1: 從 semantic_result 提取參數
    parameters = {
        "part_number": part_number,
        "start_date": semantic_result.parameters.get("start_date"),
        "end_date": semantic_result.parameters.get("end_date"),
        "limit": 100
    }
    
    # Step 2: 調用 Data-Agent
    result = await self._data_agent_client.execute_structured_query(
        intent="query_stock_history",
        parameters=parameters
    )
    
    # Step 3: 格式化結果
    return self._format_stock_history_result(result)
```

**檢查點**:
- [ ] `stock_service.query_*()` 調用已替換
- [ ] 返回格式相容
- [ ] 錯誤處理正確

---

### Step 3: 改造 ShortageAnalyzer

**目標**: 缺料分析改調 Data-Agent

**修改檔案**: `datalake-system/mm_agent/services/shortage_analyzer.py`

**改造函數**:
| 函數 | 原行為 | 新行為 |
|------|-------|-------|
| `analyze_shortage()` | 調 `stock_service.query_stock_info()` | 調 `data_agent_client.structured_query()` |

**檢查點**:
- [ ] 缺料分析功能正常
- [ ] 結果格式一致

---

### Step 4: 清理 StockService

**目標**: 刪除 stock_service.py 中的 SQL 模板

**刪除檔案**: `datalake-system/mm_agent/services/stock_service.py`

**刪除內容**:
- [ ] `query_stock_info()` - SQL 模板
- [ ] `query_stock_list()` - SQL 模板
- [ ] `query_transactions()` - SQL 模板
- [ ] `query_purchase()` - SQL 模板
- [ ] `query_sales()` - SQL 模板

**保留內容**:
- `DataAgentClient` 初始化
- 業務邏輯封裝（如有）

**檢查點**:
- [ ] 無 SQL 模板殘留
- [ ] import 語句已清理
- [ ] 單元測試通過

---

### Step 5: 評估 SQLGenerator

**目標**: 決定 sql_generator.py 去留

**選項**:
- **A**: 移至 Data-Agent
- **B**: 刪除（使用 LLM text_to_sql 替代）

**建議**: 移至 Data-Agent，作為結構化查詢的 fallback

**檢查點**:
- [ ] 去留決定已確認
- [ ] 代碼已遷移或刪除

---

## 五、需清除的代碼清單

### 5.1 完整刪除

| 檔案 | 原因 |
|------|------|
| `mm_agent/services/stock_service.py` | SQL 模板重複 |

### 5.2 部分修改

| 檔案 | 修改內容 |
|------|---------|
| `mm_agent/agent.py` | 移除 `from .services.stock_service import StockService` |
| `mm_agent/agent.py` | `_query_stock_info()` 改調 Data-Agent |
| `mm_agent/agent.py` | `_query_stock_history()` 改調 Data-Agent |
| `mm_agent/services/shortage_analyzer.py` | 移除 `from .stock_service import StockService` |
| `mm_agent/services/shortage_analyzer.py` | `analyze_shortage()` 改調 Data-Agent |

### 5.3 遷移至 Data-Agent

| 檔案 | 遷移目標 |
|------|---------|
| `mm_agent/sql_generator.py` | `data_agent/sql_template_engine.py` |

---

## 六、測試計劃

### Phase 1: 單元測試

#### Data-Agent 結構化查詢接口測試

**測試檔案**: `tests/data_agent/test_structured_query.py`

```python
async def test_query_stock_history():
    handler = StructuredQueryHandler()
    result = await handler.execute(
        intent="query_stock_history",
        parameters={
            "part_number": "10-0012",
            "start_date": "2024-02-09",
            "end_date": "2026-02-09"
        }
    )
    assert result.success == True
    assert result.row_count > 0
```

**測試場景**:
| 場景 | 預期結果 |
|------|---------|
| 有效料號 + 日期範圍 | 返回交易記錄 |
| 無效料號 | 返回空結果 |
| 缺少必要參數 | 返回錯誤 |

#### MM-Agent 改造後測試

**測試檔案**: `tests/mm_agent/test_structured_integration.py`

```python
async def test_query_stock_history_via_data_agent():
    agent = MMAgent()
    response = await agent.handle_request({
        "task_data": {
            "instruction": "料號10-0012，前兩年的進出庫存交易"
        }
    })
    assert response.success == True
    assert "transactions" in response.result
```

---

### Phase 2: 整合測試

#### AI-Box API 端到端測試

**測試命令**:
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "料號10-0012，前兩年的進出庫存交易"}],
    "agent_id": "mm-agent"
  }'
```

**預期結果**:
- MM-Agent 返回 `success: true`
- 結果包含 `transactions` 列表
- 數據來自 `tlf_file_large` 表

**檢查點**:
| 檢查項 | 狀態 |
|--------|------|
| API 返回 200 | ⏳ |
| `success: true` | ⏳ |
| 資料來自 Data-Agent | ⏳ |
| 響應格式正確 | ⏳ |

---

### Phase 3: 業務場景測試

#### 場景清單

| # | 測試場景 | 驗證重點 |
|---|---------|---------|
| 1 | 查詢料號庫存 | `query_stock_info` |
| 2 | 查詢交易歷史 | `query_stock_history` |
| 3 | 查詢採購記錄 | `query_purchase` |
| 4 | 查詢銷售記錄 | `query_sales` |
| 5 | 缺料分析 | `analyze_shortage` |

---

## 七、風險評估

### 高風險

| 風險 | 影響 | 緩解措施 |
|------|-----|---------|
| SQL 模板移除 | 查詢功能失效 | 保留舊接口作為 fallback |
| Schema 變更 | 查詢錯誤 | 單元測試覆蓋所有 intent |

### 中風險

| 風險 | 影響 | 緩解措施 |
|------|-----|---------|
| 接口不兼容 | 整合失敗 | 逐步替換 |
| 性能下降 | 響應變慢 | 添加缓存 |

---

## 八、驗收標準

### 功能驗收

- [ ] 所有 Intent 查詢正常
- [ ] 數據來源統一為 Data-Agent
- [ ] 無 SQL 模板殘留於 MM-Agent

### 架構驗收

- [ ] 職責分離清晰
- [ ] 接口文檔完整
- [ ] 測試覆蓋率 > 80%

---

## 九、下一步行動

### 確認階段（待用戶確認）

1. 閱讀本文檔
2. 確認重構範圍
3. 確認測試策略

### 執行階段

1. Step 1: Data-Agent 新增接口
2. Step 2: 改造 MM-Agent
3. Step 3: 改造 ShortageAnalyzer
4. Step 4: 清理 StockService
5. Step 5: 評估 SQLGenerator
6. Phase 1-3: 測試驗證

---

## 十、進度管控表

### 10.1 總體進度

| 階段 | 任務 | 負責人 | 開始日期 | 結束日期 | 狀態 | 進度 |
|------|------|--------|----------|----------|------|------|
| - | 文檔確認 | - | 2026-02-09 | 2026-02-09 | ✅ 已完成 | 100% |
| Step 1 | Data-Agent 新增結構化查詢接口 | - | 2026-02-09 | 2026-02-09 | ✅ 已完成 | 100% |
| Step 2 | MM-Agent agent.py 改造 | - | 2026-02-09 | 2026-02-09 | ✅ 已完成 | 100% |
| Step 3 | ShortageAnalyzer 改造 | - | 2026-02-09 | 2026-02-09 | ✅ 已完成 | 100% |
| Step 4 | StockService 清理 | - | 2026-02-09 | 2026-02-09 | ✅ 已完成 | 100% |
| Step 5 | SQLGenerator 評估 | - | 2026-02-09 | 2026-02-09 | ✅ 已完成 | 100% |
| | | | | | | |
| | **評估結果** | | | | | |
| | `sql_generator.py` | Data-Agent 使用中 | **保留**（正確位置） |
| Phase 1-3 | 測試驗證 | - | 2026-02-09 | 2026-02-09 | ✅ 已完成 | 100% |

### 10.2 Step 1 詳細進度：Data-Agent 新增結構化查詢接口

| 子任務 | 狀態 | 預估工時 | 實際工時 | 完成日期 |
|--------|------|---------|---------|----------|
| 設計接口規格 | 待開始 | 2h | - | - |
| 新增 structured_query_handler.py | 待開始 | 4h | - | - |
| 實作欄位映射邏輯 | 待開始 | 4h | - | - |
| 實作日期格式轉換 | 待開始 | 2h | - | - |
| 更新 schema_registry.json | 待開始 | 1h | - | - |
| 單元測試 | 待開始 | 2h | - | - |

### 10.3 Step 2 詳細進度：MM-Agent agent.py 改造

| 子任務 | 狀態 | 預估工時 | 實際工時 | 完成日期 |
|--------|------|---------|---------|----------|
| 修改 _query_stock_info() | 待開始 | 2h | - | - |
| 修改 _query_stock_history() | 待開始 | 2h | - | - |
| 移除 stock_service import | 待開始 | 0.5h | - | - |
| 整合測試 | 待開始 | 1h | - | - |

### 10.4 Step 3 詳細進度：ShortageAnalyzer 改造

| 子任務 | 狀態 | 預估工時 | 實際工時 | 完成日期 |
|--------|------|---------|---------|----------|
| 修改 analyze_shortage() | 待開始 | 2h | - | - |
| 移除 stock_service import | 待開始 | 0.5h | - | - |
| 整合測試 | 待開始 | 1h | - | - |

### 10.5 Step 4 詳細進度：StockService 清理

| 子任務 | 狀態 | 預估工時 | 實際工時 | 完成日期 |
|--------|------|---------|---------|----------|
| 備份 stock_service.py | 待開始 | 0.5h | - | - |
| 刪除 SQL 模板函數 | 待開始 | 2h | - | - |
| 清理 import 語句 | 待開始 | 0.5h | - | - |
| 驗證無引用殘留 | 待開始 | 1h | - | - |

### 10.6 測試階段進度

| 測試場景 | 狀態 | 測試日期 | 測試人員 | 結果 |
|----------|------|----------|----------|------|
| Data-Agent 接口單元測試 | 待開始 | - | - | - |
| MM-Agent 改造整合測試 | 待開始 | - | - | - |
| API 端到端測試 | 待開始 | - | - | - |
| 查詢料號庫存 | 待開始 | - | - | - |
| 查詢交易歷史 | 待開始 | - | - | - |
| 查詢採購記錄 | 待開始 | - | - | - |
| 查詢銷售記錄 | 待開始 | - | - | - |
| 缺料分析 | 待開始 | - | - | - |

---

## 十一、狀態說明

### 11.1 任務狀態定義

| 狀態 | 符號 | 說明 |
|------|------|------|
| 待確認 | ⏳ | 任務尚未被確認，等待審批 |
| 待開始 | 📋 | 已確認，等待分配資源開始 |
| 進行中 | 🔄 | 正在執行中 |
| 待審批 | 👁 | 已完成，等待審查驗收 |
| 已完成 | ✅ | 已驗收通過 |
| 已取消 | ❌ | 已取消，不再執行 |
| 阻礙中 | ⚠️ | 遇到阻礙，需要協助解決 |

### 11.2 進度百分比計算

| 階段 | 計算方式 |
|------|---------|
| Step 1 | (已完成子任務數 / 總子任務數) × 100% |
| Step 2 | (已完成子任務數 / 總子任務數) × 100% |
| Step 3 | (已完成子任務數 / 總子任務數) × 100% |
| Step 4 | (已完成子任務數 / 總子任務數) × 100% |
| Step 5 | (已完成子任務數 / 總子任務數) × 100% |
| Phase 1-3 | (已通過測試數 / 總測試數) × 100% |
| **總體** | 所有階段完成度的加權平均 |

### 11.3 風險狀態

| 風險等級 | 符號 | 說明 | 處理方式 |
|----------|------|------|---------|
| 高 | 🔴 | 可能導致項目失敗 | 立即處理 |
| 中 | 🟡 | 可能影響進度 | 密切監控 |
| 低 | 🟢 | 影響可控 | 定期檢查 |

### 11.4 當前風險狀態

| 風險 | 等級 | 狀態 | 負責人 | 預計解決日期 |
|------|------|------|--------|--------------|
| Schema 變更導致查詢錯誤 | 🔴 | 監控中 | - | - |
| 接口兼容性問題 | 🟡 | 監控中 | - | - |
| 性能下降 | 🟢 | 正常 | - | - |

---

## 十二、更新紀錄

| 日期 | 版本 | 更新內容 | 更新人 |
|------|------|---------|--------|
| 2026-02-09 | v1.0 | 初稿建立 | Daniel Chung |
| 2026-02-09 | v1.1 | 新增「零、關鍵教訓」章節，強調 tlf_file_large 欄位問題 | Daniel Chung |
| 2026-02-09 | v1.2 | 新增「十、進度管控表」和「十一、狀態說明」章節 | Daniel Chung |

---

**文檔狀態**: 待確認
**最後更新**: 2026-02-09
**建立者**: Daniel Chung
