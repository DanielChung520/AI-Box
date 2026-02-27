# 代碼功能說明: 結構化查詢處理器
# 創建日期: 2026-02-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-09

"""結構化查詢處理器 - 接收 MM-Agent 的意圖+參數，根據 schema 生成 SQL

職責：
1. 接收 {intent, parameters} 結構化查詢
2. 根據 intent 查詢 schema_registry.json 欄位映射
3. 將語義參數映射到實際欄位名稱
4. 生成並執行 SQL
5. 返回結果

核心原則：
- MM-Agent 傳遞語義參數 (part_number, start_date, end_date)
- Data-Agent 根據 schema 自動映射到實際欄位 (tlf01, tlf06)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .config_manager import get_config
from .datalake_service import DatalakeService
from .schema_registry_loader import get_table_columns_map, get_table_mapping_for_duckdb

logger = logging.getLogger(__name__)


@dataclass
class StructuredQueryResult:
    """結構化查詢結果"""

    success: bool
    rows: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    sql_query: Optional[str] = None
    duckdb_query: Optional[str] = None
    error: Optional[str] = None
    schema_used: Optional[Dict[str, Any]] = None


class IntentParameterMapper:
    """意圖參數映射器 - 將語義參數映射到實際欄位名稱

    MM-Agent 傳遞: part_number, start_date, end_date, warehouse, limit
    Data-Agent 映射: 使用 JP 資料庫的 mart 寬表
    """

    INTENT_MAPPINGS = {
        "query_stock_info": {
            "table": "mart_inventory_wide",
            "param_columns": {
                "part_number": "item_no",
                "warehouse": "warehouse_no",
            },
        },
        "query_stock_history": {
            "table": "mart_inventory_wide",
            "param_columns": {
                "part_number": "item_no",
                "start_date": "doc_date",
                "end_date": "doc_date",
            },
        },
        "query_purchase": {
            "table": "mart_work_order_wide",
            "param_columns": {
                "part_number": "item_no",
            },
        },
        "query_sales": {
            "table": "mart_shipping_wide",
            "param_columns": {
                "part_number": "item_no",
                "start_date": "doc_date",
                "end_date": "doc_date",
            },
        },
        "analyze_shortage": {
            "table": "mart_inventory_wide",
            "param_columns": {
                "part_number": "item_no",
                "warehouse": "warehouse_no",
            },
        },
    }

    # MM-Agent QueryIntent enum 值 → Data-Agent intent 名稱映射
    MM_TO_DA_INTENT_MAP = {
        "QUERY_STOCK": "query_stock_info",
        "QUERY_STOCK_HISTORY": "query_stock_history",
        "QUERY_PURCHASE": "query_purchase",
        "QUERY_SALES": "query_sales",
        "ANALYZE_SHORTAGE": "analyze_shortage",
    }

    @classmethod
    def map_parameters(cls, intent: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """將語義參數映射到實際欄位

        Args:
            intent: 意圖類型 (如 query_stock_history 或 QUERY_STOCK_HISTORY)
            parameters: 語義參數 {part_number, start_date, ...}

        Returns:
            映射後的參數 {tlf01: value, tlf06: value, ...}
        """
        normalized_intent = intent

        if intent in cls.MM_TO_DA_INTENT_MAP:
            normalized_intent = cls.MM_TO_DA_INTENT_MAP[intent]
            logger.info(f"Intent 映射: {intent} → {normalized_intent}")
        elif intent not in cls.INTENT_MAPPINGS:
            logger.warning(f"未知意圖: {intent}，返回原參數")
            return parameters

        mapping = cls.INTENT_MAPPINGS[normalized_intent]
        param_columns = mapping.get("param_columns", {})
        result = {}

        for param_name, column_name in param_columns.items():
            if param_name in parameters:
                result[column_name] = parameters[param_name]

        filters = mapping.get("filters", {})
        result.update(filters)

        logger.info(f"參數映射: {intent}")
        logger.info(f"  輸入: {parameters}")
        logger.info(f"  輸出: {result}")

        return result

    @classmethod
    def get_table_for_intent(cls, intent: str) -> Optional[str]:
        """根據意圖獲取目標表名稱

        Args:
            intent: 意圖類型

        Returns:
            表名稱或 None
        """
        normalized_intent = intent

        if intent in cls.MM_TO_DA_INTENT_MAP:
            normalized_intent = cls.MM_TO_DA_INTENT_MAP[intent]

        mapping = cls.INTENT_MAPPINGS.get(normalized_intent)
        return mapping.get("table") if mapping else None


class DateNormalizer:
    """日期格式正規化器 - 處理自然語言日期"""

    @staticmethod
    def normalize(date_input: Optional[str]) -> Optional[str]:
        """將自然語言日期轉換為 SQL 格式 (YYYY-MM-DD)

        Args:
            date_input: 自然語言日期 (如 "前兩年", "2024年1月", "2024-02-09")

        Returns:
            SQL 格式日期字串，或 None
        """
        if not date_input:
            return None

        date_str = str(date_input).strip()

        # 處理 "前 N 年/月/週"
        if "前" in date_str:
            parts = date_str.replace("前", "").strip()
            if "年" in parts:
                years = int(parts.replace("年", ""))
                target_date = datetime.now() - timedelta(days=years * 365)
                return target_date.strftime("%Y-%m-%d")
            elif "月" in parts:
                months = int(parts.replace("月", ""))
                target_date = datetime.now() - timedelta(days=months * 30)
                return target_date.strftime("%Y-%m-%d")
            elif "週" in parts:
                weeks = int(parts.replace("週", "").replace("周", ""))
                target_date = datetime.now() - timedelta(weeks=weeks)
                return target_date.strftime("%Y-%m-%d")
            elif "天" in parts:
                days = int(parts.replace("天", ""))
                target_date = datetime.now() - timedelta(days=days)
                return target_date.strftime("%Y-%m-%d")

        # 處理中文格式 "YYYY年MM月"
        if "年" in date_str and "月" in date_str:
            try:
                parts = date_str.replace("年", "-").replace("月", "-").strip("-")
                date_obj = datetime.strptime(parts, "%Y-%m-%")
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # 處理 "YYYY-MM" 格式
        if len(date_str) == 7 and date_str[4] == "-":
            return date_str + "-01"

        # 假設已是標準格式
        return date_str

    @staticmethod
    def normalize_date_range(
        start_date: Optional[str], end_date: Optional[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """正規化日期範圍"""
        return DateNormalizer.normalize(start_date), DateNormalizer.normalize(end_date)


class StructuredQueryHandler:
    """結構化查詢處理器

    接收 MM-Agent 的意圖+參數，根據 schema_registry 生成 SQL 並執行
    """

    def __init__(self):
        """初始化處理器"""
        self._datalake_service = None
        self._column_maps = None

    def _get_datalake_service(self) -> DatalakeService:
        """取得 Datalake 服務"""
        if self._datalake_service is None:
            self._datalake_service = DatalakeService()
        return self._datalake_service

    def _get_column_maps(self) -> Dict[str, Dict[str, str]]:
        """取得欄位映射"""
        if self._column_maps is None:
            self._column_maps = get_table_columns_map()
        return self._column_maps

    def _build_where_clause(
        self,
        table_name: str,
        mapped_params: Dict[str, Any],
    ) -> str:
        """根據映射後的參數構建 WHERE 子句"""
        column_maps = self._get_column_maps()
        columns = column_maps.get(table_name, {})

        conditions = []

        start_date = mapped_params.get("start_date")
        end_date = mapped_params.get("end_date")

        for field_name, value in mapped_params.items():
            if value is None:
                continue

            if value == "":
                continue

            if field_name in ["tlf06"]:
                if start_date and end_date and start_date != "" and end_date != "":
                    conditions.append(f"{field_name} BETWEEN '{start_date}' AND '{end_date}'")
                elif start_date and start_date != "":
                    conditions.append(f"{field_name} >= '{start_date}'")
                elif end_date and end_date != "":
                    conditions.append(f"{field_name} <= '{end_date}'")
            elif field_name in ["tlf19"]:
                conditions.append(f"{field_name} = '{value}'")
            else:
                if isinstance(value, str):
                    conditions.append(f"{field_name} = '{value}'")
                else:
                    conditions.append(f"{field_name} = {value}")

        return " AND ".join(conditions) if conditions else "1=1"

    async def execute(
        self,
        intent: str,
        parameters: Dict[str, Any],
        limit: int = 100,
    ) -> StructuredQueryResult:
        """執行結構化查詢

        Args:
            intent: 意圖類型 (如 query_stock_history)
            parameters: 語義參數
                {
                    "part_number": "10-0012",
                    "start_date": "2024-02-09",
                    "end_date": "2026-02-09",
                    "warehouse": null,
                }
            limit: 最大返回行數

        Returns:
            StructuredQueryResult: 查詢結果
        """
        try:
            logger.info(f"[StructuredQueryHandler] 執行查詢: intent={intent}")
            logger.info(f"[StructuredQueryHandler] 參數: {parameters}")

            # Step 1: 正規化日期
            start_date, end_date = DateNormalizer.normalize_date_range(
                parameters.get("start_date"),
                parameters.get("end_date"),
            )

            if start_date:
                parameters["start_date"] = start_date
            if end_date:
                parameters["end_date"] = end_date

            # Step 2: 映射參數到實際欄位
            mapped_params = IntentParameterMapper.map_parameters(intent, parameters)
            logger.info(f"[StructuredQueryHandler] 映射後參數: {mapped_params}")

            # Step 3: 根據意圖決定目標表和欄位
            normalized_intent = IntentParameterMapper.MM_TO_DA_INTENT_MAP.get(intent, intent)
            mapping = IntentParameterMapper.INTENT_MAPPINGS.get(normalized_intent)
            if not mapping:
                return StructuredQueryResult(
                    success=False,
                    error=f"未知意圖: {intent}",
                )

            table_name = mapping["table"]

            # Step 4: 構建 SQL
            where_clause = self._build_where_clause(table_name, mapped_params)

            # 獲取欄位列表
            column_maps = self._get_column_maps()
            columns = column_maps.get(table_name, {})
            column_list = list(columns.keys())[:10]  # 使用欄位 ID（如 img01, img02），最多 10 個

            # 根據意圖決定排序方式
            # mart_work_order_wide 有 tlf06（交易日期），mart_inventory_wide 沒有
            if table_name == "mart_work_order_wide":
                order_by_clause = "ORDER BY tlf06 DESC"
            elif table_name == "mart_inventory_wide":
                # mart_inventory_wide 使用庫存時間或不需要排序
                order_by_clause = ""  # 庫存查詢不需要排序
            else:
                order_by_clause = ""

            sql_query = f"""
                SELECT {", ".join(column_list)}
                FROM {table_name}
                WHERE {where_clause}
                {order_by_clause}
                LIMIT {limit}
            """.strip()

            logger.info(f"[StructuredQueryHandler] SQL: {sql_query[:200]}...")

            # Step 5: 執行查詢
            # 注意：傳遞邏輯表名給 Data-Agent，讓 Data-Agent 內部做映射
            service = self._get_datalake_service()
            result = await service.query_sql(
                sql_query=sql_query,  # 使用邏輯表名（mart_work_order_wide, mart_inventory_wide）
                max_rows=limit,
            )

            if result.get("success"):
                return StructuredQueryResult(
                    success=True,
                    rows=result.get("rows", []),
                    row_count=result.get("row_count", 0),
                    sql_query=sql_query,
                    duckdb_query=result.get("duckdb_query"),
                    schema_used=mapping,
                )
            else:
                return StructuredQueryResult(
                    success=False,
                    error=result.get("error", "查詢失敗"),
                    sql_query=sql_query,
                )

        except Exception as e:
            logger.error(f"[StructuredQueryHandler] 執行失敗: {e}", exc_info=True)
            return StructuredQueryResult(
                success=False,
                error=str(e),
            )


# 便捷函數
async def execute_structured_query(
    intent: str,
    parameters: Dict[str, Any],
    limit: int = 100,
) -> StructuredQueryResult:
    """執行結構化查詢（便捷函數）"""
    handler = StructuredQueryHandler()
    return await handler.execute(intent, parameters, limit)
