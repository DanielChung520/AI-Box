# 代碼功能說明: 知識圖譜提取服務
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""知識圖譜提取服務 - 封裝三元組提取和圖譜構建流程"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Set, Tuple
import structlog

from genai.api.services.triple_extraction_service import TripleExtractionService
from genai.api.services.kg_builder_service import KGBuilderService
from genai.api.models.triple_models import Triple
from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)

# 全局服務實例（單例模式）
_kg_extraction_service: Optional["KGExtractionService"] = None


class KGExtractionService:
    """知識圖譜提取服務類"""

    def __init__(
        self,
        triple_service: Optional[TripleExtractionService] = None,
        kg_builder: Optional[KGBuilderService] = None,
    ):
        """
        初始化知識圖譜提取服務

        Args:
            triple_service: 三元組提取服務，如果不提供則創建新實例
            kg_builder: 知識圖譜構建服務，如果不提供則創建新實例
        """
        self.triple_service = triple_service or TripleExtractionService()
        self.kg_builder = kg_builder or KGBuilderService()

        logger.info("KGExtractionService initialized")

    def _filter_chunks(
        self, chunks: List[Dict[str, Any]], filter_options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        根據過濾選項過濾分塊

        Args:
            chunks: 分塊列表
            filter_options: 過濾選項

        Returns:
            過濾後的分塊列表
        """
        filtered = chunks

        # 最小長度過濾
        min_length = filter_options.get("min_length", 0)
        if min_length > 0:
            filtered = [
                chunk for chunk in filtered if len(chunk.get("text", "")) >= min_length
            ]

        # 最大分塊數限制
        max_chunks = filter_options.get("max_chunks")
        if max_chunks and max_chunks > 0:
            filtered = filtered[:max_chunks]

        # 重要性過濾（如果分塊有重要性評分）
        importance_threshold = filter_options.get("importance_threshold")
        if importance_threshold is not None:
            filtered = [
                chunk
                for chunk in filtered
                if chunk.get("importance", 0) >= importance_threshold
            ]

        logger.debug(
            "Filtered chunks",
            original_count=len(chunks),
            filtered_count=len(filtered),
        )
        return filtered

    def _deduplicate_triples(self, triples: List[Triple]) -> List[Triple]:
        """
        三元組去重（相同三元組合併，取較高置信度）

        Args:
            triples: 三元組列表

        Returns:
            去重後的三元組列表
        """
        seen: Set[Tuple[str, str, str]] = set()
        unique_triples: List[Triple] = []
        triple_map: Dict[Tuple[str, str, str], Triple] = {}

        for triple in triples:
            key = (
                triple.subject.text.lower(),
                triple.relation.type.lower(),
                triple.object.text.lower(),
            )

            if key not in seen:
                seen.add(key)
                unique_triples.append(triple)
                triple_map[key] = triple
            else:
                # 如果已存在，更新置信度（取較高值）
                existing = triple_map[key]
                if triple.confidence > existing.confidence:
                    # 替換為置信度更高的三元組
                    index = unique_triples.index(existing)
                    unique_triples[index] = triple
                    triple_map[key] = triple

        logger.debug(
            "Deduplicated triples",
            original_count=len(triples),
            unique_count=len(unique_triples),
        )
        return unique_triples

    async def extract_triples_from_chunks(
        self, chunks: List[Dict[str, Any]], options: Optional[Dict[str, Any]] = None
    ) -> List[Triple]:
        """
        從分塊中提取三元組

        Args:
            chunks: 分塊列表，每個分塊包含 text 和 metadata
            options: 提取選項
                - mode: "all_chunks", "selected_chunks", "entire_file"
                - min_confidence: 最小置信度閾值
                - chunk_filter: 分塊過濾條件

        Returns:
            提取的三元組列表
        """
        if options is None:
            options = {}

        mode = options.get("mode", "all_chunks")
        min_confidence = options.get("min_confidence", 0.5)
        chunk_filter = options.get("chunk_filter", {})

        # 根據模式處理分塊
        if mode == "entire_file":
            # 合併所有分塊文本
            full_text = " ".join(chunk.get("text", "") for chunk in chunks)
            if not full_text.strip():
                logger.warning("No text content in chunks")
                return []

            triples = await self.triple_service.extract_triples(
                text=full_text, entities=None, enable_ner=True
            )
        elif mode == "selected_chunks":
            # 過濾分塊
            filtered_chunks = self._filter_chunks(chunks, chunk_filter)
            triples = await self._extract_from_chunks_batch(filtered_chunks)
        else:
            # 默認：處理所有分塊
            triples = await self._extract_from_chunks_batch(chunks)

        # 過濾低置信度三元組
        if min_confidence > 0:
            triples = [t for t in triples if t.confidence >= min_confidence]

        # 去重
        triples = self._deduplicate_triples(triples)

        logger.info(
            "Extracted triples from chunks",
            chunk_count=len(chunks),
            triple_count=len(triples),
            mode=mode,
        )
        return triples

    async def _extract_from_chunks_batch(
        self, chunks: List[Dict[str, Any]]
    ) -> List[Triple]:
        """
        批量從分塊中提取三元組

        Args:
            chunks: 分塊列表

        Returns:
            提取的三元組列表
        """
        all_triples: List[Triple] = []

        for i, chunk in enumerate(chunks):
            try:
                chunk_text = chunk.get("text", "")
                if not chunk_text.strip():
                    continue

                # 提取三元組
                triples = await self.triple_service.extract_triples(
                    text=chunk_text, entities=None, enable_ner=True
                )

                # 添加分塊元數據到三元組的上下文
                for triple in triples:
                    # 可以添加分塊索引等信息到上下文
                    if chunk.get("metadata"):
                        triple.context = (
                            f"{triple.context} [Chunk {i+1}/{len(chunks)}]"
                            if triple.context
                            else f"[Chunk {i+1}/{len(chunks)}]"
                        )

                all_triples.extend(triples)

                logger.debug(
                    "Extracted triples from chunk",
                    chunk_index=i + 1,
                    total_chunks=len(chunks),
                    triple_count=len(triples),
                )

            except Exception as e:
                logger.warning(
                    "Failed to extract triples from chunk",
                    chunk_index=i + 1,
                    error=str(e),
                )
                continue

        return all_triples

    async def extract_triples_from_file(
        self, file_id: str, file_text: str, options: Optional[Dict[str, Any]] = None
    ) -> List[Triple]:
        """
        從文件文本中提取三元組（不依賴分塊）

        Args:
            file_id: 文件ID
            file_text: 文件完整文本
            options: 提取選項

        Returns:
            提取的三元組列表
        """
        if options is None:
            options = {}

        min_confidence = options.get("min_confidence", 0.5)

        # 提取三元組
        triples = await self.triple_service.extract_triples(
            text=file_text, entities=None, enable_ner=True
        )

        # 過濾低置信度三元組
        if min_confidence > 0:
            triples = [t for t in triples if t.confidence >= min_confidence]

        # 去重
        triples = self._deduplicate_triples(triples)

        logger.info(
            "Extracted triples from file",
            file_id=file_id,
            triple_count=len(triples),
        )
        return triples

    async def build_kg_from_file(
        self,
        file_id: str,
        triples: List[Triple],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        從三元組構建知識圖譜並存儲到 ArangoDB

        Args:
            file_id: 文件ID
            triples: 三元組列表
            user_id: 用戶ID
            metadata: 額外元數據

        Returns:
            構建結果統計
        """
        if not triples:
            logger.warning("No triples to build KG", file_id=file_id)
            return {
                "entities_created": 0,
                "entities_updated": 0,
                "relations_created": 0,
                "relations_updated": 0,
                "total_triples": 0,
            }

        # 為三元組添加文件ID和用戶ID元數據
        # 注意：這裡我們需要修改三元組的上下文來包含文件信息
        # 但 Triple 模型可能不支持直接修改，所以我們在構建時處理

        # 構建知識圖譜
        result = await self.kg_builder.build_from_triples(triples)

        # 在實體和關係中添加文件ID和用戶ID關聯
        # 這需要在 KGBuilderService 中實現，或者通過額外的元數據集合實現
        # 暫時先返回構建結果

        logger.info(
            "Built KG from file",
            file_id=file_id,
            user_id=user_id,
            triples_count=len(triples),
            entities_created=result.get("entities_created", 0),
            relations_created=result.get("relations_created", 0),
        )

        return result

    async def extract_and_build_kg(
        self,
        file_id: str,
        chunks: List[Dict[str, Any]],
        user_id: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        提取三元組並構建知識圖譜（一站式方法）

        Args:
            file_id: 文件ID
            chunks: 分塊列表
            user_id: 用戶ID
            options: 提取選項

        Returns:
            構建結果統計
        """
        # 提取三元組
        triples = await self.extract_triples_from_chunks(chunks, options)

        # 構建知識圖譜
        result = await self.build_kg_from_file(file_id, triples, user_id)

        return {
            **result,
            "triples_extracted": len(triples),
        }


def get_kg_extraction_service() -> KGExtractionService:
    """獲取知識圖譜提取服務實例（單例模式）

    Returns:
        KGExtractionService 實例
    """
    global _kg_extraction_service
    if _kg_extraction_service is None:
        _kg_extraction_service = KGExtractionService()
    return _kg_extraction_service


def reset_kg_extraction_service() -> None:
    """重置知識圖譜提取服務實例（主要用於測試）"""
    global _kg_extraction_service
    _kg_extraction_service = None
