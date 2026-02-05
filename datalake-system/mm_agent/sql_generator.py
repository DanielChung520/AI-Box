# 代碼功能說明: SQL 生成器
# 創建日期: 2026-02-05
# 創建人: AI-Box 開發團隊

"""SQL Generator - SQL 生成器

職責：根據 QuerySpec 生成 SQL 語句
技術：純規則引擎（確定性）
"""

import logging
from typing import Optional
from mm_agent.models.query_spec import QuerySpec, QueryIntent

logger = logging.getLogger(__name__)


class SQLGenerator:
    """SQL 生成器 - 純規則引擎"""

    # SQL 模板
    TEMPLATES = {
        QueryIntent.QUERY_STOCK.value: """
            SELECT {fields}
            FROM img_file
            LEFT JOIN ima_file ON img01 = ima01
            WHERE {conditions}
            {group_by}
            {order_by}
            LIMIT {limit}
        """,
        QueryIntent.QUERY_PURCHASE.value: """
            SELECT {fields}
            FROM tlf_file
            LEFT JOIN ima_file ON tlf01 = ima01
            WHERE {conditions}
            {group_by}
            {order_by}
            LIMIT {limit}
        """,
        QueryIntent.QUERY_SALES.value: """
            SELECT {fields}
            FROM tlf_file
            LEFT JOIN ima_file ON tlf01 = ima01
            WHERE tlf19 = '202'
            AND {conditions}
            {group_by}
            {order_by}
            LIMIT {limit}
        """,
        QueryIntent.ANALYZE_SHORTAGE.value: """
            SELECT {fields}
            FROM img_file
            LEFT JOIN ima_file ON img01 = ima01
            WHERE {conditions}
            {group_by}
            {order_by}
            LIMIT {limit}
        """,
        QueryIntent.GENERATE_ORDER.value: """
            SELECT {fields}
            FROM pmn_file
            LEFT JOIN pmm_file ON pmn01 = pmm01
            LEFT JOIN ima_file ON pmn04 = ima01
            WHERE {conditions}
            {group_by}
            {order_by}
            LIMIT {limit}
        """,
    }

    def __init__(self):
        """初始化 SQL 生成器"""
        self._templates = self.TEMPLATES

    def generate(self, spec) -> str:
        """生成 SQL 語句

        Args:
            spec: QuerySpec 結構化參數 或 dict

        Returns:
            str: SQL 語句
        """
        # 如果是 dict，轉換為簡單對象
        if isinstance(spec, dict):

            class SimpleSpec:
                def __init__(self, d):
                    self.intent = d.get("intent", "QUERY_PURCHASE")
                    self.material_id = d.get("material_id")
                    self.warehouse = d.get("warehouse")
                    self.time_type = d.get("time_type")
                    self.time_value = d.get("time_value")
                    self.transaction_type = d.get("transaction_type")
                    self.material_category = d.get("material_category")
                    self.order_by = d.get("order_by")
                    self.limit = d.get("limit", 100)
                    self.aggregation = d.get("aggregation")

            spec = SimpleSpec(spec)

        # 驗證意圖
        intent_value = spec.intent.value if hasattr(spec.intent, "value") else spec.intent

        if intent_value not in self._templates:
            raise ValueError(f"不支援的意圖類型: {intent_value}")

        # 構建 SQL
        template = self._templates[intent_value]

        fields = self._build_fields(spec)
        conditions = self._build_conditions(spec)
        group_by = self._build_group_by(spec)
        order_by = self._build_order_by(spec)

        sql = template.format(
            fields=fields,
            conditions=conditions,
            group_by=group_by,
            order_by=order_by,
            limit=spec.limit,
        )

        logger.info(f"SQL 生成成功: {sql[:100]}...")
        return sql.strip()

    def _build_fields(self, spec: QuerySpec) -> str:
        """構建 SELECT 字段"""
        intent_value = spec.intent.value if hasattr(spec.intent, "value") else spec.intent

        if intent_value == QueryIntent.QUERY_STOCK.value:
            return "img01, ima02, img02, SUM(img10) as total_qty"
        elif intent_value == QueryIntent.QUERY_PURCHASE.value:
            return "tlf01, ima02, SUM(tlf10) as total_qty, COUNT(*) as tx_count"
        elif intent_value == QueryIntent.QUERY_SALES.value:
            return "tlf01, ima02, SUM(tlf10) as total_qty, COUNT(*) as tx_count"
        elif intent_value == QueryIntent.ANALYZE_SHORTAGE.value:
            return "img01, ima02, img02, img10"
        elif intent_value == QueryIntent.GENERATE_ORDER.value:
            return "pmn01, pmn02, pmn04, ima02, pmn20"
        else:
            return "*"

    def _build_conditions(self, spec: QuerySpec) -> str:
        """構建 WHERE 條件"""
        conditions = ["1=1"]

        intent_value = spec.intent.value if hasattr(spec.intent, "value") else spec.intent

        # 料號
        if spec.material_id:
            if intent_value in [QueryIntent.QUERY_STOCK.value, QueryIntent.ANALYZE_SHORTAGE.value]:
                conditions.append(f"img01 = '{spec.material_id}'")
            elif intent_value in [QueryIntent.QUERY_PURCHASE.value, QueryIntent.QUERY_SALES.value]:
                conditions.append(f"tlf01 = '{spec.material_id}'")
            elif intent_value == QueryIntent.GENERATE_ORDER.value:
                conditions.append(f"pmn04 = '{spec.material_id}'")

        # 倉庫
        if spec.warehouse:
            if intent_value in [QueryIntent.QUERY_STOCK.value, QueryIntent.ANALYZE_SHORTAGE.value]:
                conditions.append(f"img02 = '{spec.warehouse}'")

        # 交易類型
        if spec.transaction_type:
            if intent_value in [QueryIntent.QUERY_PURCHASE.value, QueryIntent.QUERY_SALES.value]:
                conditions.append(f"tlf19 = '{spec.transaction_type}'")

        # 時間
        if spec.time_type:
            time_type = spec.time_type.value if hasattr(spec.time_type, "value") else spec.time_type

            if time_type == "specific_date" and spec.time_value:
                conditions.append(f"tlf06 = '{spec.time_value}'")
            elif time_type == "date_range" and spec.time_value:
                parts = spec.time_value.split("~")
                if len(parts) == 2:
                    conditions.append(
                        f"tlf06 BETWEEN '{parts[0].strip()}' AND '{parts[1].strip()}'"
                    )
            elif time_type == "last_week":
                conditions.append("tlf06 >= CURRENT_DATE - INTERVAL '7 days'")
            elif time_type == "last_month":
                conditions.append("tlf06 >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'")
                conditions.append("tlf06 < DATE_TRUNC('month', CURRENT_DATE)")
            elif time_type == "this_month":
                conditions.append("tlf06 >= DATE_TRUNC('month', CURRENT_DATE)")
            elif time_type == "last_year":
                conditions.append("tlf06 >= DATE_TRUNC('year', CURRENT_DATE) - INTERVAL '1 year'")
                conditions.append("tlf06 < DATE_TRUNC('year', CURRENT_DATE)")
            elif time_type == "this_year":
                conditions.append("tlf06 >= DATE_TRUNC('year', CURRENT_DATE)")

        # 物料類別
        if spec.material_category:
            if spec.material_category in ["plastic", "finished", "raw"]:
                conditions.append(f"ima08 = '{spec.material_category.upper()}'")
            elif spec.material_category == "plastic":
                conditions.append("(ima02 LIKE '%塑料%' OR ima02 LIKE '%塑膠%')")

        return " AND ".join(conditions)

    def _build_group_by(self, spec: QuerySpec) -> str:
        """構建 GROUP BY"""
        intent_value = spec.intent.value if hasattr(spec.intent, "value") else spec.intent

        if intent_value == QueryIntent.QUERY_STOCK.value:
            return "GROUP BY img01, ima02, img02"
        elif intent_value in [QueryIntent.QUERY_PURCHASE.value, QueryIntent.QUERY_SALES.value]:
            return "GROUP BY tlf01, ima02"
        elif intent_value == QueryIntent.ANALYZE_SHORTAGE.value:
            return "GROUP BY img01, ima02, img02"
        elif intent_value == QueryIntent.GENERATE_ORDER.value:
            return "GROUP BY pmn01, pmn02, pmn04, ima02, pmn20"

        return ""

    def _build_order_by(self, spec: QuerySpec) -> str:
        """構建 ORDER BY"""
        if spec.order_by:
            return f"ORDER BY {spec.order_by}"

        intent_value = spec.intent.value if hasattr(spec.intent, "value") else spec.intent

        # 默認排序
        if intent_value in [QueryIntent.QUERY_PURCHASE.value, QueryIntent.QUERY_SALES.value]:
            return "ORDER BY tlf06 DESC"
        elif intent_value == QueryIntent.QUERY_STOCK.value:
            return "ORDER BY img01"

        return ""
