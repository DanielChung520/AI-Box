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
                    "tlf19": "101",
                    "part_number": "RM05-008",
                    "time_expr": "DATE_SUB(CURDATE(), INTERVAL 1 MONTH)",
                    "table_name": "tlf_file",
                    "intent": "purchase"
                }

        Returns:
            {"success": True, "sql": "...", "explanation": "..."}
        """
        try:
            table_name = structured_query.get("table_name", "img_file")
            part_number = structured_query.get("part_number")
            tlf19 = structured_query.get("tlf19")
            time_expr = structured_query.get("time_expr")
            intent = structured_query.get("intent", "unknown")

            if not part_number:
                return {
                    "success": False,
                    "error": "缺少必要參數：part_number（料號）",
                }

            # 根據表名構建不同查詢
            if table_name == "img_file":
                sql = cls._build_inventory_query(part_number)
                explanation = f"查詢料號 {part_number} 的庫存資訊"

            elif table_name == "tlf_file":
                sql = cls._build_transaction_query(part_number, tlf19, time_expr)
                tlf19_desc = cls.TLF19_MAP.get(tlf19, "未知類別")
                explanation = f"查詢料號 {part_number} 的{tlf19_desc}記錄"

            else:
                return {
                    "success": False,
                    "error": f"不支持的表名：{table_name}",
                }

            return {
                "success": True,
                "sql": sql,
                "explanation": explanation,
                "table_name": table_name,
                "part_number": part_number,
                "tlf19": tlf19,
                "intent": intent,
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
