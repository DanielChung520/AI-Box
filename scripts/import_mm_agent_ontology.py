#!/usr/bin/env python3
# 代碼功能說明: 將 MM-Agent Ontology（domain + major）導入 ArangoDB
# 創建日期: 2026-01-25 23:51 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-25 23:51 UTC+8

"""將 MM-Agent Ontology 導入 ArangoDB（須先於上架知識庫前執行）

使用方式:
    python scripts/import_mm_agent_ontology.py

注意：如果 Ontology 已存在，會跳過導入（避免重複導入）
Ontology 目錄：/Users/daniel/GitHub/AI-Box/docs/系统设计文档/核心组件/Agent平台/MM-Agent/Ontology；兩個檔案：mm-agent-domain.json、mm-agent-major.json。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from dotenv import load_dotenv

    _env_path = _project_root / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
except ImportError:
    pass

from services.api.models.ontology import OntologyCreate
from services.api.services.ontology_store_service import get_ontology_store_service


def _generate_ontology_key(type: str, name: str, version: str, tenant_id: str | None = None) -> str:
    base_key = f"{type}-{name}-{version}"
    if tenant_id:
        return f"{base_key}-{tenant_id}"
    return base_key


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ontology_dir = Path(
        "/Users/daniel/GitHub/AI-Box/docs/系统设计文档/核心组件/Agent平台/MM-Agent/Ontology"
    )
    base = ontology_dir
    domain_path = base / "mm-agent-domain.json"
    major_path = base / "mm-agent-major.json"

    if not domain_path.exists():
        print("Domain file missing:", domain_path)
        return 1
    if not major_path.exists():
        print("Major file missing:", major_path)
        return 1

    store = get_ontology_store_service()
    tenant_id = None

    raw_d = _load_json(domain_path)
    domain_key = _generate_ontology_key(raw_d["type"], raw_d["name"], raw_d["version"], tenant_id)
    existing_domain = store.get_ontology(domain_key, tenant_id)
    if existing_domain:
        print(f"Domain 已存在，跳過導入: {existing_domain.ontology_name} (key: {domain_key})")
    else:
        create_d = OntologyCreate(
            type=raw_d["type"],
            name=raw_d["name"],
            version=raw_d["version"],
            default_version=raw_d.get("default_version", True),
            ontology_name=raw_d["ontology_name"],
            description=raw_d.get("description"),
            author=raw_d.get("author"),
            last_modified=raw_d.get("last_modified"),
            inherits_from=raw_d.get("inherits_from", []),
            compatible_domains=raw_d.get("compatible_domains", []),
            tags=raw_d.get("tags", []),
            use_cases=raw_d.get("use_cases", []),
            entity_classes=raw_d.get("entity_classes", []),
            object_properties=raw_d.get("object_properties", []),
            metadata=raw_d.get("metadata", {}),
            tenant_id=None,
        )
        store.save_ontology(create_d, tenant_id=None)
        print("Domain imported:", create_d.ontology_name)

    raw_m = _load_json(major_path)
    major_key = _generate_ontology_key(raw_m["type"], raw_m["name"], raw_m["version"], tenant_id)
    existing_major = store.get_ontology(major_key, tenant_id)
    if existing_major:
        print(f"Major 已存在，跳過導入: {existing_major.ontology_name} (key: {major_key})")
    else:
        create_m = OntologyCreate(
            type=raw_m["type"],
            name=raw_m["name"],
            version=raw_m["version"],
            default_version=raw_m.get("default_version", True),
            ontology_name=raw_m["ontology_name"],
            description=raw_m.get("description"),
            author=raw_m.get("author"),
            last_modified=raw_m.get("last_modified"),
            inherits_from=raw_m.get("inherits_from", []),
            compatible_domains=raw_m.get("compatible_domains", ["mm-agent-domain.json"]),
            tags=raw_m.get("tags", []),
            use_cases=raw_m.get("use_cases", []),
            entity_classes=raw_m.get("entity_classes", []),
            object_properties=raw_m.get("object_properties", []),
            metadata=raw_m.get("metadata", {}),
            tenant_id=None,
        )
        store.save_ontology(create_m, tenant_id=None)
        print("Major imported:", create_m.ontology_name)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
