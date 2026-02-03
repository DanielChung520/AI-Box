# 代碼功能說明: Data Agent 實現
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Data Agent 實現 - 數據查詢專屬服務 Agent"""

import logging

# 導入 AI-Box 項目的模塊（datalake-system 在 AI-Box 項目中）
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)

from .config_manager import get_config
from .datalake_service import DatalakeService
from .dictionary_service import DictionaryService
from .models import DataAgentRequest, DataAgentResponse
from .query_gateway import QueryGatewayService
from .schema_service import SchemaService
from .structured_query_builder import StructuredQueryBuilder
from .text_to_sql import TextToSQLService

logger = logging.getLogger(__name__)


class DataAgent(AgentServiceProtocol):
    """Data Agent - 數據查詢專屬服務 Agent

    提供數據查詢相關服務：
    - Text-to-SQL 轉換（text_to_sql）
    - 安全查詢執行（execute_query）
    - 查詢驗證（validate_query）
    - Schema 查詢（get_schema）
    """

    def __init__(
        self,
        text_to_sql_service: Optional[TextToSQLService] = None,
        query_gateway_service: Optional[QueryGatewayService] = None,
        datalake_service: Optional[DatalakeService] = None,
        dictionary_service: Optional[DictionaryService] = None,
        schema_service: Optional[SchemaService] = None,
    ):
        """
        初始化 Data Agent

        Args:
            text_to_sql_service: Text-to-SQL 服務（可選，如果不提供則自動創建）
            query_gateway_service: 查詢閘道服務（可選，如果不提供則自動創建）
            datalake_service: Datalake 查詢服務（可選，如果不提供則自動創建）
            dictionary_service: 數據字典服務（可選，如果不提供則自動創建）
            schema_service: Schema 服務（可選，如果不提供則自動創建）
        """
        # 讀取配置
        config = get_config()
        logger.info(f"Data-Agent 初始化，使用配置: llm_models={config.get_llm_models()[:2]}...")

        self._text_to_sql_service = text_to_sql_service or TextToSQLService()
        self._query_gateway_service = query_gateway_service or QueryGatewayService()
        self._datalake_service = datalake_service or DatalakeService()
        self._dictionary_service = dictionary_service or DictionaryService()
        self._schema_service = schema_service or SchemaService()
        self._logger = logger

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        執行數據查詢任務

        Args:
            request: Agent 服務請求

        Returns:
            Agent 服務響應
        """
        try:
            # 解析請求數據
            task_data = request.task_data
            data_request = DataAgentRequest(**task_data)
            action = data_request.action

            # 根據操作類型執行相應功能
            if action == "text_to_sql":
                result = await self._handle_text_to_sql(data_request)
            elif action == "execute_query":
                result = await self._handle_execute_query(data_request)
            elif action == "validate_query":
                result = await self._handle_validate_query(data_request)
            elif action == "get_schema":
                result = await self._handle_get_schema(data_request)
            elif action == "query_datalake":
                result = await self._handle_query_datalake(data_request)
            elif action == "create_dictionary":
                result = await self._handle_create_dictionary(data_request)
            elif action == "get_dictionary":
                result = await self._handle_get_dictionary(data_request)
            elif action == "create_schema":
                result = await self._handle_create_schema(data_request)
            elif action == "validate_data":
                result = await self._handle_validate_data(data_request)
            elif action == "execute_sql_on_datalake":
                result = await self._handle_execute_sql_on_datalake(data_request)
            elif action == "execute_structured_query":
                result = await self._handle_execute_structured_query(data_request)
            else:
                result = DataAgentResponse(
                    success=False,
                    action=action,
                    error=f"Unknown action: {action}",
                )

            # 構建響應
            return AgentServiceResponse(
                task_id=request.task_id,
                status="completed" if result.success else "failed",
                result=result.model_dump(),
                error=result.error,
                metadata=request.metadata,
            )

        except Exception as e:
            self._logger.error(f"Data Agent execution failed: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,
                error=str(e),
                metadata=request.metadata,
            )

    async def _handle_text_to_sql(self, request: DataAgentRequest) -> DataAgentResponse:
        """處理 Text-to-SQL 轉換請求"""
        if not request.natural_language:
            return DataAgentResponse(
                success=False,
                action="text_to_sql",
                error="natural_language is required for text_to_sql action",
            )

        self._logger.info(f"Text-to-SQL 請求開始: {request.natural_language[:100]}...")

        try:
            # 調用 Text-to-SQL 服務
            result = await self._text_to_sql_service.convert(
                natural_language=request.natural_language,
                database_type=request.database_type or "postgresql",
                schema_info=request.schema_info,
                context={"user_id": request.user_id, "tenant_id": request.tenant_id},
                intent_analysis=request.intent_analysis,  # 傳遞意圖分析
            )

            self._logger.info(f"Text-to-SQL 轉換完成，置信度: {result.get('confidence', 0):.2f}")

            # 前置授權檢查：攔截數據修改操作（企業級 AI 要求）
            sql_query = result.get("sql_query", "")
            if sql_query:
                sql_upper = sql_query.upper()
                dangerous_operations = [
                    "INSERT",
                    "UPDATE",
                    "DELETE",
                    "DROP",
                    "TRUNCATE",
                    "ALTER",
                    "CREATE TABLE",
                    "CREATE INDEX",
                ]
                for operation in dangerous_operations:
                    if operation in sql_upper:
                        self._logger.warning(
                            f"前置異常：檢測到未授權操作: {operation}，回報前置異常"
                        )
                        return DataAgentResponse(
                            success=False,
                            action="text_to_sql",
                            error="未被授權做資料查詢以外的變更操作",
                            result={"sql_query": sql_query, "error_type": "authorization_denied"},
                        )

            return DataAgentResponse(
                success=True,
                action="text_to_sql",
                result=result,
            )

        except Exception as e:
            self._logger.error(f"Text-to-SQL conversion failed: {e}", exc_info=True)
            return DataAgentResponse(
                success=False,
                action="text_to_sql",
                error=str(e),
            )

    async def _handle_execute_query(self, request: DataAgentRequest) -> DataAgentResponse:
        """處理查詢執行請求"""
        if not request.sql_query:
            return DataAgentResponse(
                success=False,
                action="execute_query",
                error="sql_query is required for execute_query action",
            )

        try:
            # 調用查詢閘道服務
            result = await self._query_gateway_service.execute_query(
                sql_query=request.sql_query,
                connection_string=request.connection_string,
                timeout=request.timeout or 30,
                max_rows=request.max_rows or 1000,
                user_id=request.user_id,
                tenant_id=request.tenant_id,
            )

            if not result.get("success", False):
                return DataAgentResponse(
                    success=False,
                    action="execute_query",
                    error=result.get("error", "Query execution failed"),
                    result=result,
                )

            return DataAgentResponse(
                success=True,
                action="execute_query",
                result=result,
            )

        except Exception as e:
            self._logger.error(f"Query execution failed: {e}")
            return DataAgentResponse(
                success=False,
                action="execute_query",
                error=str(e),
            )

    async def _handle_validate_query(self, request: DataAgentRequest) -> DataAgentResponse:
        """處理查詢驗證請求"""
        if not request.query:
            return DataAgentResponse(
                success=False,
                action="validate_query",
                error="query is required for validate_query action",
            )

        try:
            # 調用查詢閘道服務驗證
            validation = self._query_gateway_service.validate_query(
                sql_query=request.query,
                user_id=request.user_id,
                tenant_id=request.tenant_id,
            )

            # API 總是返回 success=True（除非有異常）
            # 驗證結果在 result.valid 中
            return DataAgentResponse(
                success=True,
                action="validate_query",
                result=validation,
                error=None,
            )

        except Exception as e:
            self._logger.error(f"Query validation failed: {e}")
            return DataAgentResponse(
                success=False,
                action="validate_query",
                error=str(e),
            )

    async def _handle_get_schema(self, request: DataAgentRequest) -> DataAgentResponse:
        """處理 Schema 查詢請求"""
        if not request.schema_id:
            return DataAgentResponse(
                success=False,
                action="get_schema",
                error="schema_id is required for get_schema action",
            )

        try:
            result = await self._schema_service.get(request.schema_id)
            if not result.get("success"):
                return DataAgentResponse(
                    success=False,
                    action="get_schema",
                    error=result.get("error", "Schema query failed"),
                    result=result,
                )

            return DataAgentResponse(
                success=True,
                action="get_schema",
                result=result,
            )

        except Exception as e:
            self._logger.error(f"Get schema failed: {e}")
            return DataAgentResponse(
                success=False,
                action="get_schema",
                error=str(e),
            )

    async def _handle_query_datalake(self, request: DataAgentRequest) -> DataAgentResponse:
        """處理 Datalake 查詢請求"""
        if not request.bucket or not request.key:
            return DataAgentResponse(
                success=False,
                action="query_datalake",
                error="bucket and key are required for query_datalake action",
            )

        try:
            result = await self._datalake_service.query(
                bucket=request.bucket,
                key=request.key,
                query_type=request.query_type or "exact",
                filters=request.filters,
                user_id=request.user_id,
                tenant_id=request.tenant_id,
            )

            if not result.get("success"):
                return DataAgentResponse(
                    success=False,
                    action="query_datalake",
                    error=result.get("error", "Query failed"),
                    result=result,
                )

            return DataAgentResponse(
                success=True,
                action="query_datalake",
                result=result,
            )

        except Exception as e:
            self._logger.error(f"Datalake query failed: {e}")
            return DataAgentResponse(
                success=False,
                action="query_datalake",
                error=str(e),
            )

    async def _handle_create_dictionary(self, request: DataAgentRequest) -> DataAgentResponse:
        """處理創建數據字典請求"""
        if not request.dictionary_id or not request.dictionary_data:
            return DataAgentResponse(
                success=False,
                action="create_dictionary",
                error="dictionary_id and dictionary_data are required for create_dictionary action",
            )

        try:
            # 將 dictionary_id 合併到 dictionary_data 中
            # 數據字典服務期望 data 中包含 dictionary_id 字段
            dictionary_data = request.dictionary_data.copy()
            if "dictionary_id" not in dictionary_data:
                dictionary_data["dictionary_id"] = request.dictionary_id

            result = await self._dictionary_service.create(
                dictionary_id=request.dictionary_id,
                data=dictionary_data,
                user_id=request.user_id,
                tenant_id=request.tenant_id,
            )

            if not result.get("success"):
                return DataAgentResponse(
                    success=False,
                    action="create_dictionary",
                    error=result.get("error", "Create dictionary failed"),
                    result=result,
                )

            return DataAgentResponse(
                success=True,
                action="create_dictionary",
                result=result,
            )

        except Exception as e:
            self._logger.error(f"Create dictionary failed: {e}")
            return DataAgentResponse(
                success=False,
                action="create_dictionary",
                error=str(e),
            )

    async def _handle_get_dictionary(self, request: DataAgentRequest) -> DataAgentResponse:
        """處理查詢數據字典請求"""
        if not request.dictionary_id:
            return DataAgentResponse(
                success=False,
                action="get_dictionary",
                error="dictionary_id is required for get_dictionary action",
            )

        try:
            result = await self._dictionary_service.get(request.dictionary_id)
            if not result.get("success"):
                return DataAgentResponse(
                    success=False,
                    action="get_dictionary",
                    error=result.get("error", "Get dictionary failed"),
                    result=result,
                )

            return DataAgentResponse(
                success=True,
                action="get_dictionary",
                result=result,
            )

        except Exception as e:
            self._logger.error(f"Get dictionary failed: {e}")
            return DataAgentResponse(
                success=False,
                action="get_dictionary",
                error=str(e),
            )

    async def _handle_create_schema(self, request: DataAgentRequest) -> DataAgentResponse:
        """處理創建 Schema 請求"""
        if not request.schema_id or not request.schema_data:
            return DataAgentResponse(
                success=False,
                action="create_schema",
                error="schema_id and schema_data are required for create_schema action",
            )

        try:
            # 將 schema_data 包裝成 Schema 服務期望的格式
            # Schema 服務期望 data 中包含 json_schema 字段
            schema_data = request.schema_data
            if "json_schema" not in schema_data:
                # 如果 schema_data 本身就是 JSON Schema，則包裝它
                schema_data = {"json_schema": schema_data}

            result = await self._schema_service.create(
                schema_id=request.schema_id,
                data=schema_data,
                user_id=request.user_id,
                tenant_id=request.tenant_id,
            )

            if not result.get("success"):
                return DataAgentResponse(
                    success=False,
                    action="create_schema",
                    error=result.get("error", "Create schema failed"),
                    result=result,
                )

            return DataAgentResponse(
                success=True,
                action="create_schema",
                result=result,
            )

        except Exception as e:
            self._logger.error(f"Create schema failed: {e}")
            return DataAgentResponse(
                success=False,
                action="create_schema",
                error=str(e),
            )

    async def _handle_execute_sql_on_datalake(self, request: DataAgentRequest) -> DataAgentResponse:
        """處理 Datalake 上 SQL 查詢請求"""
        if not request.sql_query_datalake:
            return DataAgentResponse(
                success=False,
                action="execute_sql_on_datalake",
                error="sql_query_datalake is required for execute_sql_on_datalake action",
            )

        self._logger.info(f"SQL 查詢（Datalake）開始: {request.sql_query_datalake[:100]}...")

        try:
            result = await self._datalake_service.query_sql(
                sql_query=request.sql_query_datalake, max_rows=request.max_rows or 10
            )

            return DataAgentResponse(
                success=True,
                action="execute_sql_on_datalake",
                result=result,
            )
        except Exception as e:
            self._logger.error(f"SQL query (Datalake) failed: {e}")
            return DataAgentResponse(
                success=False,
                action="execute_sql_on_datalake",
                error=str(e),
            )

    async def _handle_validate_data(self, request: DataAgentRequest) -> DataAgentResponse:
        """處理數據驗證請求"""
        if not request.schema_id:
            return DataAgentResponse(
                success=False,
                action="validate_data",
                error="schema_id is required for validate_data action",
            )

        # 允許空列表作為有效輸入（空列表表示沒有數據需要驗證，這是有效的）
        if request.data is None:
            return DataAgentResponse(
                success=False,
                action="validate_data",
                error="data is required for validate_data action",
            )

        try:
            result = await self._schema_service.validate_data(
                data=request.data,
                schema_id=request.schema_id,
            )

            if not result.get("success"):
                return DataAgentResponse(
                    success=False,
                    action="validate_data",
                    error=result.get("error", "Data validation failed"),
                    result=result,
                )

            return DataAgentResponse(
                success=True,
                action="validate_data",
                result=result,
            )

        except Exception as e:
            self._logger.error(f"Validate data failed: {e}")
            return DataAgentResponse(
                success=False,
                action="validate_data",
                error=str(e),
            )

    async def _handle_execute_structured_query(
        self, request: DataAgentRequest
    ) -> DataAgentResponse:
        """處理結構化查詢請求（由 MM-Agent 提供的結構化參數）"""
        if not request.structured_query:
            return DataAgentResponse(
                success=False,
                action="execute_structured_query",
                error="structured_query is required for execute_structured_query action",
            )

        try:
            self._logger.info(f"結構化查詢請求: {request.structured_query}")

            # 1. 構建 SQL 查詢
            build_result = StructuredQueryBuilder.build_query(request.structured_query)

            if not build_result.get("success"):
                return DataAgentResponse(
                    success=False,
                    action="execute_structured_query",
                    error=build_result.get("error", "構建查詢失敗"),
                )

            sql_query = build_result["sql"]
            explanation = build_result["explanation"]

            self._logger.info(f"生成的 SQL: {sql_query[:100]}...")

            # 2. 執行查詢
            query_result = await self._datalake_service.query_sql(
                sql_query=sql_query,
                max_rows=request.max_rows or 50,
            )

            if not query_result.get("success"):
                return DataAgentResponse(
                    success=False,
                    action="execute_structured_query",
                    error=query_result.get("error", "查詢執行失敗"),
                    result={
                        "sql_query": sql_query,
                        "explanation": explanation,
                    },
                )

            # 3. 返回結果
            return DataAgentResponse(
                success=True,
                action="execute_structured_query",
                result={
                    "sql_query": sql_query,
                    "explanation": explanation,
                    "rows": query_result.get("rows", []),
                    "row_count": query_result.get("row_count", 0),
                    "structured_query": request.structured_query,
                },
            )

        except Exception as e:
            self._logger.error(f"Execute structured query failed: {e}")
            return DataAgentResponse(
                success=False,
                action="execute_structured_query",
                error=str(e),
            )

    async def health_check(self) -> AgentServiceStatus:
        """
        健康檢查

        Returns:
            服務狀態
        """
        try:
            # 檢查服務是否可用
            if self._text_to_sql_service is None or self._query_gateway_service is None:
                return AgentServiceStatus.UNAVAILABLE

            # 簡單的健康檢查
            return AgentServiceStatus.AVAILABLE

        except Exception:
            return AgentServiceStatus.UNAVAILABLE

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        獲取服務能力

        Returns:
            服務能力描述
        """
        return {
            "agent_id": "data_agent",
            "agent_type": "dedicated_service",
            "name": "Data Agent",
            "description": "數據查詢專屬服務 Agent，提供 Text-to-SQL 轉換和安全查詢閘道功能",
            "capabilities": [
                "text_to_sql",  # Text-to-SQL 轉換
                "execute_query",  # 安全查詢執行
                "validate_query",  # 查詢驗證
                "get_schema",  # Schema 查詢
                "query_datalake",  # Datalake 數據查詢
                "create_dictionary",  # 創建數據字典
                "get_dictionary",  # 查詢數據字典
                "create_schema",  # 創建 Schema
                "validate_data",  # 數據驗證
            ],
            "supported_databases": [
                "postgresql",
                "mysql",
                "sqlite",
            ],
            "security_features": [
                "SQL injection protection",  # SQL 注入防護
                "Dangerous operation detection",  # 危險操作檢測
                "Parameterized query enforcement",  # 參數化查詢強制
                "Permission verification",  # 權限驗證
                "Result filtering",  # 結果過濾
                "Sensitive data masking",  # 敏感數據脫敏
            ],
        }
