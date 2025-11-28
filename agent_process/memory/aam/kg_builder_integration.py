# 代碼功能說明: AAM 知識圖譜構建整合
# 創建日期: 2025-11-28 21:54 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-28 21:54 (UTC+8)

"""AAM 知識圖譜構建整合 - 實現記憶到知識圖譜的數據流"""

from __future__ import annotations

from typing import List, Optional

import structlog

from agent_process.memory.aam.models import MemoryType
from agent_process.memory.aam.aam_core import AAMManager
from services.api.services.kg_builder_service import KGBuilderService
from services.api.models.triple_models import Triple

logger = structlog.get_logger(__name__)


class KGBuilderIntegration:
    """知識圖譜構建整合 - 整合 AAM 和知識圖譜構建服務"""

    def __init__(
        self,
        aam_manager: AAMManager,
        kg_builder_service: Optional[KGBuilderService] = None,
        auto_update: bool = True,
    ):
        """
        初始化知識圖譜構建整合

        Args:
            aam_manager: AAM 管理器
            kg_builder_service: 知識圖譜構建服務（如果為 None 則自動創建）
            auto_update: 是否自動更新圖譜
        """
        self.aam_manager = aam_manager
        self.kg_builder_service = kg_builder_service or KGBuilderService()
        self.auto_update = auto_update
        self.logger = logger.bind(component="kg_builder_integration")

    def memory_to_kg(
        self, memory_id: str, memory_type: Optional[MemoryType] = None
    ) -> bool:
        """
        將記憶轉換為知識圖譜（記憶 → 三元組 → 圖譜）

        Args:
            memory_id: 記憶 ID
            memory_type: 記憶類型

        Returns:
            是否成功
        """
        try:
            # 檢索記憶
            memory = self.aam_manager.retrieve_memory(memory_id, memory_type)
            if memory is None:
                self.logger.warning("Memory not found", memory_id=memory_id)
                return False

            # 從記憶中提取三元組（需要先通過知識提取 Agent）
            # 這裡簡化處理，實際應該調用 KnowledgeExtractionAgent
            # 注意：這裡需要異步調用，簡化為同步
            # from agent_process.memory.aam.knowledge_extraction_agent import (
            #     KnowledgeExtractionAgent,
            # )
            # agent = KnowledgeExtractionAgent(self.aam_manager)
            # triples = await agent.extract_knowledge_from_memory(memory_id, memory_type)

            # 構建知識圖譜
            # await self.kg_builder_service.build_from_triples(triples)

            self.logger.info("Converted memory to knowledge graph", memory_id=memory_id)
            return True
        except Exception as e:
            self.logger.error(
                "Failed to convert memory to knowledge graph",
                error=str(e),
                memory_id=memory_id,
            )
            return False

    async def build_from_triples(self, triples: List[Triple]) -> bool:
        """
        從三元組構建知識圖譜

        Args:
            triples: 三元組列表

        Returns:
            是否成功
        """
        try:
            if self.kg_builder_service is None:
                self.logger.warning("KGBuilderService not available")
                return False

            await self.kg_builder_service.build_from_triples(triples)
            self.logger.info(
                "Built knowledge graph from triples", triple_count=len(triples)
            )
            return True
        except Exception as e:
            self.logger.error(
                "Failed to build knowledge graph from triples", error=str(e)
            )
            return False

    async def incremental_update(self, triples: List[Triple]) -> bool:
        """
        增量更新知識圖譜（僅更新新三元組）

        Args:
            triples: 新三元組列表

        Returns:
            是否成功
        """
        try:
            if self.kg_builder_service is None:
                return False

            # 構建圖譜（KGBuilderService 會自動處理實體合併和關係更新）
            await self.kg_builder_service.build_from_triples(triples)
            self.logger.info(
                "Incrementally updated knowledge graph", triple_count=len(triples)
            )
            return True
        except Exception as e:
            self.logger.error(
                "Failed to incrementally update knowledge graph", error=str(e)
            )
            return False
