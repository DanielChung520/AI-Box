# 代碼功能說明: Schema Registry 配置載入器
# 創建日期: 2026-02-07
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10
#
# 職責說明:
# 本模組僅提供配置讀取功能，Schema 檢索應使用 schema_rag.py

"""Schema Registry 配置載入器 - 僅包含配置相關函數"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

logger = logging.getLogger(__name__)

_DEFAULT_SCHEMA_PATH: Optional[Path] = None


def _default_schema_path() -> Path:
    global _DEFAULT_SCHEMA_PATH
    if _DEFAULT_SCHEMA_PATH is None:
        _DEFAULT_SCHEMA_PATH = ai_box_root / "datalake-system" / "metadata" / "schema_registry.json"
    return _DEFAULT_SCHEMA_PATH


def load_schema_from_registry(schema_path: Optional[str] = None) -> Dict[str, Any]:
    """從 schema_registry.json 加載 Schema 定義。"""
    path = Path(schema_path) if schema_path else _default_schema_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        return schema
    except Exception as e:
        logger.error(f"加載 Schema 失敗: {e}")
        return {}


def get_sql_dialect(schema_path: Optional[str] = None, dialect: str = "duckdb") -> Dict[str, Any]:
    """獲取 SQL 方言配置。

    Returns:
        {
            "table_source": "...",
            "join_syntax": "LEFT JOIN",
            ...
        }
    """
    schema = load_schema_from_registry(schema_path)

    default_dialects = {
        "duckdb": {
            "description": "DuckDB with S3 Parquet storage",
            "table_source": "read_parquet('s3://tiptop-raw/raw/v1/{table}/year=*/month=*/data.parquet', hive_partitioning=true)",
            "join_syntax": "LEFT JOIN",
        },
        "oracle": {
            "description": "Oracle Database",
            "table_source": "{schema}.{table}",
            "join_syntax": "LEFT JOIN",
        },
        "mysql": {
            "description": "MySQL Database",
            "table_source": "`{database}`.`{table}`",
            "join_syntax": "LEFT JOIN",
        },
    }

    dialects = schema.get("sql_dialects", {})
    return dialects.get(dialect, default_dialects.get(dialect, {}))


def get_table_mapping_for_duckdb(schema_path: Optional[str] = None) -> Dict[str, str]:
    """獲取 DuckDB 表名映射。

    Returns:
        {"mart_inventory_wide": "mart_inventory_wide", "mart_work_order_wide": "mart_work_order_wide_large", ...}
    """
    # 首先檢查是否有 legacy tables
    schema = load_schema_from_registry(schema_path)

    # 優先使用 legacy tables
    tables = schema.get("tables", {})
    if tables:
        mapping = {
            name: info.get("canonical_name", name) if isinstance(info, dict) else name
            for name, info in tables.items()
        }
    else:
        # 從 systems 加載表名映射
        systems = schema.get("systems", {})
        mapping = {}
        for system_id, config in systems.items():
            system_path_str = config.get("path", "")
            if "/tiptop_erp/" in system_path_str or system_id == "tiptop01":
                # 從 YAML 讀取
                import yaml

                full_path = (
                    Path(schema_path).parent / system_path_str
                    if schema_path
                    else ai_box_root / "datalake-system" / "metadata" / system_path_str
                )
                if full_path.exists():
                    with open(full_path, "r") as f:
                        system_schema = yaml.safe_load(f)
                    for table in system_schema.get("tables", []):
                        canonical = table.get("name")
                        tiptop_name = table.get("names", {}).get("tiptop", canonical)
                        mapping[tiptop_name] = tiptop_name

    fallback_mappings = {
        "mart_work_order_wide": "mart_work_order_wide_large",  # mart_work_order_wide_large 存在於 S3
        # mart_inventory_wide: 直接使用 mart_inventory_wide（S3 有 mart_inventory_wide）
        # mart_inventory_wide: 直接使用 mart_inventory_wide（S3 有 mart_inventory_wide）
    }

    for original_table, fallback_table in fallback_mappings.items():
        # 檢查原始表是否存在於 mapping 中，若存在則映射到 fallback 表
        if original_table in mapping:
            mapping[original_table] = fallback_table

    return mapping


def get_table_path_pattern_for_duckdb(schema_path: Optional[str] = None) -> Dict[str, str]:
    """獲取 DuckDB 表路徑模式。

    Returns:
        {"mart_work_order_wide_large": "**/*.parquet", "mart_inventory_wide": "year=*/month=*/data.parquet", ...}
    """
    schema = load_schema_from_registry(schema_path)
    tables = schema.get("tables", {})
    mapping = {}

    for table_name in tables.keys():
        if table_name.endswith("_large"):
            mapping[table_name] = "**/*.parquet"
        else:
            mapping[table_name] = "year=*/month=*/data.parquet"

    # 為 fallback 表添加路徑模式
    fallback_mappings = {
        "mart_work_order_wide": "mart_work_order_wide_large",
        "mart_inventory_wide": "mart_inventory_wide_large",
        "mart_inventory_wide": "mart_inventory_wide_large",
    }

    for original_table, fallback_table in fallback_mappings.items():
        if fallback_table not in mapping and original_table in mapping:
            # 原始表使用 _large 的路徑模式
            mapping[fallback_table] = mapping.get(original_table, "**/*.parquet")
            if mapping[original_table] == "year=*/month=*/data.parquet":
                mapping[fallback_table] = "**/*.parquet"

    return mapping


def get_tables(schema_path: Optional[str] = None) -> Dict[str, Any]:
    """獲取所有表定義。

    Returns:
        {"mart_inventory_wide": {...}, "mart_inventory_wide": {...}, ...}
    """
    schema = load_schema_from_registry(schema_path)
    return schema.get("tables", {})


def get_table_columns_map(schema_path: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """獲取表列映射。

    Returns:
        {"mart_inventory_wide": {"ima01": "料號", "ima02": "品名", ...}, ...}
    """
    tables = get_tables(schema_path)
    return {
        table_name: {col["id"]: col["name"] for col in info.get("columns", [])}
        for table_name, info in tables.items()
    }


def get_transaction_type_map(schema_path: Optional[str] = None) -> Dict[str, str]:
    """獲取交易類型映射。

    Returns:
        {"101": "採購進貨", "102": "完工入庫", ...}
    """
    schema = load_schema_from_registry(schema_path)
    concepts = schema.get("concepts", {})
    trans = concepts.get("TRANSACTION_TYPE", {})
    mappings = trans.get("mappings", {})
    return {code: m.get("description", code) for code, m in mappings.items()}
