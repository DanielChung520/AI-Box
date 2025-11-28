# 代碼功能說明: AutoGen Long-horizon 任務處理
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""實現狀態持久化、長程記憶整合、失敗恢復機制和資源控制。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_process.memory.manager import MemoryManager
from agents.autogen.planner import ExecutionPlan, PlanStatus
from agents.autogen.state_mapper import StateMapper

logger = logging.getLogger(__name__)


class LongHorizonTaskManager:
    """長時程任務管理器。"""

    def __init__(
        self,
        checkpoint_dir: str = "./datasets/autogen/checkpoints",
        memory_manager: Optional[MemoryManager] = None,
    ):
        """
        初始化長時程任務管理器。

        Args:
            checkpoint_dir: Checkpoint 保存目錄
            memory_manager: Memory Manager 實例（可選）
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.memory_manager = memory_manager
        self.state_mapper = StateMapper()

    def save_checkpoint(
        self,
        plan: ExecutionPlan,
        additional_state: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        保存檢查點。

        Args:
            plan: 執行計劃
            additional_state: 額外的狀態信息

        Returns:
            是否成功保存
        """
        try:
            checkpoint = self.state_mapper.create_state_checkpoint(
                plan, additional_state
            )

            checkpoint_file = self.checkpoint_dir / f"{plan.plan_id}.json"
            with checkpoint_file.open("w", encoding="utf-8") as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved checkpoint for plan {plan.plan_id}")
            return True
        except Exception as exc:
            logger.error(f"Failed to save checkpoint: {exc}")
            return False

    def load_checkpoint(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        載入檢查點。

        Args:
            plan_id: 計劃 ID

        Returns:
            檢查點字典，如果不存在則返回 None
        """
        try:
            checkpoint_file = self.checkpoint_dir / f"{plan_id}.json"
            if not checkpoint_file.exists():
                logger.warning(f"Checkpoint not found for plan {plan_id}")
                return None

            with checkpoint_file.open("r", encoding="utf-8") as f:
                checkpoint = json.load(f)

            logger.info(f"Loaded checkpoint for plan {plan_id}")
            return checkpoint
        except Exception as exc:
            logger.error(f"Failed to load checkpoint: {exc}")
            return None

    def restore_plan_from_checkpoint(
        self,
        plan_id: str,
    ) -> Optional[ExecutionPlan]:
        """
        從檢查點恢復計劃。

        Args:
            plan_id: 計劃 ID

        Returns:
            恢復的執行計劃，如果失敗則返回 None
        """
        checkpoint = self.load_checkpoint(plan_id)
        if not checkpoint:
            return None

        try:
            from agents.autogen.planner import PlanStep

            # 重建步驟
            steps = []
            for step_data in checkpoint.get("steps", []):
                step = PlanStep(
                    step_id=step_data["step_id"],
                    description=step_data["description"],
                    status=step_data.get("status", "pending"),
                    result=step_data.get("result"),
                    error=step_data.get("error"),
                    retry_count=step_data.get("retry_count", 0),
                    metadata=step_data.get("metadata", {}),
                )
                steps.append(step)

            # 重建計劃
            plan = ExecutionPlan(
                plan_id=checkpoint["plan_id"],
                task=checkpoint["task"],
                steps=steps,
                status=PlanStatus(checkpoint.get("status", "draft")),
                metadata=checkpoint.get("metadata", {}),
            )

            logger.info(f"Restored plan {plan_id} from checkpoint")
            return plan
        except Exception as exc:
            logger.error(f"Failed to restore plan from checkpoint: {exc}")
            return None

    def store_long_term_memory(
        self,
        plan: ExecutionPlan,
        key_points: List[Dict[str, Any]],
    ) -> bool:
        """
        存儲長期記憶。

        Args:
            plan: 執行計劃
            key_points: 關鍵決策點和結果

        Returns:
            是否成功存儲
        """
        if not self.memory_manager:
            logger.warning("Memory manager not available, skipping long-term storage")
            return False

        try:
            # 存儲計劃摘要
            plan_summary = self.state_mapper.extract_plan_summary(plan)
            value_content = json.dumps(
                {
                    "summary": plan_summary,
                    "key_points": key_points,
                }
            )
            self.memory_manager.store_long_term(
                content=value_content,
                metadata={"key": f"plan:{plan.plan_id}", "type": "plan_summary"},
            )

            # 存儲關鍵決策點
            for idx, point in enumerate(key_points):
                point_content = (
                    json.dumps(point) if isinstance(point, dict) else str(point)
                )
                self.memory_manager.store_long_term(
                    content=point_content,
                    metadata={
                        "key": f"plan:{plan.plan_id}:point:{idx}",
                        "type": "key_point",
                    },
                )

            logger.info(f"Stored long-term memory for plan {plan.plan_id}")
            return True
        except Exception as exc:
            logger.error(f"Failed to store long-term memory: {exc}")
            return False

    def retrieve_relevant_memory(
        self,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        檢索相關記憶。

        Args:
            query: 查詢字符串
            limit: 返回數量限制

        Returns:
            相關記憶列表
        """
        if not self.memory_manager:
            return []

        try:
            # 這裡簡化處理，實際應該使用向量搜索
            # 暫時返回空列表
            return []
        except Exception as exc:
            logger.error(f"Failed to retrieve memory: {exc}")
            return []

    def handle_failure(
        self,
        plan: ExecutionPlan,
        failed_step_id: str,
        error: str,
        max_retries: int = 3,
    ) -> bool:
        """
        處理失敗步驟。

        Args:
            plan: 執行計劃
            failed_step_id: 失敗的步驟 ID
            error: 錯誤信息
            max_retries: 最大重試次數

        Returns:
            是否應該重試
        """
        # 找到失敗的步驟
        failed_step = None
        for step in plan.steps:
            if step.step_id == failed_step_id:
                failed_step = step
                break

        if not failed_step:
            logger.warning(f"Failed step {failed_step_id} not found in plan")
            return False

        # 更新步驟狀態
        failed_step.status = "failed"
        failed_step.error = error
        failed_step.retry_count += 1

        # 檢查是否應該重試
        if failed_step.retry_count <= max_retries:
            failed_step.status = "pending"
            logger.info(
                f"Step {failed_step_id} will be retried "
                f"({failed_step.retry_count}/{max_retries})"
            )
            return True
        else:
            logger.warning(
                f"Step {failed_step_id} exceeded max retries, marking as skipped"
            )
            failed_step.status = "skipped"
            return False

    def check_resource_limits(
        self,
        plan: ExecutionPlan,
        budget_tokens: int,
        max_rounds: int,
    ) -> tuple[bool, str]:
        """
        檢查資源限制。

        Args:
            plan: 執行計劃
            budget_tokens: Token 預算上限
            max_rounds: 最大迭代輪數

        Returns:
            (是否在限制內, 消息)
        """
        # 檢查 token 預算
        if plan.total_estimated_tokens > budget_tokens:
            return False, f"超出 Token 預算: {plan.total_estimated_tokens}/{budget_tokens}"

        # 檢查迭代輪數（這裡簡化處理，實際應該追蹤實際執行輪數）
        # 假設每個步驟算一輪
        if len(plan.steps) > max_rounds:
            return False, f"步驟數超過最大輪數: {len(plan.steps)}/{max_rounds}"

        return True, "資源限制檢查通過"

    def pause_task(self, plan: ExecutionPlan) -> bool:
        """
        暫停任務。

        Args:
            plan: 執行計劃

        Returns:
            是否成功暫停
        """
        try:
            plan.status = PlanStatus.EXECUTING  # 標記為執行中但暫停
            self.save_checkpoint(plan, {"paused": True})
            logger.info(f"Paused task for plan {plan.plan_id}")
            return True
        except Exception as exc:
            logger.error(f"Failed to pause task: {exc}")
            return False

    def resume_task(self, plan_id: str) -> Optional[ExecutionPlan]:
        """
        恢復任務。

        Args:
            plan_id: 計劃 ID

        Returns:
            恢復的執行計劃，如果失敗則返回 None
        """
        plan = self.restore_plan_from_checkpoint(plan_id)
        if plan:
            logger.info(f"Resumed task for plan {plan_id}")
        return plan
