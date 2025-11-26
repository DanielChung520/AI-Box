# 代碼功能說明: Workflow Telemetry Publisher
# 創建日期: 2025-11-26 20:07 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 20:07 (UTC+8)

"""提供 workflow 相關 Prometheus 指標與日志輸出。"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Optional

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

WORKFLOW_EXECUTIONS = Counter(
    "workflow_executions_total",
    "Workflow 執行次數",
    ["workflow", "status", "route"],
)

WORKFLOW_STEPS = Histogram(
    "workflow_plan_steps",
    "Workflow 規劃步驟數分佈",
    buckets=(1, 2, 3, 4, 5, 7, 10, 15, 20, 30),
)


def publish_workflow_metrics(
    *,
    workflow: str,
    status: str,
    steps: int,
    route: str,
    events: Optional[Iterable[Any]] = None,
) -> None:
    """將 workflow 運行結果輸出到 Prometheus 與結構化日誌。"""

    WORKFLOW_EXECUTIONS.labels(workflow=workflow, status=status, route=route).inc()
    WORKFLOW_STEPS.observe(steps or 0)

    logger.info(
        "workflow.metrics",
        extra={
            "workflow": workflow,
            "status": status,
            "route": route,
            "steps": steps,
            "events": len(list(events)) if events else 0,
        },
    )
