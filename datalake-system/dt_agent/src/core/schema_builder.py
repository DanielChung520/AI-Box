# 代碼功能說明: DT-Agent 動態 Schema Prompt 建構器 — 根據 intent + 複雜度從 intents.json/bindings.json 建構 LLM schema context（從 data_agent v5_schema_builder.py 移植）
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class V5SchemaBuilder:
    def __init__(self, metadata_dir: Path | None = None) -> None:
        if metadata_dir is not None:
            self._metadata_dir = metadata_dir
        else:
            from dt_agent.src.loaders.config import get_config

            config = get_config()
            # 使用 config 的 intents_path 的父目錄作為 metadata_dir
            self._metadata_dir = config.intents_path.parent

    @functools.lru_cache(maxsize=1)
    def _load_intents(self) -> dict[str, Any]:
        return self._load_json(self._metadata_dir / "intents.json")

    @functools.lru_cache(maxsize=1)
    def _load_bindings(self) -> dict[str, Any]:
        return self._load_json(self._metadata_dir / "bindings.json")

    @functools.lru_cache(maxsize=1)
    def _load_concepts(self) -> dict[str, Any]:
        return self._load_json(self._metadata_dir / "concepts.json")

    def _load_json(self, file_path: Path) -> dict[str, Any]:
        if not file_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {file_path}")

        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def build_schema_prompt(self, intent_name: str, complexity: str) -> str:
        intents = self._load_intents().get("intents", {})
        intent_def = intents.get(intent_name)
        if intent_def is None:
            raise ValueError(f"Unknown intent: {intent_name}")

        normalized_complexity = complexity.strip().lower()
        if normalized_complexity not in {"simple", "complex"}:
            raise ValueError(f"Unsupported complexity: {complexity}")

        concepts = self._collect_intent_concepts(intent_def)
        # 從 intent 定義中取得 mart_table（所有 intent 都指向 mart 表）
        mart_table = intent_def.get("mart_table")

        if mart_table:
            return self._build_mart_prompt(
                intent_name=intent_name, mart_table=mart_table, concepts=concepts
            )

        # Fallback: 沒有 mart_table 的 intent（不應發生，但防禦性處理）
        raw_tables = self._collect_raw_table_columns(concepts, intent_name=intent_name)
        return self._render_prompt(
            title=f"Intent: {intent_name}（complexity={normalized_complexity}）",
            table_columns=raw_tables,
        )
    def build_full_schema_prompt(self) -> str:
        intents = self._load_intents().get("intents", {})

        all_concepts: list[str] = []
        mart_tables: set[str] = set()
        for intent_def in intents.values():
            all_concepts.extend(self._collect_intent_concepts(intent_def))
            mart_table = intent_def.get("mart_table")
            if isinstance(mart_table, str) and mart_table:
                mart_tables.add(mart_table)

        raw_table_columns = self._collect_raw_table_columns(all_concepts)

        for mart_table in sorted(mart_tables):
            raw_table_columns.setdefault(mart_table, {})
            mart_columns = self._collect_mart_table_columns(mart_table)
            if mart_columns:
                raw_table_columns[mart_table].update(mart_columns)
            else:
                raw_table_columns[mart_table]["schema_context"] = {
                    "column": "schema_context",
                    "type": "MART",
                    "description": "mart table from intents.json（no direct DUCKDB column binding found）",
                }

        return self._render_prompt(
            title="Full Schema（all intents + mart/raw tables）",
            table_columns=raw_table_columns,
        )

    def _collect_intent_concepts(self, intent_def: dict[str, Any]) -> list[str]:
        input_filters = intent_def.get("input", {}).get("filters", [])
        output_metrics = intent_def.get("output", {}).get("metrics", [])
        output_dimensions = intent_def.get("output", {}).get("dimensions", [])

        ordered_concepts = [*input_filters, *output_metrics, *output_dimensions]
        unique_concepts: list[str] = []
        seen: set[str] = set()

        for concept in ordered_concepts:
            if concept not in seen:
                seen.add(concept)
                unique_concepts.append(concept)

        return unique_concepts

    def _collect_raw_table_columns(
        self, concepts: list[str], intent_name: str | None = None
    ) -> dict[str, dict[str, dict[str, str]]]:
        bindings = self._load_bindings().get("bindings", {})
        concept_meta = self._load_concepts().get("concepts", {})

        table_columns: dict[str, dict[str, dict[str, str]]] = {}
        for concept in concepts:
            concept_binding = bindings.get(concept, {})
            # Per-intent override: check intents.{intent_name}.DUCKDB first
            duckdb_binding = None
            if intent_name:
                duckdb_binding = (
                    concept_binding.get("intents", {}).get(intent_name, {}).get("DUCKDB")
                )
            if not isinstance(duckdb_binding, dict):
                duckdb_binding = concept_binding.get("DUCKDB")
            if not isinstance(duckdb_binding, dict):
                continue

            table_name = duckdb_binding.get("table")
            column_name = duckdb_binding.get("column")
            if not isinstance(table_name, str) or not table_name:
                continue
            if not isinstance(column_name, str) or not column_name:
                continue

            concept_info = concept_meta.get(concept, {})
            concept_type = concept_info.get("type", "UNKNOWN")
            concept_desc = concept_info.get("description", "")
            aggregation = duckdb_binding.get("aggregation", "NONE")

            description_parts = [f"concept={concept}"]
            if concept_desc:
                description_parts.append(f"desc={concept_desc}")
            if aggregation and aggregation != "NONE":
                description_parts.append(f"aggregation={aggregation}")

            table_columns.setdefault(table_name, {})[column_name] = {
                "column": column_name,
                "type": str(concept_type),
                "description": "；".join(description_parts),
            }
        return table_columns

    def _collect_mart_table_columns(self, mart_table: str) -> dict[str, dict[str, str]]:
        from dt_agent.src.loaders.config import get_config
        import duckdb

        conn: duckdb.DuckDBPyConnection | None = None
        try:
            config = get_config()
            db_path = config.duckdb.database
            conn = duckdb.connect(database=db_path, read_only=True)
            rows = conn.execute(f"DESCRIBE {mart_table}").fetchall()

            columns: dict[str, dict[str, str]] = {}
            for row in rows:
                col_name = str(row[0])
                col_type = str(row[1])
                columns[col_name] = {
                    "column": col_name,
                    "type": col_type,
                    "description": col_name,
                }
            return columns
        except Exception as error:
            logger.warning(
                "DuckDB introspection failed for mart table",
                mart_table=mart_table,
                error=str(error),
            )
            return {}
        finally:
            if conn is not None:
                conn.close()

    def _build_mart_prompt(self, intent_name: str, mart_table: str, concepts: list[str]) -> str:
        """建構 mart 表的 schema prompt，融合 DuckDB 欄位資訊與 concept 語意描述。"""
        mart_columns = self._collect_mart_table_columns(mart_table)
        concept_meta = self._load_concepts().get("concepts", {})
        bindings = self._load_bindings().get("bindings", {})

        # 建立 concept → mart column 的映射（支援 per-intent override）
        concept_column_map: dict[str, dict[str, str]] = {}
        for concept in concepts:
            concept_info = concept_meta.get(concept, {})
            concept_binding = bindings.get(concept, {})
            # Per-intent override: check intents.{intent_name}.DUCKDB first
            duckdb_binding = (
                concept_binding.get("intents", {}).get(intent_name, {}).get("DUCKDB")
            )
            if not isinstance(duckdb_binding, dict):
                duckdb_binding = concept_binding.get("DUCKDB", {})
            bound_column = duckdb_binding.get("column", "").lower()
            concept_column_map[bound_column] = {
                "concept": concept,
                "type": concept_info.get("type", "UNKNOWN"),
                "description": concept_info.get("description", ""),
                "aggregation": concept_info.get(
                    "aggregation", duckdb_binding.get("aggregation", "")
                ),
            }

        # 用 concept 語意豐富 mart 欄位描述
        if mart_columns:
            for col_name, col_info in mart_columns.items():
                enrichment = concept_column_map.get(col_name.lower())
                if enrichment:
                    parts = [f"concept={enrichment['concept']}"]
                    if enrichment["description"]:
                        parts.append(f"desc={enrichment['description']}")
                    parts.append(f"type={enrichment['type']}")
                    if enrichment["aggregation"]:
                        parts.append(f"aggregation={enrichment['aggregation']}")
                    col_info["type"] = enrichment["type"]
                    col_info["description"] = "；".join(parts)
        else:
            # DuckDB introspection 失敗，用 concept 資訊建構
            for concept in concepts:
                concept_info = concept_meta.get(concept, {})
                concept_type = concept_info.get("type", "UNKNOWN")
                concept_desc = concept_info.get("description", "")
                agg = concept_info.get("aggregation", "")
                parts = [f"concept={concept}"]
                if concept_desc:
                    parts.append(f"desc={concept_desc}")
                parts.append(f"type={concept_type}")
                if agg:
                    parts.append(f"aggregation={agg}")
                mart_columns[concept] = {
                    "column": concept,
                    "type": str(concept_type),
                    "description": "；".join(parts),
                }

        return self._render_prompt(
            title=f"Intent: {intent_name}（mart_table={mart_table}）",
            table_columns={mart_table: mart_columns},
        )
    def _render_prompt(
        self, title: str, table_columns: dict[str, dict[str, dict[str, str]]]
    ) -> str:
        lines: list[str] = [
            f"## {title}",
            "",
            "## DuckDB 查詢說明",
            "",
            "- 所有表格都是 DuckDB 內建表（mart 寬表），直接使用表格名稱查詢",
            "- 範例：`SELECT ent, site, item_no, warehouse_no, existing_stocks FROM mart_inventory_wide WHERE item_no = 'NI001' LIMIT 100`",
            "- **嚴禁使用 read_parquet() 或 S3 路徑**，所有資料都在 DuckDB 本地 mart 表中",
            "",
            "## 欄位類型說明：",
            "",
            "- **METRIC**（指標）：數值型欄位，彙總時必須使用聚合函數（見欄位說明中的 aggregation）",
            "- **DIMENSION**（維度）：分類/編號型欄位，用於 GROUP BY 和 WHERE 條件",
            "",
            "## 可用表格：",
            "",
        ]

        if not table_columns:
            lines.append("（無可用表格映射）")
            return "\n".join(lines)

        # Build per-table column name lists for the boundary summary
        table_column_names: dict[str, list[str]] = {}
        for table_name in sorted(table_columns):
            col_names = [cn for cn in sorted(table_columns[table_name])]
            table_column_names[table_name] = col_names

        # Emit a global column-boundary summary block
        lines.append("## ⚠️ 嚴格欄位歸屬規則（最重要！）")
        lines.append("")
        lines.append("每張表只能使用該表定義的欄位，嚴禁跨表引用欄位。")
        lines.append("")
        for tname, cnames in table_column_names.items():
            lines.append(f"- **{tname}** 的合法欄位：{', '.join(cnames)}")
        lines.append("")
        lines.append("若某張表沒有你需要的欄位，不可從其他表借用——請僅使用該表現有的欄位。")
        lines.append("")

        for table_name in sorted(table_columns):
            col_names = table_column_names[table_name]
            lines.append(f"### {table_name}")
            lines.append(
                f"⚠️ **{table_name}** 僅包含以下 {len(col_names)} 個欄位，禁止使用其他表的欄位："
            )
            lines.append("")

            table_data = table_columns[table_name]
            lines.append("| 欄位名稱 | 類形 | 說明 |")
            lines.append("|---------|------|------|")

            for column_name in sorted(table_data):
                column_info = table_data[column_name]
                lines.append(
                    f"| {column_info['column']} | {column_info['type']} | {column_info['description']} |"
                )
            lines.append("")

        return "\n".join(lines)


_SCHEMA_BUILDER: V5SchemaBuilder | None = None


def get_schema_builder() -> V5SchemaBuilder:
    global _SCHEMA_BUILDER
    if _SCHEMA_BUILDER is None:
        _SCHEMA_BUILDER = V5SchemaBuilder()
        logger.info("Initialized V5SchemaBuilder", metadata_dir=str(_SCHEMA_BUILDER._metadata_dir))
    return _SCHEMA_BUILDER
