# 代碼功能說明: 多語言翻譯系統
# 創建日期: 2026-02-20
# 創建人: Daniel Chung

"""多語言翻譯系統

支持的語言:
- zh-TW: 繁體中文 (默認)
- en-US: 英語
- ja-JP: 日語

使用方式:
    from data_agent.services.i18n import t, get_locale

    # 翻譯
    message = t("QUERY_TIMEOUT", locale="zh-TW")

    # 獲取語言
    locale = get_locale(request)
"""

from typing import Dict, Optional
from functools import lru_cache

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "zh-TW": {
        # 一般訊息
        "SUCCESS": "成功",
        "ERROR": "錯誤",
        # SSE 階段
        "REQUEST_RECEIVED": "已接收到請求",
        "SCHEMA_CONFIRMED": "已確認找到對應的表格",
        "SQL_GENERATED": "已產生 SQL",
        "QUERY_EXECUTING": "正在執行查詢中",
        "QUERY_COMPLETED": "已查詢完成",
        "RESULT_READY": "已返回結果",
        # 錯誤訊息
        "QUERY_TIMEOUT": "查詢執行逾時，請減少查詢範圍",
        "CONNECTION_ERROR": "資料庫連線失敗，請稍後重試",
        "OUT_OF_MEMORY": "查詢記憶體不足：請減少查詢範圍",
        "SCHEMA_NOT_FOUND": "數據來源不足：表格不存在或尚未載入",
        "AMBIGUOUS_REFERENCE": "維度模糊：請更具體指定查詢維度",
        "COLUMN_NOT_FOUND": "缺乏關鍵欄位：請確認查詢維度是否正確",
        "BINDER_ERROR": "缺乏關鍵欄位：請確認查詢維度是否正確",
        "NULL_VALUE": "數據包含空值，請檢查查詢條件",
        "INTENT_NOT_FOUND": "無法識別查詢意圖",
        "INTERNAL_ERROR": "發生內部錯誤",
        "QUERY_ERROR": "查詢執行失敗",
        # 查詢相關
        "ROWS_RETURNED": "返回 {count} 筆資料",
        "EXECUTION_TIME": "耗時：{time}ms",
        "TOTAL_ROWS": "總筆數：{count}",
        # 建議
        "SUGGESTION_REDUCE_SCOPE": "請嘗試縮小查詢範圍",
        "SUGGESTION_CHECK_PARAMS": "請檢查查詢參數是否正確",
        "SUGGESTION_TRY_AGAIN": "請稍後再試",
    },
    "en-US": {
        # 一般訊息
        "SUCCESS": "Success",
        "ERROR": "Error",
        # SSE 階段
        "REQUEST_RECEIVED": "Request received",
        "SCHEMA_CONFIRMED": "Schema confirmed",
        "SQL_GENERATED": "SQL generated",
        "QUERY_EXECUTING": "Executing query",
        "QUERY_COMPLETED": "Query completed",
        "RESULT_READY": "Result ready",
        # 錯誤訊息
        "QUERY_TIMEOUT": "Query timeout. Please reduce the query scope.",
        "CONNECTION_ERROR": "Database connection failed. Please try again later.",
        "OUT_OF_MEMORY": "Query out of memory. Please reduce the query scope.",
        "SCHEMA_NOT_FOUND": "Data source insufficient: Table does not exist or not loaded",
        "AMBIGUOUS_REFERENCE": "Ambiguous dimension: Please specify query dimensions more specifically",
        "COLUMN_NOT_FOUND": "Missing key column: Please verify query dimensions",
        "BINDER_ERROR": "Missing key column: Please verify query dimensions",
        "NULL_VALUE": "Data contains null values. Please check query conditions.",
        "INTENT_NOT_FOUND": "Unable to recognize query intent",
        "INTERNAL_ERROR": "Internal error occurred",
        "QUERY_ERROR": "Query execution failed",
        # 查詢相關
        "ROWS_RETURNED": "{count} rows returned",
        "EXECUTION_TIME": "Execution time: {time}ms",
        "TOTAL_ROWS": "Total rows: {count}",
        # 建議
        "SUGGESTION_REDUCE_SCOPE": "Please try to reduce the query scope",
        "SUGGESTION_CHECK_PARAMS": "Please verify query parameters",
        "SUGGESTION_TRY_AGAIN": "Please try again later",
    },
    "ja-JP": {
        # 一般訊息
        "SUCCESS": "成功",
        "ERROR": "エラー",
        # SSE 段階
        "REQUEST_RECEIVED": "リクエストを受信しました",
        "SCHEMA_CONFIRMED": "スキーマを確認しました",
        "SQL_GENERATED": "SQLを生成しました",
        "QUERY_EXECUTING": "クエリを実行中",
        "QUERY_COMPLETED": "クエリが完了しました",
        "RESULT_READY": "結果を返します",
        # エラーメッセージ
        "QUERY_TIMEOUT": "クエリがタイムアウトしました。クエリ範囲を縮小してください。",
        "CONNECTION_ERROR": "データベース接続に失敗しました。後でもう一度お試しください。",
        "OUT_OF_MEMORY": "クエリのメモリ不足。クエリ範囲を縮小してください。",
        "SCHEMA_NOT_FOUND": "データソース不足：テーブルが存在しないか、まだロードされていません",
        "AMBIGUOUS_REFERENCE": "次元の曖昧さ：クエリの次元をより具体的に指定してください",
        "COLUMN_NOT_FOUND": "キーカラムが見つかりません：クエリの次元を確認してください",
        "BINDER_ERROR": "キーカラムが見つかりません：クエリの次元を確認してください",
        "NULL_VALUE": "データにNULL値が含まれています。クエリ条件を確認してください。",
        "INTENT_NOT_FOUND": "クエリの意図を認識できません",
        "INTERNAL_ERROR": "内部エラーが発生しました",
        "QUERY_ERROR": "クエリの実行に失敗しました",
        # クエリ関連
        "ROWS_RETURNED": "{count}件の結果を返しました",
        "EXECUTION_TIME": "実行時間：{time}ms",
        "TOTAL_ROWS": "合計件数：{count}",
        # 提案
        "SUGGESTION_REDUCE_SCOPE": "クエリ範囲を縮小してみてください",
        "SUGGESTION_CHECK_PARAMS": "クエリパラメータを確認してください",
        "SUGGESTION_TRY_AGAIN": "後でもう一度お試しください",
    },
}


def get_locale(locale: Optional[str] = None, fallback: str = "zh-TW") -> str:
    """獲取有效的語言代碼

    Args:
        locale: 輸入的語言代碼
        fallback: 默認語言

    Returns:
        有效的語言代碼
    """
    if not locale:
        return fallback

    # 標準化
    locale = locale.strip().replace("_", "-")

    # 精確匹配
    if locale in TRANSLATIONS:
        return locale

    # 語系匹配 (例如 "zh" -> "zh-TW")
    lang = locale.split("-")[0]
    for key in TRANSLATIONS:
        if key.startswith(lang):
            return key

    return fallback


def t(key: str, locale: str = "zh-TW", **kwargs) -> str:
    """翻譯訊息

    Args:
        key: 訊息鍵
        locale: 語言代碼
        **kwargs: 格式化參數

    Returns:
        翻譯後的訊息
    """
    effective_locale = get_locale(locale)

    # 獲取翻譯
    messages = TRANSLATIONS.get(effective_locale, TRANSLATIONS["zh-TW"])
    message = messages.get(key, key)

    # 格式化
    if kwargs:
        try:
            message = message.format(**kwargs)
        except (KeyError, ValueError):
            pass

    return message


def get_supported_locales() -> list:
    """獲取支持的語言列表"""
    return list(TRANSLATIONS.keys())


def add_translation(locale: str, translations: Dict[str, str]):
    """添加新的翻譯

    Args:
        locale: 語言代碼
        translations: 翻譯字典
    """
    if locale not in TRANSLATIONS:
        TRANSLATIONS[locale] = {}
    TRANSLATIONS[locale].update(translations)
