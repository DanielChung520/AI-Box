# 代碼功能說明: V5 動態 Schema Prompt 建構器 — 根據 intent + 複雜度從 intents.json/bindings.json 建構 LLM schema context
# 創建日期: 2026-03-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-10

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class V5SchemaBuilder:
    def __init__(self, metadata_dir: Path | None = None) -> None:
        project_root = Path(__file__).resolve().parents[2]
        self._metadata_dir = metadata_dir or project_root / "metadata" / "systems" / "tiptop_jp"

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
        mart_table = intent_def.get("mart_table")

        if normalized_complexity == "complex" and mart_table:
            return self._build_mart_prompt(
                intent_name=intent_name, mart_table=mart_table, concepts=concepts
            )

        raw_tables = self._collect_raw_table_columns(concepts)
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
        self, concepts: list[str]
    ) -> dict[str, dict[str, dict[str, str]]]:
        bindings = self._load_bindings().get("bindings", {})
        concept_meta = self._load_concepts().get("concepts", {})

        table_columns: dict[str, dict[str, dict[str, str]]] = {}
        for concept in concepts:
            duckdb_binding = bindings.get(concept, {}).get("DUCKDB")
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
        bindings = self._load_bindings().get("bindings", {})
        concept_meta = self._load_concepts().get("concepts", {})

        columns: dict[str, dict[str, str]] = {}
        for concept, binding_group in bindings.items():
            duckdb_binding = binding_group.get("DUCKDB")
            if not isinstance(duckdb_binding, dict):
                continue
            if duckdb_binding.get("table") != mart_table:
                continue

            column_name = duckdb_binding.get("column")
            if not isinstance(column_name, str) or not column_name:
                continue

            concept_info = concept_meta.get(concept, {})
            concept_type = concept_info.get("type", "UNKNOWN")
            concept_desc = concept_info.get("description", "")
            columns[column_name] = {
                "column": column_name,
                "type": str(concept_type),
                "description": f"concept={concept}；desc={concept_desc}"
                if concept_desc
                else f"concept={concept}",
            }

        return columns

    def _build_mart_prompt(self, intent_name: str, mart_table: str, concepts: list[str]) -> str:
        mart_columns = self._collect_mart_table_columns(mart_table)
        if not mart_columns:
            concept_meta = self._load_concepts().get("concepts", {})
            for concept in concepts:
                concept_info = concept_meta.get(concept, {})
                concept_type = concept_info.get("type", "UNKNOWN")
                concept_desc = concept_info.get("description", "")
                mart_columns[concept] = {
                    "column": concept,
                    "type": str(concept_type),
                    "description": f"concept={concept}；desc={concept_desc}"
                    if concept_desc
                    else f"concept={concept}",
                }

        return self._render_prompt(
            title=f"Intent: {intent_name}（complexity=complex, mart_table={mart_table}）",
            table_columns={mart_table: mart_columns},
        )

    def _render_prompt(
        self, title: str, table_columns: dict[str, dict[str, dict[str, str]]]
    ) -> str:
        lines: list[str] = [
            f"## {title}",
            "",
            "## 可用表格：",
            "",
        ]

        if not table_columns:
            lines.append("（無可用表格映射）")
            return "\n".join(lines)

        for table_name in sorted(table_columns):
            lines.append(f"### {table_name}")
            lines.append("| 欄位名稱 | 類型 | 說明 |")
            lines.append("|---------|------|------|")

            for column_name in sorted(table_columns[table_name]):
                column_info = table_columns[table_name][column_name]
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
