# 代碼功能說明: 正面表列檢查 - 策略檢查層
# 創建日期: 2026-01-31
# 創建人: Daniel Chung

"""正面表列檢查 - L4 策略檢查層"""

from typing import List, Tuple


class PositiveListChecker:
    """正面表列檢查器"""

    POSITIVE_KEYWORDS = [
        # 核心業務
        "採購",
        "買",
        "賣",
        "庫存",
        "訂單",
        "進貨",
        "出貨",
        "收料",
        "領料",
        "報廢",
        "盤點",
        # 數量
        "多少",
        "總數",
        "數量",
        "合計",
        "總計",
        # 時間
        "上月",
        "上個月",
        "前月",
        "最近",
        "今年",
        "去年",
        # 料號前綴
        "10-",
        "RM",
        "ABC-",
        "RM05",
        "ABC",
        # Data Dictionary
        "欄位",
        "表格",
        "結構",
        "說明",
        "定義",
        "schema",
        # 問句開頭
        "給我看",
        "告訴我",
        "查詢",
        "顯示",
    ]

    CLARIFICATION_MESSAGE = (
        "💡 無法理解您的查詢，請使用以下關鍵詞描述您的需求：\n"
        "• 業務關鍵詞：採購、庫存、訂單、進貨、出貨、收料、領料\n"
        "• 數量關鍵詞：多少、總數、數量\n"
        "• 時間關鍵詞：上月、最近、去年\n"
        "• 料號格式：RM05-008、ABC-123"
    )

    def __init__(self):
        self._logger = None

    def check(self, query: str) -> Tuple[bool, List[str]]:
        """檢查查詢是否在正面表列內

        Args:
            query: 用戶查詢

        Returns:
            Tuple[是否通過, 匹配到的關鍵詞列表]
        """
        query_lower = query.lower()
        matched = [kw for kw in self.POSITIVE_KEYWORDS if kw in query_lower]
        return len(matched) > 0, matched

    def check_strict(self, query: str) -> bool:
        """嚴格檢查（必須包含核心關鍵詞）"""
        core_keywords = ["採購", "買", "賣", "庫存", "訂單", "進貨", "出貨", "RM", "ABC"]
        return any(kw in query for kw in core_keywords)

    def get_clarification_message(self) -> str:
        """獲取澄清提示消息"""
        return self.CLARIFICATION_MESSAGE

    def needs_clarification(self, query: str) -> Tuple[bool, str]:
        """判斷是否需要澄清"""
        passed, matched = self.check(query)
        if not passed:
            return True, self.CLARIFICATION_MESSAGE
        return False, ""


if __name__ == "__main__":
    checker = PositiveListChecker()

    test_cases = [
        "RM05-008 上月買進多少",
        "今天天氣如何",
        "庫存還有多少",
        "RM05-008 採購情況",
        "告訴我 ABC-123 的庫存",
    ]

    for query in test_cases:
        passed, matched = checker.check(query)
        print(f"\n查詢: {query}")
        print(f"  通過: {passed}")
        print(f"  匹配關鍵詞: {matched}")
