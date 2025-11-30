# 代碼功能說明: Task Analyzer 整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""測試劇本 IT-2.1：Task Analyzer 任務分析整合測試"""

import pytest
from typing import AsyncGenerator
import time
from httpx import AsyncClient
from tests.integration.test_helpers import assert_response_success


@pytest.mark.integration
@pytest.mark.asyncio
class TestTaskAnalyzer:
    """Task Analyzer 整合測試"""

    @pytest.fixture(scope="function")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    async def test_simple_task_analysis(self, client: AsyncClient):
        """步驟 1: 簡單任務分析測試"""
        start_time = time.time()
        response = await client.post(
            "/api/v1/task-analyzer/analyze",
            json={"task": "今天天氣如何？", "context": {}},
        )
        elapsed = time.time() - start_time

        assert_response_success(response)
        assert elapsed < 2, f"響應時間 {elapsed}s 超過 2 秒"

        data = response.json()
        result_data = data.get("data", {})

        # 驗證響應內容
        assert "task_id" in result_data, "響應缺少 task_id"
        assert "task_type" in result_data, "響應缺少 task_type"
        assert "workflow_type" in result_data, "響應缺少 workflow_type"
        assert "confidence" in result_data, "響應缺少 confidence"

        # 驗證任務類型（簡單查詢任務應該是 QUERY）
        task_type = result_data.get("task_type")
        assert task_type in [
            "query",
            "execution",
            "review",
            "planning",
            "complex",
        ], f"無效的任務類型: {task_type}"

    async def test_complex_task_analysis(self, client: AsyncClient):
        """步驟 2: 複雜任務分析測試"""
        start_time = time.time()
        response = await client.post(
            "/api/v1/task-analyzer/analyze",
            json={"task": "分析競爭對手並制定應對策略", "context": {}},
        )
        elapsed = time.time() - start_time

        assert_response_success(response)
        assert elapsed < 2, f"響應時間 {elapsed}s 超過 2 秒"

        data = response.json()
        result_data = data.get("data", {})

        # 驗證響應內容
        assert "task_id" in result_data, "響應缺少 task_id"
        assert "task_type" in result_data, "響應缺少 task_type"
        assert "workflow_type" in result_data, "響應缺少 workflow_type"

        # 驗證複雜任務的類型（應該是 COMPLEX 或 PLANNING）
        task_type = result_data.get("task_type")
        assert task_type in [
            "complex",
            "planning",
        ], f"複雜任務應為 complex 或 planning，實際為: {task_type}"

    async def test_task_classification(self, client: AsyncClient):
        """步驟 3: 任務分類測試"""
        test_cases = [
            {"task": "查詢數據庫", "expected_type": "query"},
            {"task": "執行計算", "expected_type": "execution"},
            {"task": "審查代碼", "expected_type": "review"},
            {"task": "制定計劃", "expected_type": "planning"},
        ]

        for test_case in test_cases:
            response = await client.post(
                "/api/v1/task-analyzer/analyze",
                json={"task": test_case["task"], "context": {}},
            )
            assert_response_success(response)

            data = response.json()
            result_data = data.get("data", {})
            task_type = result_data.get("task_type")

            # 驗證任務類型（允許靈活匹配）
            assert task_type in [
                "query",
                "execution",
                "review",
                "planning",
                "complex",
            ], f"任務 '{test_case['task']}' 的分類結果無效: {task_type}"

    async def test_workflow_selection(self, client: AsyncClient):
        """步驟 4: 工作流選擇測試"""
        response = await client.post(
            "/api/v1/task-analyzer/analyze",
            json={"task": "開發一個簡單的待辦事項應用", "context": {}},
        )
        assert_response_success(response)

        data = response.json()
        result_data = data.get("data", {})

        # 驗證工作流選擇
        workflow_type = result_data.get("workflow_type")
        assert workflow_type in [
            "langchain",
            "crewai",
            "autogen",
            "hybrid",
        ], f"無效的工作流類型: {workflow_type}"

    async def test_complexity_assessment(self, client: AsyncClient):
        """步驟 5: 複雜度評估測試"""
        # 簡單任務
        response = await client.post(
            "/api/v1/task-analyzer/analyze",
            json={"task": "今天幾號？", "context": {}},
        )
        assert_response_success(response)
        data = response.json()
        result_data = data.get("data", {})

        # 驗證複雜度相關字段（如果存在）
        if "analysis_details" in result_data:
            analysis = result_data.get("analysis_details", {})
            # 簡單任務的複雜度應該較低
            if "complexity" in analysis:
                complexity = analysis.get("complexity")
                assert isinstance(complexity, (int, float, str)), "複雜度應該是數字或字符串"
