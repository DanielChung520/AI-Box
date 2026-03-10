# 代碼功能說明: 職責理解服務
# 創建日期: 2026-03-02
# 簡化版 - 支持 MMIntentRAG 返回的意圖

"""職責理解服務 - 根據語義分析結果識別職責"""

import logging
from ..models import Responsibility, SemanticAnalysisResult

logger = logging.getLogger(__name__)


class ResponsibilityAnalyzer:
    """職責理解服務"""

    def __init__(self) -> None:
        self._logger = logger

    async def understand(
        self,
        semantic_result: SemanticAnalysisResult,
    ) -> Responsibility:
        """職責理解：根據語義分析結果識別職責

        支持 MMIntentRAG 返回的意圖：
        - QUERY_INVENTORY -> query_stock
        - QUERY_INVENTORY_BY_WAREHOUSE -> query_stock
        - query_stock -> query_stock
        """
        intent = semantic_result.intent
        intent_lower = intent.lower() if intent else ""

        # 如果 semantic_result 已經標記需要澄清，直接返回
        if semantic_result.clarification_needed and semantic_result.clarification_questions:
            return Responsibility(
                type="clarification_needed",
                description="需要澄清用戶意圖",
                steps=["生成澄清問題"],
                clarification_questions=semantic_result.clarification_questions,
            )

        # 庫存查詢 (QUERY_INVENTORY from MMIntentRAG)
        if intent_lower in ("query_inventory", "query_inventory_by_warehouse", "query_stock"):
            return Responsibility(
                type="query_stock",
                description="查詢庫存信息",
                steps=[
                    "調用 Data Agent 查詢庫存數據",
                    "分析庫存狀態",
                    "格式化返回結果",
                ],
                required_data=[],  # Data-Agent 處理參數提取
            )

        # 出貨單查詢
        if intent_lower == "query_shipping":
            return Responsibility(
                type="query_shipping",
                description="查詢出貨信息",
                steps=[
                    "調用 Data Agent 查詢出貨數據",
                    "格式化返回結果",
                ],
                required_data=[],
            )

        # 料號查詢

        # 料號查詢
        if intent_lower == "query_part":
            return Responsibility(
                type="query_part",
                description="查詢物料基本信息",
                steps=[
                    "調用 Data Agent 查詢物料數據",
                    "格式化返回結果",
                ],
                required_data=["part_number"],
            )

        # 缺料分析
        if intent_lower == "analyze_shortage":
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

        # 採購單生成
        if intent_lower == "generate_purchase_order":
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

        # 知識庫查詢
        if "knowledge" in intent_lower:
            return Responsibility(
                type="knowledge_query",
                description="知識庫查詢",
                steps=[
                    "搜索知識庫",
                    "返回相關知識",
                ],
                required_data=[],
            )

        # 分析已有查詢結果
        if intent_lower in ("analyze_existing_result", "analyze_result", "explain_data"):
            return Responsibility(
                type="analyze_existing_result",
                description="分析已有查詢結果，回答用戶的分析性追問",
                steps=[
                    "從 context 取得上一次查詢結果",
                    "分析數據並生成分析性回覆",
                    "返回分析結果",
                ],
                required_data=["last_result"],
            )

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
