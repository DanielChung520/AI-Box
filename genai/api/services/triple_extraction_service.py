# 代碼功能說明: 三元組提取服務
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""三元組提取服務 - 整合 NER、RE、RT 服務實現三元組提取"""

from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

from genai.api.models.ner_models import Entity
from genai.api.models.re_models import Relation
from genai.api.models.rt_models import RelationType
from genai.api.models.triple_models import Triple, TripleEntity, TripleRelation
from genai.api.services.ner_service import NERService
from genai.api.services.re_service import REService
from genai.api.services.rt_service import STANDARD_RELATION_TYPES as RT_STANDARD_RELATION_TYPES
from genai.api.services.rt_service import RTService
from services.api.services.config_store_service import get_config_store_service

logger = structlog.get_logger(__name__)


class TripleExtractionService:
    """三元組提取服務主類"""

    def __init__(
        self,
        ner_service: Optional[NERService] = None,
        re_service: Optional[REService] = None,
        rt_service: Optional[RTService] = None,
    ):
        self.ner_service = ner_service or NERService()
        self.re_service = re_service or REService(ner_service=self.ner_service)
        self.rt_service = rt_service or RTService()

        # 結果緩存（簡單實現，使用文本哈希）
        self._cache: dict = {}

    def _calculate_triple_confidence(
        self, entity_confidence: float, relation_confidence: float, rt_confidence: float
    ) -> float:
        """計算三元組整體置信度（綜合 NER、RE、RT 置信度）"""
        # 簡單的加權平均
        return entity_confidence * 0.3 + relation_confidence * 0.4 + rt_confidence * 0.3

    def _match_entity_pairs(self, entities: List[Entity]) -> List[Tuple[Entity, Entity]]:
        """匹配實體對（基於 NER 結果）"""
        pairs = []
        for i, subj in enumerate(entities):
            for obj in entities[i + 1 :]:
                # 檢查實體對之間的距離（在同一句子或附近）
                distance = (
                    abs(subj.start - obj.end)
                    if subj.start < obj.start
                    else abs(obj.start - subj.end)
                )
                if distance < 100:  # 實體對距離小於 100 字符
                    pairs.append((subj, obj))
        return pairs

    def _validate_relation(self, relation: Relation, subject: Entity, object: Entity) -> bool:
        """驗證關係是否存在於實體對之間"""
        # 檢查關係的主體和客體是否匹配實體對
        subject_match = (
            relation.subject.text == subject.text and relation.subject.label == subject.label
        )
        object_match = relation.object.text == object.text and relation.object.label == object.label

        return subject_match and object_match

    def _deduplicate_triples(self, triples: List[Triple]) -> List[Triple]:
        """三元組去重（相同三元組合併）"""
        seen: Set[Tuple[str, str, str]] = set()
        unique_triples = []

        for triple in triples:
            key = (
                triple.subject.text,
                triple.relation.type,
                triple.object.text,
            )
            if key not in seen:
                seen.add(key)
                unique_triples.append(triple)
            else:
                # 如果已存在，更新置信度（取較高值）
                for existing in unique_triples:
                    if (
                        existing.subject.text == triple.subject.text
                        and existing.relation.type == triple.relation.type
                        and existing.object.text == triple.object.text
                    ):
                        if triple.confidence > existing.confidence:
                            existing.confidence = triple.confidence
                        break

        return unique_triples

    async def extract_triples(
        self,
        text: str,
        entities: Optional[List[Entity]] = None,
        enable_ner: bool = True,
        ontology_rules: Optional[Dict[str, Any]] = None,
    ) -> List[Triple]:
        """
        提取三元組

        Args:
            text: 待提取的文本
            entities: 預先識別的實體列表（可選）
            enable_ner: 是否啟用NER（如果entities為None）
            ontology_rules: Ontology規則（可選，如果為None則允許LLM自由提取）

        Returns:
            提取的三元組列表
        """
        # 如果ontology_rules為None，使用自由提取模式（不施加Ontology約束）
        if ontology_rules is None:
            logger.debug("Extracting triples without ontology constraints (LLM free mode)")

        # 在提取前規範化文本（確保一致性，即使存儲的文本未規範化）
        import unicodedata

        def normalize_text(text: str) -> str:
            """規範化文本編碼"""
            # 1. NFKC 規範化（處理全角ASCII和部分兼容字符）
            text = unicodedata.normalize("NFKC", text)

            # 2. 手動替換常見的兼容字符和編碼錯誤字符（如果NFKC未完全處理）
            compatibility_map = {
                # 中日韓兼容字符
                "⻛": "風",  # U+2EEB -> U+98CE (風)
                "⽣": "生",  # U+2F63 -> U+751F (生)
                "⼈": "人",  # U+2F0A -> U+4EBA (人)
                "⼤": "大",  # U+2F2A -> U+5927 (大)
                "⾃": "自",  # U+2F89 -> U+81EA (自)
                "〜": "~",  # U+301C -> U+007E (波浪號)
                # PDF 解析常見的編碼錯誤字符
                "Ā": "A",  # U+0100 -> U+0041 (A with macron -> A)
                "à": "a",  # U+00E0 -> U+0061 (a with grave -> a)
                "ÿ": "y",  # U+00FF -> U+0079 (y with diaeresis -> y)
                "⺠": "民",  # U+2EA0 -> U+6C11 (民)
            }
            for compat_char, standard_char in compatibility_map.items():
                text = text.replace(compat_char, standard_char)

            # 3. 移除控制字符（保留換行符和制表符）
            text = "".join(
                c
                for c in text
                if unicodedata.category(c)[0] != "C" or c in ["\n", "\t", "\r"]
            )
            return text

        # 規範化輸入文本
        normalized_text = normalize_text(text)

        # 步驟 1: NER（實體識別）
        if entities is None and enable_ner:
            if self.ner_service is None:
                raise RuntimeError("NER service is not available")
            entities = await self.ner_service.extract_entities(
                normalized_text, ontology_rules=ontology_rules
            )
            logger.info(
                "NER_extraction_completed",
                entity_count=len(entities) if entities else 0,
                text_preview=normalized_text[:100],  # 使用規範化後的文本
                ontology_used=ontology_rules is not None,
            )
        elif entities is None:
            entities = []

        # 從系統配置讀取 insufficient_entities_threshold（默認值為 1）
        insufficient_entities_threshold = 1
        try:
            config_service = get_config_store_service()
            kg_config = config_service.get_config("kg_extraction", tenant_id=None)
            if kg_config and kg_config.config_data:
                insufficient_entities_threshold = kg_config.config_data.get(
                    "insufficient_entities_threshold", 1
                )
        except Exception as e:
            logger.warning(
                "failed_to_read_insufficient_entities_threshold",
                error=str(e),
                message="無法讀取 insufficient_entities_threshold 配置，使用默認值 1",
            )

        if len(entities) < insufficient_entities_threshold:
            logger.info(
                "insufficient_entities",
                text=normalized_text[:50],
                text_preview=normalized_text[:200],  # 添加更長的預覽
                entity_count=len(entities),
                threshold=insufficient_entities_threshold,
                ontology_used=ontology_rules is not None,
            )
            return []

        # 步驟 2: RE（關係抽取）
        if self.re_service is None:
            raise RuntimeError("RE service is not available")
        relations = await self.re_service.extract_relations(
            normalized_text, entities, ontology_rules=ontology_rules
        )
        logger.info(
            "RE_extraction_completed",
            relation_count=len(relations) if relations else 0,
            entity_count=len(entities),
            text_preview=normalized_text[:100],  # 使用規範化後的文本
            ontology_used=ontology_rules is not None,
        )

        if not relations:
            logger.info("no_relations_found", text=normalized_text[:50], entity_count=len(entities), ontology_used=ontology_rules is not None)
            return []

        # 步驟 3: RT（關係分類）
        triples = []
        if self.rt_service is None:
            raise RuntimeError("RT service is not available")
        # 修改時間：2025-12-13 (UTC+8) - RT 優化：
        # 1) 若 RE 已輸出標準關係類型（例如 LOCATED_IN），跳過 RT（省大量 LLM 呼叫）
        # 2) 其餘關係使用 RT batch（單次 LLM 呼叫） + 快取
        rt_requests = []
        rt_request_index_map = []  # 對應回 relations 的 index
        rt_cache: dict = self._cache.setdefault("rt_cache", {})

        per_relation_types: List[List[RelationType]] = [[] for _ in relations]

        for idx, relation in enumerate(relations):
            rel_type = (relation.relation or "").strip()
            rel_type_upper = rel_type.upper()

            if rel_type_upper in RT_STANDARD_RELATION_TYPES:
                # RE 已給出可用的標準關係類型，直接使用
                per_relation_types[idx] = [
                    RelationType(type=rel_type_upper, confidence=relation.confidence)
                ]
                continue

            cache_key = (
                rel_type,
                relation.subject.text,
                relation.object.text,
            )
            cached = rt_cache.get(cache_key)
            if isinstance(cached, list):
                per_relation_types[idx] = cached
                continue

            rt_requests.append(
                {
                    "relation_text": rel_type or "RELATED_TO",
                    "subject_text": relation.subject.text,
                    "object_text": relation.object.text,
                }
            )
            rt_request_index_map.append(idx)

        if rt_requests:
            batch_results = await self.rt_service.classify_relation_types_batch(
                rt_requests, ontology_rules=ontology_rules
            )
            logger.info(
                "RT_classification_completed",
                rt_request_count=len(rt_requests),
                batch_result_count=len(batch_results) if batch_results else 0,
                relation_count=len(relations),
                ontology_used=ontology_rules is not None,
            )
            for req_i, idx in enumerate(rt_request_index_map):
                relation_types = batch_results[req_i] if req_i < len(batch_results) else []
                if not relation_types:
                    relation_types = [
                        RelationType(
                            type=relations[idx].relation,
                            confidence=relations[idx].confidence,
                        )
                    ]
                per_relation_types[idx] = relation_types
                # 寫入快取
                rel = relations[idx]
                cache_key = (rel.relation, rel.subject.text, rel.object.text)
                rt_cache[cache_key] = relation_types

        # 步驟 4: 構建三元組
        logger.info(
            "Building_triples",
            relation_count=len(relations),
            relation_type_count=sum(len(types) for types in per_relation_types),
            entity_count=len(entities),
            ontology_used=ontology_rules is not None,
        )
        unmatched_subjects = []
        unmatched_objects = []
        for idx, relation in enumerate(relations):
            relation_types = per_relation_types[idx]
            for rt in relation_types:
                # 找到對應的實體（改進匹配邏輯：先精確匹配，再模糊匹配）
                subject_entity = None
                object_entity = None

                # 精確匹配：text 和 label 都相同
                for entity in entities:
                    if (
                        entity.text == relation.subject.text
                        and entity.label == relation.subject.label
                    ):
                        subject_entity = entity
                        break
                    if (
                        entity.text == relation.object.text
                        and entity.label == relation.object.label
                    ):
                        object_entity = entity
                        break

                # 模糊匹配：如果精確匹配失敗，嘗試只匹配 text（忽略 label）
                if not subject_entity:
                    for entity in entities:
                        if entity.text == relation.subject.text:
                            subject_entity = entity
                            logger.debug(
                                "entity_label_mismatch_fallback",
                                entity_text=entity.text,
                                entity_label=entity.label,
                                relation_subject_label=relation.subject.label,
                                message="使用模糊匹配（text 相同但 label 不同）",
                            )
                            break

                if not object_entity:
                    for entity in entities:
                        if entity.text == relation.object.text:
                            object_entity = entity
                            logger.debug(
                                "entity_label_mismatch_fallback",
                                entity_text=entity.text,
                                entity_label=entity.label,
                                relation_object_label=relation.object.label,
                                message="使用模糊匹配（text 相同但 label 不同）",
                            )
                            break

                # 如果仍然未匹配，從關係中創建臨時實體（使用 RE 提取的實體信息）
                if not subject_entity:
                    # 使用 relation.subject 的信息創建臨時實體
                    from genai.api.models.ner_models import Entity as EntityModel
                    # 嘗試在原始文本中找到實體位置
                    subject_text = relation.subject.text
                    subject_start = normalized_text.find(subject_text) if subject_text in normalized_text else 0
                    subject_end = subject_start + len(subject_text) if subject_start >= 0 else len(subject_text)
                    subject_entity = EntityModel(
                        text=subject_text,
                        label=relation.subject.label,
                        start=subject_start,
                        end=subject_end,
                        confidence=relation.confidence if hasattr(relation, "confidence") else 0.5,
                    )
                    logger.debug(
                        "entity_created_from_relation",
                        entity_text=subject_entity.text,
                        entity_label=subject_entity.label,
                        message="從關係中創建臨時實體（未在 NER 中找到）",
                    )
                    unmatched_subjects.append(
                        f"{relation.subject.text} ({relation.subject.label}) [創建自關係]"
                    )

                if not object_entity:
                    # 使用 relation.object 的信息創建臨時實體
                    from genai.api.models.ner_models import Entity as EntityModel
                    # 嘗試在原始文本中找到實體位置
                    object_text = relation.object.text
                    object_start = normalized_text.find(object_text) if object_text in normalized_text else 0
                    object_end = object_start + len(object_text) if object_start >= 0 else len(object_text)
                    object_entity = EntityModel(
                        text=object_text,
                        label=relation.object.label,
                        start=object_start,
                        end=object_end,
                        confidence=relation.confidence if hasattr(relation, "confidence") else 0.5,
                    )
                    logger.debug(
                        "entity_created_from_relation",
                        entity_text=object_entity.text,
                        entity_label=object_entity.label,
                        message="從關係中創建臨時實體（未在 NER 中找到）",
                    )
                    unmatched_objects.append(
                        f"{relation.object.text} ({relation.object.label}) [創建自關係]"
                    )

                if subject_entity and object_entity:
                    # 計算三元組置信度
                    triple_confidence = self._calculate_triple_confidence(
                        subject_entity.confidence,
                        relation.confidence,
                        rt.confidence,
                    )

                    triple = Triple(
                        subject=TripleEntity(
                            text=subject_entity.text,
                            type=subject_entity.label,
                            start=subject_entity.start,
                            end=subject_entity.end,
                        ),
                        relation=TripleRelation(type=rt.type, confidence=rt.confidence),
                        object=TripleEntity(
                            text=object_entity.text,
                            type=object_entity.label,
                            start=object_entity.start,
                            end=object_entity.end,
                        ),
                        confidence=triple_confidence,
                        source_text=text,
                        context=relation.context,
                    )
                    triples.append(triple)

        # 記錄未匹配的實體
        if unmatched_subjects or unmatched_objects:
            logger.warning(
                "unmatched_entities_in_relations",
                unmatched_subject_count=len(set(unmatched_subjects)),
                unmatched_object_count=len(set(unmatched_objects)),
                sample_unmatched_subjects=list(set(unmatched_subjects))[:5],
                sample_unmatched_objects=list(set(unmatched_objects))[:5],
                available_entities=[f"{e.text} ({e.label})" for e in entities],
                message="關係中的 subject/object 實體未在 NER 實體列表中找到匹配",
            )

        # 步驟 5: 去重
        triples = self._deduplicate_triples(triples)
        logger.info(
            "Triple_extraction_completed",
            triple_count=len(triples),
            entity_count=len(entities),
            relation_count=len(relations),
            ontology_used=ontology_rules is not None,
        )
        return triples

    async def extract_triples_batch(self, texts: List[str]) -> List[List[Triple]]:
        """批量提取三元組"""
        results = []
        for text in texts:
            try:
                triples = await self.extract_triples(text)
                results.append(triples)
            except Exception as e:
                logger.error("triple_batch_extraction_failed", error=str(e), text=text[:50])
                results.append([])

        return results
