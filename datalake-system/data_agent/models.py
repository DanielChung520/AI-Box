# 代碼功能說明: Data Agent 數據模型
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Data Agent 數據模型定義"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DataAgentRequest(BaseModel):
    """Data Agent 請求模型"""

    action: str = Field(
        ...,
        description="操作類型（text_to_sql/execute_query/validate_query/get_schema/query_datalake/create_dictionary/get_dictionary/create_schema/validate_data/execute_sql_on_datalake/execute_structured_query）",
    )
    # text_to_sql 參數
    natural_language: Optional[str] = Field(
        None, description="自然語言查詢（text_to_sql 操作需要）"
    )
    database_type: Optional[str] = Field(
        "postgresql", description="數據庫類型（postgresql/mysql/sqlite，可選）"
    )
    schema_info: Optional[Dict[str, Any]] = Field(None, description="數據庫 Schema 信息（可選）")
    intent_analysis: Optional[Dict[str, Any]] = Field(
        None, description="意圖分析結果（text_to_sql 操作可選，用於指導 LLM 生成 SQL）"
    )
    # execute_query 參數
    sql_query: Optional[str] = Field(None, description="SQL 查詢語句（execute_query 操作需要）")
    connection_string: Optional[str] = Field(None, description="數據庫連接字符串（可選）")
    # validate_query 參數
    query: Optional[str] = Field(None, description="查詢語句（validate_query 操作需要）")
    # Datalake 查詢參數
    bucket: Optional[str] = Field(
        None, description="Datalake bucket 名稱（query_datalake 操作需要）"
    )
    key: Optional[str] = Field(None, description="數據鍵（文件路徑，query_datalake 操作需要）")
    query_type: Optional[str] = Field("exact", description="查詢類型（exact/fuzzy，可選）")
    filters: Optional[Dict[str, Any]] = Field(None, description="過濾條件（可選）")
    # execute_sql_on_datalake 參數
    sql_query_datalake: Optional[str] = Field(
        None, description="SQL 查詢語句（execute_sql_on_datalake 操作需要）"
    )
    # 數據字典參數
    dictionary_id: Optional[str] = Field(
        None, description="數據字典 ID（create_dictionary/get_dictionary 操作需要）"
    )
    dictionary_data: Optional[Dict[str, Any]] = Field(
        None, description="數據字典數據（create_dictionary 操作需要）"
    )
    # Schema 參數
    schema_id: Optional[str] = Field(
        None, description="Schema ID（create_schema/get_schema/validate_data 操作需要）"
    )
    schema_data: Optional[Dict[str, Any]] = Field(
        None, description="Schema 數據（create_schema 操作需要）"
    )
    data: Optional[List[Dict[str, Any]]] = Field(
        None, description="待驗證數據（validate_data 操作需要）"
    )
    # 結構化查詢參數（execute_structured_query 使用，由 MM-Agent 提供）
    structured_query: Optional[Dict[str, Any]] = Field(
        None, description="結構化查詢參數（tlf19/part_number/time_expr/table_name等）"
    )
    # 自然語言查詢（execute_structured_query 使用，由 MM-Agent 提供）
    natural_language_query: Optional[str] = Field(
        None, description="自然語言查詢（由 MM-Agent 編排後傳入）"
    )
    # 通用參數
    user_id: Optional[str] = Field(None, description="用戶 ID（可選）")
    tenant_id: Optional[str] = Field(None, description="租戶 ID（可選）")
    timeout: Optional[int] = Field(30, description="查詢超時時間（秒，可選）")
    max_rows: Optional[int] = Field(1000, description="最大返回行數（可選）")
    # 分頁參數
    pagination: Optional[Dict[str, int]] = Field(
        None, description="分頁參數（可選）{page: 頁碼, page_size: 每頁筆數}"
    )
    options: Optional[Dict[str, Any]] = Field(
        None, description="選項（可選）{return_total: 是否返回總筆數}"
    )


class DataAgentResponse(BaseModel):
    """Data Agent 響應模型"""

    success: bool = Field(..., description="是否成功")
    action: str = Field(..., description="操作類型")
    result: Optional[Dict[str, Any]] = Field(None, description="執行結果")
    error: Optional[str] = Field(None, description="錯誤信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元數據")


class TextToSQLRequest(BaseModel):
    """Text-to-SQL 請求模型"""

    natural_language: str = Field(..., description="自然語言查詢")
    database_type: str = Field("postgresql", description="數據庫類型")
    schema_info: Optional[Dict[str, Any]] = Field(None, description="數據庫 Schema 信息")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class TextToSQLResponse(BaseModel):
    """Text-to-SQL 響應模型"""

    sql_query: str = Field(..., description="生成的 SQL 查詢")
    parameters: List[str] = Field(default_factory=list, description="參數列表")
    confidence: float = Field(0.0, description="置信度（0-1）")
    explanation: Optional[str] = Field(None, description="SQL 生成說明")
    warnings: List[str] = Field(default_factory=list, description="警告列表")


class QueryGatewayRequest(BaseModel):
    """查詢閘道請求模型"""

    sql_query: str = Field(..., description="SQL 查詢語句")
    connection_string: Optional[str] = Field(None, description="數據庫連接字符串")
    user_id: Optional[str] = Field(None, description="用戶 ID")
    tenant_id: Optional[str] = Field(None, description="租戶 ID")
    timeout: Optional[int] = Field(30, description="查詢超時時間（秒）")
    max_rows: Optional[int] = Field(1000, description="最大返回行數")


class QueryGatewayResponse(BaseModel):
    """查詢閘道響應模型"""

    success: bool = Field(..., description="是否成功")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="查詢結果行")
    row_count: int = Field(0, description="返回行數")
    execution_time: float = Field(0.0, description="執行時間（秒）")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")
