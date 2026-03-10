# 代碼功能說明: V5 pipeline pytest unit tests for v5_sql_safety
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11
# -*- coding: utf-8 -*-
"""
V5 SQL Safety 單元測試

測試 validate_sql_safety() 的各種安全場景：SELECT-only、單一陳述句、DDL/DML 拒絕等。
"""

import pytest

from data_agent.services.v5_sql_safety import validate_sql_safety


class TestValidateSqlSafety:
    """validate_sql_safety() 測試"""

    def test_valid_select_accepted(self):
        """有效的 SELECT 語句應該通過"""
        result = validate_sql_safety(
            "SELECT item_no, warehouse_no FROM mart_inventory_wide WHERE item_no = 'NI001'"
        )
        assert result["safe"] is True
        assert result["reason"] == ""

    def test_drop_table_rejected(self):
        """DROP TABLE 應該被拒絕"""
        result = validate_sql_safety("DROP TABLE mart_inventory_wide")
        assert result["safe"] is False
        assert "SELECT" in result["reason"] or "Drop" in result["reason"]

    def test_delete_rejected(self):
        """DELETE 語句應該被拒絕"""
        result = validate_sql_safety("DELETE FROM mart_inventory_wide WHERE item_no = 'NI001'")
        assert result["safe"] is False
        assert "SELECT" in result["reason"] or "Delete" in result["reason"]

    def test_multi_statement_rejected(self):
        """多個語句（分號分隔）應該被拒絕"""
        result = validate_sql_safety("SELECT 1; SELECT 2")
        assert result["safe"] is False
        assert "Multiple statements" in result["reason"]

    def test_empty_string_rejected(self):
        """空字符串應該被拒絕"""
        result = validate_sql_safety("")
        assert result["safe"] is False
        assert "empty" in result["reason"].lower()

    def test_none_input_rejected(self):
        """None 輸入應該被拒絕"""
        result = validate_sql_safety(None)
        assert result["safe"] is False
        assert "empty" in result["reason"].lower()

    def test_whitespace_only_rejected(self):
        """僅空白字符應該被拒絕"""
        result = validate_sql_safety("   \n\t  ")
        assert result["safe"] is False
        assert "empty" in result["reason"].lower()

    def test_insert_rejected(self):
        """INSERT 語句應該被拒絕"""
        result = validate_sql_safety("INSERT INTO mart_inventory_wide (item_no) VALUES ('X')")
        assert result["safe"] is False

    def test_update_rejected(self):
        """UPDATE 語句應該被拒絕"""
        result = validate_sql_safety("UPDATE mart_inventory_wide SET item_no = 'X' WHERE 1=1")
        assert result["safe"] is False

    def test_complex_select_accepted(self):
        """複雜 SELECT（JOIN、GROUP BY、子查詢）應該通過"""
        sql = """
        SELECT a.item_no, SUM(a.qty)
        FROM mart_inventory_wide a
        JOIN mart_work_order_wide b ON a.item_no = b.item_no
        WHERE a.warehouse_no = 'W01'
        GROUP BY a.item_no
        HAVING SUM(a.qty) > 100
        ORDER BY SUM(a.qty) DESC
        LIMIT 10
        """
        result = validate_sql_safety(sql)
        assert result["safe"] is True
