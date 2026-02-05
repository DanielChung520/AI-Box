# 代碼功能說明: 正面表列檢查 - 策略檢查層
# 創建日期: 2026-01-31
# 創建人: Daniel Chung

"""正面表列檢查 - L4 策略檢查層"""

import re
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
        # 記憶/記錄相關（2026-02-04 新增）
        "記住",
        "記錄",
        "記得",
    ]

    CLARIFICATION_MESSAGE = (
        "💡 無法理解您的查詢，請使用以下關鍵詞描述您的需求：\n"
        "• 業務關鍵詞：採購、庫存、訂單、進貨、出貨、收料、領料\n"
        "• 數量關鍵詞：多少、總數、數量\n"
        "• 時間關鍵詞：上月、最近、去年\n"
        "• 料號格式：RM05-008、ABC-123"
    )

    # 料號正則模式
    PART_NUMBER_PATTERNS = [
        r"[A-Z]{2,4}-?\d{2,6}(?:-\d{2,6})?",  # ABC-123, RM05-008
        r"\d{2,4}-\d{2,6}",  # 10-0001
    ]

    # 動作關鍵詞
    ACTION_KEYWORDS = [
        "採購",
        "買",
        "買進",
        "進貨",
        "收料",
        "賣",
        "賣出",
        "出貨",
        "出庫",
        "銷售",
        "庫存",
        "存量",
        "剩餘",
        "還有",
        "領料",
        "領用",
        "生產領料",
        "報廢",
        "報損",
        "損耗",
        "訂單",
        "下單",
    ]

    # 數量關鍵詞
    QUANTITY_KEYWORDS = [
        "多少",
        "總數",
        "數量",
        "合計",
        "總計",
        "共",
        "有幾",
        "總共有",
        "總共",
        "共有",
        "全部",
        "餘額",
        "剩餘",
    ]

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

    def check_required_params(self, query: str) -> Tuple[bool, str]:
        """檢查必要參數是否齊全

        Returns:
            Tuple[是否缺少參數, 澄清訊息]
        """
        query_upper = query.upper()

        # 1. 檢查是否有料號
        has_part_number = False
        for pattern in self.PART_NUMBER_PATTERNS:
            if re.search(pattern, query_upper):
                has_part_number = True
                break

        # 2. 檢查是否有明確動作
        has_action = any(kw in query for kw in self.ACTION_KEYWORDS)

        # 3. 檢查是否有數量詞（對於查詢類）
        has_quantity = any(kw in query for kw in self.QUANTITY_KEYWORDS)

        # 判定缺少哪些必要參數
        missing = []
        if not has_part_number:
            missing.append("料號（如：RM05-008、ABC-123）")

        if not has_action:
            missing.append("動作（如：採購、庫存、銷售、領料）")

        # 如果有料號和動作，但沒有數量詞，給予提示但不強制
        if has_part_number and has_action and not has_quantity:
            pass  # 可選參數，不強制要求

        if missing:
            message = (
                "💡 請補充以下資訊，我才能幫您查詢：\n"
                + "\n".join([f"• {item}" for item in missing])
                + "\n\n範例：\n"
                + "• RM05-008 上月買進多少\n"
                + "• ABC-123 庫存還有多少"
            )
            return True, message

        return False, ""

    def needs_clarification(self, query: str) -> Tuple[bool, str]:
        """判斷是否需要澄清（正面表列 + 必要參數檢查）"""
        # 首先檢查是否在正面表列內
        passed, matched = self.check(query)
        if not passed:
            return True, self.CLARIFICATION_MESSAGE

        # 再檢查必要參數是否齊全
        missing_params, param_message = self.check_required_params(query)
        if missing_params:
            return True, param_message

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
