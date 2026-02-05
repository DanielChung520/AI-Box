# 代碼功能說明: 調試 Knowledge Signal internal_only 判斷
# 創建日期: 2026-02-03
# 創建人: Daniel Chung

"""調試 Knowledge Signal internal_only 判斷"""

import logging
from agents.task_analyzer.knowledge_signal_mapper import (
    KnowledgeSignalMapper,
)
from agents.task_analyzer.models import SemanticUnderstandingOutput

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def debug_weather_query():
    """調試天氣查詢為什麼沒有識別為外部搜尋"""

    mapper = KnowledgeSignalMapper()

    semantic = SemanticUnderstandingOutput(
        topics=["weather", "current"],
        entities=[],
        action_signals=["search", "query"],
        modality="question",
        certainty=0.9,
    )

    # 手動檢查匹配邏輯
    external_keywords = [
        "天氣",
        "股價",
        "匯率",
        "新聞",
        "weather",
        "stock",
        "exchange rate",
    ]

    print("\n=== 手動檢查匹配邏輯 ===")
    for topic in semantic.topics:
        topic_lower = topic.lower()
        print(f"檢查 topic: '{topic}' (lower: '{topic_lower}')")
        for keyword in external_keywords:
            keyword_lower = keyword.lower()
            matches = keyword_lower in topic_lower
            print(f"  - keyword: '{keyword}' (lower: '{keyword_lower}') → {matches}")

    # 調用 mapper
    print("\n=== 調用 mapper.map() ===")
    signal = mapper.map(semantic)
    print(f"Signal: {signal}")
    print(f"internal_only: {signal.internal_only}")
    print(f"reasons: {signal.reasons}")


if __name__ == "__main__":
    debug_weather_query()
