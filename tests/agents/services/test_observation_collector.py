# 代碼功能說明: Observation Collector 單元測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Observation Collector 單元測試

測試 Observation Collector 的核心功能：fan-in 匯整和 Observation Summary 生成。
"""


from agents.services.observation_collector import ObservationCollector
from agents.services.observation_collector.models import FanInMode
from agents.services.orchestrator.models import TaskResult, TaskStatus


class TestObservationCollector:
    """Observation Collector 測試類"""

    def test_observation_collector_init(self):
        """測試 Observation Collector 初始化"""
        collector = ObservationCollector()
        assert collector is not None

    def test_fan_in_all_mode(self):
        """測試 fan-in all 模式"""
        collector = ObservationCollector()

        observations = [
            {"task_id": "task-1", "status": "success", "confidence": 0.9},
            {"task_id": "task-2", "status": "success", "confidence": 0.8},
        ]

        summary = collector.fan_in(observations, mode=FanInMode.ALL)
        assert summary.success_rate == 1.0
        assert summary.blocking_issues is False
        assert summary.total_count == 2
        assert summary.success_count == 2

    def test_fan_in_any_mode(self):
        """測試 fan-in any 模式"""
        collector = ObservationCollector()

        observations = [
            {"task_id": "task-1", "status": "failed", "confidence": 0.3},
            {"task_id": "task-2", "status": "success", "confidence": 0.9},
        ]

        summary = collector.fan_in(observations, mode=FanInMode.ANY)
        assert summary.success_rate == 0.5
        assert summary.blocking_issues is False  # any 模式：至少一個成功即可
        assert summary.total_count == 2

    def test_fan_in_quorum_mode(self):
        """測試 fan-in quorum 模式"""
        collector = ObservationCollector()

        observations = [
            {"task_id": "task-1", "status": "success", "confidence": 0.9},
            {"task_id": "task-2", "status": "success", "confidence": 0.8},
            {"task_id": "task-3", "status": "failed", "confidence": 0.2},
        ]

        summary = collector.fan_in(observations, mode=FanInMode.QUORUM, threshold=0.7)
        assert summary.success_rate == 2.0 / 3.0
        assert summary.blocking_issues is False  # 2/3 > 0.7，滿足 quorum

    def test_fan_in_with_task_result(self):
        """測試使用 TaskResult 對象進行 fan-in"""
        collector = ObservationCollector()

        task_results = [
            TaskResult(
                task_id="task-1",
                status=TaskStatus.COMPLETED,
                result={"data": "result1"},
            ),
            TaskResult(
                task_id="task-2",
                status=TaskStatus.COMPLETED,
                result={"data": "result2"},
            ),
        ]

        summary = collector.fan_in(task_results, mode=FanInMode.ALL)
        assert summary.success_rate == 1.0
        assert summary.total_count == 2

    def test_generate_summary(self):
        """測試生成 Observation Summary"""
        collector = ObservationCollector()

        observations = [
            {"task_id": "task-1", "status": "success", "confidence": 0.9},
            {"task_id": "task-2", "status": "partial", "confidence": 0.6},
        ]

        summary = collector.generate_summary(observations, mode=FanInMode.ALL)
        assert summary.success_rate == 0.5
        assert summary.partial_count == 1
        assert summary.lowest_confidence == 0.6
