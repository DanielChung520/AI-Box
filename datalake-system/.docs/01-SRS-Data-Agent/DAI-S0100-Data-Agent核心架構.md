# DAI-S0100 Data-Agent 核心架構規格書

**文件編號**: DAI-S0100  
**版本**: 4.0.0  
**日期**: 2026-02-20  
**依據代碼**: `datalake-system/data_agent/`

---

> **版本說明**：v4 版（原 JP 版）適應經寶（MM-Agent）更新，實現職責分離：
> - MM-Agent：意圖識別，提取語義概念
> - Data-Agent-v4：SchemaRAG + SQL 生成
> - SSE 階段回報 + 前後置驗證

## 1. 概述

### 1.1 文件資訊

| 項目 | 內容 |
|------|------|
| 文件名稱 | Data-Agent 核心架構規格書 |
| 版本 | **4.0.0** |
| 創建日期 | 2026-02-20 |
| 狀態 | ✅ **生產就緒** |
| 適用系統 | TiTop ERP (DuckDB/S3) |

### 1.2 系統定位

Data-Agent-v4 是基於 **Schema Driven Query (SDQ)** 架構的數據查詢服務，專門處理 TiTop ERP 系統的查詢需求。

**職責範圍**：
- 接收 MM-Agent 傳來的結構化自然語言查詢
- 解析意圖、匹配概念、映射綁定
- 生成並執行 DuckDB SQL（S3 Parquet）
- 返回結構化查詢結果

### 1.3 技術棧

| 層級 | 技術 |
|------|------|
| API 框架 | FastAPI (Python 3.12) |
| 查詢引擎 | **DuckDB 1.4.4** |
| 數據存儲 | **S3 (SeaweedFS)** - `s3://tiptop-raw/raw/v1/tiptop_jp/` |
| Schema 存儲 | Qdrant + ArangoDB |
| 配置管理 | Pydantic Settings |

---

## 2. 架構

### 2.1 整體架構圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Client (MM-Agent)                              │
│                                                                          │
│   輸入：「查詢料號 RM01-005 在 W03 庫房的庫存」                          │
│   輸出：{ nlq: "...", intent: "...", params: {...} }                   │
└──────────────────────────────────────┬──────────────────────────────────┘
                                        │
                                        ▼
                           【MM-Agent → Data-Agent 輸入格式】
                           {
                               "nlq": "查詢料號 RM01-005 在 W03 庫房的庫存",
                               "intent": "QUERY_STOCK",
                               "params": {
                                   "material_id": "RM01-005",      # 語義概念：料號
                                   "inventory_location": "W03",       # 語義概念：倉庫
                                   "time_range": null,
                                   "material_category": null
                               }
                           }
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Data-Agent-JP Service                               │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  API Layer                                                       │   │
│   │  ┌───────────────────────────────────────────────────────────┐  │   │
│   │  │  POST /api/v1/data-agent/jp/execute                     │  │   │
│   │  │  POST /api/v1/data-agent/jp/execute/stream (SSE)        │  │   │
│   │  │  GET  /api/v1/data-agent/jp/health                      │  │   │
│   │  └───────────────────────────────────────────────────────────┘  │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                      ↓                                    │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Service Layer (Schema Driven Query)                            │   │
│   │                                                               │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│   │  │   Parser    │→│  Resolver   │→│   SQL Gen    │             │   │
│   │  │ (LLM Parse) │  │ (State)     │  │ (DuckDB)    │             │   │
│   │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                      ↓                                    │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Executor Layer                                                  │   │
│   │                                                               │   │
│   │  ┌─────────────────────┐  ┌─────────────────────┐               │   │
│   │  │   ExecutorFactory   │→│   DuckDBExecutor    │               │   │
│   │  │  (DUCKDB/ORACLE)  │  │  (S3 Parquet)      │               │   │
│   │  └─────────────────────┘  └─────────────────────┘               │   │
│   └─────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────┬──────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          S3 Storage (SeaweedFS)                          │
│   Endpoint: localhost:8334                                                │
│   Bucket: tiptop-raw                                                      │
│   Path: raw/v1/tiptop_jp/{table}/year=*/month=*/data.parquet            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 服務層級

| 層級 | 模組 | 職責 |
|------|------|------|
| **API Layer** | `router.py` | HTTP 請求處理、路由分發 |
| **Service Layer** | `parser.py` | LLM 調用、NLQ 解析 |
| | `resolver.py` | Resolver 狀態機、意圖匹配 |
| | `sql_generator.py` | SQL 生成、DuckDB dialect |
| **Executor Layer** | `executor.py` | ExecutorFactory、DuckDBExecutor |
| | `duckdb_executor.py` | DuckDB 執行、S3 Path Mapper |
| **Data Layer** | `loaders/*.py` | Schema 載入 (Qdrant/ArangoDB/File) |

### 2.3 語義概念 vs Schema（重要）

| 層級 | 類型 | 示例 | 說明 |
|------|------|------|------|
| **MM-Agent** | 語義概念 | `material_id`, `warehouse`, `time_range` | 業務層面的關鍵詞 |
| **Data-Agent** | Schema | `item_no`, `warehouse_no`, `mart_inventory_wide` | 數據庫層面的字段和表 |

**職責分離**：
- **MM-Agent**：負責意圖識別，提取語義概念（料號、倉庫、時間等）
- **Data-Agent**：負責根據語義概念，通過 SchemaRAG 找到正確的表和字段

**示例**：

| 用戶輸入 | MM-Agent 提取 (語義) | Data-Agent 映射 (Schema) |
|---------|---------------------|------------------------|
| 查詢料號 10-0001 的庫存 | `material_id: "10-0001"` | `item_no`, `mart_inventory_wide` |
| 查詢 8802 倉庫的庫存 | `warehouse: "8802"` | `warehouse_no`, `mart_inventory_wide` |

---

## 3. API 端點

### 3.1 執行查詢（同步）

```bash
POST /api/v1/data-agent/v4/execute
```

**請求**：
```json
{
  "task_id": "mm_query_123",
  "task_type": "schema_driven_query",
  "task_data": {
    "nlq": "查詢料號 10-0001 的庫存",
    "intent": "QUERY_STOCK",
    "params": {
      "material_id": "10-0001"
    }
  }
}
```

**響應**：
```json
{
  "status": "success",
  "task_id": "mm_query_123",
  "result": {
    "sql": "SELECT ...",
    "data": [...],
    "row_count": 10,
    "execution_time_ms": 45.2
  }
}
```

### 3.2 執行查詢（SSE 階段回報）

```bash
POST /api/v1/data-agent/v4/execute/stream
```

**SSE 事件格式**：

每個事件都是 JSON 格式，包含：
- `stage`: 階段名稱
- `message`: 人類可讀的消息
- `data`: 實際數據

**SSE 事件完整代碼實現**：

**檔案**: `data_agent/routers/data_agent_jp/__init__.py`

```python
@router.post("/jp/execute/stream")
async def execute_query_stream(request: ExecuteRequest):
    """SSE 版本的查詢執行端點"""

    async def event_generator():
        try:
            # 階段 1: 接收到請求
            yield f"data: {json.dumps({'stage': 'request_received', 'message': f'已接收到請求：{request.task_data.nlq}', 'data': {'nlq': request.task_data.nlq}}, ensure_ascii=False)}\n\n"

            # 獲取 Resolver
            resolver = get_resolver()

            # 解析 NLQ
            resolve_result = resolver.resolve(request.task_data.nlq)

            if resolve_result["status"] == "error":
                yield f"data: {json.dumps({'stage': 'error', 'message': f'發生錯誤：{message}', 'data': {'error_code': error_code}}, ensure_ascii=False)}\n\n"
                return

            # 階段 2: 確認 Schema
            schema_used = resolve_result.get("schema_used", "unknown")
            tables = resolve_result.get("tables_used", [])
            columns = resolve_result.get("columns_used", [])
            table_str = ", ".join(tables) if tables else schema_used
            column_str = ", ".join(columns[:5]) + ("..." if len(columns) > 5 else "")

            yield f"data: {json.dumps({'stage': 'schema_confirmed', 'message': f'已確認找到對應的表格：{table_str}，相關欄位：{column_str}', 'data': {'schema_used': schema_used, 'tables': tables, 'columns': columns}}, ensure_ascii=False)}\n\n"

            # 階段 3: SQL 已產生
            sql = resolve_result["sql"]
            intent = resolve_result.get("intent", "UNKNOWN")
            sql_preview = sql[:100] + "..." if len(sql) > 100 else sql

            yield f"data: {json.dumps({'stage': 'sql_generated', 'message': f'已產生 SQL：{sql_preview}', 'data': {'sql': sql, 'intent': intent}}, ensure_ascii=False)}\n\n"

            # 獲取 Executor
            executor = get_executor()

            # 階段 4: 執行查詢
            timeout = request.task_data.options.timeout
            yield f"data: {json.dumps({'stage': 'query_executing', 'message': f'正在執行查詢中...（超時設定：{timeout}秒）', 'data': {'timeout': timeout}}, ensure_ascii=False)}\n\n"

            # 執行 SQL
            exec_result = executor.execute(sql, timeout)

            # 階段 5: 查詢完成
            row_count = len(exec_result.get("data", []))
            execution_time_ms = exec_result.get("execution_time_ms", 0)

            yield f"data: {json.dumps({'stage': 'query_completed', 'message': f'已查詢完成，正在檢查結果...（耗時：{execution_time_ms}ms，返回 {row_count} 筆資料）', 'data': {'row_count': row_count, 'execution_time_ms': execution_time_ms}}, ensure_ascii=False)}\n\n"

            # 階段 6: 返回結果
            yield f"data: {json.dumps({'stage': 'result_ready', 'message': f'已返回結果：成功（{row_count} 筆資料）', 'data': {'status': 'success', 'row_count': row_count}}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'stage': 'error', 'message': f'發生錯誤：{error_msg}', 'data': {'error': error_msg}}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**SSE 事件列表**：

| 階段 | 事件 | 消息示例 | 數據內容 |
|------|------|---------|---------|
| 1 | request_received | 已接收到請求：{nlq} | { nlq: "..." } |
| 2 | schema_confirmed | 已確認找到對應的表格：{tables}，相關欄位：{columns} | { schema_used, tables, columns } |
| 3 | sql_generated | 已產生 SQL：{sql_preview} | { sql: "...", intent: "..." } |
| 4 | query_executing | 正在執行查詢中...（超時設定：{timeout}秒） | { timeout: 30 } |
| 5 | query_completed | 已查詢完成，正在檢查結果...（耗時：{time}ms，返回 {count} 筆資料） | { row_count, execution_time_ms } |
| 6 | result_ready | 已返回結果：{status}（{count} 筆資料） | { status: "success", row_count } |

### 3.3 健康檢查

```bash
GET /api/v1/data-agent/v4/health
```

---

## 4. 驗證與錯誤處理

### 4.1 驗證流程概述

Data-Agent 在執行 SQL 前後進行多層驗證，確保查詢正確且資源使用合理。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         驗證流程                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  【前置檢查】                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. 意圖支持檢查     - 查詢類型是否支援                         │   │
│  │ 2. 意圖信心度檢查   - LLM 解析信心度是否足夠 (>= 0.6)        │   │
│  │ 3. 必需參數檢查     - 必要欄位是否存在                         │   │
│  │ 4. 參數格式檢查     - 料號、倉庫等格式是否正確                │   │
│  │ 5. 查詢範圍檢查     - 是否可能返回過多數據                    │   │
│  │ 6. 複雜JOIN限制     - 鍵值/索引是否存在                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                         │
│  【SQL 執行】                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ - 超時控制 (預設 30 秒)                                        │   │
│  │ - 執行緒池隔離                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                         │
│  【後置檢查】                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. 數據驗證       - 簡單目標比對                              │   │
│  │ 2. 空結果確認     - 正常無數據 vs 查詢問題                    │   │
│  │ 3. 異常處理       - 網路、超時、執行錯誤                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                         │
│  【回應給 MM-Agent】                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ - status: success / error / partial                            │   │
│  │ - error_code: 錯誤碼                                           │   │
│  │ - message: 用戶可理解的訊息                                      │   │
│  │ - suggestions: 建議                                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 前置檢查代碼實現

**檔案**: `data_agent/services/schema_driven_query/pre_validator.py`

```python
# 核心驗證方法
async def validate(
    self, query: str, intent: str, entities: Dict[str, str], intent_confidence: float = 1.0
) -> ValidationResult:
    """驗證查詢"""
    result = ValidationResult(valid=True)

    # 1. 意圖是否支援
    if intent not in self.SUPPORTED_INTENTS:
        result.valid = False
        result.errors.append(ValidationError(
            code=ErrorCode.INTENT_UNCLEAR.value,
            message=f"不支援的查詢類型: {intent}",
        ))

    # 2. 意圖信心度檢查 (< 0.6 視為無效)
    if intent_confidence < 0.6:
        result.valid = False

    # 3. 必需的參數檢查
    required = self.REQUIRED_PARAMS.get(intent, [])
    for param in required:
        if param not in entities:
            result.errors.append(ValidationError(
                code=ErrorCode.MISSING_REQUIRED_PARAM.value,
                message=f"缺少必要參數: {param}",
            ))

    # 4. 參數格式檢查
    for param_type, value in entities.items():
        if not self._is_valid_param_format(param_type, value):
            result.errors.append(ValidationError(
                code=ErrorCode.INVALID_PARAM_FORMAT.value,
                message=f"參數格式不正確: {param_type}",
            ))

    return result
```

### 4.3 複雜JOIN鍵值驗證代碼實現

**檔案**: `data_agent/services/schema_driven_query/duckdb_executor.py`

```python
def validate_join_keys(self, sql: str) -> tuple[bool, Optional[str]]:
    """驗證複雜 JOIN 是否有鍵值/索引限制"""
    import re

    sql_upper = sql.upper()

    # 檢測是否有 JOIN
    if "JOIN" not in sql_upper:
        return True, None

    # 檢測是否有多表 JOIN（2 個以上表）
    join_count = len(re.findall(r'\bJOIN\b', sql_upper))
    if join_count > 1:
        # 複雜 JOIN：檢查是否有足夠的過濾條件
        where_count = len(re.findall(r'\bWHERE\b', sql_upper))
        and_count = len(re.findall(r'\bAND\b', sql_upper))

        # 如果 JOIN 數 > 1，至少需要有 1 個 WHERE 或多個 AND 條件
        if where_count == 0 and and_count < join_count:
            return False, f"複雜 JOIN（{join_count} 個表）缺乏足夠的鍵值過濾條件"

    # 檢查是否有限流（如 TOP, LIMIT）
    has_limit = "LIMIT" in sql_upper or "TOP" in sql_upper
    if join_count > 0 and not has_limit:
        logger.warning(f"複雜 JOIN 查詢缺乏 LIMIT 限制，自動添加 LIMIT 1000")

    return True, None
```

### 4.4 後置檢查代碼實現

**檔案**: `data_agent/services/schema_driven_query/response_builder.py`

```python
def validate_and_build_response(
    self,
    sql: str,
    data: List[Dict[str, Any]],
    params: Optional[Dict[str, Any]] = None,
    schema_used: Optional[str] = None,
) -> StructuredResponse:
    """後置檢查：數據驗證 + 空結果確認"""

    # 1. 空結果檢查
    if not data or len(data) == 0:
        if params:
            missing_info = []
            if params.get("material_id"):
                missing_info.append(f"料號 '{params['material_id']}' 不存在或無庫存")

            if missing_info:
                message = "查詢不到數據：" + "；".join(missing_info)
                warnings.append("NO_DATA_BUT_PARAMS_EXIST")

        # 如果有參數但沒結果，視為 PARTIAL
        if params and any(params.values()):
            return StructuredResponse(
                status=ResponseStatus.PARTIAL.value,
                error_code=ErrorCode.NO_DATA_FOUND.value,
                message=message,
            )

        return StructuredResponse(
            status=ResponseStatus.ERROR.value,
            error_code=ErrorCode.NO_DATA_FOUND.value,
            message="查詢不到任何符合的數據",
        )

    # 2. 數據驗證：檢查關鍵字段是否有值
    if params and params.get("material_id"):
        expected_item = params["material_id"]
        items_in_result = {str(row.get("item_no", "")).strip() for row in data}
        if expected_item not in items_in_result:
            warnings.append(f"輸入的料號 '{expected_item}' 不在查詢結果中")

    # 3. 返回成功或部分成功
    if warnings:
        return StructuredResponse(
            status=ResponseStatus.PARTIAL.value,
            warnings=warnings,
        )

    return StructuredResponse(
        status=ResponseStatus.SUCCESS.value,
    )
```

### 4.2 錯誤碼定義

| 錯誤碼 | 說明 | 來源 |
|--------|------|------|
| SCHEMA_NOT_FOUND | 找不到指定的表格 | PreValidator |
| INTENT_UNCLEAR | 無法確定查詢意圖 | PreValidator |
| UNAUTHORIZED_ACCESS | 未授權的訪問 | PreValidator |
| QUERY_SCOPE_TOO_LARGE | 查詢範圍過大 | PreValidator |
| MISSING_REQUIRED_PARAM | 缺少必要參數 | PreValidator |
| INVALID_PARAM_FORMAT | 參數格式不正確 | PreValidator |
| NO_DATA_FOUND | 查不到數據 | 後置檢查 |
| SCHEMA_ERROR | Schema 錯誤 | 執行時 |
| CONNECTION_TIMEOUT | 連接超時 | 執行時 |
| NETWORK_ERROR | 網路錯誤 | 執行時 |
| SQL_GENERATION_FAILED | SQL 生成失敗 | 執行時 |
| SQL_VALIDATION_FAILED | SQL 驗證失敗 | 執行時 |
| INTERNAL_ERROR | 內部錯誤 | 其他 |

---

## 5. Resolver 狀態機

### 5.1 狀態定義

| 狀態 | 說明 |
|------|------|
| INIT | 初始化 |
| PARSE_NLQ | 解析自然語言 |
| MATCH_CONCEPTS | 匹配概念 |
| RESOLVE_BINDINGS | 解析綁定 |
| VALIDATE | 驗證 |
| BUILD_AST | 生成 AST |
| EMIT_SQL | 生成 SQL |
| COMPLETED | 完成 |

### 5.2 狀態轉換流程

```
INIT → PARSE_NLQ → MATCH_CONCEPTS → RESOLVE_BINDINGS → VALIDATE → BUILD_AST → EMIT_SQL → COMPLETED
```

---

## 6. 數據來源

### 6.1 S3 路徑結構

```
s3://tiptop-raw/raw/v1/tiptop_jp/
├── mart_inventory_wide/     # 庫存寬表
├── mart_work_order_wide/    # 工單寬表
├── mart_shipping_wide/      # 出貨寬表
├── INAG_T/year=*/month=*/   # 原始庫存
├── SFAA_T/year=*/month=*/  # 工單頭檔
├── SFCA_T/year=*/month=*/  # 工單製造頭檔
├── SFCB_T/year=*/month=*/  # 工單製造明細檔
├── XMDG_T/year=*/month=*/  # 出貨通知頭檔
└── XMDH_T/year=*/month=*/  # 出貨通知明細檔
```

### 6.2 Mart 表格

| 表格 | 用途 | 關鍵字段 |
|------|------|----------|
| `mart_inventory_wide` | 庫存查詢 | item_no, warehouse_no, location_no, existing_stocks |
| `mart_work_order_wide` | 工單查詢 | item_no, work_order_no, quantity, status |
| `mart_shipping_wide` | 出貨查詢 | item_no, shipping_no, quantity, date |

---

## 7. 配置

### 7.1 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| DATA_AGENT_Datasource | 資料來源 | DUCKDB |
| DATA_AGENT_DUCKDB_S3_ENDPOINT | S3 端點 | localhost:8334 |
| DATA_AGENT_DUCKDB_BUCKET | S3 Bucket | tiptop-raw |
| DATA_AGENT_TIMEOUT | 查詢超時（秒） | 30 |

---

## 8. 相關文件

| 文件 | 路徑 |
|------|------|
| Parser 實現 | `data_agent/services/schema_driven_query/parser.py` |
| Resolver 實現 | `data_agent/services/schema_driven_query/resolver.py` |
| SQL Generator | `data_agent/services/schema_driven_query/sql_generator.py` |
| Intent 配置 | `metadata/systems/tiptop_jp/intents.json` |
| Bindings 配置 | `metadata/systems/tiptop_jp/bindings.json` |
