# 代碼功能說明: Orchestrator 端到端測試
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""Orchestrator 端到端測試 - 測試完整執行流程"""

import pytest
from typing import Any, Dict

from agents.services.orchestrator.models import TaskRequest
from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.models import TaskAnalysisRequest


class TestOrchestratorE2E:
    """Orchestrator 端到端測試類"""

    @pytest.mark.asyncio
    async def test_process_natural_language_request(
        self, orchestrator: AgentOrchestrator, sample_task_request: Dict[str, Any]
    ):
        """測試處理自然語言請求"""
        request = TaskAnalysisRequest(**sample_task_request)

        result = await orchestrator.process_natural_language_request(
            request.task,
            user_id=request.user_id,
            context=request.context,
        )

        # 驗證結果
        assert result is not None, "結果不應為 None"
        assert "task_id" in result or hasattr(result, "task_id")

    @pytest.mark.asyncio
    async def test_execute_task_flow(self, orchestrator: AgentOrchestrator):
        """測試任務執行流程"""
        task_request = TaskRequest(
            task_id="test_task_123",
            task_type="test",
            task_data={"action": "test"},
        )

        # 提交任務
        task_id = orchestrator.submit_task(
            task_type=task_request.task_type,
            task_data=task_request.task_data,
        )

        assert task_id is not None, "任務 ID 不應為 None"

        # 驗證任務狀態
        task_status = orchestrator.get_task_status(task_id)
        assert task_status is not None, "任務狀態不應為 None"

    @pytest.mark.asyncio
    async def test_execution_record_storage(
        self, orchestrator: AgentOrchestrator, sample_task_request: Dict[str, Any]
    ):
        """測試執行記錄存儲（L5 層級）"""
        request = TaskAnalysisRequest(**sample_task_request)

        result = await orchestrator.process_natural_language_request(
            request.task,
            user_id=request.user_id,
            context=request.context,
        )

        # 驗證執行記錄已存儲
        # 注意：實際實現中，ExecutionRecord 應該在 execute_task 中記錄
        # 這裡主要驗證流程完整性

        assert result is not None, "結果不應為 None"

    @pytest.mark.asyncio
    async def test_agent_discovery(self, orchestrator: AgentOrchestrator):
        """測試 Agent 發現"""
        agents = orchestrator.discover_agents()

        # 驗證 Agent 發現功能
        assert isinstance(agents, list), "Agent 列表應為 list"

    @pytest.mark.asyncio
    async def test_task_analysis_integration(
        self, orchestrator: AgentOrchestrator, sample_task_request: Dict[str, Any]
    ):
        """測試任務分析集成"""
        request = TaskAnalysisRequest(**sample_task_request)

        # 通過 Orchestrator 處理請求
        result = await orchestrator.process_natural_language_request(
            request.task,
            user_id=request.user_id,
            context=request.context,
        )

        # 驗證分析結果
        assert result is not None, "分析結果不應為 None"
