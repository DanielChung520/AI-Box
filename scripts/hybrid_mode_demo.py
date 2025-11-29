#!/usr/bin/env python3
# 代碼功能說明: 混合模式演示腳本
# 創建日期: 2025-11-26 23:50 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 23:50 (UTC+8)

"""展示混合模式工作流的實際使用範例。"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from agents.task_analyzer.analyzer import TaskAnalyzer  # noqa: E402
from agents.task_analyzer.models import TaskAnalysisRequest  # noqa: E402
from agents.workflows.base import WorkflowRequestContext  # noqa: E402
from agents.workflows.factory_router import get_workflow_factory_router  # noqa: E402
from agents.task_analyzer.models import WorkflowType  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def demo_hybrid_mode():
    """演示混合模式工作流。"""

    print("=" * 80)
    print("混合模式工作流演示")
    print("=" * 80)
    print()

    # 步驟 1: 任務分析
    print("步驟 1: 任務分析")
    print("-" * 80)

    analyzer = TaskAnalyzer()

    # 創建一個高複雜度任務
    request = TaskAnalysisRequest(
        task=(
            "這是一個複雜的多步驟任務："
            "1. 分析市場趨勢並生成報告"
            "2. 根據分析結果制定長期戰略規劃"
            "3. 執行戰略並監控執行狀態"
            "4. 根據執行結果調整策略"
        ),
        context={
            "complexity_score": 80,
            "step_count": 15,
            "requires_observability": True,
            "requires_long_horizon": True,
        },
    )

    analysis_result = analyzer.analyze(request)

    print(f"任務 ID: {analysis_result.task_id}")
    print(f"任務類型: {analysis_result.task_type.value}")
    print(f"工作流類型: {analysis_result.workflow_type.value}")
    print(f"置信度: {analysis_result.confidence:.2f}")
    print()

    # 檢查是否為混合模式
    if analysis_result.workflow_type == WorkflowType.HYBRID:
        print("✓ 檢測到混合模式策略")
        if "workflow_strategy" in analysis_result.analysis_details:
            strategy = analysis_result.analysis_details["workflow_strategy"]
            print(f"  模式: {strategy['mode']}")
            print(f"  主要工作流: {strategy['primary']}")
            print(f"  備用工作流: {strategy['fallback']}")
            print(f"  決策理由: {strategy['reasoning']}")
            print()
            print("  切換條件:")
            for key, value in strategy["switch_conditions"].items():
                print(f"    - {key}: {value}")
    else:
        print("⚠ 未使用混合模式")
        print(f"  選擇的工作流: {analysis_result.workflow_type.value}")

    print()
    print("=" * 80)
    print()

    # 步驟 2: 工作流構建
    print("步驟 2: 工作流構建")
    print("-" * 80)

    router = get_workflow_factory_router()
    factory = router.get_factory(WorkflowType.HYBRID)

    if factory:
        print("✓ 混合模式工廠已註冊")

        # 構建工作流
        workflow_config = analysis_result.analysis_details.get("workflow", {}).get(
            "config", {}
        )

        request_ctx = WorkflowRequestContext(
            task_id=analysis_result.task_id,
            task=request.task,
            context=request.context,
            workflow_config=workflow_config,
        )

        workflow = router.build_workflow(WorkflowType.HYBRID, request_ctx)

        if workflow:
            print("✓ 混合模式工作流構建成功")
            print(f"  主要模式: {workflow._primary_mode}")
            print(f"  備用模式: {workflow._fallback_modes}")
        else:
            print("⚠ 工作流構建失敗")
    else:
        print("⚠ 混合模式工廠未找到")

    print()
    print("=" * 80)
    print()

    # 步驟 3: 狀態同步演示
    print("步驟 3: 狀態同步演示")
    print("-" * 80)

    from agents.workflows.hybrid_orchestrator import (
        HybridState,
        PlanningSync,
        StateSync,
    )
    from agents.autogen.planner import ExecutionPlan, PlanStep, PlanStatus

    # 創建一個 AutoGen 計畫
    plan_steps = [
        PlanStep(
            step_id="step_1",
            description="收集市場數據",
            dependencies=[],
            status="completed",
            result="數據收集完成",
        ),
        PlanStep(
            step_id="step_2",
            description="分析市場趨勢",
            dependencies=["step_1"],
            status="executing",
        ),
        PlanStep(
            step_id="step_3",
            description="生成報告",
            dependencies=["step_2"],
            status="pending",
        ),
    ]

    autogen_plan = ExecutionPlan(
        plan_id="plan-demo-1",
        task="演示任務",
        steps=plan_steps,
        status=PlanStatus.EXECUTING,
    )

    # 測試 PlanningSync
    planning_sync = PlanningSync()
    langgraph_state = planning_sync.autogen_to_langgraph(autogen_plan)

    print("✓ AutoGen 計畫 → LangGraph 狀態轉換成功")
    print(f"  計畫步驟數: {len(autogen_plan.steps)}")
    print(f"  LangGraph plan 長度: {len(langgraph_state.get('plan', []))}")
    print(f"  當前步驟: {langgraph_state.get('current_step', 0)}")
    print(f"  輸出數量: {len(langgraph_state.get('outputs', []))}")

    # 測試 StateSync
    state_sync = StateSync()
    autogen_context = state_sync.langgraph_to_autogen(langgraph_state)

    print("✓ LangGraph 狀態 → AutoGen 上下文轉換成功")
    print(f"  執行結果數量: {len(autogen_context.get('execution_results', []))}")
    print(f"  計畫上下文數量: {len(autogen_context.get('plan_context', []))}")

    print()
    print("=" * 80)
    print()

    # 步驟 4: 切換控制器演示
    print("步驟 4: 切換控制器演示")
    print("-" * 80)

    from agents.workflows.hybrid_orchestrator import SwitchController

    controller = SwitchController(cooldown_seconds=60, max_switches=5)

    hybrid_state: HybridState = {
        "task_id": "demo-task-1",
        "task": "演示任務",
        "context": {"fallback_modes": ["langgraph"]},
        "current_mode": "autogen",
        "autogen_plan": {},
        "langgraph_state": {},
        "switch_history": [],
        "sync_checkpoint": {},
        "created_at": "2025-11-26T23:50:00",
        "updated_at": "2025-11-26T23:50:00",
    }

    # 測試高錯誤率觸發切換
    metrics_high_error = {
        "error_rate": 0.5,
        "latency": 0.0,
        "cost": 0.0,
        "cost_threshold": 100.0,
    }

    target_mode = controller.should_switch("autogen", hybrid_state, metrics_high_error)
    if target_mode:
        print(f"✓ 高錯誤率觸發切換: autogen → {target_mode}")
    else:
        print("⚠ 未觸發切換")

    # 測試成本超標觸發切換
    metrics_high_cost = {
        "error_rate": 0.0,
        "latency": 0.0,
        "cost": 150.0,
        "cost_threshold": 100.0,
    }

    target_mode = controller.should_switch("autogen", hybrid_state, metrics_high_cost)
    if target_mode:
        print(f"✓ 成本超標觸發切換: autogen → {target_mode}")
    else:
        print("⚠ 未觸發切換")

    print()
    print("=" * 80)
    print()

    print("演示完成！")
    print()
    print("總結:")
    print("  - 混合模式可以根據任務複雜度自動選擇")
    print("  - 支援 AutoGen 和 LangGraph 之間的狀態同步")
    print("  - 支援執行中動態切換模式")
    print("  - 提供完整的可觀測性和錯誤處理")


if __name__ == "__main__":
    asyncio.run(demo_hybrid_mode())
