# 代碼功能說明: DT-Agent SQL 安全驗證層 — 使用 sqlglot AST 強制 SELECT-only 和單一陳述句規則（從 data_agent v5_sql_safety.py 移植）
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

from typing import Optional

import sqlglot
import sqlglot.expressions as exp
import structlog

logger = structlog.get_logger(__name__)


def validate_sql_safety(sql: Optional[str]) -> dict:
    """
    驗證 SQL 安全性：
    1. 非空檢查
    2. 單一陳述句（禁止分號分隔多個語句）
    3. SELECT-only（禁止 DDL/DML）

    Args:
        sql: SQL 語句字符串

    Returns:
        {"safe": bool, "reason": str}
    """
    # Edge cases
    if not sql or not sql.strip():
        return {"safe": False, "reason": "SQL is empty"}

    try:
        statements = sqlglot.parse(sql, dialect="duckdb")
    except Exception as e:
        logger.warning(
            "SQL parse failed during safety check",
            sql=sql[:200],
            error=str(e),
        )
        return {"safe": False, "reason": f"SQL parse error: {e}"}

    # Single-statement check
    if len(statements) != 1:
        logger.warning(
            "Multi-statement SQL rejected",
            statement_count=len(statements),
            sql=sql[:200],
        )
        return {
            "safe": False,
            "reason": f"Multiple statements detected ({len(statements)}). Only single SELECT allowed.",
        }

    stmt = statements[0]
    if stmt is None:
        return {"safe": False, "reason": "SQL parsed to empty statement"}

    # SELECT-only check
    if not isinstance(stmt, exp.Select):
        stmt_type = type(stmt).__name__
        logger.warning(
            "Non-SELECT SQL rejected",
            stmt_type=stmt_type,
            sql=sql[:200],
        )
        return {
            "safe": False,
            "reason": f"Only SELECT statements allowed. Got: {stmt_type}",
        }

    return {"safe": True, "reason": ""}
