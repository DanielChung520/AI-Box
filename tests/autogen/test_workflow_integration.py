# 代碼功能說明: AutoGen 工作流集成測試
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""測試 AutoGen 與 Task Analyzer、Context Recorder、Telemetry 的整合。"""

from agents.workflows.base import WorkflowRequestContext
from agents.task_analyzer.models import WorkflowType
from agents.task_analyzer.workflow_selector import WorkflowSelector
from agents.task_analyzer.analyzer import TaskAnalyzer


def test_task_analyzer_selects_autogen():
    """測試 Task Analyzer 選擇 AutoGen。"""
    analyzer = TaskAnalyzer()
    selector = WorkflowSelector()

    # 創建一個複雜度 60-80 的規劃任務
    task = "制定一個包含多個步驟的詳細執行計劃，需要動態調整和迭代優化"
    classification = analyzer.classify_task(task)

    # 選擇工作流
    selection = selector.select(classification, task)

    # 驗證選擇結果
    assert selection.workflow_type in [WorkflowType.AUTOGEN, WorkflowType.HYBRID]
    print(f"Task Analyzer 選擇: {selection.workflow_type.value}")


def test_workflow_factory_integration():
    """測試 Workflow Factory 整合。"""
    from agents.workflows.factory_router import get_workflow_factory_router
    from agents.task_analyzer.models import WorkflowType

    router = get_workflow_factory_router()
    factory = router.get_factory(WorkflowType.AUTOGEN)

    assert factory is not None

    # 構建 workflow
    ctx = WorkflowRequestContext(
        task_id="integration-test-001",
        task="集成測試任務",
    )
    workflow = factory.build_workflow(ctx)

    assert workflow is not None
    assert workflow._ctx.task_id == "integration-test-001"


def test_context_recorder_integration():
    """測試 Context Recorder 整合。"""
    from agents.autogen.conversation import ConversationManager
    from genai.workflows.context.recorder import ContextRecorder

    recorder = ContextRecorder()
    manager = ConversationManager(
        session_id="test-session-001",
        context_recorder=recorder,
    )

    # 記錄消息
    manager.record_message(
        agent_name="planner",
        role="assistant",
        content="測試消息",
    )

    # 驗證記錄
    history = recorder.get_history("test-session-001")
    assert len(history) > 0
    assert history[0].content == "測試消息"


def test_telemetry_integration():
    """測試 Telemetry 整合。"""
    from agents.autogen.workflow import AutoGenWorkflow
    from agents.autogen.config import load_autogen_settings

    settings = load_autogen_settings()
    ctx = WorkflowRequestContext(
        task_id="telemetry-test-001",
        task="Telemetry 測試任務",
    )

    workflow = AutoGenWorkflow(settings=settings, request_ctx=ctx)

    # 發送 telemetry 事件
    workflow._emit_telemetry("test.event", test_param="test_value")

    # 驗證事件
    assert len(workflow._telemetry_events) > 0
    assert workflow._telemetry_events[0].name == "test.event"
    assert workflow._telemetry_events[0].payload["test_param"] == "test_value"
