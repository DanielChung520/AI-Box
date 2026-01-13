# 代碼功能說明: 料號查詢服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""料號查詢服務 - 通過Data Agent查詢物料信息"""

import logging
import os
from typing import Any, Dict, Optional

from agents.services.protocol.base import AgentServiceRequest

from ..orchestrator_client import OrchestratorClient

logger = logging.getLogger(__name__)


class PartService:
    """料號查詢服務"""

    def __init__(
        self,
        orchestrator_client: Optional[Any] = None,
    ) -> None:
        """初始化料號查詢服務

        Args:
            orchestrator_client: Orchestrator客戶端或Data Agent直接客戶端（可選）
        """
        # 如果沒有提供客戶端，根據環境變數決定使用哪個
        if orchestrator_client is None:
            use_direct = os.getenv("WAREHOUSE_AGENT_USE_DIRECT_CLIENT", "false").lower() == "true"
            if use_direct:
                from ..data_agent_direct_client import DataAgentDirectClient

                orchestrator_client = DataAgentDirectClient()
            else:
                orchestrator_client = OrchestratorClient()

        self._orchestrator_client = orchestrator_client
        self._logger = logger

    async def query_part_info(
        self,
        part_number: str,
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """查詢物料信息

        Args:
            part_number: 料號
            request: Agent服務請求

        Returns:
            物料信息

        Raises:
            ValueError: 查詢失敗或物料不存在時拋出異常
        """
        try:
            result = await self._orchestrator_client.call_data_agent(
                action="query_datalake",
                parameters={
                    "bucket": "bucket-datalake-assets",
                    "key": f"parts/{part_number}.json",
                    "query_type": "exact",
                },
                request=request,
            )

            if not result.get("success"):
                error_msg = result.get("error", "Failed to query part info")
                raise ValueError(f"Failed to query part info: {error_msg}")

            rows = result.get("rows", [])
            if not rows:
                raise ValueError(f"Part not found: {part_number}")

            return rows[0]  # 返回第一個結果

        except Exception as e:
            self._logger.error(f"查詢物料信息失敗: part_number={part_number}, error={e}")
            raise
