# 代碼功能說明: LangChain/Graph Workflow 可觀測性工具
# 創建日期: 2025-11-26 20:07 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 20:07 (UTC+8)

"""提供 workflow telemetry 蒐集與輸出輔助。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

from agents.workflows.base import WorkflowTelemetryEvent

logger = logging.getLogger(__name__)


@dataclass
class WorkflowTelemetryCollector:
    """簡易的工作流觀測資料收集器。"""

    enabled_metrics: bool = True
    enabled_traces: bool = True
    enabled_logs: bool = True
    _events: List[WorkflowTelemetryEvent] = field(default_factory=list)

    def emit(self, name: str, **payload: Any) -> WorkflowTelemetryEvent:
        """新增一筆觀測事件並視設定輸出。"""

        event = WorkflowTelemetryEvent(name=name, payload=payload)
        self._events.append(event)

        if self.enabled_logs:
            logger.info("[workflow.telemetry] %s | %s", name, payload)

        return event

    def export(self) -> List[WorkflowTelemetryEvent]:
        """取得所有事件（用於結果返回或 Prometheus/Tracing）。"""

        return list(self._events)

    def as_metrics_payload(self) -> List[Dict[str, Any]]:
        """轉換為可直接給 metrics pipeline 的格式。"""

        if not self.enabled_metrics:
            return []
        payloads: List[Dict[str, Any]] = []
        for event in self._events:
            payload = {"name": event.name}
            payload.update(event.payload)
            payloads.append(payload)
        return payloads
