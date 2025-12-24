# 代碼功能說明: 數據分類與標記模型定義（WBS-4.2.1: 數據分類與標記）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""數據分類與標記模型定義

定義數據分類級別和敏感性標籤的枚舉類型。
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional


class DataClassification(str, Enum):
    """數據分類級別（WBS-4.2.1）

    基於常見標準的四級分類方案，可根據業務需求調整。
    """

    PUBLIC = "public"  # 公開：可公開訪問的數據，無限制
    INTERNAL = "internal"  # 內部：僅限組織內部使用，不對外公開
    CONFIDENTIAL = "confidential"  # 機密：僅限授權人員訪問，需要特殊權限
    RESTRICTED = "restricted"  # 限制：最高機密級別，僅限特定人員訪問

    @classmethod
    def get_default(cls) -> str:
        """獲取默認分類級別"""
        return cls.INTERNAL.value

    @classmethod
    def get_all_values(cls) -> List[str]:
        """獲取所有分類級別的值"""
        return [item.value for item in cls]


class SensitivityLabel(str, Enum):
    """敏感性標籤（WBS-4.2.1）

    標記數據的敏感屬性，一個數據可以有多個標籤。
    """

    PII = "pii"  # 個人識別資訊（Personally Identifiable Information）
    PHI = "phi"  # 受保護健康資訊（Protected Health Information）
    FINANCIAL = "financial"  # 財務資訊
    IP = "ip"  # 智慧財產權（Intellectual Property）
    CUSTOMER = "customer"  # 客戶資訊
    PROPRIETARY = "proprietary"  # 專有資訊

    @classmethod
    def get_all_values(cls) -> List[str]:
        """獲取所有敏感性標籤的值"""
        return [item.value for item in cls]


def validate_classification(classification: Optional[str]) -> Optional[str]:
    """驗證分類級別是否有效

    Args:
        classification: 分類級別字符串

    Returns:
        有效的分類級別字符串，如果無效則返回 None

    Raises:
        ValueError: 如果分類級別無效且不為 None
    """
    if classification is None:
        return None

    valid_values = DataClassification.get_all_values()
    if classification not in valid_values:
        raise ValueError(
            f"Invalid classification: {classification}. "
            f"Must be one of: {', '.join(valid_values)}"
        )

    return classification


def validate_sensitivity_labels(labels: Optional[List[str]]) -> Optional[List[str]]:
    """驗證敏感性標籤列表是否有效

    Args:
        labels: 敏感性標籤列表

    Returns:
        有效的敏感性標籤列表，如果無效則返回 None

    Raises:
        ValueError: 如果標籤列表包含無效值
    """
    if labels is None or len(labels) == 0:
        return None

    valid_values = SensitivityLabel.get_all_values()
    invalid_labels = [label for label in labels if label not in valid_values]

    if invalid_labels:
        raise ValueError(
            f"Invalid sensitivity labels: {invalid_labels}. "
            f"Must be one of: {', '.join(valid_values)}"
        )

    return labels
