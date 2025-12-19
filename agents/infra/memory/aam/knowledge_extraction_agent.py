# 代碼功能說明: AAM 知識提取 Agent
# 創建日期: 2025-11-28 21:54 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-28 21:54 (UTC+8)

"""AAM 知識提取 Agent - 從對話中提取知識並構建知識圖譜"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from agents.infra.memory.aam.aam_core import AAMManager
from agents.infra.memory.aam.models import Memory, MemoryPriority, MemoryType
from genai.api.models.triple_models import Triple
from genai.api.services.triple_extraction_service import TripleExtractionService

logger = structlog.get_logger(__name__)


class KnowledgeExtractionAgent:
    """知識提取 Agent - 從記憶中提取知識三元組"""

    def __init__(
        self,
        aam_manager: AAMManager,
        triple_extraction_service: Optional[TripleExtractionService] = None,
    ):
        """
        初始化知識提取 Agent

        Args:
            aam_manager: AAM 管理器
            triple_extraction_service: 三元組提取服務（如果為 None 則自動創建）
        """
        self.aam_manager = aam_manager
        self.triple_extraction_service = triple_extraction_service or TripleExtractionService()
        self.logger = logger.bind(component="knowledge_extraction_agent")

    async def extract_knowledge_from_memory(
        self, memory_id: str, memory_type: Optional[MemoryType] = None
    ) -> List[Triple]:
        """
        從記憶中提取知識三元組

        Args:
            memory_id: 記憶 ID
            memory_type: 記憶類型

        Returns:
            三元組列表
        """
        try:
            # 檢索記憶
            memory = self.aam_manager.retrieve_memory(memory_id, memory_type)
            if memory is None:
                self.logger.warning("Memory not found", memory_id=memory_id)
                return []

            # 提取三元組
            triples = await self.triple_extraction_service.extract_triples(memory.content)

            # 更新記憶元數據
            metadata = memory.metadata.copy()
            metadata["triple_count"] = len(triples)
            metadata["knowledge_extracted"] = True

            self.aam_manager.update_memory(memory_id, metadata=metadata)

            self.logger.info(
                "Extracted knowledge from memory",
                memory_id=memory_id,
                triple_count=len(triples),
            )

            return triples
        except Exception as e:
            self.logger.error(
                "Failed to extract knowledge from memory",
                error=str(e),
                memory_id=memory_id,
            )
            return []

    async def extract_knowledge_from_text(self, text: str) -> List[Triple]:
        """
        從文本中提取知識三元組

        Args:
            text: 文本內容

        Returns:
            三元組列表
        """
        try:
            triples = await self.triple_extraction_service.extract_triples(text)
            self.logger.info("Extracted knowledge from text", triple_count=len(triples))
            return triples
        except Exception as e:
            self.logger.error("Failed to extract knowledge from text", error=str(e))
            return []

    def analyze_memory(self, memory: Memory) -> Dict[str, Any]:
        """
        分析記憶（提取關鍵信息）

        Args:
            memory: 記憶對象

        Returns:
            分析結果
        """
        try:
            analysis: Dict[str, Any] = {
                "memory_id": memory.memory_id,
                "content_length": len(memory.content),
                "word_count": len(memory.content.split()),
                "priority": memory.priority.value,
                "access_count": memory.access_count,
                "relevance_score": memory.relevance_score,
            }

            # 簡單的關鍵詞提取（實際應用中可以使用更複雜的 NLP 方法）
            words = memory.content.split()
            analysis["word_frequency"] = {}
            for word in words:
                if len(word) > 3:  # 只統計長度大於3的詞
                    analysis["word_frequency"][word] = analysis["word_frequency"].get(word, 0) + 1

            return analysis
        except Exception as e:
            self.logger.error("Failed to analyze memory", error=str(e))
            return {}

    def classify_memory(self, memory: Memory) -> str:
        """
        分類記憶（按類型、重要性分類）

        Args:
            memory: 記憶對象

        Returns:
            分類標籤
        """
        try:
            # 簡單的分類邏輯（實際應用中可以使用 ML 模型）
            if memory.priority == MemoryPriority.CRITICAL:
                return "critical"
            elif memory.priority == MemoryPriority.HIGH:
                return "important"
            elif memory.access_count > 10:
                return "frequently_accessed"
            else:
                return "normal"
        except Exception as e:
            self.logger.error("Failed to classify memory", error=str(e))
            return "unknown"
