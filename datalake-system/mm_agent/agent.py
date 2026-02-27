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

        # JP endpoint 直接調用
        self._jp_endpoint = (
            os.getenv("DATA_AGENT_SERVICE_URL", "http://localhost:8004")
            + "/api/v1/data-agent/jp/execute"
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
            return await self._query_stock_info(parameters, request)

        elif responsibility_type == "query_stock_history":
            part_number = parameters.get("part_number")
            if not part_number:
                return {
                    "success": False,
                    "error": "缺少料號參數（part_number）",
                }
            return await self._query_stock_history(part_number, request)

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
            # 生成澄清問題的自然語言解釋
            questions = responsibility.clarification_questions or []
            if questions:
                explanation = questions[0] + "\n"
                for q in questions[1:]:
                    explanation += q + "\n"
            else:
                explanation = "您的指令不夠明確，請提供更多細節。"

            return {
                "success": False,
                "error": "需要澄清用戶意圖",
                "clarification_questions": questions,
                "response": explanation.strip(),
            }

        else:
            return {
                "success": False,
                "error": f"未知的職責類型: {responsibility_type}",
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
    ) -> Dict[str, Any]:
        """查詢庫存信息

        使用 Data-Agent-JP 的 /jp/execute 端點處理庫存查詢。
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
            self._logger.info(f"[Agent] 查詢庫存，參數: {parameters}")

            # 構建自然語言查詢
            nlq = parameters.get("nlq", "")
            if not nlq:
                # 從參數構建查詢
                part_no = parameters.get("part_number", "")
                warehouse = parameters.get("warehouse", "")
                if part_no:
                    nlq = f"查詢料號 {part_no} 的庫存"
                elif warehouse:
                    nlq = f"查詢 {warehouse} 倉庫的庫存"
                else:
                    nlq = "查詢所有庫存"

            # 使用新的 /jp/execute 端點 (schema_driven_query)
            payload = {
                "task_id": f"mm-agent-{request.task_id}",
                "task_type": "schema_driven_query",
                "task_data": {"nlq": nlq},
            }

            # 使用同步 client
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(self._jp_endpoint, json=payload)
                result = resp.json()

            self._logger.info(f"[Agent] JP response: {result.get('status')}")

            # ============================================================
            # 處理 Data-Agent 結構化響應
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

            warnings = result.get("warnings", [])

            # 判斷錯誤類型
            error_codes = [e.get("code", "") for e in errors]
            error_messages = [e.get("message", "") for e in errors]

            # 1. 查無資料 (NO_DATA_FOUND) - 交由 LLM 業務回覆
            if result.get("status") == "success":
                data_result = result.get("result", {})
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
                "message": "無法連接到 Data-Agent 服務，請確認服務是否正常運行",
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
        if result.get("data_found") == False:
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
                    result["response"] = (
                        f"抱歉，根據您的查詢條件「{user_instruction}」，系統中沒有找到符合的資料。"
                    )
                    result["response_type"] = "no_data_fallback"
            else:
                result["response"] = (
                    f"抱歉，根據您的查詢條件「{user_instruction}」，系統中沒有找到符合的資料。"
                )
                result["response_type"] = "no_data_fallback"
            return result

        # 2. 需要回問確認 - 生成確認請求回覆
        if result.get("needs_clarification"):
            clarification_type = result.get("clarification_type", "UNKNOWN")
            message = result.get("message", "需要確認")
            suggestions = result.get("suggestions", [])

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
                    result["response"] = clarification_msgs.get(clarification_type, f"⚠️ {message}")
                    result["response_type"] = "clarification_fallback"
            else:
                clarification_msgs = {
                    "QUERY_SCOPE_TOO_LARGE": f"⚠️ {message}\n\n請提供更多篩選條件以縮小查詢範圍。",
                    "INTENT_UNCLEAR": f"⚠️ {message}\n\n請重新描述您的查詢需求。",
                }
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
                        "CONNECTION_ERROR": f"❌ 連線錯誤：無法連接到資料庫服務，請稍後再試。",
                        "TIMEOUT": f"❌ 查詢超時：{message}",
                        "INTERNAL_ERROR": f"❌ 系統錯誤：{message}",
                    }
                    result["response"] = error_msgs.get(error_type, f"❌ 錯誤：{message}")
                    result["response_type"] = "error_fallback"
            else:
                error_msgs = {
                    "SCHEMA_ERROR": f"❌ 資料庫結構錯誤：{message}",
                    "CONNECTION_ERROR": f"❌ 連線錯誤：無法連接到資料庫服務，請稍後再試。",
                    "TIMEOUT": f"❌ 查詢超時：{message}",
                    "INTERNAL_ERROR": f"❌ 系統錯誤：{message}",
                }
                result["response"] = error_msgs.get(error_type, f"❌ 錯誤：{message}")
                result["response_type"] = "error_fallback"
            return result

        # 4. 有資料 - 始終使用 LLM 生成業務回覆（無論是否有手動 response）
        if result.get("success") and result.get("stock_list"):
            self._logger.info("[LLM] 生成庫存查詢回覆")
            if self._prompt_manager:
                try:
                    stock_list = result.get("stock_list", [])
                    count = result.get("count", 0)
                    warehouse = result.get("query_context", {}).get("warehouse", "")

                    llm_response = await self._prompt_manager.generate_stock_response(
                        warehouse=warehouse or "未知倉庫",
                        stock_list=stock_list,
                        count=count,
                        user_instruction=user_instruction,
                    )
                    result["response"] = llm_response
                    result["response_type"] = "llm_business"
                except Exception as e:
                    self._logger.warning(f"LLM 生成庫存回覆失敗: {e}")
                    # 保留現有的手動格式
                    result["response_type"] = "manual_fallback"
            else:
                result["response_type"] = "manual_fallback"
            return result

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
