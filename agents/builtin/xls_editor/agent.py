# 代碼功能說明: Excel 編輯器 Agent 主類
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Excel 編輯器 Agent 主類

實現 AgentServiceProtocol 接口，提供結構化 Excel 文件編輯服務。
"""

import logging
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from agents.builtin.xls_editor.models import ExcelPatchResponse
from agents.core.editing_v2.error_handler import EditingError, ErrorHandler
from agents.core.editing_v2.excel_intent_validator import ExcelIntentValidator
from agents.core.editing_v2.excel_parser import ExcelParser
from agents.core.editing_v2.excel_patch_generator import ExcelPatchGenerator
from agents.core.editing_v2.excel_target_locator import ExcelTargetLocator
from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)

logger = logging.getLogger(__name__)


class XlsEditingAgent(AgentServiceProtocol):
    """Excel 編輯器 Agent

    基於 Intent DSL 和 Structured Patch 的結構化 Excel 文件編輯 Agent。
    """

    def __init__(self):
        """初始化 Excel 編輯器 Agent"""
        self.agent_id = "xls-editor"
        self.logger = logger
        self.error_handler = ErrorHandler()
        self.intent_validator = ExcelIntentValidator()

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        執行 Excel 文件編輯任務

        Args:
            request: Agent 服務請求

        Returns:
            Agent 服務響應
        """
        try:
            # 從 task_data 中提取參數
            task_data = request.task_data
            document_context_data = task_data.get("document_context", {})
            edit_intent_data = task_data.get("edit_intent", {})

            if not document_context_data:
                return AgentServiceResponse(
                    task_id=request.task_id,
                    status="error",
                    result=None,
                    error="Missing required parameter: document_context",
                    metadata=request.metadata,
                )

            if not edit_intent_data:
                return AgentServiceResponse(
                    task_id=request.task_id,
                    status="error",
                    result=None,
                    error="Missing required parameter: edit_intent",
                    metadata=request.metadata,
                )

            # 解析和驗證輸入
            document_context = self.parse_document_context(document_context_data)
            edit_intent = self.intent_validator.parse_intent(edit_intent_data)

            # 讀取 Excel 文件
            file_path = document_context.file_path
            excel_parser = ExcelParser()
            excel_parser.load(file_path)

            # 定位目標
            target_locator = ExcelTargetLocator(excel_parser)
            target_info = target_locator.locate(edit_intent.target_selector)

            # 驗證約束（max_cells 檢查）
            if edit_intent.constraints and edit_intent.constraints.max_cells:
                # 計算受影響的單元格數（簡化實現）
                affected_cells = 1  # 默認值，實際應該根據操作計算
                if affected_cells > edit_intent.constraints.max_cells:
                    raise EditingError(
                        code="VALIDATION_FAILED",
                        message=f"受影響的單元格數 ({affected_cells}) 超過最大限制 ({edit_intent.constraints.max_cells})",
                    )

            # 生成 Patch
            patch_generator = ExcelPatchGenerator(excel_parser)
            structured_patch = patch_generator.generate_patch(edit_intent, target_info)

            # 構建響應
            patch_id = str(uuid4())
            patch_response = ExcelPatchResponse(
                patch_id=patch_id,
                intent_id=edit_intent.intent_id,
                structured_patch=structured_patch,
                preview=target_info,
                audit_info={
                    "model_version": "xls-editor-v2.0",
                    "generated_at": datetime.utcnow().isoformat(),
                    "generated_by": "xls-editor-v2.0",
                },
            )

            result = patch_response.model_dump()

            self.logger.info(
                f"Excel editing completed: task_id={request.task_id}, "
                f"intent_id={edit_intent.intent_id}, patch_id={patch_id}"
            )

            return AgentServiceResponse(
                task_id=request.task_id,
                status="completed",
                result=result,
                error=None,
                metadata=request.metadata,
            )

        except EditingError as e:
            self.logger.error(
                f"Excel editing error: task_id={request.task_id}, error={e.code}, message={e.message}",
                exc_info=True,
            )
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,
                error=e.message,
                metadata={**(request.metadata or {}), **{"error_details": e.to_dict()}},
            )

        except Exception as e:
            self.logger.error(
                f"Excel editing failed: task_id={request.task_id}, error={str(e)}",
                exc_info=True,
            )
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,
                error=str(e),
                metadata=request.metadata,
            )

    def parse_document_context(self, context_data: Dict[str, Any]) -> Any:
        """
        解析 DocumentContext（臨時實現，應該使用統一的模型）

        Args:
            context_data: DocumentContext 數據

        Returns:
            DocumentContext 對象
        """
        from agents.builtin.document_editing_v2.models import DocumentContext

        return DocumentContext(**context_data)

    async def health_check(self) -> AgentServiceStatus:
        """
        健康檢查

        Returns:
            服務狀態
        """
        try:
            # 檢查 openpyxl 是否可用
            try:
                import openpyxl  # noqa: F401

                return AgentServiceStatus.AVAILABLE
            except ImportError:
                return AgentServiceStatus.ERROR
        except Exception as e:
            self.logger.error(f"Health check failed: {e}", exc_info=True)
            return AgentServiceStatus.ERROR

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        獲取服務能力

        Returns:
            服務能力描述
        """
        return {
            "name": "Excel Editor Agent (v2.0)",
            "description": "基於 Intent DSL 和 Structured Patch 的結構化 Excel 文件編輯服務",
            "capabilities": [
                "document_editing",
                "excel_editing",
                "structured_editing",
                "structured_patch",
            ],
            "version": "2.0.0",
            "agent_id": self.agent_id,
            "agent_type": "document_editing",
        }
