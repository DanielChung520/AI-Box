# 代碼功能說明: AAM 實時檢索服務單元測試
# 創建日期: 2025-11-28 21:54 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-28 21:54 (UTC+8)

"""AAM 實時檢索服務單元測試"""

import pytest
from unittest.mock import Mock

from agents.infra.memory.aam.models import Memory, MemoryType, MemoryPriority
from agents.infra.memory.aam.aam_core import AAMManager
from agents.infra.memory.aam.realtime_retrieval import RealtimeRetrievalService
from agents.infra.memory.aam.context_integration import ContextIntegration
from agent_process.context.manager import ContextManager


class TestRealtimeRetrievalService:
    """實時檢索服務測試"""

    @pytest.fixture
    def mock_aam_manager(self):
        """創建 AAM 管理器 Mock"""
        manager = Mock(spec=AAMManager)
        manager.enable_short_term = True
        manager.enable_long_term = True
        manager.search_memories = Mock(return_value=[])
        return manager

    @pytest.fixture
    def retrieval_service(self, mock_aam_manager):
        """創建實時檢索服務實例"""
        return RealtimeRetrievalService(mock_aam_manager, cache_enabled=True)

    def test_retrieve_with_cache(self, retrieval_service, mock_aam_manager):
        """測試帶緩存的檢索"""
        # 設置 Mock 返回值（只返回一個結果，避免並行搜索重複）
        test_memories = [
            Memory(
                memory_id="test-1",
                content="Test content 1",
                memory_type=MemoryType.SHORT_TERM,
                relevance_score=0.8,
            )
        ]
        mock_aam_manager.search_memories.return_value = test_memories

        # 禁用長期記憶以簡化測試
        retrieval_service.aam_manager.enable_long_term = False

        # 第一次檢索（應該調用 search_memories）
        results1 = retrieval_service.retrieve("test query", limit=10)
        assert len(results1) >= 1
        assert mock_aam_manager.search_memories.call_count >= 1

        # 第二次檢索（應該使用緩存）
        call_count_before = mock_aam_manager.search_memories.call_count
        results2 = retrieval_service.retrieve("test query", limit=10)
        assert len(results2) >= 1
        # 應該使用緩存，不增加調用次數
        assert mock_aam_manager.search_memories.call_count == call_count_before

    def test_retrieve_without_cache(self, retrieval_service, mock_aam_manager):
        """測試不使用緩存的檢索"""
        test_memories = [
            Memory(
                memory_id="test-1",
                content="Test content 1",
                memory_type=MemoryType.SHORT_TERM,
                relevance_score=0.8,
            )
        ]
        mock_aam_manager.search_memories.return_value = test_memories

        # 禁用長期記憶以簡化測試
        retrieval_service.aam_manager.enable_long_term = False

        # 不使用緩存
        results = retrieval_service.retrieve("test query", use_cache=False, limit=10)
        assert len(results) >= 1

    def test_calculate_relevance(self, retrieval_service):
        """測試相關度計算"""
        memory = Memory(
            memory_id="test-1",
            content="Test content",
            memory_type=MemoryType.SHORT_TERM,
            priority=MemoryPriority.HIGH,
            relevance_score=0.5,
        )
        relevance = retrieval_service._calculate_relevance(memory, "test query")
        assert 0.0 <= relevance <= 1.0

    def test_sort_memories(self, retrieval_service):
        """測試記憶排序"""
        memories = [
            Memory(
                memory_id="test-1",
                content="Test content 1",
                memory_type=MemoryType.SHORT_TERM,
                priority=MemoryPriority.LOW,
                relevance_score=0.3,
            ),
            Memory(
                memory_id="test-2",
                content="Test content 2",
                memory_type=MemoryType.SHORT_TERM,
                priority=MemoryPriority.HIGH,
                relevance_score=0.5,
            ),
        ]
        sorted_memories = retrieval_service._sort_memories(memories, "test query")
        assert len(sorted_memories) == 2
        # 應該按相關度排序
        assert sorted_memories[0].relevance_score >= sorted_memories[1].relevance_score

    def test_clear_cache(self, retrieval_service, mock_aam_manager):
        """測試清空緩存"""
        test_memories = [
            Memory(
                memory_id="test-1",
                content="Test content 1",
                memory_type=MemoryType.SHORT_TERM,
            )
        ]
        mock_aam_manager.search_memories.return_value = test_memories

        # 禁用長期記憶以簡化測試
        retrieval_service.aam_manager.enable_long_term = False

        # 執行檢索（會設置緩存）
        retrieval_service.retrieve("test query", limit=10)
        assert len(retrieval_service._cache) > 0

        # 清空緩存
        count = retrieval_service.clear_cache()
        assert count > 0
        assert len(retrieval_service._cache) == 0


class TestContextIntegration:
    """上下文整合測試"""

    @pytest.fixture
    def mock_context_manager(self):
        """創建上下文管理器 Mock"""
        manager = Mock(spec=ContextManager)
        manager.get_messages = Mock(return_value=[])
        manager.record_message = Mock(return_value=True)
        return manager

    @pytest.fixture
    def mock_aam_manager(self):
        """創建 AAM 管理器 Mock"""
        manager = Mock(spec=AAMManager)
        manager.store_memory = Mock(return_value="test-memory-id")
        return manager

    @pytest.fixture
    def context_integration(self, mock_context_manager, mock_aam_manager):
        """創建上下文整合實例"""
        return ContextIntegration(
            context_manager=mock_context_manager,
            aam_manager=mock_aam_manager,
        )

    def test_context_to_memory(
        self, context_integration, mock_context_manager, mock_aam_manager
    ):
        """測試上下文轉換為記憶"""
        # 設置 Mock 返回值
        from agent_process.context.models import ContextMessage
        from datetime import datetime

        messages = [
            ContextMessage(
                role="user",
                content="Hello",
                timestamp=datetime.now(),
            ),
            ContextMessage(
                role="assistant",
                content="Hi there",
                timestamp=datetime.now(),
            ),
        ]
        mock_context_manager.get_messages.return_value = messages

        memory_id = context_integration.context_to_memory("test-session")
        assert memory_id is not None
        mock_aam_manager.store_memory.assert_called_once()

    def test_inject_memory_to_context(self, context_integration, mock_context_manager):
        """測試將記憶注入到上下文"""
        # 設置 Mock 返回值
        from agents.infra.memory.aam.models import Memory, MemoryType

        test_memories = [
            Memory(
                memory_id="test-1",
                content="Test memory",
                memory_type=MemoryType.SHORT_TERM,
                relevance_score=0.8,
            )
        ]

        # Mock retrieval_service
        mock_retrieval = Mock()
        mock_retrieval.retrieve = Mock(return_value=test_memories)
        context_integration.retrieval_service = mock_retrieval

        memories = context_integration.inject_memory_to_context(
            "test-session", query="test"
        )
        assert len(memories) == 1
        mock_context_manager.record_message.assert_called()
