# 代碼功能說明: Document Editing Agent v2.0 主類（支持審計日誌）
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Document Editing Agent v2.0 主類

實現 AgentServiceProtocol 接口，提供結構化文件編輯服務，支持模糊匹配、進階驗證和審計日誌。
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from agents.builtin.document_editing_v2.models import PatchResponse
from agents.core.editing_v2.audit_logger import AuditLogger
from agents.core.editing_v2.audit_models import AuditEventType
from agents.core.editing_v2.content_generator import ContentGenerator
from agents.core.editing_v2.context_assembler import ContextAssembler
from agents.core.editing_v2.error_handler import EditingError, ErrorHandler
from agents.core.editing_v2.intent_validator import IntentValidator
from agents.core.editing_v2.markdown_parser import MarkdownParser
from agents.core.editing_v2.patch_generator import PatchGenerator
from agents.core.editing_v2.target_locator import TargetLocator
from agents.core.editing_v2.validator_linter import ValidatorLinter
from agents.core.editing_v2.workspace_integration import WorkspaceIntegration
from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)

logger = logging.getLogger(__name__)


class DocumentEditingAgentV2(AgentServiceProtocol):
    """Document Editing Agent v2.0

    基於 Intent DSL 和 Block Patch 的結構化文件編輯 Agent。
    """

    def __init__(self, arango_client=None):
        """
        初始化 Document Editing Agent v2.0

        Args:
            arango_client: ArangoDB 客戶端（可選，用於審計日誌存儲）
        """
        self.agent_id = "md-editor"
        self.logger = logger
        self.error_handler = ErrorHandler()
        self.intent_validator = IntentValidator()
        self.workspace_integration = WorkspaceIntegration()
        self.audit_logger = AuditLogger(arango_client=arango_client)

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        執行文件編輯任務

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
            document_context = self.intent_validator.parse_document_context(document_context_data)
            edit_intent = self.intent_validator.parse_intent(edit_intent_data)

            # 記錄 Intent 接收事件
            self.audit_logger.log_event(
                event_type=AuditEventType.INTENT_RECEIVED,
                intent_id=edit_intent.intent_id,
                doc_id=document_context.doc_id,
                user_id=document_context.user_id,
                tenant_id=document_context.tenant_id,
            )

            # 存儲 Intent（不可變存儲）
            self.audit_logger.store_intent(
                intent_id=edit_intent.intent_id,
                doc_id=document_context.doc_id,
                intent_data=edit_intent_data,
            )

            # 記錄 Intent 驗證事件
            validation_start = time.time()
            # 驗證已在 parse_intent 中完成，這裡記錄事件
            validation_duration = time.time() - validation_start
            self.audit_logger.log_event(
                event_type=AuditEventType.INTENT_VALIDATED,
                intent_id=edit_intent.intent_id,
                doc_id=document_context.doc_id,
                duration=validation_duration,
            )

            # 讀取文件內容（使用 WorkspaceIntegration）
            # 從 DocumentContext 中提取 file_id（從 file_path 中提取）
            file_id = self._extract_file_id_from_path(document_context.file_path)
            file_content = self.workspace_integration.get_file_content(
                file_id=file_id, task_id=document_context.task_id
            )
            if file_content is None:
                return AgentServiceResponse(
                    task_id=request.task_id,
                    status="error",
                    result=None,
                    error=f"Failed to read file: {document_context.file_path}",
                    metadata=request.metadata,
                )

            # 解析 Markdown
            parser = MarkdownParser()
            parser.parse(file_content)

            # 定位目標 Block
            target_locator = TargetLocator(parser)
            locate_start = time.time()
            target_block = target_locator.locate(edit_intent.target_selector)
            locate_duration = time.time() - locate_start

            # 記錄目標定位事件
            self.audit_logger.log_event(
                event_type=AuditEventType.TARGET_LOCATED,
                intent_id=edit_intent.intent_id,
                doc_id=document_context.doc_id,
                duration=locate_duration,
                metadata={"target_selector": edit_intent.target_selector.model_dump()},
            )

            # 裝配上下文
            context_assembler = ContextAssembler(parser)
            context_start = time.time()
            context_blocks = context_assembler.assemble_context(target_block)
            context_text = context_assembler.format_context_for_llm(context_blocks)
            context_digest = context_assembler.compute_context_digest(context_blocks)
            context_duration = time.time() - context_start

            # 記錄上下文裝配事件
            self.audit_logger.log_event(
                event_type=AuditEventType.CONTEXT_ASSEMBLED,
                intent_id=edit_intent.intent_id,
                doc_id=document_context.doc_id,
                duration=context_duration,
                metadata={"context_digest": context_digest},
            )

            # 生成內容（如果需要）
            new_content = None
            if edit_intent.action.mode in ["insert", "update"]:
                content_generator = ContentGenerator()
                generate_start = time.time()
                new_content = await content_generator.generate_content(
                    target_block=target_block,
                    action=edit_intent.action,
                    context_blocks=context_blocks,
                    context_text=context_text,
                )
                generate_duration = time.time() - generate_start

                # 記錄內容生成事件
                self.audit_logger.log_event(
                    event_type=AuditEventType.CONTENT_GENERATED,
                    intent_id=edit_intent.intent_id,
                    doc_id=document_context.doc_id,
                    duration=generate_duration,
                )

                # 驗證生成內容
                validator = ValidatorLinter(
                    parser,
                    original_content=target_block.content if target_block else None,
                    context_content=context_text,
                )
                validation_start = time.time()
                try:
                    validator.validate(new_content, edit_intent.constraints)
                    validation_duration = time.time() - validation_start

                    # 記錄驗證通過事件
                    self.audit_logger.log_event(
                        event_type=AuditEventType.VALIDATION_PASSED,
                        intent_id=edit_intent.intent_id,
                        doc_id=document_context.doc_id,
                        duration=validation_duration,
                    )
                except EditingError as e:
                    validation_duration = time.time() - validation_start

                    # 記錄驗證失敗事件
                    self.audit_logger.log_event(
                        event_type=AuditEventType.VALIDATION_FAILED,
                        intent_id=edit_intent.intent_id,
                        doc_id=document_context.doc_id,
                        duration=validation_duration,
                        metadata={"error": e.to_dict()},
                    )
                    raise

            # 生成 Patch
            patch_generator = PatchGenerator(parser)
            patch_start = time.time()
            block_patch = patch_generator.generate_block_patch(
                target_block=target_block,
                action=edit_intent.action,
                new_content=new_content,
            )

            # 生成 Text Patch
            text_patch = patch_generator.generate_text_patch(file_content, block_patch)
            patch_duration = time.time() - patch_start

            # 構建響應
            patch_id = str(uuid4())

            # 存儲 Patch（不可變存儲）
            self.audit_logger.store_patch(
                patch_id=patch_id,
                intent_id=edit_intent.intent_id,
                doc_id=document_context.doc_id,
                block_patch=block_patch,
                text_patch=text_patch,
            )

            # 記錄 Patch 生成事件
            self.audit_logger.log_event(
                event_type=AuditEventType.PATCH_GENERATED,
                intent_id=edit_intent.intent_id,
                patch_id=patch_id,
                doc_id=document_context.doc_id,
                duration=patch_duration,
            )

            patch_response = PatchResponse(
                patch_id=patch_id,
                intent_id=edit_intent.intent_id,
                block_patch=block_patch,
                text_patch=text_patch,
                preview=new_content,
                audit_info={
                    "model_version": "gpt-4-turbo-preview-2026-01-09",
                    "context_digest": context_digest,
                    "generated_at": datetime.utcnow().isoformat(),
                    "generated_by": "md-editor-v2.0",
                },
            )

            result = patch_response.model_dump()

            self.logger.info(
                f"Document editing completed: task_id={request.task_id}, "
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
                f"Document editing error: task_id={request.task_id}, error={e.code}, message={e.message}",
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
                f"Document editing failed: task_id={request.task_id}, error={str(e)}",
                exc_info=True,
            )
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,
                error=str(e),
                metadata=request.metadata,
            )

    def _extract_file_id_from_path(self, file_path: str) -> str:
        """
        從文件路徑中提取 file_id

        Args:
            file_path: 文件路徑（格式：data/tasks/{task_id}/workspace/{file_id}.md）

        Returns:
            文件 ID
        """
        # 從路徑中提取文件名（不含擴展名）
        # 例如：data/tasks/{task_id}/workspace/{file_id}.md -> {file_id}
        from pathlib import Path

        path_obj = Path(file_path)
        return path_obj.stem  # 獲取不含擴展名的文件名

    async def health_check(self) -> AgentServiceStatus:
        """
        健康檢查

        Returns:
            服務狀態
        """
        try:
            # 檢查依賴是否可用
            return AgentServiceStatus.AVAILABLE
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
            "name": "Markdown Editor Agent (v2.0)",
            "description": "基於 Intent DSL 和 Block Patch 的結構化 Markdown 文件編輯服務",
            "capabilities": [
                "document_editing",
                "markdown_editing",
                "structured_editing",
                "block_patch",
            ],
            "version": "2.0.0",
            "agent_id": self.agent_id,
            "agent_type": "document_editing",
        }
