from __future__ import annotations
# 代碼功能說明: FileUploadAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""FileUploadAgent實現 - 負責文件上傳和驗證LangGraph節點"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class FileUploadResult:
    """文件上傳結果"""
    files_uploaded: int
    files_validated: int
    files_stored: bool
    upload_success: bool
    total_size: int
    processing_triggered: bool
    uploaded_files: List[Dict[str, Any]] = field(default_factory=list) 
    validation_errors: List[str] = field(default_factory=list) 
    reasoning: str = ""


class FileUploadAgent(BaseAgentNode):
    """文件上傳Agent - 負責接收、驗證並初步存儲用戶上傳的文件"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化上傳服務
        self.upload_service = None
        self._initialize_services()

    def _initialize_services(self) -> None:
        """初始化上傳相關服務"""
        try:
            # 從系統服務中獲取文件上傳服務
            from services.api.services.file_metadata_service import FileMetadataService

            self.upload_service = FileMetadataService()
            logger.info("FileMetadataService initialized for FileUploadAgent")
        except Exception as e:
            logger.error(f"Failed to initialize FileMetadataService: {e}")
            self.upload_service = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行文件上傳和驗證
        """
        try:
            # 獲取要上傳的文件
            files = self._extract_files_from_state(state)
            if not files:
                return NodeResult.success(data={"message": "No files to upload"})

            # 執行文件上傳
            upload_result = await self._process_uploads(files, state)

            if not upload_result:
                return NodeResult.failure("File upload failed")

            # 更新狀態
            state.file_ids.extend(
                [f.get("file_id") for f in upload_result.uploaded_files if f.get("file_id")]
            )

            # 記錄觀察
            state.add_observation(
                "file_upload_completed",
                {
                    "files_uploaded": upload_result.files_uploaded,
                    "upload_success": upload_result.upload_success,
                },
                1.0 if upload_result.upload_success else 0.0,
            )

            logger.info(f"File upload completed: {upload_result.files_uploaded} files")

            return NodeResult.success(
                data={
                    "file_upload": {
                        "files_uploaded": upload_result.files_uploaded,
                        "upload_success": upload_result.upload_success,
                        "uploaded_files": upload_result.uploaded_files,
                        "reasoning": upload_result.reasoning,
                    },
                    "upload_summary": self._create_upload_summary(upload_result),
                },
                next_layer="resource_check",
            )

        except Exception as e:
            logger.error(f"FileUploadAgent execution error: {e}")
            return NodeResult.failure(f"File upload error: {e}")

    def _extract_files_from_state(self, state: AIBoxState) -> List[Dict[str, Any]]:
        """從狀態中提取要上傳的文件"""
        return []

    async def _process_uploads(
        self, files: List[Dict[str, Any]], state: AIBoxState,
    ) -> Optional[FileUploadResult]:
        """處理文件上傳"""
        return FileUploadResult(
            files_uploaded=len(files),
            files_validated=len(files),
            files_stored=True,
            upload_success=True,
            total_size=0,
            processing_triggered=True,
            uploaded_files=[],
            reasoning="Simulated upload success.",
        )

    def _create_upload_summary(self, upload_result: FileUploadResult) -> Dict[str, Any]:
        return {
            "uploaded": upload_result.files_uploaded,
            "success": upload_result.upload_success,
        }


def create_file_upload_agent_config() -> NodeConfig:
    return NodeConfig(
        name="FileUploadAgent",
        description="文件上傳Agent - 負責接收、驗證並初步存儲用戶上傳的文件",
        max_retries=1,
        timeout=60.0,
        required_inputs=["user_id"],
        optional_inputs=["messages"],
        output_keys=["file_ids", "upload_summary"],
    )


def create_file_upload_agent() -> FileUploadAgent:
    config = create_file_upload_agent_config()
    return FileUploadAgent(config)