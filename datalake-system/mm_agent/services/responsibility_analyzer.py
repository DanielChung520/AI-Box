# 代碼功能說明: 職責理解服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""職責理解服務 - 根據語義分析結果識別職責"""

import logging

from ..models import Responsibility, SemanticAnalysisResult

logger = logging.getLogger(__name__)


class ResponsibilityAnalyzer:
    """職責理解服務"""

    def __init__(self) -> None:
        """初始化職責分析器"""
        self._logger = logger

    async def understand(
        self,
        semantic_result: SemanticAnalysisResult,
    ) -> Responsibility:
        """職責理解：根據語義分析結果識別職責

        Args:
            semantic_result: 語義分析結果

        Returns:
            職責定義
        """
        intent = semantic_result.intent

        if intent == "query_part":
            return Responsibility(
                type="query_part",
                description="查詢物料基本信息",
                steps=[
                    "調用 Data Agent 查詢物料數據",
                    "格式化返回結果",
                ],
                required_data=["part_number"],
            )

        elif intent == "query_stock":
            return Responsibility(
                type="query_stock",
                description="查詢庫存信息",
                steps=[
                    "調用 Data Agent 查詢庫存數據",
                    "分析庫存狀態",
                    "格式化返回結果",
                ],
                required_data=[],  # 不強制要求參數，Data-Agent 處理通用查詢
            )

        elif intent == "query_stock_history":
            # 如果語義分析需要澄清時間範圍，使用語義分析的澄清問題
            if semantic_result.clarification_needed and semantic_result.clarification_questions:
                return Responsibility(
                    type="clarification_needed",
                    description="需要澄清時間範圍",
                    steps=["生成時間範圍澄清問題"],
                    clarification_questions=semantic_result.clarification_questions,
                )
            # 否則，執行查詢庫存歷史
            return Responsibility(
                type="query_stock_history",
                description="查詢庫存/進貨歷史",
                steps=[
                    "調用 Data Agent 查詢交易歷史",
                    "格式化返回結果",
                ],
                required_data=["part_number"],
            )
            logger.info(
                f"[ResponsibilityAnalyzer] query_stock_history - clarification_questions: {semantic_result.clarification_questions}"
            )

            if semantic_result.clarification_needed and semantic_result.clarification_questions:
                return Responsibility(
                    type="clarification_needed",
                    description="需要澄清時間範圍",
                    steps=["生成時間範圍澄清問題"],
                    clarification_questions=semantic_result.clarification_questions,
                )
            # 否則，執行查詢庫存歷史
            return Responsibility(
                type="query_stock_history",
                description="查詢庫存/進貨歷史",
                steps=[
                    "調用 Data Agent 查詢交易歷史",
                    "格式化返回結果",
                ],
                required_data=["part_number"],
            )

        elif intent == "analyze_shortage":
            return Responsibility(
                type="analyze_shortage",
                description="缺料分析",
                steps=[
                    "調用 Data Agent 查詢當前庫存",
                    "調用 Data Agent 查詢安全庫存",
                    "計算缺料數量",
                    "判斷缺料狀態",
                    "生成分析報告",
                ],
                required_data=["part_number"],
            )

        elif intent == "generate_purchase_order":
            return Responsibility(
                type="generate_purchase_order",
                description="生成採購單",
                steps=[
                    "驗證缺料狀態（可選）",
                    "生成採購單記錄",
                    "記錄採購單信息",
                    "返回採購單結果",
                ],
                required_data=["part_number", "quantity"],
            )

        else:
            # 未識別意圖，需要澄清
            return Responsibility(
                type="clarification_needed",
                description="需要澄清用戶意圖",
                steps=["生成澄清問題"],
                clarification_questions=[
                    "請明確您要執行哪個操作？",
                    "1. 查詢料號信息",
                    "2. 查詢庫存",
                    "3. 缺料分析",
                    "4. 生成採購單",
                ],
            )
