"""Intent RAG 客戶端 - 用於意圖分類輔助"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

_intent_rag_client: Optional["IntentRAGClient"] = None


class IntentRAGClient:
    def __init__(
        self,
        intents_file: Optional[Path] = None,
        collection_name: str = "mm_agent_intents",
    ):
        self._client = None
        self._metadata = None
        self._intents_file = intents_file
        self._collection_name = collection_name

    def _lazy_init(self):
        if self._client is not None:
            return

        if self._intents_file is None:
            self._intents_file = (
                Path(__file__).resolve().parent.parent.parent
                / "data"
                / "intents"
                / "mm_agent_intents.json"
            )

        try:
            import sys

            ai_box_root = Path(__file__).resolve().parent.parent.parent
            sys.path.insert(0, str(ai_box_root))

            from data.intents.sync_intent import IntentRAGStore

            self._store = IntentRAGStore(
                intents_file=self._intents_file,
                collection_name=self._collection_name,
            )

            try:
                self._store.sync(rebuild=False)
            except Exception as e:
                logger.debug(f"Intent RAG sync not needed or failed: {e}")

            self._client = self._store
            logger.info(f"Intent RAG client initialized with {self._intents_file}")

        except Exception as e:
            logger.warning(f"Failed to initialize Intent RAG client: {e}")
            self._client = None

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.3,
    ) -> List[Dict[str, Any]]:
        self._lazy_init()

        if self._client is None:
            return []

        try:
            results = self._client.retrieve(
                query=query,
                top_k=top_k,
                min_score=min_score,
            )

            if results:
                logger.info(
                    f"Intent RAG retrieved {len(results)} results for query: {query[:30]}..., "
                    f"top intent: {results[0]['intent']}"
                )

            return results

        except Exception as e:
            logger.warning(f"Intent RAG retrieval failed: {e}")
            return []

    def get_few_shot_examples(
        self,
        query: str,
        top_k: int = 2,
        min_score: float = 0.5,
    ) -> List[Dict[str, str]]:
        results = self.retrieve(query=query, top_k=top_k, min_score=min_score)

        examples = []
        for result in results:
            examples.append(
                {
                    "user_input": result.get("query", ""),
                    "intent": result.get("intent", ""),
                    "description": result.get("description", ""),
                }
            )

        return examples


def get_intent_rag_client() -> IntentRAGClient:
    global _intent_rag_client

    if _intent_rag_client is None:
        _intent_rag_client = IntentRAGClient()

    return _intent_rag_client


def reset_intent_rag_client():
    global _intent_rag_client
    _intent_rag_client = None
