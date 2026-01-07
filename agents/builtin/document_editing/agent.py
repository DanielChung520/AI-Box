# 代碼功能說明: Document Editing Agent 核心實現
# 創建日期: 2026-01-06
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-06

"""Document Editing Agent - 文件編輯專用 Agent

實現文件編輯服務，支持 Markdown 文件的 AI 驅動編輯。
"""

import logging
from typing import Any, Dict, Optional

from agents.core.execution.document_editing_service import DocumentEditingService
from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)
from services.api.services.file_metadata_service import FileMetadataService
from storage.file_storage import create_storage_from_config
from system.infra.config.config import get_config_section

logger = logging.getLogger(__name__)


class DocumentEditingAgent(AgentServiceProtocol):
    """Document Editing Agent - 文件編輯專用 Agent

    提供文件編輯服務，支持：
    - Markdown 文件編輯
    - Search-and-Replace 協議
    - 流式編輯輸出
    """

    def __init__(self):
        """初始化 Document Editing Agent"""
        self.agent_id = "document-editing-agent"
        self.editing_service = DocumentEditingService()
        self.logger = logger

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        執行文件編輯任務

        Args:
            request: Agent 服務請求

        Returns:
            Agent 服務響應
        """
        try:
            # 從 task_data 中提取編輯請求參數
            task_data = request.task_data
            command = task_data.get("command", "")
            doc_id = task_data.get("doc_id", "")
            cursor_context = task_data.get("cursor_context", {})
            doc_format = task_data.get("format", "md")

            if not command:
                return AgentServiceResponse(
                    task_id=request.task_id,
                    status="error",
                    result=None,
                    error="Missing required parameter: command",
                    metadata=request.metadata,
                )

            if not doc_id:
                return AgentServiceResponse(
                    task_id=request.task_id,
                    status="error",
                    result=None,
                    error="Missing required parameter: doc_id",
                    metadata=request.metadata,
                )

            # 獲取文件內容
            file_content = await self._get_file_content(doc_id)
            if file_content is None:
                return AgentServiceResponse(
                    task_id=request.task_id,
                    status="error",
                    result=None,
                    error=f"Failed to read file content: {doc_id}",
                    metadata=request.metadata,
                )

            # 提取游標位置（如果提供）
            cursor_position = None
            if cursor_context:
                cursor_position = cursor_context.get("position") or cursor_context.get("line")

            # 調用 DocumentEditingService 生成 patches
            (
                patch_kind,
                patch_payload,
                summary,
            ) = await self.editing_service.generate_editing_patches(
                instruction=command,
                file_content=file_content,
                doc_format=doc_format,
                cursor_position=cursor_position,
            )

            # 修改時間：2026-01-06 - 驗證並規範化 patch_payload 格式
            # 確保 patch_payload 包含正確的 Search-and-Replace 格式
            if patch_kind == "search_replace":
                if not isinstance(patch_payload, dict):
                    self.logger.warning(
                        f"Invalid patch_payload type for search_replace: {type(patch_payload)}"
                    )
                    patch_payload = {"patches": []}
                elif "patches" not in patch_payload:
                    self.logger.warning("patch_payload missing 'patches' key")
                    patch_payload = {"patches": []}
                elif not isinstance(patch_payload.get("patches"), list):
                    self.logger.warning("patch_payload.patches is not a list")
                    patch_payload = {"patches": []}
                else:
                    # 驗證每個 patch 的格式
                    valid_patches = []
                    for patch in patch_payload.get("patches", []):
                        if (
                            isinstance(patch, dict)
                            and "search_block" in patch
                            and "replace_block" in patch
                        ):
                            valid_patches.append(
                                {
                                    "search_block": str(patch["search_block"]),
                                    "replace_block": str(patch["replace_block"]),
                                }
                            )
                        else:
                            patch_keys = list(patch.keys()) if isinstance(patch, dict) else None
                            self.logger.warning(
                                f"Invalid patch format: {patch}, patch_keys: {patch_keys}",
                            )
                    patch_payload = {"patches": valid_patches}
                    if not valid_patches:
                        self.logger.warning("No valid patches found after validation")

            # 構建響應結果
            result = {
                "patch_kind": patch_kind,
                "patch_payload": patch_payload,
                "summary": summary or "",
                "doc_id": doc_id,
                "format": doc_format,
            }

            # 修改時間：2026-01-06 - 添加詳細的日誌記錄
            patch_count = 0
            if patch_kind == "search_replace" and isinstance(patch_payload, dict):
                patch_count = len(patch_payload.get("patches", []))

            self.logger.info(
                f"Document editing completed: task_id={request.task_id}, "
                f"doc_id={doc_id}, patch_kind={patch_kind}, patch_count={patch_count}"
            )

            return AgentServiceResponse(
                task_id=request.task_id,
                status="completed",
                result=result,
                error=None,
                metadata=request.metadata,
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

    async def _get_file_content(self, file_id: str) -> Optional[str]:
        """
        獲取文件內容

        Args:
            file_id: 文件 ID

        Returns:
            文件內容字符串，如果失敗返回 None
        """
        try:
            # 獲取文件元數據
            metadata_service = FileMetadataService()
            file_metadata = metadata_service.get(file_id)
            if not file_metadata or not file_metadata.storage_path:
                self.logger.warning(f"File not found: {file_id}")
                return None

            # 讀取文件內容
            config = get_config_section("file_upload", default={}) or {}
            storage = create_storage_from_config(config)
            content = storage.read_file(
                file_id=file_id,
                metadata_storage_path=file_metadata.storage_path,
            )
            if content is None:
                self.logger.warning(f"Failed to read file: {file_metadata.storage_path}")
                return None

            # 解碼為字符串
            if isinstance(content, bytes):
                return content.decode("utf-8")
            return str(content)

        except Exception as e:
            self.logger.error(f"Error reading file {file_id}: {e}", exc_info=True)
            return None

    async def health_check(self) -> AgentServiceStatus:
        """
        健康檢查

        Returns:
            服務狀態
        """
        try:
            # 檢查 editing_service 是否可用
            if self.editing_service is None:
                return AgentServiceStatus.UNAVAILABLE
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
            "name": "Document Editing Agent",
            "description": "文件編輯服務，支持 Markdown 文件的 AI 驅動編輯",
            "capabilities": [
                "document_editing",
                "file_editing",
                "markdown_editing",
                "streaming_editing",
            ],
            "version": "1.0.0",
            "agent_id": self.agent_id,
            "agent_type": "document_editing",
        }
