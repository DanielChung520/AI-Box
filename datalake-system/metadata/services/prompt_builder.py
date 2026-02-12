# 代碼功能說明: Prompt 構建器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10

"""
Prompt Builder

功能：
- 使用 Jinja2 模板動態生成 Prompt
- 支持按需加載 Table
- 支持多系統多方言

使用示例：
    loader = SmartSchemaLoader(Path("/metadata"))
    builder = PromptBuilder(loader)

    # 構建 Schema Prompt
    prompt = builder.build_schema_prompt(
        system_id="tiptop_erp",
        table_names=["item_master", "inventory"],
        user_query="料號 10-0001 的庫存"
    )
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from jinja2 import Environment, BaseLoader

from .schema_loader import SmartSchemaLoader, NamingConvention
from .sql_renderer import SQLDialect

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Prompt 構建器

    使用 Jinja2 模板，從 YAML 動態生成 Prompt
    """

    def __init__(self, loader: SmartSchemaLoader):
        self.loader = loader
        self._jinja_env = self._init_jinja_env()

    def _init_jinja_env(self) -> Environment:
        """初始化 Jinja2 環境"""
        env = Environment(
            loader=BaseLoader(),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        env.filters["format_type"] = self._format_column_type
        env.filters["format_example"] = self._format_example

        return env

    def _format_column_type(self, col_type: str) -> str:
        """格式化欄位類型"""
        type_map = {
            "V": "VARCHAR",
            "N": "DECIMAL",
            "D": "DATE",
            "string": "VARCHAR",
            "integer": "INTEGER",
            "decimal": "DECIMAL",
            "date": "DATE",
        }
        return type_map.get(col_type, col_type)

    def _format_example(self, example: Optional[str]) -> str:
        """格式化範例"""
        return f"範例: {example}" if example else ""

    def _render_table_ref(self, canonical_name: str, convention: NamingConvention) -> str:
        """渲染 Table 引用"""
        return canonical_name

    def _get_template(self, dialect: str):
        """獲取 Jinja2 模板"""
        template_path = (
            self.loader.metadata_root / "templates" / "prompt" / "dialects" / f"{dialect}.jinja2"
        )

        if not template_path.exists():
            default_path = (
                self.loader.metadata_root / "templates" / "prompt" / "dialects" / "duckdb.jinja2"
            )
            with open(default_path, "r") as f:
                return self._jinja_env.from_string(f.read())

        with open(template_path, "r") as f:
            return self._jinja_env.from_string(f.read())

    def _extract_all_relationships(self, tables: List) -> List[dict]:
        """提取所有關聯關係"""
        relationships = []
        seen = set()

        for table in tables:
            for rel in table.relationships:
                key = (rel["from_table"], rel["to_table"])
                if key not in seen:
                    seen.add(key)
                    relationships.append(rel)

        return relationships

    def build_schema_prompt(
        self,
        system_id: str,
        table_names: List[str],
        user_query: str,
        dialect: SQLDialect = SQLDialect.DUCKDB,
    ) -> str:
        """
        構建 Schema Prompt
        """
        tables = self.loader.get_related_tables(system_id, set(table_names))

        rules = self.loader.load_shared_config("rules")

        system = self.loader.load_system(system_id)

        template = self._get_template(dialect.value)

        prompt = template.render(
            system=system,
            tables=tables,
            user_query=user_query,
            rules=rules.get("sql_rules", []),
            relationships=self._extract_all_relationships(tables),
        )

        return prompt

    def build_with_documentation(
        self,
        system_id: str,
        table_names: List[str],
        user_query: str,
        dialect: SQLDialect = SQLDialect.DUCKDB,
        include_docs: bool = True,
    ) -> str:
        """
        構建含文檔的 Schema Prompt

        Args:
            system_id: 系統 ID
            table_names: 表名列表
            user_query: 用戶查詢
            dialect: SQL 方言
            include_docs: 是否包含文檔引用
        """
        base_prompt = self.build_schema_prompt(system_id, table_names, user_query, dialect)

        if not include_docs:
            return base_prompt

        # 添加文檔引用
        doc_path = self.loader.metadata_root / ".metadata_docs" / "SCHEMA_DOCUMENTATION.md"

        if doc_path.exists():
            with open(doc_path, "r", encoding="utf-8") as f:
                doc_content = f.read()

            # 提取相關章節
            relevant_sections = []
            for table_name in table_names:
                for line in doc_content.split("\n"):
                    if f"| {table_name}" in line or f"`{table_name}`" in line:
                        relevant_sections.append(line)

            if relevant_sections:
                docs_ref = "\n".join(relevant_sections[:10])  # 最多 10 行
                return f"{base_prompt}\n\n【文檔參考】\n{docs_ref}"

        return base_prompt

    def build_intent_prompt(
        self,
        system_id: str,
        intent_type: str,
        user_query: str,
        dialect: SQLDialect = SQLDialect.DUCKDB,
    ) -> str:
        """
        構建 Intent Prompt（Few-shot Learning）
        """
        system = self.loader.load_system(system_id)

        system_dict = {
            "id": system.id,
            "name": system.name,
            "dialect": system.dialect,
            "naming_convention": system.naming_convention,
            "bucket": system.bucket,
            "intents": system.intents,
        }

        target_intent = None
        for intent in system_dict.get("intents", []):
            if intent["name"] == intent_type:
                target_intent = intent
                break

        if not target_intent:
            return self.build_schema_prompt(
                system_id,
                target_intent.get("tables", []) if target_intent else [],
                user_query,
                dialect,
            )

        template = self._get_template(dialect.value)

        prompt = template.render(
            system=system,
            tables=self.loader.get_related_tables(system_id, set(target_intent.get("tables", []))),
            user_query=user_query,
            rules=[],
            intent_examples=target_intent.get("example_queries", []),
            is_intent_prompt=True,
        )

        return prompt
