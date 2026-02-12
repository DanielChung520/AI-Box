# 代碼功能說明: 缺料分析服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-09

"""缺料分析服務 - 分析庫存是否缺料

職責：
- 分析料號的庫存狀態
- 判斷是否缺料
- 生成建議

核心原則：
- 使用 Data-Agent 的 StructuredQueryHandler 進行查詢
- 不直接構造 SQL，由 Data-Agent 根據 schema 映射欄位
"""

import logging
from typing import Any, Dict, Optional

from agents.services.protocol.base import AgentServiceRequest

from data_agent.structured_query_handler import StructuredQueryHandler

from ..orchestrator_client import OrchestratorClient
from ..validators.data_validator import DataValidator
from .part_service import PartService

logger = logging.getLogger(__name__)


class ShortageAnalyzer:
    """缺料分析服務"""

    def __init__(
        self,
        part_service: Optional[PartService] = None,
        data_validator: Optional[DataValidator] = None,
    ) -> None:
        """初始化缺料分析服務

        Args:
            part_service: 料號查詢服務（可選）
            data_validator: 數據驗證器（可選）
        """
        orchestrator_client = OrchestratorClient()
        self._part_service = part_service or PartService(orchestrator_client)
        self._data_validator = data_validator or DataValidator()
        self._query_handler = StructuredQueryHandler()
        self._logger = logger

    async def analyze_shortage(
        self,
        part_number: str,
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """缺料分析

        Args:
            part_number: 料號
            request: Agent服務請求

        Returns:
            缺料分析結果

        Raises:
            ValueError: 分析失敗時拋出異常
        """
        try:
            # 1. 使用 Data-Agent 查詢庫存信息
            # MM-Agent 只傳遞語義參數，Data-Agent 根據 schema 映射欄位
            result = self._query_handler.execute(
                intent="query_stock_info",
                parameters={
                    "part_number": part_number,
                },
                limit=1,
            )

            if not result.success or not result.rows:
                raise ValueError(f"查無此料號的庫存資料: {part_number}")

            stock_info = result.rows[0]

            # 2. 查詢物料信息（獲取安全庫存）
            part_info = await self._part_service.query_part_info(part_number, request)

            # 3. 驗證數據
            validation = self._data_validator.validate_data(part_info, stock_info)
            if not validation.valid:
                raise ValueError(f"Data validation failed: {validation.issues}")

            # 4. 分析庫存狀態
            current_stock = stock_info.get("current_stock", 0) or stock_info.get("img10", 0)
            safety_stock = part_info.get("safety_stock", 0)

            stock_status = self._data_validator.analyze_stock_status(current_stock, safety_stock)

            # 5. 生成分析報告
            analysis_result = {
                "part_number": part_number,
                "part_name": part_info.get("name"),
                "current_stock": current_stock,
                "safety_stock": safety_stock,
                "status": stock_status.status,
                "is_shortage": stock_status.is_shortage,
                "shortage_quantity": stock_status.shortage_quantity,
                "location": stock_info.get("location") or stock_info.get("img02", ""),
                "recommendation": self._generate_recommendation(stock_status),
                "anomalies": stock_info.get("anomalies", []),
            }

            return analysis_result

        except Exception as e:
            self._logger.error(f"缺料分析失敗: part_number={part_number}, error={e}")
            raise

    def _generate_recommendation(self, stock_status: Any) -> str:
        """生成建議

        Args:
            stock_status: 庫存狀態

        Returns:
            建議文本
        """
        if stock_status.status == "normal":
            return "庫存充足，無需補貨"
        elif stock_status.status == "low":
            return f"庫存偏低，建議補貨 {stock_status.shortage_quantity} 件"
        else:
            return f"庫存缺料，建議立即補貨 {stock_status.shortage_quantity} 件"
