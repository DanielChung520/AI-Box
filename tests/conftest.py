# 代碼功能說明: Pytest 共享配置和 Fixtures
# 創建日期: 2025-01-27 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 (UTC+8)

"""Pytest 共享配置和 Fixtures"""

import pytest

from services.api.models.ner_models import Entity


@pytest.fixture
def mock_entity() -> Entity:
    """創建模擬實體"""
    return Entity(
        text="張三",
        label="PERSON",
        start=0,
        end=2,
        confidence=0.95,
    )


@pytest.fixture
def mock_entities() -> list[Entity]:
    """創建模擬實體列表"""
    return [
        Entity(text="張三", label="PERSON", start=0, end=2, confidence=0.95),
        Entity(text="微軟", label="ORG", start=5, end=7, confidence=0.90),
        Entity(text="北京", label="LOC", start=10, end=12, confidence=0.88),
    ]
