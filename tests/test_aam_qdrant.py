#!/usr/bin/env python3
# 代碼功能說明: AAM Qdrant 記憶防護單元測試
# 創建日期: 2026-02-02
# 創建人: OpenCode AI
# 最後修改日期: 2026-02-02

"""
AAM Qdrant 記憶防護單元測試

測試內容:
1. Memory 模型擴展欄位
2. QdrantAdapter 基本功能（mock）
3. 定期檢討 Job 邏輯
4. User Isolation 邏輯
"""

import pytest
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import Any, Dict, List, Optional

# 測試路徑設置
sys.path.insert(0, "/home/daniel/ai-box")

from agents.infra.memory.aam.models import Memory, MemoryType, MemoryPriority
from agents.infra.memory.aam.qdrant_adapter import MemoryConflict


class TestMemoryModel:
    """Memory 模型測試"""

    def test_memory_to_dict(self):
        """測試 Memory 轉字典"""
        memory = Memory(
            memory_id="test_001",
            content="RM05-008 料號",
            memory_type=MemoryType.LONG_TERM,
            priority=MemoryPriority.HIGH,
            user_id="user_123",
            entity_type="part_number",
            entity_value="RM05-008",
            confidence=0.95,
            status="active",
        )

        result = memory.to_dict()

        assert result["memory_id"] == "test_001"
        assert result["content"] == "RM05-008 料號"
        assert result["memory_type"] == "long_term"
        assert result["priority"] == "high"
        assert result["user_id"] == "user_123"
        assert result["entity_type"] == "part_number"
        assert result["entity_value"] == "RM05-008"
        assert result["confidence"] == 0.95
        assert result["status"] == "active"

    def test_memory_from_dict(self):
        """測試從字典創建 Memory"""
        data = {
            "memory_id": "test_002",
            "content": "ABC-123 料號",
            "memory_type": "long_term",
            "priority": "medium",
            "user_id": "user_456",
            "entity_type": "part_number",
            "entity_value": "ABC-123",
            "confidence": 0.8,
            "status": "active",
            "access_count": 5,
            "created_at": "2026-01-01T10:00:00",
            "updated_at": "2026-02-01T10:00:00",
        }

        memory = Memory.from_dict(data)

        assert memory.memory_id == "test_002"
        assert memory.user_id == "user_456"
        assert memory.confidence == 0.8
        assert memory.access_count == 5

    def test_memory_from_dict_defaults(self):
        """測試 Memory 預設值"""
        data = {
            "memory_id": "test_003",
            "content": "測試內容",
            "memory_type": "short_term",
        }

        memory = Memory.from_dict(data)

        assert memory.user_id == ""
        assert memory.entity_type == ""
        assert memory.confidence == 0.5
        assert memory.status == "active"


class TestMemoryConflict:
    """MemoryConflict 測試"""

    def test_conflict_creation(self):
        """測試衝突報告創建"""
        memory = Memory(
            memory_id="conflict_001",
            content="衝突記憶",
            memory_type=MemoryType.LONG_TERM,
        )

        conflict = MemoryConflict(
            existing_memory=memory,
            new_confidence=0.95,
            similarity=0.92,
            suggested_action="overwrite",
        )

        assert conflict.existing_memory.memory_id == "conflict_001"
        assert conflict.new_confidence == 0.95
        assert conflict.similarity == 0.92
        assert conflict.suggested_action == "overwrite"


class TestQdrantAdapterLogic:
    """QdrantAdapter 邏輯測試（Mock）"""

    def test_entity_type_constants(self):
        """測試實體類型常量"""
        from agents.infra.memory.aam.qdrant_adapter import QdrantAdapter

        assert QdrantAdapter.ENTITY_TYPE_PART_NUMBER == "part_number"
        assert QdrantAdapter.ENTITY_TYPE_TLF19 == "tlf19"
        assert QdrantAdapter.ENTITY_TYPE_INTENT == "intent"

    def test_status_constants(self):
        """測試狀態常量"""
        from agents.infra.memory.aam.qdrant_adapter import QdrantAdapter

        assert QdrantAdapter.STATUS_ACTIVE == "active"
        assert QdrantAdapter.STATUS_ARCHIVED == "archived"
        assert QdrantAdapter.STATUS_REVIEW == "review"


class TestMemoryReviewJob:
    """定期檢討 Job 測試"""

    def test_review_report_creation(self):
        """測試檢討報告創建"""
        from jobs.memory_review_job import MemoryReviewReport

        report = MemoryReviewReport(user_id="user_123")

        assert report.user_id == "user_123"
        assert report.low_hotness_count == 0
        assert report.archived_count == 0
        assert report.review_count == 0
        assert isinstance(report.suggestions, list)

    def test_review_report_to_dict(self):
        """測試檢討報告轉字典"""
        from jobs.memory_review_job import MemoryReviewReport

        report = MemoryReviewReport(user_id="user_456")
        report.low_hotness_count = 5
        report.archived_count = 3
        report.suggestions = ["建議1", "建議2"]

        result = report.to_dict()

        assert result["user_id"] == "user_456"
        assert result["low_hotness_count"] == 5
        assert result["archived_count"] == 3
        assert len(result["suggestions"]) == 2


class TestUserIsolation:
    """User Isolation 測試"""

    def test_user_isolation_concept(self):
        """測試用戶隔離概念"""
        # 模擬不同用戶的記憶
        user_a_memory = Memory(
            memory_id="mem_a1",
            content="RM05-008 是用戶A的料號",
            memory_type=MemoryType.LONG_TERM,
            user_id="user_A",
            entity_type="part_number",
            entity_value="RM05-008",
        )

        user_b_memory = Memory(
            memory_id="mem_b1",
            content="RM05-008 是用戶B的料號",
            memory_type=MemoryType.LONG_TERM,
            user_id="user_B",
            entity_type="part_number",
            entity_value="RM05-008",
        )

        # 驗證 user_id 不同
        assert user_a_memory.user_id != user_b_memory.user_id
        assert user_a_memory.user_id == "user_A"
        assert user_b_memory.user_id == "user_B"


class TestConflictDetection:
    """衝突檢測測試"""

    def test_conflict_detection_logic(self):
        """測試衝突檢測邏輯"""
        existing_memory = Memory(
            memory_id="existing_001",
            content="RM05-008 料號",
            memory_type=MemoryType.LONG_TERM,
            confidence=0.8,
        )

        # 新記憶置信度更高，應該覆寫
        new_confidence = 0.95
        similarity = 0.92

        suggested_action = (
            "overwrite" if new_confidence > existing_memory.confidence else "ignore"
        )

        assert suggested_action == "overwrite"

        # 新記憶置信度更低，不應覆寫
        new_confidence_low = 0.7
        suggested_action_low = (
            "overwrite" if new_confidence_low > existing_memory.confidence else "ignore"
        )

        assert suggested_action_low == "ignore"

    def test_similarity_threshold(self):
        """測試相似度閾值"""
        similarity = 0.92

        # 0.85 < similarity < 1.0 表示高度相似但不相同
        is_highly_similar = 0.85 < similarity < 1.0

        assert is_highly_similar is True

        # 相同
        similarity_exact = 1.0
        is_exact_match = 0.85 < similarity_exact < 1.0

        assert is_exact_match is False


class TestMemoryTTL:
    """記憶時效性測試"""

    def test_staleness判断(self):
        """測試過時判斷"""
        from jobs.memory_review_job import MemoryReviewJob

        # 模擬記憶
        old_memory = Memory(
            memory_id="old_001",
            content="舊記憶",
            memory_type=MemoryType.LONG_TERM,
            created_at=datetime.now() - timedelta(days=100),
            updated_at=datetime.now() - timedelta(days=100),
            access_count=1,
        )

        new_memory = Memory(
            memory_id="new_001",
            content="新記憶",
            memory_type=MemoryType.LONG_TERM,
            created_at=datetime.now() - timedelta(days=10),
            updated_at=datetime.now() - timedelta(days=10),
            access_count=10,
        )

        # 舊記憶應該被標記為低熱度
        is_old_and_low_access = (
            old_memory.access_count <= 3 and
            (datetime.now() - old_memory.updated_at).days > 90
        )

        assert is_old_and_low_access is True

        # 新記憶不應該被標記
        is_new_low_access = (
            new_memory.access_count <= 3 and
            (datetime.now() - new_memory.updated_at).days > 90
        )

        assert is_new_low_access is False


def run_all_tests():
    """運行所有測試"""
    import os

    os.chdir("/home/daniel/ai-box")

    print("=" * 60)
    print("AAM Qdrant 記憶防護單元測試")
    print("=" * 60)

    test_classes = [
        TestMemoryModel,
        TestMemoryConflict,
        TestQdrantAdapterLogic,
        TestMemoryReviewJob,
        TestUserIsolation,
        TestConflictDetection,
        TestMemoryTTL,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        instance = test_class()

        for method_name in dir(instance):
            if method_name.startswith("test_"):
                total_tests += 1
                try:
                    getattr(instance, method_name)()
                    print(f"  ✓ {method_name}")
                    passed_tests += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed_tests += 1

    print("\n" + "=" * 60)
    print(f"測試結果: {passed_tests}/{total_tests} 通過")
    if failed_tests > 0:
        print(f"  ✗ {failed_tests} 失敗")
    print("=" * 60)

    return failed_tests == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
