# 代碼功能說明: Task Analyzer v4.0 性能測試 - 階段七測試驗證
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Task Analyzer v4.0 性能測試 - 測試各層級性能指標"""

import pytest
import time
from unittest.mock import AsyncMock, patch

from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import TaskAnalysisRequest


@pytest.mark.performance
@pytest.mark.asyncio
class TestTaskAnalyzerV4Performance:
    """Task Analyzer v4.0 性能測試類"""

    @pytest.fixture
    def task_analyzer(self):
        """創建 TaskAnalyzer 實例"""
        return TaskAnalyzer()

    @pytest.mark.asyncio
    async def test_l1_latency(self, task_analyzer, sample_task_request, mock_router_llm):
        """測試 L1 層級延遲時間"""
        request = TaskAnalysisRequest(**sample_task_request)

        start_time = time.time()
        with patch.object(task_analyzer.router_llm, "route_v4", new=mock_router_llm.route_v4):
            result = await task_analyzer.analyze(request)
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000
        assert latency_ms < 5000  # L1 延遲應該小於 5 秒

    @pytest.mark.asyncio
    async def test_total_latency(self, task_analyzer, sample_task_request, mock_router_llm, mock_orchestrator):
        """測試總體處理時間"""
        request = TaskAnalysisRequest(**sample_task_request)

        start_time = time.time()
        with patch.object(task_analyzer.router_llm, "route_v4", new=mock_router_llm.route_v4):
            with patch.object(task_analyzer, "_execute_task_dag", new=mock_orchestrator.execute_task):
                result = await task_analyzer.analyze(request)
        end_time = time.time()

        total_latency_ms = (end_time - start_time) * 1000
        assert total_latency_ms < 10000  # 總體延遲應該小於 10 秒

    @pytest.mark.asyncio
    async def test_performance_metrics_in_result(self, task_analyzer, sample_task_request, mock_router_llm, mock_orchestrator):
        """測試性能指標是否記錄在結果中"""
        request = TaskAnalysisRequest(**sample_task_request)

        with patch.object(task_analyzer.router_llm, "route_v4", new=mock_router_llm.route_v4):
            with patch.object(task_analyzer, "_execute_task_dag", new=mock_orchestrator.execute_task):
                result = await task_analyzer.analyze(request)

                assert "performance_metrics" in result.analysis_details
                metrics = result.analysis_details["performance_metrics"]
                assert isinstance(metrics, dict)
