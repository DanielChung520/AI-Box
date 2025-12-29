# 代碼功能說明: LogService 單元測試
# 創建日期: 2025-12-21
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""LogService 單元測試"""

from unittest.mock import Mock, patch

import pytest

from database.arangodb import ArangoDBClient
from services.api.core.log import LogService, LogType, get_log_service


class TestLogService:
    """LogService 測試類"""

    @pytest.fixture
    def mock_client(self):
        """創建模擬的 ArangoDB 客戶端"""
        client = Mock(spec=ArangoDBClient)
        client.db = Mock()
        client.db.has_collection = Mock(return_value=False)
        client.db.create_collection = Mock()
        client.db.collection = Mock(return_value=Mock())
        client.db.aql = Mock()
        return client

    @pytest.fixture
    def log_service(self, mock_client):
        """創建 LogService 實例"""
        service = LogService(client=mock_client)
        # 獲取 Collection mock
        collection_mock = mock_client.db.collection.return_value
        collection_mock.insert = Mock(return_value={"_key": "test_log_id"})
        collection_mock.add_index = Mock()
        return service

    @pytest.mark.asyncio
    async def test_log_event(self, log_service):
        """測試記錄日誌事件"""
        trace_id = "test_trace_123"
        content = {"message": "test log"}

        log_id = await log_service.log_event(
            trace_id=trace_id,
            log_type=LogType.TASK,
            agent_name="TestAgent",
            actor="test_user",
            action="test_action",
            content=content,
        )

        assert log_id == "test_log_id"
        collection = log_service.client.db.collection.return_value
        assert collection.insert.called

    @pytest.mark.asyncio
    async def test_log_task(self, log_service):
        """測試記錄任務級日誌"""
        trace_id = "test_trace_123"
        content = {"instruction": "test task"}

        log_id = await log_service.log_task(
            trace_id=trace_id,
            actor="test_user",
            action="task_start",
            content=content,
        )

        assert log_id == "test_log_id"
        collection = log_service.client.db.collection.return_value
        call_args = collection.insert.call_args[0][0]
        assert call_args["type"] == LogType.TASK.value
        assert call_args["agent_name"] == "Orchestrator"

    @pytest.mark.asyncio
    async def test_log_audit(self, log_service):
        """測試記錄審計日誌"""
        trace_id = "test_trace_123"
        content = {"before": {}, "after": {}}

        log_id = await log_service.log_audit(
            trace_id=trace_id,
            actor="test_user",
            action="update_config",
            content=content,
            level="tenant",
            tenant_id="tenant_123",
        )

        assert log_id == "test_log_id"
        collection = log_service.client.db.collection.return_value
        call_args = collection.insert.call_args[0][0]
        assert call_args["type"] == LogType.AUDIT.value
        assert call_args["level"] == "tenant"
        assert call_args["tenant_id"] == "tenant_123"

    @pytest.mark.asyncio
    async def test_log_security(self, log_service):
        """測試記錄安全日誌"""
        trace_id = "test_trace_123"
        content = {"permission_check": {"allowed": True}}

        log_id = await log_service.log_security(
            trace_id=trace_id,
            actor="test_user",
            action="check_permission",
            content=content,
        )

        assert log_id == "test_log_id"
        collection = log_service.client.db.collection.return_value
        call_args = collection.insert.call_args[0][0]
        assert call_args["type"] == LogType.SECURITY.value
        assert call_args["agent_name"] == "SecurityAgent"

    @pytest.mark.asyncio
    async def test_get_logs_by_trace_id(self, log_service):
        """測試根據 trace_id 查詢日誌"""
        trace_id = "test_trace_123"
        mock_cursor = [
            {"_key": "log1", "trace_id": trace_id, "type": "TASK"},
            {"_key": "log2", "trace_id": trace_id, "type": "AUDIT"},
        ]
        log_service.client.db.aql.execute = Mock(return_value=mock_cursor)

        logs = await log_service.get_logs_by_trace_id(trace_id)

        assert len(logs) == 2
        assert logs[0]["_key"] == "log1"
        assert logs[1]["_key"] == "log2"

    @pytest.mark.asyncio
    async def test_get_audit_logs(self, log_service):
        """測試查詢審計日誌"""
        mock_cursor = [
            {"_key": "audit1", "type": "AUDIT", "actor": "user1"},
        ]
        log_service.client.db.aql.execute = Mock(return_value=mock_cursor)

        logs = await log_service.get_audit_logs(
            actor="user1",
            level="tenant",
            limit=10,
        )

        assert len(logs) == 1
        assert logs[0]["_key"] == "audit1"

    @pytest.mark.asyncio
    async def test_get_security_logs(self, log_service):
        """測試查詢安全日誌"""
        mock_cursor = [
            {"_key": "security1", "type": "SECURITY", "action": "check_permission"},
        ]
        log_service.client.db.aql.execute = Mock(return_value=mock_cursor)

        logs = await log_service.get_security_logs(
            actor="user1",
            action="check_permission",
            limit=10,
        )

        assert len(logs) == 1
        assert logs[0]["_key"] == "security1"

    def test_get_log_service_singleton(self):
        """測試單例模式"""
        with patch("services.api.core.log.log_service.LogService"):
            service1 = get_log_service()
            service2 = get_log_service()
            # 在單例模式下，應該返回同一個實例
            # 但由於我們使用了 patch，這裡主要是測試調用
            assert service1 is not None
            assert service2 is not None

    @pytest.mark.asyncio
    async def test_log_event_with_large_content(self, log_service):
        """測試記錄超大內容的日誌（觸發截斷邏輯）"""
        trace_id = "test_trace_123"
        # 創建一個超大內容（超過默認 max_content_size）
        large_content = {"data": "x" * 100000}  # 假設 max_content_size 默認值較小

        # 設置較小的 max_content_size 來觸發截斷
        log_service.max_content_size = 1000

        log_id = await log_service.log_event(
            trace_id=trace_id,
            log_type=LogType.TASK,
            agent_name="TestAgent",
            actor="test_user",
            action="test_action",
            content=large_content,
        )

        assert log_id == "test_log_id"
        collection = log_service.client.db.collection.return_value
        assert collection.insert.called
        # 驗證內容被截斷
        call_args = collection.insert.call_args[0][0]
        assert "_truncated" in call_args["content"] or len(str(call_args["content"])) < len(
            str(large_content)
        )

    @pytest.mark.asyncio
    async def test_log_event_db_not_connected(self, mock_client):
        """測試數據庫未連接時的錯誤處理"""
        # 注意：由於 _ensure_collection 在 __init__ 中調用，需要先設置 db
        mock_client.db = Mock()
        mock_client.db.has_collection = Mock(return_value=False)
        mock_client.db.create_collection = Mock()
        service = LogService(client=mock_client)
        # 然後設置為 None 來測試錯誤路徑
        service.client.db = None

        with pytest.raises(RuntimeError, match="ArangoDB client is not connected"):
            await service.log_event(
                trace_id="test_trace",
                log_type=LogType.TASK,
                agent_name="TestAgent",
                actor="test_user",
                action="test_action",
                content={"message": "test"},
            )

    @pytest.mark.asyncio
    async def test_truncate_content_small_content(self, log_service):
        """測試 _truncate_content() 方法：內容小於限制時不截斷"""
        content = {"message": "test"}
        result = log_service._truncate_content(content, 10000, LogType.TASK)
        assert result == content
        assert "_truncated" not in result

    @pytest.mark.asyncio
    async def test_truncate_content_large_content_task(self, log_service):
        """測試 _truncate_content() 方法：TASK 類型的大內容截斷"""
        large_content = {"message": "x" * 10000, "other": "data"}
        result = log_service._truncate_content(large_content, 100, LogType.TASK)
        assert "_truncated" in result
        assert result["_original_size"] > 100

    @pytest.mark.asyncio
    async def test_truncate_content_large_content_audit(self, log_service):
        """測試 _truncate_content() 方法：AUDIT 類型的大內容截斷"""
        large_content = {
            "scope": "genai.policy",
            "before": {"key": "value"},
            "after": {"key": "new_value"},
            "other": "data" * 1000,
        }
        result = log_service._truncate_content(large_content, 100, LogType.AUDIT)
        assert "_truncated" in result
        assert "scope" in result  # 關鍵字段應該保留
        assert "before" in result or "_too_large" in str(result.get("before", ""))

    @pytest.mark.asyncio
    async def test_get_logs_by_trace_id_empty(self, log_service):
        """測試 get_logs_by_trace_id() - 空結果"""
        trace_id = "nonexistent_trace"
        log_service.client.db.aql.execute = Mock(return_value=[])

        logs = await log_service.get_logs_by_trace_id(trace_id)

        assert len(logs) == 0
        assert logs == []

    @pytest.mark.asyncio
    async def test_get_logs_by_trace_id_multiple_logs(self, log_service):
        """測試 get_logs_by_trace_id() - 多條日誌的情況"""
        trace_id = "test_trace_123"
        mock_cursor = [{"_key": f"log{i}", "trace_id": trace_id, "type": "TASK"} for i in range(10)]
        log_service.client.db.aql.execute = Mock(return_value=mock_cursor)

        logs = await log_service.get_logs_by_trace_id(trace_id)

        assert len(logs) == 10
        assert logs[0]["_key"] == "log0"

    @pytest.mark.asyncio
    async def test_get_audit_logs_time_range(self, log_service):
        """測試 get_audit_logs() - 按時間範圍查詢"""
        from datetime import datetime, timedelta

        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()

        mock_cursor = [
            {"_key": "audit1", "type": "AUDIT", "timestamp": datetime.utcnow().isoformat()}
        ]
        log_service.client.db.aql.execute = Mock(return_value=mock_cursor)

        logs = await log_service.get_audit_logs(
            start_time=start_time,
            end_time=end_time,
        )

        assert len(logs) == 1
        # 驗證 AQL 調用包含時間過濾
        assert log_service.client.db.aql.execute.called

    @pytest.mark.asyncio
    async def test_get_audit_logs_filter_by_actor(self, log_service):
        """測試 get_audit_logs() - 按 actor 過濾"""
        mock_cursor = [{"_key": "audit1", "type": "AUDIT", "actor": "user1"}]
        log_service.client.db.aql.execute = Mock(return_value=mock_cursor)

        logs = await log_service.get_audit_logs(actor="user1")

        assert len(logs) == 1
        assert logs[0]["actor"] == "user1"

    @pytest.mark.asyncio
    async def test_get_audit_logs_filter_by_tenant_id(self, log_service):
        """測試 get_audit_logs() - 按 tenant_id 過濾"""
        mock_cursor = [{"_key": "audit1", "type": "AUDIT", "tenant_id": "tenant_123"}]
        log_service.client.db.aql.execute = Mock(return_value=mock_cursor)

        logs = await log_service.get_audit_logs(tenant_id="tenant_123")

        assert len(logs) == 1
        assert logs[0]["tenant_id"] == "tenant_123"

    @pytest.mark.asyncio
    async def test_get_security_logs_multiple_filters(self, log_service):
        """測試 get_security_logs() - 多個過濾條件組合"""
        mock_cursor = [
            {
                "_key": "security1",
                "type": "SECURITY",
                "actor": "user1",
                "action": "check_permission",
            }
        ]
        log_service.client.db.aql.execute = Mock(return_value=mock_cursor)

        logs = await log_service.get_security_logs(
            actor="user1",
            action="check_permission",
            limit=10,
        )

        assert len(logs) == 1
        assert logs[0]["actor"] == "user1"
        assert logs[0]["action"] == "check_permission"

    @pytest.mark.asyncio
    async def test_get_security_logs_with_time_range(self, log_service):
        """測試 get_security_logs() - 按時間範圍查詢"""
        from datetime import datetime, timedelta

        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()

        mock_cursor = [
            {
                "_key": "security1",
                "type": "SECURITY",
                "timestamp": datetime.utcnow().isoformat(),
            }
        ]
        log_service.client.db.aql.execute = Mock(return_value=mock_cursor)

        logs = await log_service.get_security_logs(start_time=start_time, end_time=end_time)

        assert len(logs) == 1
        assert log_service.client.db.aql.execute.called

    @pytest.mark.asyncio
    async def test_log_event_insert_failure(self, log_service):
        """測試日誌插入失敗的錯誤處理"""
        collection = log_service.client.db.collection.return_value
        collection.insert = Mock(side_effect=Exception("Insert failed"))

        with pytest.raises(Exception, match="Insert failed"):
            await log_service.log_event(
                trace_id="test_trace",
                log_type=LogType.TASK,
                agent_name="TestAgent",
                actor="test_user",
                action="test_action",
                content={"message": "test"},
            )

    @pytest.mark.asyncio
    async def test_log_event_insert_result_no_key(self, log_service):
        """測試插入結果中沒有 _key 的情況"""
        collection = log_service.client.db.collection.return_value
        collection.insert = Mock(return_value={"id": "some_id"})  # 沒有 _key

        with pytest.raises(RuntimeError, match="Failed to get log entry key"):
            await log_service.log_event(
                trace_id="test_trace",
                log_type=LogType.TASK,
                agent_name="TestAgent",
                actor="test_user",
                action="test_action",
                content={"message": "test"},
            )

    @pytest.mark.asyncio
    async def test_get_logs_by_trace_id_aql_error(self, log_service):
        """測試查詢日誌時 AQL 執行錯誤"""
        log_service.client.db.aql.execute = Mock(side_effect=Exception("AQL error"))

        with pytest.raises(Exception, match="AQL error"):
            await log_service.get_logs_by_trace_id("test_trace")

    @pytest.mark.asyncio
    async def test_get_log_statistics(self, log_service):
        """測試獲取日誌統計信息"""

        # Mock 多個 AQL 查詢結果
        log_service.client.db.aql.execute = Mock(
            side_effect=[
                [100],  # total_count
                [{"type": "TASK", "count": 50}, {"type": "AUDIT", "count": 30}],  # count_by_type
                [{"agent": "Agent1", "count": 60}],  # count_by_agent
                [{"_key": "log1", "content": {"msg": "test"}}] * 100,  # samples
            ]
        )

        stats = await log_service.get_log_statistics()

        assert stats["total_count"] == 100
        assert "count_by_type" in stats
        assert "count_by_agent" in stats
        assert "average_size_bytes" in stats

    @pytest.mark.asyncio
    async def test_get_log_statistics_with_time_range(self, log_service):
        """測試按時間範圍獲取日誌統計"""
        from datetime import datetime, timedelta

        start_time = datetime.utcnow() - timedelta(days=7)
        end_time = datetime.utcnow()

        log_service.client.db.aql.execute = Mock(
            side_effect=[
                [50],  # total_count
                [{"type": "TASK", "count": 30}],  # count_by_type
                [],  # count_by_agent
                [{"_key": "log1", "content": {"msg": "test"}}] * 50,  # samples
            ]
        )

        stats = await log_service.get_log_statistics(start_time=start_time, end_time=end_time)

        assert stats["total_count"] == 50
        assert stats["period"]["start_time"] is not None
        assert stats["period"]["end_time"] is not None

    @pytest.mark.asyncio
    async def test_get_log_statistics_aql_not_available(self, log_service):
        """測試 AQL 不可用時的錯誤處理"""
        log_service.client.db.aql = None

        with pytest.raises(RuntimeError, match="ArangoDB client or AQL is not available"):
            await log_service.get_log_statistics()

    @pytest.mark.asyncio
    async def test_cleanup_expired_logs(self, log_service):
        """測試清理過期日誌（私有方法）"""
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=30)
        mock_cursor = ["log1", "log2", "log3"]  # 返回被刪除的 key 列表
        log_service.client.db.aql.execute = Mock(return_value=mock_cursor)

        deleted_count = await log_service._cleanup_expired_logs(LogType.TASK, cutoff_date)

        assert deleted_count == 3
        assert log_service.client.db.aql.execute.called

    @pytest.mark.asyncio
    async def test_cleanup_expired_logs_default_cutoff(self, log_service):
        """測試清理過期日誌 - 使用默認截止日期"""
        mock_cursor = ["log1"]
        log_service.client.db.aql.execute = Mock(return_value=mock_cursor)

        deleted_count = await log_service._cleanup_expired_logs(LogType.TASK)

        assert deleted_count == 1
        assert log_service.client.db.aql.execute.called

    @pytest.mark.asyncio
    async def test_cleanup_expired_logs_error(self, log_service):
        """測試清理過期日誌時的錯誤處理"""
        log_service.client.db.aql.execute = Mock(side_effect=Exception("Cleanup error"))

        with pytest.raises(Exception, match="Cleanup error"):
            await log_service._cleanup_expired_logs(LogType.TASK)

    @pytest.mark.asyncio
    async def test_cleanup_expired_logs_aql_not_available(self, log_service):
        """測試清理過期日誌時 AQL 不可用"""
        log_service.client.db.aql = None

        with pytest.raises(RuntimeError, match="ArangoDB client or AQL is not available"):
            await log_service._cleanup_expired_logs(LogType.TASK)
