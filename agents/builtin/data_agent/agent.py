# 代碼功能說明: Data Agent 實現
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Data Agent 實現 - 數據查詢專屬服務 Agent"""

import logging
from typing import Any, Dict, Optional

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)

from .models import DataAgentRequest, DataAgentResponse
from .query_gateway import QueryGatewayService
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
    ):
        """
        初始化 Data Agent

        Args:
            text_to_sql_service: Text-to-SQL 服務（可選，如果不提供則自動創建）
            query_gateway_service: 查詢閘道服務（可選，如果不提供則自動創建）
        """
        self._text_to_sql_service = text_to_sql_service or TextToSQLService()
        self._query_gateway_service = query_gateway_service or QueryGatewayService()
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

        try:
            # 調用 Text-to-SQL 服務
            result = await self._text_to_sql_service.convert(
                natural_language=request.natural_language,
                database_type=request.database_type or "postgresql",
                schema_info=request.schema_info,
                context={"user_id": request.user_id, "tenant_id": request.tenant_id},
            )

            return DataAgentResponse(
                success=True,
                action="text_to_sql",
                result=result,
            )

        except Exception as e:
            self._logger.error(f"Text-to-SQL conversion failed: {e}")
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

            return DataAgentResponse(
                success=validation["valid"],
                action="validate_query",
                result=validation,
                error=None if validation["valid"] else validation.get("error"),
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
        try:
            # 這裡應該實現實際的 Schema 查詢邏輯
            # 目前返回基本響應
            return DataAgentResponse(
                success=False,
                action="get_schema",
                error="get_schema action is not yet implemented",
            )

        except Exception as e:
            self._logger.error(f"Get schema failed: {e}")
            return DataAgentResponse(
                success=False,
                action="get_schema",
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
                "get_schema",  # Schema 查詢（待實現）
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
