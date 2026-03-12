# 代碼功能說明: 簡化版語義分析服務
# 創建日期: 2026-03-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-12

"""簡化版語義分析服務 - 使用 MMIntentRAG"""

import logging
import re
from typing import Any, Dict, List, Optional
from ..models import SemanticAnalysisResult
from ..mm_intent_rag_client import get_mm_intent_rag_client

logger = logging.getLogger(__name__)


class SemanticAnalyzer:
    """語義分析服務 - 簡化版

    職責：
    1. 使用 MMIntentRAG 進行意圖分類
    2. 使用 MMIntentRAG 判斷 return_mode (summary/list)
    3. 檢查是否需要 clarification

    注意：參數提取由 Data-Agent v5 處理
    """

    def __init__(self) -> None:
        """初始化語義分析器"""
        self._logger = logger

        # 初始化 MMIntentRAG 客戶端
        try:
            self._intent_rag_client = get_mm_intent_rag_client()
            logger.info("[SemanticAnalyzer] MMIntentRAG 客戶端已初始化")
        except Exception as e:
            logger.warning(f"[SemanticAnalyzer] 無法初始化 MMIntentRAG: {e}")
            self._intent_rag_client = None

    async def analyze(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> SemanticAnalysisResult:
        """語義分析

        Args:
            instruction: 用戶指令
            context: 上下文信息（可選）

        Returns:
            語義分析結果
        """
        # 預設值
        intent = None
        confidence = 0.0
        clarification_needed = False
        clarification_questions: List[str] = []

        # 1. 使用 MMIntentRAG 進行意圖分類
        if self._intent_rag_client:
            try:
                # 意圖分類
                rag_intent = self._intent_rag_client.classify_intent(instruction)
                if rag_intent:
                    # 映射到系統意圖
                    system_intent = self._intent_rag_client.get_system_intent(rag_intent)
                    intent = rag_intent
                    confidence = 0.9
                    logger.info(f"[SemanticAnalyzer] 意圖分類: {rag_intent} -> {system_intent}")
                else:
                    # 未匹配到意圖，檢查是否需要澄清
                    logger.info("[SemanticAnalyzer] 未匹配到意圖，可能需要澄清")
                    clarification_needed = True
                    clarification_questions = [
                        "請問您想要查詢什麼？",
                        "例如：查詢庫存、查詢採購記錄等",
                    ]

            except Exception as e:
                logger.warning(f"[SemanticAnalyzer] 意圖分類失敗: {e}")
                clarification_needed = True
                clarification_questions = ["抱歉，我無法理解您的請求，請重新描述"]
        else:
            # 無法使用 MMIntentRAG
            logger.warning("[SemanticAnalyzer] MMIntentRAG 不可用")
            clarification_needed = True
            clarification_questions = ["系統暫時無法處理您的請求"]

        # Note: return_mode 和 responsibility_type 由 Data-Agent 後續處理
        # 3. 檢查模糊詞彙（需要 clarification）
        # 但如果用戶已提供具體時間範圍，則視為已澄清，不觸發 clarification
        ambiguous_keywords = ["最近", "這幾天", "近來", "近期"]
        specific_time_patterns = [
            "一天", "兩天", "三天", "四天", "五天",
            "一週", "兩週", "三週", "一個月", "兩個月", "三個月",
            "六個月", "半年", "一年",
            "今天", "昨天", "前天", "本週", "上週", "本月", "上個月",
        ]
        # 也匹配數字+時間單位，如「7天」、「30天」、「2個月」
        numeric_time_pattern = re.compile(r"\d+\s*[天週月年日]")  # noqa: W605
        has_ambiguous = any(kw in instruction for kw in ambiguous_keywords)
        has_specific_time = (
            any(tp in instruction for tp in specific_time_patterns)
            or bool(numeric_time_pattern.search(instruction))
        )
        if has_ambiguous and not has_specific_time:
            clarification_needed = True
            clarification_questions = [
                "「最近」是指什麼時間範圍？",
                "• 今天",
                "• 最近一週",
                "• 最近一個月",
                "• 最近三個月",
            ]

        return SemanticAnalysisResult(
            intent=intent,
            confidence=confidence,
            parameters={},  # 參數由 Data-Agent 提取
            original_instruction=instruction,
            clarification_needed=clarification_needed,
            clarification_questions=clarification_questions,
        )

