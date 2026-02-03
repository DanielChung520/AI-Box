# 代碼功能說明: 負面表列檢查 - 權限控制層
# 創建日期: 2026-02-01
# 創建人: Daniel Chung

"""負面表列檢查 - L4 權限控制層"""

from typing import List, Tuple


class NegativeListChecker:
    """負面表列檢查器 - 用於權限控制"""

    # 禁止的關鍵詞（未授權的操作或資料）
    FORBIDDEN_KEYWORDS = [
        # 敏感資料
        "薪資",
        "工資",
        "薪水",
        "員工",
        "人事",
        "機密",
        # 系統操作
        "刪除",
        "修改",
        "更新",
        "新增",
        "創建",
        "drop",
        "delete",
        "update",
        "insert",
        # 非業務查詢
        "天氣",
        "新聞",
        "八卦",
    ]

    # 禁止的表名
    FORBIDDEN_TABLES = [
        "employee",
        "salary",
        "payroll",
        "hr",
    ]

    DENIED_MESSAGE = (
        "❌ 您的查詢包含未授權的操作或資料，請聯繫管理員。\n"
        "支援的查詢範圍：庫存、採購、銷售、領料、報廢、盤點等物料管理相關操作。"
    )

    def __init__(self):
        self._logger = None

    def check(self, query: str) -> Tuple[bool, List[str]]:
        """檢查查詢是否在負面表列內

        Args:
            query: 用戶查詢

        Returns:
            Tuple[是否禁止, 匹配到的關鍵詞列表]
        """
        query_lower = query.lower()
        matched = [kw for kw in self.FORBIDDEN_KEYWORDS if kw.lower() in query_lower]
        return len(matched) > 0, matched

    def check_table(self, table_name: str) -> bool:
        """檢查表名是否被禁止

        Args:
            table_name: 表名

        Returns:
            是否禁止
        """
        return table_name.lower() in [t.lower() for t in self.FORBIDDEN_TABLES]

    def get_denied_message(self) -> str:
        """獲取拒絕訊息"""
        return self.DENIED_MESSAGE

    def is_denied(self, query: str) -> Tuple[bool, str]:
        """判斷是否拒絕查詢

        Args:
            query: 用戶查詢

        Returns:
            Tuple[是否拒絕, 拒絕訊息]
        """
        # 檢查關鍵詞
        denied, matched = self.check(query)
        if denied:
            return True, self.get_denied_message()

        return False, ""

    def check_sql_safety(self, sql_query: str) -> Tuple[bool, str]:
        """檢查 SQL 查詢的安全性

        Args:
            sql_query: SQL 查詢

        Returns:
            Tuple[是否安全, 錯誤訊息]
        """
        sql_lower = sql_query.lower()

        # 檢查危險操作
        dangerous_keywords = ["drop", "delete", "truncate", "alter", "create", "insert", "update"]
        for keyword in dangerous_keywords:
            if keyword in sql_lower:
                return False, f"❌ 禁止操作：{keyword.upper()}"

        return True, ""
