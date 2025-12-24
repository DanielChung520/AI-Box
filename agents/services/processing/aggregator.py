# 代碼功能說明: Result Aggregator 結果聚合器
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Result Aggregator - 收集和聚合多個 Agent 的執行結果"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResultAggregator:
    """結果聚合器 - 收集 Agent 產出並格式化輸出"""

    def __init__(self):
        """初始化結果聚合器"""
        self._logger = logger

    def aggregate_results(
        self,
        task_results: List[Dict[str, Any]],
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        聚合多個 Agent 的執行結果

        Args:
            task_results: Agent 執行結果列表
                [
                    {
                        "agent_id": "agent-1",
                        "status": "completed",
                        "result": {...},
                        "output_files": [...],  # 產出物文件 URL 列表
                        "metadata": {...}
                    },
                    ...
                ]
            task_id: 任務 ID（可選）

        Returns:
            聚合結果字典
        """
        try:
            aggregated: Dict[str, Any] = {
                "task_id": task_id,
                "aggregated_at": datetime.now().isoformat(),
                "total_agents": len(task_results),
                "successful_agents": 0,
                "failed_agents": 0,
                "results": [],
                "output_files": [],
                "summary": {},
            }

            # 聚合每個 Agent 的結果
            for result in task_results:
                agent_id = result.get("agent_id", "unknown")
                status = result.get("status", "unknown")

                if status == "completed":
                    aggregated["successful_agents"] += 1
                    aggregated["results"].append(
                        {
                            "agent_id": agent_id,
                            "status": status,
                            "result": result.get("result"),
                            "metadata": result.get("metadata", {}),
                        }
                    )

                    # 收集產出物文件 URL
                    output_files = result.get("output_files", [])
                    if output_files:
                        aggregated["output_files"].extend(output_files)
                else:
                    aggregated["failed_agents"] += 1
                    aggregated["results"].append(
                        {
                            "agent_id": agent_id,
                            "status": status,
                            "error": result.get("error"),
                            "metadata": result.get("metadata", {}),
                        }
                    )

            # 生成摘要
            aggregated["summary"] = self._generate_summary(aggregated)

            self._logger.info(
                f"Aggregated results for {len(task_results)} agents " f"(task_id: {task_id})"
            )

            return aggregated

        except Exception as e:
            self._logger.error(f"Failed to aggregate results: {e}")
            raise

    def _generate_summary(self, aggregated: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成結果摘要

        Args:
            aggregated: 聚合結果

        Returns:
            摘要字典
        """
        return {
            "total_count": aggregated["total_agents"],
            "success_count": aggregated["successful_agents"],
            "failure_count": aggregated["failed_agents"],
            "success_rate": (
                aggregated["successful_agents"] / aggregated["total_agents"]
                if aggregated["total_agents"] > 0
                else 0.0
            ),
            "output_file_count": len(aggregated["output_files"]),
        }
