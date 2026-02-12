# 代碼功能說明: Schema Registry 客戶端
# 創建日期: 2026-02-05
# 創建人: Daniel Chung

"""Schema Registry 客戶端 - 提供 Schema 載入、查詢與驗證功能"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ColumnDefinition:
    """欄位定義"""

    id: str
    name: str
    type: str
    description: str = ""


@dataclass
class TableDefinition:
    """資料表定義"""

    canonical_name: str
    tiptop_name: str
    columns: List[ColumnDefinition]

    def get_column(self, column_id: str) -> Optional[ColumnDefinition]:
        """根據欄位 ID 查找欄位"""
        for col in self.columns:
            if col.id == column_id:
                return col
        return None


@dataclass
class ConceptMapping:
    """概念映射"""

    keywords: List[str]
    target_field: str
    operator: str
    description: str = ""
    pattern: str = ""
    value: str = ""
    sql_expr: str = ""


@dataclass
class ConceptDefinition:
    """概念定義"""

    description: str
    mappings: Dict[str, ConceptMapping]


@dataclass
class JoinDefinition:
    """JOIN 定義"""

    table: str
    on: str
    type: str = "LEFT"


@dataclass
class IntentTemplate:
    """意圖模板"""

    description: str
    intent_type: str
    primary_table: str
    joins: List[JoinDefinition] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    output_fields: List[str] = field(default_factory=list)
    group_by: List[str] = field(default_factory=list)
    order_by: str = ""
    where_clause: str = ""
    examples: List[str] = field(default_factory=list)


@dataclass
class ValidationRule:
    """驗證規則"""

    required: List[str] = field(default_factory=list)
    at_least_one_of: List[str] = field(default_factory=list)
    error_message: str = ""
    clarification_prompt: Dict[str, str] = field(default_factory=dict)


@dataclass
class TableRelationships:
    """表關聯關係"""

    relationships: Dict[str, str] = field(default_factory=dict)

    def get_join_condition(self, from_field: str) -> Optional[str]:
        """根據欄位查找關聯的目標表欄位"""
        return self.relationships.get(from_field)


class SchemaRegistry:
    """Schema Registry 客戶端"""

    def __init__(self, registry_path: Optional[str] = None):
        """初始化 Schema Registry

        Args:
            registry_path: Schema Registry JSON 檔案路徑（可選）
        """
        self._registry_path = registry_path
        self._tables: Dict[str, TableDefinition] = {}
        self._concepts: Dict[str, ConceptDefinition] = {}
        self._intent_templates: Dict[str, IntentTemplate] = {}
        self._validation_rules: Dict[str, ValidationRule] = {}
        self._table_relationships: TableRelationships = TableRelationships()
        self._keywords_index: Dict[str, Dict[str, str]] = {}  # keyword -> concept -> mapping
        self._metadata: Dict[str, Any] = {}

        self._load_registry()

    def _load_registry(self) -> None:
        """載入 Schema Registry"""
        if self._registry_path is None:
            # 從 mm_agent/services 目錄向上查找
            current_dir = Path(__file__).resolve()
            # mm_agent/services -> mm_agent -> datalake-system -> metadata
            self._registry_path = str(
                current_dir.parent.parent.parent / "metadata" / "schema_registry.json"
            )

        try:
            with open(self._registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)

            self._parse_tables(registry.get("tables", {}))
            self._parse_concepts(registry.get("concepts", {}))
            self._parse_intent_templates(registry.get("intent_templates", {}))
            self._parse_validation_rules(registry.get("validation_rules", {}))
            self._parse_relationships(registry.get("table_relationships", {}))
            self._metadata = registry.get("metadata", {})

            logger.info(
                f"Schema Registry 已載入: {len(self._tables)} 個表, "
                f"{len(self._concepts)} 個概念, "
                f"{len(self._intent_templates)} 個意圖模板"
            )

        except FileNotFoundError:
            logger.error(f"Schema Registry 不存在: {self._registry_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Schema Registry JSON 解析錯誤: {e}")
            raise

    def _parse_tables(self, tables_data: Dict[str, Any]) -> None:
        """解析資料表定義"""
        for table_name, table_data in tables_data.items():
            columns = [
                ColumnDefinition(
                    id=col.get("id", ""),
                    name=col.get("name", ""),
                    type=col.get("type", "string"),
                    description=col.get("description", ""),
                )
                for col in table_data.get("columns", [])
            ]

            self._tables[table_name] = TableDefinition(
                canonical_name=table_data.get("canonical_name", table_name),
                tiptop_name=table_data.get("tiptop_name", ""),
                columns=columns,
            )

    def _parse_concepts(self, concepts_data: Dict[str, Any]) -> None:
        """解析概念定義"""
        for concept_name, concept_data in concepts_data.items():
            mappings = {}
            for mapping_key, mapping_data in concept_data.get("mappings", {}).items():
                mappings[mapping_key] = ConceptMapping(
                    keywords=mapping_data.get("keywords", []),
                    target_field=mapping_data.get("target_field", ""),
                    operator=mapping_data.get("operator", "="),
                    description=mapping_data.get("description", ""),
                    pattern=mapping_data.get("pattern", ""),
                    value=mapping_data.get("value", ""),
                    sql_expr=mapping_data.get("sql_expr", ""),
                )

            self._concepts[concept_name] = ConceptDefinition(
                description=concept_data.get("description", ""), mappings=mappings
            )

            # 建立關鍵詞索引
            for mapping_key, mapping in mappings.items():
                for keyword in mapping.keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower not in self._keywords_index:
                        self._keywords_index[keyword_lower] = {}
                    self._keywords_index[keyword_lower][concept_name] = mapping_key

    def _parse_intent_templates(self, templates_data: Dict[str, Any]) -> None:
        """解析意圖模板"""
        for template_name, template_data in templates_data.items():
            joins = [
                JoinDefinition(
                    table=j.get("table", ""), on=j.get("on", ""), type=j.get("type", "LEFT")
                )
                for j in template_data.get("joins", [])
            ]

            self._intent_templates[template_name] = IntentTemplate(
                description=template_data.get("description", ""),
                intent_type=template_data.get("intent_type", ""),
                primary_table=template_data.get("primary_table", ""),
                joins=joins,
                required_fields=template_data.get("required_fields", []),
                optional_fields=template_data.get("optional_fields", []),
                output_fields=template_data.get("output_fields", []),
                group_by=template_data.get("group_by", []),
                order_by=template_data.get("order_by", ""),
                where_clause=template_data.get("where_clause", ""),
                examples=template_data.get("examples", []),
            )

    def _parse_validation_rules(self, rules_data: Dict[str, Any]) -> None:
        """解析驗證規則"""
        for rule_name, rule_data in rules_data.items():
            self._validation_rules[rule_name] = ValidationRule(
                required=rule_data.get("required", []),
                at_least_one_of=rule_data.get("at_least_one_of", []),
                error_message=rule_data.get("error_message", ""),
                clarification_prompt=rule_data.get("clarification_prompt", {}),
            )

    def _parse_relationships(self, relationships_data: Dict[str, str]) -> None:
        """解析表關聯關係"""
        self._table_relationships = TableRelationships(relationships=relationships_data)

    # ==================== 公開 API ====================

    def get_table(self, table_name: str) -> Optional[TableDefinition]:
        """根據表名獲取資料表定義"""
        return self._tables.get(table_name)

    def get_all_tables(self) -> Dict[str, TableDefinition]:
        """獲取所有資料表定義"""
        return self._tables.copy()

    def get_column_info(self, table_name: str, column_id: str) -> Optional[ColumnDefinition]:
        """獲取欄位資訊"""
        table = self.get_table(table_name)
        if table:
            return table.get_column(column_id)
        return None

    def find_concept_mapping(self, keyword: str) -> Optional[tuple]:
        """根據關鍵詞查找概念映射

        Returns:
            (concept_name, mapping_key) 或 None
        """
        keyword_lower = keyword.lower()

        # 精確匹配
        if keyword_lower in self._keywords_index:
            concepts = self._keywords_index[keyword_lower]
            for concept_name, mapping_key in concepts.items():
                return (concept_name, mapping_key)

        # 模糊匹配
        for kw, concepts in self._keywords_index.items():
            if keyword_lower in kw or kw in keyword_lower:
                for concept_name, mapping_key in concepts.items():
                    return (concept_name, mapping_key)

        return None

    def get_concept(self, concept_name: str) -> Optional[ConceptDefinition]:
        """根據概念名稱獲取概念定義"""
        return self._concepts.get(concept_name)

    def get_all_concepts(self) -> Dict[str, ConceptDefinition]:
        """獲取所有概念定義"""
        return self._concepts.copy()

    def get_mapping_by_keyword(
        self, keyword: str
    ) -> Optional[tuple[ConceptDefinition, ConceptMapping]]:
        """根據關鍵詞獲取概念與映射

        Returns:
            (ConceptDefinition, ConceptMapping) 或 None
        """
        result = self.find_concept_mapping(keyword)
        if result:
            concept_name, mapping_key = result
            concept = self.get_concept(concept_name)
            if concept:
                mapping = concept.mappings.get(mapping_key)
                if mapping:
                    return (concept, mapping)
        return None

    def get_intent_template(self, intent_name: str) -> Optional[IntentTemplate]:
        """根據意圖名稱獲取意圖模板"""
        return self._intent_templates.get(intent_name)

    def get_all_intent_templates(self) -> Dict[str, IntentTemplate]:
        """獲取所有意圖模板"""
        return self._intent_templates.copy()

    def get_validation_rule(self, intent_name: str) -> Optional[ValidationRule]:
        """根據意圖名稱獲取驗證規則"""
        return self._validation_rules.get(intent_name)

    def validate_constraints(self, intent_name: str, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """驗證約束條件是否完整

        Args:
            intent_name: 意圖名稱
            constraints: 約束條件字典

        Returns:
            驗證結果 {
                "valid": bool,
                "missing_fields": List[str],
                "error_message": str,
                "clarification_prompt": Dict[str, str]
            }
        """
        rule = self.get_validation_rule(intent_name)
        if not rule:
            # 如果沒有對應規則，預設為有效
            return {
                "valid": True,
                "missing_fields": [],
                "error_message": "",
                "clarification_prompt": {},
            }

        missing_fields = []

        # 檢查 required 欄位
        for field_name in rule.required:
            if not constraints.get(field_name):
                missing_fields.append(field_name)

        # 檢查 at_least_one_of 欄位
        if rule.at_least_one_of:
            has_at_least_one = any(constraints.get(f) for f in rule.at_least_one_of)
            if not has_at_least_one:
                missing_fields.extend(rule.at_least_one_of)

        return {
            "valid": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "error_message": rule.error_message,
            "clarification_prompt": {
                f: rule.clarification_prompt.get(f, f"請提供 {f}") for f in missing_fields
            },
        }

    def generate_where_clause(
        self, constraints: Dict[str, Any], table_alias: str = "", intent_name: str = ""
    ) -> str:
        """根據約束條件生成 WHERE 子句

        Args:
            constraints: 約束條件字典
            table_alias: 表別名
            intent_name: 意圖名稱（用於決定欄位映射）

        Returns:
            WHERE 子句字串
        """
        conditions = []

        # 根據意圖決定 material_id 的欄位
        if intent_name == "QUERY_PURCHASE":
            material_id_field = "pmn04"  # 採購單身
        else:
            material_id_field = "img01"  # 庫存表

        # 根據意圖決定時間欄位
        if intent_name == "QUERY_PURCHASE":
            time_field = "pmm02"  # 採購單頭的日期
        elif intent_name == "QUERY_SALES":
            time_field = "coptd02"  # 銷售訂單日期
        else:
            time_field = "tlf06"  # 交易記錄日期

        for key, value in constraints.items():
            if value is None:
                continue

            # 根據約束類型處理
            if key == "material_id":
                field_name = (
                    f"{table_alias}.{material_id_field}" if table_alias else material_id_field
                )
                conditions.append(f"{field_name} = '{value}'")

            elif key == "inventory_location":
                field_name = f"{table_alias}.img02" if table_alias else "img02"
                conditions.append(f"{field_name} = '{value}'")

            elif key == "transaction_type":
                # 只有 tlf_file 有 transaction_type (tlf19)
                if intent_name not in ["QUERY_PURCHASE", "QUERY_SALES"]:
                    field_name = f"{table_alias}.tlf19" if table_alias else "tlf19"
                    conditions.append(f"{field_name} = '{value}'")

            elif key == "material_category":
                # 查找 material_category 的映射
                result = self.get_mapping_by_keyword(value)
                if result:
                    concept, mapping = result
                    field_name = (
                        f"{table_alias}.{mapping.target_field}"
                        if table_alias
                        else mapping.target_field
                    )
                    if mapping.operator == "LIKE":
                        pattern = mapping.pattern.replace("{value}", value)
                        conditions.append(f"{field_name} LIKE '%{value}%'")
                    elif mapping.value:
                        conditions.append(f"{field_name} = '{mapping.value}'")

            elif key == "time_range":
                if isinstance(value, dict):
                    time_type = value.get("type", "")
                    field_name = f"{table_alias}.{time_field}" if table_alias else time_field

                    # 處理日期範圍格式
                    if time_type == "":
                        start = value.get("start", "")
                        end = value.get("end", "")
                        if start and end:
                            conditions.append(f"{field_name} BETWEEN '{start}' AND '{end}'")
                        elif start:
                            conditions.append(f"{field_name} >= '{start}'")
                        elif end:
                            conditions.append(f"{field_name} <= '{end}'")

                    # 處理具體日期 (如 2024-04-14)
                    elif time_type == "specific_date":
                        date_val = value.get("date", "")
                        if date_val:
                            conditions.append(f"{field_name} = '{date_val}'")

                    # 處理日期範圍
                    elif time_type == "date_range":
                        start = value.get("start", "")
                        end = value.get("end", "")
                        if start and end:
                            conditions.append(f"{field_name} BETWEEN '{start}' AND '{end}'")
                        elif start:
                            conditions.append(f"{field_name} >= '{start}'")
                        elif end:
                            conditions.append(f"{field_name} <= '{end}'")

            elif key == "time_type":
                field_name = f"{table_alias}.tlf06" if table_alias else "tlf06"
                time_value = value
                if isinstance(value, dict):
                    time_type = value.get("type", "")

                    # 處理相對時間
                    if time_type == "last_month":
                        conditions.append(
                            f"{field_name} >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'"
                        )
                        conditions.append(f"{field_name} < DATE_TRUNC('month', CURRENT_DATE)")
                    elif time_type == "this_month":
                        conditions.append(f"{field_name} >= DATE_TRUNC('month', CURRENT_DATE)")
                    elif time_type == "last_year":
                        conditions.append(
                            f"{field_name} >= DATE_TRUNC('year', CURRENT_DATE) - INTERVAL '1 year'"
                        )
                        conditions.append(f"{field_name} < DATE_TRUNC('year', CURRENT_DATE)")
                    elif time_type == "this_year":
                        conditions.append(f"{field_name} >= DATE_TRUNC('year', CURRENT_DATE)")
                    elif time_type == "last_week":
                        conditions.append(f"{field_name} >= CURRENT_DATE - INTERVAL '7 days'")

                    # 處理具體日期 (如 2024-04-14)
                    elif time_type == "specific_date":
                        date_val = value.get("date", "")
                        if date_val:
                            conditions.append(f"{field_name} = '{date_val}'")

                    # 處理日期範圍
                    elif time_type == "date_range":
                        start = value.get("start", "")
                        end = value.get("end", "")
                        if start and end:
                            conditions.append(f"{field_name} BETWEEN '{start}' AND '{end}'")
                        elif start:
                            conditions.append(f"{field_name} >= '{start}'")
                        elif end:
                            conditions.append(f"{field_name} <= '{end}'")

            elif key == "warehouse":
                field_name = f"{table_alias}.img02" if table_alias else "img02"
                conditions.append(f"{field_name} = '{value}'")

        return " AND ".join(conditions) if conditions else "1=1"

    def _get_parquet_path(self, table_name: str) -> str:
        """獲取表的 Parquet 路徑"""
        parquet_paths = {
            "img_file": "read_parquet('s3://tiptop-raw/raw/v1/img_file/year=*/*/data.parquet', hive_partitioning=true) AS img_file",
            "ima_file": "read_parquet('s3://tiptop-raw/raw/v1/ima_file/year=*/*/data.parquet', hive_partitioning=true) AS ima_file",
            "tlf_file": "read_parquet('s3://tiptop-raw/raw/v1/tlf_file/year=*/*/data.parquet', hive_partitioning=true) AS tlf_file",
            "pmn_file": "read_parquet('s3://tiptop-raw/raw/v1/pmn_file/year=*/*/data.parquet', hive_partitioning=true) AS pmn_file",
            "pmm_file": "read_parquet('s3://tiptop-raw/raw/v1/pmm_file/year=*/*/data.parquet', hive_partitioning=true) AS pmm_file",
        }
        return parquet_paths.get(table_name, table_name)

    def generate_sql(
        self, intent_name: str, constraints: Dict[str, Any], limit: int = 100
    ) -> Optional[str]:
        """根據意圖模板生成 SQL

        Args:
            intent_name: 意圖名稱
            constraints: 約束條件
            limit: 結果限制

        Returns:
            SQL 語句字串
        """
        template = self.get_intent_template(intent_name)
        if not template:
            logger.warning(f"未找到意圖模板: {intent_name}")
            return None

        # 生成 WHERE 子句
        where_clause = self.generate_where_clause(constraints, intent_name=intent_name)
        if template.where_clause:
            where_clause = f"{where_clause} AND {template.where_clause}"

        # 構建 JOIN 子句（替換為 Parquet 路徑）
        join_clauses = []
        for join in template.joins:
            parquet_path = self._get_parquet_path(join.table)
            join_clauses.append(f"{join.type} JOIN {parquet_path} ON {join.on}")

        # 構建 SELECT 子句
        select_fields = ", ".join(template.output_fields)

        # 構建 FROM 子句（替換為 Parquet 路徑）
        from_clause = self._get_parquet_path(template.primary_table)

        # 添加 JOIN
        if join_clauses:
            from_clause = f"{from_clause} {' '.join(join_clauses)}"

        # 構建 GROUP BY 子句
        group_by_clause = ""
        if template.group_by:
            group_by_clause = f"GROUP BY {', '.join(template.group_by)}"

        # 構建 ORDER BY 子句
        order_by_clause = ""
        if template.order_by:
            order_by_clause = f"ORDER BY {template.order_by}"

        # 組合完整 SQL
        sql = f"""
SELECT {select_fields}
FROM {from_clause}
WHERE {where_clause}
{group_by_clause}
{order_by_clause}
LIMIT {limit}
        """.strip()

        return sql

    def get_table_relationship(self, from_field: str) -> Optional[str]:
        """根據欄位獲取關聯的目標欄位"""
        return self._table_relationships.get_join_condition(from_field)

    def get_metadata(self) -> Dict[str, Any]:
        """獲取 Schema Registry 元數據"""
        return self._metadata.copy()

    def reload(self) -> None:
        """重新載入 Schema Registry"""
        self._tables.clear()
        self._concepts.clear()
        self._intent_templates.clear()
        self._validation_rules.clear()
        self._keywords_index.clear()
        self._load_registry()


# ==================== 便捷函數 ====================

# 全局 Schema Registry 實例
_registry_instance: Optional[SchemaRegistry] = None


def get_schema_registry(registry_path: Optional[str] = None) -> SchemaRegistry:
    """獲取全局 Schema Registry 實例（單例模式）"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = SchemaRegistry(registry_path)
    return _registry_instance


def reset_schema_registry() -> None:
    """重置全局 Schema Registry 實例（用於測試）"""
    global _registry_instance
    _registry_instance = None


# ==================== 測試 ====================

if __name__ == "__main__":
    import asyncio

    async def test():
        # 設置日誌
        logging.basicConfig(level=logging.INFO)

        # 獲取 Schema Registry
        registry = get_schema_registry()

        # 測試 1：查找概念
        print("\n=== 測試 1：查找概念映射 ===")
        result = registry.get_mapping_by_keyword("塑料件")
        if result:
            concept, mapping = result
            print(f"概念: {concept.description}")
            print(f"映射: {mapping.keywords}")
            print(f"目標欄位: {mapping.target_field}")

        # 測試 2：獲取意圖模板
        print("\n=== 測試 2：獲取意圖模板 ===")
        template = registry.get_intent_template("QUERY_STOCK")
        if template:
            print(f"意圖: {template.description}")
            print(f"主表: {template.primary_table}")
            print(f"必填欄位: {template.required_fields}")
            print(f"選填欄位: {template.optional_fields}")

        # 測試 3：驗證約束
        print("\n=== 測試 3：驗證約束 ===")
        constraints = {"inventory_location": "W01"}
        result = registry.validate_constraints("QUERY_STOCK", constraints)
        print(f"驗證結果: {result}")

        # 測試 4：生成 SQL
        print("\n=== 測試 4：生成 SQL ===")
        sql = registry.generate_sql(
            "QUERY_STOCK", {"inventory_location": "W01", "material_category": "plastic"}
        )
        print(f"生成的 SQL:\n{sql}")

        # 測試 5：查找所有表
        print("\n=== 測試 5：所有資料表 ===")
        tables = registry.get_all_tables()
        for name in tables:
            print(f"  - {name}")

        # 測試 6：查找所有概念
        print("\n=== 測試 6：所有概念 ===")
        concepts = registry.get_all_concepts()
        for name in concepts:
            print(f"  - {name}")

    asyncio.run(test())
