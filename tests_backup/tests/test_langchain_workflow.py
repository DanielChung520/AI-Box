# 代碼功能說明: LangChain/Graph Workflow 單元測試
# 創建日期: 2025-11-26 20:07 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 20:07 (UTC+8)

"""測試 LangChainWorkflowFactory 與 LangChainGraphWorkflow。"""

from __future__ import annotations

import asyncio

from agents.workflows import WorkflowRequestContext
from agents.workflows.langchain_graph_factory import LangChainWorkflowFactory
from agents.workflows.settings import (
    LangChainGraphSettings,
    LangGraphStateStoreSettings,
)


def _build_factory() -> LangChainWorkflowFactory:
    settings = LangChainGraphSettings(
        state_store=LangGraphStateStoreSettings(
            backend="memory",
            redis_url="redis://localhost:6379/5",
            namespace="ai-box:test",
            ttl_seconds=60,
        )
    )
    return LangChainWorkflowFactory(settings=settings)


def test_langchain_workflow_standard_route():
    factory = _build_factory()
    ctx = WorkflowRequestContext(
        task_id="test-standard",
        task="整理輸入並提供摘要",
        workflow_config={"complexity_score": 20},
    )
    workflow = factory.build_workflow(ctx)

    result = asyncio.run(workflow.run())

    assert result.status == "completed"
    assert len(result.output["plan"]) >= 1
    assert result.state_snapshot.get("route") == "standard"


def test_langchain_workflow_deep_dive_route():
    factory = _build_factory()
    ctx = WorkflowRequestContext(
        task_id="test-deep",
        task="進行多渠道競品深入分析並生成洞察",
        workflow_config={"complexity_score": 80},
    )
    workflow = factory.build_workflow(ctx)

    result = asyncio.run(workflow.run())

    assert result.status == "completed"
    assert result.state_snapshot.get("route") == "deep_dive"
    assert any("Research" in output for output in result.output["outputs"])
