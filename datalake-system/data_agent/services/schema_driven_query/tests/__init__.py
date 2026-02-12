# 代碼功能說明: 整合測試
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

"""Data-Agent-JP 整合測試"""

import pytest
import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from services.schema_driven_query.config import SchemaDrivenQueryConfig
from services.schema_driven_query.models import (
    ConceptsContainer,
    IntentsContainer,
    BindingsContainer,
    QueryAST,
    ParsedIntent,
    ConceptDefinition,
    ConceptType,
    IntentDefinition,
)
from services.schema_driven_query.parser import SimpleNLQParser
from services.schema_driven_query.sql_generator import SQLGenerator


class TestConfig:
    """配置測試"""

    def test_default_config(self):
        """測試預設配置"""
        config = SchemaDrivenQueryConfig()

        assert config.system_id == "jp_tiptop_erp"
        assert config.oracle.host == "192.168.5.16"
        assert config.qdrant.use_qdrant is True
        assert config.arangodb.use_arangodb is True

    def test_config_paths(self):
        """測試配置路徑"""
        config = SchemaDrivenQueryConfig()

        assert "jp_tiptop_erp" in str(config.concepts_path)
        assert "jp_tiptop_erp" in str(config.intents_path)
        assert "jp_tiptop_erp" in str(config.bindings_path)


class TestModels:
    """模型測試"""

    def test_concepts_container(self):
        """測試 Concepts 容器"""
        concepts = ConceptsContainer(
            version="1.0",
            concepts={
                "PART_NO": ConceptDefinition(
                    description="料件編號", type=ConceptType.DIMENSION, values={}
                )
            },
        )

        assert concepts.version == "1.0"
        assert "PART_NO" in concepts.concepts
        assert concepts.concepts["PART_NO"].type.value == "DIMENSION"

    def test_intents_container(self):
        """測試 Intents 容器"""
        from services.schema_driven_query.models import IntentInput, IntentOutput

        intents = IntentsContainer(
            version="1.0",
            intents={
                "QUERY_INVENTORY": IntentDefinition(
                    description="查詢庫存",
                    input=IntentInput(filters=["PART_NO", "WAREHOUSE"], required_filters=[]),
                    output=IntentOutput(metrics=["ON_HAND_QTY"], dimensions=["PART_NO"]),
                )
            },
        )

        assert intents.version == "1.0"
        assert "QUERY_INVENTORY" in intents.intents

    def test_query_ast(self):
        """測試 Query AST"""
        ast = QueryAST(
            select=[{"expr": "SUM(INAG008)", "alias": "on_hand_qty"}],
            from_tables=["INAG_T"],
            where_conditions=[{"column": "INAG001", "operator": "=", "value": "RM01-005"}],
            group_by=["INAG001"],
        )

        assert len(ast.select) == 1
        assert "INAG_T" in ast.from_tables
        assert len(ast.where_conditions) == 1
        assert "INAG001" in ast.group_by

    def test_parsed_intent(self):
        """測試解析意圖"""
        parsed = ParsedIntent(
            intent="QUERY_INVENTORY", confidence=0.9, params={"PART_NO": "RM01-005"}
        )

        assert parsed.intent == "QUERY_INVENTORY"
        assert parsed.confidence == 0.9
        assert parsed.params["PART_NO"] == "RM01-005"


class TestParser:
    """解析器測試"""

    def test_simple_parser_inventory(self):
        """測試庫存查詢解析"""
        parser = SimpleNLQParser()

        result = parser.parse("查詢料號 RM01-005 的庫存")

        assert result.intent == "QUERY_INVENTORY"
        assert result.confidence > 0
        assert "PART_NO" in result.params

    def test_simple_parser_with_warehouse(self):
        """測試帶倉庫的查詢"""
        parser = SimpleNLQParser()

        result = parser.parse("RM01-005 在 W03 的庫存")

        assert result.intent == "QUERY_INVENTORY"
        assert result.params.get("PART_NO") == "RM01-005"
        assert result.params.get("WAREHOUSE") == "W03"

    def test_simple_parser_unknown(self):
        """測試未知查詢"""
        parser = SimpleNLQParser()

        result = parser.parse("xyz abc")

        assert result.intent == "UNKNOWN"
        assert result.confidence == 0.0


class TestSQLGenerator:
    """SQL 生成器測試"""

    def test_simple_select(self):
        """測試簡單 SELECT"""
        generator = SQLGenerator()

        ast = QueryAST(
            select=[{"expr": "INAG001", "alias": "part_no"}],
            from_tables=["INAG_T"],
            where_conditions=[],
        )

        sql = generator.generate(ast)

        assert "SELECT" in sql
        assert "INAG_T" in sql
        assert "part_no" in sql

    def test_select_with_aggregation(self):
        """測試帶聚合的 SELECT"""
        generator = SQLGenerator()

        ast = QueryAST(
            select=[
                {"expr": "INAG001", "alias": "part_no"},
                {"expr": "SUM(INAG008)", "alias": "total_qty"},
            ],
            from_tables=["INAG_T"],
            where_conditions=[{"column": "INAG001", "operator": "=", "value": "RM01-005"}],
            group_by=["INAG001"],
        )

        sql = generator.generate(ast)

        assert "SUM(INAG008)" in sql
        assert "GROUP BY" in sql
        assert "INAG001" in sql

    def test_where_clause(self):
        """測試 WHERE 子句"""
        generator = SQLGenerator()

        ast = QueryAST(
            select=[{"expr": "*"}],
            from_tables=["INAG_T"],
            where_conditions=[
                {"column": "INAG001", "operator": "=", "value": "RM01-005"},
                {"column": "INAG004", "operator": "=", "value": "W03"},
            ],
        )

        sql = generator.generate(ast)

        assert "WHERE" in sql
        assert "RM01-005" in sql
        assert "W03" in sql

    def test_like_operator(self):
        """測試 LIKE 運算符"""
        generator = SQLGenerator()

        ast = QueryAST(
            select=[{"expr": "*"}],
            from_tables=["INAG_T"],
            where_conditions=[{"column": "INAG001", "operator": "LIKE", "value": "RM%"}],
        )

        sql = generator.generate(ast)

        assert "LIKE" in sql
        assert "RM%" in sql


class TestIntegration:
    """整合測試"""

    def test_full_query_flow(self):
        """測試完整查詢流程"""
        # 1. 解析
        parser = SimpleNLQParser()
        parsed = parser.parse("RM01-005 在 W03 的庫存")

        assert parsed.intent == "QUERY_INVENTORY"
        assert parsed.confidence > 0

        # 2. 生成 AST
        ast = QueryAST(
            select=[{"expr": "SUM(INAG008)", "alias": "on_hand_qty"}],
            from_tables=["INAG_T"],
            where_conditions=[
                {"column": "INAG001", "operator": "=", "value": parsed.params.get("PART_NO")},
                {"column": "INAG004", "operator": "=", "value": parsed.params.get("WAREHOUSE")},
            ],
        )

        # 3. 生成 SQL
        generator = SQLGenerator()
        sql = generator.generate(ast)

        assert "SELECT" in sql
        assert "SUM(INAG008)" in sql
        assert "INAG_T" in sql
        assert "RM01-005" in sql
        assert "W03" in sql


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
