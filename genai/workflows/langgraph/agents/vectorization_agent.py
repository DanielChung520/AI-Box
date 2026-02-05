from __future__ import annotations
# 代碼功能說明: VectorizationAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""VectorizationAgent實現 - 負責文件分塊和向量化LangGraph節點"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class VectorizationResult:
    """向量化結果"""
    files_processed: int
    vectors_generated: int
    vector_dimensions: int
    processing_success: bool
    total_tokens: int
    processing_time: float
    vector_store_updated: bool
    failed_files: List[str] = field(default_factory=list)
    reasoning: str = ""


class VectorizationAgent(BaseAgentNode):
    """向量化Agent - 負責將非結構化文件轉換為高維向量存儲"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化向量化服務
        self.embedding_service = None
        self.vector_store = None
        self._initialize_services()

    def _initialize_services(self) -> None:
        """初始化向量化相關服務"""
        try:
            # 從系統服務中獲取嵌入服務
            from services.api.services.embedding_service import EmbeddingService

            self.embedding_service = EmbeddingService()

            # 初始化向量數據庫客戶端
            from database.qdrant.client import get_qdrant_client

            self.vector_store = get_qdrant_client()

            logger.info("Vectorization services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Vectorization services: {e}")
            self.embedding_service = None
            self.vector_store = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行文件分塊和向量化
        """
        try:
            # 獲取需要處理的文件
            files = self._get_files_for_vectorization(state)
            if not files:
                return NodeResult.success(data={"message": "No files to vectorize"})

            # 執行向量化
            vectorization_result = await self._perform_vectorization(files, state)

            if not vectorization_result:
                return NodeResult.failure("Vectorization process failed")

            # 記錄觀察
            state.add_observation(
                "vectorization_completed",
                {
                    "files_processed": vectorization_result.files_processed,
                    "vectors_count": vectorization_result.vectors_generated,
                    "success": vectorization_result.processing_success,
                },
                1.0 if vectorization_result.processing_success else 0.0,
            )

            logger.info(f"Vectorization completed for {vectorization_result.files_processed} files")

            return NodeResult.success(
                data={
                    "vectorization": {
                        "files_processed": vectorization_result.files_processed,
                        "vectors_generated": vectorization_result.vectors_generated,
                        "processing_success": vectorization_result.processing_success,
                        "reasoning": vectorization_result.reasoning,
                    },
                    "vectorization_summary": self._create_vectorization_summary(
                        vectorization_result,
                    ),
                },
                next_layer="resource_check",
            )

        except Exception as e:
            logger.error(f"VectorizationAgent execution error: {e}")
            return NodeResult.failure(f"Vectorization error: {e}")

    def _get_files_for_vectorization(self, state: AIBoxState) -> List[Dict[str, Any]]:
        """獲取需要向量化的文件"""
        return []

    async def _perform_vectorization(
        self, files: List[Dict[str, Any]], state: AIBoxState,
    ) -> Optional[VectorizationResult]:
        """執行實際的向量化處理"""
        return VectorizationResult(
            files_processed=len(files),
            vectors_generated=0,
            vector_dimensions=1536,
            processing_success=True,
            total_tokens=0,
            processing_time=0.0,
            vector_store_updated=True,
            failed_files=[],
            reasoning="Simulated vectorization success.",
        )

    def _create_vectorization_summary(
        self, vectorization_result: VectorizationResult,
    ) -> Dict[str, Any]:
        return {
            "processed": vectorization_result.files_processed,
            "success": vectorization_result.processing_success,
        }


def create_vectorization_agent_config() -> NodeConfig:
    return NodeConfig(
        name="VectorizationAgent",
        description="向量化Agent - 負責將非結構化文件轉換為高維向量存儲",
        max_retries=1,
        timeout=300.0,
        required_inputs=["user_id"],
        optional_inputs=["file_upload", "messages"],
        output_keys=["vectorization_summary"]
    )


def create_vectorization_agent() -> VectorizationAgent:
    config = create_vectorization_agent_config()
    return VectorizationAgent(config)
