# 代碼功能說明: Task Analyzer 性能測試
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""Task Analyzer 性能測試 - 測試響應時間和性能指標"""

import statistics
import time
from typing import Any, Dict, List

import pytest

from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import TaskAnalysisRequest


class TestTaskAnalyzerPerformance:
    """Task Analyzer 性能測試類"""

    @pytest.mark.asyncio
    async def test_l1_response_time(
        self, task_analyzer: TaskAnalyzer, sample_task_request: Dict[str, Any], benchmark
    ):
        """測試 L1 層響應時間"""
        request = TaskAnalysisRequest(**sample_task_request)

        # 運行多次測試以獲取統計數據
        response_times: List[float] = []

        async def run_test():
            start_time = time.time()
            result = await task_analyzer.analyze(request)
            elapsed_time = time.time() - start_time
            response_times.append(elapsed_time)
            return result

        # 運行 10 次測試
        for _ in range(10):
            await run_test()

        # 計算統計數據
        mean_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]  # P95

        print(f"L1 層響應時間統計:")
        print(f"  平均: {mean_time:.3f}s")
        print(f"  P95: {p95_time:.3f}s")
        print(f"  最小: {min(response_times):.3f}s")
        print(f"  最大: {max(response_times):.3f}s")

        # 驗證 P95 響應時間 ≤1秒
        assert p95_time <= 1.0, f"L1 層 P95 響應時間 {p95_time:.3f}s 超過 1 秒"

    @pytest.mark.asyncio
    async def test_end_to_end_response_time(
        self, task_analyzer: TaskAnalyzer, sample_task_request: Dict[str, Any]
    ):
        """測試端到端響應時間"""
        request = TaskAnalysisRequest(**sample_task_request)

        # 運行多次測試以獲取統計數據
        response_times: List[float] = []

        for _ in range(10):
            start_time = time.time()
            result = await task_analyzer.analyze(request)
            elapsed_time = time.time() - start_time
            response_times.append(elapsed_time)
            assert result is not None

        # 計算統計數據
        mean_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]  # P95

        print(f"端到端響應時間統計:")
        print(f"  平均: {mean_time:.3f}s")
        print(f"  P95: {p95_time:.3f}s")
        print(f"  最小: {min(response_times):.3f}s")
        print(f"  最大: {max(response_times):.3f}s")

        # 驗證 P95 響應時間 ≤3秒
        assert p95_time <= 3.0, f"端到端 P95 響應時間 {p95_time:.3f}s 超過 3 秒"

    @pytest.mark.asyncio
    async def test_simple_query_performance(
        self, task_analyzer: TaskAnalyzer, sample_simple_query: Dict[str, Any]
    ):
        """測試簡單查詢性能（Layer 0）"""
        request = TaskAnalysisRequest(**sample_simple_query)

        response_times: List[float] = []

        for _ in range(10):
            start_time = time.time()
            result = await task_analyzer.analyze(request)
            elapsed_time = time.time() - start_time
            response_times.append(elapsed_time)
            assert result is not None

        mean_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]

        print(f"簡單查詢響應時間統計:")
        print(f"  平均: {mean_time:.3f}s")
        print(f"  P95: {p95_time:.3f}s")

        # Layer 0 應該非常快
        assert p95_time <= 0.5, f"簡單查詢 P95 響應時間 {p95_time:.3f}s 超過 0.5 秒"

    @pytest.mark.asyncio
    async def test_complex_task_performance(
        self, task_analyzer: TaskAnalyzer, sample_complex_task: Dict[str, Any]
    ):
        """測試複雜任務性能"""
        request = TaskAnalysisRequest(**sample_complex_task)

        response_times: List[float] = []

        for _ in range(5):  # 複雜任務運行較少次數
            start_time = time.time()
            result = await task_analyzer.analyze(request)
            elapsed_time = time.time() - start_time
            response_times.append(elapsed_time)
            assert result is not None

        mean_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)

        print(f"複雜任務響應時間統計:")
        print(f"  平均: {mean_time:.3f}s")
        print(f"  P95: {p95_time:.3f}s")

        # 複雜任務可能需要更長時間，但仍然應該在合理範圍內
        assert p95_time <= 5.0, f"複雜任務 P95 響應時間 {p95_time:.3f}s 超過 5 秒"

    @pytest.mark.asyncio
    async def test_concurrent_requests(
        self, task_analyzer: TaskAnalyzer, sample_task_request: Dict[str, Any]
    ):
        """測試並發請求性能"""
        import asyncio

        request = TaskAnalysisRequest(**sample_task_request)

        async def process_request():
            start_time = time.time()
            result = await task_analyzer.analyze(request)
            elapsed_time = time.time() - start_time
            return elapsed_time, result

        # 並發處理 5 個請求
        tasks = [process_request() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        response_times = [r[0] for r in results]

        mean_time = statistics.mean(response_times)
        max_time = max(response_times)

        print(f"並發請求響應時間統計:")
        print(f"  平均: {mean_time:.3f}s")
        print(f"  最大: {max_time:.3f}s")

        # 並發請求不應該顯著增加響應時間
        assert max_time <= 4.0, f"並發請求最大響應時間 {max_time:.3f}s 超過 4 秒"
