# 代碼功能說明: 知識圖譜提取服務
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-10

"""知識圖譜提取服務 - 封裝三元組提取和圖譜構建流程"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Set, Tuple
import structlog

from genai.api.services.triple_extraction_service import TripleExtractionService
from genai.api.services.kg_builder_service import KGBuilderService
from genai.api.models.triple_models import Triple

# 導入 Ontology 管理相關模組
logger = structlog.get_logger(__name__)  # 定義 logger 在 try-except 之前

try:
    from kag.kag_schema_manager import OntologyManager
    from kag.ontology_selector import OntologySelector

    ONTOLOGY_SUPPORT = True
except ImportError:
    ONTOLOGY_SUPPORT = False
    logger.warning("Ontology support not available - kag module not found")

# 全局服務實例（單例模式）
_kg_extraction_service: Optional["KGExtractionService"] = None


class KGExtractionService:
    """知識圖譜提取服務類"""

    def __init__(
        self,
        triple_service: Optional[TripleExtractionService] = None,
        kg_builder: Optional[KGBuilderService] = None,
        ontology_manager: Optional[OntologyManager] = None,
        ontology_selector: Optional[OntologySelector] = None,
    ):
        """
        初始化知識圖譜提取服務

        Args:
            triple_service: 三元組提取服務，如果不提供則創建新實例
            kg_builder: 知識圖譜構建服務，如果不提供則創建新實例
            ontology_manager: Ontology 管理器，如果不提供則創建新實例
            ontology_selector: Ontology 選擇器，如果不提供則創建新實例
        """
        self.triple_service = triple_service or TripleExtractionService()
        self.kg_builder = kg_builder or KGBuilderService()

        # 初始化 Ontology 相關服務（如果可用）
        if ONTOLOGY_SUPPORT:
            self.ontology_manager = ontology_manager or OntologyManager()
            self.ontology_selector = ontology_selector or OntologySelector()
            self._current_ontology_rules: Optional[Dict[str, Any]] = None
        else:
            self.ontology_manager = None
            self.ontology_selector = None
            self._current_ontology_rules = None

        logger.info(
            "KGExtractionService initialized", ontology_support=ONTOLOGY_SUPPORT
        )

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

    def _load_ontology_for_extraction(
        self,
        file_name: Optional[str] = None,
        file_content: Optional[str] = None,
        file_metadata: Optional[Dict[str, Any]] = None,
        manual_ontology: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        為提取任務載入合適的 Ontology

        Args:
            file_name: 文件名
            file_content: 文件內容預覽
            file_metadata: 文件元數據
            manual_ontology: 手動指定的 Ontology 配置
                - domain: List[str] domain 文件名列表
                - major: Optional[str] major 文件名

        Returns:
            合併後的 Ontology 規則，如果載入失敗則返回 None
        """
        if not ONTOLOGY_SUPPORT or not self.ontology_manager:
            logger.debug("Ontology support not available, skipping ontology loading")
            return None

        try:
            # 如果手動指定了 Ontology，使用手動配置
            if manual_ontology:
                domain_files = manual_ontology.get("domain", [])
                major_file = manual_ontology.get("major")
                logger.info(
                    "Using manual ontology configuration",
                    domain=domain_files,
                    major=major_file,
                )
            else:
                # 自動選擇 Ontology
                if not self.ontology_selector:
                    logger.warning("Ontology selector not available, using base only")
                    domain_files = []
                    major_file = None
                else:
                    selection = self.ontology_selector.select_auto(
                        file_name=file_name,
                        file_content=file_content,
                        file_metadata=file_metadata,
                    )
                    domain_files = selection.get("domain", [])
                    major_file = (
                        selection.get("major", [None])[0]
                        if selection.get("major")
                        else None
                    )

                    logger.info(
                        "Auto-selected ontology",
                        method=selection.get("selection_method"),
                        domain=domain_files,
                        major=major_file,
                    )

            # 載入並合併 Ontology
            rules = self.ontology_manager.merge_ontologies(
                domain_files=domain_files, task_file=major_file
            )

            self._current_ontology_rules = rules

            logger.info(
                "Ontology loaded successfully",
                entity_count=len(rules.get("entity_classes", [])),
                relationship_count=len(rules.get("relationship_types", [])),
            )

            return rules

        except Exception as e:
            logger.warning(
                "Failed to load ontology, continuing without ontology constraints",
                error=str(e),
                exc_info=True,
            )
            return None

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
                - file_name: 文件名（用於 Ontology 選擇）
                - file_metadata: 文件元數據（用於 Ontology 選擇）
                - ontology: 手動指定的 Ontology 配置
                    - domain: List[str]
                    - major: Optional[str]
                - use_ontology: bool 是否使用 Ontology（默認 True）

        Returns:
            提取的三元組列表
        """
        if options is None:
            options = {}

        mode = options.get("mode", "all_chunks")
        min_confidence = options.get("min_confidence", 0.5)
        chunk_filter = options.get("chunk_filter", {})
        use_ontology = options.get("use_ontology", True)

        # 載入 Ontology（如果啟用）
        ontology_rules = None
        if use_ontology and ONTOLOGY_SUPPORT:
            file_name = options.get("file_name")
            file_metadata = options.get("file_metadata")
            manual_ontology = options.get("ontology")

            # 獲取文件內容預覽（用於 Ontology 選擇）
            file_content_preview = None
            if chunks:
                # 合併前幾個分塊作為預覽
                preview_chunks = chunks[:3]
                file_content_preview = " ".join(
                    chunk.get("text", "")[:500] for chunk in preview_chunks
                )

            ontology_rules = self._load_ontology_for_extraction(
                file_name=file_name,
                file_content=file_content_preview,
                file_metadata=file_metadata,
                manual_ontology=manual_ontology,
            )

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
            triples = await self._extract_from_chunks_batch(
                filtered_chunks, ontology_rules
            )
        else:
            # 默認：處理所有分塊
            triples = await self._extract_from_chunks_batch(chunks, ontology_rules)

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
            ontology_loaded=ontology_rules is not None,
        )
        return triples

    async def _extract_from_chunks_batch(
        self,
        chunks: List[Dict[str, Any]],
        ontology_rules: Optional[Dict[str, Any]] = None,
    ) -> List[Triple]:
        """
        批量從分塊中提取三元組

        Args:
            chunks: 分塊列表
            ontology_rules: 已載入的 Ontology 規則（用於生成 prompt）

        Returns:
            提取的三元組列表
        """
        all_triples: List[Triple] = []

        # 如果載入了 Ontology，生成 prompt 模板（用於後續 LLM 調用）
        prompt_template = None
        if ontology_rules and self.ontology_manager:
            try:
                # 生成示例 prompt（實際使用時會為每個 chunk 生成）
                sample_text = chunks[0].get("text", "")[:200] if chunks else ""
                prompt_template = self.ontology_manager.generate_prompt(
                    text_chunk=sample_text,
                    ontology_rules=ontology_rules,
                    include_owl_constraints=True,
                )
                logger.debug(
                    "Generated prompt template from ontology",
                    length=len(prompt_template),
                )
            except Exception as e:
                logger.warning("Failed to generate prompt template", error=str(e))

        for i, chunk in enumerate(chunks):
            try:
                chunk_text = chunk.get("text", "")
                if not chunk_text.strip():
                    continue

                # 如果使用 Ontology，可以為每個 chunk 生成專用的 prompt
                # 這裡暫時保持原有邏輯，prompt 可以在 triple_service 層面使用
                # 提取三元組
                triples = await self.triple_service.extract_triples(
                    text=chunk_text, entities=None, enable_ner=True
                )

                # 如果載入了 Ontology，可以進行驗證（使用 Pydantic）
                # 注意：這裡的驗證需要將 Triple 轉換為 kag_schema_manager 的 Triple 格式
                # 暫時跳過，因為格式可能不同

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
                    ontology_used=ontology_rules is not None,
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

        # 構建知識圖譜（傳遞file_id和user_id）
        result = await self.kg_builder.build_from_triples(
            triples, file_id=file_id, user_id=user_id
        )

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
