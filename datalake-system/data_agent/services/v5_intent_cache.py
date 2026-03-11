# -*- coding: utf-8 -*-
# 代碼功能說明: V5 意圖快取 — thin wrapper, 委派給 DA_IntentRAG
# 創建日期: 2026-03-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

"""
CachedIntentMatcher — thin wrapper over DA_IntentRAG

DA_IntentRAG now handles:
  - Qdrant-backed intent lookup (1 embed + 1 search)
  - In-memory fallback with embedding cache
  - complexity determination via detect_query_complexity()
This module exists for backward compatibility with v5_routes.py.
"""

from typing import Optional

import structlog

from data_agent.services.schema_driven_query.da_intent_rag import (
    DA_IntentRAG,
    IntentMatchResult,
    detect_query_complexity,
)

logger = structlog.get_logger(__name__)


class CachedIntentMatcher:
    """Thin wrapper over DA_IntentRAG for backward compatibility."""

    async def match_intent(self, nlq: str) -> IntentMatchResult:
        """Delegate to DA_IntentRAG singleton."""
        rag = await DA_IntentRAG.get_instance()
        result = await rag.match_intent(nlq)
        if result is None:
            return IntentMatchResult(
                intent="UNKNOWN",
                confidence=0.0,
                description="",
                input_filters=[],
                mart_table=None,
                complexity=detect_query_complexity(nlq),
            )
        return result


# ──────────────────────────────────────────────────
# Singleton Factory
# ──────────────────────────────────────────────────

_singleton: Optional[CachedIntentMatcher] = None


def get_cached_intent_matcher() -> CachedIntentMatcher:
    """取得 CachedIntentMatcher 單例"""
    global _singleton  # noqa: PLW0603
    if _singleton is None:
        _singleton = CachedIntentMatcher()
    return _singleton
