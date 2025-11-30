# 代碼功能說明: AAM 核心單元測試
# 創建日期: 2025-11-28 21:54 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-28 21:54 (UTC+8)

"""AAM 核心功能單元測試"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from agent_process.memory.aam.models import Memory, MemoryType, MemoryPriority
from agent_process.memory.aam.aam_core import AAMManager
from agent_process.memory.aam.storage_adapter import (
    RedisAdapter,
    ChromaDBAdapter,
    ArangoDBAdapter,
)


class TestMemory:
    """Memory 模型測試"""

    def test_memory_creation(self):
        """測試記憶創建"""
        memory = Memory(
            memory_id="test-1",
            content="Test content",
            memory_type=MemoryType.SHORT_TERM,
            priority=MemoryPriority.HIGH,
        )
        assert memory.memory_id == "test-1"
        assert memory.content == "Test content"
        assert memory.memory_type == MemoryType.SHORT_TERM
        assert memory.priority == MemoryPriority.HIGH

    def test_memory_to_dict(self):
        """測試記憶轉換為字典"""
        memory = Memory(
            memory_id="test-1",
            content="Test content",
            memory_type=MemoryType.SHORT_TERM,
        )
        data = memory.to_dict()
        assert data["memory_id"] == "test-1"
        assert data["content"] == "Test content"
        assert data["memory_type"] == "short_term"

    def test_memory_from_dict(self):
        """測試從字典創建記憶"""
        data = {
            "memory_id": "test-1",
            "content": "Test content",
            "memory_type": "short_term",
            "priority": "high",
            "metadata": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "access_count": 0,
            "relevance_score": 0.5,
        }
        memory = Memory.from_dict(data)
        assert memory.memory_id == "test-1"
        assert memory.memory_type == MemoryType.SHORT_TERM
        assert memory.priority == MemoryPriority.HIGH

    def test_memory_update_access(self):
        """測試記憶訪問更新"""
        memory = Memory(
            memory_id="test-1",
            content="Test content",
            memory_type=MemoryType.SHORT_TERM,
        )
        initial_count = memory.access_count
        memory.update_access()
        assert memory.access_count == initial_count + 1
        assert memory.accessed_at is not None


class TestAAMManager:
    """AAM 管理器測試"""

    @pytest.fixture
    def mock_redis_adapter(self):
        """創建 Redis 適配器 Mock"""
        adapter = Mock(spec=RedisAdapter)
        adapter.store = Mock(return_value=True)
        adapter.retrieve = Mock(return_value=None)
        adapter.update = Mock(return_value=True)
        adapter.delete = Mock(return_value=True)
        adapter.search = Mock(return_value=[])
        return adapter

    @pytest.fixture
    def mock_chromadb_adapter(self):
        """創建 ChromaDB 適配器 Mock"""
        adapter = Mock(spec=ChromaDBAdapter)
        adapter.store = Mock(return_value=True)
        adapter.retrieve = Mock(return_value=None)
        adapter.update = Mock(return_value=True)
        adapter.delete = Mock(return_value=True)
        adapter.search = Mock(return_value=[])
        return adapter

    @pytest.fixture
    def mock_arangodb_adapter(self):
        """創建 ArangoDB 適配器 Mock"""
        adapter = Mock(spec=ArangoDBAdapter)
        adapter.store = Mock(return_value=True)
        adapter.retrieve = Mock(return_value=None)
        adapter.update = Mock(return_value=True)
        adapter.delete = Mock(return_value=True)
        adapter.search = Mock(return_value=[])
        return adapter

    @pytest.fixture
    def aam_manager(
        self, mock_redis_adapter, mock_chromadb_adapter, mock_arangodb_adapter
    ):
        """創建 AAM 管理器實例"""
        return AAMManager(
            redis_adapter=mock_redis_adapter,
            chromadb_adapter=mock_chromadb_adapter,
            arangodb_adapter=mock_arangodb_adapter,
        )

    def test_store_short_term_memory(self, aam_manager, mock_redis_adapter):
        """測試存儲短期記憶"""
        memory_id = aam_manager.store_memory(
            content="Test content",
            memory_type=MemoryType.SHORT_TERM,
            priority=MemoryPriority.HIGH,
        )
        assert memory_id is not None
        mock_redis_adapter.store.assert_called_once()

    def test_store_long_term_memory(self, aam_manager, mock_chromadb_adapter):
        """測試存儲長期記憶"""
        memory_id = aam_manager.store_memory(
            content="Test content",
            memory_type=MemoryType.LONG_TERM,
        )
        assert memory_id is not None
        mock_chromadb_adapter.store.assert_called_once()

    def test_retrieve_memory(self, aam_manager, mock_redis_adapter):
        """測試檢索記憶"""
        # 設置 Mock 返回值
        test_memory = Memory(
            memory_id="test-1",
            content="Test content",
            memory_type=MemoryType.SHORT_TERM,
        )
        mock_redis_adapter.retrieve.return_value = test_memory

        memory = aam_manager.retrieve_memory("test-1", MemoryType.SHORT_TERM)
        assert memory is not None
        assert memory.memory_id == "test-1"
        mock_redis_adapter.retrieve.assert_called_once_with("test-1")

    def test_update_memory(self, aam_manager, mock_redis_adapter):
        """測試更新記憶"""
        # 設置 Mock 返回值
        test_memory = Memory(
            memory_id="test-1",
            content="Original content",
            memory_type=MemoryType.SHORT_TERM,
        )
        mock_redis_adapter.retrieve.return_value = test_memory

        success = aam_manager.update_memory(
            "test-1",
            content="Updated content",
            priority=MemoryPriority.HIGH,
        )
        assert success is True
        mock_redis_adapter.update.assert_called_once()

    def test_delete_memory(self, aam_manager, mock_redis_adapter):
        """測試刪除記憶"""
        success = aam_manager.delete_memory("test-1", MemoryType.SHORT_TERM)
        assert success is True
        mock_redis_adapter.delete.assert_called_once_with("test-1")

    def test_search_memories(self, aam_manager, mock_chromadb_adapter):
        """測試搜索記憶"""
        # 設置 Mock 返回值
        test_memories = [
            Memory(
                memory_id="test-1",
                content="Test content 1",
                memory_type=MemoryType.LONG_TERM,
                relevance_score=0.8,
            ),
            Memory(
                memory_id="test-2",
                content="Test content 2",
                memory_type=MemoryType.LONG_TERM,
                relevance_score=0.6,
            ),
        ]
        mock_chromadb_adapter.search.return_value = test_memories

        results = aam_manager.search_memories("test", MemoryType.LONG_TERM, limit=10)
        assert len(results) == 2
        mock_chromadb_adapter.search.assert_called_once()
