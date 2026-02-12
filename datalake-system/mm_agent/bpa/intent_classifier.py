# 代碼功能說明: BPA 意圖分類器
# 創建日期: 2026-02-05
# 創建人: AI-Box 開發團隊

"""BPA 意圖分類器 - 業務意圖分類"""

import re
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class QueryIntent(str, Enum):
    """查詢意圖枚舉"""

    QUERY_STOCK = "QUERY_STOCK"  # 庫存查詢（當前庫存）
    QUERY_STOCK_HISTORY = "QUERY_STOCK_HISTORY"  # 庫存歷史查詢
    QUERY_PURCHASE = "QUERY_PURCHASE"  # 採購交易查詢
    QUERY_SALES = "QUERY_SALES"  # 銷售交易查詢
    ANALYZE_SHORTAGE = "ANALYZE_SHORTAGE"  # 缺料分析
    GENERATE_ORDER = "GENERATE_ORDER"  # 生成訂單
    CLARIFICATION = "CLARIFICATION"  # 需要澄清


class TaskComplexity(str, Enum):
    """任務複雜度枚舉"""

    SIMPLE = "simple"  # 簡單查詢
    COMPLEX = "complex"  # 複雜任務


class IntentClassification(BaseModel):
    """意圖分類結果"""

    intent: QueryIntent
    complexity: TaskComplexity
    confidence: float = 1.0
    is_complex: bool = False
    needs_clarification: bool = False
    missing_fields: list = []


class IntentClassifier:
    """意圖分類器"""

    # 庫存關鍵詞
    STOCK_KEYWORDS = ["庫存", "存量", "還有多少", "有多少", "庫存多少"]

    # 採購關鍵詞
    PURCHASE_KEYWORDS = ["採購", "買進", "進貨", "收料", "採購了多少"]

    # 銷售關鍵詞
    SALES_KEYWORDS = ["銷售", "賣出", "出貨", "賣了多少"]

    # 缺料關鍵詞
    SHORTAGE_KEYWORDS = ["缺料", "不足", "不夠", "缺什麼"]

    # 訂單關鍵詞
    ORDER_KEYWORDS = ["訂單", "採購單", "請購", "下單"]

    # 複雜任務關鍵詞
    COMPLEX_KEYWORDS = ["分析", "比較", "排名", "ABC", "分類", "趨勢", "預測", "統計", "報告"]

    # 多實體關鍵詞
    MULTI_ENTITY_PATTERNS = [r"\d+個", r"\w+系列", r"\w+和\w+", r"\w+或\w+"]

    def classify(self, user_input: str, context: Optional[dict] = None) -> IntentClassification:
        """分類用戶意圖

        Args:
            user_input: 用戶輸入
            context: 上下文（可選）

        Returns:
            IntentClassification: 分類結果
        """
        input_lower = user_input.lower()
        input_clean = user_input.strip()

        # 判斷複雜度
        is_complex, reasons = self._判断复杂度(input_clean)

        # 判斷意圖
        intent = self._判断意图(input_clean)

        # 檢查是否需要澄清
        needs_clarification, missing = self._检查需要澄清(intent, input_clean, context)

        return IntentClassification(
            intent=intent,
            complexity=TaskComplexity.COMPLEX if is_complex else TaskComplexity.SIMPLE,
            confidence=0.95,
            is_complex=is_complex,
            needs_clarification=needs_clarification,
            missing_fields=missing,
        )

    def _判断复杂度(self, text: str) -> tuple:
        """判斷任務複雜度"""
        reasons = []

        # 檢查複雜關鍵詞
        for keyword in self.COMPLEX_KEYWORDS:
            if keyword in text:
                reasons.append(f"包含關鍵詞: {keyword}")
                return True, reasons

        # 檢查多實體模式
        for pattern in self.MULTI_ENTITY_PATTERNS:
            if re.search(pattern, text):
                reasons.append(f"包含多實體模式")
                return True, reasons

        return False, []

    def _判断意图(self, text: str) -> QueryIntent:
        """判斷查詢意圖"""
        # 按優先級判斷
        if any(kw in text for kw in self.ORDER_KEYWORDS):
            return QueryIntent.GENERATE_ORDER

        if any(kw in text for kw in self.SHORTAGE_KEYWORDS):
            return QueryIntent.ANALYZE_SHORTAGE

        if any(kw in text for kw in self.SALES_KEYWORDS):
            return QueryIntent.QUERY_SALES

        if any(kw in text for kw in self.PURCHASE_KEYWORDS):
            return QueryIntent.QUERY_PURCHASE

        if any(kw in text for kw in self.STOCK_KEYWORDS):
            return QueryIntent.QUERY_STOCK

        # 默認返回庫存查詢
        return QueryIntent.QUERY_STOCK

    def _检查需要澄清(self, intent: QueryIntent, text: str, context: Optional[dict]) -> tuple:
        """檢查是否需要澄清"""
        missing = []

        # 檢查關鍵欄位
        if intent in [QueryIntent.QUERY_PURCHASE, QueryIntent.QUERY_SALES]:
            # 需要交易類型或料號
            has_material = bool(re.search(r"[A-Z]{2,4}-?\d{2,6}", text))
            has_transaction = any(kw in text for kw in ["採購", "買進", "進貨", "銷售", "賣出"])
            if not has_material and not has_transaction:
                missing.append("料號或交易類型")

        if intent == QueryIntent.QUERY_STOCK:
            # 庫存查詢可以只提供倉庫，不一定要料號
            has_material = bool(re.search(r"[A-Z]{2,4}-?\d{2,6}", text))
            has_warehouse = bool(re.search(r"\b(W\d{2})\b", text))
            if not has_material and not has_warehouse:
                missing.append("料號或倉庫")

        # 檢查上下文
        if context and not missing:
            # 有上下文時，不需要澄清
            return False, []

        return len(missing) > 0, missing
