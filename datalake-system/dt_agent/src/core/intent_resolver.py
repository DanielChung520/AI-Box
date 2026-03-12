# -*- coding: utf-8 -*-
# 代碼功能說明: DT-Agent 意圖快取 — thin wrapper, 委派給 DT_IntentRAG
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

"""
CachedIntentMatcher — thin wrapper over DT_IntentRAG

DT_IntentRAG now handles:
  - Qdrant-backed intent lookup (1 embed + 1 search)
  - In-memory fallback with embedding cache
  - complexity determination via detect_query_complexity()
This module exists for backward compatibility.
"""

from typing import Optional

import structlog

from dt_agent.src.core.dt_intent_rag import (
    DT_IntentRAG,
    IntentMatchResult,
    detect_query_complexity,
)

logger = structlog.get_logger(__name__)


class CachedIntentMatcher:
    """Thin wrapper over DT_IntentRAG for backward compatibility."""

    async def match_intent(self, nlq: str) -> IntentMatchResult:
        """Delegate to DT_IntentRAG singleton."""
        rag = await DT_IntentRAG.get_instance()
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
