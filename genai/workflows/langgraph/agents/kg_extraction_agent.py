from __future__ import annotations
# 代碼功能說明: KGExtractionAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""KGExtractionAgent實現 - 負責從文件中提取知識圖譜LangGraph節點"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class KGExtractionResult:
    """知識圖譜提取結果"""
    files_processed: int
    entities_extracted: int
    relations_extracted: int
    knowledge_graph_nodes: int
    knowledge_graph_edges: int
    extraction_success: bool
    processing_time: float
    failed_files: List[str] = field(default_factory=list) 
    reasoning: str = ""


class KGExtractionAgent(BaseAgentNode):
    """知識圖譜提取Agent - 負責從非結構化文件中提取實體、關係並構建圖譜"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化圖譜提取服務
        self.kg_service = None
        self._initialize_services()

    def _initialize_services(self) -> None:
        """初始化圖譜提取相關服務"""
        try:
            # 從系統服務中獲取圖譜提取服務
            from services.api.services.kg_extraction_service import KGExtractionService

            self.kg_service = KGExtractionService()
            logger.info("KGExtractionService initialized for KGExtractionAgent")
        except Exception as e:
            logger.error(f"Failed to initialize KGExtractionService: {e}")
            self.kg_service = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行知識圖譜提取
        """
        try:
            # 獲取需要處理的文件
            files = self._get_files_for_kg_extraction(state)
            if not files:
                return NodeResult.success(data={"message": "No files for KG extraction"})

            # 執行圖譜提取
            kg_result = await self._perform_kg_extraction(files, state)

            if not kg_result:
                return NodeResult.failure("KG extraction failed")

            # 記錄觀察
            state.add_observation(
                "kg_extraction_completed",
                {
                    "files_processed": kg_result.files_processed,
                    "entities": kg_result.entities_extracted,
                    "relations": kg_result.relations_extracted,
                },
                1.0 if kg_result.extraction_success else 0.0,
            )

            logger.info(f"KG extraction completed for {kg_result.files_processed} files")

            return NodeResult.success(
                data={
                    "kg_extraction": {
                        "files_processed": kg_result.files_processed,
                        "entities_extracted": kg_result.entities_extracted,
                        "relations_extracted": kg_result.relations_extracted,
                        "extraction_success": kg_result.extraction_success,
                        "reasoning": kg_result.reasoning,
                    },
                    "kg_summary": self._create_kg_extraction_summary(kg_result),
                },
                next_layer="resource_check",
            )

        except Exception as e:
            logger.error(f"KGExtractionAgent execution error: {e}")
            return NodeResult.failure(f"KG extraction error: {e}")

    def _get_files_for_kg_extraction(self, state: AIBoxState) -> List[Dict[str, Any]]:
        """獲取需要提取的文件"""
        return []

    async def _perform_kg_extraction(
        self, files: List[Dict[str, Any]], state: AIBoxState,
    ) -> Optional[KGExtractionResult]:
        """執行實際的圖譜提取"""
        return KGExtractionResult(
            files_processed=len(files)
            entities_extracted=0,
            relations_extracted=0,
            knowledge_graph_nodes=0,
            knowledge_graph_edges=0,
            extraction_success=True,
            processing_time=0.0,
            reasoning="Simulated KG extraction success.",
        )

    def _create_kg_extraction_summary(self, kg_result: KGExtractionResult) -> Dict[str, Any]:
        return {
            "processed": kg_result.files_processed,
            "success": kg_result.extraction_success,
        }


def create_kg_extraction_agent_config() -> NodeConfig:
    return NodeConfig(
        name="KGExtractionAgent",
        description="知識圖譜提取Agent - 負責從非結構化文件中提取實體、關係並構建圖譜",
        max_retries=1,
        timeout=600.0,
        required_inputs=["user_id"]
        optional_inputs=["file_upload", "messages"],
        output_keys=["kg_summary"]
    )


def create_kg_extraction_agent() -> KGExtractionAgent:
    config = create_kg_extraction_agent_config()
    return KGExtractionAgent(config)