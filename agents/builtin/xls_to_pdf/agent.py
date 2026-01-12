# 代碼功能說明: Excel 轉 PDF Agent 主類
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Excel 轉 PDF Agent 主類

實現 AgentServiceProtocol 接口，提供 Excel 到 PDF 的轉換服務。
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from agents.builtin.xls_to_pdf.excel_pdf_converter import ExcelPdfConverter
from agents.builtin.xls_to_pdf.models import ExcelConversionConfig, ExcelConversionResponse
from agents.core.editing_v2.workspace_integration import WorkspaceIntegration
from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)

logger = logging.getLogger(__name__)


class XlsToPdfAgent(AgentServiceProtocol):
    """Excel 轉 PDF Agent

    提供 Excel 到 PDF 的轉換服務。
    """

    def __init__(self):
        """初始化 Excel 轉 PDF Agent"""
        self.agent_id = "xls-to-pdf"
        self.logger = logger
        self._converter = None
        self.workspace_integration = WorkspaceIntegration()

    def _get_converter(self):
        """獲取轉換器（延遲初始化）"""
        if self._converter is None:
            self._converter = ExcelPdfConverter()
        return self._converter

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        執行 Excel 轉 PDF 任務

        Args:
            request: Agent 服務請求

        Returns:
            Agent 服務響應
        """
        try:
            task_data = request.task_data
            document_context_data = task_data.get("document_context", {})
            conversion_config_data = task_data.get("conversion_config", {})

            if not document_context_data or not conversion_config_data:
                return AgentServiceResponse(
                    task_id=request.task_id,
                    status="error",
                    result=None,
                    error="Missing required parameters",
                    metadata=request.metadata,
                )

            conversion_config = ExcelConversionConfig(**conversion_config_data)
            file_path = document_context_data.get("file_path")

            if not file_path or not os.path.exists(file_path):
                return AgentServiceResponse(
                    task_id=request.task_id,
                    status="error",
                    result=None,
                    error=f"File not found: {file_path}",
                    metadata=request.metadata,
                )

            task_id = document_context_data.get("task_id", "unknown")
            user_id = document_context_data.get("user_id", "unknown")

            # 確保任務工作區存在
            self.workspace_integration.ensure_workspace_exists(task_id, user_id)

            # 生成輸出文件路徑
            output_file_id = str(uuid4())
            output_file_path = self.workspace_integration.generate_file_path(
                task_id, output_file_id, "pdf"
            )

            # 確保目錄存在
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

            success = self._get_converter().convert(
                file_path, output_file_path, conversion_config.options
            )

            if not success:
                return AgentServiceResponse(
                    task_id=request.task_id,
                    status="error",
                    result=None,
                    error="PDF conversion failed",
                    metadata=request.metadata,
                )

            # 創建文件元數據
            file_metadata = self.workspace_integration.create_file_from_path(
                task_id=task_id,
                user_id=user_id,
                file_name=conversion_config.output_file_name,
                source_file_path=output_file_path,
                file_format="pdf",
                file_id=output_file_id,
            )

            conversion_response = ExcelConversionResponse(
                conversion_id=conversion_config.conversion_id,
                source_doc_id=document_context_data.get("doc_id", ""),
                output_doc_id=output_file_id,
                output_file_path=output_file_path,
                status="success",
                message="PDF conversion completed successfully",
                metadata={
                    "file_size": file_metadata.file_size,
                },
                audit_info={
                    "converted_at": datetime.utcnow().isoformat(),
                    "converted_by": "xls-to-pdf-v2.0",
                    "tool_version": "openpyxl+reportlab",
                },
            )

            return AgentServiceResponse(
                task_id=request.task_id,
                status="completed",
                result=conversion_response.model_dump(),
                error=None,
                metadata=request.metadata,
            )

        except Exception as e:
            self.logger.error(f"Excel to PDF conversion failed: {e}", exc_info=True)
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,
                error=str(e),
                metadata=request.metadata,
            )

    async def health_check(self) -> AgentServiceStatus:
        """健康檢查"""
        try:
            return AgentServiceStatus.AVAILABLE
        except Exception:
            return AgentServiceStatus.ERROR

    async def get_capabilities(self) -> Dict[str, Any]:
        """獲取服務能力"""
        return {
            "name": "Excel to PDF Agent (v2.0)",
            "description": "將 Excel 文件轉換為 PDF 文件",
            "capabilities": ["document_conversion", "excel_to_pdf", "pdf_generation"],
            "version": "2.0.0",
            "agent_id": self.agent_id,
            "agent_type": "document_conversion",
        }
