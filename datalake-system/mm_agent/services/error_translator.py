# -*- coding: utf-8 -*-
"""
錯誤訊息翻譯器

將技術性資料庫/系統錯誤轉換為人類可理解的友善訊息。

建立日期: 2026-02-11
建立人: Daniel Chung
"""


class ErrorMessageTranslator:
    """錯誤訊息翻譯器"""

    ORA_ERROR_MAP = {
        "ORA-01114": "資料庫儲存空間不足，無法執行查詢。系統管理員需要清理或擴充儲存空間。",
        "ORA-01017": "資料庫連線驗證失敗，請聯繫系統管理員檢查資料庫設定。",
        "ORA-12170": "資料庫連線超時，網路連線不穩定，請稍後再試。",
        "ORA-01028": "內存緩衝區提取不完整，請重新執行查詢。",
        "ORA-00942": "資料表不存在或無權限訪問，請確認查詢的資料表名稱是否正確。",
        "ORA-00904": "無效的欄位名稱，請確認查詢的欄位名稱是否正確。",
        "ORA-01722": "欄位類型轉換錯誤，數值格式無效。",
        "ORA-01400": "無法插入空值，請確認所有必要欄位都已填寫。",
        "ORA-00001": "違反唯一性約束，資料已經存在。",
        "ORA-01031": "權限不足，無法執行此操作。",
        "ORA-01000": "開啟的游標數量超過上限，請稍後再試。",
        "ORA-01013": "使用者取消當前操作。",
        "ORA-01410": "無效的 ROWID 格式。",
        "ORA-01555": "快照過舊，資料已被其他交易修改，請重新執行查詢。",
        "ORA-00054": "資源忙碌中，鎖定衝突，請稍後再試。",
        "ORA-28002": "密碼已過期，請更新密碼後再試。",
    }

    GENERAL_ERROR_MAP = {
        "connection refused": "無法連線到資料庫伺服器，請確認伺服器是否正常運作。",
        "connection timeout": "資料庫連線超時，網路連線不穩定。",
        "no such file or directory": "無法找到資料庫配置或必要的系統檔案。",
        "authentication failed": "資料庫登入驗證失敗，請檢查帳號密碼。",
        "disk full": "系統磁碟空間不足，無法寫入資料。",
        "out of memory": "系統記憶體不足，無法執行查詢。",
        "broken pipe": "連線中斷，請重新執行查詢。",
        "too many connections": "資料庫連線數已達上限，請稍後再試。",
        "lock wait timeout": "資料庫鎖定等待超時，請稍後再試。",
        "deadlock detected": "偵測到資料庫死結，系統正在處理中。",
    }

    DATA_AGENT_ERROR_MAP = {
        "PARSE_NLQ": "無法理解您的查詢內容，請嘗試使用更簡單的描述方式。",
        "MATCH_CONCEPTS": "找不到符合的查詢類型，請嘗試重新描述您的需求。",
        "RESOLVE_BINDINGS": "查詢欄位設定有問題，無法完成查詢。",
        "VALIDATE": "查詢條件不完整，請提供更多資訊。",
        "BUILD_AST": "無法建立查詢語法，請重新描述您的需求。",
        "EMIT_SQL": "無法產生查詢語法，請聯繫系統管理員。",
        "INTERNAL_ERROR": "系統發生內部錯誤，請稍後再試或聯繫系統管理員。",
        "UNKNOWN_ERROR": "發生未預期的錯誤，請稍後再試。",
    }

    @classmethod
    def translate(cls, error_message: str, error_code: str = None) -> str:
        """
        翻譯錯誤訊息

        Args:
            error_message: 原始錯誤訊息
            error_code: 錯誤碼（可選）

        Returns:
            翻譯後的友善錯誤訊息
        """
        if not error_message:
            return "發生未知錯誤，請稍後再試。"

        error_msg = str(error_message).strip()
        error_code = error_code.strip() if error_code else ""

        # 1. 先檢查 Data-Agent 錯誤碼
        if error_code in cls.DATA_AGENT_ERROR_MAP:
            return cls.DATA_AGENT_ERROR_MAP[error_code]

        # 2. 檢查 Oracle ORA 錯誤
        for ora_code, friendly_msg in cls.ORA_ERROR_MAP.items():
            if ora_code in error_msg:
                return friendly_msg

        # 3. 檢查一般性錯誤
        for general_pattern, friendly_msg in cls.GENERAL_ERROR_MAP.items():
            if general_pattern.lower() in error_msg.lower():
                return friendly_msg

        # 4. 檢查關鍵字模式
        friendly_msg = cls._translate_by_keywords(error_msg)
        if friendly_msg:
            return friendly_msg

        # 5. 如果都沒有匹配，返回通用訊息
        return cls._create_fallback_message(error_msg, error_code)

    @classmethod
    def _translate_by_keywords(cls, error_msg: str) -> str:
        """根據關鍵字翻譯錯誤訊息"""
        error_lower = error_msg.lower()

        patterns = [
            (
                ["timeout", "超時", "time out"],
                "查詢執行時間過長，請嘗試縮小查詢範圍或減少查詢數量。",
            ),
            (["disk", "空間", "storage"], "系統儲存空間不足，請聯繫系統管理員。"),
            (["memory", "記憶體"], "系統記憶體不足，請縮小查詢範圍後再試。"),
            (["permission", "權限", "access denied"], "沒有執行此操作的權限，請確認您的帳號權限。"),
            (["null", "空值", "none"], "資料不存在或為空值。"),
            (["invalid", "無效", "不正確"], "輸入的資料格式有誤，請檢查後重新輸入。"),
            (["not found", "不存在", "找不到"], "找不到指定的資料，請確認查詢條件是否正確。"),
            (["duplicate", "重複", "已存在"], "資料已經存在，無法新增重複的記錄。"),
            (["syntax", "語法", "格式"], "查詢語法有誤，請重新描述您的需求。"),
            (["network", "網路", "連線"], "網路連線不穩定，請稍後再試。"),
            (["service", "服務", "server"], "伺服器暫時無法處理請求，請稍後再試。"),
        ]

        for keywords, message in patterns:
            for keyword in keywords:
                if keyword.lower() in error_lower:
                    return message

        return None

    @classmethod
    def _create_fallback_message(cls, error_msg: str, error_code: str) -> str:
        """建立後備錯誤訊息"""
        # 如果錯誤訊息太長，截取並簡化
        if len(error_msg) > 100:
            error_msg = error_msg[:100] + "..."

        if error_code:
            return f"發生錯誤（錯誤碼：{error_code}），請稍後再試。如果問題持續，請聯繫系統管理員。"

        return f"執行時發生錯誤：{error_msg}。請稍後再試或聯繫系統管理員。"

    @classmethod
    def translate_query_result(
        cls,
        success: bool,
        error_message: str = None,
        error_code: str = None,
        result_count: int = 0,
    ) -> dict:
        """
        翻譯查詢結果中的錯誤

        Args:
            success: 是否成功
            error_message: 錯誤訊息
            error_code: 錯誤碼
            result_count: 結果數量

        Returns:
            包含翻譯後訊息的字典
        """
        if success:
            return {
                "success": True,
                "friendly_message": None,
                "error_message": None,
                "error_code": None,
            }

        friendly_message = cls.translate(error_message, error_code)

        return {
            "success": False,
            "friendly_message": friendly_message,
            "error_message": error_message,
            "error_code": error_code,
        }


# 便捷函數
def translate_error(error_message: str, error_code: str = None) -> str:
    """翻譯錯誤訊息"""
    return ErrorMessageTranslator.translate(error_message, error_code)


def translate_query_result_error(
    success: bool, error_message: str = None, error_code: str = None
) -> dict:
    """翻譯查詢結果錯誤"""
    return ErrorMessageTranslator.translate_query_result(success, error_message, error_code)
