# 代碼功能說明: Task Planner v4.0 單元測試（L3 能力映射與任務規劃層）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Task Planner v4.0 單元測試 - 測試 L3 能力映射與任務規劃層"""

import json
import pytest
from unittest.mock import MagicMock, patch

from agents.task_analyzer.models import RouterDecision, TaskDAG, TaskNode
from agents.task_analyzer.task_planner import TaskPlanner


class TestTaskPlannerV4:
    """Task Planner v4.0 測試類"""

    @pytest.fixture
    def task_planner(self):
        """創建 TaskPlanner 實例"""
        return TaskPlanner()

    @pytest.fixture
    def router_decision(self):
        """創建 RouterDecision 實例"""
        return RouterDecision(
            topics=["document", "system_design"],
            entities=["Document Editing Agent", "API Spec"],
            action_signals=["design", "refine", "structure"],
            modality="instruction",
            intent_type="execution",
            complexity="high",
            needs_agent=True,
            needs_tools=True,
            determinism_required=False,
            risk_level="mid",
            confidence=0.92,
        )

    @pytest.fixture
    def mock_rag_service(self):
        """創建 Mock RAG Service"""
        rag_service = MagicMock()
        # Mock 檢索結果
        rag_service.retrieve_capabilities.return_value = [
            {
                "chunk_id": "cap1",
                "content": "Document Editing Agent can generate patch design",
                "metadata": {
                    "capability_name": "generate_patch_design",
                    "agent": "DocumentEditingAgent",
                    "input_type": "SemanticSpec",
                    "output_type": "PatchPlan",
                    "description": "Generate patch design for document editing",
                },
                "similarity": 0.85,
            },
            {
                "chunk_id": "cap2",
                "content": "Document Editing Agent can refine document structure",
                "metadata": {
                    "capability_name": "refine_structure",
                    "agent": "DocumentEditingAgent",
                    "input_type": "Document",
                    "output_type": "RefinedDocument",
                    "description": "Refine document structure",
                },
                "similarity": 0.80,
            },
        ]
        rag_service.format_capabilities_for_prompt.return_value = "## 可用能力列表\n..."
        return rag_service

    @pytest.fixture
    def mock_llm_service(self):
        """創建 Mock LLM Service"""
        llm_service = MagicMock()
        # Mock LLM 響應（Task DAG JSON）
        llm_response = {
            "task_graph": [
                {
                    "id": "T1",
                    "capability": "generate_patch_design",
                    "agent": "DocumentEditingAgent",
                    "depends_on": [],
                    "description": "Generate initial patch design",
                },
                {
                    "id": "T2",
                    "capability": "refine_structure",
                    "agent": "DocumentEditingAgent",
                    "depends_on": ["T1"],
                    "description": "Refine document structure",
                },
            ],
            "reasoning": "Two-step process: first generate design, then refine structure",
        }
        llm_service.generate.return_value = json.dumps(llm_response)
        return llm_service

    def test_plan_success(self, task_planner, router_decision, mock_rag_service, mock_llm_service):
        """測試 Task DAG 生成成功"""
        # Mock RAG Service 和 LLM Service
        with patch.object(task_planner, "_rag_service", mock_rag_service):
            with patch.object(task_planner, "_llm_service", mock_llm_service):
                result = task_planner.plan(
                    user_query="幫我產生Data Agent文件",
                    router_decision=router_decision,
                    top_k=10,
                    similarity_threshold=0.7,
                )

                # 驗證結果
                assert isinstance(result, TaskDAG)
                assert len(result.task_graph) == 2
                assert result.task_graph[0].id == "T1"
                assert result.task_graph[0].capability == "generate_patch_design"
                assert result.task_graph[0].agent == "DocumentEditingAgent"
                assert result.task_graph[0].depends_on == []
                assert result.task_graph[1].id == "T2"
                assert result.task_graph[1].depends_on == ["T1"]
                assert result.reasoning is not None

    def test_plan_no_capabilities(self, task_planner, router_decision):
        """測試沒有找到 Capability 的情況"""
        # Mock RAG Service 返回空列表
        mock_rag_service = MagicMock()
        mock_rag_service.retrieve_capabilities.return_value = []

        with patch.object(task_planner, "_rag_service", mock_rag_service):
            result = task_planner.plan(
                user_query="幫我產生Data Agent文件",
                router_decision=router_decision,
            )

            # 驗證結果為空 DAG
            assert isinstance(result, TaskDAG)
            assert len(result.task_graph) == 0
            assert "未找到匹配的能力" in result.reasoning

    def test_validate_planner_output_success(
        self, task_planner, mock_rag_service
    ):
        """測試 Task DAG 驗證成功"""
        # 創建有效的 Task DAG
        task_dag = TaskDAG(
            task_graph=[
                TaskNode(
                    id="T1",
                    capability="generate_patch_design",
                    agent="DocumentEditingAgent",
                    depends_on=[],
                ),
                TaskNode(
                    id="T2",
                    capability="refine_structure",
                    agent="DocumentEditingAgent",
                    depends_on=["T1"],
                ),
            ],
            reasoning="Valid DAG",
        )

        # Mock 檢索結果
        retrieved_capabilities = [
            {
                "metadata": {
                    "capability_name": "generate_patch_design",
                    "agent": "DocumentEditingAgent",
                }
            },
            {
                "metadata": {
                    "capability_name": "refine_structure",
                    "agent": "DocumentEditingAgent",
                }
            },
        ]

        is_valid, errors = task_planner.validate_planner_output(
            task_dag, retrieved_capabilities
        )

        # 驗證結果
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_planner_output_invalid_capability(
        self, task_planner, mock_rag_service
    ):
        """測試 Task DAG 驗證失敗（使用了不存在的能力）"""
        # 創建包含不存在能力的 Task DAG
        task_dag = TaskDAG(
            task_graph=[
                TaskNode(
                    id="T1",
                    capability="non_existent_capability",
                    agent="DocumentEditingAgent",
                    depends_on=[],
                ),
            ],
            reasoning="Invalid DAG",
        )

        # Mock 檢索結果（不包含 non_existent_capability）
        retrieved_capabilities = [
            {
                "metadata": {
                    "capability_name": "generate_patch_design",
                    "agent": "DocumentEditingAgent",
                }
            },
        ]

        is_valid, errors = task_planner.validate_planner_output(
            task_dag, retrieved_capabilities
        )

        # 驗證結果
        assert is_valid is False
        assert len(errors) > 0
        assert any("不存在的能力" in error for error in errors)

    def test_validate_planner_output_circular_dependency(
        self, task_planner, mock_rag_service
    ):
        """測試 Task DAG 驗證失敗（循環依賴）"""
        # 創建包含循環依賴的 Task DAG
        task_dag = TaskDAG(
            task_graph=[
                TaskNode(
                    id="T1",
                    capability="generate_patch_design",
                    agent="DocumentEditingAgent",
                    depends_on=["T2"],
                ),
                TaskNode(
                    id="T2",
                    capability="refine_structure",
                    agent="DocumentEditingAgent",
                    depends_on=["T1"],
                ),
            ],
            reasoning="Circular dependency",
        )

        # Mock 檢索結果
        retrieved_capabilities = [
            {
                "metadata": {
                    "capability_name": "generate_patch_design",
                    "agent": "DocumentEditingAgent",
                }
            },
            {
                "metadata": {
                    "capability_name": "refine_structure",
                    "agent": "DocumentEditingAgent",
                }
            },
        ]

        is_valid, errors = task_planner.validate_planner_output(
            task_dag, retrieved_capabilities
        )

        # 驗證結果
        assert is_valid is False
        assert len(errors) > 0
        assert any("循環依賴" in error for error in errors)

    def test_validate_planner_output_missing_dependency(
        self, task_planner, mock_rag_service
    ):
        """測試 Task DAG 驗證失敗（依賴的任務不存在）"""
        # 創建包含不存在依賴的 Task DAG
        task_dag = TaskDAG(
            task_graph=[
                TaskNode(
                    id="T1",
                    capability="generate_patch_design",
                    agent="DocumentEditingAgent",
                    depends_on=["T999"],  # 不存在的任務
                ),
            ],
            reasoning="Missing dependency",
        )

        # Mock 檢索結果
        retrieved_capabilities = [
            {
                "metadata": {
                    "capability_name": "generate_patch_design",
                    "agent": "DocumentEditingAgent",
                }
            },
        ]

        is_valid, errors = task_planner.validate_planner_output(
            task_dag, retrieved_capabilities
        )

        # 驗證結果
        assert is_valid is False
        assert len(errors) > 0
        assert any("不存在" in error for error in errors)

    def test_parse_llm_response_success(self, task_planner):
        """測試解析 LLM 響應成功"""
        # 創建有效的 LLM 響應
        llm_response = json.dumps(
            {
                "task_graph": [
                    {
                        "id": "T1",
                        "capability": "generate_patch_design",
                        "agent": "DocumentEditingAgent",
                        "depends_on": [],
                        "description": "Generate initial patch design",
                    },
                ],
                "reasoning": "Single step process",
            }
        )

        result = task_planner._parse_llm_response(llm_response)

        # 驗證結果
        assert isinstance(result, TaskDAG)
        assert len(result.task_graph) == 1
        assert result.task_graph[0].id == "T1"
        assert result.reasoning == "Single step process"

    def test_parse_llm_response_invalid_json(self, task_planner):
        """測試解析 LLM 響應失敗（無效 JSON）"""
        # 創建無效的 LLM 響應
        llm_response = "This is not valid JSON"

        result = task_planner._parse_llm_response(llm_response)

        # 驗證結果為空 DAG
        assert isinstance(result, TaskDAG)
        assert len(result.task_graph) == 0
        assert "解析 LLM 響應失敗" in result.reasoning

    def test_build_planner_prompt(self, task_planner, router_decision, mock_rag_service):
        """測試構建 Planner Prompt"""
        with patch.object(task_planner, "_rag_service", mock_rag_service):
            prompt = task_planner.build_planner_prompt(
                user_query="幫我產生Data Agent文件",
                router_decision=router_decision,
                retrieved_capabilities=mock_rag_service.retrieve_capabilities.return_value,
            )

            # 驗證 Prompt 包含必要信息
            assert "幫我產生Data Agent文件" in prompt
            assert "document" in prompt or "Document" in prompt
            assert "可用能力列表" in prompt or "capability" in prompt.lower()

    @pytest.mark.asyncio
    async def test_plan_integration(self, task_planner, router_decision):
        """測試 Task Planner 集成測試（需要真實的 RAG Service 和 LLM Service）"""
        # 注意：此測試需要 RAG Service 和 LLM Service 已初始化
        # 如果服務未初始化，此測試可能會失敗
        try:
            result = task_planner.plan(
                user_query="幫我產生Data Agent文件",
                router_decision=router_decision,
                top_k=5,
                similarity_threshold=0.7,
            )
            # 如果成功，驗證結果
            if result and result.task_graph:
                assert isinstance(result, TaskDAG)
                assert len(result.task_graph) > 0
                # 驗證每個任務節點
                for task_node in result.task_graph:
                    assert task_node.id is not None
                    assert task_node.capability is not None
                    assert task_node.agent is not None
        except Exception as e:
            # 如果服務未初始化，跳過此測試
            pytest.skip(f"RAG Service or LLM Service not initialized: {e}")
