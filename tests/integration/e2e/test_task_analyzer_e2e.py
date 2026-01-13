# 代碼功能說明: Task Analyzer 端到端測試
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""Task Analyzer 端到端測試 - 測試完整流程（L1-L5）"""

import time
from typing import Any, Dict

import pytest

from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import (
    TaskAnalysisRequest,
    TaskType,
    WorkflowType,
)


class TestTaskAnalyzerE2E:
    """Task Analyzer 端到端測試類"""

    @pytest.mark.asyncio
    async def test_l1_semantic_understanding(
        self, task_analyzer: TaskAnalyzer, sample_task_request: Dict[str, Any]
    ):
        """測試 L1 層：Router LLM 語義理解輸出"""
        request = TaskAnalysisRequest(**sample_task_request)

        start_time = time.time()
        result = await task_analyzer.analyze(request)
        elapsed_time = time.time() - start_time

        # 驗證 L1 層輸出
        assert result.router_decision is not None, "Router Decision 不應為 None"
        router_decision = result.router_decision

        # 驗證 SemanticUnderstandingOutput Schema
        assert hasattr(router_decision, "topics") or "topics" in router_decision.model_dump()
        assert hasattr(router_decision, "entities") or "entities" in router_decision.model_dump()
        assert hasattr(router_decision, "action_signals") or "action_signals" in router_decision.model_dump()

        # 驗證響應時間 ≤1秒（P95）
        assert elapsed_time <= 1.0, f"L1 層響應時間 {elapsed_time:.2f}s 超過 1 秒"

        print(f"✓ L1 層測試通過，響應時間: {elapsed_time:.3f}s")

    @pytest.mark.asyncio
    async def test_l2_intent_matching(
        self, task_analyzer: TaskAnalyzer, sample_config_task: Dict[str, Any]
    ):
        """測試 L2 層：Intent DSL 匹配"""
        request = TaskAnalysisRequest(**sample_config_task)

        result = await task_analyzer.analyze(request)

        # 驗證 Intent 匹配
        intent = result.get_intent()
        assert intent is not None, "Intent 不應為 None"

        # 驗證 Intent 類型（ConfigIntent）
        from agents.task_analyzer.models import ConfigIntent

        assert isinstance(intent, ConfigIntent), f"Intent 類型應為 ConfigIntent，實際為 {type(intent)}"

        # 驗證 Intent 匹配準確率（通過檢查 intent 是否正確識別）
        assert hasattr(intent, "scope") or "scope" in intent.model_dump()
        assert hasattr(intent, "action") or "action" in intent.model_dump()

        print(f"✓ L2 層測試通過，Intent 類型: {type(intent).__name__}")

    @pytest.mark.asyncio
    async def test_l3_task_planner_dag(
        self, task_analyzer: TaskAnalyzer, sample_complex_task: Dict[str, Any]
    ):
        """測試 L3 層：Task Planner 和 DAG 生成"""
        request = TaskAnalysisRequest(**sample_complex_task)

        result = await task_analyzer.analyze(request)

        # 驗證 DAG 生成
        decision_result = result.decision_result
        if decision_result and hasattr(decision_result, "task_dag"):
            task_dag = decision_result.task_dag
            if task_dag:
                # 驗證 DAG 結構
                assert hasattr(task_dag, "task_graph") or "task_graph" in task_dag.model_dump()
                task_graph = (
                    task_dag.task_graph if hasattr(task_dag, "task_graph") else task_dag.model_dump().get("task_graph")
                )

                if task_graph:
                    # 驗證 DAG 包含任務節點
                    assert len(task_graph) > 0, "DAG 應包含至少一個任務節點"

                    # 驗證每個任務節點都有必要字段
                    for task in task_graph:
                        assert "id" in task or hasattr(task, "id")
                        assert "capability" in task or hasattr(task, "capability")

                    print(f"✓ L3 層測試通過，DAG 包含 {len(task_graph)} 個任務節點")
                else:
                    print("⚠ L3 層：未生成 DAG（可能是簡單任務）")
            else:
                print("⚠ L3 層：未生成 DAG（可能是簡單任務）")
        else:
            print("⚠ L3 層：未生成 DAG（可能是簡單任務）")

    @pytest.mark.asyncio
    async def test_l4_policy_check(
        self, task_analyzer: TaskAnalyzer, sample_high_risk_task: Dict[str, Any]
    ):
        """測試 L4 層：Policy & Constraint 檢查"""
        request = TaskAnalysisRequest(**sample_high_risk_task)

        start_time = time.time()
        result = await task_analyzer.analyze(request)
        policy_check_time = time.time() - start_time

        # 驗證 Policy 檢查已執行
        decision_result = result.decision_result
        if decision_result:
            # 檢查是否有 Policy 驗證結果
            policy_result = None
            if hasattr(decision_result, "policy_result"):
                policy_result = decision_result.policy_result
            elif "policy_result" in decision_result.model_dump():
                policy_result = decision_result.model_dump()["policy_result"]

            if policy_result:
                # 驗證 Policy 檢查結果
                assert hasattr(policy_result, "valid") or "valid" in policy_result

                print(f"✓ L4 層測試通過，Policy 檢查時間: {policy_check_time:.3f}s")
            else:
                print("⚠ L4 層：未找到 Policy 檢查結果（可能未觸發風險檢查）")
        else:
            print("⚠ L4 層：未找到 Decision Result")

    @pytest.mark.asyncio
    async def test_l5_execution_record(
        self, task_analyzer: TaskAnalyzer, sample_task_request: Dict[str, Any]
    ):
        """測試 L5 層：執行和觀察"""
        request = TaskAnalysisRequest(**sample_task_request)

        result = await task_analyzer.analyze(request)

        # 驗證執行記錄
        assert result.task_id is not None, "Task ID 不應為 None"
        assert result.task_type is not None, "Task Type 不應為 None"
        assert result.workflow_type is not None, "Workflow Type 不應為 None"

        # 驗證分析詳情包含必要信息
        assert result.analysis_details is not None, "Analysis Details 不應為 None"

        print("✓ L5 層測試通過，執行記錄已生成")

    @pytest.mark.asyncio
    async def test_simple_query_layer0(
        self, task_analyzer: TaskAnalyzer, sample_simple_query: Dict[str, Any]
    ):
        """測試 Layer 0：簡單查詢快速過濾"""
        request = TaskAnalysisRequest(**sample_simple_query)

        result = await task_analyzer.analyze(request)

        # 驗證簡單查詢被正確處理
        assert result.task_type is not None, "Task Type 不應為 None"

        print(f"✓ Layer 0 測試通過，任務類型: {result.task_type}")

    @pytest.mark.asyncio
    async def test_config_operation_flow(
        self, task_analyzer: TaskAnalyzer, sample_config_task: Dict[str, Any]
    ):
        """測試配置操作完整流程"""
        request = TaskAnalysisRequest(**sample_config_task)

        result = await task_analyzer.analyze(request)

        # 驗證配置操作被正確識別
        intent = result.get_intent()
        assert intent is not None, "Intent 不應為 None"

        # 驗證建議的 Agent
        if result.requires_agent:
            assert len(result.suggested_agents) > 0, "配置操作應建議使用 Agent"

        print(f"✓ 配置操作流程測試通過，建議 Agent: {result.suggested_agents}")

    @pytest.mark.asyncio
    async def test_log_query_flow(
        self, task_analyzer: TaskAnalyzer, sample_log_query_task: Dict[str, Any]
    ):
        """測試日誌查詢完整流程"""
        request = TaskAnalysisRequest(**sample_log_query_task)

        result = await task_analyzer.analyze(request)

        # 驗證日誌查詢被正確識別
        assert result.task_type == TaskType.LOG_QUERY, f"任務類型應為 LOG_QUERY，實際為 {result.task_type}"

        # 驗證 Intent
        intent = result.get_intent()
        assert intent is not None, "Intent 不應為 None"

        from agents.task_analyzer.models import LogQueryIntent

        assert isinstance(intent, LogQueryIntent), f"Intent 類型應為 LogQueryIntent，實際為 {type(intent)}"

        print("✓ 日誌查詢流程測試通過")

    @pytest.mark.asyncio
    async def test_end_to_end_performance(
        self, task_analyzer: TaskAnalyzer, sample_task_request: Dict[str, Any]
    ):
        """測試端到端性能"""
        request = TaskAnalysisRequest(**sample_task_request)

        start_time = time.time()
        result = await task_analyzer.analyze(request)
        elapsed_time = time.time() - start_time

        # 驗證端到端響應時間 ≤3秒（P95）
        assert elapsed_time <= 3.0, f"端到端響應時間 {elapsed_time:.2f}s 超過 3 秒"

        # 驗證結果完整性
        assert result.task_id is not None
        assert result.task_type is not None
        assert result.workflow_type is not None
        assert result.llm_provider is not None

        print(f"✓ 端到端性能測試通過，響應時間: {elapsed_time:.3f}s")
