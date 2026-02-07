# -*- coding: utf-8 -*-
# 代碼功能說明: 時間表達提取器
# 創建日期: 2026-02-06
# 創建人: AI-Box 開發團隊

"""TimeExtractor - 獨立時間表達提取模組

職責：
- 提取時間表達（簡體/繁體中文）
- 支持企業級時間表達（Q1~Q4、W32、YOY 等）
- 支持所有日期時間格式（YYYY-MM-DD、YYYY/MM/DD、HH:MM 等）
- 獨立模組，可測試，可移植

時間類型：
- SPECIFIC_DATE: 特定日期
- YEAR_MONTH: 年月
- DATE_RANGE: 日期範圍
- TIME: 時間（HH:MM:SS）
- DATETIME: 日期時間
- LAST_WEEK: 最近7天
- LAST_MONTH: 上月
- THIS_MONTH: 本月
- LAST_YEAR: 去年
- THIS_YEAR: 今年
- LAST_2_WEEKS: 上兩週
- LAST_2_MONTHS: 上兩月
- QUARTER: 季度
- QUARTER_END: 季末
- WEEK_OF_YEAR: 年度週
- YOY: 同比
- MOM: 環比
"""

import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class TimeMatch:
    """時間匹配結果"""

    time_type: str
    time_value: Optional[str] = None
    matched_keyword: Optional[str] = None
    confidence: float = 1.0


@dataclass
class TimeClarification:
    """時間澄清結果（用於模糊表達）"""

    need_clarification: bool = False
    fuzzy_keyword: Optional[str] = None
    question: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)


class TimeExtractor:
    """獨立時間表達提取器

    特點：
    - 純規則引擎，無 LLM 依賴
    - 支持簡體/繁體中文
    - 支持企業級時間表達
    - 支持所有日期時間格式
    - 獨立模組，可測試，可移植
    - 可配置規則
    """

    # ========== 1. 日期時間格式 ==========

    # 完整日期（格式：YYYY-MM-DD、YYYY/MM/DD、YYYY.MM.DD、YYYYMMDD）
    DATE_PATTERNS = [
        (r"(\d{4}-\d{2}-\d{2})", "SPECIFIC_DATE"),  # YYYY-MM-DD（橫槓）
        (r"(\d{4}/\d{2}/\d{2})", "SPECIFIC_DATE"),  # YYYY/MM/DD（斜槓）
        (r"(\d{4}\.\d{2}\.\d{2})", "SPECIFIC_DATE"),  # YYYY.MM.DD（點號）
        (r"(\d{8})", "SPECIFIC_DATE"),  # YYYYMMDD（無分隔）
        (r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})", "SPECIFIC_DATE"),  # ISO 8601
    ]

    # 年月（格式：YYYY-MM、YYYY/MM、YYYY.MM）
    YEAR_MONTH_PATTERNS = [
        (r"(\d{4}-\d{2})\b", "YEAR_MONTH"),  # YYYY-MM
        (r"(\d{4}/\d{2})\b", "YEAR_MONTH"),  # YYYY/MM
        (r"(\d{4}\.\d{2})\b", "YEAR_MONTH"),  # YYYY.MM
        (r"(\d{6})\b", "YEAR_MONTH"),  # YYYYMM
    ]

    # 時間（格式：HH:MM:SS、HH:MM）
    TIME_PATTERNS = [
        (r"(\d{2}:\d{2}:\d{2})", "TIME"),  # HH:MM:SS
        (r"(\d{2}:\d{2})", "TIME"),  # HH:MM
    ]

    # 日期時間
    DATETIME_PATTERNS = [
        (r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", "DATETIME"),  # YYYY-MM-DD HH:MM
        (r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})", "DATETIME"),  # YYYY/MM/DD HH:MM
    ]

    # 日期範圍
    DATE_RANGE_PATTERNS = [
        (
            r"(\d{4}-\d{2}-\d{2})\s*[至到]\s*(\d{4}-\d{2}-\d{2})",
            "DATE_RANGE",
        ),  # YYYY-MM-DD ~ YYYY-MM-DD
        (
            r"(\d{4}/\d{2}/\d{2})\s*[至到]\s*(\d{4}/\d{2}/\d{2})",
            "DATE_RANGE",
        ),  # YYYY/MM/DD ~ YYYY/MM/DD
        (r"(\d{8})\s*[至到]\s*(\d{8})", "DATE_RANGE"),  # YYYYMMDD ~ YYYYMMDD
    ]

    # ========== 2. 相對時間表達（長表達必須在前） ==========

    # 相對日期
    RELATIVE_DATE = {
        "day_before_yesterday": ["前天", "前日"],
        "yesterday": ["昨天", "昨日"],
        "today": ["今天", "今日", "此刻", "現在"],
        "tomorrow": ["明天", "明日"],
        "day_after_tomorrow": ["後天", "後日"],
        "last_event": ["上次", "上一次", "上回"],  # 單次事件
    }

    # 相對週
    RELATIVE_WEEK = {
        "last_2_weeks": ["上上週", "上上周", "前第二週", "上週之前"],
        "this_2_weeks": ["這兩週", "這两周", "本兩週"],
        "last_week": [
            "上週",
            "上周",
            "上星期",
            "最近一週",
            "最近一周",
            "過去一週",
            "過去一周",
            "過去七天",
            "最近7天",
        ],
        "this_week": ["本週", "本周", "這週"],
        "next_week": ["下週", "下周"],
        "week_start": ["週初", "周初"],
        "week_end": ["週末", "周末"],
    }

    # 相對月
    RELATIVE_MONTH = {
        "last_2_months": ["上上月", "上上个月", "前第二個月", "上月之前", "上上個月"],
        "last_month": ["上月", "上個月", "上个月"],
        "this_month": ["本月", "這個月", "这个月"],
        "next_month": ["下月", "下個月", "下个月"],
        "month_start": ["月初", "月頭"],
        "month_middle": ["月中"],
        "month_end": ["月底", "月尾"],
    }

    # 相對季
    RELATIVE_QUARTER = {
        "last_2_quarters": ["上上季"],
        "last_quarter": ["上一季", "上季", "上季度"],
        "this_quarter": ["這一季", "這季", "本季", "本季度", "這季度"],
        "next_quarter": ["下一季", "下季", "下季度"],
        "quarter_start": ["季初", "季度初"],
        "quarter_middle": ["季中", "季度中"],
        "quarter_end": ["季末", "季度末"],
    }

    # 相對年
    RELATIVE_YEAR = {
        "last_year": ["去年", "去年同期"],
        "this_year": ["今年", "本年", "這年"],
        "next_year": ["明年", "來年"],
        "year_start": ["年初", "年頭"],
        "year_middle": ["年中"],
        "year_end": ["年底", "年末", "年尾"],
    }

    # ========== 3. 企業級時間表達 ==========

    # 季度表達
    QUARTER_PATTERNS = [
        (r"Q([1-4])\b", "QUARTER"),  # Q1, Q2, Q3, Q4
        (r"Q[1-4]季", "QUARTER"),  # Q1季
        (r"第一季", "QUARTER"),
        (r"第二季", "QUARTER"),
        (r"第三季", "QUARTER"),
        (r"第四季", "QUARTER"),
    ]

    # 季末表達
    QUARTER_END_PATTERNS = [
        (r"Q([1-4])E", "QUARTER_END"),  # Q1E, Q2E
        (r"季末", "QUARTER_END"),
        (r"季度末", "QUARTER_END"),
    ]

    # 年度週表達
    WEEK_PATTERNS = [
        (r"W(\d{1,2})\b", "WEEK_OF_YEAR"),  # W01, W32
        (r"第(\d{1,2})週", "WEEK_OF_YEAR"),  # 第32週
        (r"第(\d{1,2})周", "WEEK_OF_YEAR"),  # 第32周
        (r"全年第(\d{1,2})週", "WEEK_OF_YEAR"),  # 全年第32週
    ]

    # 同比/環比表達
    COMPARISON_PATTERNS = [
        (r"YoY", "YOY"),
        (r"YOY", "YOY"),
        (r"同比", "YOY"),
        (r"去年同期", "YOY"),
        (r"MoM", "MOM"),
        (r"MOM", "MOM"),
        (r"環比", "MOM"),
        (r"上月同期", "MOM"),
        (r"QoQ", "QOQ"),  # 季比
        (r"WoW", "WOW"),  # 週比
    ]

    # ========== 4. 財會期間 ==========

    FISCAL_PATTERNS = [
        (r"FY(\d{2,4})\b", "FISCAL_YEAR"),  # FY24, FY2024
        (r"FY\s*[Qq]([1-4])", "FISCAL_QUARTER"),  # FY Q1, FYQ1
        (r"P(\d{1,2})\b", "PERIOD"),  # P1, P12
        (r"[上下]半年", "HALF_YEAR"),  # 上半年, 下半年
    ]

    # ========== 5. 企業指標期間 ==========

    INDICATOR_PATTERNS = [
        (r"\bYTD\b", "YTD"),  # Year to Date
        (r"\bMTD\b", "MTD"),  # Month to Date
        (r"\bQTD\b", "QTD"),  # Quarter to Date
        (r"\bWTD\b", "WTD"),  # Week to Date
        (r"年初至今", "YTD"),
        (r"年初到現在", "YTD"),
        (r"年初到現在", "YTD"),
        (r"今年到現在", "YTD"),
        (r"今年至今", "YTD"),
        (r"本月至今", "MTD"),
        (r"本月到現在", "MTD"),
        (r"本月截至目前", "MTD"),
        (r"本月截至現在", "MTD"),
        (r"至今", "MTD"),
        (r"到目前", "MTD"),
        (r"到現在", "MTD"),
        (r"季初至今", "QTD"),
        (r"季初到現在", "QTD"),
        (r"週初至今", "WTD"),
        (r"週初到現在", "WTD"),
    ]

    # ========== 6. 模糊時間（需要 Clarification）==========
    # 這些表達無法精確識別，需要回問用戶

    FUZZY_EXPRESSIONS = {
        "fuzzy_recent": ["最近", "近來", "近期"],
        "fuzzy_days_ago": ["前幾天", "前几天", "前些天", "前陣子"],
        "fuzzy_time_range": ["這段時間", "那段時間", "那段期間"],
        "fuzzy_period": ["有一段時間", "有一段期間"],
        "fuzzy_n_days": ["近三十天", "近七天", "近九十天", "近N天"],
    }

    def __init__(self, custom_rules: Optional[Dict[str, List[str]]] = None):
        """初始化時間提取器

        Args:
            custom_rules: 自定義規則（可覆蓋預設規則）
        """
        # 合併所有相對時間表達
        self.RELATIVE_EXPRESSIONS = {}
        self.RELATIVE_EXPRESSIONS.update(self.RELATIVE_DATE)
        self.RELATIVE_EXPRESSIONS.update(self.RELATIVE_WEEK)
        self.RELATIVE_EXPRESSIONS.update(self.RELATIVE_MONTH)
        self.RELATIVE_EXPRESSIONS.update(self.RELATIVE_QUARTER)
        self.RELATIVE_EXPRESSIONS.update(self.RELATIVE_YEAR)

        # 模糊表達（用於 Clarification）
        self.FUZZY_KEYWORDS = []
        for keywords in self.FUZZY_EXPRESSIONS.values():
            self.FUZZY_KEYWORDS.extend(keywords)

        if custom_rules:
            self.RELATIVE_EXPRESSIONS.update(custom_rules)

        # 預編譯正則表達式
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """編譯正則表達式（支持多個模式）"""
        patterns = {}

        def add_patterns(pattern_list):
            for pattern, time_type in pattern_list:
                if time_type not in patterns:
                    patterns[time_type] = []
                try:
                    patterns[time_type].append(re.compile(pattern))
                except re.error as e:
                    print(f"Warning: Invalid regex pattern '{pattern}': {e}")

        add_patterns(self.DATE_PATTERNS)
        add_patterns(self.YEAR_MONTH_PATTERNS)
        add_patterns(self.TIME_PATTERNS)
        add_patterns(self.DATETIME_PATTERNS)
        add_patterns(self.DATE_RANGE_PATTERNS)
        add_patterns(self.QUARTER_PATTERNS)
        add_patterns(self.QUARTER_END_PATTERNS)
        add_patterns(self.WEEK_PATTERNS)
        add_patterns(self.COMPARISON_PATTERNS)
        add_patterns(self.FISCAL_PATTERNS)
        add_patterns(self.INDICATOR_PATTERNS)

        return patterns

    def _match_patterns(self, text: str, time_type: str) -> Optional[re.Match]:
        """匹配模式列表"""
        patterns = self._compiled_patterns.get(time_type, [])
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return match
        return None

    def extract(self, text: str) -> Optional[TimeMatch]:
        """提取時間表達

        Args:
            text: 用戶輸入文本

        Returns:
            TimeMatch 或 None
        """
        # 步驟 1：日期範圍（必須在任何日期之前！）
        match = self._extract_date_range(text)
        if match:
            return match

        # 步驟 2：日期時間格式
        match = self._extract_date(text)
        if match:
            return match

        match = self._extract_year_month(text)
        if match:
            return match

        match = self._extract_time(text)
        if match:
            return match

        match = self._extract_datetime(text)
        if match:
            return match

        # 步驟 3：企業級時間表達
        match = self._extract_fiscal(text)
        if match:
            return match

        match = self._extract_quarter(text)
        if match:
            return match

        match = self._extract_quarter_end(text)
        if match:
            return match

        match = self._extract_week_of_year(text)
        if match:
            return match

        match = self._extract_comparison(text)
        if match:
            return match

        match = self._extract_indicator(text)
        if match:
            return match

        # 步驟 4：相對時間（按優先級）
        match = self._extract_relative_time(text)
        if match:
            return match

        return None

    def _get_clarification_question(self, fuzzy_type: str) -> tuple:
        """獲取澄清問題和建議"""
        questions = {
            "fuzzy_recent": ("請問具體是幾天？", ["最近7天", "最近30天", "最近90天", "最近一季"]),
            "fuzzy_days_ago": (
                "請問具體是幾天前？",
                ["前3天", "前5天", "前7天", "前14天", "前30天"],
            ),
            "fuzzy_time_range": ("請問具體時間範圍？", ["請提供開始日期", "請提供結束日期"]),
            "fuzzy_period": ("請問具體時間範圍？", ["請提供具體日期區間"]),
        }
        return questions.get(fuzzy_type, ("請提供具體時間", []))

    def check_fuzzy(self, text: str) -> TimeClarification:
        """檢查模糊表達（返回 Clarification）"""
        for fuzzy_type, keywords in self.FUZZY_EXPRESSIONS.items():
            for keyword in keywords:
                if keyword in text:
                    question, suggestions = self._get_clarification_question(fuzzy_type)
                    return TimeClarification(
                        need_clarification=True,
                        fuzzy_keyword=keyword,
                        question=question,
                        suggestions=suggestions,
                    )
        return TimeClarification(need_clarification=False)

    def extract_with_clarification(self, text: str) -> tuple:
        """提取時間表達（包含 Clarification）

        Returns:
            tuple: (TimeMatch or None, TimeClarification)
        """
        # 先檢查模糊表達
        clarification = self.check_fuzzy(text)
        if clarification.need_clarification:
            return None, clarification

        # 提取精確時間
        match = self.extract(text)
        return match, TimeClarification(need_clarification=False)

    def _extract_date(self, text: str) -> Optional[TimeMatch]:
        """提取完整日期"""
        match = self._match_patterns(text, "SPECIFIC_DATE")
        if match:
            return TimeMatch(
                time_type="SPECIFIC_DATE",
                time_value=match.group(1),
                matched_keyword=match.group(1),
                confidence=1.0,
            )
        return None

    def _extract_year_month(self, text: str) -> Optional[TimeMatch]:
        """提取年月"""
        match = self._match_patterns(text, "YEAR_MONTH")
        if match:
            return TimeMatch(
                time_type="YEAR_MONTH",
                time_value=match.group(1),
                matched_keyword=match.group(1),
                confidence=1.0,
            )
        return None

    def _extract_time(self, text: str) -> Optional[TimeMatch]:
        """提取時間"""
        match = self._match_patterns(text, "TIME")
        if match:
            return TimeMatch(
                time_type="TIME",
                time_value=match.group(1),
                matched_keyword=match.group(1),
                confidence=1.0,
            )
        return None

    def _extract_datetime(self, text: str) -> Optional[TimeMatch]:
        """提取日期時間"""
        match = self._match_patterns(text, "DATETIME")
        if match:
            return TimeMatch(
                time_type="DATETIME",
                time_value=match.group(1),
                matched_keyword=match.group(1),
                confidence=1.0,
            )
        return None

    def _extract_date_range(self, text: str) -> Optional[TimeMatch]:
        """提取日期範圍"""
        match = self._match_patterns(text, "DATE_RANGE")
        if match:
            time_value = f"{match.group(1)} ~ {match.group(2)}"
            return TimeMatch(
                time_type="DATE_RANGE",
                time_value=time_value,
                matched_keyword=f"{match.group(1)} 到 {match.group(2)}",
                confidence=1.0,
            )
        return None

    def _extract_quarter(self, text: str) -> Optional[TimeMatch]:
        """提取季度"""
        match = self._match_patterns(text, "QUARTER")
        if match:
            if match.lastindex:
                quarter = match.group(1)
                cn_map = {"一": "1", "二": "2", "三": "3", "四": "4"}
                quarter = cn_map.get(quarter, quarter)
            else:
                matched = match.group(0)
                cn_map = {"一": "1", "二": "2", "三": "3", "四": "4"}
                for cn, num in cn_map.items():
                    if cn in matched:
                        quarter = num
                        break
                else:
                    quarter = ""

            return TimeMatch(
                time_type="QUARTER",
                time_value=f"Q{quarter}" if quarter else "Q",
                matched_keyword=match.group(0),
                confidence=1.0,
            )
        return None

    def _extract_quarter_end(self, text: str) -> Optional[TimeMatch]:
        """提取季末"""
        match = self._match_patterns(text, "QUARTER_END")
        if match:
            quarter = match.group(1) if match.lastindex else ""
            cn_map = {"一": "1", "二": "2", "三": "3", "四": "4"}
            quarter = cn_map.get(quarter, quarter)

            return TimeMatch(
                time_type="QUARTER_END",
                time_value=f"Q{quarter}E" if quarter else "QE",
                matched_keyword=match.group(0),
                confidence=1.0,
            )
        return None

    def _extract_week_of_year(self, text: str) -> Optional[TimeMatch]:
        """提取年度週"""
        match = self._match_patterns(text, "WEEK_OF_YEAR")
        if match:
            week = match.group(1)
            week = week.zfill(2)

            return TimeMatch(
                time_type="WEEK_OF_YEAR",
                time_value=f"W{week}",
                matched_keyword=match.group(0),
                confidence=1.0,
            )
        return None

    def _extract_comparison(self, text: str) -> Optional[TimeMatch]:
        """提取同比/環比"""
        if self._match_patterns(text, "YOY"):
            return TimeMatch(
                time_type="YOY",
                matched_keyword="YOY/同比",
                confidence=1.0,
            )

        if self._match_patterns(text, "MOM"):
            return TimeMatch(
                time_type="MOM",
                matched_keyword="MOM/環比",
                confidence=1.0,
            )

        if self._match_patterns(text, "QOQ"):
            return TimeMatch(
                time_type="QOQ",
                matched_keyword="QOQ/季比",
                confidence=1.0,
            )

        if self._match_patterns(text, "WOW"):
            return TimeMatch(
                time_type="WOW",
                matched_keyword="WOW/週比",
                confidence=1.0,
            )

        return None

    def _extract_fiscal(self, text: str) -> Optional[TimeMatch]:
        """提取財會期間"""
        match = self._match_patterns(text, "FISCAL_YEAR")
        if match:
            year = match.group(1)
            if len(year) == 2:
                year = f"20{year}"
            return TimeMatch(
                time_type="FISCAL_YEAR",
                time_value=f"FY{year}",
                matched_keyword=match.group(0),
                confidence=1.0,
            )

        match = self._match_patterns(text, "FISCAL_QUARTER")
        if match:
            quarter = match.group(1)
            return TimeMatch(
                time_type="FISCAL_QUARTER",
                time_value=f"FQ{quarter}",
                matched_keyword=match.group(0),
                confidence=1.0,
            )

        match = self._match_patterns(text, "PERIOD")
        if match:
            return TimeMatch(
                time_type="PERIOD",
                time_value=f"P{match.group(1)}",
                matched_keyword=match.group(0),
                confidence=1.0,
            )

        match = self._match_patterns(text, "HALF_YEAR")
        if match:
            return TimeMatch(
                time_type="HALF_YEAR",
                time_value=match.group(0),
                matched_keyword=match.group(0),
                confidence=1.0,
            )

        return None

    def _extract_indicator(self, text: str) -> Optional[TimeMatch]:
        """提取企業指標期間"""
        match = self._match_patterns(text, "YTD")
        if match:
            return TimeMatch(
                time_type="YTD",
                matched_keyword="YTD/年初至今",
                confidence=1.0,
            )

        match = self._match_patterns(text, "MTD")
        if match:
            return TimeMatch(
                time_type="MTD",
                matched_keyword="MTD/月初至今",
                confidence=1.0,
            )

        match = self._match_patterns(text, "QTD")
        if match:
            return TimeMatch(
                time_type="QTD",
                matched_keyword="QTD/季初至今",
                confidence=1.0,
            )

        match = self._match_patterns(text, "WTD")
        if match:
            return TimeMatch(
                time_type="WTD",
                matched_keyword="WTD/週初至今",
                confidence=1.0,
            )

        return None

    def _extract_relative_time(self, text: str) -> Optional[TimeMatch]:
        """提取相對時間"""
        for time_type, keywords in self.RELATIVE_EXPRESSIONS.items():
            for keyword in keywords:
                if keyword in text:
                    return TimeMatch(
                        time_type=time_type,
                        matched_keyword=keyword,
                        confidence=1.0,
                    )
        return None

    def extract_all(self, text: str) -> List[TimeMatch]:
        """提取所有時間表達"""
        results = []

        # 按優先級檢查
        check_order = [
            "SPECIFIC_DATE",
            "YEAR_MONTH",
            "TIME",
            "DATETIME",
            "DATE_RANGE",
            "QUARTER",
            "QUARTER_END",
            "WEEK_OF_YEAR",
            "YOY",
            "MOM",
            "QOQ",
            "WOW",
            "FISCAL_YEAR",
            "FISCAL_QUARTER",
            "PERIOD",
            "HALF_YEAR",
            "YTD",
            "MTD",
            "QTD",
            "WTD",
        ]

        for time_type in check_order:
            match = self._match_patterns(text, time_type)
            if match:
                if time_type == "DATE_RANGE":
                    results.append(
                        TimeMatch(
                            time_type=time_type,
                            time_value=f"{match.group(1)} ~ {match.group(2)}",
                            matched_keyword=match.group(0),
                            confidence=1.0,
                        )
                    )
                elif time_type in ["SPECIFIC_DATE", "YEAR_MONTH", "TIME"]:
                    results.append(
                        TimeMatch(
                            time_type=time_type,
                            time_value=match.group(1),
                            matched_keyword=match.group(1),
                            confidence=1.0,
                        )
                    )
                else:
                    results.append(
                        TimeMatch(
                            time_type=time_type,
                            matched_keyword=match.group(0),
                            confidence=1.0,
                        )
                    )

        return results

    def get_all_rules(self) -> Dict[str, List[str]]:
        """獲取所有規則（用於測試）"""
        return self.RELATIVE_EXPRESSIONS.copy()


# 便捷函數
def extract_time(text: str) -> Optional[TimeMatch]:
    """便捷函數：提取時間表達"""
    extractor = TimeExtractor()
    return extractor.extract(text)


def extract_time_as_dict(text: str) -> Dict[str, Any]:
    """便捷函數：提取時間並轉為字典"""
    extractor = TimeExtractor()
    match = extractor.extract(text)
    if match:
        return {"time_type": match.time_type, "time_value": match.time_value}
    return {}


if __name__ == "__main__":
    extractor = TimeExtractor()

    print("=" * 80)
    print("TimeExtractor 測試")
    print("=" * 80)

    test_cases = [
        # 日期格式
        ("2024-01-01 的採購", "SPECIFIC_DATE"),
        ("2024/01/01 的銷售", "SPECIFIC_DATE"),
        ("2024.01.01 庫存", "SPECIFIC_DATE"),
        ("20240101 訂單", "SPECIFIC_DATE"),
        # 年月
        ("2024-01 採購", "YEAR_MONTH"),
        ("202401", "YEAR_MONTH"),
        # 時間
        ("14:30 開會", "TIME"),
        ("2024-01-01 14:30", "DATETIME"),
        # 日期範圍
        ("2024-01-01 到 2024-03-31", "DATE_RANGE"),
        ("20240101 至 20240331", "DATE_RANGE"),
        # 季度
        ("Q1 採購", "QUARTER"),
        ("第一季銷售", "QUARTER"),
        ("Q3庫存", "QUARTER"),
        # 季末
        ("Q1E 結算", "QUARTER_END"),
        ("季末盤點", "QUARTER_END"),
        # 年度週
        ("W32 銷售", "WEEK_OF_YEAR"),
        ("全年第32週", "WEEK_OF_YEAR"),
        # 同比/環比
        ("YOY 成長", "YOY"),
        ("MOM 變化", "MOM"),
        ("QoQ 增長", "QOQ"),
        # 財會
        ("FY2024 報告", "FISCAL_YEAR"),
        ("FY Q1", "FISCAL_QUARTER"),
        ("P12", "PERIOD"),
        ("上半年", "HALF_YEAR"),
        # 指標期間
        ("YTD 統計", "YTD"),
        ("MTD 銷售", "MTD"),
        # 相對日期
        ("昨天的庫存", "yesterday"),
        ("前天的銷售", "day_before_yesterday"),
        # 相對週
        ("上上週的採購", "last_2_weeks"),
        ("上週庫存", "last_week"),
        # 相對月
        ("上上月的訂單", "last_2_months"),
        ("上月的採購", "last_month"),
        # 相對年
        ("去年的銷售", "last_year"),
        ("年底盤點", "year_end"),
    ]

    print(f"\n{'輸入':<25} | {'識別結果':<20} | {'時間值':<15}")
    print("-" * 65)

    for text, expected in test_cases:
        result = extractor.extract(text)
        if result:
            status = "✅" if result.time_type == expected else "❌"
            print(f"{text:<25} | {result.time_type:<20} | {result.time_value or '-':<15} {status}")
        else:
            print(f"{text:<25} | {'None':<20} | {'-':<15} ❌")

    print("\n" + "=" * 80)
