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

from .models import ConversationContext, WarehouseAgentResponse
from .orchestrator_client import OrchestratorClient
from .ptao.loop import PTAOLoop
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
        prompt_manager: Optional[Any] = None,
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
            prompt_manager: 提示詞管理器（可選）
        """
        self.agent_id = "mm-agent"
        self._logger = logger

        # 初始化服務
        # 如果沒有提供客戶端，根據環境變數決定使用哪個
        if orchestrator_client is None:
            use_direct = os.getenv("MM_AGENT_USE_DIRECT_CLIENT", "false").lower() == "true"
            if use_direct:
                from .data_agent_direct_client import DTAgentDirectClient

                orchestrator_client = DTAgentDirectClient()
            else:
                orchestrator_client = OrchestratorClient()

        self._orchestrator_client = orchestrator_client
        self._semantic_analyzer = semantic_analyzer or SemanticAnalyzer()
        self._responsibility_analyzer = responsibility_analyzer or ResponsibilityAnalyzer()
        self._context_manager = context_manager or ContextManager()
        self._data_validator = data_validator or DataValidator()
        self._result_validator = result_validator or ResultValidator()
        self._prompt_manager = prompt_manager

        # 初始化業務服務
        self._part_service = part_service or PartService()
        self._stock_service = stock_service or StockService()
        self._shortage_analyzer = shortage_analyzer or ShortageAnalyzer(
            self._part_service, self._data_validator
        )
        self._purchase_service = purchase_service or PurchaseService(
            self._part_service, self._shortage_analyzer
        )

        from data_agent.structured_query_handler import StructuredQueryHandler

        self._query_handler = StructuredQueryHandler()

        # DT-Agent endpoint 直接調用
        self._jp_endpoint = (
            os.getenv(
                "DT_AGENT_SERVICE_URL", os.getenv("DATA_AGENT_SERVICE_URL", "http://localhost:8005")
            )
            + "/api/v1/dt-agent/execute"
        )

        # 初始化職責分派 Registry
        from mm_agent.ptao.responsibility_registry import ResponsibilityRegistry

        self._responsibility_registry = ResponsibilityRegistry()
        self._responsibility_registry.register("query_part", self._handle_query_part)
        self._responsibility_registry.register("query_stock", self._handle_query_stock)
        self._responsibility_registry.register(
            "query_stock_history", self._handle_query_stock_history
        )
        self._responsibility_registry.register("analyze_shortage", self._handle_analyze_shortage)
        self._responsibility_registry.register(
            "generate_purchase_order", self._handle_generate_purchase_order
        )
        self._responsibility_registry.register(
            "analyze_existing_result", self._handle_analyze_existing_result
        )
        self._responsibility_registry.register(
            "clarification_needed", self._handle_clarification_needed
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
        ptao_result = None
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

            # 7. 執行任務（P-T-A-O 迴圈）
            ptao_result = await PTAOLoop(self._responsibility_registry).run(
                responsibility=responsibility,
                semantic_result=semantic_result,
                request=request,
                user_instruction=resolved_instruction,
            )
            result = ptao_result.raw_result

            # 7.5. 生成 LLM 業務回覆（如需要）
            result = await self._generate_llm_business_response(
                result=result,
                user_instruction=user_instruction,
                responsibility_type=responsibility.type,
            )

            # 8. 更新上下文
            await self._context_manager.update_context(
                session_id=session_id,
                instruction=user_instruction,
                result=result,
            )

            # 9. 構建響應
            ptao_metadata = {
                "ptao": {
                    "thought": ptao_result.thought.model_dump(),
                    "observation": ptao_result.observation.model_dump(),
                    "decision_log": [e.model_dump() for e in ptao_result.decision_log.entries],
                }
            }
            response = WarehouseAgentResponse(
                success=result.get("success", False),
                task_type=responsibility.type,
                response=result.get("response"),  # 提取 LLM 回覆到頂層
                result=result,
                semantic_analysis=semantic_result.model_dump(),
                responsibility=responsibility.description,
                metadata=ptao_metadata,
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
        user_instruction: str = "",
    ) -> Dict[str, Any]:
        """執行職責

        Args:
            responsibility: 職責定義
            semantic_result: 語義分析結果
            request: Agent服務請求

        Returns:
            執行結果
        """
        handler = self._responsibility_registry.get_handler(responsibility.type)
        if handler is None:
            return {"success": False, "error": f"未知的職責類型: {responsibility.type}"}
        return await handler(responsibility, semantic_result, request, user_instruction)

    async def _handle_query_part(
        self,
        responsibility: Any,
        semantic_result: Any,
        request: AgentServiceRequest,
        user_instruction: str = "",
    ) -> Dict[str, Any]:
        """處理料號查詢職責"""
        parameters = semantic_result.parameters
        part_number = parameters.get("part_number")
        if not part_number:
            return {
                "success": False,
                "error": "缺少料號參數（part_number）",
            }
        return await self._query_part_info(part_number, request)

    async def _handle_query_stock(
        self,
        responsibility: Any,
        semantic_result: Any,
        request: AgentServiceRequest,
        user_instruction: str = "",
    ) -> Dict[str, Any]:
        """處理庫存查詢職責"""
        parameters = semantic_result.parameters
        return await self._query_stock_info(parameters, request, user_instruction)

    async def _handle_query_stock_history(
        self,
        responsibility: Any,
        semantic_result: Any,
        request: AgentServiceRequest,
        user_instruction: str = "",
    ) -> Dict[str, Any]:
        """處理進料歷史查詢職責"""
        parameters = semantic_result.parameters
        part_number = parameters.get("part_number")
        if not part_number:
            return {
                "success": False,
                "error": "缺少料號參數（part_number）",
            }
        return await self._query_stock_history(part_number, request)

    async def _handle_analyze_shortage(
        self,
        responsibility: Any,
        semantic_result: Any,
        request: AgentServiceRequest,
        user_instruction: str = "",
    ) -> Dict[str, Any]:
        """處理缺料分析職責"""
        parameters = semantic_result.parameters
        part_number = parameters.get("part_number")
        if not part_number:
            return {
                "success": False,
                "error": "缺少料號參數（part_number）",
            }
        return await self._analyze_shortage(part_number, request)

    async def _handle_generate_purchase_order(
        self,
        responsibility: Any,
        semantic_result: Any,
        request: AgentServiceRequest,
        user_instruction: str = "",
    ) -> Dict[str, Any]:
        """處理採購單生成職責"""
        parameters = semantic_result.parameters
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

    async def _handle_analyze_existing_result(
        self,
        responsibility: Any,
        semantic_result: Any,
        request: AgentServiceRequest,
        user_instruction: str = "",
    ) -> Dict[str, Any]:
        """處理分析既有結果職責"""
        context = await self._context_manager.get_context(
            (request.metadata.get("session_id") if request.metadata else None) or request.task_id
        )
        result = await self._analyze_existing_result(user_instruction, context)
        return result

    async def _handle_clarification_needed(
        self,
        responsibility: Any,
        semantic_result: Any,
        request: AgentServiceRequest,
        user_instruction: str = "",
    ) -> Dict[str, Any]:
        """處理需要澄清的職責"""
        questions = responsibility.clarification_questions or []
        if questions:
            explanation = questions[0] + "\n"
            for q in questions[1:]:
                explanation += q + "\n"
        else:
            explanation = "您的指令不夠明確，請提供更多細節。"

        return {
            "success": True,
            "needs_clarification": True,
            "clarification_message": explanation.strip(),
            "clarification_questions": questions,
            "response": explanation.strip(),
        }

    async def _query_part_info(
        self,
        part_number: str,
        request: AgentServiceRequest = None,
    ) -> Dict[str, Any]:
        """查詢物料信息

        Args:
            part_number: 料號

        Returns:
            查詢結果
        """
        try:
            part_info = await self._part_service.query_part_info(part_number)

            # 生成自然語言解釋
            explanation = f"以下是料號 {part_number} 的詳細資料：\n"
            explanation += f"• 料號：{part_info.get('part_number', part_number)}\n"
            if part_info.get("description"):
                explanation += f"• 描述：{part_info.get('description')}\n"
            if part_info.get("spec"):
                explanation += f"• 規格：{part_info.get('spec')}\n"
            if part_info.get("supplier"):
                explanation += f"• 供應商：{part_info.get('supplier')}\n"
            if part_info.get("unit"):
                explanation += f"• 單位：{part_info.get('unit')}\n"

            return {
                "success": True,
                "part_info": part_info,
                "response": explanation,
            }
        except Exception as e:
            self._logger.error(f"查詢物料信息失敗: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            self._logger.error(f"查詢物料信息失敗: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _query_stock_info(
        self,
        parameters: Dict[str, Any],
        request: AgentServiceRequest,
        user_instruction: str = "",
    ) -> Dict[str, Any]:
        """查詢庫存信息

        使用 DT-Agent 的 /api/v1/dt-agent/execute 端點處理庫存查詢。
        必須使用新架構（schema_driven_query），禁止使用舊的 StructuredQueryHandler。

        Args:
            parameters: 語義分析提取的參數
            request: Agent服務請求

        Returns:
            查詢結果
        """
        import httpx

        # 預設值，避免 except 塊中未定義
        nlq = ""

        try:
            self._logger.info(
                f"[Agent] 查詢庫存，參數: {parameters}, user_instruction: {user_instruction}"
            )

            # 構建自然語言查詢
            nlq = parameters.get("nlq", "")
            if not nlq:
                part_no = parameters.get("part_number", "")
                warehouse = parameters.get("warehouse", "")
                if part_no:
                    nlq = f"查詢料號 {part_no} 各倉庫的庫存數量"
                elif warehouse:
                    nlq = f"查詢 {warehouse} 倉庫的庫存"

            # 如果 parameters 都沒有，才用 user_instruction
            if not nlq and user_instruction:
                nlq = user_instruction

            # 如果都沒有，返回需要澄清
            if not nlq:
                return {
                    "success": False,
                    "needs_clarification": True,
                    "clarification_questions": ["請問您想查詢哪個料號或倉庫的庫存？"],
                    "message": "查詢條件不足，需要澄清",
                }

            # 使用 DT-Agent /api/v1/dt-agent/execute 端點
            payload = {
                "task_id": f"mm-agent-{request.task_id}",
                "task_type": "simple_query",
                "task_data": {"nlq": nlq},
            }

            # 使用同步 client
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(self._jp_endpoint, json=payload)
                result = resp.json()

            self._logger.info(f"[Agent] DT-Agent response: {result.get('success')}")

            # ============================================================
            # 處理 DT-Agent 結構化響應
            # ============================================================

            # 檢查是否有錯誤 - 支援兩種格式：errors 陣列 或 error_code 頂層欄位
            errors = result.get("errors", [])

            # 如果沒有 errors 陣列但有頂層 error_code，則構造 errors 陣列
            if not errors and result.get("error_code"):
                errors = [
                    {
                        "code": result.get("error_code", ""),
                        "message": result.get("message", "未知錯誤"),
                    }
                ]

            # 判斷錯誤類型
            error_codes = [e.get("code", "") for e in errors]
            error_messages = [e.get("message", "") for e in errors]

            # 1. 查詢成功 - DT-Agent 返回 success: true
            if result.get("success") is True:
                # DT-Agent: result directly contains data
                data_result = result if result.get("data") else result.get("result", {})
                rows = data_result.get("data", [])

                if not rows:
                    # 查詢結構正確，但確實沒有資料
                    self._logger.info("[Agent] 查詢成功但無資料")
                    return {
                        "success": True,
                        "data_found": False,  # 標記為查無資料
                        "stock_list": [],
                        "count": 0,
                        "response": None,  # 交由 LLM 生成業務回覆
                        "sql": data_result.get("sql", ""),
                        "query_context": {
                            "nlq": nlq,
                            "intent": "QUERY_INVENTORY",
                            "warehouse": parameters.get("warehouse", ""),
                            "part_no": parameters.get("part_number", ""),
                        },
                    }

                # 有資料，繼續處理
                stock_list = rows
                count = len(rows)
                sql = data_result.get("sql", "")

                self._logger.info(f"[Agent] SQL: {sql[:100]}...")

                # 新欄位映射 (mart_inventory_wide)
                explanation = f"庫存查詢結果：共找到 {count} 筆資料\n\n"

                if stock_list:
                    for i, row in enumerate(stock_list[:10], 1):
                        # 使用新的欄位名稱
                        item_no = row.get("item_no", "-")
                        warehouse_no = row.get("warehouse_no", "-")
                        location_no = row.get("location_no", "-")
                        existing_stocks = row.get("existing_stocks", 0)
                        unit = row.get("unit", "PC")

                        explanation += f"{i}. 料號：{item_no}\n"
                        explanation += f"   倉庫：{warehouse_no}\n"
                        explanation += f"   儲位：{location_no or '-'}\n"
                        explanation += f"   庫存：{existing_stocks:,.0f} {unit}\n\n"

                    if count > 10:
                        explanation += f"... 還有 {count - 10} 筆資料"

                return {
                    "success": True,
                    "data_found": True,
                    "stock_list": stock_list,
                    "count": count,
                    "response": explanation,
                    "sql": sql,
                    "query_context": {
                        "nlq": nlq,
                        "intent": "QUERY_INVENTORY",
                        "warehouse": parameters.get("warehouse", ""),
                        "part_no": parameters.get("part_number", ""),
                    },
                }

            # 2. 邊界查詢過大 (QUERY_SCOPE_TOO_LARGE) - 需要回問確認
            if "QUERY_SCOPE_TOO_LARGE" in error_codes:
                error_msg = error_messages[0] if error_messages else "查詢範圍過大"
                self._logger.warning(f"[Agent] 邊界查詢需要確認: {error_msg}")
                return {
                    "success": False,
                    "needs_clarification": True,  # 標記需要回問
                    "clarification_type": "QUERY_SCOPE_TOO_LARGE",
                    "message": error_msg,
                    "suggestions": errors[0].get("suggestions", []) if errors else [],
                    "original_query": nlq,
                }

            # 3. 意圖不清晰 (INTENT_UNCLEAR) - 需要回問確認
            if "INTENT_UNCLEAR" in error_codes:
                error_msg = error_messages[0] if error_messages else "無法識別查詢意圖"
                self._logger.warning(f"[Agent] 意圖不清晰: {error_msg}")
                return {
                    "success": False,
                    "needs_clarification": True,
                    "clarification_type": "INTENT_UNCLEAR",
                    "message": error_msg,
                    "suggestions": errors[0].get("suggestions", []) if errors else [],
                    "original_query": nlq,
                }

            # 3.5 DT-Agent Guard 攔截 (QUERY_GUARD_REJECTED) - 需要引導用戶
            if "QUERY_GUARD_REJECTED" in error_codes:
                guard_type = result.get("metadata", {}).get("guard_type", "unknown")
                clarification_steps = result.get("clarification_needed", [])
                suggestion = result.get("suggestion", "")
                error_msg = result.get("message", "查詢被攔截")
                self._logger.warning(f"[Agent] Guard 攔截 ({guard_type}): {error_msg}")
                return {
                    "success": False,
                    "needs_clarification": True,
                    "clarification_type": "QUERY_GUARD_REJECTED",
                    "guard_type": guard_type,
                    "clarification_needed": clarification_steps,
                    "suggestion": suggestion,
                    "message": error_msg,
                    "original_query": nlq,
                }

            # 3.6 DT-Agent Schema 構建失敗 (SCHEMA_PROMPT_BUILD_FAILED)
            if "SCHEMA_PROMPT_BUILD_FAILED" in error_codes:
                error_msg = error_messages[0] if error_messages else "Schema 構建失敗"
                self._logger.error(f"[Agent] Schema 構建失敗: {error_msg}")
                return {
                    "success": False,
                    "error_type": "SCHEMA_ERROR",
                    "message": error_msg,
                    "original_query": nlq,
                }

            # 3.7 DT-Agent SQL 生成失敗 (SQL_GENERATION_FAILED)
            if "SQL_GENERATION_FAILED" in error_codes:
                error_msg = error_messages[0] if error_messages else "SQL 生成失敗"
                self._logger.error(f"[Agent] SQL 生成失敗: {error_msg}")
                return {
                    "success": False,
                    "error_type": "SQL_GENERATION_ERROR",
                    "message": error_msg,
                    "original_query": nlq,
                }

            # 3.8 DT-Agent SQL 安全檢查失敗 (SQL_SAFETY_CHECK_FAILED)
            if "SQL_SAFETY_CHECK_FAILED" in error_codes:
                error_msg = error_messages[0] if error_messages else "SQL 安全檢查未通過"
                sql = (
                    result.get("details", {}).get("sql", "")
                    if isinstance(result.get("details"), dict)
                    else ""
                )
                self._logger.error(f"[Agent] SQL 安全檢查失敗: {error_msg}, sql={sql}")
                return {
                    "success": False,
                    "error_type": "SQL_SAFETY_ERROR",
                    "message": error_msg,
                    "original_query": nlq,
                }

            # 3.9 DT-Agent SQL 執行失敗 (SQL_EXECUTION_FAILED)
            if "SQL_EXECUTION_FAILED" in error_codes:
                error_msg = error_messages[0] if error_messages else "SQL 執行失敗"
                sql = (
                    result.get("details", {}).get("sql", "")
                    if isinstance(result.get("details"), dict)
                    else ""
                )
                self._logger.error(f"[Agent] SQL 執行失敗: {error_msg}, sql={sql}")
                return {
                    "success": False,
                    "error_type": "SQL_EXECUTION_ERROR",
                    "message": error_msg,
                    "original_query": nlq,
                }

            # 4. Schema 錯誤 (SCHEMA_NOT_FOUND) - 記錄異常
            if "SCHEMA_NOT_FOUND" in error_codes:
                error_msg = error_messages[0] if error_messages else "Schema 錯誤"
                self._logger.error(f"[Agent] Schema 錯誤: {error_msg}")
                return {
                    "success": False,
                    "error_type": "SCHEMA_ERROR",
                    "message": error_msg,
                    "exception": errors[0].get("exception") if errors else None,
                    "original_query": nlq,
                }

            # 5. 連接/網路異常 - 記錄異常
            if "CONNECTION_TIMEOUT" in error_codes or "NETWORK_ERROR" in error_codes:
                error_msg = error_messages[0] if error_messages else "連線超時或網路異常"
                self._logger.error(f"[Agent] 連線異常: {error_msg}")
                return {
                    "success": False,
                    "error_type": "CONNECTION_ERROR",
                    "message": error_msg,
                    "exception": errors[0].get("exception") if errors else None,
                    "original_query": nlq,
                }

            # 6. 其他錯誤 - 記錄異常
            error_msg = error_messages[0] if error_messages else "未知錯誤"
            self._logger.error(f"[Agent] 查詢失敗: {error_msg}")
            return {
                "success": False,
                "error_type": "UNKNOWN_ERROR",
                "message": error_msg,
                "error_codes": error_codes,
                "original_query": nlq,
            }

        except httpx.TimeoutException:
            self._logger.error("[Agent] 查詢超時")
            return {
                "success": False,
                "error_type": "TIMEOUT",
                "message": "查詢執行超時，請嘗試更明確的查詢條件",
                "original_query": nlq,
            }
        except httpx.ConnectError:
            self._logger.error("[Agent] 連接失敗")
            return {
                "success": False,
                "error_type": "CONNECTION_ERROR",
                "message": "無法連接到 DT-Agent 服務，請確認服務是否正常運行",
                "original_query": nlq,
            }
        except Exception as e:
            self._logger.error(f"查詢庫存信息失敗: {e}")
            return {
                "success": False,
                "error_type": "INTERNAL_ERROR",
                "message": str(e),
                "original_query": nlq,
            }

    async def _analyze_existing_result(
        self,
        query: str,
        context: ConversationContext,
    ) -> Dict[str, Any]:
        """分析已有的查詢結果

        基於 context.last_result 進行分析性回覆，不重新調用 Data-Agent。

        Args:
            query: 用戶的分析性問題
            context: 對話上下文（包含 last_result）

        Returns:
            分析結果字典
        """
        try:
            self._logger.info(f"[Agent] 分析已有結果，問題: {query[:50]}")

            if self._prompt_manager is None:
                from .services.prompt_manager import PromptManager

                self._prompt_manager = PromptManager()

            last_result = context.last_result if context else None

            # 邊界情況 1：無 last_result
            if not last_result:
                response = await self._prompt_manager.generate_analytical_response(
                    query, None, context
                )
                return {
                    "success": False,
                    "needs_clarification": True,
                    "response": response,
                }

            # 邊界情況 2：上次查詢失敗
            if last_result.get("status") != "success" and not last_result.get("success"):
                return {
                    "success": False,
                    "error": "上次查詢結果無效，無法進行分析",
                    "response": "上次查詢沒有成功，請重新查詢後再進行分析。",
                }

            # 邊界情況 3：上次查詢無數據
            # context.last_result 的格式是 _query_stock_info() 的返回值，使用 stock_list 欄位
            data = last_result.get("stock_list", last_result.get("data", []))
            if not data:
                return {
                    "success": True,
                    "response": "上次查詢結果沒有資料，無法進行分析。請先查詢有資料的料號或倉庫。",
                }

            # 正常情況：調用 LLM 分析
            # 標準化 last_result 格式供 generate_analytical_response 使用
            normalized_result = {
                "status": "success",
                "data": last_result.get("stock_list", last_result.get("data", [])),
                "sql": last_result.get("sql", ""),
                "row_count": last_result.get("count", len(last_result.get("stock_list", []))),
            }
            response = await self._prompt_manager.generate_analytical_response(
                query,
                normalized_result,
                context,
            )

            return {
                "success": True,
                "response": response,
                "analysis_source": "last_result",
            }

        except Exception as e:
            self._logger.error(f"[Agent] 分析已有結果失敗: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": "分析過程中發生錯誤，請稍後再試。",
            }

    async def _generate_llm_business_response(
        self,
        result: Dict[str, Any],
        user_instruction: str,
        responsibility_type: str,
    ) -> Dict[str, Any]:
        """生成 LLM 業務回覆

        根據 Data-Agent 返回的結構化結果，生成對用戶友好的業務回覆。

        Args:
            result: 執行任務後的結果
            user_instruction: 用戶原始指令
            responsibility_type: 職責類型

        Returns:
            添加了 LLM 業務回覆的結果
        """
        # Debug: 記錄收到的 result 結構
        self._logger.info(f"[LLM] 收到 result keys: {list(result.keys())}")
        self._logger.info(
            f"[LLM] success={result.get('success')}, stock_list={'stock_list' in result}, data_found={result.get('data_found')}"
        )

        # 延遲加載 prompt_manager（只在需要時加載）
        if self._prompt_manager is None:
            try:
                from .services.prompt_manager import PromptManager

                self._prompt_manager = PromptManager()
                self._logger.info("[LLM] PromptManager 加載成功")
            except Exception as e:
                self._logger.warning(f"無法加載 PromptManager: {e}")
                # 不 return，繼續使用手動格式

        # 1. 查無資料 - 生成「查無資料」業務回覆
        if result.get("data_found") is False:
            self._logger.info("[LLM] 生成查無資料回覆")
            if self._prompt_manager:
                try:
                    query_context = result.get("query_context", {})
                    nlq = query_context.get("nlq", user_instruction)

                    llm_response = await self._prompt_manager.generate_no_data_response(
                        query=nlq,
                        user_instruction=user_instruction,
                    )
                    result["response"] = llm_response
                    result["response_type"] = "no_data"
                except Exception as e:
                    self._logger.warning(f"LLM 生成查無資料回覆失敗: {e}")
                    result["response"] = f"抱歉，根據您的查詢條件「{user_instruction}」，系統中沒有找到符合的資料。"
                    result["response_type"] = "no_data_fallback"
            else:
                result["response"] = f"抱歉，根據您的查詢條件「{user_instruction}」，系統中沒有找到符合的資料。"
                result["response_type"] = "no_data_fallback"
            return result

        # 2. 需要回問確認 - 生成確認請求回覆
        if result.get("needs_clarification"):
            # 如果已經有 clarification_message（來自 _handle_clarification_needed 路徑），
            # 直接使用，不再透過 LLM 重寫（避免覆蓋結構化的澄清問題）
            if result.get("clarification_message") and result.get("response"):
                self._logger.info("[LLM] 跳過 LLM 重寫：已有結構化澄清問題")
                result["response_type"] = "clarification"
                return result

            clarification_type = result.get("clarification_type", "UNKNOWN")
            message = result.get("message", "需要確認")
            suggestions = result.get("suggestions", [])

            # Guard 攔截特殊處理：提取 clarification_needed 和 suggestion
            guard_type = result.get("guard_type", "")  # noqa: F841 - 保留用於日誌追蹤
            clarification_steps = result.get("clarification_needed", [])
            suggestion = result.get("suggestion", "")

            self._logger.info(f"[LLM] 生成確認回覆: {clarification_type}")
            if self._prompt_manager:
                try:
                    llm_response = await self._prompt_manager.generate_clarification_response(
                        clarification_type=clarification_type,
                        message=message,
                        suggestions=suggestions,
                        user_instruction=user_instruction,
                    )
                    result["response"] = llm_response
                    result["response_type"] = "clarification"
                except Exception as e:
                    self._logger.warning(f"LLM 生成確認回覆失敗: {e}")
                    clarification_msgs = {
                        "QUERY_SCOPE_TOO_LARGE": f"⚠️ {message}\n\n請提供更多篩選條件以縮小查詢範圍。",
                        "INTENT_UNCLEAR": f"⚠️ {message}\n\n請重新描述您的查詢需求。",
                    }
                    # Guard 攔截的 fallback 回覆
                    if clarification_type == "QUERY_GUARD_REJECTED" and clarification_steps:
                        steps_text = "\n".join(
                            f"  {i+1}. {step}" for i, step in enumerate(clarification_steps)
                        )
                        guard_response = f"⚠️ {message}\n\n建議步驟：\n{steps_text}"
                        if suggestion:
                            guard_response += f"\n\n💡 建議查詢：{suggestion}"
                        clarification_msgs["QUERY_GUARD_REJECTED"] = guard_response
                    result["response"] = clarification_msgs.get(clarification_type, f"⚠️ {message}")
                    result["response_type"] = "clarification_fallback"
            else:
                clarification_msgs = {
                    "QUERY_SCOPE_TOO_LARGE": f"⚠️ {message}\n\n請提供更多篩選條件以縮小查詢範圍。",
                    "INTENT_UNCLEAR": f"⚠️ {message}\n\n請重新描述您的查詢需求。",
                }
                # Guard 攔截的 fallback 回覆
                if clarification_type == "QUERY_GUARD_REJECTED" and clarification_steps:
                    steps_text = "\n".join(
                        f"  {i+1}. {step}" for i, step in enumerate(clarification_steps)
                    )
                    guard_response = f"⚠️ {message}\n\n建議步驟：\n{steps_text}"
                    if suggestion:
                        guard_response += f"\n\n💡 建議查詢：{suggestion}"
                    clarification_msgs["QUERY_GUARD_REJECTED"] = guard_response
                result["response"] = clarification_msgs.get(clarification_type, f"⚠️ {message}")
                result["response_type"] = "clarification_fallback"
            return result

        # 3. 執行錯誤 - 生成錯誤說明回覆
        if not result.get("success", True):
            error_type = result.get("error_type", "UNKNOWN_ERROR")
            message = result.get("message", "執行過程中發生錯誤")
            original_query = result.get("original_query", user_instruction)

            self._logger.info(f"[LLM] 生成錯誤回覆: {error_type}")
            if self._prompt_manager:
                try:
                    llm_response = await self._prompt_manager.generate_error_response(
                        error_type=error_type,
                        message=message,
                        original_query=original_query,
                    )
                    result["response"] = llm_response
                    result["response_type"] = "error"
                except Exception as e:
                    self._logger.warning(f"LLM 生成錯誤回覆失敗: {e}")
                    error_msgs = {
                        "SCHEMA_ERROR": f"❌ 資料庫結構錯誤：{message}",
                        "CONNECTION_ERROR": "❌ 連線錯誤：無法連接到資料庫服務，請稍後再試。",
                        "TIMEOUT": f"❌ 查詢超時：{message}",
                        "INTERNAL_ERROR": f"❌ 系統錯誤：{message}",
                        "SQL_GENERATION_ERROR": f"❌ SQL 生成失敗：{message}，請嘗試更明確的查詢條件。",
                        "SQL_SAFETY_ERROR": f"❌ 查詢安全檢查未通過：{message}",
                        "SQL_EXECUTION_ERROR": f"❌ SQL 執行失敗：{message}，請檢查查詢條件是否正確。",
                    }
                    result["response"] = error_msgs.get(error_type, f"❌ 錯誤：{message}")
                    result["response_type"] = "error_fallback"
            else:
                error_msgs = {
                    "SCHEMA_ERROR": f"❌ 資料庫結構錯誤：{message}",
                    "CONNECTION_ERROR": "❌ 連線錯誤：無法連接到資料庫服務，請稍後再試。",
                    "TIMEOUT": f"❌ 查詢超時：{message}",
                    "INTERNAL_ERROR": f"❌ 系統錯誤：{message}",
                    "SQL_GENERATION_ERROR": f"❌ SQL 生成失敗：{message}，請嘗試更明確的查詢條件。",
                    "SQL_SAFETY_ERROR": f"❌ 查詢安全檢查未通過：{message}",
                    "SQL_EXECUTION_ERROR": f"❌ SQL 執行失敗：{message}，請檢查查詢條件是否正確。",
                }
                result["response"] = error_msgs.get(error_type, f"❌ 錯誤：{message}")
                result["response_type"] = "error_fallback"
            return result
        # 4. 有資料 - 始終使用 LLM 生成業務回覆（無論是否有手動 response）
        # 檢查是否有嵌套的 result 結構
        inner_result = result.get("result", result)
        if inner_result.get("success") and inner_result.get("stock_list"):
            self._logger.info("[LLM] 生成庫存查詢回覆")
            if self._prompt_manager:
                try:
                    stock_list = inner_result.get("stock_list", [])
                    count = inner_result.get("count", 0)
                    warehouse = inner_result.get("query_context", {}).get("warehouse", "")

                    # 轉換數據格式：Data-Agent 返回 {warehouse_no, total} → prompt_manager 期望 {part_number, batch_no, quantity}
                    # 嘗試從多個來源獲取料號
                    query_context = inner_result.get("query_context", {})
                    part_number = query_context.get("part_number", "") or query_context.get(
                        "part_no", ""
                    )

                    # Fallback: 從 SQL 中提取料號
                    if not part_number:
                        sql = inner_result.get("sql", "")
                        if sql:
                            import re

                            sql_match = re.search(r"item_no\s*=\s*'([^']+)'", sql, re.IGNORECASE)
                            if sql_match:
                                part_number = sql_match.group(1)

                    converted_stock_list = []
                    for item in stock_list:
                        # DT-Agent 格式：保留所有原始欄位，額外加上 prompt_manager 所需的別名
                        # （DT-Agent SQL 可能只 SELECT 部分欄位）
                        if "existing_stocks" in item:
                            converted = dict(item)  # 保留所有原始欄位（ent, site, item_no, warehouse_no 等）
                            converted["part_number"] = item.get("item_no", part_number or "-")
                            converted["batch_no"] = item.get("warehouse_no", "-")
                            converted["quantity"] = item.get("existing_stocks", 0)
                            self._logger.info(f"[DEBUG] DT-Agent 格式轉換: {converted}")
                            converted_stock_list.append(converted)
                        # 舊格式 (warehouse_no, total)
                        elif "warehouse_no" in item and "total" in item:
                            qty = item.get("total", 0)
                            self._logger.info(
                                f"[DEBUG] 轉換: warehouse_no={item.get('warehouse_no')}, total={qty}"
                            )
                            converted_stock_list.append(
                                {
                                    "part_number": part_number or "-",
                                    "batch_no": "-",
                                    "quantity": qty,
                                }
                            )
                        else:
                            # 未知格式，直接使用
                            converted_stock_list.append(item)

                    self._logger.info(f"[DEBUG] converted_stock_list: {converted_stock_list}")

                    llm_response = await self._prompt_manager.generate_stock_response(
                        warehouse=warehouse or stock_list[0].get("warehouse_no", "未知倉庫")
                        if stock_list
                        else "未知倉庫",
                        stock_list=converted_stock_list,
                        count=count,
                        user_instruction=user_instruction,
                    )
                    inner_result["response"] = llm_response
                    inner_result["response_type"] = "llm_business"
                except Exception as e:
                    self._logger.warning(f"LLM 生成庫存查詢回覆失敗: {e}")
                    # 保留現有的手動格式
                    inner_result["response_type"] = "manual_fallback"
            else:
                inner_result["response_type"] = "manual_fallback"
            return result

        # 5. 已有 response（手動生成的），直接返回

        # 5. 已有 response（手動生成的），直接返回
        return result

    async def _query_stock_history(
        self,
        part_number: str,
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """查詢進料/交易歷史

        Args:
            part_number: 料號
            request: Agent服務請求

        Returns:
            交易歷史結果
        """
        try:
            user_id = request.metadata.get("user_id") if request.metadata else None

            # 查詢最近進貨記錄（tlf19=101）
            purchase_history = await self._stock_service.query_purchase(
                part_number=part_number,
                user_id=user_id,
            )

            transactions = purchase_history.get("transactions", [])
            count = purchase_history.get("count", 0)

            # 生成自然語言解釋
            if count == 0:
                explanation = f"料號 {part_number} 查無進料記錄。"
            else:
                explanation = f"料號 {part_number} 的最近進料記錄（共 {count} 筆）：\n\n"
                for i, trans in enumerate(transactions[:10], 1):
                    trans_date = trans.get("trans_date", "-")
                    quantity = trans.get("quantity", 0)
                    unit = trans.get("unit", "件")
                    warehouse = trans.get("warehouse", "-")
                    explanation += f"{i}. 日期：{trans_date}\n"
                    explanation += f"   數量：{quantity:,} {unit}\n"
                    explanation += f"   倉庫：{warehouse}\n\n"

                if count > 10:
                    explanation += f"... 還有 {count - 10} 筆更早的記錄"

            return {
                "success": True,
                "part_number": part_number,
                "purchase_history": purchase_history,
                "response": explanation,
            }
        except Exception as e:
            self._logger.error(f"查詢進料記錄失敗: {e}")
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
