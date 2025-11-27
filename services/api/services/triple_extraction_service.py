# 代碼功能說明: 三元組提取服務
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""三元組提取服務 - 整合 NER、RE、RT 服務實現三元組提取"""

from typing import List, Optional, Set, Tuple
import structlog

from services.api.models.triple_models import Triple, TripleEntity, TripleRelation
from services.api.models.ner_models import Entity
from services.api.models.re_models import Relation
from services.api.models.rt_models import RelationType
from services.api.services.ner_service import NERService
from services.api.services.re_service import REService
from services.api.services.rt_service import RTService

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

    def _match_entity_pairs(
        self, entities: List[Entity]
    ) -> List[Tuple[Entity, Entity]]:
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

    def _validate_relation(
        self, relation: Relation, subject: Entity, object: Entity
    ) -> bool:
        """驗證關係是否存在於實體對之間"""
        # 檢查關係的主體和客體是否匹配實體對
        subject_match = (
            relation.subject.text == subject.text
            and relation.subject.label == subject.label
        )
        object_match = (
            relation.object.text == object.text
            and relation.object.label == object.label
        )

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
    ) -> List[Triple]:
        """提取三元組"""
        # 步驟 1: NER（實體識別）
        if entities is None and enable_ner:
            entities = await self.ner_service.extract_entities(text)
        elif entities is None:
            entities = []

        if len(entities) < 2:
            logger.info(
                "insufficient_entities", text=text[:50], entity_count=len(entities)
            )
            return []

        # 步驟 2: RE（關係抽取）
        relations = await self.re_service.extract_relations(text, entities)

        if not relations:
            logger.info("no_relations_found", text=text[:50])
            return []

        # 步驟 3: RT（關係分類）
        triples = []
        for relation in relations:
            # 對每個關係進行類型分類
            relation_types = await self.rt_service.classify_relation_type(
                relation.relation, relation.subject.text, relation.object.text
            )

            if not relation_types:
                # 如果分類失敗，使用原始關係類型
                relation_types = [
                    RelationType(type=relation.relation, confidence=relation.confidence)
                ]

            # 步驟 4: 構建三元組
            for rt in relation_types:
                # 找到對應的實體
                subject_entity = None
                object_entity = None

                for entity in entities:
                    if (
                        entity.text == relation.subject.text
                        and entity.label == relation.subject.label
                    ):
                        subject_entity = entity
                    if (
                        entity.text == relation.object.text
                        and entity.label == relation.object.label
                    ):
                        object_entity = entity

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

        # 步驟 5: 去重
        triples = self._deduplicate_triples(triples)

        return triples

    async def extract_triples_batch(self, texts: List[str]) -> List[List[Triple]]:
        """批量提取三元組"""
        results = []
        for text in texts:
            try:
                triples = await self.extract_triples(text)
                results.append(triples)
            except Exception as e:
                logger.error(
                    "triple_batch_extraction_failed", error=str(e), text=text[:50]
                )
                results.append([])

        return results
