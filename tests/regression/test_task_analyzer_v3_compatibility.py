# 代碼功能說明: Task Analyzer v3 兼容性回歸測試 - 階段七測試驗證
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Task Analyzer v3 兼容性回歸測試 - 確保 v3 功能在 v4.0 中仍然正常"""

import pytest
from unittest.mock import AsyncMock, patch

from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import TaskAnalysisRequest, TaskType


@pytest.mark.regression
@pytest.mark.asyncio
class TestTaskAnalyzerV3Compatibility:
    """Task Analyzer v3 兼容性回歸測試類"""

    @pytest.fixture
    def task_analyzer(self):
        """創建 TaskAnalyzer 實例"""
        return TaskAnalyzer()

    @pytest.mark.asyncio
    async def test_v3_basic_query_still_works(self, task_analyzer, sample_simple_query, mock_router_llm):
        """測試 v3 基本查詢功能仍然正常"""
        request = TaskAnalysisRequest(**sample_simple_query)

        with patch.object(task_analyzer.router_llm, "route_v4", new=mock_router_llm.route_v4):
            result = await task_analyzer.analyze(request)

            assert result is not None
            assert result.task_id is not None
            assert result.task_type == TaskType.QUERY

    @pytest.mark.asyncio
    async def test_v3_execution_task_still_works(self, task_analyzer, sample_document_editing_task, mock_router_llm, mock_orchestrator):
        """測試 v3 執行任務功能仍然正常"""
        request = TaskAnalysisRequest(**sample_document_editing_task)

        with patch.object(task_analyzer.router_llm, "route_v4", new=mock_router_llm.route_v4):
            with patch.object(task_analyzer, "_execute_task_dag", new=mock_orchestrator.execute_task):
                result = await task_analyzer.analyze(request)

                assert result is not None
                assert result.task_id is not None
                assert result.task_type in [TaskType.EXECUTION, TaskType.COMPLEX]
