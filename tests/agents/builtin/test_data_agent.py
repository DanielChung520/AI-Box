# 代碼功能說明: Data Agent 單元測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Data Agent 單元測試

測試 Data Agent 的核心功能：Text-to-SQL 轉換、安全查詢閘道和查詢執行。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.builtin.data_agent.agent import DataAgent
from agents.builtin.data_agent.query_gateway import QueryGatewayService
from agents.builtin.data_agent.text_to_sql import TextToSQLService
from agents.services.protocol.base import AgentServiceRequest, AgentServiceStatus


class TestDataAgent:
    """Data Agent 測試類"""

    @pytest.fixture
    def data_agent(self):
        """創建 DataAgent 實例"""
        with patch("agents.builtin.data_agent.agent.TextToSQLService") as mock_text_to_sql:
            with patch("agents.builtin.data_agent.agent.QueryGatewayService") as mock_gateway:
                mock_text_service = MagicMock()
                mock_gateway_service = MagicMock()
                mock_text_to_sql.return_value = mock_text_service
                mock_gateway.return_value = mock_gateway_service
                return DataAgent(
                    text_to_sql_service=mock_text_service,
                    query_gateway_service=mock_gateway_service,
                )

    @pytest.mark.asyncio
    async def test_execute_text_to_sql(self, data_agent):
        """測試 Text-to-SQL 轉換"""
        request = AgentServiceRequest(
            task_id="test-task-001",
            task_type="data",
            task_data={
                "action": "text_to_sql",
                "natural_language": "查詢所有用戶",
                "database_type": "postgresql",
            },
        )

        # Mock TextToSQLService 的 convert 方法
        data_agent._text_to_sql_service.convert = AsyncMock(
            return_value={
                "sql_query": "SELECT * FROM users",
                "parameters": [],
                "confidence": 0.8,
            }
        )

        response = await data_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True
        assert response.result["action"] == "text_to_sql"

    @pytest.mark.asyncio
    async def test_execute_execute_query(self, data_agent):
        """測試查詢執行"""
        request = AgentServiceRequest(
            task_id="test-task-002",
            task_type="data",
            task_data={
                "action": "execute_query",
                "sql_query": "SELECT * FROM users LIMIT 10",
            },
        )

        # Mock QueryGatewayService 的 execute_query 方法
        data_agent._query_gateway_service.execute_query = AsyncMock(
            return_value={
                "success": True,
                "rows": [{"id": 1, "name": "用戶1"}],
                "row_count": 1,
                "execution_time": 0.1,
            }
        )

        response = await data_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True
        assert response.result["action"] == "execute_query"

    @pytest.mark.asyncio
    async def test_execute_validate_query(self, data_agent):
        """測試查詢驗證"""
        request = AgentServiceRequest(
            task_id="test-task-003",
            task_type="data",
            task_data={
                "action": "validate_query",
                "query": "SELECT * FROM users WHERE id = ?",
            },
        )

        # Mock QueryGatewayService 的 validate_query 方法
        data_agent._query_gateway_service.validate_query = MagicMock(
            return_value={"valid": True, "warnings": []}
        )

        response = await data_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True
        assert response.result["action"] == "validate_query"

    @pytest.mark.asyncio
    async def test_execute_missing_parameters(self, data_agent):
        """測試缺少必要參數"""
        request = AgentServiceRequest(
            task_id="test-task-004",
            task_type="data",
            task_data={"action": "text_to_sql"},
        )

        response = await data_agent.execute(request)

        assert response.status == "failed"
        assert response.result["success"] is False
        assert "natural_language is required" in response.result["error"]

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self, data_agent):
        """測試未知操作"""
        request = AgentServiceRequest(
            task_id="test-task-005",
            task_type="data",
            task_data={"action": "unknown_action"},
        )

        response = await data_agent.execute(request)

        assert response.status == "failed"
        assert response.result["success"] is False
        assert "Unknown action" in response.result["error"]

    @pytest.mark.asyncio
    async def test_health_check(self, data_agent):
        """測試健康檢查"""
        status = await data_agent.health_check()
        assert status == AgentServiceStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_get_capabilities(self, data_agent):
        """測試獲取服務能力"""
        capabilities = await data_agent.get_capabilities()

        assert capabilities["agent_id"] == "data_agent"
        assert capabilities["agent_type"] == "dedicated_service"
        assert "text_to_sql" in capabilities["capabilities"]
        assert "execute_query" in capabilities["capabilities"]


class TestTextToSQLService:
    """Text-to-SQL Service 測試類"""

    @pytest.fixture
    def text_to_sql_service(self):
        """創建 TextToSQLService 實例"""
        with patch("agents.builtin.data_agent.text_to_sql.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.generate = AsyncMock(
                return_value={"text": "SELECT * FROM users WHERE name = ?"}
            )
            return TextToSQLService()

    @pytest.mark.asyncio
    async def test_convert(self, text_to_sql_service):
        """測試自然語言轉 SQL 轉換"""
        result = await text_to_sql_service.convert(
            natural_language="查詢所有用戶",
            database_type="postgresql",
        )

        assert "sql_query" in result
        assert "parameters" in result
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_convert_with_schema(self, text_to_sql_service):
        """測試帶 Schema 信息的轉換"""
        schema_info = {
            "tables": [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "INTEGER"},
                        {"name": "name", "type": "VARCHAR"},
                    ],
                }
            ]
        }

        result = await text_to_sql_service.convert(
            natural_language="查詢用戶表",
            database_type="postgresql",
            schema_info=schema_info,
        )

        assert "sql_query" in result

    def test_extract_sql(self, text_to_sql_service):
        """測試 SQL 提取"""
        text = "```sql\nSELECT * FROM users;\n```"
        sql = text_to_sql_service._extract_sql(text)

        assert "SELECT" in sql
        assert "users" in sql
        assert not sql.endswith(";")

    def test_validate_sql(self, text_to_sql_service):
        """測試 SQL 驗證"""
        sql = "SELECT * FROM users WHERE id = ?"
        validated, warnings = text_to_sql_service._validate_sql(sql, "postgresql")

        assert validated == sql
        assert isinstance(warnings, list)

    def test_validate_sql_dangerous(self, text_to_sql_service):
        """測試危險 SQL 檢測"""
        sql = "DROP TABLE users"
        validated, warnings = text_to_sql_service._validate_sql(sql, "postgresql")

        assert len(warnings) > 0
        assert any("DROP" in w for w in warnings)

    def test_extract_parameters(self, text_to_sql_service):
        """測試參數提取"""
        sql1 = "SELECT * FROM users WHERE id = ?"
        sql2 = "SELECT * FROM users WHERE id = $1 AND name = $2"

        params1 = text_to_sql_service._extract_parameters(sql1)
        params2 = text_to_sql_service._extract_parameters(sql2)

        assert len(params1) > 0
        assert len(params2) == 2

    def test_calculate_confidence(self, text_to_sql_service):
        """測試置信度計算"""
        sql1 = "SELECT * FROM users WHERE id = ?"
        sql2 = "DROP TABLE users"

        confidence1 = text_to_sql_service._calculate_confidence(sql1, "查詢用戶")
        confidence2 = text_to_sql_service._calculate_confidence(sql2, "刪除表")

        assert confidence1 > confidence2
        assert 0.0 <= confidence1 <= 1.0


class TestQueryGatewayService:
    """Query Gateway Service 測試類"""

    @pytest.fixture
    def query_gateway(self):
        """創建 QueryGatewayService 實例"""
        return QueryGatewayService()

    def test_validate_query_safe(self, query_gateway):
        """測試安全查詢驗證"""
        sql = "SELECT * FROM users WHERE id = ?"
        result = query_gateway.validate_query(sql)

        assert result["valid"] is True

    def test_validate_query_sql_injection(self, query_gateway):
        """測試 SQL 注入檢測"""
        sql = "SELECT * FROM users WHERE id = '1' OR '1'='1'"
        result = query_gateway.validate_query(sql)

        assert result["valid"] is False
        assert "SQL injection" in result["error"]

    def test_validate_query_dangerous_operation(self, query_gateway):
        """測試危險操作檢測"""
        sql = "DROP TABLE users"
        result = query_gateway.validate_query(sql)

        assert result["valid"] is False
        assert "Dangerous operation" in result["error"]

    def test_check_sql_injection(self, query_gateway):
        """測試 SQL 注入檢查"""
        sql1 = "SELECT * FROM users WHERE id = ?"
        sql2 = "SELECT * FROM users WHERE id = '1' OR '1'='1'"

        result1 = query_gateway._check_sql_injection(sql1)
        result2 = query_gateway._check_sql_injection(sql2)

        assert result1["safe"] is True
        assert result2["safe"] is False

    def test_check_dangerous_operations(self, query_gateway):
        """測試危險操作檢查"""
        sql1 = "SELECT * FROM users"
        sql2 = "DROP TABLE users"
        sql3 = "DELETE FROM users"

        result1 = query_gateway._check_dangerous_operations(sql1)
        result2 = query_gateway._check_dangerous_operations(sql2)
        result3 = query_gateway._check_dangerous_operations(sql3)

        assert result1["safe"] is True
        assert result2["safe"] is False
        assert result3["safe"] is False

    def test_check_parameterized_query(self, query_gateway):
        """測試參數化查詢檢查"""
        sql1 = "SELECT * FROM users WHERE id = ?"
        sql2 = "SELECT * FROM users WHERE id = '1'"

        result1 = query_gateway._check_parameterized_query(sql1)
        result2 = query_gateway._check_parameterized_query(sql2)

        assert result1["safe"] is True
        assert result2["safe"] is False

    def test_filter_results(self, query_gateway):
        """測試結果過濾"""
        rows = [{"id": i, "name": f"用戶{i}"} for i in range(100)]

        filtered = query_gateway.filter_results(rows, max_rows=10)
        assert len(filtered) == 10

    def test_filter_results_sensitive_data(self, query_gateway):
        """測試敏感數據脫敏"""
        rows = [{"id": 1, "name": "張三", "email": "zhang@example.com"}]

        filtered = query_gateway.filter_results(rows, max_rows=10, sensitive_columns=["email"])

        assert len(filtered) == 1
        assert "***" in filtered[0]["email"]

    @pytest.mark.asyncio
    async def test_execute_query(self, query_gateway):
        """測試查詢執行"""
        sql = "SELECT * FROM users WHERE id = ?"

        result = await query_gateway.execute_query(
            sql_query=sql,
            timeout=30,
            max_rows=100,
        )

        # 注意：這是模擬實現，實際應該連接到數據庫
        assert "success" in result
        assert "rows" in result
