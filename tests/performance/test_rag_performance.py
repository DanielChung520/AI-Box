# 代碼功能說明: RAG 檢索性能測試
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""RAG 檢索性能測試 - 測試 RAG-1/RAG-2/RAG-3 檢索時間"""

import statistics
import time
from typing import List

import pytest

from agents.task_analyzer.rag_service import RAGService


class TestRAGPerformance:
    """RAG 檢索性能測試類"""

    @pytest.fixture
    def rag_service(self):
        """創建 RAG Service 實例"""
        from agents.task_analyzer.rag_service import RAGService

        return RAGService()

    @pytest.mark.asyncio
    async def test_rag_retrieval_time(self, rag_service: RAGService):
        """測試 RAG 檢索時間"""
        query = "查詢系統架構信息"

        response_times: List[float] = []

        for _ in range(10):
            start_time = time.time()
            # 測試 RAG-1 檢索
            results = await rag_service.retrieve(
                query=query,
                namespace="RAG-1",
                top_k=5,
            )
            elapsed_time = time.time() - start_time
            response_times.append(elapsed_time)

        mean_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]

        print(f"RAG 檢索響應時間統計:")
        print(f"  平均: {mean_time:.3f}s")
        print(f"  P95: {p95_time:.3f}s")

        # 驗證 P95 響應時間 ≤200ms
        assert p95_time <= 0.2, f"RAG 檢索 P95 響應時間 {p95_time:.3f}s 超過 200ms"

    @pytest.mark.asyncio
    async def test_rag2_capability_retrieval(self, rag_service: RAGService):
        """測試 RAG-2 Capability 檢索性能"""
        query = "需要文件編輯能力"

        response_times: List[float] = []

        for _ in range(10):
            start_time = time.time()
            results = await rag_service.retrieve(
                query=query,
                namespace="RAG-2",
                top_k=10,
            )
            elapsed_time = time.time() - start_time
            response_times.append(elapsed_time)

        mean_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]

        print(f"RAG-2 Capability 檢索響應時間統計:")
        print(f"  平均: {mean_time:.3f}s")
        print(f"  P95: {p95_time:.3f}s")

        # RAG-2 檢索應該很快
        assert p95_time <= 0.2, f"RAG-2 檢索 P95 響應時間 {p95_time:.3f}s 超過 200ms"

    @pytest.mark.asyncio
    async def test_rag3_policy_retrieval(self, rag_service: RAGService):
        """測試 RAG-3 Policy 檢索性能"""
        query = "查詢策略和約束信息"

        response_times: List[float] = []

        for _ in range(10):
            start_time = time.time()
            results = await rag_service.retrieve(
                query=query,
                namespace="RAG-3",
                top_k=5,
            )
            elapsed_time = time.time() - start_time
            response_times.append(elapsed_time)

        mean_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]

        print(f"RAG-3 Policy 檢索響應時間統計:")
        print(f"  平均: {mean_time:.3f}s")
        print(f"  P95: {p95_time:.3f}s")

        # RAG-3 檢索應該很快
        assert p95_time <= 0.2, f"RAG-3 檢索 P95 響應時間 {p95_time:.3f}s 超過 200ms"
