# 代碼功能說明: 偏見檢測服務
# 創建日期: 2025-12-06 15:47 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 15:47 (UTC+8)

"""偏見檢測服務 - 檢測NER/RE/RT結果中的偏見"""

from typing import List, Optional, Dict, Any
import structlog
import re

from genai.api.models.ner_models import Entity
from genai.api.models.re_models import Relation

logger = structlog.get_logger(__name__)

# 敏感詞模式（基礎實現）
SENSITIVE_PATTERNS = {
    "gender": [
        r"男[性人]",
        r"女[性人]",
        r"男性",
        r"女性",
        r"先生",
        r"女士",
        r"小姐",
    ],
    "race": [
        r"種族",
        r"民族",
    ],
    "age": [
        r"老人",
        r"年輕人",
        r"小孩",
    ],
}


class BiasIssue:
    """偏見問題"""

    def __init__(
        self,
        bias_type: str,
        severity: str,
        description: str,
        entity: Optional[Entity] = None,
        relation: Optional[Relation] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化偏見問題

        Args:
            bias_type: 偏見類型（性別、種族、年齡等）
            severity: 嚴重程度（high, medium, low）
            description: 問題描述
            entity: 相關實體（如果適用）
            relation: 相關關係（如果適用）
            details: 詳細信息
        """
        self.bias_type = bias_type
        self.severity = severity
        self.description = description
        self.entity = entity
        self.relation = relation
        self.details = details or {}


class BiasDetectionService:
    """偏見檢測服務"""

    def __init__(self):
        """初始化偏見檢測服務"""
        self.logger = logger
        self.patterns = SENSITIVE_PATTERNS

    def detect_entity_bias(self, entities: List[Entity]) -> List[BiasIssue]:
        """
        檢測實體中的偏見

        Args:
            entities: 實體列表

        Returns:
            偏見問題列表
        """
        issues: List[BiasIssue] = []

        for entity in entities:
            text = entity.text.lower()

            # 檢查性別偏見
            for pattern in self.patterns.get("gender", []):
                if re.search(pattern, text):
                    issues.append(
                        BiasIssue(
                            bias_type="性別",
                            severity="medium",
                            description=f"實體「{entity.text}」可能包含性別相關信息",
                            entity=entity,
                            details={"pattern": pattern},
                        )
                    )

            # 檢查種族偏見
            for pattern in self.patterns.get("race", []):
                if re.search(pattern, text):
                    issues.append(
                        BiasIssue(
                            bias_type="種族",
                            severity="high",
                            description=f"實體「{entity.text}」可能包含種族相關信息",
                            entity=entity,
                            details={"pattern": pattern},
                        )
                    )

            # 檢查年齡偏見
            for pattern in self.patterns.get("age", []):
                if re.search(pattern, text):
                    issues.append(
                        BiasIssue(
                            bias_type="年齡",
                            severity="low",
                            description=f"實體「{entity.text}」可能包含年齡相關信息",
                            entity=entity,
                            details={"pattern": pattern},
                        )
                    )

        return issues

    def detect_relation_bias(self, relations: List[Relation]) -> List[BiasIssue]:
        """
        檢測關係中的偏見

        Args:
            relations: 關係列表

        Returns:
            偏見問題列表
        """
        issues: List[BiasIssue] = []

        for relation in relations:
            # 檢查主體和客體中的偏見
            subject_text = relation.subject.text.lower()
            object_text = relation.object.text.lower()

            # 檢查性別偏見
            for pattern in self.patterns.get("gender", []):
                if re.search(pattern, subject_text) or re.search(pattern, object_text):
                    issues.append(
                        BiasIssue(
                            bias_type="性別",
                            severity="medium",
                            description=f"關係「{relation.relation}」可能涉及性別偏見",
                            relation=relation,
                            details={"pattern": pattern},
                        )
                    )

        return issues

    def detect_bias(
        self,
        entities: Optional[List[Entity]] = None,
        relations: Optional[List[Relation]] = None,
    ) -> List[BiasIssue]:
        """
        綜合檢測偏見

        Args:
            entities: 實體列表（可選）
            relations: 關係列表（可選）

        Returns:
            偏見問題列表
        """
        issues: List[BiasIssue] = []

        if entities:
            issues.extend(self.detect_entity_bias(entities))

        if relations:
            issues.extend(self.detect_relation_bias(relations))

        return issues


# 全局服務實例（懶加載）
_bias_detection_service: Optional[BiasDetectionService] = None


def get_bias_detection_service() -> BiasDetectionService:
    """獲取偏見檢測服務實例（單例模式）"""
    global _bias_detection_service
    if _bias_detection_service is None:
        _bias_detection_service = BiasDetectionService()
    return _bias_detection_service
