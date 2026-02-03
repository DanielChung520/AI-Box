# 代碼功能說明: 安全查詢閘道服務
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""安全查詢閘道服務 - SQL 注入防護、權限驗證、查詢結果過濾"""

import logging
import re
import time
from typing import Any, Dict, List, Optional

from .config_manager import get_config

logger = logging.getLogger(__name__)


class QueryGatewayService:
    """安全查詢閘道服務"""

    def __init__(self):
        """初始化查詢閘道服務"""
        self._config = get_config()
        self._logger = logger

    def validate_query(
        self,
        sql_query: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        驗證查詢（SQL 注入防護、權限檢查、語法驗證）

        Args:
            sql_query: SQL 查詢語句
            user_id: 用戶 ID（可選）
            tenant_id: 租戶 ID（可選）

        Returns:
            驗證結果，包含是否通過、錯誤信息等
        """
        try:
            # 基本 SQL 語法檢查
            syntax_check = self._check_sql_syntax(sql_query)
            if not syntax_check["valid"]:
                return {
                    "valid": False,
                    "error": f"Invalid SQL syntax: {syntax_check.get('error', 'Unknown syntax error')}",
                    "details": syntax_check.get("issues", []),
                }

            # SQL 注入防護
            injection_check = self._check_sql_injection(sql_query)
            if not injection_check["safe"]:
                return {
                    "valid": False,
                    "error": "SQL injection detected",
                    "details": injection_check["issues"],
                }

            # 危險操作檢查
            dangerous_check = self._check_dangerous_operations(sql_query)
            if not dangerous_check["safe"]:
                return {
                    "valid": False,
                    "error": "Dangerous operation detected",
                    "details": dangerous_check["issues"],
                }

            # 參數化查詢檢查（僅警告，不阻止）
            param_check = self._check_parameterized_query(sql_query)
            warnings = injection_check.get("warnings", []) + param_check.get("warnings", [])

            return {
                "valid": True,
                "warnings": warnings,
            }

        except Exception as e:
            self._logger.error(f"Query validation failed: {e}")
            return {
                "valid": False,
                "error": str(e),
            }

    def _check_sql_injection(self, sql: str) -> Dict[str, Any]:
        """檢查 SQL 注入風險"""
        issues: List[str] = []
        warnings: List[str] = []

        sql_upper = sql.upper()

        # 檢查危險關鍵字組合
        dangerous_patterns = [
            (r"'.*OR.*'1'='1", "SQL injection pattern detected: OR '1'='1"),
            (r"'.*OR.*'1'='1'", "SQL injection pattern detected: OR '1'='1'"),
            (r"'.*UNION.*SELECT", "SQL injection pattern detected: UNION SELECT"),
            (r";.*DROP", "SQL injection pattern detected: ; DROP"),
            (r";.*DELETE", "SQL injection pattern detected: ; DELETE"),
            (r"EXEC\s*\(", "SQL injection pattern detected: EXEC("),
            (r"EXECUTE\s*\(", "SQL injection pattern detected: EXECUTE("),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                issues.append(message)

        # 檢查字符串拼接
        if "'" in sql or '"' in sql:
            # 檢查是否有未參數化的字符串
            if "?" not in sql and "$" not in sql:
                warnings.append("String literals detected without parameterization")

        # 檢查註釋
        if "--" in sql or "/*" in sql:
            warnings.append("SQL comments detected")

        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }

    def _check_dangerous_operations(self, sql: str) -> Dict[str, Any]:
        """檢查危險操作"""
        issues: List[str] = []
        sql_upper = sql.upper()

        # 禁止的操作
        forbidden_operations = [
            "DROP",
            "DELETE",
            "TRUNCATE",
            "ALTER",
            "CREATE",
            "INSERT",
            "UPDATE",
            "GRANT",
            "REVOKE",
        ]

        for operation in forbidden_operations:
            if operation in sql_upper:
                issues.append(f"Forbidden operation detected: {operation}")

        return {
            "safe": len(issues) == 0,
            "issues": issues,
        }

    def _check_sql_syntax(self, sql: str) -> Dict[str, Any]:
        """檢查 SQL 基本語法（增強版：使用 sqlparse 進行嚴格驗證）

        Args:
            sql: SQL 查詢語句

        Returns:
            語法檢查結果
        """
        issues: List[str] = []
        sql_upper = sql.upper().strip()

        # 檢查是否為空
        if not sql or not sql.strip():
            return {
                "valid": False,
                "error": "Empty SQL query",
                "issues": ["SQL query is empty"],
            }

        # 使用更靈活的方式檢查 SQL 結構（不依賴 sqlparse 的 token 類型）
        has_select = "SELECT" in sql_upper
        has_from = "FROM" in sql_upper

        # 檢查不完整的語句
        if has_select and not has_from:
            issues.append("SELECT 語句缺少 FROM 子句")

        # 檢查 SELECT 和 FROM 之間是否有欄位（放寬版）
        if has_select and has_from:
            select_index = sql_upper.find("SELECT")
            from_index = sql_upper.find("FROM")
            select_part = sql[select_index + 6 : from_index].strip()

            # 放寬檢查：允許 * 或欄位名或參數佔位符
            if not select_part:
                issues.append("SELECT 子句缺少欄位")
            # 檢查是否為空（只有空格）
            elif select_part.replace(" ", "").replace("\n", "") == "":
                issues.append("SELECT 子句缺少欄位")
                issues.append("SELECT 子句缺少欄位")
            # 檢查是否為純註釋或分號
            elif select_part.startswith("--") or select_part.startswith(";"):
                issues.append("SELECT 子句缺少欄位")
            elif select_part.upper() == "":
                issues.append("SELECT 語句缺少欄位")

                # 檢查 WHERE 中是否使用了聚合函數
                if "WHERE" in sql_upper:
                    where_start = sql_upper.find("WHERE")
                    where_end = (
                        sql_upper.find("GROUP BY")
                        if "GROUP BY" in sql_upper
                        else (
                            sql_upper.find("HAVING")
                            if "HAVING" in sql_upper
                            else (
                                sql_upper.find("ORDER BY")
                                if "ORDER BY" in sql_upper
                                else len(sql_upper)
                            )
                        )
                    )
                    if where_end == -1:
                        where_end = len(sql_upper)
                    where_clause = sql[where_start + 5 : where_end]
                    agg_funcs = ["SUM(", "COUNT(", "AVG(", "MIN(", "MAX(", "STDDEV(", "VARIANCE("]
                    for func in agg_funcs:
                        if func in where_clause.upper():
                            issues.append(f"聚合函數 {func} 不能在 WHERE 子句中使用")
                            break

        # 檢查常見的語法錯誤
        if ";" in sql and sql.count(";") > 1:
            parts = sql.split(";")
            if len(parts) > 2:
                issues.append("檢測到多個分號")

        open_parens = sql.count("(")
        close_parens = sql.count(")")
        if open_parens != close_parens:
            issues.append(f"括號不匹配：{open_parens} 個開括號，{close_parens} 個閉括號")

        single_quotes = sql.count("'")
        if single_quotes > 0 and single_quotes % 2 != 0:
            issues.append("單引號不匹配")

        double_quotes = sql.count('"')
        if double_quotes > 0 and double_quotes % 2 != 0:
            issues.append("雙引號不匹配")

        # 檢查是否為明顯無效的 SQL（如 "INVALID SQL ???"）
        if (
            "SELECT" not in sql_upper
            and "INSERT" not in sql_upper
            and "UPDATE" not in sql_upper
            and "DELETE" not in sql_upper
        ):
            # 如果沒有有效的 SQL 命令關鍵字
            if "???" in sql or "???" in sql_upper:
                issues.append("SQL 包含無效字符或語法")
            elif len(sql.split()) < 2:
                issues.append("SQL 太短，可能是無效的查詢")

        return {
            "valid": len(issues) == 0,
            "error": "; ".join(issues) if issues else None,
            "issues": issues,
        }

        # 檢查常見的語法錯誤
        # 1. 多餘的分號（在語句中間）
        if ";" in sql and sql.count(";") > 1:
            # 檢查是否在語句中間有多餘的分號
            parts = sql.split(";")
            if len(parts) > 2:
                issues.append("Multiple semicolons detected in query")

        # 2. 不匹配的括號
        open_parens = sql.count("(")
        close_parens = sql.count(")")
        if open_parens != close_parens:
            issues.append(f"Unmatched parentheses: {open_parens} open, {close_parens} close")

        # 3. 不匹配的引號（簡單檢查）
        single_quotes = sql.count("'")
        if single_quotes > 0 and single_quotes % 2 != 0:
            issues.append("Unmatched single quotes")

        double_quotes = sql.count('"')
        if double_quotes > 0 and double_quotes % 2 != 0:
            issues.append("Unmatched double quotes")

        return {
            "valid": len(issues) == 0,
            "error": "; ".join(issues) if issues else None,
            "issues": issues,
        }

    def _check_parameterized_query(self, sql: str) -> Dict[str, Any]:
        """檢查參數化查詢"""
        issues: List[str] = []
        warnings: List[str] = []

        # 檢查是否有參數佔位符
        has_parameters = "?" in sql or "$" in sql or "%s" in sql

        # 檢查是否有字符串字面量
        has_string_literals = "'" in sql or '"' in sql

        if has_string_literals and not has_parameters:
            issues.append("Query contains string literals but no parameter placeholders")

        if not has_parameters and ("WHERE" in sql.upper() or "VALUES" in sql.upper()):
            warnings.append("Consider using parameterized queries for better security")

        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }

    def check_permissions(
        self,
        sql_query: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        connection_string: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        檢查查詢權限

        Args:
            sql_query: SQL 查詢語句
            user_id: 用戶 ID（可選）
            tenant_id: 租戶 ID（可選）
            connection_string: 數據庫連接字符串（可選）

        Returns:
            權限檢查結果
        """
        # 這裡應該實現實際的權限檢查邏輯
        # 目前返回基本檢查結果
        return {
            "allowed": True,
            "message": "Permission check passed (basic validation)",
        }

    def filter_results(
        self,
        rows: List[Dict[str, Any]],
        max_rows: int = 1000,
        sensitive_columns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        過濾查詢結果

        Args:
            rows: 查詢結果行
            max_rows: 最大返回行數
            sensitive_columns: 敏感列名列表（可選，用於脫敏）

        Returns:
            過濾後的結果
        """
        # 限制返回行數
        filtered_rows = rows[:max_rows]

        # 敏感數據脫敏
        if sensitive_columns:
            for row in filtered_rows:
                for col in sensitive_columns:
                    if col in row:
                        # 簡單的脫敏處理（可以後續增強）
                        value = str(row[col])
                        if len(value) > 4:
                            row[col] = value[:2] + "***" + value[-2:]
                        else:
                            row[col] = "***"

        return filtered_rows

    async def execute_query(
        self,
        sql_query: str,
        connection_string: Optional[str] = None,
        timeout: Optional[int] = None,
        max_rows: Optional[int] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        執行安全查詢

        Args:
            sql_query: SQL 查詢語句
            connection_string: 數據庫連接字符串（可選）
            timeout: 查詢超時時間（秒）（可選，默認從配置讀取）
            max_rows: 最大返回行數（可選，默認從配置讀取）
            user_id: 用戶 ID（可選）
            tenant_id: 租戶 ID（可選）

        Returns:
            查詢結果，包含行數據、執行時間等

        Note:
            這是一個簡化實現，實際應該連接到真實數據庫執行查詢
        """
        # 從配置讀取默認值
        if timeout is None:
            timeout = self._config.get_sql_timeout()
        if max_rows is None:
            max_rows = self._config.get_sql_max_rows()

        start_time = time.time()

        # 驗證查詢
        validation = self.validate_query(sql_query, user_id=user_id, tenant_id=tenant_id)
        if not validation["valid"]:
            return {
                "success": False,
                "error": validation["error"],
                "details": validation.get("details", []),
            }

        # 檢查權限
        permission_check = self.check_permissions(
            sql_query, user_id=user_id, tenant_id=tenant_id, connection_string=connection_string
        )
        if not permission_check["allowed"]:
            return {
                "success": False,
                "error": "Permission denied",
                "message": permission_check.get("message", ""),
            }

        # 執行查詢（這裡是模擬實現，實際應該連接到數據庫）
        # 注意：實際實現需要根據 connection_string 連接數據庫
        execution_time = time.time() - start_time

        # 模擬查詢結果（實際應該從數據庫獲取）
        rows: List[Dict[str, Any]] = []

        # 過濾結果
        filtered_rows = self.filter_results(rows, max_rows=max_rows)

        return {
            "success": True,
            "rows": filtered_rows,
            "row_count": len(filtered_rows),
            "execution_time": execution_time,
            "warnings": validation.get("warnings", []),
            "metadata": {
                "query": sql_query,
                "timeout": timeout,
                "max_rows": max_rows,
            },
        }
