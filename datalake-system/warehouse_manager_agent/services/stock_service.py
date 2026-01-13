# 代碼功能說明: 庫存查詢服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""庫存查詢服務 - 通過Data Agent查詢庫存信息"""

import logging
import os
from typing import Any, Dict, Optional

from agents.services.protocol.base import AgentServiceRequest

from ..orchestrator_client import OrchestratorClient
from ..validators.data_validator import DataValidator

logger = logging.getLogger(__name__)


class StockService:
    """庫存查詢服務"""

    def __init__(
        self,
        orchestrator_client: Optional[Any] = None,
        data_validator: Optional[DataValidator] = None,
    ) -> None:
        """初始化庫存查詢服務

        Args:
            orchestrator_client: Orchestrator客戶端或Data Agent直接客戶端（可選）
            data_validator: 數據驗證器（可選）
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
        self._data_validator = data_validator or DataValidator()
        self._logger = logger

    async def query_stock_info(
        self,
        part_number: str,
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """查詢庫存信息

        Args:
            part_number: 料號
            request: Agent服務請求

        Returns:
            庫存信息

        Raises:
            ValueError: 查詢失敗或庫存不存在時拋出異常
        """
        try:
            result = await self._orchestrator_client.call_data_agent(
                action="query_datalake",
                parameters={
                    "bucket": "bucket-datalake-assets",
                    "key": f"stock/{part_number}.json",
                    "query_type": "exact",
                },
                request=request,
            )

            if not result.get("success"):
                error_msg = result.get("error", "Failed to query stock info")
                raise ValueError(f"Failed to query stock info: {error_msg}")

            rows = result.get("rows", [])
            if not rows:
                raise ValueError(f"Stock not found: {part_number}")

            stock_info = rows[0]

            # 處理數據異常
            stock_info = self._data_validator.handle_data_anomalies(stock_info)

            return stock_info

        except Exception as e:
            self._logger.error(f"查詢庫存信息失敗: part_number={part_number}, error={e}")
            raise
