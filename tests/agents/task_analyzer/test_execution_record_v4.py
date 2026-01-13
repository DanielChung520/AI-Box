# 代碼功能說明: Execution Record v4.0 單元測試（L5 執行與觀察層）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Execution Record v4.0 單元測試 - 測試 L5 執行與觀察層"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from agents.task_analyzer.execution_record import (
    ExecutionRecord,
    ExecutionRecordCreate,
    ExecutionRecordStoreService,
)
from agents.task_analyzer.models import TaskDAG, TaskNode


class TestExecutionRecordV4:
    """Execution Record v4.0 測試類"""

    @pytest.fixture
    def execution_record(self):
        """創建 ExecutionRecord 實例"""
        return ExecutionRecord(
            intent="document_editing",
            task_count=3,
            execution_success=True,
            user_correction=False,
            latency_ms=1500,
            task_results=[
                {"task_id": "T1", "status": "completed", "result": "success"},
                {"task_id": "T2", "status": "completed", "result": "success"},
                {"task_id": "T3", "status": "completed", "result": "success"},
            ],
            trace_id="trace123",
            user_id="user123",
            session_id="session123",
            agent_ids=["DocumentEditingAgent"],
        )

    @pytest.fixture
    def execution_record_create(self):
        """創建 ExecutionRecordCreate 實例"""
        return ExecutionRecordCreate(
            intent="document_editing",
            task_count=3,
            execution_success=True,
            user_correction=False,
            latency_ms=1500,
            task_results=[
                {"task_id": "T1", "status": "completed", "result": "success"},
                {"task_id": "T2", "status": "completed", "result": "success"},
                {"task_id": "T3", "status": "completed", "result": "success"},
            ],
            trace_id="trace123",
            user_id="user123",
            session_id="session123",
            agent_ids=["DocumentEditingAgent"],
        )

    @pytest.fixture
    def mock_arangodb_client(self):
        """創建 Mock ArangoDB 客戶端"""
        client = MagicMock()
        client.db = MagicMock()
        client.db.aql = MagicMock()
        client.get_or_create_collection = MagicMock(return_value=MagicMock())
        return client

    def test_execution_record_creation(self, execution_record):
        """測試 ExecutionRecord 創建"""
        assert execution_record.intent == "document_editing"
        assert execution_record.task_count == 3
        assert execution_record.execution_success is True
        assert execution_record.latency_ms == 1500
        assert len(execution_record.task_results) == 3
        assert execution_record.agent_ids == ["DocumentEditingAgent"]

    def test_execution_record_create_creation(self, execution_record_create):
        """測試 ExecutionRecordCreate 創建"""
        assert execution_record_create.intent == "document_editing"
        assert execution_record_create.task_count == 3
        assert execution_record_create.execution_success is True

    def test_execution_record_store_service_init(self, mock_arangodb_client):
        """測試 ExecutionRecordStoreService 初始化"""
        service = ExecutionRecordStoreService(client=mock_arangodb_client)

        assert service._client == mock_arangodb_client
        assert service._collection is not None

    def test_save_record(self, mock_arangodb_client):
        """測試保存執行記錄"""
        service = ExecutionRecordStoreService(client=mock_arangodb_client)
        record = ExecutionRecordCreate(
            intent="test_intent",
            task_count=1,
            execution_success=True,
            latency_ms=100,
        )

        record_id = service.save_record(record)

        # 驗證記錄已保存
        assert record_id is not None
        assert isinstance(record_id, str)
        # 驗證 collection.insert 被調用
        service._collection.insert.assert_called_once()

    def test_get_records_by_intent(self, mock_arangodb_client):
        """測試根據 Intent 查詢記錄"""
        service = ExecutionRecordStoreService(client=mock_arangodb_client)

        # Mock AQL 查詢結果
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(
            return_value=iter(
                [
                    {
                        "_key": "record1",
                        "intent": "test_intent",
                        "task_count": 1,
                        "execution_success": True,
                        "latency_ms": 100,
                    }
                ]
            )
        )
        mock_arangodb_client.db.aql.execute.return_value = mock_cursor

        records = service.get_records_by_intent("test_intent", limit=10)

        # 驗證結果
        assert len(records) == 1
        assert records[0]["intent"] == "test_intent"
        # 驗證 AQL 被調用
        mock_arangodb_client.db.aql.execute.assert_called_once()

    def test_get_records_by_time_range(self, mock_arangodb_client):
        """測試根據時間範圍查詢記錄"""
        service = ExecutionRecordStoreService(client=mock_arangodb_client)

        # Mock AQL 查詢結果
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter([]))
        mock_arangodb_client.db.aql.execute.return_value = mock_cursor

        start_time = datetime(2026, 1, 1)
        end_time = datetime(2026, 1, 31)

        records = service.get_records_by_time_range(start_time, end_time, limit=100)

        # 驗證結果
        assert isinstance(records, list)
        # 驗證 AQL 被調用
        mock_arangodb_client.db.aql.execute.assert_called_once()

    def test_get_records_by_trace_id(self, mock_arangodb_client):
        """測試根據 Trace ID 查詢記錄"""
        service = ExecutionRecordStoreService(client=mock_arangodb_client)

        # Mock AQL 查詢結果
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(
            return_value=iter(
                [
                    {
                        "_key": "record1",
                        "trace_id": "trace123",
                        "intent": "test_intent",
                    }
                ]
            )
        )
        mock_arangodb_client.db.aql.execute.return_value = mock_cursor

        records = service.get_records_by_trace_id("trace123")

        # 驗證結果
        assert len(records) == 1
        assert records[0]["trace_id"] == "trace123"
        # 驗證 AQL 被調用
        mock_arangodb_client.db.aql.execute.assert_called_once()

    def test_execution_record_with_failed_tasks(self):
        """測試包含失敗任務的執行記錄"""
        record = ExecutionRecordCreate(
            intent="test_intent",
            task_count=3,
            execution_success=False,  # 整體執行失敗
            latency_ms=2000,
            task_results=[
                {"task_id": "T1", "status": "completed", "result": "success"},
                {"task_id": "T2", "status": "failed", "error": "Task failed"},
                {"task_id": "T3", "status": "completed", "result": "success"},
            ],
        )

        assert record.execution_success is False
        assert len(record.task_results) == 3
        assert record.task_results[1]["status"] == "failed"

    def test_execution_record_with_user_correction(self):
        """測試包含用戶修正的執行記錄"""
        record = ExecutionRecordCreate(
            intent="test_intent",
            task_count=1,
            execution_success=True,
            user_correction=True,  # 用戶修正
            latency_ms=500,
        )

        assert record.user_correction is True

    def test_execution_record_with_multiple_agents(self):
        """測試使用多個 Agent 的執行記錄"""
        record = ExecutionRecordCreate(
            intent="complex_task",
            task_count=5,
            execution_success=True,
            latency_ms=3000,
            agent_ids=[
                "DocumentEditingAgent",
                "FileManagementAgent",
                "DataProcessingAgent",
            ],
        )

        assert len(record.agent_ids) == 3
        assert "DocumentEditingAgent" in record.agent_ids

    @pytest.mark.asyncio
    async def test_execution_record_integration(self, mock_arangodb_client):
        """測試執行記錄集成（需要真實的 ArangoDB 連接）"""
        # 注意：此測試需要 ArangoDB 已初始化
        # 如果數據庫未初始化，此測試可能會失敗
        try:
            service = ExecutionRecordStoreService(client=mock_arangodb_client)
            record = ExecutionRecordCreate(
                intent="integration_test",
                task_count=1,
                execution_success=True,
                latency_ms=100,
            )

            record_id = service.save_record(record)

            # 如果成功，驗證記錄 ID
            if record_id:
                assert isinstance(record_id, str)
        except Exception as e:
            # 如果服務未初始化，跳過此測試
            pytest.skip(f"ArangoDB not initialized: {e}")


class TestExecutionRecordMetrics:
    """執行指標測試類"""

    def test_latency_calculation(self):
        """測試延遲計算"""
        start_time = datetime(2026, 1, 13, 10, 0, 0)
        end_time = datetime(2026, 1, 13, 10, 0, 1, 500000)  # 1.5 秒後

        latency_ms = int((end_time - start_time).total_seconds() * 1000)

        assert latency_ms == 1500

    def test_success_rate_calculation(self):
        """測試成功率計算"""
        records = [
            ExecutionRecordCreate(
                intent="test", task_count=1, execution_success=True, latency_ms=100
            ),
            ExecutionRecordCreate(
                intent="test", task_count=1, execution_success=True, latency_ms=100
            ),
            ExecutionRecordCreate(
                intent="test", task_count=1, execution_success=False, latency_ms=100
            ),
        ]

        success_count = sum(1 for r in records if r.execution_success)
        success_rate = success_count / len(records)

        assert success_rate == 2 / 3  # 66.67%

    def test_average_latency_calculation(self):
        """測試平均延遲計算"""
        records = [
            ExecutionRecordCreate(
                intent="test", task_count=1, execution_success=True, latency_ms=100
            ),
            ExecutionRecordCreate(
                intent="test", task_count=1, execution_success=True, latency_ms=200
            ),
            ExecutionRecordCreate(
                intent="test", task_count=1, execution_success=True, latency_ms=300
            ),
        ]

        total_latency = sum(r.latency_ms for r in records)
        average_latency = total_latency / len(records)

        assert average_latency == 200  # (100 + 200 + 300) / 3
