# 代碼功能說明: 回歸測試
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""回歸測試 - 測試現有功能不受影響、向後兼容性、API 兼容性"""

import pytest
from typing import Any, Dict

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import (
    TaskAnalysisRequest,
    TaskAnalysisResult,
    TaskType,
    WorkflowType,
)


class TestRegression:
    """回歸測試類"""

    @pytest.mark.asyncio
    async def test_existing_task_analyzer_functionality(
        self, task_analyzer: TaskAnalyzer, sample_task_request: Dict[str, Any]
    ):
        """測試現有 Task Analyzer 功能不受影響"""
        request = TaskAnalysisRequest(**sample_task_request)

        result = await task_analyzer.analyze(request)

        # 驗證現有功能仍然正常
        assert isinstance(result, TaskAnalysisResult), "結果類型應為 TaskAnalysisResult"
        assert result.task_id is not None, "Task ID 不應為 None"
        assert result.task_type in TaskType, f"Task Type 應為有效的 TaskType，實際為 {result.task_type}"
        assert result.workflow_type in WorkflowType, f"Workflow Type 應為有效的 WorkflowType，實際為 {result.workflow_type}"
        assert 0.0 <= result.confidence <= 1.0, f"Confidence 應在 0-1 之間，實際為 {result.confidence}"
        assert isinstance(result.requires_agent, bool), "requires_agent 應為 bool"
        assert isinstance(result.suggested_agents, list), "suggested_agents 應為 list"
        assert isinstance(result.analysis_details, dict), "analysis_details 應為 dict"

    @pytest.mark.asyncio
    async def test_backward_compatibility_api_format(
        self, task_analyzer: TaskAnalyzer, sample_task_request: Dict[str, Any]
    ):
        """測試 API 格式向後兼容"""
        request = TaskAnalysisRequest(**sample_task_request)

        result = await task_analyzer.analyze(request)

        # 驗證 API 響應格式兼容
        result_dict = result.model_dump()

        # 驗證必要字段存在
        required_fields = [
            "task_id",
            "task_type",
            "workflow_type",
            "llm_provider",
            "confidence",
            "requires_agent",
            "suggested_agents",
            "analysis_details",
        ]

        for field in required_fields:
            assert field in result_dict, f"API 響應應包含字段: {field}"

    @pytest.mark.asyncio
    async def test_backward_compatibility_intent_format(
        self, task_analyzer: TaskAnalyzer, sample_config_task: Dict[str, Any]
    ):
        """測試 Intent 格式向後兼容"""
        request = TaskAnalysisRequest(**sample_config_task)

        result = await task_analyzer.analyze(request)

        # 驗證 Intent 格式兼容
        intent = result.get_intent()

        if intent:
            # Intent 應該可以轉換為字典
            intent_dict = intent.model_dump() if hasattr(intent, "model_dump") else dict(intent)

            # 驗證 Intent 包含必要字段
            assert isinstance(intent_dict, dict), "Intent 應可轉換為字典"

    @pytest.mark.asyncio
    async def test_backward_compatibility_router_decision(
        self, task_analyzer: TaskAnalyzer, sample_task_request: Dict[str, Any]
    ):
        """測試 Router Decision 向後兼容"""
        request = TaskAnalysisRequest(**sample_task_request)

        result = await task_analyzer.analyze(request)

        # 驗證 Router Decision 格式兼容
        if result.router_decision:
            router_dict = result.router_decision.model_dump()

            # 驗證必要字段存在（v4 新增字段）
            v4_fields = ["topics", "entities", "action_signals", "modality"]

            for field in v4_fields:
                # 新字段可能不存在（向後兼容），但如果存在應該有正確的類型
                if field in router_dict:
                    assert router_dict[field] is not None, f"字段 {field} 不應為 None"

    @pytest.mark.asyncio
    async def test_existing_orchestrator_functionality(
        self, orchestrator: AgentOrchestrator
    ):
        """測試現有 Orchestrator 功能不受影響"""
        # 測試 Agent 發現
        agents = orchestrator.discover_agents()
        assert isinstance(agents, list), "Agent 列表應為 list"

        # 測試任務提交
        task_id = orchestrator.submit_task(
            task_type="test",
            task_data={"action": "test"},
        )
        assert task_id is not None, "任務 ID 不應為 None"

        # 測試任務狀態查詢
        task_status = orchestrator.get_task_status(task_id)
        assert task_status is not None, "任務狀態不應為 None"

    @pytest.mark.asyncio
    async def test_api_compatibility_request_format(
        self, task_analyzer: TaskAnalyzer
    ):
        """測試 API 請求格式兼容"""
        # 測試最小請求格式
        minimal_request = TaskAnalysisRequest(task="測試任務")
        result = await task_analyzer.analyze(minimal_request)
        assert result is not None, "最小請求應返回結果"

        # 測試完整請求格式
        full_request = TaskAnalysisRequest(
            task="測試任務",
            context={"user_id": "test_user", "tenant_id": "test_tenant"},
            user_id="test_user",
            session_id="test_session",
            specified_agent_id="test_agent",
        )
        result = await task_analyzer.analyze(full_request)
        assert result is not None, "完整請求應返回結果"

    @pytest.mark.asyncio
    async def test_api_compatibility_response_format(
        self, task_analyzer: TaskAnalyzer, sample_task_request: Dict[str, Any]
    ):
        """測試 API 響應格式兼容"""
        request = TaskAnalysisRequest(**sample_task_request)

        result = await task_analyzer.analyze(request)

        # 驗證響應可以序列化為 JSON
        result_dict = result.model_dump()

        # 驗證所有字段都可以序列化
        import json

        try:
            json_str = json.dumps(result_dict, default=str)
            assert len(json_str) > 0, "響應應可序列化為 JSON"
        except Exception as e:
            pytest.fail(f"響應序列化失敗: {e}")

    @pytest.mark.asyncio
    async def test_data_model_compatibility(
        self, task_analyzer: TaskAnalyzer, sample_task_request: Dict[str, Any]
    ):
        """測試數據模型兼容"""
        request = TaskAnalysisRequest(**sample_task_request)

        result = await task_analyzer.analyze(request)

        # 驗證數據模型類型
        assert isinstance(result.task_id, str), "task_id 應為 str"
        assert isinstance(result.task_type, (str, TaskType)), "task_type 應為 str 或 TaskType"
        assert isinstance(result.workflow_type, (str, WorkflowType)), "workflow_type 應為 str 或 WorkflowType"
        assert isinstance(result.confidence, float), "confidence 應為 float"
        assert isinstance(result.requires_agent, bool), "requires_agent 應為 bool"
        assert isinstance(result.suggested_agents, list), "suggested_agents 應為 list"
        assert isinstance(result.analysis_details, dict), "analysis_details 應為 dict"
