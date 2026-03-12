# 代碼功能說明: 前置查詢驗證（Pre-validation Guardrail）— 在 SQL 生成前攔截結構性不可回答的查詢
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

"""
QueryGuard — 前置錯誤識別模組

在 IntentResolver 匹配 intent 之後、SQLGenerator 生成 SQL 之前，
檢查查詢的結構可回答性。若偵測到「目標 mart 表無法滿足查詢需求」，
直接回傳 clarification_needed 響應，避免 LLM 臆造不存在的欄位或函數。

偵測模式：
1. TIME 查詢 vs 無時間欄位 — NLQ 含時間關鍵詞，但目標 mart 無時間欄位
2. 高階統計概念 — DuckDB 不支援的統計函數（預測區間、迴歸、ARIMA 等）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# ──────────────────────────────────────────────────
# 各 mart 表的時間欄位定義（硬性事實，非業務數據）
# ──────────────────────────────────────────────────
MART_TIME_COLUMNS: dict[str, list[str]] = {
    "mart_inventory_wide": [],  # 無時間欄位
    "mart_work_order_wide": [],  # 無時間欄位
    "mart_shipping_wide": ["doc_date", "expected_shipping_date"],
    "mart_price_wide": ["doc_date", "valid_date"],
}

# ──────────────────────────────────────────────────
# 時間相關關鍵詞（觸發時間查詢偵測）
# ──────────────────────────────────────────────────
TIME_KEYWORDS: list[str] = [
    # 明確時間單位
    "月",
    "年",
    "季",
    "週",
    "日",
    "天",
    # 相對時間
    "最近",
    "去年",
    "今年",
    "本月",
    "上月",
    "下月",
    "本季",
    "上季",
    "本年",
    "前年",
    "昨天",
    "今天",
    "明天",
    "上半年",
    "下半年",
    # 時間範圍
    "期間",
    "時段",
    "時間範圍",
    # 時間趨勢
    "趨勢",
    "變化",
    # 英文月份/年份模式
    "2024",
    "2025",
    "2026",
    # 時間函數暗示
    "月份",
    "年份",
    "季度",
    "日期",
]

# 更精確的時間模式（需要搭配時間上下文才算）
TIME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\d{4}年"),  # 2025年
    re.compile(r"\d{1,2}月"),  # 3月, 12月
    re.compile(r"最近\d+[個天週月年季]"),  # 最近3個月
    re.compile(r"過去\d+[個天週月年季]"),  # 過去6個月
    re.compile(r"前\d+[個天週月年季]"),  # 前3個月
    re.compile(r"近\d+[個天週月年季]"),  # 近3個月
    re.compile(r"每[月年季週日天]"),  # 每月, 每年
]

# ──────────────────────────────────────────────────
# 高階統計關鍵詞（DuckDB 不支援的概念）
# ──────────────────────────────────────────────────
ADVANCED_STATS_KEYWORDS: list[str] = [
    "預測區間",
    "預測",
    "信賴區間",
    "信心區間",
    "迴歸",
    "回歸",
    "線性迴歸",
    "ARIMA",
    "arima",
    "機器學習",
    "深度學習",
    "神經網路",
    "類神經",
    "貝氏",
    "貝葉斯",
    "馬可夫",
    "蒙特卡羅",
    "蒙地卡羅",
    "時間序列預測",
    "異常偵測",
    "異常檢測",
    "Holt-Winters",
    "holt-winters",
    "霍特-溫特斯",
]

# ──────────────────────────────────────────────────
# 多步驟分析關鍵詞（需分解為多個子查詢才能回答）
# ──────────────────────────────────────────────────
MULTI_STEP_KEYWORDS: list[str] = [
    # 統計分散/集中度
    "波動",
    "偏離",
    "分散",
    # 複合分析模式（僅覆蓋已知失敗案例，避免投機性擴充）
]

# ──────────────────────────────────────────────────
# 各 mart 表的建議替代說明
# ──────────────────────────────────────────────────
MART_TIME_SUGGESTIONS: dict[str, str] = {
    "mart_inventory_wide": (
        "庫存表（mart_inventory_wide）不含時間欄位，僅記錄當前庫存快照。"
        "如需查詢有時間維度的資料，建議改查：\n"
        "• 出貨資料（mart_shipping_wide）：有 doc_date、expected_shipping_date\n"
        "• 報價資料（mart_price_wide）：有 doc_date、valid_date"
    ),
    "mart_work_order_wide": (
        "工單表（mart_work_order_wide）不含時間欄位，僅記錄當前工單狀態。"
        "如需查詢有時間維度的資料，建議改查：\n"
        "• 出貨資料（mart_shipping_wide）：有 doc_date、expected_shipping_date\n"
        "• 報價資料（mart_price_wide）：有 doc_date、valid_date"
    ),
}


@dataclass
class GuardResult:
    """前置驗證結果"""

    passed: bool
    """是否通過驗證（True=可繼續生成 SQL）"""
    reason: Optional[str] = None
    """攔截原因（僅 passed=False 時有值）"""
    clarification_needed: list[str] = field(default_factory=list)
    """需要確認的事項列表"""
    suggestion: Optional[str] = None
    """建議替代查詢方向"""
    guard_type: Optional[str] = None
    """攔截類型：time_dimension_missing / advanced_stats_unsupported / multi_step_required"""


def _has_time_intent(nlq: str) -> bool:
    """檢查 NLQ 是否包含時間相關意圖"""
    nlq_lower = nlq.lower()

    # 檢查精確時間模式（正則）
    for pattern in TIME_PATTERNS:
        if pattern.search(nlq):
            return True

    # 檢查時間關鍵詞
    for keyword in TIME_KEYWORDS:
        if keyword in nlq_lower:
            return True

    return False


def _has_advanced_stats(nlq: str) -> bool:
    """檢查 NLQ 是否包含高階統計概念"""
    nlq_lower = nlq.lower()
    for keyword in ADVANCED_STATS_KEYWORDS:
        if keyword.lower() in nlq_lower:
            return True
    return False

def _has_multi_step_intent(nlq: str) -> bool:
    """檢查 NLQ 是否包含需多步驟分解的分析意圖"""
    for keyword in MULTI_STEP_KEYWORDS:
        if keyword in nlq:
            return True
    return False


def _get_mart_table_from_intent(intent_name: str, intents_data: dict) -> Optional[str]:
    """從 intent 名稱取得對應的 mart_table"""
    intents = intents_data.get("intents", {})
    intent_def = intents.get(intent_name, {})
    return intent_def.get("mart_table")


def validate_query(
    nlq: str,
    intent_name: str,
    mart_table: Optional[str] = None,
) -> GuardResult:
    """
    前置驗證查詢的結構可回答性。

    Args:
        nlq: 原始自然語言查詢
        intent_name: 匹配到的 intent 名稱
        mart_table: 目標 mart 表名（來自 IntentMatchResult.mart_table）

    Returns:
        GuardResult: 驗證結果
    """
    # Guard 1: 高階統計概念攔截
    if _has_advanced_stats(nlq):
        logger.info(
            "QueryGuard 攔截：高階統計概念",
            nlq=nlq,
            intent=intent_name,
            guard_type="advanced_stats_unsupported",
        )
        return GuardResult(
            passed=False,
            reason="查詢包含高階統計概念（如預測、迴歸等），DuckDB SQL 查詢無法支援此類分析",
            clarification_needed=[
                "此查詢需要進階統計分析功能，目前系統僅支援 SQL 聚合查詢（SUM/AVG/COUNT/MIN/MAX/STDDEV 等）",
                "建議改用基礎統計查詢，例如：平均值、標準差、最大/最小值等",
            ],
            suggestion="建議將查詢改為基礎統計分析，例如「計算庫存的平均值和標準差」",
            guard_type="advanced_stats_unsupported",
        )

    # Guard 2: 多步驟分析攔截（需分解為多個子查詢）
    if _has_multi_step_intent(nlq):
        logger.info(
            "QueryGuard 攔截：多步驟分析查詢",
            nlq=nlq,
            intent=intent_name,
            guard_type="multi_step_required",
        )
        return GuardResult(
            passed=False,
            reason="此查詢需要多個步驟才能完整回答，建議分解為以下子查詢",
            clarification_needed=[
                "此查詢涉及複合統計分析（如波動/偏離/分散），無法用單一 SQL 直接回答",
                "建議分解為多步驟查詢：",
                "  步驟 1：先查詢基礎資料（如全部庫存）",
                "  步驟 2：計算彙總統計值（如平均值、標準差）",
                "  步驟 3：再依此條件篩選或排序",
            ],
            suggestion="建議將查詢分解為多個子步驟，例如：先查詢各料號庫存，再計算其標準差或偏差值",
            guard_type="multi_step_required",
        )

    # Guard 3: 時間查詢 vs 無時間欄位
    if mart_table and _has_time_intent(nlq):
        time_columns = MART_TIME_COLUMNS.get(mart_table, [])
        if not time_columns:
            suggestion = MART_TIME_SUGGESTIONS.get(mart_table)
            logger.info(
                "QueryGuard 攔截：時間查詢但目標表無時間欄位",
                nlq=nlq,
                intent=intent_name,
                mart_table=mart_table,
                guard_type="time_dimension_missing",
            )
            return GuardResult(
                passed=False,
                reason=f"查詢包含時間條件，但 {mart_table} 不包含任何時間欄位",
                clarification_needed=[
                    f"您的查詢似乎需要按時間篩選或分析，但 {mart_table} 僅記錄當前狀態快照，沒有時間欄位",
                    "請改用包含時間欄位的資料表，或移除時間條件",
                ],
                suggestion=suggestion,
                guard_type="time_dimension_missing",
            )

    # 所有驗證通過
    return GuardResult(passed=True)
