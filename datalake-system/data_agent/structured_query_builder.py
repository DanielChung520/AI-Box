# 代碼功能說明: 結構化查詢構建器
# 創建日期: 2026-01-31
# 創建人: Daniel Chung

"""結構化查詢構建器 - 將 MM-Agent 的結構化輸出轉換為 SQL"""

from typing import Any, Dict, Optional


class StructuredQueryBuilder:
    """結構化查詢構建器"""

    # Tiptop ERP 表名映射
    TABLE_MAP = {
        "img_file": {
            "name": "img_file",
            "description": "庫存明細檔",
            "columns": {
                "img01": "料號",
                "img02": "倉庫代號",
                "img03": "儲位代號",
                "img04": "庫存數量",
                "img05": "單位",
                "img09": "最近更新日期",
            },
        },
        "tlf_file": {
            "name": "tlf_file",
            "description": "異動明細檔",
            "columns": {
                "tlf01": "異動序號",
                "tlf02": "料號",
                "tlf06": "單據日期",
                "tlf07": "異動別",
                "tlf08": "單據單號",
                "tlf09": "單據項次",
                "tlf10": "異動數量",
                "tlf11": "異動單位",
                "tlf12": "單據確認碼",
                "tlf13": "異動金額",
                "tlf17": "倉庫代號",
                "tlf19": "異動分類",  # 101=採購進貨, 102=完工入庫, 201=生產領料, 202=銷售出庫, 301=報廢
            },
        },
    }

    # tlf19 交易類別映射
    TLF19_MAP = {
        "101": "採購進貨",
        "102": "完工入庫",
        "201": "生產領料",
        "202": "銷售出庫",
        "301": "庫存報廢",
    }

    @classmethod
    def build_query(cls, structured_query: Dict[str, Any]) -> Dict[str, Any]:
        """構建 SQL 查詢

        Args:
            structured_query: 結構化查詢參數
                {
                    "table": "img_file",
                    "filters": {"img02": "W01", "img01": "RM05-008"},
                    "columns": ["img01", "img02", "img10"],
                    "group_by": ["img01"],
                    "aggregations": {"SUM": {"column": "img10", "alias": "total_qty"}}
                }

        Returns:
            {"success": True, "sql": "...", "explanation": "..."}
        """
        try:
            table_name = structured_query.get("table", "img_file")
            filters = structured_query.get("filters", {})
            columns = structured_query.get("columns", ["*"])
            time_range = structured_query.get("time_range")
            aggregations = structured_query.get("aggregations")
            group_by = structured_query.get("group_by")

            # 處理 pmn_file 需要 JOIN pmm_file 的情況
            needs_join = table_name == "pmn_file" and time_range
            date_column = time_range.get("date_column", "pmm02") if time_range else None
            is_pmm_date = date_column in ["pmm02", "pmm.pmm02"] if date_column else False

            # 構建 SELECT 子句
            if aggregations:
                select_parts = []
                for agg_type, agg_info in aggregations.items():
                    col = agg_info.get("column", "*")
                    alias = agg_info.get("alias", f"{agg_type.lower()}_{col}")
                    if agg_type.upper() == "COUNT":
                        select_parts.append(f"COUNT(*) AS {alias}")
                    elif agg_type.upper() == "SUM":
                        select_parts.append(f"SUM(CAST({col} AS DECIMAL(18,4))) AS {alias}")
                    elif agg_type.upper() == "AVG":
                        select_parts.append(f"AVG(CAST({col} AS DECIMAL(18,4))) AS {alias}")
                    elif agg_type.upper() == "MAX":
                        select_parts.append(f"MAX({col}) AS {alias}")
                    elif agg_type.upper() == "MIN":
                        select_parts.append(f"MIN({col}) AS {alias}")
                select_clause = ", ".join(select_parts)
            else:
                select_clause = ", ".join(columns) if columns else "*"

            # 構建 FROM 和 JOIN
            if needs_join:
                pmn_path = f"s3://tiptop-raw/raw/v1/pmn_file/year=*/month=*/data.parquet"
                pmm_path = f"s3://tiptop-raw/raw/v1/pmm_file/year=*/month=*/data.parquet"
                from_clause = f"read_parquet('{pmn_path}', hive_partitioning=true) AS pmn LEFT JOIN read_parquet('{pmm_path}', hive_partitioning=true) AS pmm ON pmn.pmn01 = pmm.pmm01"
            else:
                s3_path = f"s3://tiptop-raw/raw/v1/{table_name}/year=*/month=*/data.parquet"
                from_clause = f"read_parquet('{s3_path}', hive_partitioning=true)"

            # 構建 WHERE 子句
            where_parts = []
            for col, val in filters.items():
                if val is None:
                    continue
                # 處理 LIKE 模式
                if isinstance(val, dict) and val.get("like"):
                    where_parts.append(f"{col} LIKE '{val['like']}'")
                else:
                    where_parts.append(f"{col} = '{val}'")

            # 時間範圍處理
            if time_range:
                if isinstance(time_range, dict):
                    date_col = time_range.get("date_column", "pmm02")
                    if needs_join and is_pmm_date:
                        date_col = "pmm.pmm02"
                    if time_range.get("start"):
                        where_parts.append(
                            f"CAST({date_col} AS DATE) >= DATE '{time_range['start']}'"
                        )
                    if time_range.get("end"):
                        where_parts.append(f"CAST({date_col} AS DATE) < DATE '{time_range['end']}'")

            where_clause = " AND ".join(where_parts) if where_parts else "1=1"

            # 構建 GROUP BY 子句
            group_clause = ""
            if group_by:
                if needs_join and any("pmm02" in str(g) for g in group_by):
                    # 處理 GROUP BY 中引用 pmm02 的情況
                    processed_group = []
                    for g in group_by:
                        if "pmm02" in str(g):
                            processed_group.append(f"DATE_TRUNC('month', CAST(pmm.pmm02 AS DATE))")
                        else:
                            processed_group.append(str(g))
                    group_clause = f"GROUP BY {', '.join(processed_group)}"
                else:
                    group_clause = f"GROUP BY {', '.join(str(g) for g in group_by)}"

            # 構建完整 SQL
            sql = f"""
                SELECT {select_clause}
                FROM {from_clause}
                WHERE {where_clause}
                {group_clause}
                LIMIT 50
            """.strip()

            # 生成說明
            table_desc = {
                "img_file": "庫存表",
                "pmn_file": "採購單身",
                "pmm_file": "採購單頭",
                "ima_file": "物料主檔",
                "coptd_file": "訂單身",
            }.get(table_name, table_name)

            filter_desc = ", ".join([f"{k}={v}" for k, v in filters.items()]) if filters else "無"
            explanation = f"查詢{table_desc}，條件：{filter_desc}"

            return {
                "success": True,
                "sql": sql,
                "explanation": explanation,
                "table": table_name,
                "filters": filters,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"構建查詢失敗：{str(e)}",
            }

    @classmethod
    def _build_inventory_query(cls, part_number: str) -> str:
        """構建庫存查詢"""
        return f"""
            SELECT 
                img01 as part_number,
                img02 as warehouse,
                img03 as location,
                img04 as quantity,
                img05 as unit,
                img09 as last_update
            FROM img_file
            WHERE img01 = '{part_number}'
            LIMIT 10
        """.strip()

    @classmethod
    def _build_transaction_query(
        cls,
        part_number: str,
        tlf19: Optional[str] = None,
        time_expr: Optional[str] = None,
    ) -> str:
        """構建交易查詢"""
        where_conditions = [f"tlf02 = '{part_number}'"]

        if tlf19:
            where_conditions.append(f"tlf19 = '{tlf19}'")

        if time_expr:
            # 處理時間表達式
            if "INTERVAL" in time_expr:
                where_conditions.append(f"tlf06 >= {time_expr}")
            elif "LIKE" in time_expr:
                where_conditions.append(f"tlf06 {time_expr}")

        where_clause = " AND ".join(where_conditions)

        return f"""
            SELECT 
                tlf01 as seq,
                tlf02 as part_number,
                tlf06 as trans_date,
                tlf07 as trans_type,
                tlf08 as doc_no,
                tlf09 as doc_seq,
                tlf10 as quantity,
                tlf11 as unit,
                tlf17 as warehouse,
                tlf19 as tlf19_type
            FROM tlf_file
            WHERE {where_clause}
            ORDER BY tlf06 DESC
            LIMIT 50
        """.strip()


if __name__ == "__main__":
    # 測試結構化查詢構建
    test_cases = [
        {
            "tlf19": "101",
            "part_number": "RM05-008",
            "time_expr": "DATE_SUB(CURDATE(), INTERVAL 1 MONTH)",
            "table_name": "tlf_file",
            "intent": "purchase",
        },
        {
            "part_number": "RM05-008",
            "table_name": "img_file",
            "intent": "inventory",
        },
        {
            "tlf19": "202",
            "part_number": "ABC-123",
            "table_name": "tlf_file",
            "intent": "sales",
        },
    ]

    print("=" * 60)
    print("結構化查詢構建器測試")
    print("=" * 60)

    for i, query in enumerate(test_cases, 1):
        print(f"\n測試 {i}:")
        print(f"  輸入: {query}")
        result = StructuredQueryBuilder.build_query(query)
        if result.get("success"):
            print(f"  ✅ 成功")
            print(f"  SQL: {result['sql'][:100]}...")
            print(f"  說明: {result['explanation']}")
        else:
            print(f"  ❌ 失敗: {result.get('error')}")
