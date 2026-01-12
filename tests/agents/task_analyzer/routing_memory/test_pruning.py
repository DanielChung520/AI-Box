# 代碼功能說明: 記憶裁剪測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""記憶裁剪測試 - 測試記憶裁剪服務功能"""


import pytest

from agents.task_analyzer.routing_memory.pruning import PruningService


class TestPruningService:
    """測試記憶裁剪服務"""

    def test_calculate_frequency(self):
        """測試計算使用頻率"""
        pruning_service = PruningService(ttl_days=90)

        # 注意：實際測試需要 mock ArangoDB 或使用測試數據庫
        frequencies = pruning_service.calculate_frequency(days=30)

        assert isinstance(frequencies, dict)
        # 驗證頻率值在 0-1 之間
        for freq in frequencies.values():
            assert 0.0 <= freq <= 1.0

    def test_prune_by_ttl(self):
        """測試根據 TTL 清理過期數據"""
        pruning_service = PruningService(ttl_days=90)

        # 注意：實際測試需要 mock ArangoDB
        deleted_count = pruning_service.prune_by_ttl()

        assert isinstance(deleted_count, int)
        assert deleted_count >= 0

    def test_prune_by_frequency(self):
        """測試根據頻率清理低價值數據"""
        pruning_service = PruningService(ttl_days=90, min_frequency=0.01, min_success_rate=0.3)

        # 提供測試頻率數據
        test_frequencies = {
            "decision-1": 0.05,  # 高頻率，應該保留
            "decision-2": 0.005,  # 低頻率，應該清理
            "decision-3": 0.02,  # 中等頻率，應該保留
        }

        # 注意：實際測試需要 mock ArangoDB
        deleted_count = pruning_service.prune_by_frequency(frequencies=test_frequencies)

        assert isinstance(deleted_count, int)
        assert deleted_count >= 0

    @pytest.mark.asyncio
    async def test_update_embeddings(self):
        """測試更新 Embedding"""
        pruning_service = PruningService()

        # 注意：實際測試需要 mock 服務
        updated_count = await pruning_service.update_embeddings(
            decision_keys=["decision-1", "decision-2"]
        )

        assert isinstance(updated_count, int)
        assert updated_count >= 0

    @pytest.mark.asyncio
    async def test_prune_all(self):
        """測試完整的記憶裁剪流程"""
        pruning_service = PruningService(ttl_days=90, min_frequency=0.01, min_success_rate=0.3)

        # 注意：實際測試需要 mock ArangoDB
        stats = await pruning_service.prune_all()

        assert isinstance(stats, dict)
        assert "ttl_pruned" in stats
        assert "frequency_pruned" in stats
        assert "total_pruned" in stats
        assert stats["total_pruned"] == stats["ttl_pruned"] + stats["frequency_pruned"]


class TestPruningTask:
    """測試記憶裁剪後台任務"""

    @pytest.mark.asyncio
    async def test_run_once(self):
        """測試執行一次記憶裁剪"""
        from agents.task_analyzer.routing_memory.pruning_task import PruningTask

        task = PruningTask(interval_hours=24, ttl_days=90)

        # 注意：實際測試需要 mock 服務
        stats = await task.run_once()

        assert isinstance(stats, dict)
