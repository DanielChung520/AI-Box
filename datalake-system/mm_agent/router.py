# 代碼功能說明: 意圖路由器
# 創建日期: 2026-02-05
# 創建人: AI-Box 開發團隊

"""Router - 意圖路由器

職責：判斷任務類型
- GREETING：打招呼
- ERROR_INPUT：错误输入
- QUERY：简单查询
- COMPLEX：复杂任务
"""

import re
from typing import Optional
from mm_agent.models.query_spec import TaskType, RouterResult


class Router:
    """意圖路由器 - 任務類型分類"""

    # 打招呼關鍵詞
    GREETING_KEYWORDS = [
        "你好",
        "早安",
        "午安",
        "晚安",
        "嗨",
        "hi",
        "hello",
        "您好",
        "各位好",
        "大家好",
        "在嗎",
        "在嗎?",
        "在不在",
    ]

    # 複雜任務關鍵詞
    COMPLEX_KEYWORDS = [
        "如何",
        "怎麼",
        "步驟",
        "設置",
        "設定",
        "操作",
        "方法",
        "指引",
        "說明",
        "介紹",
        "教學",
        "流程",
        "規則",
        "規定",
        "標準",
        "注意事項",
        "先",
        "然後",
        "接著",
        "最後",
        "完成後",
        "並且",
        "以及",
    ]

    # 錯誤輸入模式
    ERROR_PATTERNS = [
        r"^[^\w\u4e00-\u9fff]+$",  # 只有符號
        r"^[\d\s]{1,5}$",  # 只有數字和空格
        r"(.)\1{4,}",  # 重複字符
    ]

    def __init__(self):
        self._greeting_set = set(self.GREETING_KEYWORDS)
        self._complex_set = set(self.COMPLEX_KEYWORDS)

    def classify(self, user_input: str) -> RouterResult:
        """分類用戶輸入

        Args:
            user_input: 用戶原始輸入

        Returns:
            RouterResult：包含任務類型和處理結果
        """
        if not user_input or not user_input.strip():
            return RouterResult(
                task_type=TaskType.ERROR_INPUT,
                response="我沒有聽懂，請重新輸入您的問題。",
                needs_llm=False,
            )

        input_clean = user_input.strip()
        input_lower = input_clean.lower()

        # 檢查錯誤輸入
        if self._is_error_input(input_clean):
            return RouterResult(
                task_type=TaskType.ERROR_INPUT,
                response="我無法理解這個輸入，請換個方式描述您的問題。",
                needs_llm=False,
            )

        # 檢查打招呼
        if self._is_greeting(input_clean):
            greetings = [
                "您好！我是庫存管理助手。請問有什麼可以幫您？",
                "嗨！很高興為您服務。需要查詢庫存或交易數據嗎？",
                "您好！請直接告訴我您想查詢的內容，例如：「RM05-008 上月買進多少」。",
            ]
            import random

            return RouterResult(
                task_type=TaskType.GREETING, response=random.choice(greetings), needs_llm=False
            )

        # 檢查複雜任務
        if self._is_complex_task(input_clean):
            return RouterResult(task_type=TaskType.COMPLEX, needs_llm=True)

        # 預設是簡單查詢
        return RouterResult(task_type=TaskType.QUERY, needs_llm=True)

    def _is_greeting(self, text: str) -> bool:
        """檢查是否為打招呼"""
        # 純打招呼（沒有其他內容）
        if text in self._greeting_set:
            return True

        # 只有打招呼語，沒有其他內容
        greeting_phrases = [
            "你好",
            "早安",
            "午安",
            "晚安",
            "嗨嗨",
            "嗨您好",
            "您好",
            "各位好",
            "大家好",
        ]
        if text in greeting_phrases:
            return True

        return False

    def _is_complex_task(self, text: str) -> bool:
        """檢查是否為複雜任務"""
        # 檢查複雜任務關鍵詞
        for keyword in self._complex_set:
            if keyword in text:
                return True

        # 檢查多步驟模式
        step_patterns = [
            r"先.*再.*",  # 先...再...
            r"先.*然後.*",  # 先...然後...
            r"先.*接著.*",  # 先...接著...
            r".*然後.*最後.*",  # ...然後...最後...
            r".*並且.*",  # ...並且...
            r".*以及.*",  # ...以及...
        ]
        for pattern in step_patterns:
            if re.search(pattern, text):
                return True

        return False

    def _is_error_input(self, text: str) -> bool:
        """檢查是否為錯誤輸入"""
        # 檢查錯誤模式
        for pattern in self.ERROR_PATTERNS:
            if re.match(pattern, text):
                return True

        # 過短的無意義輸入
        if len(text.strip()) < 2:
            return True

        # 只有問號
        if text.strip() in ["?", "？", "？？", "??"]:
            return True

        return False
