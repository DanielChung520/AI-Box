# 代碼功能說明: Task Analyzer v4.0 壓力測試 - 階段七測試驗證
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Task Analyzer v4.0 壓力測試 - 測試高並發和大負載下的系統穩定性"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import TaskAnalysisRequest


@pytest.mark.stress
@pytest.mark.asyncio
class TestTaskAnalyzerV4Stress:
    """Task Analyzer v4.0 壓力測試類"""

    @pytest.fixture
    def task_analyzer(self):
        """創建 TaskAnalyzer 實例"""
        return TaskAnalyzer()

    @pytest.mark.asyncio
    async def test_concurrent_requests_10(self, task_analyzer, sample_task_request, mock_router_llm):
        """測試 10 個並發請求"""
        request = TaskAnalysisRequest(**sample_task_request)

        async def run_analysis():
            with patch.object(task_analyzer.router_llm, "route_v4", new=mock_router_llm.route_v4):
                return await task_analyzer.analyze(request)

        tasks = [run_analysis() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 驗證所有請求都成功（沒有異常）
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        assert success_count >= 9  # 至少 90% 成功率

    @pytest.mark.asyncio
    async def test_concurrent_requests_50(self, task_analyzer, sample_task_request, mock_router_llm):
        """測試 50 個並發請求"""
        request = TaskAnalysisRequest(**sample_task_request)

        async def run_analysis():
            with patch.object(task_analyzer.router_llm, "route_v4", new=mock_router_llm.route_v4):
                return await task_analyzer.analyze(request)

        tasks = [run_analysis() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 驗證大部分請求成功
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        assert success_count >= 45  # 至少 90% 成功率
