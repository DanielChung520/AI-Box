# 代碼功能說明: 知識圖譜提取服務
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""知識圖譜提取服務 - 封裝三元組提取和圖譜構建流程"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

from database.redis import get_redis_client
from genai.api.models.triple_models import Triple
from genai.api.services.kg_builder_service import KGBuilderService
from genai.api.services.triple_extraction_service import TripleExtractionService

# 導入 Ontology 管理相關模組
logger = structlog.get_logger(__name__)  # 定義 logger 在 try-except 之前

try:
    from kag.kag_schema_manager import OntologyManager
    from kag.ontology_selector import OntologySelector

    ONTOLOGY_SUPPORT = True
except ImportError:
    ONTOLOGY_SUPPORT = False
    logger.warning("Ontology support not available - kag module not found")
    # 定義類型別名以支持類型檢查
    OntologyManager = None  # type: ignore[assignment,misc]
    OntologySelector = None  # type: ignore[assignment,misc]

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
            self.ontology_manager: Optional[OntologyManager] = ontology_manager or OntologyManager()
            self.ontology_selector: Optional[OntologySelector] = (
                ontology_selector or OntologySelector()
            )
            self._current_ontology_rules: Optional[Dict[str, Any]] = None
        else:
            # 在 else 分支中，屬性已在 if 分支中定義，不需要重複定義
            pass

        logger.info("KGExtractionService initialized", ontology_support=ONTOLOGY_SUPPORT)

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
            filtered = [chunk for chunk in filtered if len(chunk.get("text", "")) >= min_length]

        # 最大分塊數限制
        max_chunks = filter_options.get("max_chunks")
        if max_chunks and max_chunks > 0:
            filtered = filtered[:max_chunks]

        # 重要性過濾（如果分塊有重要性評分）
        importance_threshold = filter_options.get("importance_threshold")
        if importance_threshold is not None:
            filtered = [
                chunk for chunk in filtered if chunk.get("importance", 0) >= importance_threshold
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
        為提取任務載入合適的 Ontology（帶優先級降級fallback策略）

        優先級策略：
        1. Tier 1: Major Ontology（優先嘗試）
        2. Tier 2: Domain Ontology（如果major無法匹配）
        3. Tier 3: Base Ontology（如果domain找不到）
        4. Tier 4: None（如果都找不到，允許LLM自由發揮）

        Args:
            file_name: 文件名
            file_content: 文件內容預覽
            file_metadata: 文件元數據
            manual_ontology: 手動指定的 Ontology 配置
                - domain: List[str] domain 文件名列表
                - major: Optional[str] major 文件名

        Returns:
            合併後的 Ontology 規則，如果所有層級都找不到則返回 None（允許LLM自由發揮）
        """
        if not ONTOLOGY_SUPPORT or not self.ontology_manager:
            logger.debug(
                "Ontology support not available, allowing LLM free extraction",
            )
            return None

        try:
            # 如果手動指定了 Ontology，使用手動配置（不進行降級）
            if manual_ontology:
                domain_files = manual_ontology.get("domain", [])
                major_file = manual_ontology.get("major")
                logger.info(
                    "Using manual ontology configuration",
                    domain=domain_files,
                    major=major_file,
                )
                # 載入並合併 Ontology
                rules = self.ontology_manager.merge_ontologies(
                    domain_files=domain_files, task_file=major_file
                )
                self._current_ontology_rules = rules
                logger.info(
                    "Ontology loaded successfully (manual)",
                    entity_count=len(rules.get("entity_classes", [])),
                    relationship_count=len(rules.get("relationship_types", [])),
                )
                return rules

            # 自動選擇 Ontology（帶優先級降級fallback）
            if not self.ontology_selector:
                logger.warning("Ontology selector not available, trying base ontology only")
                # 降級到Base Ontology
                return self._try_load_base_ontology()

            # 獲取所有可能的候選
            selection = self.ontology_selector.select_auto(
                file_name=file_name,
                file_content=file_content,
                file_metadata=file_metadata,
            )
            major_candidates = selection.get("major", [])
            domain_candidates = selection.get("domain", [])

            # Tier 1: 嘗試 Major Ontology（優先）
            if major_candidates:
                major_file = major_candidates[0]
                logger.info(
                    "Trying Tier 1: Major Ontology",
                    major=major_file,
                    selection_method=selection.get("selection_method"),
                )
                try:
                    rules = self.ontology_manager.merge_ontologies(
                        domain_files=[], task_file=major_file
                    )
                    self._current_ontology_rules = rules
                    logger.info(
                        "Ontology loaded successfully (Tier 1: Major)",
                        major=major_file,
                        entity_count=len(rules.get("entity_classes", [])),
                        relationship_count=len(rules.get("relationship_types", [])),
                    )
                    return rules
                except Exception as e:
                    logger.warning(
                        "Tier 1 (Major) failed, falling back to Tier 2 (Domain)",
                        major=major_file,
                        error=str(e),
                    )

            # Tier 2: 嘗試 Domain Ontology
            if domain_candidates:
                for domain_file in domain_candidates:
                    logger.info(
                        "Trying Tier 2: Domain Ontology",
                        domain=domain_file,
                        selection_method=selection.get("selection_method"),
                    )
                    try:
                        rules = self.ontology_manager.merge_ontologies(
                            domain_files=[domain_file], task_file=None
                        )
                        self._current_ontology_rules = rules
                        logger.info(
                            "Ontology loaded successfully (Tier 2: Domain)",
                            domain=domain_file,
                            entity_count=len(rules.get("entity_classes", [])),
                            relationship_count=len(rules.get("relationship_types", [])),
                        )
                        return rules
                    except Exception as e:
                        logger.warning(
                            "Domain ontology failed, trying next",
                            domain=domain_file,
                            error=str(e),
                        )
                        continue

            # Tier 3: 嘗試 Base Ontology
            logger.info("Trying Tier 3: Base Ontology")
            base_rules = self._try_load_base_ontology()
            if base_rules:
                return base_rules

            # Tier 4: 所有Ontology都找不到，允許LLM自由發揮
            logger.info(
                "Tier 4: No ontology matched, allowing LLM free extraction",
                reason="All ontology tiers (Major, Domain, Base) failed or not found",
            )
            return None

        except Exception as e:
            logger.warning(
                "Failed to load ontology, allowing LLM free extraction",
                error=str(e),
                exc_info=True,
            )
            return None

    def _try_load_base_ontology(self) -> Optional[Dict[str, Any]]:
        """
        嘗試載入Base Ontology

        Returns:
            Base Ontology規則，如果載入失敗則返回None
        """
        try:
            rules = self.ontology_manager.merge_ontologies(domain_files=[], task_file=None)
            self._current_ontology_rules = rules
            logger.info(
                "Base Ontology loaded successfully",
                entity_count=len(rules.get("entity_classes", [])),
                relationship_count=len(rules.get("relationship_types", [])),
            )
            return rules
        except Exception as e:
            logger.warning("Failed to load Base Ontology", error=str(e))
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
                text=full_text, entities=None, enable_ner=True, ontology_rules=ontology_rules
            )
        elif mode == "selected_chunks":
            # 過濾分塊
            filtered_chunks = self._filter_chunks(chunks, chunk_filter)
            triples = await self._extract_from_chunks_batch(filtered_chunks, ontology_rules)
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
                # 提取三元組（傳遞ontology_rules，如果為None則允許LLM自由提取）
                triples = await self.triple_service.extract_triples(
                    text=chunk_text, entities=None, enable_ner=True, ontology_rules=ontology_rules
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

    def _kg_chunk_state_key(self, file_id: str) -> str:
        return f"kg:chunk_state:{file_id}"

    def _load_chunk_state(self, file_id: str) -> Dict[str, Any]:
        redis_client = get_redis_client()
        raw = redis_client.get(self._kg_chunk_state_key(file_id))  # type: ignore[arg-type]  # 同步 Redis，返回 Optional[str]
        if not raw:
            return {}
        try:
            return json.loads(raw)  # type: ignore[arg-type]  # raw 已檢查不為 None，且 decode_responses=True 返回 str
        except Exception:
            return {}

    def _save_chunk_state(self, file_id: str, state: Dict[str, Any]) -> None:
        redis_client = get_redis_client()
        # 保留 7 天，支援斷點續跑
        redis_client.setex(self._kg_chunk_state_key(file_id), 7 * 24 * 3600, json.dumps(state))

    def _update_processing_status_kv(self, file_id: str, patch: Dict[str, Any]) -> None:
        """避免跨模組 import：直接更新 processing:status:{file_id} 的 JSON。"""
        redis_client = get_redis_client()
        status_key = f"processing:status:{file_id}"
        raw = redis_client.get(status_key)  # type: ignore[arg-type]  # 同步 Redis，返回 Optional[str]
        status_data: Dict[str, Any] = {}
        if raw:
            try:
                status_data = json.loads(raw)  # type: ignore[arg-type]  # raw 已檢查不為 None，且 decode_responses=True 返回 str
            except Exception:
                status_data = {}
        # shallow merge
        for k, v in patch.items():
            if isinstance(v, dict) and isinstance(status_data.get(k), dict):
                status_data[k].update(v)
            else:
                status_data[k] = v
        redis_client.setex(status_key, 7200, json.dumps(status_data))

    async def extract_and_build_incremental(
        self,
        file_id: str,
        chunks: List[Dict[str, Any]],
        user_id: str,
        options: Optional[Dict[str, Any]] = None,
        *,
        concurrency: int = 3,
        time_budget_seconds: Optional[int] = 150,
    ) -> Dict[str, Any]:
        """分塊提取 + 逐塊寫入 KG（可斷點續跑、可並行提取）。

        不依賴提高 job_timeout：若 time_budget_seconds 到期，會提早結束並回傳 remaining_chunks。
        """
        if options is None:
            options = {}

        mode = options.get("mode", "all_chunks")
        chunk_filter = options.get("chunk_filter", {})
        use_ontology = options.get("use_ontology", True)

        # 載入 Ontology（同 extract_triples_from_chunks）
        ontology_rules = None
        if use_ontology and ONTOLOGY_SUPPORT:
            file_name = options.get("file_name")
            file_metadata = options.get("file_metadata")
            manual_ontology = options.get("ontology")
            file_content_preview = None
            if chunks:
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

        # 決定要處理的 chunk 列表（保留原 index，支援續跑）
        indexed_chunks: List[Tuple[int, Dict[str, Any]]] = [
            (i + 1, c) for i, c in enumerate(chunks)
        ]
        if mode == "selected_chunks":
            filtered = self._filter_chunks(chunks, chunk_filter)
            allowed_ids = {id(c) for c in filtered}
            indexed_chunks = [(i, c) for i, c in indexed_chunks if id(c) in allowed_ids]
        elif mode == "entire_file":
            # 視為單一 chunk
            full_text = " ".join(c.get("text", "") for c in chunks)
            indexed_chunks = [(1, {"text": full_text, "metadata": {"merged": True}})]

        total_chunks = len(indexed_chunks)
        state = self._load_chunk_state(file_id)
        completed_chunks: Set[int] = set(state.get("completed_chunks", []) or [])
        failed_chunks: Set[int] = set(state.get("failed_chunks", []) or [])
        failed_permanent_chunks: Set[int] = set(state.get("failed_permanent_chunks", []) or [])
        attempts: Dict[str, int] = state.get("attempts", {}) or {}
        errors: Dict[str, Any] = state.get("errors", {}) or {}

        max_retries = int(options.get("max_chunk_retries", 3) or 3)

        start_time = time.monotonic()
        pending = [
            (idx, c)
            for idx, c in indexed_chunks
            if idx not in completed_chunks and idx not in failed_permanent_chunks
        ]

        # 更新 processing status：開始/續跑
        self._update_processing_status_kv(
            file_id,
            {
                "status": "processing",
                "kg_extraction": {
                    "status": "processing",
                    "progress": int(len(completed_chunks) / max(total_chunks, 1) * 100),
                    "message": "開始（或續跑）圖譜提取",
                    "total_chunks": total_chunks,
                    "completed_chunks": sorted(list(completed_chunks)),
                    "mode": mode,
                    "ontology_loaded": ontology_rules is not None,
                },
            },
        )

        sem = asyncio.Semaphore(max(1, concurrency))

        async def extract_one(chunk_index: int, chunk: Dict[str, Any]) -> Tuple[int, List[Triple]]:
            async with sem:
                try:
                    chunk_text = chunk.get("text", "")
                    if not chunk_text.strip():
                        return (chunk_index, [])
                    triples = await self.triple_service.extract_triples(
                        text=chunk_text, entities=None, enable_ner=True, ontology_rules=ontology_rules
                    )
                    # chunk 上下文標記
                    for t in triples:
                        t.context = (
                            f"{t.context} [Chunk {chunk_index}/{total_chunks}]"
                            if t.context
                            else f"[Chunk {chunk_index}/{total_chunks}]"
                        )
                    logger.debug(
                        "Extracted triples from chunk",
                        file_id=file_id,
                        chunk_index=chunk_index,
                        total_chunks=total_chunks,
                        triple_count=len(triples),
                        ontology_used=ontology_rules is not None,
                    )
                    return (chunk_index, triples)
                except Exception as e:
                    # 這裡不 raise，改由上層記錄 chunk error，允許續跑
                    logger.warning(
                        "Chunk triple extraction failed",
                        file_id=file_id,
                        chunk_index=chunk_index,
                        error=str(e),
                    )
                    return (chunk_index, [])

        triples_total = 0
        entities_created_total = 0
        relations_created_total = 0

        # 逐批處理：每批最多 concurrency 個 chunk；每批之間檢查 time budget
        remaining_chunks: List[int] = []
        cursor = 0
        while cursor < len(pending):
            if (
                time_budget_seconds is not None
                and (time.monotonic() - start_time) > time_budget_seconds
            ):
                remaining_chunks = [idx for idx, _ in pending[cursor:]]
                break

            batch = pending[cursor : cursor + max(1, concurrency)]
            cursor += len(batch)

            extracted = await asyncio.gather(
                *[extract_one(idx, c) for idx, c in batch],
                return_exceptions=False,
            )

            # 逐塊寫入 KG + 更新狀態（可續跑）
            for chunk_index, chunk_triples in extracted:
                try:
                    # 安全處理 chunk_triples 可能為 None 的情況
                    if chunk_triples is None:
                        chunk_triples = []
                    
                    build_result = await self.build_kg_from_file(
                        file_id, chunk_triples, user_id, options=options
                    )
                    triples_total += len(chunk_triples)
                    # 統計包含 created 和 updated 的總數（實際存儲的實體/關係數量）
                    entities_count = int(build_result.get("entities_created", 0) or 0) + int(build_result.get("entities_updated", 0) or 0)
                    relations_count = int(build_result.get("relations_created", 0) or 0) + int(build_result.get("relations_updated", 0) or 0)
                    entities_created_total += int(build_result.get("entities_created", 0) or 0)
                    relations_created_total += int(build_result.get("relations_created", 0) or 0)

                    completed_chunks.add(chunk_index)
                    failed_chunks.discard(chunk_index)
                    state.setdefault("chunks", {})[str(chunk_index)] = {
                        "triples": len(chunk_triples or []),
                        "ts": int(time.time()),
                        "status": "completed",
                    }
                except Exception as e:
                    # chunk 級錯誤：記錄並允許後續重試
                    key = str(chunk_index)
                    attempts[key] = int(attempts.get(key, 0) or 0) + 1
                    errors[key] = {"error": str(e), "ts": int(time.time())}
                    failed_chunks.add(chunk_index)
                    # 安全處理 chunk_triples 可能為 None 的情況
                    triples_count = len(chunk_triples) if chunk_triples is not None else 0
                    state.setdefault("chunks", {})[key] = {
                        "triples": triples_count,
                        "ts": int(time.time()),
                        "status": "failed",
                        "attempts": attempts[key],
                        "error": str(e),
                    }

                    if attempts[key] >= max_retries:
                        failed_permanent_chunks.add(chunk_index)
                        logger.warning(
                            "Chunk permanently failed",
                            file_id=file_id,
                            chunk_index=chunk_index,
                            attempts=attempts[key],
                            max_retries=max_retries,
                        )

                # 寫入狀態（不論成功/失敗都要落地）
                state["completed_chunks"] = sorted(list(completed_chunks))
                state["failed_chunks"] = sorted(list(failed_chunks))
                state["failed_permanent_chunks"] = sorted(list(failed_permanent_chunks))
                state["attempts"] = attempts
                state["errors"] = errors
                state["total_chunks"] = total_chunks
                self._save_chunk_state(file_id, state)

                progress = int(len(completed_chunks) / max(total_chunks, 1) * 100)
                remaining_now = [
                    idx
                    for idx, _ in indexed_chunks
                    if idx not in completed_chunks and idx not in failed_permanent_chunks
                ]
                self._update_processing_status_kv(
                    file_id,
                    {
                        "kg_extraction": {
                            "status": "processing",
                            "progress": progress,
                            "message": f"圖譜提取進行中：{len(completed_chunks)}/{total_chunks}",
                            "total_chunks": total_chunks,
                            "completed_chunks": sorted(list(completed_chunks)),
                            "failed_chunks": sorted(list(failed_chunks)),
                            "failed_permanent_chunks": sorted(list(failed_permanent_chunks)),
                            "remaining_chunks": remaining_now,
                            "last_completed_chunk": chunk_index,
                            "triples_count": triples_total,
                        }
                    },
                )

        done = (len(completed_chunks) + len(failed_permanent_chunks)) >= total_chunks
        return {
            "success": bool(done and not failed_permanent_chunks),
            "file_id": file_id,
            "total_chunks": total_chunks,
            "completed_chunks": sorted(list(completed_chunks)),
            "failed_chunks": sorted(list(failed_chunks)),
            "failed_permanent_chunks": sorted(list(failed_permanent_chunks)),
            "remaining_chunks": remaining_chunks,
            "triples_count": triples_total,
            "entities_created": entities_created_total,
            "relations_created": relations_created_total,
            "mode": mode,
        }

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
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        從三元組構建知識圖譜並存儲到 ArangoDB

        Args:
            file_id: 文件ID
            triples: 三元組列表
            user_id: 用戶ID
            metadata: 額外元數據
            options: 構建選項
                - min_confidence: 最小置信度閾值（默認 0.5）
                - core_node_threshold: 核心節點閾值（默認 0.9）
                - enable_judgment: 是否啟用裁決層（默認 True）

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

        # GraphRAG 裁決層配置（從 options 讀取）
        if options is None:
            options = {}
        min_confidence = options.get("min_confidence", 0.5)
        core_node_threshold = options.get("core_node_threshold", 0.9)
        enable_judgment = options.get("enable_judgment", True)

        result = await self.kg_builder.build_from_triples(
            triples,
            file_id=file_id,
            user_id=user_id,
            min_confidence=min_confidence,
            core_node_threshold=core_node_threshold,
            enable_judgment=enable_judgment,
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
