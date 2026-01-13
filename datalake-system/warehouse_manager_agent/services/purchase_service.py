# 代碼功能說明: 採購單生成服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""採購單生成服務 - 生成採購單（虛擬）"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from agents.services.protocol.base import AgentServiceRequest

from ..models import PurchaseOrder
from .part_service import PartService
from .shortage_analyzer import ShortageAnalyzer

logger = logging.getLogger(__name__)


class PurchaseService:
    """採購單生成服務"""

    def __init__(
        self,
        part_service: Optional[PartService] = None,
        shortage_analyzer: Optional[ShortageAnalyzer] = None,
    ) -> None:
        """初始化採購單生成服務

        Args:
            part_service: 料號查詢服務（可選）
            shortage_analyzer: 缺料分析服務（可選）
        """
        from ..orchestrator_client import OrchestratorClient

        orchestrator_client = OrchestratorClient()
        self._part_service = part_service or PartService(orchestrator_client)
        self._shortage_analyzer = shortage_analyzer or ShortageAnalyzer(part_service, None, None)
        self._logger = logger

    async def generate_purchase_order(
        self,
        part_number: str,
        quantity: int,
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """生成採購單（虛擬）

        Args:
            part_number: 料號
            quantity: 採購數量
            request: Agent服務請求

        Returns:
            採購單信息

        Raises:
            ValueError: 生成失敗時拋出異常
        """
        try:
            # 1. 驗證參數
            if quantity <= 0:
                raise ValueError("Purchase quantity must be greater than 0")

            # 2. 查詢物料信息（獲取供應商信息）
            part_info = await self._part_service.query_part_info(part_number, request)

            # 3. 可選：檢查缺料狀態
            try:
                shortage_analysis = await self._shortage_analyzer.analyze_shortage(
                    part_number, request
                )
                if not shortage_analysis.get("is_shortage"):
                    # 雖然不缺料，但用戶明確要求生成採購單，仍然生成
                    pass
            except Exception as e:
                self._logger.warning(f"缺料分析失敗，繼續生成採購單: {e}")

            # 4. 生成採購單記錄
            purchase_order_id = (
                f"PO-{datetime.now().strftime('%Y%m%d')}-" f"{uuid.uuid4().hex[:6].upper()}"
            )

            unit_price = part_info.get("unit_price", 0)
            purchase_order = PurchaseOrder(
                purchase_order_id=purchase_order_id,
                part_number=part_number,
                part_name=part_info.get("name"),
                quantity=quantity,
                supplier=part_info.get("supplier"),
                unit_price=unit_price,
                total_amount=quantity * unit_price,
                status="虛擬生成",
                created_at=datetime.now().isoformat(),
                created_by="warehouse_manager_agent",
                note="此為虛擬採購單，僅用於測試",
            )

            # 5. 記錄採購單（可選：存儲到數據庫或日誌）
            self._logger.info(
                f"採購單已生成: purchase_order_id={purchase_order_id}, "
                f"part_number={part_number}, quantity={quantity}"
            )

            return purchase_order.model_dump()

        except Exception as e:
            self._logger.error(
                f"生成採購單失敗: part_number={part_number}, " f"quantity={quantity}, error={e}"
            )
            raise
