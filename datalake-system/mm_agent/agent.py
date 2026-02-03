# 代碼功能說明: 庫管員Agent實現
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""庫管員Agent實現 - 庫存管理業務Agent"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)

from .models import WarehouseAgentResponse
from .orchestrator_client import OrchestratorClient
from .services.context_manager import ContextManager
from .services.part_service import PartService
from .services.purchase_service import PurchaseService
from .services.responsibility_analyzer import ResponsibilityAnalyzer
from .services.semantic_analyzer import SemanticAnalyzer
from .services.shortage_analyzer import ShortageAnalyzer
from .services.stock_service import StockService
from .validators.data_validator import DataValidator
from .validators.result_validator import ResultValidator

logger = logging.getLogger(__name__)


class MMAgent(AgentServiceProtocol):
    """庫管員Agent - 庫存管理業務Agent"""

    def __init__(
        self,
        orchestrator_client: Optional[OrchestratorClient] = None,
        semantic_analyzer: Optional[SemanticAnalyzer] = None,
        responsibility_analyzer: Optional[ResponsibilityAnalyzer] = None,
        context_manager: Optional[ContextManager] = None,
        part_service: Optional[PartService] = None,
        stock_service: Optional[StockService] = None,
        shortage_analyzer: Optional[ShortageAnalyzer] = None,
        purchase_service: Optional[PurchaseService] = None,
        result_validator: Optional[ResultValidator] = None,
        data_validator: Optional[DataValidator] = None,
    ) -> None:
        """初始化庫管員Agent

        Args:
            orchestrator_client: Orchestrator客戶端（可選）
            semantic_analyzer: 語義分析器（可選）
            responsibility_analyzer: 職責分析器（可選）
            context_manager: 上下文管理器（可選）
            part_service: 料號查詢服務（可選）
            stock_service: 庫存查詢服務（可選）
            shortage_analyzer: 缺料分析服務（可選）
            purchase_service: 採購單生成服務（可選）
            result_validator: 結果驗證器（可選）
            data_validator: 數據驗證器（可選）
        """
        self.agent_id = "mm-agent"
        self._logger = logger

        # 初始化服務
        # 如果沒有提供客戶端，根據環境變數決定使用哪個
        if orchestrator_client is None:
            use_direct = os.getenv("MM_AGENT_USE_DIRECT_CLIENT", "false").lower() == "true"
            if use_direct:
                from .data_agent_direct_client import DataAgentDirectClient

                orchestrator_client = DataAgentDirectClient()
            else:
                orchestrator_client = OrchestratorClient()

        self._orchestrator_client = orchestrator_client
        self._semantic_analyzer = semantic_analyzer or SemanticAnalyzer()
        self._responsibility_analyzer = responsibility_analyzer or ResponsibilityAnalyzer()
        self._context_manager = context_manager or ContextManager()
        self._data_validator = data_validator or DataValidator()
        self._result_validator = result_validator or ResultValidator()

        # 初始化業務服務
        self._part_service = part_service or PartService(self._orchestrator_client)
        self._stock_service = stock_service or StockService()
        self._shortage_analyzer = shortage_analyzer or ShortageAnalyzer(
            self._part_service, self._stock_service, self._data_validator
        )
        self._purchase_service = purchase_service or PurchaseService(
            self._part_service, self._shortage_analyzer
        )

    async def execute(
        self,
        request: AgentServiceRequest,
    ) -> AgentServiceResponse:
        """執行庫存管理任務

        Args:
            request: Agent服務請求，包含：
                - task_id: 任務ID
                - task_data: 任務數據（用戶指令或結構化請求）
                - metadata: 元數據（用戶信息、租戶信息等）

        Returns:
            Agent服務響應，包含：
                - task_id: 任務ID
                - status: 任務狀態（completed/failed/error）
                - result: 執行結果
                - error: 錯誤信息（如果有）
                - metadata: 元數據
        """
        try:
            # 1. 獲取會話ID
            session_id = (
                request.metadata.get("session_id") if request.metadata else None
            ) or request.task_id

            # 2. 獲取上下文
            context = await self._context_manager.get_context(session_id)

            # 3. 獲取用戶指令
            user_instruction = request.task_data.get("instruction", "")
            if not user_instruction:
                return AgentServiceResponse(
                    task_id=request.task_id,
                    status="failed",
                    result=WarehouseAgentResponse(
                        success=False,
                        task_type="unknown",
                        error="缺少用戶指令（instruction字段）",
                    ).model_dump(),
                    error="缺少用戶指令",
                    metadata=request.metadata,
                )

            # 4. 解析指代（如果存在）
            resolved_instruction = await self._context_manager.resolve_references(
                user_instruction, context
            )

            # 5. 語義分析（使用上下文）
            context_info = None
            if context.last_result:
                context_info = {
                    "last_query": context.current_query,
                    "last_result": context.last_result,
                    "entities": context.entities,
                }

            semantic_result = await self._semantic_analyzer.analyze(
                resolved_instruction, context_info
            )

            # 6. 職責理解
            responsibility = await self._responsibility_analyzer.understand(semantic_result)

            # 7. 執行任務
            result = await self._execute_responsibility(responsibility, semantic_result, request)

            # 8. 更新上下文
            await self._context_manager.update_context(
                session_id=session_id,
                instruction=user_instruction,
                result=result,
            )

            # 9. 構建響應
            response = WarehouseAgentResponse(
                success=result.get("success", False),
                task_type=responsibility.type,
                result=result,
                semantic_analysis=semantic_result.model_dump(),
                responsibility=responsibility.description,
            )

            return AgentServiceResponse(
                task_id=request.task_id,
                status="completed" if response.success else "failed",
                result=response.model_dump(),
                error=result.get("error"),
                metadata=request.metadata,
            )

        except Exception as e:
            self._logger.error(f"庫管員Agent執行失敗: {e}", exc_info=True)
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=WarehouseAgentResponse(
                    success=False,
                    task_type="unknown",
                    error=str(e),
                ).model_dump(),
                error=str(e),
                metadata=request.metadata,
            )

    async def _execute_responsibility(
        self,
        responsibility: Any,
        semantic_result: Any,
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """執行職責

        Args:
            responsibility: 職責定義
            semantic_result: 語義分析結果
            request: Agent服務請求

        Returns:
            執行結果
        """
        responsibility_type = responsibility.type
        parameters = semantic_result.parameters

        if responsibility_type == "query_part":
            part_number = parameters.get("part_number")
            if not part_number:
                return {
                    "success": False,
                    "error": "缺少料號參數（part_number）",
                }
            return await self._query_part_info(part_number, request)

        elif responsibility_type == "query_stock":
            part_number = parameters.get("part_number")
            if not part_number:
                return {
                    "success": False,
                    "error": "缺少料號參數（part_number）",
                }
            return await self._query_stock_info(part_number, request)

        elif responsibility_type == "analyze_shortage":
            part_number = parameters.get("part_number")
            if not part_number:
                return {
                    "success": False,
                    "error": "缺少料號參數（part_number）",
                }
            return await self._analyze_shortage(part_number, request)

        elif responsibility_type == "generate_purchase_order":
            part_number = parameters.get("part_number")
            quantity = parameters.get("quantity")
            if not part_number:
                return {
                    "success": False,
                    "error": "缺少料號參數（part_number）",
                }
            if not quantity:
                return {
                    "success": False,
                    "error": "缺少數量參數（quantity）",
                }
            return await self._generate_purchase_order(part_number, quantity, request)

        elif responsibility_type == "clarification_needed":
            return {
                "success": False,
                "error": "需要澄清用戶意圖",
                "clarification_questions": responsibility.clarification_questions,
            }

        else:
            return {
                "success": False,
                "error": f"未知的職責類型: {responsibility_type}",
            }

    async def _query_part_info(
        self,
        part_number: str,
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """查詢物料信息

        Args:
            part_number: 料號
            request: Agent服務請求

        Returns:
            查詢結果
        """
        try:
            part_info = await self._part_service.query_part_info(part_number, request)
            return {
                "success": True,
                "part_number": part_number,
                "part_info": part_info,
            }
        except Exception as e:
            self._logger.error(f"查詢物料信息失敗: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _query_stock_info(
        self,
        part_number: str,
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """查詢庫存信息

        Args:
            part_number: 料號
            request: Agent服務請求

        Returns:
            查詢結果
        """
        try:
            stock_info = await self._stock_service.query_stock_info(part_number, request)
            return {
                "success": True,
                "part_number": part_number,
                "stock_info": stock_info,
            }
        except Exception as e:
            self._logger.error(f"查詢庫存信息失敗: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _analyze_shortage(
        self,
        part_number: str,
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """缺料分析

        Args:
            part_number: 料號
            request: Agent服務請求

        Returns:
            分析結果
        """
        try:
            analysis_result = await self._shortage_analyzer.analyze_shortage(part_number, request)
            return {
                "success": True,
                "analysis": analysis_result,
            }
        except Exception as e:
            self._logger.error(f"缺料分析失敗: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _generate_purchase_order(
        self,
        part_number: str,
        quantity: int,
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """生成採購單

        Args:
            part_number: 料號
            quantity: 數量
            request: Agent服務請求

        Returns:
            採購單結果
        """
        try:
            purchase_order = await self._purchase_service.generate_purchase_order(
                part_number, quantity, request
            )
            return {
                "success": True,
                "purchase_order": purchase_order,
            }
        except Exception as e:
            self._logger.error(f"生成採購單失敗: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def health_check(self) -> AgentServiceStatus:
        """健康檢查

        Returns:
            Agent服務狀態
        """
        return AgentServiceStatus.AVAILABLE

    async def get_capabilities(self) -> Dict[str, Any]:
        """獲取服務能力

        Returns:
            服務能力描述
        """
        return {
            "capabilities": [
                "query_part",
                "query_stock",
                "analyze_shortage",
                "generate_purchase_order",
            ],
            "description": "庫存管理業務Agent",
        }
