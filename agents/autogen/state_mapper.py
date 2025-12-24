# 代碼功能說明: AutoGen 狀態映射器（為混合模式準備）
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""將 AutoGen 計畫節點轉換為 LangGraph 狀態格式，支援混合模式。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from agents.autogen.planner import ExecutionPlan

logger = logging.getLogger(__name__)


class StateMapper:
    """狀態映射器，用於 AutoGen 和 LangGraph 之間的狀態轉換。"""

    def plan_to_langgraph_state(
        self,
        plan: ExecutionPlan,
    ) -> Dict[str, Any]:
        """
        將 AutoGen 計劃轉換為 LangGraph 狀態格式。

        Args:
            plan: 執行計劃

        Returns:
            LangGraph 狀態字典
        """
        # 構建節點映射
        nodes = {}
        edges = []

        for step in plan.steps:
            # 將步驟轉換為節點
            node_id = f"step_{step.step_id}"
            nodes[node_id] = {
                "type": "execution",
                "step_id": step.step_id,
                "description": step.description,
                "status": step.status,
                "metadata": step.metadata,
            }

            # 構建依賴邊
            for dep in step.dependencies:
                dep_node_id = f"step_{dep}"
                if dep_node_id in nodes:
                    edges.append(
                        {
                            "from": dep_node_id,
                            "to": node_id,
                            "type": "dependency",
                        }
                    )

        # 構建狀態結構
        state = {
            "task": plan.task,
            "plan_id": plan.plan_id,
            "status": plan.status.value,
            "nodes": nodes,
            "edges": edges,
            "current_step": None,
            "completed_steps": [step.step_id for step in plan.steps if step.status == "completed"],
            "failed_steps": [step.step_id for step in plan.steps if step.status == "failed"],
            "metadata": plan.metadata,
        }

        logger.debug(f"Mapped plan {plan.plan_id} to LangGraph state")
        return state

    def langgraph_state_to_partial_plan(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        將 LangGraph 狀態轉換為 AutoGen 可用的部分計劃。

        Args:
            state: LangGraph 狀態字典

        Returns:
            部分計劃字典
        """
        partial_plan = {
            "task": state.get("task", ""),
            "current_step": state.get("current_step"),
            "completed_steps": state.get("completed_steps", []),
            "failed_steps": state.get("failed_steps", []),
            "nodes": state.get("nodes", {}),
            "edges": state.get("edges", []),
        }

        logger.debug("Converted LangGraph state to partial plan")
        return partial_plan

    def extract_plan_summary(
        self,
        plan: ExecutionPlan,
    ) -> Dict[str, Any]:
        """
        提取計劃摘要（供 CrewAI 或其他系統參照）。

        Args:
            plan: 執行計劃

        Returns:
            計劃摘要字典
        """
        summary = {
            "plan_id": plan.plan_id,
            "task": plan.task,
            "total_steps": len(plan.steps),
            "completed_steps": len([s for s in plan.steps if s.status == "completed"]),
            "failed_steps": len([s for s in plan.steps if s.status == "failed"]),
            "status": plan.status.value,
            "feasibility_score": plan.feasibility_score,
            "estimated_tokens": plan.total_estimated_tokens,
            "estimated_duration": plan.total_estimated_duration,
            "step_summaries": [
                {
                    "step_id": step.step_id,
                    "description": step.description,
                    "status": step.status,
                    "dependencies": step.dependencies,
                }
                for step in plan.steps
            ],
        }

        return summary

    def create_state_checkpoint(
        self,
        plan: ExecutionPlan,
        additional_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        創建狀態檢查點（用於持久化和恢復）。

        Args:
            plan: 執行計劃
            additional_state: 額外的狀態信息

        Returns:
            檢查點字典
        """
        checkpoint = {
            "plan_id": plan.plan_id,
            "task": plan.task,
            "status": plan.status.value,
            "steps": [
                {
                    "step_id": step.step_id,
                    "description": step.description,
                    "status": step.status,
                    "result": step.result,
                    "error": step.error,
                    "retry_count": step.retry_count,
                    "metadata": step.metadata,
                }
                for step in plan.steps
            ],
            "metadata": plan.metadata,
        }

        if additional_state:
            checkpoint["additional_state"] = additional_state

        logger.debug(f"Created checkpoint for plan {plan.plan_id}")
        return checkpoint
